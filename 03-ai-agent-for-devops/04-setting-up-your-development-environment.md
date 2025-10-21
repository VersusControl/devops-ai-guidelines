# Chapter 4: Setting Up Your Development Environment

> ⭐ **Starring** this repository to support this work

## Getting Your Hands Dirty

You've learned what AI agents are, how they're different from traditional tools, and what components you need. Now it's time to actually build something.

Before you can write your first AI agent, you need a development environment. This means installing Python, setting up the right libraries, getting API keys, and making sure everything works together.

Don't worry if you're not a Python expert. I'll walk you through every step. By the end of this chapter, you'll have everything installed and you'll run your first piece of code that talks to an AI model.

## What You'll Need

Here's the complete list of what we're setting up:

1. **Python 3.9 or higher** - The programming language we'll use
2. **pip** - Python's package installer (comes with Python)
3. **A code editor** - VS Code is a good choice
4. **Git** - For version control (optional but recommended)
5. **Google AI Studio account** - To get your Gemini API key
6. **Python libraries** - We'll install these with pip

Let's go through each one.

```mermaid
graph LR
    A[Your Computer] --> B[Install Python]
    B --> C[Install Libraries]
    C --> D[Get API Key]
    D --> E[Test Setup]
    E --> F[✓ Ready to Build]
    
    style A fill:#718096,color:#fff
    style B fill:#4dabf7,color:#000
    style C fill:#4dabf7,color:#000
    style D fill:#ffd43b,stroke:#fab005,color:#000
    style E fill:#667eea,stroke:#764ba2,color:#fff
    style F fill:#51cf66,stroke:#2f9e44,color:#000
```

**Figure 4.1:** Setup Flow - Five steps to get your environment ready.

## Installing Python

First, you need Python installed on your machine. Most modern operating systems come with Python, but it might be an older version. You want Python 3.9 or newer.

### Check If You Have Python

Open your terminal and type:

```bash
python3 --version
```

If you see something like "Python 3.11.5" or any version 3.9 or higher, you're good. Skip to the next section.

If you get an error or see a version older than 3.9, you need to install Python.

### Installing Python on Mac

The easiest way is using Homebrew. If you don't have Homebrew, install it first:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python:

```bash
brew install python3
```

### Installing Python on Linux

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install python3 python3-pip
```

On Fedora or CentOS:

```bash
sudo dnf install python3 python3-pip
```

## Setting Up a Project Directory

Create a folder for your AI logging agent project. This keeps everything organized.

```bash
# Create project directory
mkdir ai-logging-agent
cd ai-logging-agent

# Create a directory for your code
mkdir src

# Create a directory for logs (we'll use this later)
mkdir logs
```

Your structure should look like this:

```
ai-logging-agent/
├── src/
└── logs/
```

## Installing Python Libraries

Now you need to install the libraries your agent will use. We'll use a virtual environment to keep things clean.

### Create a Virtual Environment

A virtual environment is like a sandbox for your Python project. It keeps your project's libraries separate from your system's Python installation.

```bash
```bash
python3 -m venv venv

# Activate it
source venv/bin/activate
```

When activated, your terminal prompt will show `(venv)` at the beginning. This means you're in the virtual environment.

### Install Required Libraries

Create a file called `requirements.txt` in your project root:

```bash
touch requirements.txt
```

Add these libraries to the file:

```
google-generativeai>=0.8.5
python-dotenv>=1.1.1
requests>=2.32.5
```

Now install them:

```bash
pip install -r requirements.txt
```

Here's what each library does:

- **google-generativeai**: Official Gemini API client
- **python-dotenv**: Loads environment variables from a `.env` file
- **requests**: Makes HTTP requests (we'll use this to fetch logs)

```mermaid
graph LR
    V[Virtual Environment] --> L1[google-generativeai<br/>Talk to Gemini]
    V --> L2[python-dotenv<br/>Manage secrets]
    V --> L3[requests<br/>Fetch logs]
    
    L1 --> Agent[Your AI Agent]
    L2 --> Agent
    L3 --> Agent
    
    style V fill:#667eea,stroke:#764ba2,color:#fff
    style Agent fill:#51cf66,stroke:#2f9e44,color:#000
```

**Figure 4.2:** Python Libraries - Each library serves a specific purpose.

## Getting Your Gemini API Key

Your AI agent needs to talk to Gemini's API. For that, you need an API key.

### Step 1: Go to Google AI Studio

Open your browser and go to [https://aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys)

Sign in with your Google account.

### Step 2: Create an API Key

Click "Get API Key" or "Create API Key in new project".

Google will generate a key that looks like this:
```
AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q
```

**Important**: Keep this key secret. Don't share it or commit it to Git.

### Step 3: Store Your API Key Safely

Create a `.env` file in your project root:

```bash
touch .env
```

Add your API key to this file:

```
GEMINI_API_KEY=your-actual-api-key-here
```

Replace `your-actual-api-key-here` with the key you just got.

### Step 4: Add .env to .gitignore

If you're using Git, make sure your `.env` file doesn't get committed.

Create a `.gitignore` file if you don't have one:

**Mac/Linux:**
```bash
cat > .gitignore << EOF
.env
venv/
__pycache__/
*.pyc
EOF
```

This prevents accidentally sharing your API key.

```mermaid
graph LR
    A[Google AI Studio] --> B[Generate API Key]
    B --> C[Save to .env file]
    C --> D[Add .env to .gitignore]
    D --> E[✓ Safe & Ready]
    
    style A fill:#4285f4,color:#fff
    style E fill:#51cf66,stroke:#2f9e44,color:#000
```

**Figure 4.3:** API Key Setup - Secure way to store your credentials.

## Your First AI Agent Code

Let's write a simple script to test that everything works. This will be your "Hello World" for AI agents.

Create a file called `src/test_setup.py`:

```python
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file")
    exit(1)

genai.configure(api_key=api_key)

# Create a model instance
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# Test with a simple log analysis
sample_log = """
2024-10-21 14:23:45 ERROR Database connection failed
2024-10-21 14:23:46 WARN Retry attempt 1 of 3
2024-10-21 14:23:48 ERROR Database connection failed
2024-10-21 14:23:49 WARN Retry attempt 2 of 3
2024-10-21 14:23:51 ERROR Database connection failed
2024-10-21 14:23:52 ERROR Maximum retries reached
"""

# Ask the AI to analyze it
prompt = f"""You are a DevOps engineer analyzing application logs.
Analyze this log and explain what's happening:

{sample_log}

Provide a brief analysis and suggest what might be wrong."""

print("Analyzing logs with AI...")
print("-" * 50)

response = model.generate_content(prompt)
print(response.text)

print("-" * 50)
print("✓ Setup successful! Your environment is ready.")
```

This script does four things:

1. Loads your API key from the `.env` file
2. Connects to Gemini
3. Sends a sample log for analysis
4. Prints the AI's response

### Run Your Test Script

Make sure you're in your project root directory and your virtual environment is activated, then run:

```bash
python src/test_setup.py
```

If everything is set up correctly, you'll see output like:

```
Analyzing logs with AI...
--------------------------------------------------
The logs show a database connection failure with 
multiple retry attempts. The application tried to 
connect three times but failed each time, eventually 
reaching the maximum retry limit.

Possible causes:
1. Database server is down or unreachable
2. Network issues between app and database
3. Invalid connection credentials
4. Connection pool exhausted

Recommended actions:
- Check if the database service is running
- Verify network connectivity
- Review database logs for additional clues
- Check connection string configuration
--------------------------------------------------
✓ Setup successful! Your environment is ready.
```

The exact response will vary because AI models generate slightly different text each time. But you should see a coherent analysis of the log file.

```mermaid
graph LR
    A[test_setup.py] --> B[Load API Key]
    B --> C[Connect to Gemini]
    C --> D[Send Sample Log]
    D --> E[Receive Analysis]
    E --> F[Print Results]
    
    F --> G{Works?}
    G -->|Yes| H[✓ Setup Complete]
    G -->|No| I[Check Errors Below]
    
    style A fill:#4dabf7,color:#000
    style E fill:#667eea,stroke:#764ba2,color:#fff
    style H fill:#51cf66,stroke:#2f9e44,color:#000
    style I fill:#ff6b6b,stroke:#c92a2a,color:#fff
```

**Figure 4.4:** Test Flow - Verify your setup works end-to-end.

## Common Issues and Solutions

Here are the problems you're most likely to run into, and how to fix them.

### "No module named 'google.generativeai'"

**Problem**: The library isn't installed.

**Solution**: Make sure your virtual environment is activated and run:
```bash
pip install -r requirements.txt
```

### "GEMINI_API_KEY not found in .env file"

**Problem**: Your `.env` file is missing or the API key isn't set correctly.

**Solution**: 
1. Check that the `.env` file exists in your project root
2. Open it and verify it has: `GEMINI_API_KEY=your-key-here`
3. Make sure there are no spaces around the `=`
4. Make sure you replaced `your-key-here` with your actual API key

### "API key not valid"

**Problem**: Your API key is incorrect or expired.

**Solution**: 
1. Go back to Google AI Studio
2. Generate a new API key
3. Update your `.env` file with the new key

### "Rate limit exceeded"

**Problem**: You're making too many API calls.

**Solution**: 
- Wait a few minutes and try again
- Free tier has limits on requests per minute
- For production use, consider upgrading to a paid plan

## Understanding Your Project Structure

Let's look at what you have now:

```
ai-logging-agent/
├── .env                    # Your API key (never commit this)
├── .gitignore             # Tells Git what to ignore
├── requirements.txt       # Python dependencies
├── venv/                  # Virtual environment (never commit this)
├── logs/                  # Sample logs will go here
└── src/
    └── test_setup.py      # Your first test script
```

This structure will grow as we add more components in the next chapters. You'll add:
- A main agent file
- Tool implementations
- Memory management
- Log retrieval functions
- Configuration files

But for now, this is a good starting point.

```mermaid
graph TB
    Root[ai-logging-agent/]
    
    Root --> Env[.env<br/>Secrets]
    Root --> Git[.gitignore<br/>Exclusions]
    Root --> Req[requirements.txt<br/>Dependencies]
    Root --> Venv[venv/<br/>Python packages]
    Root --> Logs[logs/<br/>Test data]
    Root --> Src[src/<br/>Your code]
    
    Src --> Test[test_setup.py<br/>First test]
    
    style Root fill:#667eea,stroke:#764ba2,color:#fff
    style Env fill:#ff6b6b,stroke:#c92a2a,color:#fff
    style Src fill:#51cf66,stroke:#2f9e44,color:#000
```

**Figure 4.5:** Project Structure - Organized layout for your AI agent.

## Best Practices for Development

Now that you have everything set up, here are some tips to keep your development smooth:

### Use Virtual Environments Always

Every time you start working on this project, activate your virtual environment:

```bash
source venv/bin/activate
```

When you're done, deactivate it:

```bash
deactivate
```

This keeps your project's dependencies isolated from other Python projects.

### Keep Your Dependencies Updated

Periodically update your libraries:

```bash
pip install --upgrade -r requirements.txt
```

But test after updating to make sure nothing breaks.

### Use Version Control

If you're not using Git yet, now is a good time to start:

```bash
git init
git add .
git commit -m "Initial setup"
```

Commit your changes regularly. This gives you a history to roll back to if something breaks.

### Keep API Keys Secret

Never, ever commit your `.env` file or API keys to Git. If you accidentally do:

1. Immediately revoke the API key in Google AI Studio
2. Generate a new one
3. Update your `.env` file
4. Remove the key from Git history

### Monitor Your API Usage

Gemini's free tier has limits. Keep an eye on your usage in Google AI Studio so you don't get surprised by rate limits or costs.

## What You Can Do Now

With your environment set up, you can start experimenting. Try modifying the test script:

**Change the log content**:
```python
sample_log = """
2024-10-21 15:30:12 INFO User login successful: user_id=12345
2024-10-21 15:30:15 WARN High memory usage: 85%
2024-10-21 15:30:20 ERROR Out of memory exception
2024-10-21 15:30:21 ERROR Application crashed
"""
```

**Change the prompt**:
```python
prompt = f"""You are a security analyst.
Check these logs for any security concerns:

{sample_log}

Report any suspicious activity."""
```

**Try different models**:
```python
# Try other Gemini models:
model = genai.GenerativeModel('gemini-2.5-pro')     # More capable, faster
```

Play around. Break things. That's how you learn what works and what doesn't.

```mermaid
graph LR
    A[Your Setup] --> B[Modify Logs]
    A --> C[Change Prompts]
    A --> D[Try Models]
    
    B --> E[Learn & Experiment]
    C --> E
    D --> E
    
    E --> F[Build Real Agent]
    
    style A fill:#667eea,stroke:#764ba2,color:#fff
    style E fill:#4dabf7,color:#000
    style F fill:#51cf66,stroke:#2f9e44,color:#000
```

**Figure 4.6:** Experimentation Path - Use your setup to learn and explore.

## Creating Sample Log Files

Let's create some sample log files you can use for testing. Create a file called `logs/sample_app.log`:

```
2024-10-21 10:15:23 INFO Application started successfully
2024-10-21 10:15:24 INFO Database connection pool initialized: size=10
2024-10-21 10:15:25 INFO HTTP server listening on port 8080
2024-10-21 10:17:42 INFO Processing request: GET /api/users
2024-10-21 10:17:43 INFO Request completed: 200 OK (125ms)
2024-10-21 10:18:15 WARN Slow query detected: SELECT * FROM orders (850ms)
2024-10-21 10:19:03 ERROR Database connection timeout
2024-10-21 10:19:04 WARN Retry attempt 1 of 3
2024-10-21 10:19:07 ERROR Database connection timeout
2024-10-21 10:19:08 WARN Retry attempt 2 of 3
2024-10-21 10:19:11 ERROR Database connection timeout
2024-10-21 10:19:12 ERROR Maximum retries exceeded
2024-10-21 10:19:12 ERROR Request failed: 500 Internal Server Error
2024-10-21 10:19:45 WARN High memory usage: 87%
2024-10-21 10:20:12 ERROR Out of memory exception
2024-10-21 10:20:13 FATAL Application shutting down
```

Now create a script to analyze this file. Create `src/analyze_log_file.py`:

```python
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# Read the log file
with open('logs/sample_app.log', 'r') as f:
    logs = f.read()

# Analyze with AI
prompt = f"""You are an expert DevOps engineer analyzing application logs.

Analyze these logs and provide:
1. A summary of what happened
2. The root cause of any issues
3. Recommended actions to fix the problems

Logs:
{logs}

Provide a clear, structured analysis."""

print("Analyzing log file...")
print("=" * 60)

response = model.generate_content(prompt)
print(response.text)

print("=" * 60)
```

Run it:

```bash
python src/analyze_log_file.py
```

You should see a detailed analysis of the log file, identifying the database connection issues and memory problems.

## Next: Understanding Code Structure

Before we move to the next chapter, let's understand the basic code pattern you'll be using:

```python
# 1. Setup
import os
from dotenv import load_dotenv
import google.generativeai as genai

# 2. Configuration
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# 3. Prepare data
data = "your log content here"

# 4. Create prompt
prompt = f"""Your instructions here
Data: {data}"""

# 5. Get AI response
response = model.generate_content(prompt)

# 6. Use the result
print(response.text)
```

This is the core pattern you'll see over and over. You'll add more sophistication (tools, memory, loops), but this is the foundation.

## What You've Learned

You now have a complete development environment for building AI agents. You installed Python, set up a virtual environment, installed the necessary libraries, and got your Gemini API key configured.

You wrote and ran your first AI-powered script that analyzes logs. You understand the basic code structure and how to communicate with the Gemini API. You know how to keep your API keys secure and how to organize your project files.

You also learned common pitfalls and how to fix them, and you have sample log files you can use for testing.

Most importantly, you verified that everything works end-to-end. Your environment is ready for real development.

## What's Next

Now that your environment is set up, it's time to understand the different levels of AI logging systems. In Chapter 5, you'll learn how AI agents can start simple and grow more sophisticated over time.

We'll map out a progression from basic log parsing to autonomous incident response. This will help you understand where to start and how to incrementally improve your agent.

Then in Chapter 6, we'll start building the actual components. You'll write code for roles, tasks, and tools. You'll implement memory so your agent learns from past incidents. That's when your AI logging agent starts to come alive.

---

## 💝 Support This Work

[![Sponsor](https://img.shields.io/badge/Sponsor-❤️-red?style=for-the-badge)](https://github.com/sponsors/hoalongnatsu)

> **Support this project:** Consider [sponsoring this work](https://github.com/sponsors/hoalongnatsu) to help create more AI-powered DevOps resources.

---
