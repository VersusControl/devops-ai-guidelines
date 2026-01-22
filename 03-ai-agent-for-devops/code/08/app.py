"""
AI Log Analyzer - Streamlit Chat Interface

A web-based chat interface for the AI logging agent using Streamlit.
Run with: streamlit run app.py
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
        st.title("🔍 AI Log Analyzer")
        st.markdown("---")
        
        st.subheader("About")
        st.markdown("""
        An AI-powered log analysis tool that helps you:
        - 📁 Read and analyze log files
        - 🔎 Search for specific patterns
        - 💡 Get intelligent insights
        - 🗨️ Ask questions in natural language
        """)
        
        st.markdown("---")
        
        st.subheader("Available Tools")
        st.markdown("""
        - **read_log_file**: Read a specific log file
        - **list_log_files**: List all available logs
        - **search_logs**: Search for patterns in logs
        """)
        
        st.markdown("---")
        
        st.subheader("Example Questions")
        st.markdown("""
        - "What log files are available?"
        - "Read the app.log file"
        - "What errors are in error.log?"
        - "Search for 'database' in app.log"
        - "When did the connection fail?"
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
    st.title("Chat with AI Log Analyzer")
    st.markdown("Ask me anything about your log files!")
    
    # Display chat messages
    display_chat_messages()
    
    # Chat input
    if prompt := st.chat_input("Ask about your logs..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
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
