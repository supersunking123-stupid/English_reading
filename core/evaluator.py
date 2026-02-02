"""
Evaluation module for grading answers and saving test logs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.ai_client import AIClient
from prompts.evaluation import get_evaluation_prompt
from config import USERS_DIR, LOG_DIR


def evaluate_answers(
    questions: List[Dict[str, Any]],
    user_answers: List[str],
    client: AIClient,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Evaluate user's answers using AI.

    Args:
        questions: List of question dictionaries
        user_answers: List of user's answers
        client: AI client instance
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary with evaluation results, or None if failed
    """
    system_prompt, user_prompt = get_evaluation_prompt(questions, user_answers)

    for attempt in range(max_retries):
        try:
            response = client.generate(user_prompt, system_prompt)

            # Try to extract JSON from response
            from core.content_generator import parse_json_response
            data = parse_json_response(response)

            # Validate response structure
            if validate_evaluation_response(data):
                return data
            else:
                print(f"Attempt {attempt + 1}: Invalid evaluation structure, retrying...")

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                return None

    return None


def validate_evaluation_response(data: Dict[str, Any]) -> bool:
    """
    Validate the structure of evaluation response.

    Args:
        data: Response data dictionary

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    required_keys = ['score', 'item_analysis', 'overall_feedback', 'suggestions']
    if not all(key in data for key in required_keys):
        return False

    # Validate score
    if not isinstance(data['score'], (int, float)) or data['score'] < 0 or data['score'] > 100:
        return False

    # Validate item_analysis
    if not isinstance(data['item_analysis'], list):
        return False

    return True


def save_article_log(
    username: str,
    article: str,
    questions: List[Dict[str, Any]],
    article_type: str = "Story"
) -> str:
    """
    Save article generation log (without answers/evaluation).

    Args:
        username: The username
        article: The article content
        questions: List of questions
        article_type: Type of article

    Returns:
        Timestamp ID of the saved log
    """
    # Create log directory with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = USERS_DIR / username / LOG_DIR / today
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%H-%M-%S")
    log_file = log_dir / f"article_{timestamp}.json"

    # Prepare log data
    full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "timestamp": full_timestamp,
        "article": article,
        "questions": questions,
        "article_type": article_type,
        "status": "generated",  # Status: generated, completed
        "user_answers": None,
        "score": None,
        "item_analysis": None,
        "overall_feedback": None,
        "suggestions": None
    }

    # Save to file
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    return full_timestamp


def save_test_log(
    username: str,
    article: str,
    questions: List[Dict[str, Any]],
    user_answers: List[str],
    evaluation: Dict[str, Any],
    article_type: str = "Story"
) -> bool:
    """
    Save test log to user's log directory.

    Args:
        username: The username
        article: The article content
        questions: List of questions
        user_answers: List of user's answers
        evaluation: Evaluation results
        article_type: Type of article

    Returns:
        True if saved successfully
    """
    # Create log directory with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = USERS_DIR / username / LOG_DIR / today
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%H-%M-%S")
    log_file = log_dir / f"test_{timestamp}.json"

    # Prepare log data
    log_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "article": article,
        "questions": questions,
        "article_type": article_type,
        "status": "completed",
        "user_answers": user_answers,
        "score": evaluation['score'],
        "item_analysis": evaluation['item_analysis'],
        "overall_feedback": evaluation['overall_feedback'],
        "suggestions": evaluation['suggestions']
    }

    # Save to file
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    return True
