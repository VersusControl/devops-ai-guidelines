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