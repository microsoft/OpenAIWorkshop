"""
Skill registry for domain-focused agent operation.

A Skill bundles together:
  - instructions  : the focused system-prompt text for that domain
  - allowed_tools : which MCP tools the agent may call
  - triggers      : keywords used for lightweight domain detection
  - fallback      : what to say when the query is out-of-domain

Usage (single agent):

    skill = SkillRegistry.select("I got a huge invoice this month")
    instructions = skill.build_instructions()
    allowed_tools = skill.allowed_tools
    # → inject instructions + filter tools before creating the agent
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Skill dataclass
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """
    A runtime skill object that encapsulates one domain's behaviour contract.

    Attributes:
        name          : Unique identifier, e.g. "billing"
        display_name  : Human-readable label shown in logs/metrics
        instructions  : System-prompt text injected into the agent
        allowed_tools : MCP tool names this skill exposes to the agent
        triggers      : Keywords (lower-case) used for detection
        fallback      : Out-of-domain response prefix
        skill_md_path : Optional relative path to the backing SKILL.md
    """

    name: str
    display_name: str
    instructions: str
    allowed_tools: List[str]
    triggers: List[str]
    fallback: str = (
        "This request is outside my area of expertise. "
        "Let me connect you with the right specialist."
    )
    skill_md_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Score this skill against a query (higher = better match)
    # ------------------------------------------------------------------
    def score(self, query: str) -> int:
        """Return the number of trigger keywords found in *query*."""
        q = query.lower()
        return sum(1 for t in self.triggers if t in q)

    # ------------------------------------------------------------------
    # Compose the full system prompt from this skill
    # ------------------------------------------------------------------
    def build_instructions(self) -> str:
        """
        Return the complete system-prompt text to inject for this skill.

        The instructions from the skill definition are used directly.
        A brief domain-boundary reminder is appended.
        """
        boundary = (
            "\n\n---\n"
            "**Domain boundary rule**: If the user's question falls outside your "
            "specialist area, respond exactly with:\n"
            f'"{self.fallback}"'
        )
        return self.instructions + boundary


# ---------------------------------------------------------------------------
# Pre-built skills
# ---------------------------------------------------------------------------

_BILLING_SKILL = Skill(
    name="billing",
    display_name="CRM & Billing Specialist",
    skill_md_path=".github/skills/contoso-billing-skill/SKILL.md",
    triggers=[
        "invoice", "invoices", "billing", "bill", "payment", "payments",
        "charge", "charged", "refund", "credit", "subscription", "autopay",
        "overdue", "balance", "data usage", "overage", "receipt", "statement",
        "amount due", "monthly fee", "pay my",
    ],
    allowed_tools=[
        "get_all_customers",
        "get_customer_detail",
        "get_subscription_detail",
        "get_billing_summary",
        "get_invoice_payments",
        "pay_invoice",
        "get_data_usage",
        "update_subscription",
        "search_knowledge_base",
    ],
    instructions=(
        "You are the CRM & Billing Specialist for Contoso customer support.\n\n"
        "## Your Expertise\n"
        "- Customer accounts, subscriptions, billing, invoices, payments\n"
        "- Account adjustments, data usage, subscription updates\n\n"
        "## Critical Rules\n"
        "1. ALWAYS use your tools to retrieve factual data. NEVER guess billing amounts, "
        "rates, or account details.\n"
        "2. Cite specific data from tools: invoice #, payment date, usage in GB, customer ID.\n"
        "3. Be concise and professional. Provide exact amounts, dates, and action items.\n\n"
        "## Available Tools\n"
        "Use: get_customer_detail, get_billing_summary, get_subscription_detail, "
        "get_invoice_payments, pay_invoice, get_data_usage, update_subscription, "
        "search_knowledge_base"
    ),
)

_PRODUCT_SKILL = Skill(
    name="product",
    display_name="Product & Promotions Specialist",
    skill_md_path=".github/skills/contoso-product-skill/SKILL.md",
    triggers=[
        "product", "products", "plan", "plans", "upgrade", "downgrade",
        "speed", "speeds", "promotion", "promotions", "discount", "discounts",
        "offer", "offers", "feature", "features", "internet", "mobile", "tv",
        "bundle", "bundles", "roaming", "hotspot", "static ip", "eligib",
        "recommend", "compare plans", "which plan",
    ],
    allowed_tools=[
        "get_products",
        "get_product_detail",
        "get_promotions",
        "get_eligible_promotions",
        "get_customer_orders",
        "search_knowledge_base",
    ],
    instructions=(
        "You are the Product & Promotions Specialist for Contoso customer support.\n\n"
        "## Your Expertise\n"
        "- Product catalog: Internet, Mobile, TV, Bundle plans with full feature specs\n"
        "- Active promotions, discounts, eligibility rules\n"
        "- Customer orders, product recommendations, upsell opportunities\n\n"
        "## Critical Rules\n"
        "1. ALWAYS use tools to retrieve features, pricing, or eligibility. NEVER guess.\n"
        "2. Cite product IDs, promotion codes, and specific pricing from tool responses.\n"
        "3. Be enthusiastic and helpful — highlight benefits and savings for the customer.\n\n"
        "## Available Tools\n"
        "Use: get_products, get_product_detail, get_promotions, get_eligible_promotions, "
        "get_customer_orders, search_knowledge_base"
    ),
)

_SECURITY_SKILL = Skill(
    name="security",
    display_name="Security & Authentication Specialist",
    skill_md_path=".github/skills/contoso-security-skill/SKILL.md",
    triggers=[
        "locked", "lockout", "lock out", "security", "password", "reset password",
        "authentication", "2fa", "two-factor", "mfa", "access", "unauthorized",
        "suspicious", "breach", "hacked", "compromise", "identity", "verify",
        "log in", "login", "cannot log",
    ],
    allowed_tools=[
        "get_security_logs",
        "unlock_account",
        "get_support_tickets",
        "create_support_ticket",
        "search_knowledge_base",
    ],
    instructions=(
        "You are the Security & Authentication Specialist for Contoso customer support.\n\n"
        "## Your Expertise\n"
        "- Account lockouts, failed login attempts, account recovery\n"
        "- Security incident investigation using security logs\n"
        "- Support ticket creation and escalation for security issues\n\n"
        "## Critical Rules\n"
        "1. ALWAYS verify customer identity before taking any account action.\n"
        "2. NEVER guess or hallucinate security data — retrieve actual logs and tickets.\n"
        "3. Treat all security reports seriously. Escalate when in doubt.\n"
        "4. Cite log timestamps, incident IDs, and ticket numbers when explaining.\n\n"
        "## Available Tools\n"
        "Use: get_security_logs, unlock_account, get_support_tickets, "
        "create_support_ticket, search_knowledge_base"
    ),
)

# Fallback when no domain can be detected
_GENERAL_SKILL = Skill(
    name="general",
    display_name="General Support",
    triggers=[],
    allowed_tools=[
        "get_all_customers",
        "get_customer_detail",
        "get_billing_summary",
        "get_subscription_detail",
        "get_products",
        "search_knowledge_base",
    ],
    instructions=(
        "You are a helpful Contoso customer support assistant.\n"
        "Use the available tools to answer customer questions.\n"
        "Never hallucinate operations not supported by your tools.\n"
        "If a question is too specialised, acknowledge that and offer to "
        "connect the customer with the right team."
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """
    Central registry of all available skills.

    Call ``SkillRegistry.select(query)`` at the start of each request to get
    the best-matching Skill object.  Use its ``instructions`` and
    ``allowed_tools`` to configure the agent for that turn.
    """

    _skills: List[Skill] = [_BILLING_SKILL, _PRODUCT_SKILL, _SECURITY_SKILL]
    _fallback: Skill = _GENERAL_SKILL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def select(cls, query: str) -> Tuple[Skill, float]:
        """
        Select the best-matching skill for *query*.

        Returns:
            (skill, confidence)  where confidence is 0.0–1.0.
            Falls back to the general skill when no triggers match.
        """
        scores = [(skill.score(query), skill) for skill in cls._skills]
        best_score, best_skill = max(scores, key=lambda x: x[0])

        if best_score == 0:
            logger.debug("[Skills] No domain match — using general skill.")
            return cls._fallback, 0.0

        # Confidence: cap at 1.0; assumes ~5 keyword hits = full confidence
        confidence = min(1.0, best_score / 5.0)
        logger.info(
            f"[Skills] Selected '{best_skill.name}' "
            f"(score={best_score}, confidence={confidence:.2f})"
        )
        return best_skill, confidence

    @classmethod
    def get(cls, name: str) -> Optional[Skill]:
        """Return skill by name, or None if not found."""
        for skill in cls._skills:
            if skill.name == name:
                return skill
        if cls._fallback.name == name:
            return cls._fallback
        return None

    @classmethod
    def all_skills(cls) -> List[Skill]:
        """Return all registered domain skills (excluding fallback)."""
        return list(cls._skills)

    # ------------------------------------------------------------------
    # Optional: load instructions from backing SKILL.md at startup
    # ------------------------------------------------------------------

    @classmethod
    def load_instructions_from_md(cls, workspace_root: str) -> None:
        """
        Optionally overwrite each skill's ``instructions`` field with the
        body of its backing SKILL.md file.

        This lets you edit the .md files without touching the Python registry.
        Call once at application start if you want .md-driven instructions.
        """
        for skill in cls._skills:
            if not skill.skill_md_path:
                continue
            full_path = os.path.join(workspace_root, skill.skill_md_path)
            try:
                with open(full_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                body = cls._strip_frontmatter(content)
                if body:
                    skill.instructions = body
                    logger.info(
                        f"[Skills] Loaded instructions for '{skill.name}' "
                        f"from {skill.skill_md_path}"
                    )
            except FileNotFoundError:
                logger.warning(
                    f"[Skills] SKILL.md not found for '{skill.name}': {full_path}. "
                    "Using built-in instructions."
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_frontmatter(content: str) -> str:
        """Remove YAML frontmatter (between --- delimiters) and return body."""
        lines = content.split("\n")
        fence_count = 0
        body: List[str] = []
        for line in lines:
            if line.strip() == "---":
                fence_count += 1
                continue
            if fence_count >= 2:
                body.append(line)
        return "\n".join(body).strip()
