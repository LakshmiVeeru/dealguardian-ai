import json
import os
from datetime import datetime

import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DEALS_FILE = "deals.json"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="DealGuardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #f7f8fa;
    }

    /* Remove excessive top padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* Header */
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6b7280;
        margin-top: 0.2rem;
        margin-bottom: 1.5rem;
    }

    /* Cards */
    .metric-card {
        background: white;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }

    .metric-label {
        font-size: 0.85rem;
        color: #6b7280;
    }

    .metric-value {
        font-size: 1.7rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    /* Deal card */
    .deal-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        margin-bottom: 0.6rem;
    }

    /* Timeline */
    .timeline-card {
        background: white;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        margin-bottom: 0.8rem;
    }

    .timeline-header {
        font-weight: 700;
        font-size: 1rem;
    }

    .timeline-meta {
        color: #6b7280;
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }

    .timeline-text {
        white-space: pre-wrap;
        line-height: 1.5;
    }

    .reasoning {
        background: #f8fafc;
        border-left: 4px solid #64748b;
        padding: 0.7rem;
        margin-top: 0.6rem;
        border-radius: 4px;
        color: #475569;
    }

    /* Status */
    .status {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .status-negotiating {
        background: #fef3c7;
        color: #92400e;
    }

    .status-accepted {
        background: #dcfce7;
        color: #166534;
    }

    .status-rejected {
        background: #fee2e2;
        color: #991b1b;
    }

    .status-escalated {
        background: #ffedd5;
        color: #9a3412;
    }

    .status-walked {
        background: #f3f4f6;
        color: #374151;
    }

    /* Divider */
    .section-divider {
        margin-top: 1rem;
        margin-bottom: 1rem;
        border-top: 1px solid #e5e7eb;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA FUNCTIONS
# ============================================================

def load_deals():
    """Load deals from deals.json."""

    if not os.path.exists(DEALS_FILE):
        return {}

    try:
        with open(DEALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except json.JSONDecodeError:
        st.error("deals.json contains invalid JSON.")
        return {}

    except Exception as e:
        st.error(f"Unable to load deals.json: {e}")
        return {}


def format_money(value, currency="USD"):
    """Format a numeric amount safely."""

    if value is None or value == "":
        return "—"

    try:
        return f"{currency} {float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def format_timestamp(timestamp):
    """Format ISO timestamp for display."""

    if not timestamp:
        return "Unknown time"

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y • %I:%M %p")
    except Exception:
        return str(timestamp)


def status_label(status):
    """Return readable status label."""

    labels = {
        "negotiating": "🟡 Negotiating",
        "accepted": "🟢 Accepted",
        "rejected": "🔴 Rejected",
        "escalated": "🚨 Escalated",
        "walked_away": "⚫ Walked Away",
    }

    return labels.get(status, status.title() if status else "Unknown")


def status_class(status):
    """Return CSS class for status."""

    return {
        "negotiating": "status-negotiating",
        "accepted": "status-accepted",
        "rejected": "status-rejected",
        "escalated": "status-escalated",
        "walked_away": "status-walked",
    }.get(status, "status-negotiating")


def action_icon(action):
    """Return icon for history action."""

    icons = {
        "offer": "📩",
        "counter": "🤖",
        "accept": "✅",
        "reject": "❌",
        "escalate": "🚨",
        "resolve": "👤",
    }

    return icons.get(action, "🔹")


def action_title(who, action):
    """Generate readable history title."""

    if who == "counterparty":
        if action == "offer":
            return "Counterparty Message"

        return f"Counterparty — {action.title()}"

    if who == "agent":
        return f"AI Agent — {action.title()}"

    if who == "human":
        return f"Owner — {action.title()}"

    return f"{who.title()} — {action.title()}"


# ============================================================
# SESSION STATE
# ============================================================

if "selected_deal_id" not in st.session_state:
    st.session_state.selected_deal_id = None


# ============================================================
# LOAD DATA
# ============================================================

deals = load_deals()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🛡️ DealGuardian")

    st.caption("AI Procurement Negotiation Agent")

    st.divider()

    st.markdown("### Controls")

    if st.button(
        "🔄 Refresh",
        use_container_width=True,
    ):
        st.rerun()

    st.divider()

    st.markdown("### Filter Deals")

    filter_status = st.selectbox(
        "Status",
        [
            "All",
            "Negotiating",
            "Escalated",
            "Accepted",
            "Rejected",
            "Walked Away",
        ],
    )


# ============================================================
# FILTER DEALS
# ============================================================

status_mapping = {
    "Negotiating": "negotiating",
    "Escalated": "escalated",
    "Accepted": "accepted",
    "Rejected": "rejected",
    "Walked Away": "walked_away",
}

if filter_status == "All":
    filtered_deals = deals
else:
    selected_status = status_mapping[filter_status]

    filtered_deals = {
        deal_id: deal
        for deal_id, deal in deals.items()
        if deal.get("status") == selected_status
    }


# ============================================================
# HEADER
# ============================================================

# st.markdown(
#     '<div class="main-title">🛡️ DealGuardian</div>',
#     unsafe_allow_html=True,
# )
st.title("🛡️ DealGuardian")
st.markdown(
    '<div class="subtitle">'
    "<h2> AI-powered procurement negotiation monitoring dashboard"
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# METRICS
# ============================================================

all_deals = list(deals.values())

total_deals = len(all_deals)

negotiating_count = sum(
    1 for deal in all_deals
    if deal.get("status") == "negotiating"
)

escalated_count = sum(
    1 for deal in all_deals
    if deal.get("status") == "escalated"
)

accepted_count = sum(
    1 for deal in all_deals
    if deal.get("status") == "accepted"
)

rejected_count = sum(
    1 for deal in all_deals
    if deal.get("status") == "rejected"
)


metric_cols = st.columns(5)

with metric_cols[0]:
    st.metric("Total Deals", total_deals)

with metric_cols[1]:
    st.metric("🟡 Negotiating", negotiating_count)

with metric_cols[2]:
    st.metric("🚨 Escalated", escalated_count)

with metric_cols[3]:
    st.metric("🟢 Accepted", accepted_count)

with metric_cols[4]:
    st.metric("🔴 Rejected", rejected_count)


# st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ============================================================
# NO DEALS
# ============================================================

if not deals:

    st.info(
        "No deals found yet. Send an email to  Caspian-connected agent \n"
        "negotiation details and the deal will appear here."
    )

    st.stop()


# ============================================================
# MAIN LAYOUT
# ============================================================

left_col, right_col = st.columns([1, 2.5])


# ============================================================
# DEAL LIST
# ============================================================

with left_col:

    st.markdown("### Deals")

    if not filtered_deals:

        st.info("No deals match the selected filter.")

    else:

        # Sort by most recently updated
        sorted_deals = sorted(
            filtered_deals.items(),
            key=lambda x: x[1].get("updated_at", ""),
            reverse=True,
        )

        for deal_id, deal in sorted_deals:

            status = deal.get("status", "negotiating")

            item = deal.get("item") or "Unnamed Deal"

            current_offer = deal.get("current_offer")

            currency = deal.get("currency") or "USD"

            # Use Streamlit button as deal selector
            button_label = (
                f"{status_label(status)}\n"
                f"{item}\n"
                f"{format_money(current_offer, currency)}"
            )

            if st.button(
                button_label,
                key=f"deal_{deal_id}",
                use_container_width=True,
            ):
                st.session_state.selected_deal_id = deal_id
                st.rerun()


# ============================================================
# SELECT DEAL
# ============================================================

if st.session_state.selected_deal_id:

    selected_id = st.session_state.selected_deal_id

    if selected_id in deals:
        selected_deal = deals[selected_id]
    else:
        selected_deal = None

else:

    # Automatically select most recent deal
    sorted_all = sorted(
        deals.items(),
        key=lambda x: x[1].get("updated_at", ""),
        reverse=True,
    )

    if sorted_all:
        selected_id, selected_deal = sorted_all[0]
        st.session_state.selected_deal_id = selected_id
    else:
        selected_id = None
        selected_deal = None


# ============================================================
# DEAL DETAILS
# ============================================================

with right_col:

    if selected_deal is None:

        st.info("Select a deal to view details.")

    else:

        deal = selected_deal

        deal_id = deal.get("deal_id", selected_id)

        item = deal.get("item") or "Unnamed Item"

        status = deal.get("status", "negotiating")

        currency = deal.get("currency") or "USD"

        counterparty = deal.get(
            "counterparty",
            "Unknown",
        )

        # ----------------------------------------------------
        # DEAL HEADER
        # ----------------------------------------------------

        header_col1, header_col2 = st.columns([3, 1])

        with header_col1:

            st.markdown(
                f"## {item}"
            )

            st.caption(
                f"Deal ID: `{deal_id}`"
            )

        with header_col2:

            st.markdown(
                f'<div style="text-align:right;">'
                f'<span class="status {status_class(status)}">'
                f'{status_label(status)}'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


        # ----------------------------------------------------
        # BASIC INFORMATION
        # ----------------------------------------------------

        st.markdown("### Deal Information")

        info1, info2, info3, info4 = st.columns(4)

        with info1:

            st.markdown("**Counterparty**")

            st.write(counterparty)

        with info2:

            st.markdown("**Quantity**")

            st.write(
                deal.get("quantity")
                if deal.get("quantity") is not None
                else "—"
            )

        with info3:

            st.markdown("**Current Offer**")

            st.write(
                format_money(
                    deal.get("current_offer"),
                    currency,
                )
            )

        with info4:

            st.markdown("**Rounds**")

            st.write(
                deal.get("rounds", 0)
            )


        st.markdown("<div class='section-divider'></div>",
                    unsafe_allow_html=True)


        # ----------------------------------------------------
        # PRICING
        # ----------------------------------------------------

        st.markdown("### 💰 Negotiation Position")

        price1, price2, price3 = st.columns(3)

        with price1:

            st.metric(
                "Target Price",
                format_money(
                    deal.get("target_price"),
                    currency,
                ),
            )

        with price2:

            st.metric(
                "Ceiling Price",
                format_money(
                    deal.get("ceiling_price"),
                    currency,
                ),
            )

        with price3:

            current_offer = deal.get("current_offer")

            if (
                current_offer is not None
                and deal.get("ceiling_price") is not None
            ):

                try:

                    remaining = (
                        float(deal["ceiling_price"])
                        - float(current_offer)
                    )

                    st.metric(
                        "Room to Ceiling",
                        format_money(
                            remaining,
                            currency,
                        ),
                    )

                except Exception:

                    st.metric(
                        "Room to Ceiling",
                        "—",
                    )

            else:

                st.metric(
                    "Room to Ceiling",
                    "—",
                )


        # ----------------------------------------------------
        # EXTRACTED DEAL INFORMATION
        # ----------------------------------------------------

        st.markdown("###  Extracted Deal Information")

        extract1, extract2 = st.columns(2)

        with extract1:

            st.markdown("**Item**")
            st.write(deal.get("item") or "—")

            st.markdown("**Quantity**")
            st.write(deal.get("quantity") or "—")

            st.markdown("**Currency**")
            st.write(deal.get("currency") or "—")

        with extract2:

            st.markdown("**Payment Terms**")
            st.write(deal.get("payment_terms") or "—")

            st.markdown("**Delivery Terms**")
            st.write(deal.get("delivery_terms") or "—")

            st.markdown("**Intent**")
            st.write(deal.get("intent") or "—")


        # ----------------------------------------------------
        # RISK FLAGS
        # ----------------------------------------------------

        risk_flags = deal.get("risk_flags", [])

        if risk_flags:

            st.markdown("### ⚠️ Risk Flags")

            if isinstance(risk_flags, list):

                for risk in risk_flags:
                    st.warning(str(risk))

            else:

                st.warning(str(risk_flags))


        # ----------------------------------------------------
        # REQUESTED CHANGES
        # ----------------------------------------------------

        requested_changes = deal.get(
            "requested_changes",
            [],
        )

        if requested_changes:

            st.markdown("### 📌 Requested Changes")

            if isinstance(requested_changes, list):

                for change in requested_changes:
                    st.write(f"• {change}")

            else:

                st.write(requested_changes)


        # ----------------------------------------------------
        # NEGOTIATION TIMELINE
        # ----------------------------------------------------

        st.markdown("###  Negotiation Timeline")

        history = deal.get("history", [])

        if not history:

            st.info(
                "No negotiation history recorded yet."
            )

        else:

            # Show oldest → newest
            history = list(history)

            for index, event in enumerate(history):

                who = event.get(
                    "who",
                    "unknown",
                )

                action = event.get(
                    "action",
                    "unknown",
                )

                text = event.get(
                    "text",
                    "",
                )

                reasoning = event.get(
                    "reasoning",
                    "",
                )

                price = event.get(
                    "price"
                )

                timestamp = event.get(
                    "timestamp"
                )

                icon = action_icon(action)

                title = action_title(
                    who,
                    action,
                )

                
                st.markdown(f'<div class="timeline-header">{icon} {title}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="timeline-meta">{format_timestamp(timestamp)}</div>', unsafe_allow_html=True)

                # Price
                if price is not None:

                    st.markdown(
                        f"**Price:** "
                        f"{format_money(price, currency)}"
                    )

                # Main text
                if text:

                    st.markdown(
                        f"""
                        <div class="timeline-text">
                        {text}
                        
                        """,
                        unsafe_allow_html=True,
                    )

                # AI reasoning
                if reasoning:

                    st.markdown(
                        f"""
                        <div class="reasoning">
                        <strong>AI Reasoning:</strong><br>
                        {reasoning}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # st.markdown(
                #     "<br>",
                #     unsafe_allow_html=True,
                # )
                # st.divider()

        # ----------------------------------------------------
        # DEAL METADATA
        # ----------------------------------------------------

        st.markdown("### 🕒 Deal Metadata")

        meta1, meta2 = st.columns(2)

        with meta1:

            st.markdown("**Created**")

            st.write(
                format_timestamp(
                    deal.get("created_at")
                )
            )

        with meta2:

            st.markdown("**Last Updated**")

            st.write(
                format_timestamp(
                    deal.get("updated_at")
                )
            )


# ============================================================
# FOOTER
# ============================================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.caption(
    "🛡️ DealGuardian • AI Procurement Negotiation Agent"
)