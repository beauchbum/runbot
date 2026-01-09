"""
Local LLM Client for BeauchBot

Provides a wrapper around the local LLM server that mimics the OpenAI client API.
This allows for easy replacement of OpenAI calls with local LLM calls.
"""

import os
import logging
import requests
from typing import Any, Dict, List, Optional
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ChatCompletionMessage:
    """Mimics OpenAI's ChatCompletionMessage."""

    def __init__(self, content: str, role: str = "assistant"):
        self.content = content
        self.role = role


class ChatCompletionChoice:
    """Mimics OpenAI's ChatCompletionChoice."""

    def __init__(self, message: ChatCompletionMessage):
        self.message = message
        self.finish_reason = "stop"
        self.index = 0


class ChatCompletion:
    """Mimics OpenAI's ChatCompletion response."""

    def __init__(self, content: str):
        self.choices = [ChatCompletionChoice(ChatCompletionMessage(content))]
        self.id = "local-llm"
        self.model = "local"
        self.object = "chat.completion"


class ChatCompletions:
    """Mimics OpenAI's chat.completions API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password

    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion using the local LLM server.

        Args:
            model: Model name (ignored for local LLM, kept for API compatibility)
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments (ignored)

        Returns:
            ChatCompletion object with the response

        Raises:
            requests.RequestException: If the API request fails
            RuntimeError: If the server returns an error
        """
        # Convert messages to a single prompt
        # Format: system message + user messages
        prompt_parts = []

        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')

            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")

        # Join all parts and add final prompt for assistant response
        prompt = "\n\n".join(prompt_parts)
        if not prompt.endswith("Assistant:"):
            prompt += "\n\nAssistant:"

        # Call the local LLM server
        try:
            response = requests.post(
                f"{self.base_url}/query",
                auth=HTTPBasicAuth(self.username, self.password),
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": kwargs.get('top_p', 0.95),
                },
                timeout=120,  # 2 minute timeout for generation
            )

            response.raise_for_status()
            result = response.json()

            # Extract the generated text
            generated_text = result.get('response', '').strip()

            logger.debug(f"Local LLM response: {generated_text[:100]}...")

            return ChatCompletion(generated_text)

        except requests.exceptions.Timeout:
            logger.error("Local LLM server request timed out")
            raise RuntimeError("Local LLM server request timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling local LLM server: {e}")
            raise RuntimeError(f"Failed to call local LLM server: {e}")
        except Exception as e:
            logger.error(f"Unexpected error with local LLM: {e}")
            raise RuntimeError(f"Unexpected error with local LLM: {e}")


class Chat:
    """Mimics OpenAI's chat API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.completions = ChatCompletions(base_url, username, password)


class LocalLLMClient:
    """
    Local LLM client that mimics the OpenAI client API.

    Usage:
        client = LocalLLMClient()
        response = client.chat.completions.create(
            model="gpt-4o",  # ignored
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"}
            ]
        )
        print(response.choices[0].message.content)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize the local LLM client.

        Args:
            base_url: Base URL of the local LLM server (default: from LLM_SERVER_URL env var)
            username: Username for authentication (default: from LLM_USERNAME env var)
            password: Password for authentication (default: from LLM_PASSWORD env var)

        Raises:
            ValueError: If required environment variables are not set
        """
        self.base_url = base_url or os.getenv('LLM_SERVER_URL')
        self.username = username or os.getenv('LLM_USERNAME')
        self.password = password or os.getenv('LLM_PASSWORD')

        if not self.base_url:
            raise ValueError(
                "LLM_SERVER_URL environment variable is required. "
                "Example: http://llm-server:8000"
            )

        if not self.username or not self.password:
            raise ValueError(
                "LLM_USERNAME and LLM_PASSWORD environment variables are required"
            )

        # Remove trailing slash from base_url
        self.base_url = self.base_url.rstrip('/')

        # Initialize chat API
        self.chat = Chat(self.base_url, self.username, self.password)

        logger.info(f"Local LLM client initialized with base URL: {self.base_url}")

    def health_check(self) -> bool:
        """
        Check if the local LLM server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get('status') == 'healthy'
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


def get_llm_client() -> LocalLLMClient:
    """
    Get a local LLM client instance.

    This is a convenience function that creates a new client with
    configuration from environment variables.

    Returns:
        LocalLLMClient instance
    """
    return LocalLLMClient()
