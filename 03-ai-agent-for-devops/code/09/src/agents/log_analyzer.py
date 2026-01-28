"""
Log Analyzer Agent with Kubernetes Actions (Chapter 9)
AI agent for analyzing logs and managing Kubernetes pods
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from ..models import GeminiModel
from ..tools import get_all_tools
from ..utils.response import extract_response_text
from ..config import Config


class LogAnalyzerAgent:
    """
    AI Logging Agent with Kubernetes Management Capabilities
    
    Capabilities:
    - Read and analyze application logs from Kubernetes pods
    - Detect critical issues (OutOfMemoryError, CrashLoopBackOff, etc.)
    - Automatically restart failed pods for P1 issues
    - Check pod status and retrieve pod logs
    - Scale deployments when needed
    - Maintain conversation history
    """
    
    def __init__(self):
        """Initialize the agent"""
        # Initialize model
        self.model = GeminiModel()
        self.llm = self.model.get_llm()
        
        # Get all tools (log readers + K8s actions)
        self.tools = get_all_tools()
        
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
        Handle tool calls from the model with iterative execution.
        
        Args:
            response: LLM response containing tool calls
            user_input: Original user input
            chat_history: Conversation history
        
        Returns:
            Final response after executing tools
        """
        from langchain_core.messages import AIMessage, ToolMessage
        
        # Keep track of all messages for the agent loop
        messages = self.prompt.format_messages(
            chat_history=chat_history,
            input=user_input
        )
        
        # Agent loop: continue until no more tool calls
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        current_response = response
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check if there are tool calls
            if not (hasattr(current_response, 'tool_calls') and current_response.tool_calls):
                # No more tool calls, return the final response
                return extract_response_text(current_response)
            
            # Execute each tool call
            tool_messages = []
            for tool_call in current_response.tool_calls:
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
                        tool_messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call['id']
                            )
                        )
                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        tool_messages.append(
                            ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_call['id']
                            )
                        )
            
            # Add AI response and tool results to messages
            messages.append(AIMessage(content=current_response.content, tool_calls=current_response.tool_calls))
            messages.extend(tool_messages)
            
            # Get next response from LLM (might call more tools or finish)
            current_response = self.llm_with_tools.invoke(messages)
        
        # If we hit max iterations, return what we have
        return extract_response_text(current_response)
