"""
Log Analyzer Agent
Simple AI agent for analyzing log files
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from ..models import GeminiModel
from ..tools import get_log_tools
from ..utils.response import extract_response_text
from ..config import Config


class LogAnalyzerAgent:
    """
    AI Logging Agent
    
    Capabilities:
    - Read and analyze log files
    - Answer questions about logs
    - Maintain conversation history
    
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
        
        # Create chat memory
        self.chat_history = InMemoryChatMessageHistory()
        
        # Create prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", Config.get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])
        
        # Create chain
        chain = self.prompt | self.llm_with_tools
        
        # Wrap with message history
        self.chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: self.chat_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        
        self.session_id = "default_session"
    
    def process_query(self, user_input: str) -> str:
        """
        Process a user query and return the response.
        
        Args:
            user_input: User's question or command
        
        Returns:
            String containing the agent's response
        """
        try:
            # Get response from chain with history
            response = self.chain_with_history.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": self.session_id}}
            )
            
            # Check if model wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return self._handle_tool_calls(response, user_input)
            else:
                # Direct response without tools
                response_text = extract_response_text(response)
                
                # Add to chat history
                self.chat_history.add_user_message(user_input)
                self.chat_history.add_ai_message(response_text)
                
                return response_text
        
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"\n{error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    def _handle_tool_calls(self, response, user_input: str) -> str:
        """
        Handle tool calls from the model.
        
        Args:
            response: Model response containing tool calls
            user_input: Original user input
        
        Returns:
            String containing the final response after tool execution
        """
        tool_results = []
        
        # Execute all tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Find and execute the tool
            for tool in self.tools:
                if tool.name == tool_name:
                    result = tool.invoke(tool_args)
                    tool_results.append({
                        'name': tool_name,
                        'result': result
                    })
                    print(f"\n[Tool: {tool_name}]")
                    print(f"{result}\n")
                    break
        
        # Get final response based on tool results
        tool_context = "\n\n".join([
            f"Tool: {tr['name']}\nResult:\n{tr['result']}"
            for tr in tool_results
        ])
        
        final_response = self.llm.invoke([
            ("system", Config.get_system_prompt() + 
             "\n\nYou used tools to get information. Now provide a clear, concise answer based on the tool results. "
             "Do not generate fake data - only analyze what you actually received."),
            ("user", f"User asked: {user_input}\n\nTool results:\n{tool_context}\n\n"
                    "Please analyze these results and answer the user's question."),
        ])
        
        # Extract and save response
        response_text = extract_response_text(final_response)
        
        # Add to chat history
        self.chat_history.add_user_message(user_input)
        self.chat_history.add_ai_message(response_text)
        
        return response_text
    
    def clear_history(self):
        """Clear the conversation history"""
        self.chat_history = InMemoryChatMessageHistory()
    
    def get_history(self) -> list:
        """Get the conversation history"""
        return self.chat_history.messages
