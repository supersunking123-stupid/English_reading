"""
AI client adapter module providing unified interface for multiple AI providers.
"""

import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import anthropic
import openai
from dashscope import Generation


class AIClient(ABC):
    """Base class for AI clients with unified interface."""

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate content using AI model.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)

        Returns:
            Generated text content
        """
        pass


class AnthropicClient(AIClient):
    """Claude API client."""

    def __init__(self, model: str, api_key: str):
        super().__init__(model, api_key)
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = [{"role": "user", "content": prompt}]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class OpenAIClient(AIClient):
    """OpenAI GPT client."""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        super().__init__(model, api_key)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096
        )

        return response.choices[0].message.content


class DashScopeClient(AIClient):
    """Alibaba DashScope (Qwen) client."""

    def __init__(self, model: str, api_key: str):
        super().__init__(model, api_key)
        import dashscope
        dashscope.api_key = api_key

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = Generation.call(
            model=self.model,
            messages=messages,
            result_format='message'
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"DashScope API error: {response.message}")


def get_client(provider: str, model: str, api_key: str, base_url: Optional[str] = None) -> AIClient:
    """
    Factory method to create appropriate AI client.

    Args:
        provider: Provider name ('anthropic', 'openai', or 'dashscope')
        model: Model name
        api_key: API key
        base_url: Optional base URL for API endpoint

    Returns:
        AIClient instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = provider.lower()

    if provider == "anthropic":
        return AnthropicClient(model, api_key)
    elif provider == "openai":
        return OpenAIClient(model, api_key, base_url)
    elif provider == "dashscope":
        return DashScopeClient(model, api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def load_api_config(username: str) -> Optional[Dict[str, Any]]:
    """
    Load API configuration from user's api_key.txt file.

    Args:
        username: The username

    Returns:
        Dictionary with API configurations, or None if file doesn't exist
    """
    from config import USERS_DIR, API_KEY_FILE

    api_file = USERS_DIR / username / API_KEY_FILE

    if not api_file.exists() or api_file.stat().st_size == 0:
        return None

    try:
        with open(api_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError:
        return None


def save_api_config(username: str, config: Dict[str, Any]) -> bool:
    """
    Save API configuration to user's api_key.txt file.

    Args:
        username: The username
        config: API configuration dictionary

    Returns:
        True if saved successfully
    """
    from config import USERS_DIR, API_KEY_FILE

    api_file = USERS_DIR / username / API_KEY_FILE

    with open(api_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return True


def fetch_available_models(provider_type: str, api_key: str, base_url: Optional[str] = None) -> list:
    """
    Fetch available models from API provider.

    Args:
        provider_type: Provider type ('openai', 'dashscope', 'anthropic')
        api_key: API key
        base_url: Optional base URL for OpenAI-compatible APIs

    Returns:
        List of model names
    """
    try:
        if provider_type.lower() == 'openai':
            # Use OpenAI API to list models
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = openai.OpenAI(**kwargs)

            models = client.models.list()
            return [model.id for model in models.data]

        elif provider_type.lower() == 'dashscope':
            # DashScope doesn't have a public models list API
            # Return common Qwen models
            return [
                'qwen-max',
                'qwen-max-latest',
                'qwen-plus',
                'qwen-plus-latest',
                'qwen-turbo',
                'qwen-turbo-latest',
                'qwen-long',
                'qwen2.5-72b-instruct',
                'qwen2.5-32b-instruct',
                'qwen2.5-14b-instruct',
                'qwen2.5-7b-instruct'
            ]

        elif provider_type.lower() == 'anthropic':
            # Anthropic doesn't have a public models list API
            # Return known Claude models
            return [
                'claude-3-5-sonnet-20241022',
                'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ]

        else:
            return []

    except Exception as e:
        print(f"Error fetching models for {provider_type}: {e}")
        return []
