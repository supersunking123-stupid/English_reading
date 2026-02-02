"""
Log management module for retrieving and displaying test history.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from config import USERS_DIR, LOG_DIR


def get_user_logs(username: str) -> List[Dict[str, Any]]:
    """
    Get all logs (both article and test) for a user.

    Args:
        username: The username

    Returns:
        List of log dictionaries, sorted by date (newest first)
    """
    log_base_dir = USERS_DIR / username / LOG_DIR

    if not log_base_dir.exists():
        return []

    logs = []

    # Iterate through date directories
    for date_dir in sorted(log_base_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue

        # Iterate through ALL log files (test_*.json and article_*.json)
        for log_file in sorted(date_dir.glob("*.json"), reverse=True):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    log_data['file_path'] = str(log_file)
                    logs.append(log_data)
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
                continue

    return logs


def format_log_for_display(log_data: Dict[str, Any]) -> str:
    """
    Format a log entry for display.

    Args:
        log_data: Log data dictionary

    Returns:
        Formatted string for display
    """
    output = []

    status = log_data.get('status', 'completed')
    article_type = log_data.get('article_type', 'N/A')

    if status == 'generated':
        output.append(f"# Article Log - {log_data.get('timestamp', 'Unknown')}")
        output.append(f"\n**Type:** {article_type}")
        output.append(f"**Status:** Generated (Not yet completed)\n")
    else:
        output.append(f"# Test Log - {log_data.get('timestamp', 'Unknown')}")
        output.append(f"\n**Type:** {article_type}")
        output.append(f"**Score: {log_data.get('score', 'N/A')}/100**\n")

    output.append("## Article")
    output.append(log_data.get('article', 'N/A'))

    output.append("\n## Questions")
    questions = log_data.get('questions', [])
    user_answers = log_data.get('user_answers', [])
    item_analysis = log_data.get('item_analysis', [])

    # Display questions with or without answers based on status
    if user_answers and len(user_answers) > 0:
        # Show questions with answers (completed test)
        for i, (q, ans) in enumerate(zip(questions, user_answers), 1):
            output.append(f"\n### Question {i}")
            output.append(f"**Type:** {q.get('type', 'N/A')}")
            output.append(f"**Question:** {q.get('question', 'N/A')}")

            if q.get('type') == 'multiple_choice' and 'options' in q:
                output.append("**Options:**")
                for opt in q['options']:
                    output.append(f"  - {opt}")

            output.append(f"**Your Answer:** {ans}")
            output.append(f"**Correct Answer:** {q.get('correct_answer', 'N/A')}")

            # Add analysis if available
            if i - 1 < len(item_analysis):
                analysis = item_analysis[i - 1]
                correct = analysis.get('correct', False)
                status_mark = "✓ Correct" if correct else "✗ Incorrect"
                output.append(f"**Result:** {status_mark}")
                if 'feedback' in analysis:
                    output.append(f"**Feedback:** {analysis['feedback']}")
    else:
        # Show questions only (generated but not completed)
        for i, q in enumerate(questions, 1):
            output.append(f"\n### Question {i}")
            output.append(f"**Type:** {q.get('type', 'N/A')}")
            output.append(f"**Question:** {q.get('question', 'N/A')}")

            if q.get('type') == 'multiple_choice' and 'options' in q:
                output.append("**Options:**")
                for opt in q['options']:
                    output.append(f"  - {opt}")

    # Only show feedback and suggestions if available
    if log_data.get('overall_feedback'):
        output.append("\n## Overall Feedback")
        output.append(log_data.get('overall_feedback'))

    if log_data.get('suggestions'):
        output.append("\n## Suggestions")
        output.append(log_data.get('suggestions'))

    return "\n".join(output)


def get_score_history(username: str) -> List[tuple]:
    """
    Get score history for a user.

    Args:
        username: The username

    Returns:
        List of (timestamp, score) tuples
    """
    logs = get_user_logs(username)

    history = []
    for log in logs:
        timestamp = log.get('timestamp', '')
        score = log.get('score', 0)
        history.append((timestamp, score))

    return history
