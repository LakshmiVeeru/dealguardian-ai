"""
All the knobs live here. Nothing clever — just numbers and thresholds
so you can tune the agent's behavior without touching the logic.
"""
import os

from dotenv import load_dotenv
load_dotenv()
# ---------------------------------------------------------------------------
# NEGOTIATION POLICY (you are the BUYER — you set a ceiling, not a floor)
# ---------------------------------------------------------------------------
CEILING_PRICE  = float(os.getenv("CEILING_PRICE", "5000"))   # hard max — agent must NEVER agree above this
TARGET_PRICE   = float(os.getenv("TARGET_PRICE", "3800"))    # what a "good deal" looks like
OPENING_OFFER  = float(os.getenv("OPENING_OFFER", "3200"))   # agent's first counter-offer

# ---------------------------------------------------------------------------
# WHEN TO ESCALATE TO YOU (this is the heart of "human judgment required")
# ---------------------------------------------------------------------------
MAX_ROUNDS_BEFORE_ESCALATE = 5     # after N back-and-forths with no deal, ask you
CONFIDENCE_ESCALATE_BELOW  = 0.6   # if the model isn't confident (0-1), ask you
NEAR_CEILING_FRACTION      = 0.9   # if counterparty's ask is >= 90% of ceiling, ask you

# ---------------------------------------------------------------------------
# HUGGING FACE (the "brain")
# ---------------------------------------------------------------------------
# HF_API_KEY    = os.environ["HF_Read_Token"]
# HF_MODEL      = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
# HF Inference Providers expose an OpenAI-compatible chat endpoint.
# Double check this matches what your HF account/model actually supports
# before the demo — this is the one part most likely to need a tweak.
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

# ---------------------------------------------------------------------------
# FILES
# ---------------------------------------------------------------------------
DEALS_FILE   = "deals.json"          # full history, source of truth
SUMMARY_FILE = "deals_summary.csv"   # one row per deal, for quick comparison

# ---------------------------------------------------------------------------
# ESCALATION TARGET — where the agent pings YOU
# ---------------------------------------------------------------------------
# This should be whatever address/handle Caspian uses to reach you on Telegram
# (the identity you connected with `caspian connect telegram`).
OWNER_TELEGRAM_ADDRESS = os.environ["telegram_bot_token"]
CASPIAN_BASE_URL = os.environ["CASPIAN_BASE_URL"]
CASPIAN_API_KEY = os.environ["CASPIAN_API_KEY"]

# ---------------------------------------------------------------------------
# GROQ (the "brain")
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
# Plain instruct model, not a reasoning model — gpt-oss-120b works but Groq
# has an open bug where reasoning tokens sometimes leak into `content` even
# with reasoning hidden. This avoids that class of bug entirely.
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
 