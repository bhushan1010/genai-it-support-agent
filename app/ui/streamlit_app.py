"""A quiet, session-based workspace for runbook troubleshooting."""
from __future__ import annotations

import os
import re

import httpx
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
STARTERS = [
    ("Wi-Fi & VPN", "Connection failures and remote access.", "My laptop cannot connect to Wi-Fi after a Windows update."),
    ("Account access", "Password resets and locked accounts.", "My account is locked after too many failed login attempts."),
    ("Application errors", "Launch problems and missing files.", "An application says DLL not found when I try to launch it."),
    ("Device performance", "Slow computers, heat and resource usage.", "My computer is running very slowly since this morning."),
]

st.set_page_config(page_title="Support desk", page_icon=":material/support_agent:", layout="wide")
st.markdown("""
<style>
.stApp { background: #f8f9f6; color: #26332c; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stMainBlockContainer"] { max-width: 960px; padding-top: 3.2rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #eef1eb; border-right: 1px solid #dce2d9; }
[data-testid="stSidebar"] > div:first-child { padding-top: 2rem; }
h1 { font-family: Georgia, 'Times New Roman', serif; font-weight: 400 !important; letter-spacing: -.045em; font-size: 2.9rem !important; line-height: 1.16 !important; }
h2 { font-size: 1.3rem !important; font-weight: 550 !important; letter-spacing: -.02em; }
h3 { font-size: 1.08rem !important; font-weight: 600 !important; }
p, li { line-height: 1.65; }
.eyebrow { font-size: .69rem; letter-spacing: .15em; font-weight: 650; color: #6b776d; margin-bottom: .8rem; }
.wordmark { font-size: 1.35rem; font-weight: 650; letter-spacing: -.055em; margin-bottom: .15rem; }
.sidebar-note { color: #647064; font-size: .82rem; line-height: 1.6; }
.status { font-size: .78rem; color: #44654e; padding: .6rem 0; }
.status::before { content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #63816a; margin-right: 8px; vertical-align: middle; }
.status.offline { color: #82603f; }
.status.offline::before { background: #a4865d; }
.session-label { font-size: .69rem; letter-spacing: .12em; color: #738073; margin-top: 2rem; margin-bottom: .6rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 6px !important; border-color: #dce2d9 !important; }
[data-testid="stBaseButton-secondary"] { border-radius: 5px; border-color: #cfd8cd; background: #fff; color: #2b4434; font-weight: 500; text-align: left; }
[data-testid="stBaseButton-secondary"]:hover { border-color: #6b8671; background: #f0f4ed; color: #243d2e; }
[data-testid="stBaseButton-primary"] { border-radius: 5px; background: #355a43; border-color: #355a43; color: #fff; }
[data-testid="stChatInput"] { border: 1px solid #c8d2c5; border-radius: 7px; background: #fff; box-shadow: 0 3px 18px #20382a08; }
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] { background: #f8f9f6; }
[data-testid="stChatMessage"] { border-radius: 5px; }
hr { border-color: #dce2d9; margin: 1.35rem 0; }
@media(max-width: 640px) {
    [data-testid="stMainBlockContainer"] { padding: 2rem 1.1rem 2rem; }
    h1 { font-size: 2.2rem !important; }
}
</style>
""", unsafe_allow_html=True)

for name, default in {"messages": [], "attempts": {}, "issue_query": None, "resolved": False, "pending_query": None}.items():
    if name not in st.session_state:
        st.session_state[name] = default


def reset_session():
    st.session_state.messages = []
    st.session_state.attempts = {}
    st.session_state.issue_query = None
    st.session_state.resolved = False
    st.session_state.pending_query = None
    for key in list(st.session_state):
        if key.startswith("outcome_"):
            del st.session_state[key]


def check_backend_health():
    try:
        response = httpx.get(f"{API_BASE}/health", timeout=5)
        return response.json() if response.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def call_support_api(query, history):
    try:
        response = httpx.post(f"{API_BASE}/support", json={
            "query": query,
            "rulebooks": st.session_state.get("rulebooks", []),
            "internet_fallback": st.session_state.get("internet_fallback", True),
            "issue_query": st.session_state.issue_query,
            "attempts": [{"step_id": key, "outcome": value} for key, value in st.session_state.attempts.items()],
            "conversation_history": [{"role": m["role"], "content": m["content"][:8000]} for m in history[-10:]],
        }, timeout=60)
        if response.status_code == 200:
            return response.json()
        st.error("This request could not be completed. Please try again or contact your helpdesk.")
    except (httpx.HTTPError, ValueError):
        st.error("The support service isn't responding. Please try again in a moment.")
    return None


def display_answer(message):
    # Keep the API's explicit mode label, presented as a short caption in the UI.
    content = message["content"]
    if content.startswith("[RUNBOOK EXTRACT"):
        content = re.sub(r"^\[RUNBOOK EXTRACT[^\]]*\]\s*", "", content)
    return content


with st.sidebar:
    st.markdown('<div class="wordmark">desk.</div><div class="sidebar-note">IT support workspace</div>', unsafe_allow_html=True)
    st.divider()
    st.button("New issue / clear session", on_click=reset_session, use_container_width=True)
    st.markdown('<div class="session-label">CURRENT SESSION</div>', unsafe_allow_html=True)
    if st.session_state.issue_query:
        st.write(st.session_state.issue_query)
    else:
        st.caption("No open issue")
    attempts = len(st.session_state.attempts)
    st.caption(f"{attempts} procedure{'s' if attempts != 1 else ''} recorded")
    st.markdown('<div class="session-label">YOUR RULEBOOKS</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Add rulebooks", type=["md", "txt"], accept_multiple_files=True,
        help="Up to 3 UTF-8 Markdown/text files, 100 KB each and 200 KB combined. Uploads stay in this session. Use headings and numbered procedures.")
    st.caption("Up to 3 files; 100 KB each and 200 KB combined.")
    with st.expander("Or paste a rulebook"):
        pasted_rulebook = st.text_area("Rulebook text", max_chars=100_000, height=150,
            help="Use headings and numbered steps. This text stays in your session.")
    books = []
    upload_error = None
    if len(uploaded_files) > 3 or sum(file.size for file in uploaded_files) > 200_000:
        upload_error = "Use up to 3 files, no more than 200 KB combined."
    else:
        for file in uploaded_files:
            if file.size > 100_000:
                upload_error = "Each rulebook must be 100 KB or smaller."
                break
            try:
                content = file.getvalue().decode("utf-8-sig")
                if not content.strip():
                    raise ValueError("Empty file")
                books.append({"name": file.name, "content": content})
            except (UnicodeDecodeError, ValueError):
                upload_error = "Use nonempty UTF-8 Markdown or text files."
                break
    if pasted_rulebook.strip():
        books.append({"name": "pasted-rulebook.md", "content": pasted_rulebook})
    if len(books) > 3 or sum(len(book["content"].encode("utf-8")) for book in books) > 200_000 or any(len(book["content"].encode("utf-8")) > 100_000 for book in books):
        upload_error = "Use up to 3 rulebooks, 100 KB each and 200 KB combined, including pasted text."
    if upload_error:
        st.error(upload_error)
        books = []
    st.session_state.rulebooks = books
    st.session_state.upload_error = upload_error
    import hashlib
    book_signature = hashlib.sha256(repr(books).encode()).hexdigest()
    if st.session_state.get("book_signature", book_signature) != book_signature:
        reset_session()
    st.session_state.book_signature = book_signature
    if books:
        st.caption(f"{len(books)} rulebook(s) selected. These replace the sample runbooks for this session.")
    st.toggle("Internet fallback", value=True, key="internet_fallback")
    st.caption("If no procedure is found, search Microsoft Learn and check the fetched pages. Only search text is sent; uploaded rulebooks stay local. Do not include confidential details in queries.")
    st.markdown('<div class="session-label">KNOWLEDGE BASE</div>', unsafe_allow_html=True)
    health = check_backend_health()
    online = health and health.get("status") == "ok"
    if online:
        st.markdown('<div class="status">Runbooks available</div>', unsafe_allow_html=True)
        provider = health.get("llm_provider")
        st.caption("Guidance quoted from local runbooks." if provider == "extractive" else "Test preview — no generated guidance." if provider == "mock" else "Model-generated guidance with sources.")
    else:
        st.markdown('<div class="status offline">Service unavailable</div>', unsafe_allow_html=True)
        st.caption("Reconnect to the support service to continue.")
    st.divider()
    st.caption("This session is temporary. Start a new issue to clear its history and outcomes.")
    with st.expander("About this workspace"):
        st.write("A demonstration using sample IT runbooks. Review each procedure and its prerequisites before making changes. Contact your helpdesk for urgent issues.")

st.markdown('<div class="eyebrow">OPERATIONS / SUPPORT</div>', unsafe_allow_html=True)
st.title("Support desk")
st.write("Find the right procedure. Keep track of what you’ve tried.")
st.divider()

if not st.session_state.messages:
    st.subheader("What needs fixing?")
    st.caption("Describe what happened below, or start with a common issue.")
    for row in range(2):
        columns = st.columns(2, gap="medium")
        for column, (label, detail, question) in zip(columns, STARTERS[row*2:row*2+2]):
            with column:
                with st.container(border=True):
                    if st.button(label, key=f"starter_{row}_{label}", use_container_width=True):
                        st.session_state.pending_query = question
                    st.caption(detail)
    st.caption("Include the affected application or device, the exact error, and anything you’ve already tried.")

for index, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        with st.container():
            st.markdown('<div class="eyebrow">YOUR NOTE</div>', unsafe_allow_html=True)
            st.write(message["content"])
    else:
        with st.container(border=True):
            label = "RUNBOOK GUIDANCE" if message.get("answer_mode") == "extractive" else "SUPPORT GUIDANCE"
            st.markdown(f'<div class="eyebrow">{label}</div>', unsafe_allow_html=True)
            origin = message.get("knowledge_origin")
            if origin == "internet":
                st.caption("External guidance · Microsoft documentation. Check compatibility with your environment and company rules.")
            elif origin == "uploaded_rulebook":
                st.caption("From your uploaded rulebooks")
            if message.get("analysis"):
                with st.expander("Source checks"):
                    for note in message["analysis"]:
                        st.write(note)
            if message.get("category") and not message["category"].startswith("Unknown"):
                st.caption(message["category"])
            for step in message.get("steps", []):
                if step.get("sequence"):
                    st.caption(f"Procedure {step['position']} of {len(step['sequence'])}")
                    with st.expander("Procedure order", expanded=True):
                        for position, title in enumerate(step["sequence"], start=1):
                            st.write(title + (" — current" if position == step["position"] else ""))
            prerequisites = [check for step in message.get("steps", []) for check in step.get("prerequisites", [])]
            if prerequisites:
                st.markdown("### Before you start")
                for check in prerequisites:
                    st.markdown(check["text"] if check["text"].lstrip().startswith(("- ", "* ")) else "- " + check["text"])
                st.caption("These are checks for you to confirm. This app cannot inspect your device or guarantee a fix.")
                with st.expander("Where these checks come from"):
                    for check in prerequisites:
                        st.text(f"{check['doc_id']} · {check['source_section']}")
                        if check.get("source_quote"):
                            st.caption(check["source_quote"])
                st.divider()
            st.markdown(display_answer(message))
            for step in message.get("steps", []):
                if any(any(s["step_id"] == step["step_id"] for s in later.get("steps", [])) for later in st.session_state.messages[index+1:]):
                    continue
                labels = ["Not tried", "Tried", "Worked", "Didn't work"]
                values = {"Tried": "tried", "Worked": "worked", "Didn't work": "did_not_work"}
                current = next((key for key, value in values.items() if value == st.session_state.attempts.get(step["step_id"])), "Not tried")
                selected = st.selectbox("How did this procedure go?", labels, index=labels.index(current), key=f"outcome_{index}_{step['step_id']}")
                if selected in values:
                    st.session_state.attempts[step["step_id"]] = values[selected]
                else:
                    st.session_state.attempts.pop(step["step_id"], None)
            if message.get("sources"):
                with st.expander("Source references"):
                    for source in message["sources"]:
                        st.text(f"{source['doc_id']} · {source['source']}")
                        st.caption(source["excerpt"])
                        if source.get("url"):
                            st.link_button("Open official source", source["url"])
                            st.caption("Fetched: " + source.get("fetched_at", ""))
            if message.get("disclaimer"):
                st.caption(message["disclaimer"])
    st.write("")

st.session_state.resolved = "worked" in st.session_state.attempts.values()
if st.session_state.resolved:
    st.success("Marked as resolved. Start a new issue if you need anything else.")
elif st.session_state.attempts:
    if st.button("Show next supported step", type="primary"):
        st.session_state.pending_query = "Please show the next supported step."

pending = st.session_state.pop("pending_query", None)
query = st.chat_input("Describe the issue or add a detail…") or pending
if query and st.session_state.get("upload_error"):
    st.error("Fix the rulebook upload before submitting a query.")
    query = None
if query:
    if st.session_state.issue_query is None:
        st.session_state.issue_query = query
    history = st.session_state.messages[:]
    st.session_state.messages.append({"role": "user", "content": query})
    with st.spinner("Checking the runbooks…"):
        response = call_support_api(query, history)
    if response:
        st.session_state.messages.append({
            "role": "assistant", "content": response.get("answer", "No guidance returned."),
            "sources": response.get("sources", []), "steps": response.get("steps", []),
            "knowledge_origin": response.get("knowledge_origin"), "analysis": response.get("analysis", []),
            "category": response.get("category", ""), "answer_mode": response.get("answer_mode", "mock"),
            "disclaimer": response.get("disclaimer", "Review the procedure before applying changes."),
        })
        st.rerun()
