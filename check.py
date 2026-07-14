"""
Quick standalone test to check if an OpenRouter model is up and responding.
Run with: python test_model.py
"""

import os
import requests
from dotenv import load_dotenv

# Loads variables from your .env file (must be in the same folder, or a parent folder)
load_dotenv()

# Change "OPENROUTER_API_KEY" below if your .env uses a different variable name
API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "No API key found. Check that your .env file exists and the variable "
        "name matches what's used here (currently looking for OPENROUTER_API_KEY)."
    )

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  # change this to test other models

def test_model(model: str):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello in one word."}],
    }

    print(f"Testing model: {model}")
    response = requests.post(url, headers=headers, json=payload, timeout=30)

    print(f"Status code: {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        print("Response was not valid JSON:")
        print(response.text)
        return

    if response.status_code == 200:
        reply = data["choices"][0]["message"]["content"]
        print(f"✅ Model is working. Reply: {reply}")
    else:
        error = data.get("error", {})
        print(f"❌ Model failed. Code: {error.get('code')}, Message: {error.get('message')}")
        if "metadata" in error:
            print(f"   Details: {error['metadata']}")


if __name__ == "__main__":
    test_model(MODEL)