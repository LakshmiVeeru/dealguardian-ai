# DealGuardian AI

## Procurement Negotiation Agent

A procurement negotiation agent. Emails vendors, negotiates within a price ceiling you set, and escalates to you on Telegram when it needs a human call.Buys things on your behalf. One Caspian handler, both channels.



# How it works, in one loop

```
Email arrives from seller
        │
        ▼
  Is this a new deal or an ongoing one?  ──►  deals.json
        │
        ▼
  brain.decide() — one LLM call, returns:
    counter / accept / reject / escalate
        │
   ┌────┴─────┐
   ▼          ▼(escalate)
 reply       ping you on Telegram,
 by email    wait for "approve" / "reject" / free-text instruction
             │
             ▼
        your reply resumes the deal, agent emails the counterparty
```

# Folder structure
```
dealguardian-ai/
│
├── README.md            ← you are here
├── requirements.txt      ← pip dependencies
├── .env.example           ← template for secrets — copy to .env, fill in, never commit .env
├── .gitignore
├── dashboard.py           ← Streamlit UI — reads deals.json directly, runs as its own process
│
└── app/
    ├── __init__.py       ← empty, just marks app/ as a Python package
    ├── config.py         ← every setting and credential, in one place
    ├── deal_store.py     ← reads/writes deals.json + deals_summary.csv
    ├── brain.py           ← the one LLM call that decides what to do next
    ├── helper.py          ← small file-based utility (email message_id lookup)
    └── agent.py            ← the Caspian handler — entry point, ties everything together
    |__ extractor.py      ← deals extracting from the email
```

Generated at runtime, in the project root (not inside app/, and not committed — see .gitignore):

deals.json — full negotiation history, one entry per deal
deals_summary.csv — one row per deal, for quick side-by-side comparison
owner_telegram_convo.txt — your Telegram conversation_id, captured on first message
email_conversation_id.txt — the most recent inbound email's message_id
What each file is for, and why it's separated out this way

# app/config.py :
- every number, model name, and credential the agent uses. It's just settings. Keeping this separate means you can retune the negotiation (raise the ceiling, swap the model, change escalation sensitivity) without touching logic anywhere else. It also calls load_dotenv() once, so every other file automatically gets your .env values without needing to load it themselves.

# app/deal_store.py :
- the only file that touches deals.json and deals_summary.csv. Every other file asks this file to read or write deal state; nothing else opens those files directly. That's deliberate: if you ever change how deals are stored (e.g. move to a real database later), this is the only file you'd need to touch.

# app/brain.py :
- the only file that calls Groq. One function, decide(): given a deal and an incoming message, it returns a structured decision (counter/accept/reject/escalate). It also enforces the hard safety rules (never exceed CEILING_PRICE, escalate on low confidence or too many rounds) in plain code — not just prompted — so the agent can't be talked into a bad price even if the model itself gets it wrong.

# app/helper.py :
- a small utility for looking up the last inbound email's message_id from disk. Split out because it's infrastructure plumbing, not negotiation logic — keeping it separate makes agent.py easier to read.

# app/agent.py :
- the entry point. Registers handle() as the single Caspian message handler for both email and Telegram, and contains all the routing logic: email from a vendor moves a deal forward, Telegram from you resolves an escalation. This is the file which uses "one CASPIAN handler, two channels" rule is about - everything else exists to support this file, not duplicate it.

# dashboard.py :
- a Streamlit viewer for deals.json. It's completely decoupled from agent.py: it just reads whatever's currently on disk and displays it, so you run it as a separate process, in a separate terminal, alongside the agent. Neither file imports the other.

### Setup
bash
cd dealguardian-ai
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env          # then fill in real values in .env
Running

From the project root (not from inside app/):

bash
python -m app.agent

Running it as -m app.agent (rather than python app/agent.py directly) 
