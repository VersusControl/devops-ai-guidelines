#!/usr/bin/env python3
"""
AI Logging Agent
Main entry point for the interactive agent
"""
import sys

from .agents import LogAnalyzerAgent
from .config import Config


def print_banner():
    """Print welcome banner"""
    print("=" * 60)
    print("AI Log Analyzer")
    print("=" * 60)
    print("\nCapabilities:")
    print("  - Read and analyze log files")
    print("  - Answer questions about errors and patterns")
    print("  - Maintain conversation context")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the program")
    print("  'clear' - Clear conversation history")
    print("  'help' - Show available commands")
    print("=" * 60)
    print()


def print_help():
    """Print help information"""
    print("\nAvailable commands:")
    print("  quit/exit  - Exit the program")
    print("  clear      - Clear conversation history")
    print("  help       - Show this help message")
    print("\nExample questions:")
    print("  - What log files are available?")
    print("  - Read the app.log file")
    print("  - What errors are in app.log?")
    print("  - Search for 'ERROR' in app.log")
    print("  - When did the database connection fail?")
    print()


def main():
    """Main interactive loop"""
    try:
        # Validate configuration
        Config.validate()
        
        # Print banner
        print_banner()
        
        # Initialize agent
        print("Initializing AI agent...")
        agent = LogAnalyzerAgent()
        print("Ready!\n")
        
        # Main loop
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                # Handle empty input
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if user_input.lower() == 'clear':
                    agent.clear_history()
                    print("\nConversation history cleared.\n")
                    continue
                
                if user_input.lower() == 'help':
                    print_help()
                    continue
                
                # Process query
                response = agent.process_query(user_input)
                print(f"\nAgent: {response}\n")
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit.\n")
                continue
            except EOFError:
                print("\n\nGoodbye!")
                break
    
    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
        print("Please check your .env file and ensure GEMINI_API_KEY is set.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
