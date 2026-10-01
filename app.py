"""ABC Bank – Relationship Manager AI Assistant (Streamlit UI).

Run:  streamlit run app.py
"""
from __future__ import annotations

import html
import json
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from agents.llm import ollama_up
from db import repository
from db.connection import ping as pg_up
from graph.workflow import process_email
from observability.tracing import phoenix_trace_url, phoenix_up

st.set_page_config(page_title="ABC Bank · RM Assistant", page_icon="🏦", layout="wide")

AGENT_LABELS = {
    "intent_identification_agent": ("🧠", "Intent Identification"),
    "authentication_agent": ("🔐", "Authentication"),
    "product_information_agent": ("📚", "Product Information"),
    "core_banking_agent": ("🏦", "Core Banking"),
    "email_drafting_agent": ("✍️", "Email Drafting"),
}
STATUS_STYLE = {
    "NEW": ("New", "#1565C0", "#E3F2FD"),
    "PENDING_REVIEW": ("Pending review", "#B26A00", "#FFF4E0"),
    "APPROVED": ("Approved", "#1B7F3B", "#E6F4EA"),
    "REJECTED": ("Rejected", "#B3261E", "#FDECEA"),
}
PRIORITY_COLOR = {"HIGH": "#B3261E", "NORMAL": "#5A6475", "LOW": "#8A94A6"}

# ---------------------------------------------------------------- styles
st.markdown("""
<style>
  .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px;}
  [data-testid="stSidebar"] {background: #0B1F44;}
  [data-testid="stSidebar"] * {color: #E8ECF5;}
  [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
  [data-testid="stSidebar"] [data-baseweb="select"] * {color: #1B2437 !important;}
  [data-testid="stSidebar"] button p {color: #1B2437 !important;}
  .app-header {background: linear-gradient(100deg, #0B1F44 0%, #0B3D91 70%, #1456C8 100%);
      border-radius: 14px; padding: 18px 26px; color: #fff; display: flex;
      justify-content: space-between; align-items: center; margin-bottom: 18px;
      box-shadow: 0 6px 18px rgba(11,31,68,.18);}
  .app-header h1 {font-size: 1.55rem; margin: 0; color: #fff; font-weight: 700;}
  .app-header .sub {color: #C9D6F2; font-size: .9rem; margin-top: 2px;}
  .app-header .gold {color: #E3B341;}
  .app-header .right {text-align: right; font-size: .85rem; color: #C9D6F2;}
  .kpi {background: #fff; border-radius: 12px; padding: 14px 18px; border: 1px solid #E3E8F1;
      box-shadow: 0 1px 3px rgba(16,24,40,.05);}
  .kpi .label {color: #5A6475; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em;}
  .kpi .value {font-size: 1.7rem; font-weight: 700; color: #0B1F44; line-height: 1.2;}
  .kpi .hint {font-size: .75rem; color: #8A94A6;}
  .badge {display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: .72rem;
      font-weight: 600; white-space: nowrap;}
  .mail-meta {color: #5A6475; font-size: .85rem;}
  .mail-subject {font-size: 1.15rem; font-weight: 700; color: #0B1F44; margin: 4px 0 6px;}
  .mail-body {background: #F8FAFD; border: 1px solid #E3E8F1; border-radius: 10px; padding: 14px 16px;
      white-space: pre-wrap; font-size: .92rem; color: #1B2437;}
  .pipeline {display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin: 6px 0 12px;}
  .step {padding: 8px 12px; border-radius: 10px; font-size: .8rem; font-weight: 600; border: 1px solid;}
  .step.done {background: #E6F4EA; color: #1B7F3B; border-color: #B7DFC3;}
  .step.fail {background: #FDECEA; color: #B3261E; border-color: #F3C2BE;}
  .step.skip {background: #F1F3F7; color: #9AA3B2; border-color: #E3E8F1; text-decoration: line-through;}
  .arrow {color: #9AA3B2; font-weight: 700;}
  .notes {background: #FFF8E6; border-left: 4px solid #E3B341; padding: 10px 14px; border-radius: 6px;
      font-size: .87rem; white-space: pre-wrap;}
  .section-title {font-weight: 700; color: #0B1F44; font-size: 1rem; margin: 4px 0 8px;}
  .health {font-size: .85rem; margin: 2px 0;}
  .rm-card {background: rgba(255,255,255,.06); border-radius: 10px; padding: 12px 14px; margin-bottom: 8px;}
  div[data-testid="stButton"] button[kind="secondary"] {text-align: left;}
</style>
""", unsafe_allow_html=True)


def badge(text: str, fg: str, bg: str) -> str:
    return f'<span class="badge" style="color:{fg};background:{bg}">{html.escape(text)}</span>'


def status_badge(status: str) -> str:
    label, fg, bg = STATUS_STYLE.get(status, (status, "#5A6475", "#F1F3F7"))
    return badge(label, fg, bg)


def intent_badge(intent: str | None) -> str:
    if intent == "account":
        return badge("Account", "#6A1B9A", "#F3E5F5")
    if intent == "non_account":
        return badge("Non-account", "#00695C", "#E0F2F1")
    return ""


def fmt_time(ts: str | None) -> str:
    if not ts:
        return ""
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%d %b, %H:%M")


@st.cache_data(ttl=20, show_spinner=False)
def health() -> dict:
    return {"PostgreSQL": pg_up(), f"Ollama · {config.OLLAMA_MODEL}": ollama_up(), "Arize Phoenix": phoenix_up()}


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"""<div class="rm-card"><div style="font-size:.75rem;opacity:.7">RELATIONSHIP MANAGER</div>
        <div style="font-size:1.05rem;font-weight:700">{config.RM_NAME}</div>
        <div style="font-size:.8rem;opacity:.8">{config.RM_TITLE} · Mumbai Wealth Desk</div></div>""",
                unsafe_allow_html=True)

    st.markdown("**System health**")
    for name, ok in health().items():
        st.markdown(f'<div class="health">{"🟢" if ok else "🔴"} {name}</div>', unsafe_allow_html=True)
    st.link_button("Open Phoenix traces ↗", phoenix_trace_url(None), width="stretch")

    st.divider()
    st.markdown("**Inbox filter**")
    status_filter = st.selectbox("Status", ["All", "NEW", "PENDING_REVIEW", "APPROVED", "REJECTED"], key="status_filter",
                                 format_func=lambda s: STATUS_STYLE.get(s, ("All",))[0],
                                 label_visibility="collapsed")

    st.divider()
    with st.expander("✉️ Simulate incoming email"):
        with st.form("new_email", clear_on_submit=True):
            from_name = st.text_input("Sender name", "Rahul Mehta", key="sim_name")
            from_email = st.text_input("Sender email", "rahul.mehta@example.com", key="sim_email",
                                       help="Use a registered customer email (e.g. meera.joshi@example.com) "
                                            "for account queries.")
            subject = st.text_input("Subject", "Credit card outstanding", key="sim_subject")
            body = st.text_area("Body", key="sim_body", value="Hi Priya,\n\nWhat is my credit card outstanding and due date?\n\nRahul",
                                height=130)
            priority = st.selectbox("Priority", ["NORMAL", "HIGH", "LOW"], key="sim_priority")
            if st.form_submit_button("Send to RM inbox", width="stretch", key="sim_submit"):
                new_id = repository.add_email(from_email, from_name, subject, body, priority)
                st.session_state.selected_email = new_id
                st.toast(f"New email #{new_id} received", icon="📨")
                st.rerun()

# ---------------------------------------------------------------- header + KPIs
st.markdown(f"""
<div class="app-header">
  <div><h1>🏦 {config.BANK_NAME} <span class="gold">·</span> RM Assistant</h1>
       <div class="sub">Agentic AI for customer query resolution — intent · authentication · data retrieval · drafting</div></div>
  <div class="right">{datetime.now().strftime('%A, %d %B %Y')}<br/>Powered by LangGraph · Ollama · Phoenix</div>
</div>""", unsafe_allow_html=True)

k = repository.kpis()
kpi_cols = st.columns(5)
kpi_data = [
    ("New queries", k["new"], "Awaiting AI processing"),
    ("Pending review", k["pending_review"], "Drafts ready for you"),
    ("Approved", k["approved"], f"{k['edited']} with edits"),
    ("Rejected", k["rejected"], "Sent back / re-process"),
    ("Avg. turnaround", f"{k['avg_secs'] or 0}s", "vs ~2 hrs manual"),
]
for col, (label, value, hint) in zip(kpi_cols, kpi_data):
    col.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>'
                 f'<div class="hint">{hint}</div></div>', unsafe_allow_html=True)
st.write("")

tab_inbox, tab_history = st.tabs(["📥  Inbox", "📊  Activity history"])


# ---------------------------------------------------------------- inbox
def render_pipeline(trace: list[dict], intent: str | None) -> None:
    ran = {t["agent"]: t for t in trace}
    path = ["intent_identification_agent"]
    path += (["authentication_agent", "core_banking_agent"] if intent == "account"
             else ["product_information_agent"])
    path.append("email_drafting_agent")
    parts = []
    for agent in path:
        icon, label = AGENT_LABELS[agent]
        t = ran.get(agent)
        cls = "skip" if not t else ("fail" if t["status"] == "failed" else "done")
        mark = "✓" if cls == "done" else ("✕" if cls == "fail" else "–")
        ms = f" · {t['duration_ms'] / 1000:.1f}s" if t else ""
        parts.append(f'<span class="step {cls}">{icon} {label} {mark}{ms}</span>')
    st.markdown('<div class="pipeline">' + '<span class="arrow">→</span>'.join(parts) + "</div>",
                unsafe_allow_html=True)


def run_agents(email_id: int) -> None:
    with st.status("Running AI agents…", expanded=True) as status:
        def on_step(node: str, delta: dict) -> None:
            icon, label = AGENT_LABELS.get(node, ("•", node))
            for t in delta.get("agent_trace", []):
                st.write(f"{icon} **{label}** — {t['summary']}  _({t['duration_ms'] / 1000:.1f}s)_")
            status.update(label=f"{label} complete…")

        st.write("📨 Email received — handing over to Intent Identification Agent")
        try:
            result = process_email(email_id, on_step=on_step)
            status.update(label=f"Draft ready in {result['processing_ms'] / 1000:.1f}s", state="complete",
                          expanded=False)
        except Exception as exc:
            status.update(label="Agent pipeline failed", state="error")
            st.exception(exc)
            st.stop()
    st.rerun()


def render_response(email: dict, resp: dict) -> None:
    trace = resp["agent_trace"] or []
    render_pipeline(trace, resp["intent"])

    m = st.columns(5)
    m[0].metric("Intent", (resp["intent"] or "-").replace("_", "-").title())
    m[1].metric("Sub-intent", (resp["sub_intent"] or "-").replace("_", " ").title())
    m[2].metric("Confidence", f"{float(resp['confidence'] or 0):.0%}")
    m[3].metric("Authentication", resp["auth_status"] or "N/A")
    m[4].metric("Processing time", f"{(resp['processing_ms'] or 0) / 1000:.1f}s")

    t_draft, t_data, t_trace = st.tabs(["✉️ Draft reply", "🗄️ Retrieved data", "🧭 Agent trace"])

    with t_draft:
        rid = resp["response_id"]
        actioned = resp["rm_action"] is not None
        if resp.get("internal_notes"):
            st.markdown(f'<div class="notes"><b>🔒 Internal notes for RM</b> (not sent to customer)\n'
                        f'{html.escape(resp["internal_notes"])}</div>', unsafe_allow_html=True)
            st.write("")
        st.markdown(f'<div class="mail-meta">To: {html.escape(email["from_name"] or "")} '
                    f'&lt;{html.escape(email["from_email"])}&gt;</div>', unsafe_allow_html=True)

        if actioned:
            action = resp["rm_action"]
            color = {"ACCEPTED": "success", "ACCEPTED_WITH_EDITS": "success", "REJECTED": "error"}[action]
            getattr(st, color)(f"**{action.replace('_', ' ').title()}** by {config.RM_NAME} on "
                               f"{fmt_time(resp['actioned_at'])}"
                               + (f" — _{resp['rm_comment']}_" if resp.get("rm_comment") else ""))
            st.text_input("Subject", resp["final_subject"] or resp["draft_subject"], disabled=True,
                          key=f"fs_{rid}")
            st.text_area("Email body", resp["final_body"] or resp["draft_body"], height=380, disabled=True,
                         key=f"fb_{rid}")
            if action == "ACCEPTED_WITH_EDITS":
                with st.expander("View original AI draft"):
                    st.text(resp["draft_body"])
            if st.button("🔄 Re-process with AI", key=f"re_{rid}"):
                run_agents(email["email_id"])
            return

        subj = st.text_input("Subject", resp["draft_subject"], key=f"subj_{rid}")
        body = st.text_area("Email body (editable)", resp["draft_body"], height=380, key=f"body_{rid}")
        edited = subj.strip() != (resp["draft_subject"] or "").strip() or body.strip() != resp["draft_body"].strip()
        if edited:
            st.caption("✏️ You have edited the draft — use **Accept with edits** to send your version.")

        comment = st.text_input("Comment (required to reject)", key=f"cm_{rid}",
                                placeholder="e.g. Incorrect product suggested; needs branch confirmation")
        c1, c2, c3, _ = st.columns([1, 1.2, 1, 2])
        if c1.button("✅ Accept", type="primary", width="stretch", key=f"acc_{rid}",
                     disabled=edited, help="Send the AI draft as-is"):
            repository.record_action(rid, "ACCEPTED", resp["draft_subject"], resp["draft_body"], comment or None)
            st.toast("Reply approved and queued for sending", icon="✅")
            st.rerun()
        if c2.button("✏️ Accept with edits", width="stretch", key=f"edit_{rid}", disabled=not edited):
            repository.record_action(rid, "ACCEPTED_WITH_EDITS", subj, body, comment or None)
            st.toast("Edited reply approved and queued for sending", icon="✏️")
            st.rerun()
        if c3.button("❌ Reject", width="stretch", key=f"rej_{rid}"):
            if not comment.strip():
                st.warning("Please add a comment explaining the rejection.")
            else:
                repository.record_action(rid, "REJECTED", None, None, comment)
                st.toast("Draft rejected", icon="❌")
                st.rerun()

    with t_data:
        data = resp["retrieved_data"] or {}
        source = {"core_banking": "Core Banking System (PostgreSQL)",
                  "product_information": "Product Information Database (PostgreSQL)"}.get(resp["data_source"],
                                                                                            "No data retrieved")
        st.caption(f"Source: **{source}**" + (f" · Customer ID **{resp['customer_id']}**" if resp["customer_id"] else ""))
        if not data:
            st.info("No data was retrieved for this query.")
        for name, rows in data.items():
            st.markdown(f'<div class="section-title">{name.replace("_", " ").title()}</div>',
                        unsafe_allow_html=True)
            if rows:
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            else:
                st.caption("No records.")

    with t_trace:
        st.link_button("🔭 Open this trace in Arize Phoenix", phoenix_trace_url(resp["trace_id"]))
        st.caption(f"Trace ID: `{resp['trace_id']}`")
        for step in trace:
            icon, label = AGENT_LABELS.get(step["agent"], ("•", step["agent"]))
            with st.expander(f"{icon} {label} — {step['summary']} ({step['duration_ms']} ms)"):
                st.json(step["output"])


with tab_inbox:
    emails = repository.list_emails(None if status_filter == "All" else status_filter)
    left, right = st.columns([1, 2.1], gap="large")

    with left:
        st.markdown(f'<div class="section-title">Customer emails ({len(emails)})</div>', unsafe_allow_html=True)
        if "selected_email" not in st.session_state and emails:
            st.session_state.selected_email = emails[0]["email_id"]
        with st.container(height=720, border=False):
            for e in emails:
                selected = st.session_state.get("selected_email") == e["email_id"]
                with st.container(border=True):
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;gap:6px">'
                        f'<b style="color:#0B1F44">{html.escape(e["from_name"] or e["from_email"])}</b>'
                        f'<span class="mail-meta">{fmt_time(e["received_at"])}</span></div>'
                        f'<div style="font-size:.88rem;margin:2px 0 6px">{html.escape(e["subject"])}</div>'
                        f'{status_badge(e["status"])} {intent_badge(e["intent"])} '
                        f'<span class="badge" style="color:{PRIORITY_COLOR[e["priority"]]};background:#F1F3F7">'
                        f'{e["priority"].title()}</span>',
                        unsafe_allow_html=True)
                    if st.button("Viewing" if selected else "Open", key=f"open_{e['email_id']}",
                                 type="primary" if selected else "secondary", width="stretch"):
                        st.session_state.selected_email = e["email_id"]
                        st.rerun()

    with right:
        email = repository.get_email(st.session_state.get("selected_email") or 0)
        if not email:
            st.info("Select an email from the inbox.")
        else:
            st.markdown(
                f'<div class="mail-meta">From <b>{html.escape(email["from_name"] or "")}</b> '
                f'&lt;{html.escape(email["from_email"])}&gt; · {fmt_time(email["received_at"])} · '
                f'#{email["email_id"]} {status_badge(email["status"])}</div>'
                f'<div class="mail-subject">{html.escape(email["subject"])}</div>'
                f'<div class="mail-body">{html.escape(email["body"])}</div>',
                unsafe_allow_html=True)
            st.write("")

            resp = repository.latest_response(email["email_id"])
            if resp is None:
                st.info("This query has not been processed yet. The AI agents will classify it, authenticate "
                        "the customer if needed, fetch the relevant data and draft a reply for your approval.")
                if st.button("🤖 Process with AI agents", type="primary", key="process_email"):
                    run_agents(email["email_id"])
            else:
                if resp["rm_action"] == "REJECTED" and email["status"] == "REJECTED":
                    st.caption("This draft was rejected. You can re-process the email to generate a fresh draft.")
                render_response(email, resp)

# ---------------------------------------------------------------- history
with tab_history:
    rows = repository.history()
    if not rows:
        st.info("No emails processed yet.")
    else:
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("Drafts generated", len(df))
        c2.metric("Account queries", int((df["intent"] == "account").sum()))
        acted = df["rm_action"].notna().sum()
        accepted = df["rm_action"].isin(["ACCEPTED", "ACCEPTED_WITH_EDITS"]).sum()
        c3.metric("Acceptance rate", f"{accepted / acted:.0%}" if acted else "–")

        df["processing_s"] = (df["processing_ms"] / 1000).round(1)
        df["rm_action"] = df["rm_action"].fillna("PENDING")
        st.dataframe(
            df[["response_id", "email_id", "from_name", "subject", "intent", "sub_intent", "data_source",
                "rm_action", "processing_s", "created_at", "actioned_at", "trace_id"]],
            width="stretch", hide_index=True,
            column_config={"processing_s": st.column_config.NumberColumn("Processing (s)"),
                           "trace_id": st.column_config.TextColumn("Phoenix trace")})
