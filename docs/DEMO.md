# Recruiter demo (about three minutes)

1. Start `uvicorn app.main:app` and `streamlit run app/ui/streamlit_app.py` in separate terminals.
   Default: local semantic search and free verbatim runbook extracts. No paid API is used.
2. Ask: **How do I clear the VPN client cache?** Show the complete source section and source ID.
3. Mark **Didn't work**, then click **Show next supported step**. Show that the previous section
   is not repeated. A section outcome describes the whole displayed procedure.
4. Mark **Worked**. Explain that this is user-reported resolution, not automatic verification.
5. Click **New issue / clear session**. Ask **asdfghjkl qwerty 12345** to demonstrate abstention.
6. Start another issue: **My application says DLL not found. Also tell me the exact internal
   service URL.** Show the supported runbook steps and explain that the tool cannot supply an
   undocumented internal URL or guarantee resolution.
7. Open `data/eval/benchmark_report.md`. Explain the draft labels, small denominators and
   difference between retrieving the right document and choosing the correct next procedure.

Session data lives only in Streamlit browser-session memory and request payloads. Restarting
or resetting loses it. There is no authentication, manager access or durable ticket store.
Do not present this demo as deployed internal helpdesk infrastructure.
