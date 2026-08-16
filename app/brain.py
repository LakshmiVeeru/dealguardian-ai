"""
One function, one job: given the deal-so-far and a new incoming message,
decide what the agent should do next. Returns a plain dict — no magic.

We ask the model to output ONLY JSON so we never have to guess-parse
free text. If it ever fails to parse, we escalate automatically —
that's the safe default, not a bug.
"""
import json
from groq import Groq

from app.config import (
    GROQ_API_KEY, GROQ_MODEL,
    CEILING_PRICE, TARGET_PRICE, OPENING_OFFER,
    MAX_ROUNDS_BEFORE_ESCALATE, CONFIDENCE_ESCALATE_BELOW, NEAR_CEILING_FRACTION,
)

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a procurement negotiation agent. You are BUYING on behalf of your \
principal. You must never agree to, or imply agreement to, a price above the ceiling.

Respond with ONLY a JSON object, no other text, no markdown fences. Schema:
{
  "parsed_price": <number or null>,       // price you read out of their message, if any
  "action": "counter" | "accept" | "reject" | "escalate",
  "counter_price": <number or null>,      // required if action is "counter"
  "message_to_send": "<string>",          // the email reply text, written in a professional,
                                           // friendly, concise negotiating tone. Empty string if escalating.
  "confidence": <0.0-1.0>,                // how sure you are this is the right move
  "reasoning": "<one or two sentences, for the human's eyes only, not sent to counterparty>"
}

Rules:
- NEVER propose or accept a price above the ceiling.
-  If the counterparty's offer is at or below your target price, that's a great deal — set
  action to "accept" rather than continuing to negotiate for marginal extra savings.
- If the counterparty's message contains anything you can't confidently evaluate on price alone
  (unusual terms, bundled items, ambiguous wording, a threat to walk away, anything emotionally
  charged, or a price suspiciously good or bad), set action to "escalate" and explain why in reasoning.
- If you're not escalating, negotiate firmly but reasonably toward the target price.
- Keep message_to_send under 120 words.
"""

def _build_user_prompt(deal: dict, incoming_text: str) -> str:
    history_lines = []
    for turn in deal["history"][-8:]:  # last 8 turns is plenty of context
        price_str = f" (price: {turn['price']})" if turn.get("price") is not None else ""
        history_lines.append(f"- {turn['who']} {turn['action']}{price_str}: {turn['text'][:200]}")
    history_block = "\n".join(history_lines) if history_lines else "(no prior turns)"

    return f"""DEAL CONTEXT
Item: {deal['item']}
Your ceiling price: {deal['ceiling_price']}
Your target price: {deal['target_price']}
Current known offer on the table: {deal.get('current_offer')}
Rounds so far: {deal['rounds']} (escalate if this is at or above {MAX_ROUNDS_BEFORE_ESCALATE})

HISTORY
{history_block}

NEW INCOMING MESSAGE FROM COUNTERPARTY
\"\"\"{incoming_text}\"\"\"

Decide the next action now, following the JSON schema exactly.
"""

def decide(deal: dict, incoming_text: str) -> dict:
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(deal, incoming_text)},
            ],
            temperature=0.3,
            max_completion_tokens=800,
            response_format={"type": "json_object"},
        )
        msg = completion.choices[0].message
        raw = (msg.content or "").strip()

        if not raw:
            # Safety net in case GROQ_MODEL gets swapped to a reasoning model
            # later (e.g. gpt-oss-120b) — some responses put the real content
            # in a separate `reasoning` field instead of `content`.

            raw = (getattr(msg, "reasoning", "") or "").strip()

        raw = raw.replace("```json", "").replace("```", "").strip()
        if not raw.startswith("{"):
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]

        decision = json.loads(raw)
        original_action = decision.get("action")

    except Exception as e:
         #logger.error("LLM call failed, escalating to human")
        # Anything goes wrong -> safest default is to ask the human, never guess.
        return {
            "parsed_price": None,
            "action": "escalate",
            "counter_price": None,
            "message_to_send": "",
            "confidence": 0.0,
            "reasoning": f"Model call or JSON parse failed ({e}); escalating to be safe.",
        }

    # --- Hard safety net: never trust the model blindly on the ceiling rule ---
    if decision.get("action") == "accept" and deal.get("current_offer") not in (None,):
        if deal["current_offer"] > CEILING_PRICE:
            decision["action"] = "escalate"
            decision["reasoning"] += " [Overridden: offer exceeds hard ceiling.]"
    if decision.get("action") == "counter" and decision.get("counter_price"):
        if decision["counter_price"] > CEILING_PRICE:
            decision["counter_price"] = CEILING_PRICE

    # --- Confidence / round-count escalation, enforced in code, not just prompted ---
    if decision.get("confidence", 1.0) < CONFIDENCE_ESCALATE_BELOW:
        decision["action"] = "escalate"
    if deal["rounds"] >= MAX_ROUNDS_BEFORE_ESCALATE and decision["action"] != "accept":
        decision["action"] = "escalate"
        decision["reasoning"] += " [Overridden: round limit reached.]"
    price_on_table = decision.get("parsed_price") or deal.get("current_offer")
    if price_on_table and price_on_table >= NEAR_CEILING_FRACTION * CEILING_PRICE:
        decision["action"] = "escalate"
        decision["reasoning"] += " [Overridden: offer near ceiling, human should confirm.]"

    # --- Auto-accept great deals: don't keep negotiating for marginal savings ---
        # This runs last, so it wins over the round-limit/confidence overrides above —
        # but only when the model's OWN original read of the message wasn't already
        # "escalate" (e.g. it noticed odd terms or a threat). A good price doesn't
        # excuse ignoring something else in the message that needs your attention.
        if original_action != "escalate" and price_on_table is not None and price_on_table <= TARGET_PRICE:
            decision["action"] = "accept"
            decision["counter_price"] = None
            if not decision.get("message_to_send"):
                decision["message_to_send"] = "Thanks — that price works for us. Let's finalize the deal."
            decision["reasoning"] = (
                decision.get("reasoning", "") + " [Overridden: offer at/below target price — auto-accepted.]"
            ).strip()
    
    return decision