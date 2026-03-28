"""
AI Logging Agent
Streamlit chat UI with real-time thinking steps.
"""
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agents import LogAnalyzerAgent
from src.config import Config

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Log Analyzer - AWS",
    page_icon="AWS",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────
# StreamlitProgress — live "thinking" UI
# ─────────────────────────────────────────────────────────────
TOOL_LABELS = {
    "list_log_files":          "Listing log files",
    "read_log_file":           "Reading log file",
    "search_logs":             "Searching logs",
    "reboot_rds_instance":     "Rebooting RDS instance",
    "restart_kubernetes_pod":  "Restarting Kubernetes pod",
    "send_slack_notification": "Sending Slack notification",
}


class StreamlitProgress:
    """Callbacks that render live tool-call progress inside a st.status container."""

    def __init__(self, container):
        self.status = container
        self.tool_count = 0
        self.steps = []                    # saved into message history

    def on_thinking(self):
        self.status.update(label="Thinking...", state="running")

    def on_reasoning(self, text: str):
        if text:
            self.status.write(f"_{text}_")
            self.steps.append({"label": "Reasoning", "detail": text})

    def on_tool_start(self, tool_name: str, tool_args: dict):
        self.tool_count += 1
        label = TOOL_LABELS.get(tool_name, tool_name)
        self.status.update(label=f"{label}...", state="running")

    def on_tool_end(self, tool_name: str, result: str, success: bool = True):
        label = TOOL_LABELS.get(tool_name, tool_name)
        marker = "OK" if success else "FAIL"
        preview = _summarize_result(tool_name, result)
        self.status.write(f"[{marker}] **{label}** — {preview}")
        self.steps.append({"label": label, "detail": f"[{marker}] {preview}"})

    def on_approval_skipped(self, tool_name: str, tool_args: dict):
        label = TOOL_LABELS.get(tool_name, tool_name)
        self.status.write(f"[BLOCKED] **{label}** — requires your approval")
        self.steps.append({"label": label, "detail": "[BLOCKED] requires approval"})

    def complete(self):
        n = self.tool_count
        if n:
            self.status.update(
                label=f"Done — {n} tool{'s' if n != 1 else ''} used",
                state="complete", expanded=False,
            )
        else:
            self.status.update(label="Done", state="complete", expanded=False)

    def error(self, msg: str):
        self.status.update(label="Error", state="error")
        self.status.write(f"Error: {msg}")


def _summarize_result(tool_name: str, result: str) -> str:
    """One-line preview of a tool result for the progress panel."""
    r = str(result)
    if tool_name == "list_log_files":
        count = r.count(".log")
        return f"found {count} log file{'s' if count != 1 else ''}"
    if tool_name == "read_log_file":
        return "file read"
    if tool_name == "search_logs":
        first_line = r.split("\n")[0]
        return first_line.lower() if "Found" in first_line else "search complete"
    if tool_name == "send_slack_notification":
        return "notification sent"
    if tool_name in ("reboot_rds_instance", "restart_kubernetes_pod"):
        return "initiated"
    return r[:80]


# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        Config.validate()
        st.session_state.agent = LogAnalyzerAgent()


# ─────────────────────────────────────────────────────────────
# Chat helpers
# ─────────────────────────────────────────────────────────────
def to_langchain(messages: list) -> list:
    """Convert our message dicts to LangChain message objects."""
    out = []
    for m in messages:
        if m["role"] == "user":
            out.append(HumanMessage(content=m["content"]))
        else:
            out.append(AIMessage(content=m["content"]))
    return out


def display_history():
    """Render all past messages, including collapsed thinking steps."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            steps = msg.get("steps")
            if steps:
                with st.expander(
                    f"{len(steps)} step{'s' if len(steps) != 1 else ''}",
                    expanded=False,
                ):
                    for s in steps:
                        st.write(f"**{s['label']}** — {s['detail']}")
            st.markdown(msg["content"])


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.title("AI Logging Agent")
        st.markdown("---")

        st.subheader("Configuration")
        provider = {"gemini": "Gemini", "github": "GitHub Models", "minimax": "MiniMax"}.get(
            Config.LLM_PROVIDER, Config.LLM_PROVIDER,
        )
        st.markdown(f"- Provider: **{provider}**")
        st.markdown(f"- AWS: {'Connected' if Config.is_aws_configured() else 'Placeholder mode'}")
        st.markdown(f"- Slack: {'Connected' if Config.is_slack_configured() else 'Placeholder mode'}")

        st.markdown("---")
        st.subheader("Available Tools")
        st.markdown("""
        **Auto-execute (safe):**
        - `read_log_file` — Read pod log files
        - `list_log_files` — List available logs
        - `search_logs` — Search log patterns
        - `send_slack_notification` — Notify team

        **Requires approval:**
        - `reboot_rds_instance` — Reboot RDS database
        - `restart_kubernetes_pod` — Restart failed pod
        """)

        st.markdown("---")
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    init_session()
    sidebar()

    st.info("**Try:** *Analyze backend pod logs and detect issues*")
    display_history()

    if prompt := st.chat_input("Ask about backend logs, database issues, or pod status..."):
        # Save and show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            status = st.status("Analyzing...", expanded=True)
            progress = StreamlitProgress(status)

            history = to_langchain(st.session_state.messages[:-1])

            try:
                response = st.session_state.agent.process_query(
                    user_input=prompt,
                    chat_history=history,
                    callbacks=progress,
                )
                if not response or not response.strip():
                    response = "No response generated. Try a different question."
                progress.complete()
            except Exception as e:
                progress.error(str(e))
                response = f"Error: {e}"

            st.markdown(response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "steps": progress.steps,
        })


if __name__ == "__main__":
    main()
