"""
Log Analyzer Agent
AI agent for analyzing log files with Streamlit support
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from ..models import GeminiModel
from ..tools import get_log_tools
from ..utils.response import extract_response_text
from ..config import Config


class LogAnalyzerAgent:
    """
    AI Logging Agent with Streamlit Support
    
    Capabilities:
    - Read and analyze log files
    - Answer questions about logs
    - Maintain conversation history (via external storage)
    
    Limitations:
    - No routing decisions
    - No automated actions
    - No multi-source integration
    """
    
    def __init__(self):
        """Initialize the agent"""
        # Initialize model
        self.model = GeminiModel()
        self.llm = self.model.get_llm()
        
        # Get tools
        self.tools = get_log_tools()
        
        # Bind tools to model
        self.llm_with_tools = self.model.get_llm_with_tools(self.tools)
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", Config.get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])
    
    def process_query(self, user_input: str, chat_history: list = None) -> str:
        """
        Process a user query and return the response.
        
        Args:
            user_input: User's question or command
            chat_history: List of previous messages (HumanMessage, AIMessage)
        
        Returns:
            String containing the agent's response
        """
        if chat_history is None:
            chat_history = []
        
        try:
            # Format messages for the prompt
            messages = self.prompt.format_messages(
                chat_history=chat_history,
                input=user_input
            )
            
            # Get response from LLM with tools
            response = self.llm_with_tools.invoke(messages)
            
            # Check if model wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return self._handle_tool_calls(response, user_input, chat_history)
            else:
                # Direct response without tools
                return extract_response_text(response)
        
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"\n{error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    def _handle_tool_calls(self, response, user_input: str, chat_history: list) -> str:
        """
        Handle tool calls from the model.
        
        Args:
            response: LLM response containing tool calls
            user_input: Original user input
            chat_history: Conversation history
        
        Returns:
            Final response after executing tools
        """
        tool_results = []
        
        # Execute each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Find and execute the tool
            tool_func = None
            for tool in self.tools:
                if tool.name == tool_name:
                    tool_func = tool
                    break
            
            if tool_func:
                try:
                    result = tool_func.invoke(tool_args)
                    tool_results.append({
                        'tool': tool_name,
                        'result': result
                    })
                except Exception as e:
                    tool_results.append({
                        'tool': tool_name,
                        'result': f"Error: {str(e)}"
                    })
        
        # Build analysis prompt with tool results
        analysis_prompt = f"User asked: {user_input}\n\n"
        analysis_prompt += "Tool results:\n"
        for tr in tool_results:
            analysis_prompt += f"\n{tr['tool']}:\n{tr['result']}\n"
        analysis_prompt += "\nPlease analyze these results and answer the user's question."
        
        # Get final analysis from LLM
        final_response = self.llm.invoke(analysis_prompt)
        return extract_response_text(final_response)
