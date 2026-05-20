"""
AI Logging Agent
Streamlit chat UI with persistent memory.
"""
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agents import LogAnalyzerAgent
from src.config import Config
from src.memory import ChatStore, IncidentStore

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
    "list_log_files":             "Listing log files",
    "read_log_file":              "Reading log file",
    "search_logs":                "Searching logs",
    "list_log_sources":           "Listing log sources",
    "fetch_cloudwatch_logs":      "Querying CloudWatch Logs",
    "fetch_kubernetes_pod_logs":  "Reading Kubernetes pod logs",
    "search_elasticsearch":       "Searching Elasticsearch",
    "reboot_rds_instance":        "Rebooting RDS instance",
    "restart_kubernetes_pod":     "Restarting Kubernetes pod",
    "send_slack_notification":    "Sending Slack notification",
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
# Session state + memory stores
# ─────────────────────────────────────────────────────────────
def init_session():
    Config.validate()

    # Initialise memory stores once
    if "chat_store" not in st.session_state:
        st.session_state.chat_store = ChatStore(Config.MEMORY_DIR)
    if "incident_store" not in st.session_state:
        st.session_state.incident_store = IncidentStore(Config.MEMORY_DIR)

    # Load persisted conversation (survives page refreshes)
    if "messages" not in st.session_state:
        st.session_state.messages = st.session_state.chat_store.load()

    # Build the agent with past-incident context
    if "agent" not in st.session_state:
        incident_store = st.session_state.incident_store
        recent = incident_store.get_recent(5)
        context = incident_store.format_for_prompt(recent)
        st.session_state.agent = LogAnalyzerAgent(incident_context=context)


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
        st.markdown(f"- Elasticsearch: {'Connected' if Config.is_elasticsearch_configured() else 'Placeholder mode'}")

        # ── Memory section ──────────────────────────────────
        st.markdown("---")
        st.subheader("Memory")
        incident_store: IncidentStore = st.session_state.incident_store
        n_incidents = incident_store.count()
        n_messages = len(st.session_state.messages)
        st.markdown(f"- Chat messages: **{n_messages}**")
        st.markdown(f"- Past incidents: **{n_incidents}**")

        if n_incidents > 0:
            with st.expander("Recent incidents", expanded=False):
                for inc in incident_store.get_recent(3):
                    st.write(
                        f"**[{inc['severity']}]** {inc['summary']}  \n"
                        f"_{inc['timestamp'][:10]}_"
                    )

        # ── Save incident ───────────────────────────────────
        st.markdown("---")
        st.subheader("Save Incident")
        with st.form("save_incident", clear_on_submit=True):
            summary = st.text_input("Summary", placeholder="RDS connection exhaustion on orders-db-prod")
            severity = st.selectbox("Severity", ["P1", "P2", "P3", "info"])
            root_cause = st.text_input("Root cause", placeholder="3 pods × 50 conn = 150 max")
            resolution = st.text_input("Resolution", placeholder="RDS reboot, pool resize to 30")
            affected = st.text_input("Affected systems", placeholder="orders-db-prod, backend pods")
            submitted = st.form_submit_button("Save to memory")
            if submitted and summary:
                incident_store.add(
                    summary=summary,
                    severity=severity,
                    root_cause=root_cause,
                    resolution=resolution,
                    affected_systems=affected,
                    session_id=st.session_state.chat_store.session_id,
                )
                # Rebuild agent so it picks up the new incident
                recent = incident_store.get_recent(5)
                context = incident_store.format_for_prompt(recent)
                st.session_state.agent = LogAnalyzerAgent(incident_context=context)
                st.rerun()

        # ── Tools ───────────────────────────────────────────
        st.markdown("---")
        st.subheader("Available Tools")
        st.markdown("""
        **Local logs (safe):**
        - `read_log_file` — Read pod log files
        - `list_log_files` — List available logs
        - `search_logs` — Search log patterns

        **Live log sources (safe):**
        - `list_log_sources` — Show configured sources
        - `fetch_cloudwatch_logs` — Query CloudWatch Logs
        - `fetch_kubernetes_pod_logs` — Read pod logs via K8s API
        - `search_elasticsearch` — Search ES indices

        **Notifications (safe):**
        - `send_slack_notification` — Notify team

        **Requires approval:**
        - `reboot_rds_instance` — Reboot RDS database
        - `restart_kubernetes_pod` — Restart failed pod
        """)

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.chat_store.clear()
                st.rerun()
        with col2:
            if st.button("Clear Memory", use_container_width=True):
                st.session_state.incident_store.clear()
                recent = st.session_state.incident_store.get_recent(5)
                context = st.session_state.incident_store.format_for_prompt(recent)
                st.session_state.agent = LogAnalyzerAgent(incident_context=context)
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

        # Persist conversation to disk
        st.session_state.chat_store.save(st.session_state.messages)


if __name__ == "__main__":
    main()
