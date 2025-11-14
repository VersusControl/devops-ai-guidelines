import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# Load environment variables
load_dotenv()

# Initialize the model with tool binding
@tool
def read_log_file(filename: str) -> str:
    """Read contents of a log file. Input should be the filename."""
    try:
        with open(f"logs/{filename}", 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"Log file {filename} not found"

@tool
def count_errors(log_content: str) -> str:
    """Count how many error lines are in log content. Input should be the log content as a string."""
    lines = log_content.split('\n')
    errors = [line for line in lines if 'ERROR' in line or 'error' in line]
    return f"Found {len(errors)} error lines"

# Create tools list
tools = [read_log_file, count_errors]

# Initialize the model
llm = ChatGoogleGenerativeAI(
    model='gemini-2.5-flash',
    google_api_key=os.environ['GEMINI_API_KEY'],
    temperature=0.1
)

# Bind tools to the model
llm_with_tools = llm.bind_tools(tools)

# Create chat memory
chat_history = InMemoryChatMessageHistory()

# Create a prompt that includes message history
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a DevOps expert analyzing application logs. Use the available tools to read log files and analyze them."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
])

# Create a chain with the prompt and model
chain = prompt | llm_with_tools

# Wrap the chain with message history
chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: chat_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

# Helper function to extract text from response
def extract_response_text(response) -> str:
    """Extract text content from various response formats."""
    if hasattr(response, 'content'):
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # Handle structured content (list of content blocks)
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and 'text' in block:
                    text_parts.append(block['text'])
                elif isinstance(block, str):
                    text_parts.append(block)
            return ''.join(text_parts)
        else:
            return str(response.content)
    return str(response)

# Main interaction loop
def main():
    print("AI Log Analyzer ready. Type 'quit' to exit.")
    print("Try asking: 'Read the app.log file' or 'What errors are in the logs?'\n")
    
    session_id = "default_session"
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        try:
            # Get response from chain with history
            response = chain_with_history.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
            
            # Check if model wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tool calls
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # Find and execute the tool
                    for tool in tools:
                        if tool.name == tool_name:
                            result = tool.invoke(tool_args)
                            print(f"\n[Tool: {tool_name}]\n{result}\n")
                            
                            # Get final response based on tool results
                            final_response = llm.invoke([
                                ("system", "You are a DevOps expert analyzing logs. The user asked a question and you used a tool to get information. Now provide a clear, concise answer to the user's question based on the tool results."),
                                ("user", f"User asked: {user_input}\n\nTool result:\n{result}\n\nPlease analyze these actual logs and answer the user's question."),
                            ])
                            
                            # Extract and display response
                            response_text = extract_response_text(final_response)
                            print(f"Agent: {response_text}\n")
                            
                            # Add to chat history
                            chat_history.add_user_message(user_input)
                            chat_history.add_ai_message(response_text)
                            break
            else:
                # Direct response without tools
                response_text = extract_response_text(response)
                print(f"\nAgent: {response_text}\n")
                
                # Add to chat history
                chat_history.add_user_message(user_input)
                chat_history.add_ai_message(response_text)
                
        except Exception as e:
            print(f"Error: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()