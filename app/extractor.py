import json
from groq import Groq

from app.config import (
    GROQ_API_KEY, GROQ_MODEL,
    CEILING_PRICE, TARGET_PRICE, OPENING_OFFER,
    MAX_ROUNDS_BEFORE_ESCALATE, CONFIDENCE_ESCALATE_BELOW, NEAR_CEILING_FRACTION,
)
import os
from openai import OpenAI
from pydantic import BaseModel

# class DealExtraction(BaseModel):
#     item: str | None
#     quantity: int | None
#     price: float | None
#     currency: str | None
#     payment_terms: str | None
#     delivery_terms: str | None
#     requested_changes: list[str]
#     intent: str
#     urgency: str
#     risk_flags: list[str]

# To extract the deal details from the message, we can use a simple function that looks for specific keywords and patterns in the text. Here's an example implementation:
SYSTEM_PROMPT="""You are a deal-information extraction agent for a procurement negotiation system.

Your job is to read the incoming message from a counterparty and extract only the information explicitly stated or strongly implied in the message.

Extract:

1. item:
   - The product or service being negotiated.
   - Return null if it cannot be identified.

2. quantity:
   - Number of units/items requested or discussed.
   - Return null if not mentioned.

3. price:
   - The price or offer stated by the counterparty.
   - Return null if no price is mentioned.
   - Return only the numeric value.

4. currency:
   - Currency associated with the price.
   - Examples: USD, EUR, GBP, INR.
   - Return null if not specified.

5. payment_terms:
   - Payment terms such as "Net 30", "50% upfront", "due on delivery".
   - Return null if not mentioned.

6. delivery_terms:
   - Delivery/shipping timing or conditions.
   - Return null if not mentioned.

7. requested_changes:
   - Any terms or conditions the counterparty wants changed.
   - Return an empty list if none.

8. intent:
   - Classify the counterparty's main intent as one of:
     "new_offer",
     "counter_offer",
     "acceptance",
     "rejection",
     "question",
     "information",
     "other".

9. urgency:
   - "low", "medium", or "high".
   - Use "high" only when the message explicitly indicates urgency, deadline, or immediate action.

10. risk_flags:
   - List unusual, ambiguous, threatening, or potentially important negotiation statements.
   - Return an empty list if none.

Rules:
- Do not invent information.
- Do not infer a price when none is stated.
- Preserve the meaning of the counterparty's message.
- If multiple prices are mentioned, identify the counterparty's current offer and explain the distinction in risk_flags if necessary.
- Return ONLY valid JSON.
- Do not include markdown or explanations outside the JSON.

JSON schema:

{
  "item": null,
  "quantity": null,
  "price": null,
  "currency": null,
  "payment_terms": null,
  "delivery_terms": null,
  "requested_changes": [],
  "intent": "other",
  "urgency": "low",
  "risk_flags": []
}

"""



USER_PROMPT="""Extract the deal information from this incoming counterparty message:

{{incoming_message}}

"""



client = Groq(api_key=GROQ_API_KEY)


def extract_deal_details(message):
    completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT.replace("{{incoming_message}}", message)},
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

    deal_output = json.loads(raw)


    return deal_output

# out = extract_deal_details("We can offer 100 units of the product at $50 each, with delivery in 2 weeks. Payment terms are Net 30. We would like to change the warranty period to 1 year instead of 2 years. Please let us know if this works for you.")
# print(out)