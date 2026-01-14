# Chapter 7: Building Your First AI Logging Agent

This is a simple AI logging agent - focused and effective.

## What It Does

- Reads log files from the `logs/` directory
- Analyzes logs using Google Gemini AI
- Answers questions about errors, patterns, and issues
- Maintains conversation history

## What It Doesn't Do (Yet)

- No routing decisions (that's Level 2)
- No multi-source integration (that's Level 3)
- No automated actions or remediation
- No database or persistent storage

## Project Structure

```
07/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── models/
│   │   └── gemini.py        # LLM wrapper
│   ├── tools/
│   │   └── log_reader.py    # Log reading tools
│   ├── agents/
│   │   └── log_analyzer.py  # Main agent logic
│   └── utils/
│       └── response.py      # Response formatting
├── logs/                     # Sample log files
├── tests/                    # Basic tests
└── requirements.txt
```

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # or: conda activate ai-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Usage

Run the interactive agent:
```bash
python -m src
```

Or use the Makefile:
```bash
make run
```

## Example Conversation

```
AI Log Analyzer (Level 1) ready. Type 'quit' to exit.

You: What errors are in app.log?
Agent: I'll read the app.log file for you...

[Reading: logs/app.log]

I found 2 errors in app.log:
1. Database connection timeout at 10:24:12
2. Failed to execute query at 10:24:13

Both errors occurred around the same time, suggesting a database connectivity issue.

You: What happened after that?
Agent: After the errors, the application retried the connection and successfully reconnected at 10:24:15.
```

## Key Concepts

- **Level 1 Agent**: Simple, stateless log analyzer
- **Tool-based**: Uses LangChain tools for file reading
- **Memory**: Maintains conversation context
- **Clean architecture**: Separation of concerns (models, tools, agents, utils)
