#!/usr/bin/env python3
"""Diagnose Vertex AI connectivity."""
import os
from dotenv import load_dotenv

load_dotenv()

project = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

print(f"Project:  {project}")
print(f"Location: {location}")
print(f"Creds:    {creds_file}")
print(f"Creds file exists: {os.path.exists(creds_file) if creds_file else 'GOOGLE_APPLICATION_CREDENTIALS not set'}")
print()

# Check what identity the credentials resolve to
try:
    import google.auth
    credentials, detected_project = google.auth.default()
    print(f"google.auth.default() → project: {detected_project}")
    print(f"Credential type: {type(credentials).__name__}")
except Exception as e:
    print(f"google.auth.default() failed: {e}")

print()

# Try a simple Vertex AI call with a known-stable model
from google import genai
from google.genai import types


client = genai.Client()

# List all models and filter by what they support (e.g., content generation)
# for model in client.models.list():
#     print(f"Model ID: {model.name} -> Display Name: {model.display_name}")

# for model_id in [
#     "publishers/google/models/gemini-3.5-flash",
#     "gemini-3-flash-preview",
#     "gemini-3.1-flash-lite",
#     "gemini-2.5-flash",
# ]:
    # print(f"Testing model: {model_id} ...", end=" ", flush=True)
try:
    resp = client.models.generate_content(
        model="projects/plan-my-trip-493220/locations/us-central1/publishers/google/models/gemini-3.5-flash",
        contents="Say 'ok' and nothing else.",
    )
    print(f"✓  response: {resp.text}")
except Exception as e:
    print(f"✗  {type(e).__name__}: {str(e)}")
