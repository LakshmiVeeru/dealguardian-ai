"""
ONE handler for BOTH channels — this is what the hackathon rule requires.

Logic:
  - Message arrives on EMAIL from a counterparty  -> move a negotiation forward
  - Message arrives on TELEGRAM from you (owner)   -> resolve an open escalation

NOTE ON FIELD NAMES: caspian-sdk's exact `message` object attributes may differ
slightly from what's below depending on SDK version. The first time you run
this, add `print(vars(message))` inside handle() to see the real fields, then
adjust `sender_address`, `channel`, `thread_key` below to match. Everything
else in this file (the negotiation logic) does not depend on those details.
"""
from caspian_sdk import CommClient
from caspian_sdk import blocks as b

from config import CEILING_PRICE, TARGET_PRICE, OPENING_OFFER, OWNER_TELEGRAM_ADDRESS,CASPIAN_API_KEY, CASPIAN_BASE_URL
import deal_store as deal_store
import brain as brain
from helper import get_msg_id_from_file
from extractor import extract_deal_details

import logging
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


client = CommClient(api_key=CASPIAN_API_KEY, base_url=CASPIAN_BASE_URL)                      # reads CASPIAN_API_KEY / CASPIAN_BASE_URL
logger.info("Connected Caspian client")

# ---------------------------------------------------------------------------
# Telegram can't cold-start (initiate) a chat — the bot must be messaged
# first. Bootstrap: message your own bot once (e.g. send "/start"), then
# the block below captures that conversation_id here and reuses it for
# every escalation via send_message(), which only needs SEND, not INITIATE.
# ---------------------------------------------------------------------------
OWNER_CONVO_FILE = "owner_telegram_convo.txt"

def _load_owner_conversation_id():
    try:
        with open(OWNER_CONVO_FILE) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None

def _save_owner_conversation_id(conversation_id: str):
    with open(OWNER_CONVO_FILE, "w") as f:
        f.write(conversation_id)


def is_from_owner(message) -> bool:
    """Telegram messages from you (the owner) are commands, not new deals."""
    return getattr(message, "channel", "") == "telegram"


# def extract_item_and_price(text: str):
#     """Very light first-pass — brain.decide() does the real understanding.
#     This is only used to seed a brand-new deal's title before we have history."""
#     return text.strip().splitlines()[0][:80] or "Unnamed item"


client.connect_email()  # reads email credentials from .env
client.connect_telegram(bot_token=OWNER_TELEGRAM_ADDRESS)  # reads Telegram bot token from .env

# client.connect_telegram(bot_token=OWNER_TELEGRAM_ADDRESS)  # reads Telegram bot token from .env
email_conversation_id=''
@client.on_message
def handle(message):
    text = message.text or ""
    email_conversation_id = getattr(message, "conversation_id", None) if message.channel == "email" else None
    msg_id = getattr(message, "id", None) if message.channel == "email" else None
    if msg_id and message.channel=='email':
        with open("message_id.txt", "w") as f:
            f.write(msg_id)
    thread_key = getattr(message, "thread_id", None) or getattr(message, "sender", "unknown")

    # ---------------------------------------------------------------
    # CASE 1: You, replying on Telegram, resolving an escalation
    # ---------------------------------------------------------------
    if is_from_owner(message):
        # Always keep the freshest conversation_id, in case it changes.
        _save_owner_conversation_id(message.conversation_id)

        deals = deal_store.load_deals()
        deal_id, deal = deal_store.find_escalated_deal(deals)
        if not deal_id:
             #logger.info("No deal is currently waiting on you.")
            message.reply("No deal is currently waiting on you.")
            return

        instruction = text.strip().lower()
        if instruction in ("approve", "accept", "yes"):
            deal_store.log_turn(deal_id, "human", "resolve", price=deal.get("current_offer"),
                                 text="Human approved current offer.")
            deal_store.set_status(deal_id, "accepted")
            # client.initiate(deal["thread_key"], deal["counterparty"],
            #                  f"Great — we accept your offer. Let's finalize the deal.")
            msg_id = get_msg_id_from_file()
            client.reply(msg_id, f"Great — we accept your offer. Let's finalize the deal.")
            message.reply(f"Deal {deal_id} accepted at {deal.get('current_offer')}. Notified counterparty.")

        elif instruction in ("reject", "no", "walk away", "walk"):
            deal_store.log_turn(deal_id, "human", "resolve", text="Human rejected / walked away.")
            deal_store.set_status(deal_id, "walked_away")
            # client.initiate(deal["thread_key"], deal["counterparty"],
            #                  "Thanks for the discussion, but we won't be moving forward at this price.")
            # client.reply(deal["thread_key"], deal["counterparty"],
            #              "Thanks for the discussion, but we won't be moving forward at this price.")
            # with open("email_conversation_id.txt", "r") as f:
            #     msg_id = f.read().strip()
                # client.reply(email_conversation_id, deal["counterparty"],
                #              "Thanks for the discussion, but we won't be moving forward at this price.")
            msg_id = get_msg_id_from_file()
            client.reply(msg_id, "Thanks for the discussion, but we won't be moving forward at this price.")
            # client.send_message(email_conversation_id, "Thanks for the discussion, but we won't be moving forward at this price.")
            message.reply(f"Thanks for the discussion, but we won't be moving forward at this price./nDeal {deal_id} closed as walked away.")

        else:
            # Free-text instruction, e.g. "counter at 4200" or "tell them we need net-30 terms"
            deal_store.log_turn(deal_id, "human", "resolve", text=f"Human instruction: {text}")
            deal_store.set_status(deal_id, "negotiating")
            decision = brain.decide(deal, f"[INSTRUCTION FROM YOUR PRINCIPAL, follow it]: {text}")
            _apply_agent_decision(deal_id, deal, decision)
            message.reply(f"On it — sent to {deal['counterparty']}.")
        return

    # ---------------------------------------------------------------
    # CASE 2: Email from a counterparty — new or ongoing negotiation
    # ---------------------------------------------------------------
    deals = deal_store.load_deals()
    deal_id, deal = deal_store.find_deal_by_thread(deals, thread_key)

    if deal is None:
        # New deal — create a record for it

        item_details = extract_deal_details(text)
        # item = extract_item_and_price(text)
        deal_id, deal = deal_store.create_deal(
            thread_key=thread_key,
            counterparty=getattr(message, "sender", "unknown"),
            ceiling=CEILING_PRICE,
            target=TARGET_PRICE,
            item=item_details["item"],
            quantity=item_details["quantity"],
            price=item_details["price"],
            currency=item_details["currency"],
            delivery_terms=item_details["delivery_terms"],
            payment_terms=item_details["payment_terms"],
            requested_changes=item_details["requested_changes"],
            intent=item_details["intent"],
            urgency=item_details["urgency"],
            risk_flags=item_details["risk_flags"],
            
        )

    deal_store.log_turn(deal_id, "counterparty", "offer", text=text)
    deal = deal_store.load_deals()[deal_id]  # reload with the turn we just logged

    decision = brain.decide(deal, text)
    _apply_agent_decision(deal_id, deal, decision, reply_via=message)


def _apply_agent_decision(deal_id, deal, decision, reply_via=None):
    action = decision["action"]

    if action == "escalate":

        deal_store.log_turn(deal_id, "agent", "escalate", reasoning=decision["reasoning"])
        deal_store.set_status(deal_id, "escalated")

        owner_convo_id = _load_owner_conversation_id()
        text = (
            f"Deal {deal_id} ({deal['item']}) needs your call.\n\n"
            f"Offer: {deal.get('current_offer')} | Ceiling: {deal['ceiling_price']} | Target: {deal['target_price']}\n"
            f"Why: {decision['reasoning']}\n"
            f"Reply: approve / reject / or free-text instructions."
        )
        if owner_convo_id:
            # client.connect_telegram(bot_token=OWNER_TELEGRAM_ADDRESS)  # reads Telegram bot token from .env
             #logger.info("Escalatign to Human for review")
            # Normal path: push into the conversation you already have with the bot.
            client.send_message(owner_convo_id, text=text)
        else:
            # First run only — you haven't messaged the bot yet, so there's no
            # conversation to push into. Message the bot yourself once and
            # this branch won't trigger again.
             #logger.info("No owner Telegram conversation on file yet. "
                #   "Message your bot once (e.g. send 'hi') so it can capture "
                #   "your conversation_id, then retry.")
            print("No owner Telegram conversation on file yet. "
                  "Message your bot once (e.g. send 'hi') so it can capture "
                  "your conversation_id, then retry.")
        return

    if action == "accept":
         #logger.info("Accepting the offer")
        deal_store.log_turn(deal_id, "agent", "accept", price=deal.get("current_offer"),
                             text=decision["message_to_send"], reasoning=decision["reasoning"])
        deal_store.set_status(deal_id, "accepted")

    elif action == "reject":
         #logger.info("Rejected the deal")
        deal_store.log_turn(deal_id, "agent", "reject", text=decision["message_to_send"],
                             reasoning=decision["reasoning"])
        deal_store.set_status(deal_id, "rejected")

    elif action == "counter":
        #  logger.info("replying with counter offer")
        if decision["counter_price"] <= TARGET_PRICE:
            offer_price = decision["parsed_price"]
        deal_store.log_turn(deal_id, "agent", "counter", price=offer_price,#price=decision["counter_price"],
                             text=decision["message_to_send"], reasoning=decision["reasoning"])

    # Send the email reply
    msg_id = get_msg_id_from_file()
    if reply_via is not None:
        reply_via.reply(msg_id,decision["message_to_send"])
        owner_convo_id = _load_owner_conversation_id()
        if owner_convo_id:
            text = (
                        f"Deal {deal_id} ({deal['item']}).\n\n"
                        f"Offer: {deal.get('current_offer')} | Ceiling: {deal['ceiling_price']} | Target: {deal['target_price']}\n"
                        f"Why: {decision['reasoning']}\n"
                        f"replied to counter party : {decision['message_to_send']}\n"
                        f"Reasoning of LLM: {decision["reasoning"]}"
                    )
            # Normal path: push into the conversation you already have with the bot.
            client.send_message(owner_convo_id, text=text)


        
    else:
        # client.initiate(deal["thread_key"], deal["counterparty"], decision["message_to_send"])
        
        client.reply(msg_id, decision["message_to_send"])


if __name__ == "__main__":
    print("Negotiation agent listening on all connected channels...")
    client.listen()