# Agent Framework State Management Guide

State in the Agent Framework is managed at two complementary layers:

1. **Agent threads** – Persist conversation history, tool invocations, and service-managed context for a single agent.
2. **Workflows (multi-agent orchestration)** – Persist executor-local data, shared workflow state, and queued messages/checkpoints for whole teams.

This guide explains how those layers work together, how to persist and restore state for multi-turn conversations, and how to plug in external storage such as Redis, Azure Cosmos DB, or application-level memory keyed by user sessions.

---

## 1. Key building blocks

| Concept | File(s) | Purpose |
| --- | --- | --- |
| `AgentThread` | `python/packages/main/agent_framework/_threads.py` | Ties an agent run to either a service-managed thread ID or a custom `ChatMessageStore`. |
| `ChatMessageStore` protocol | `python/packages/main/agent_framework/_threads.py` | Pluggable persistence for chat histories and tool call transcripts. |
| `WorkflowContext` | `python/packages/main/agent_framework/_workflow/_workflow_context.py` | Gives executors APIs to send messages, yield workflow outputs, and mutate state. |
| `Executor` | `python/packages/main/agent_framework/_workflow/_executor.py` | Base class for workflow units (agents, tools, orchestrators). Supports custom `snapshot_state`/`restore_state`. |
| `WorkflowCheckpoint` + `CheckpointStorage` | `python/packages/main/agent_framework/_workflow/_checkpoint.py` | Encodes full workflow snapshots and pluggable persistence backends. |
| `InProcRunnerContext` | `python/packages/main/agent_framework/_workflow/_runner_context.py` | Implements message queues, shared state, and checkpoint creation/restoration. |

---

## 2. Single-agent state lifecycle

### 2.1 Creation paths

1. **Service-managed threads** – Provide `service_thread_id` on `AgentThread`. Azure OpenAI Assistants and similar services store conversation state on their side; the framework simply remembers the ID.
2. **Self-managed threads** – Provide `message_store` implementing `ChatMessageStore`. The framework will append every user/assistant/tool message via `thread_on_new_messages` and pull history with `list_messages()` when preparing the next model call.
3. **Default in-memory store** – If neither `service_thread_id` nor `message_store` is passed, the agent uses `ChatMessageList`, a simple list-backed store.

### 2.2 What gets stored

Each `ChatMessage` serialized by the store includes:

- Role (`user`, `assistant`, `tool`, system),
- Text/components,
- Tool call metadata via `FunctionCallContent`,
- Tool outputs via `FunctionResultContent`,
- Timestamps and optional annotations.

A well-behaved store persists messages exactly as received so the agent can replay tool calls and results on restore.

### 2.3 Persisting and restoring

```python
from agent_framework import AgentThread
from agent_framework._threads import deserialize_thread_state

async def save_thread(thread: AgentThread, persist_fn):
    serialized = await thread.serialize()
    await persist_fn(serialized)  # write to DB, blob, etc.

async def load_thread(store_factory, fetch_fn) -> AgentThread:
    state = await fetch_fn()
    thread = AgentThread(message_store=store_factory())
    await deserialize_thread_state(thread, state)
    return thread
```

- `AgentThread.serialize()` emits `{"service_thread_id": "...", "chat_message_store_state": {...}}`.
- `deserialize_thread_state` hydrates either the thread ID or `message_store` snapshot.

> **Tip:** Use `chat_message_store_factory` on higher-level agent builders to lazily create typed stores per thread/session (see the Redis sample in `python/samples/getting_started/threads/redis_chat_message_store_thread.py`).

---

## 3. Multi-turn agent persistence recipes

### 3.1 Application in-memory store keyed by session ID

```python
from collections import defaultdict
from typing import Dict
from agent_framework import AgentThread, ChatAgent
from agent_framework._threads import ChatMessageList

_session_threads: Dict[str, AgentThread] = {}
_session_messages: Dict[str, ChatMessageList] = defaultdict(ChatMessageList)

def get_or_create_thread(session_id: str) -> AgentThread:
    if session_id not in _session_threads:
        store = _session_messages[session_id]
        _session_threads[session_id] = AgentThread(message_store=store)
    return _session_threads[session_id]

async def chat(session_id: str, user_input: str, agent: ChatAgent) -> str:
    thread = get_or_create_thread(session_id)
    result = await agent.run(user_input, thread=thread)
    return result.text
```

Use this pattern for short-lived apps or when you pair in-memory state with your own eviction/TTL policy.

### 3.2 Persisting to Redis

- Preferred when you need durability or horizontal scaling.
- Reuse `RedisChatMessageStore` (`agent_framework.redis` package) as shown in `python/samples/getting_started/threads/redis_chat_message_store_thread.py`.
- Each store instance gets a `thread_id`; reuse that ID to resume conversations after restarts.

```python
from agent_framework import AgentThread
from agent_framework.redis import RedisChatMessageStore

def session_store_factory(user_id: str, session_id: str) -> RedisChatMessageStore:
    return RedisChatMessageStore(
        redis_url="redis://localhost:6379",
        thread_id=f"user:{user_id}:session:{session_id}",
        max_messages=200,
    )
```

### 3.3 Persisting to Azure Cosmos DB

Implement a custom `ChatMessageStore` that:

1. Stores serialized `ChatMessage` objects in a container (partition by `thread_id`).
2. Implements `list_messages` by querying in ascending timestamp order.
3. Implements `serialize_state` / `deserialize_state` to dump/load cached messages when you don’t fetch directly from Cosmos on every call.

```python
from azure.cosmos.aio import CosmosClient
from agent_framework._threads import ChatMessageStore, StoreState
from agent_framework._types import ChatMessage

class CosmosChatMessageStore(ChatMessageStore):
    def __init__(self, client: CosmosClient, database: str, container: str, thread_id: str):
        self._client = client
        self._container = client.get_database_client(database).get_container_client(container)
        self._thread_id = thread_id
        self._cache: list[ChatMessage] = []

    async def list_messages(self) -> list[ChatMessage]:
        if not self._cache:
            query = "SELECT * FROM c WHERE c.threadId=@threadId ORDER BY c.ts ASC"
            params = [{"name": "@threadId", "value": self._thread_id}]
            items = self._container.query_items(query=query, parameters=params, enable_cross_partition_query=False)
            self._cache = [ChatMessage.model_validate(item["payload"]) async for item in items]
        return self._cache

    async def add_messages(self, messages: list[ChatMessage]) -> None:
        for message in messages:
            doc = {
                "id": f"{self._thread_id}:{message.id}",
                "threadId": self._thread_id,
                "ts": message.created_at or message.id,
                "payload": message.model_dump(mode="json"),
            }
            await self._container.upsert_item(doc)
        self._cache.extend(messages)

    async def serialize_state(self, **_) -> dict:
        return StoreState(messages=self._cache).model_dump(mode="json")

    async def deserialize_state(self, serialized_store_state: dict, **_) -> None:
        state = StoreState.model_validate(serialized_store_state)
        self._cache = state.messages
```

> **Note:** Replace `message.id` with a deterministic key if your payloads don’t include IDs.

### 3.4 Persisting to your own database

- Implement `ChatMessageStore` once.
- Serialize `StoreState` JSON to your database.
- Register a factory that returns a new store instance for each thread.

---

## 4. Workflow (multi-agent) state architecture

### 4.1 Executors and state

- Every executor extends `Executor` (`snapshot_state`, `restore_state`, handler methods).
- During execution, the framework calls handlers decorated with `@handler`.
- Handler signature includes `WorkflowContext`, letting you:
  - `send_message(...)` to downstream executors.
  - `yield_output(...)` to emit workflow outputs.
  - `set_state(...)` / `get_state(...)` for executor-local persistence (json-serializable).
  - `set_shared_state(...)` / `get_shared_state(...)` for workflow-wide coordination.

### 4.2 Runner context & message queues

`InProcRunnerContext` stores:

- `messages`: pending messages per executor.
- `shared_state`: `SharedState` dictionary visible to all executors.
- `executor_states`: map of executor ID → state snapshots.
- `iteration_count`, `max_iterations`: loop control.
- `events`: streaming updates (useful for UIs).

This context is what gets serialized in checkpoints.

### 4.3 Multi-agent conversation details

- Magentic teams (`python/packages/main/agent_framework/_workflow/_magentic.py`) wrap each participant in a `MagenticAgentExecutor`.
- Each participant’s conversation is a `chat_history` list (a sequence of `ChatMessage` dicts).
- The orchestrator tracks roster metadata, plan reviews, and manager state.
- On checkpoint, orchestrator + each participant contribute their own snapshot.

---

## 5. Workflow checkpointing

### 5.1 Creating checkpoints

```python
from agent_framework._workflow import Workflow

runner = Workflow(...).build_runner(checkpoint_storage=my_storage)
runner.set_workflow_id("order-tracking")

await runner.run(initial_input)
checkpoint_id = await runner.create_checkpoint(metadata={"user": "alice"})
```

- Call `create_checkpoint` whenever you reach a turn boundary, a human-in-the-loop pause, or on a timer.
- Metadata can include user/session IDs, business status, etc.

### 5.2 Restoring checkpoints

```python
restored = await runner.restore_from_checkpoint(checkpoint_id)
if not restored:
    raise RuntimeError("Checkpoint could not be loaded")

await runner.run(next_input)
```

- `restore_from_checkpoint` repopulates message queues, executor states, shared state, and iteration counters before processing new input.

### 5.3 WorkflowCheckpoint payload

```json
{
  "checkpoint_id": "guid",
  "workflow_id": "order-tracking",
  "messages": { "executorA": [ ... ], "executorB": [ ... ] },
  "shared_state": { "orders": [...], "status": "awaiting-approval" },
  "executor_states": {
    "executorA": { "last_prompt": "...", "pending_tools": [...] },
    "executorB": { "chat_history": [...], "request_ids": [...] }
  },
  "iteration_count": 4,
  "metadata": { "user": "alice" }
}
```

Executors can include arbitrary JSON-friendly payloads in their `snapshot_state`.

---

## 6. External checkpoint storage implementations

### 6.1 Redis-backed CheckpointStorage

```python
import json
from aioredis import Redis
from agent_framework._workflow._checkpoint import CheckpointStorage, WorkflowCheckpoint

class RedisCheckpointStorage(CheckpointStorage):
    def __init__(self, redis: Redis, namespace: str = "af:workflow:"):
        self._redis = redis
        self._namespace = namespace

    def _key(self, checkpoint_id: str) -> str:
        return f"{self._namespace}{checkpoint_id}"

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> str:
        payload = json.dumps(checkpoint.to_dict(), ensure_ascii=False)
        await self._redis.set(self._key(checkpoint.checkpoint_id), payload)
        if checkpoint.workflow_id:
            await self._redis.sadd(f"{self._namespace}wf:{checkpoint.workflow_id}", checkpoint.checkpoint_id)
        return checkpoint.checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        payload = await self._redis.get(self._key(checkpoint_id))
        if not payload:
            return None
        return WorkflowCheckpoint.from_dict(json.loads(payload))

    async def list_checkpoint_ids(self, workflow_id: str | None = None) -> list[str]:
        if workflow_id is None:
            pattern = f"{self._namespace}*"
            keys = await self._redis.keys(pattern)
            return [key[len(self._namespace):] for key in keys if not key.endswith(":wf")]
        ids = await self._redis.smembers(f"{self._namespace}wf:{workflow_id}")
        return list(ids)

    async def list_checkpoints(self, workflow_id: str | None = None) -> list[WorkflowCheckpoint]:
        ids = await self.list_checkpoint_ids(workflow_id)
        checkpoints = []
        for cid in ids:
            cp = await self.load_checkpoint(cid)
            if cp:
                checkpoints.append(cp)
        return checkpoints

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        key = self._key(checkpoint_id)
        removed = await self._redis.delete(key)
        return removed > 0
```

### 6.2 Azure Cosmos DB CheckpointStorage

```python
from azure.cosmos.aio import CosmosClient
from agent_framework._workflow._checkpoint import CheckpointStorage, WorkflowCheckpoint

class CosmosCheckpointStorage(CheckpointStorage):
    def __init__(self, client: CosmosClient, db_name: str, container_name: str):
        self._container = client.get_database_client(db_name).get_container_client(container_name)

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> str:
        document = checkpoint.to_dict()
        document["id"] = checkpoint.checkpoint_id
        await self._container.upsert_item(document)
        return checkpoint.checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        try:
            doc = await self._container.read_item(checkpoint_id, partition_key=checkpoint_id)
        except Exception:
            return None
        return WorkflowCheckpoint.from_dict(doc)

    async def list_checkpoint_ids(self, workflow_id: str | None = None) -> list[str]:
        if workflow_id:
            query = "SELECT c.id FROM c WHERE c.workflow_id = @workflow_id"
            params = [{"name": "@workflow_id", "value": workflow_id}]
        else:
            query = "SELECT c.id FROM c"
            params = []
        return [doc["id"] async for doc in self._container.query_items(query, parameters=params)]

    async def list_checkpoints(self, workflow_id: str | None = None) -> list[WorkflowCheckpoint]:
        ids = await self.list_checkpoint_ids(workflow_id)
        checkpoints = []
        for cid in ids:
            cp = await self.load_checkpoint(cid)
            if cp:
                checkpoints.append(cp)
        return checkpoints

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        try:
            await self._container.delete_item(checkpoint_id, partition_key=checkpoint_id)
            return True
        except Exception:
            return False
```

> Use a synthetic partition key (e.g., checkpoint ID) or a composite key based on `workflow_id` + checkpoint ID depending on your throughput patterns.

### 6.3 In-memory cache scoped by user session

For stateless APIs that only need short-lived state:

```python
from collections import defaultdict
from agent_framework._workflow._checkpoint import WorkflowCheckpoint, CheckpointStorage

class SessionMemoryCheckpointStorage(CheckpointStorage):
    def __init__(self):
        self._store = defaultdict(dict)  # {workflow_id: {checkpoint_id: WorkflowCheckpoint}}

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> str:
        wf_id = checkpoint.workflow_id or "_"
        self._store[wf_id][checkpoint.checkpoint_id] = checkpoint
        return checkpoint.checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        for checkpoints in self._store.values():
            if checkpoint_id in checkpoints:
                return checkpoints[checkpoint_id]
        return None

    async def list_checkpoint_ids(self, workflow_id: str | None = None) -> list[str]:
        if workflow_id is None:
            return [cid for checkpoints in self._store.values() for cid in checkpoints]
        return list(self._store[workflow_id])

    async def list_checkpoints(self, workflow_id: str | None = None) -> list[WorkflowCheckpoint]:
        if workflow_id is None:
            return [cp for checkpoints in self._store.values() for cp in checkpoints.values()]
        return list(self._store[workflow_id].values())

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        for wf_id, checkpoints in self._store.items():
            if checkpoint_id in checkpoints:
                del checkpoints[checkpoint_id]
                if not checkpoints:
                    del self._store[wf_id]
                return True
        return False
```

---

## 7. Multi-turn patterns combining agents and workflows

1. **Single agent → stored thread → workflow**  
   - Persist the agent’s `AgentThread` alongside the workflow checkpoint metadata.
   - When resuming, hydrate the thread first, then restore the workflow so downstream agents have history.

2. **Team agent**  
   - `MagenticOrchestratorExecutor` automatically snapshots each participant’s `chat_history`.
   - Checkpoints include outstanding tool requests and plan-review state managed by the orchestrator via `WorkflowEvent(type="request_info")`.
   - Ensure all custom executors implement `restore_state` to interpret snapshots after schema changes.

3. **Human-in-the-loop**  
   - Store check-point IDs keyed by user session.
   - When the user returns, restore the checkpoint, push the human response as a message, and resume the workflow.

---

## 8. Best practices

- **Keep stores stateless per thread** – Avoid reusing a `ChatMessageStore` instance across threads; create a new one per conversation to prevent leaking history.
- **Use JSON-safe data** – `CheckpointStorage` and `ChatMessageStore` should emit JSON-serializable structures; Pydantic models are handled automatically by checkpoint encoding.
- **Back up schemas** – When evolving custom store formats, include version metadata so you can migrate old snapshots gracefully.
- **Leverage metadata** – Add user/session IDs and domain-specific identifiers to checkpoint metadata for auditability and targeted restores.
- **Throttle checkpoint frequency** – For workflows with frequent turns, checkpoint at logical milestones to balance durability with storage cost.

---

## 9. Troubleshooting checklist

- **Missing tool calls after restore** → Ensure your `ChatMessageStore.serialize_state` includes tool-role messages; verify both `FunctionCallContent` and `FunctionResultContent` fields round-trip.
- **Executor state not restored** → Confirm `snapshot_state` returns JSON-friendly dicts and `restore_state` handles absent/partial data for backward compatibility.
- **Service thread vs. custom store** → Never set both `service_thread_id` and `message_store` on the same `AgentThread`. If you switch from service-managed to self-managed, create a new thread.
- **Checkpoint restore mismatch** → For team workflows, make sure the executor IDs and topology at restore time match the snapshot; mismatches trigger validation in `MagenticOrchestratorExecutor`.

---

## 10. Additional references

- Redis message store sample: `python/samples/getting_started/threads/redis_chat_message_store_thread.py`
- Workflow orchestration fundamentals: `python/packages/main/agent_framework/_workflow/__init__.py`
- Checkpoint encoding helpers: `python/packages/main/agent_framework/_workflow/_runner_context.py`
- .NET equivalents (if you’re cross-language): `dotnet/src/Microsoft.Agents.Workflows`

Use these building blocks to tailor persistence strategies for your deployment—whether you need ultra-fast in-memory state keyed by web session, durable Redis/Cosmos stores, or full workflow checkpoints that survive restarts and redeployments.