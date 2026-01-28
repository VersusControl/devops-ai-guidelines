"""
AI Logging Agent
"""
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents import LogAnalyzerAgent
from src.config import Config


# Page configuration
st.set_page_config(
    page_title="AI Log Analyzer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'agent' not in st.session_state:
        try:
            Config.validate()
            st.session_state.agent = LogAnalyzerAgent()
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()


def display_sidebar():
    """Display sidebar with information and controls"""
    with st.sidebar:
        st.title("AI Logging Agent")
        st.markdown("---")
        
        st.subheader("About")
        st.markdown("""
        AI-powered log analysis and incident response:
        - Read and analyze pod logs
        - Detect critical issues
        - Action when needed
        - Get intelligent recommendations
        - Natural language interface
        """)
        
        st.markdown("---")
        
        st.subheader("Available Tools")
        st.markdown("""
        **Log Analysis:**
        - `read_log_file` - Read specific log file
        - `list_log_files` - List available logs
        - `search_logs` - Search log patterns
        
        **Kubernetes Actions:**
        - `restart_kubernetes_pod` - Restart failed pod
          - 🔒 Always asks for approval
          - ⚡ Recommended for P1 OOM issues
        """)
        
        st.markdown("---")
        
        st.subheader("Example Questions")
        st.markdown("""
        - "Check app.log for issues"
        - "What errors are in the Java pod logs?"
        - "Analyze the OutOfMemoryError"
        - "List all log files"
        - "Search for 'CrashLoopBackOff'"
        """)
        
        st.markdown("---")
        
        st.subheader("Severity Levels")
        st.markdown("""
        - **P1**: OOM, pod crashes
        - **P2**: Errors, degradation
        - **P3**: Warnings
        - **Info**: Normal operations
        """)
        
        st.markdown("---")
        
        st.subheader("How It Works")
        st.markdown("""
        1. **Analysis**: AI examines logs and identifies issues
        2. **Recommendation**: Suggests actions (e.g., pod restart)
        3. **Confirmation**: Asks for your approval
        4. **Execution**: Performs action after you confirm
        """)
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # System info
        st.markdown("---")
        st.caption(f"Model: {Config.GEMINI_MODEL}")
        st.caption(f"Temperature: {Config.TEMPERATURE}")
        st.caption(f"Log Directory: {Config.LOG_DIRECTORY}")
        st.caption(f"K8s Namespace: {Config.K8S_DEFAULT_NAMESPACE}")


def display_chat_messages():
    """Display all chat messages from history"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def convert_to_langchain_messages(messages):
    """Convert Streamlit messages to LangChain message format"""
    langchain_messages = []
    for msg in messages:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))
    return langchain_messages


def main():
    """Main application logic"""
    # Initialize session state
    initialize_session_state()
    
    # Display sidebar
    display_sidebar()
    
    # Main content area
    st.markdown("Analyze pod logs and manage incidents with intelligent automation")
    
    # Info banner
    st.info("""
    💡 **Tip**: Ask me to check `app.log` to see intelligent incident analysis!
    I will analyze the issue, recommend actions, and wait for your confirmation before executing.
    """)
    
    # Display chat messages
    display_chat_messages()
    
    # Chat input
    if prompt := st.chat_input("Ask about Kubernetes logs or pod status..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing logs and checking pod status..."):
                # Convert chat history to LangChain format
                chat_history = convert_to_langchain_messages(
                    st.session_state.messages[:-1]  # Exclude the current message
                )
                
                # Get response from agent
                response = st.session_state.agent.process_query(
                    user_input=prompt,
                    chat_history=chat_history
                )
                
                # Display response
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
