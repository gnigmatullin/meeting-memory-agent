import streamlit as st
import tempfile
import os
import time
from transcript_processor import parse_transcript
from memory_store import store_meeting, get_open_action_items, mark_action_complete, get_stats
from agent import ask
from gmail_client import fetch_meeting_transcripts, is_authenticated

st.set_page_config(page_title="Meeting Memory Agent", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.title("Meeting Memory")

    stats = get_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("Meetings", stats["meetings"])
    col2.metric("Open tasks", stats["open_actions"])
    col3.metric("Done", stats["completed_actions"])

    st.divider()

    # Upload transcript
    st.subheader("Upload Transcript")
    uploaded_file = st.file_uploader("Choose a TXT file", type=["txt"])

    if uploaded_file:
        if uploaded_file.size > 1 * 1024 * 1024:
            st.error("File too large. Maximum size is 1MB.")
        else:
            if st.button("Index Transcript", type="primary"):
                with st.spinner("Processing..."):
                    text = uploaded_file.read().decode("utf-8")
                    meeting = parse_transcript(text)
                    count = store_meeting(meeting)
                    st.session_state["last_meeting"] = meeting.title
                    st.success(f"Indexed: {meeting.title} ({count} chunks)")
                    st.rerun()

    st.divider()

    # Gmail integration
    st.subheader("Gmail Integration")

    if is_authenticated():
        st.success("Gmail connected")
        if st.button("Fetch Meeting Transcripts"):
            with st.spinner("Fetching from Gmail..."):
                transcripts = fetch_meeting_transcripts(max_results=10)
                if not transcripts:
                    st.warning("No meeting transcripts found in Gmail.")
                else:
                    indexed = 0
                    for t in transcripts:
                        meeting = parse_transcript(t["body"], meeting_date=t["date"][:10])
                        store_meeting(meeting)
                        indexed += 1
                    st.success(f"Indexed {indexed} meetings from Gmail.")
                    st.rerun()
    else:
        st.info("Connect Gmail to auto-fetch meeting transcripts.")
        if st.button("Connect Gmail"):
            with st.spinner("Opening browser for authentication..."):
                from gmail_client import get_gmail_service
                get_gmail_service()
                st.rerun()

    st.divider()

    # Example questions
    st.subheader("Example questions")
    examples = [
        "What was discussed in the last meeting?",
        "What are the open action items?",
        "What decisions were made?",
        "Who needs to do what?",
    ]
    for q in examples:
        if st.button(q, use_container_width=True):
            st.session_state["example_q"] = q

# --- Main area: tabs ---
tab_chat, tab_actions = st.tabs(["💬 Chat", "✅ Action Items"])

# --- Chat tab ---
with tab_chat:
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    default_input = st.session_state.pop("example_q", "")

    if question := st.chat_input("Ask about your meetings..."):
        default_input = question

    if default_input:
        # Rate limiting
        if "last_query_time" in st.session_state:
            elapsed = time.time() - st.session_state["last_query_time"]
            if elapsed < 3:
                st.warning("Please wait before sending another message.")
                st.stop()
        st.session_state["last_query_time"] = time.time()

        if stats["meetings"] == 0:
            st.warning("No meetings indexed yet. Upload a transcript first.")
        else:
            st.session_state["messages"].append({"role": "user", "content": default_input})
            with st.chat_message("user"):
                st.markdown(default_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = ask(default_input, st.session_state["messages"][:-1])
                st.markdown(answer)

            st.session_state["messages"].append({"role": "assistant", "content": answer})
            st.rerun()

# --- Action Items tab ---
with tab_actions:
    st.subheader("Open Action Items")

    actions = get_open_action_items()

    if not actions:
        st.info("No open action items.")
    else:
        for action in actions:
            meta = action["metadata"]
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{meta.get('assignee', 'Unknown')}**")
                    st.caption(f"{action['text'][:150]}...")
                    st.caption(f"Meeting: {meta.get('title', '')} · {meta.get('date', '')}")
                with col2:
                    if st.button("Done", key=action["id"]):
                        mark_action_complete(action["id"])
                        st.rerun()