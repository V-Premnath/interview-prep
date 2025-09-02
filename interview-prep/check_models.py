import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load the same API key from your .env file
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

print("Checking for models compatible with the 'live.connect' feature...")

compatible_models = []
for model in genai.list_models():
    # The key is to check for the 'bidi-generate-content' method
    if 'bidi-generate-content' in model.supported_generation_methods:
        compatible_models.append(model.name)

if compatible_models:
    print("\n✅ Found compatible models for your API key:")
    for model_name in compatible_models:
        print(f"   - {model_name}")
    print("\nACTION: Copy one of these model names into your 'live_interview_agent.py' script.")
else:
    print("\n❌ No models compatible with the live API were found for your account.")
    print("ACTION: Please check your Google Cloud project to ensure the 'Generative AI API' is enabled and that your account has access to this preview feature.")