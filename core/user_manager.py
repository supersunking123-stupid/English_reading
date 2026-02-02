"""
User management module for creating, loading, and managing user profiles.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
from config import USERS_DIR, USER_INFO_FILE, API_KEY_FILE, WORD_BANK_FILE, LOG_DIR


def list_users() -> List[str]:
    """
    List all existing users.

    Returns:
        List of usernames
    """
    if not USERS_DIR.exists():
        return []

    users = [d.name for d in USERS_DIR.iterdir() if d.is_dir()]
    return sorted(users)


def create_user(username: str) -> bool:
    """
    Create a new user with directory structure.

    Args:
        username: The username to create

    Returns:
        True if created successfully, False if user already exists
    """
    user_dir = USERS_DIR / username

    if user_dir.exists():
        return False

    # Create user directory structure
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / LOG_DIR).mkdir(exist_ok=True)

    # Create empty files
    (user_dir / USER_INFO_FILE).touch()
    (user_dir / API_KEY_FILE).touch()
    (user_dir / WORD_BANK_FILE).touch()

    return True


def load_user_info(username: str) -> Optional[Dict[str, int]]:
    """
    Load user information (age and lexile level).

    Args:
        username: The username to load

    Returns:
        Dictionary with 'age' and 'lexile_level', or None if user doesn't exist
    """
    user_dir = USERS_DIR / username
    info_file = user_dir / USER_INFO_FILE

    if not info_file.exists():
        return None

    info = {}
    with open(info_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key == 'age':
                    info['age'] = int(value)
                elif key == 'lexile_level':
                    info['lexile_level'] = int(value)

    return info if info else None


def save_user_info(username: str, age: int, lexile: int) -> bool:
    """
    Save user information to file.

    Args:
        username: The username
        age: User's age
        lexile: User's Lexile level

    Returns:
        True if saved successfully
    """
    user_dir = USERS_DIR / username

    if not user_dir.exists():
        create_user(username)

    info_file = user_dir / USER_INFO_FILE

    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(f"age: {age}\n")
        f.write(f"lexile_level: {lexile}\n")

    return True


def get_user_dir(username: str) -> Path:
    """
    Get the directory path for a user.

    Args:
        username: The username

    Returns:
        Path object for the user's directory
    """
    return USERS_DIR / username


def user_exists(username: str) -> bool:
    """
    Check if a user exists.

    Args:
        username: The username to check

    Returns:
        True if user exists
    """
    return (USERS_DIR / username).exists()


def save_user_preferences(username: str, provider: str, model: str) -> bool:
    """
    Save user's last selected AI provider and model.

    Args:
        username: The username
        provider: AI provider name
        model: Model name

    Returns:
        True if saved successfully
    """
    user_dir = USERS_DIR / username

    if not user_dir.exists():
        return False

    pref_file = user_dir / "preferences.txt"

    with open(pref_file, 'w', encoding='utf-8') as f:
        f.write(f"provider: {provider}\n")
        f.write(f"model: {model}\n")

    return True


def load_user_preferences(username: str) -> Optional[Dict[str, str]]:
    """
    Load user's last selected AI provider and model.

    Args:
        username: The username

    Returns:
        Dictionary with 'provider' and 'model', or None if not found
    """
    user_dir = USERS_DIR / username
    pref_file = user_dir / "preferences.txt"

    if not pref_file.exists():
        return None

    prefs = {}
    with open(pref_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key in ['provider', 'model']:
                    prefs[key] = value

    return prefs if prefs else None
