"""
Every deal lives in deals.json (full history — what was said, what was
offered, why the agent decided what it decided).

Every time a deal is created or updated, we also rewrite deals_summary.csv —
one row per deal — so you can open it in Excel/Sheets and compare deals
at a glance without reading the full JSON.
"""
import json
import csv
import os
import uuid
from datetime import datetime, timezone

from config import DEALS_FILE, SUMMARY_FILE

def _now():
    return datetime.now(timezone.utc).isoformat()

def load_deals() -> dict:
     
    if not os.path.exists(DEALS_FILE):
         
        return {}
    with open(DEALS_FILE, "r") as f:
         
        return json.load(f)

def save_deals(deals: dict):
    with open(DEALS_FILE, "w") as f:
        json.dump(deals, f, indent=2)
    _export_summary_csv(deals)

def find_deal_by_thread(deals: dict, thread_key: str):
    """thread_key = something stable that identifies this email conversation,
    e.g. the email thread id or the counterparty's email address."""
    for deal_id, deal in deals.items():
        if deal.get("thread_key") == thread_key and deal["status"] == "negotiating":
            return deal_id, deal
    return None, None

def find_escalated_deal(deals: dict):
    """Used when a Telegram message arrives from you — find the deal
    that's currently waiting on your answer. Assumes one escalation
    open at a time; extend with a deal_id in your reply if you run more."""
    #find the escalated deals
    
    for deal_id, deal in deals.items():
        if deal["status"] == "escalated":
             #logger.info("Escaled deal:", deal['deal_id'])
            return deal_id, deal
    return None, None

    
def create_deal(thread_key: str, counterparty: str, ceiling: float, target: float, item: str,quantity: str,
                price: float, currency: str, delivery_terms: str,payment_terms:str, requested_changes:str,
                intent:str,urgency:str,risk_flags:str ) -> tuple[str, dict]:
    deals = load_deals()
    deal_id = str(uuid.uuid4())[:8]
    deal = {
        "deal_id": deal_id,
        "thread_key": thread_key,
        "counterparty": counterparty,
        "item": item,
        "ceiling_price": ceiling,
        "target_price": target,
        "current_offer": None,
        "currency" : currency,
        "quantity":quantity,
        "payment_terms":payment_terms,
        "risk_flags": risk_flags,
        "status": "negotiating",       # negotiating | escalated | accepted | rejected | walked_away
        "rounds": 0,
        "history": [],                 # list of {who, action, price, text, reasoning, timestamp}
        "created_at": _now(),
        "updated_at": _now(),
    }
    deals[deal_id] = deal
     #logger.info("Deal is logged")
    save_deals(deals)
    return deal_id, deal

def log_turn(deal_id: str, who: str, action: str, price=None, text="", reasoning=""):
    deals = load_deals()
    deal = deals[deal_id]
    deal["history"].append({
        "who": who,             # "counterparty" | "agent" | "human"
        "action": action,       # "offer" | "counter" | "accept" | "reject" | "escalate" | "resolve"
        "price": price,
        "text": text,
        "reasoning": reasoning,
        "timestamp": _now(),
    })
    if price is not None:
        deal["current_offer"] = price
    if who == "agent" and action == "counter":
        deal["rounds"] += 1
    deal["updated_at"] = _now()
    save_deals(deals)
    return deal

def set_status(deal_id: str, status: str):
    deals = load_deals()
    deals[deal_id]["status"] = status
    deals[deal_id]["updated_at"] = _now()
    save_deals(deals)
    return deals[deal_id]

def _export_summary_csv(deals: dict):
    fields = [
        "deal_id", "counterparty", "item", "ceiling_price", "target_price",
        "current_offer", "status", "rounds", "savings_vs_ceiling", "updated_at",
    ]
    with open(SUMMARY_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for deal in deals.values():
            offer = deal.get("current_offer")
            savings = (deal["ceiling_price"] - offer) if offer is not None else ""
            writer.writerow({
                "deal_id": deal["deal_id"],
                "counterparty": deal["counterparty"],
                "item": deal["item"],
                "ceiling_price": deal["ceiling_price"],
                "target_price": deal["target_price"],
                "current_offer": offer,
                "status": deal["status"],
                "rounds": deal["rounds"],
                "savings_vs_ceiling": savings,
                "updated_at": deal["updated_at"],
            })
