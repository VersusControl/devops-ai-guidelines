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