"""
Global configuration loader for shared API keys.
"""

import configparser
from pathlib import Path
from typing import Dict, Optional


def load_global_api_config() -> Optional[Dict]:
    """
    Load global API configuration from .key_env file.

    Returns:
        Dictionary with API configurations, keyed by section name (e.g., ALIYUN, NVIDIA)
        Structure:
        {
            'ALIYUN': {
                'provider_type': 'dashscope',
                'api_key': '...',
                'api_base': '...',
                'models': ['qwen-max', 'qwen-plus', ...]
            },
            'NVIDIA': {
                'provider_type': 'openai',
                'api_key': '...',
                'api_base': '...',
                'models': ['nvidia/llama-3.1-nemotron-70b-instruct', ...]
            }
        }
    """
    config_file = Path(__file__).parent.parent / ".key_env"

    if not config_file.exists():
        return None

    try:
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')

        api_config = {}

        # Map section names to provider types
        provider_mapping = {
            'ALIYUN': 'dashscope',
            'NVIDIA': 'openai',  # NVIDIA uses OpenAI-compatible API
            'ANTIG': 'openai',   # ANTIG uses OpenAI-compatible API
            'DeepSeek': 'openai' # DeepSeek uses OpenAI-compatible API
        }

        for section in config.sections():
            if section in provider_mapping:
                provider_type = provider_mapping[section]
                api_key = config.get(section, 'API_KEY', fallback=None)
                api_base = config.get(section, 'API_BASE', fallback=None)
                model_names = config.get(section, 'MODEL_NAME', fallback=section.lower())

                if api_key:
                    # Parse model names - can be comma-separated
                    models = [m.strip() for m in model_names.split(',') if m.strip()]

                    # Store config under section name (e.g., ALIYUN, NVIDIA)
                    api_config[section] = {
                        'provider_type': provider_type,
                        'api_key': api_key,
                        'api_base': api_base,
                        'models': models
                    }

        return api_config if api_config else None

    except Exception as e:
        print(f"Error loading global API config: {e}")
        return None


def get_model_base_url(api_config: Dict, provider: str, model: str) -> Optional[str]:
    """
    Get the base URL for a specific provider.

    Args:
        api_config: API configuration dictionary
        provider: Provider section name (e.g., ALIYUN, NVIDIA)
        model: Model name (not used currently, kept for backward compatibility)

    Returns:
        Base URL string or None
    """
    if provider not in api_config:
        return None

    return api_config[provider].get('api_base')
