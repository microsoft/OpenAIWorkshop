from __future__ import annotations  
  
import asyncio  
import os  
import sqlite3  
import uuid  
from datetime import datetime, timedelta  
from typing import List, Optional, Dict, Any  
  
from dotenv import load_dotenv  
from fastmcp import FastMCP  
from pydantic import BaseModel, Field, field_validator  
import logging
  
# ──────────────────── FastMCP initialisation ────────────────────────  
mcp = FastMCP(  
    name="Contoso Logistics API as Tools",  
    instructions=(  
        "You are the Logistics agent responsible for arranging product-return "  
        "pick-ups.  All logistics information is accessible *solely* through "  
        "the tool endpoints declared below and their pydantic schemas.  "  
        "NEVER reveal implementation or database details – return exactly and "  
        "only the schema-conforming JSON."  
    ),  
)  
  
# ───────────────────── Env / database helper ────────────────────────  
load_dotenv()  
DB_PATH = os.getenv("DB_PATH", "data/contoso.db")  
  
  
def get_db() -> sqlite3.Connection:  
    """Lightweight helper; also lazily creates the Pickups table the first  
    time the Logistics agent touches the database."""  
    db = sqlite3.connect(DB_PATH)  
    db.row_factory = sqlite3.Row  
    db.execute(  
        """  
        CREATE TABLE IF NOT EXISTS Pickups(  
            pickup_id   INTEGER PRIMARY KEY AUTOINCREMENT,  
            order_id    INTEGER,  
            slot_id     TEXT,  
            date        TEXT,  
            start_time  TEXT,  
            end_time    TEXT,  
            carrier     TEXT,  
            address     TEXT,  
            status      TEXT,  
            created_at  TEXT  
        )  
        """  
    )  
    db.commit()  
    return db  
  
# ───────────────────────── Pydantic models ──────────────────────────  
  
class PickupAvailabilityRequest(BaseModel):  
    """  
    Request parameters sent by a foreign agent (e.g. CS agent) to ask  
    for available pick-up slots.  
    """  
  
    address: str = Field(..., description="Street address for the return pick-up")  
    earliest_date: str = Field(  description="First acceptable date (YYYY-MM-DD)")  
    latest_date: Optional[str] = Field( description="Last acceptable date (YYYY-MM-DD)"  
    )  
    count: Optional[int] = Field(  
        5, description="How many candidate slots to return (max 10)"  
    )  
  
    @field_validator("earliest_date", mode="before")  
    @classmethod  
    def _default_earliest(cls, v):  
        return v or (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")  
  
    @field_validator("latest_date", mode="before")  
    @classmethod  
    def _default_latest(cls, v):  
        return v or (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")  
  
    @field_validator("count")  
    @classmethod  
    def _count_bounds(cls, v):  
        if not 1 <= v <= 10:  
            raise ValueError("count must be between 1 and 10")  
        return v  
  
class PickupSlot(BaseModel):  
    """A single concrete pick-up slot offered by Logistics."""  
    slot_id: str  
    date: str  # YYYY-MM-DD  
    start_time: str  # HH:MM (24h)  
    end_time: str  # HH:MM (24h)  
    carrier: str  
  
class PickupAvailabilityResponse(BaseModel):  
    """List of slots the caller may choose from."""  
    slots: List[PickupSlot]  
  
class SelectedSlot(PickupSlot):  
    """The slot the calling agent picked to schedule."""  
  
class PickupConfirmationRequest(BaseModel):  
    """Request to lock in / schedule a chosen slot for a return."""  
    order_id: int  
    address: str  
    slot: SelectedSlot  
  
class PickupScheduledConfirmation(BaseModel):  
    """Success response once Logistics has reserved the carrier."""  
    pickup_id: int  
    order_id: int  
    slot: PickupSlot  
    status: str  # scheduled | in_transit | completed | cancelled  
  
class PickupStatus(BaseModel):  
    """Status lookup response."""  
    pickup_id: int  
    order_id: int  
    carrier: str  
    status: str  
    date: str  
    start_time: str  
    end_time: str  
    address: str  
  
# ───────────────────────────── Tools ────────────────────────────────  
  
@mcp.tool(description="Return available return-pickup slots for the given address / date range.")  
def get_pickup_availability(  
    params: PickupAvailabilityRequest,  
) -> PickupAvailabilityResponse:  
    """  
    A *very* simple availability generator: for every business day in the  
    requested interval we expose three windows – 09-12, 12-15, 15-18 –  
    until we have satisfied `count` slots.  
    """  
    print(f"Received availability request: {params}")  # Debug output
    carriers = ["UPS", "FedEx", "DHL"]  # round-robin assignment  
  
    start = datetime.strptime(params.earliest_date, "%Y-%m-%d")  
    end = datetime.strptime(params.latest_date, "%Y-%m-%d")  
    if end < start:  
        raise ValueError("latest_date must be after earliest_date")  
  
    slots: List[PickupSlot] = []  
    day_cursor = start  
    while len(slots) < params.count and day_cursor <= end:  
        if day_cursor.weekday() < 5:  # Mon-Fri only  
            for window in (("09:00", "12:00"), ("12:00", "15:00"), ("15:00", "18:00")):  
                if len(slots) >= params.count:  
                    break  
                slots.append(  
                    PickupSlot(  
                        slot_id=uuid.uuid4().hex[:8],  
                        date=day_cursor.strftime("%Y-%m-%d"),  
                        start_time=window[0],  
                        end_time=window[1],  
                        carrier=carriers[len(slots) % len(carriers)],  
                    )  
                )  
        day_cursor += timedelta(days=1) 
    logging.debug("Generated slots: %s", slots)  # Debug output 
  
    return PickupAvailabilityResponse(slots=slots)  
  
@mcp.tool(description="Lock in a selected slot and schedule the carrier pick-up.")  
def schedule_pickup(  
    request: PickupConfirmationRequest,  
) -> PickupScheduledConfirmation:  
    db = get_db()  
    try:
        cur = db.execute(  
                """  
                INSERT INTO Pickups(order_id, slot_id, date, start_time, end_time,  
                                    carrier, address, status, created_at)  
                VALUES (?,?,?,?,?,?,?,?,?)  
                """,  
                (  
                    request.order_id,  
                    request.slot.slot_id,  
                    request.slot.date,  
                    request.slot.start_time,  
                    request.slot.end_time,  
                    request.slot.carrier,  
                    request.address,  
                    "scheduled",  
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),  
                ),  
            )  
        pickup_id = cur.lastrowid  
        db.commit()  
        db.close()  
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")  # Log database errors
    
  
    return PickupScheduledConfirmation(  
        pickup_id=pickup_id,  
        order_id=request.order_id,  
        slot=request.slot,  
        status="scheduled",  
    )  
  
@mcp.tool(description="Retrieve current status for an existing pick-up.")  
def get_pickup_status(pickup_id: int) -> PickupStatus:  
    db = get_db()  
    row = db.execute("SELECT * FROM Pickups WHERE pickup_id = ?", (pickup_id,)).fetchone()  
    db.close()  
    if not row:  
        raise ValueError("Pickup not found")  
  
    return PickupStatus(**dict(row))  
  
@mcp.tool(description="Cancel a previously scheduled pick-up.")  
def cancel_pickup(pickup_id: int) -> Dict[str, Any]:  
    db = get_db()  
    cur = db.execute(  
        "UPDATE Pickups SET status = 'cancelled' WHERE pickup_id = ? AND status = 'scheduled'",  
        (pickup_id,),  
    )  
    db.commit()  
    db.close()  
  
    if cur.rowcount == 0:  
        raise ValueError("Pickup not found or cannot be cancelled")  
  
    return {"pickup_id": pickup_id, "status": "cancelled"}  
  
# ────────────────────────── Run server ─────────────────────────────  
  
if __name__ == "__main__":  
    asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8100))  