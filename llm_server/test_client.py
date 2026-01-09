#!/usr/bin/env python3
"""
Simple test client for the LLM server.
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth


def test_llm_server(
    base_url: str = "http://localhost:8000",
    username: str = None,
    password: str = None,
):
    """Test the LLM server endpoints."""

    # Get credentials from environment or use defaults
    username = username or os.getenv("LLM_USERNAME", "admin")
    password = password or os.getenv("LLM_PASSWORD", "password")

    print(f"Testing LLM server at {base_url}")
    print(f"Using credentials: {username}:{'*' * len(password)}\n")

    # Test 1: Health check (no auth required)
    print("Test 1: Health check endpoint")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}\n")
    except Exception as e:
        print(f"Error: {e}\n")
        return False

    # Test 2: Query endpoint (requires auth)
    print("Test 2: Query endpoint with authentication")
    try:
        response = requests.post(
            f"{base_url}/query",
            auth=HTTPBasicAuth(username, password),
            json={
                "prompt": "What is the capital of France? Answer in one sentence.",
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.95,
            },
            timeout=60,  # Generation can take a while on CPU
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Model: {result['model_name']}")
            print(f"Prompt: {result['prompt']}")
            print(f"Response: {result['response']}\n")
        else:
            print(f"Error: {response.text}\n")
            return False

    except Exception as e:
        print(f"Error: {e}\n")
        return False

    # Test 3: Test without authentication (should fail)
    print("Test 3: Query without authentication (should fail)")
    try:
        response = requests.post(
            f"{base_url}/query",
            json={
                "prompt": "Hello",
                "max_tokens": 50,
            },
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 401:
            print("Authentication correctly required!\n")
        else:
            print(f"Warning: Expected 401, got {response.status_code}\n")

    except Exception as e:
        print(f"Error: {e}\n")
        return False

    print("All tests completed successfully!")
    return True


if __name__ == "__main__":
    # Allow command line arguments
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    username = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None

    success = test_llm_server(base_url, username, password)
    sys.exit(0 if success else 1)
