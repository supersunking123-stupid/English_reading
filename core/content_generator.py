"""
Content generation module for creating articles and questions.
"""

import json
import re
from typing import List, Dict, Any, Optional
from core.ai_client import AIClient
from prompts.article_generation import get_article_generation_prompt


def generate_article_and_questions(
    words: List[str],
    age: int,
    lexile: int,
    client: AIClient,
    article_type: str = "Story",
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Generate reading article and test questions.

    Args:
        words: List of words to use
        age: User's age
        lexile: User's Lexile level
        client: AI client instance
        article_type: Type of article (Story, Science, Nature, History)
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary with 'article' and 'questions', or None if failed
    """
    system_prompt, user_prompt = get_article_generation_prompt(words, age, lexile, article_type)

    for attempt in range(max_retries):
        try:
            response = client.generate(user_prompt, system_prompt)

            # Try to extract JSON from response
            data = parse_json_response(response)

            # Validate response structure
            if validate_article_response(data):
                return data
            else:
                print(f"Attempt {attempt + 1}: Invalid response structure, retrying...")

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                return None

    return None


def parse_json_response(response: str) -> Dict[str, Any]:
    """
    Parse JSON from AI response, handling various formats.

    Args:
        response: Raw response text

    Returns:
        Parsed JSON dictionary

    Raises:
        json.JSONDecodeError: If JSON cannot be parsed
    """
    # Try direct JSON parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to find JSON object in response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))

    raise json.JSONDecodeError("No valid JSON found in response", response, 0)


def validate_article_response(data: Dict[str, Any]) -> bool:
    """
    Validate the structure of article generation response.

    Args:
        data: Response data dictionary

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    # Check for required keys
    if 'article' not in data or 'questions' not in data:
        return False

    # Validate article
    if not isinstance(data['article'], str) or len(data['article']) < 50:
        return False

    # Validate questions
    questions = data['questions']
    if not isinstance(questions, list) or len(questions) != 5:
        return False

    # Validate each question
    for q in questions:
        if not isinstance(q, dict):
            return False

        required_keys = ['type', 'question', 'correct_answer']
        if not all(key in q for key in required_keys):
            return False

        # Type-specific validation
        if q['type'] == 'multiple_choice':
            if 'options' not in q or not isinstance(q['options'], list):
                return False
            if len(q['options']) != 4:
                return False

        elif q['type'] not in ['fill_blank', 'true_false']:
            return False

    return True
