"""
Prompt templates for article and question generation.
"""

from typing import List


def get_article_generation_prompt(words: List[str], age: int, lexile: int, article_type: str = "Story") -> tuple:
    """
    Generate prompts for article and question creation.

    Args:
        words: List of words to include (can be empty)
        age: User's age
        lexile: User's Lexile level
        article_type: Type of article (Story, Science, Nature, History)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are a professional English teacher who excels at creating appropriate reading materials for beginners. You must return valid JSON format only."""

    # Define article type descriptions
    type_descriptions = {
        "Story": "an engaging narrative story with characters and plot",
        "Science": "a scientific article explaining a concept or phenomenon",
        "Nature": "an article about nature, animals, plants, or environmental topics",
        "History": "a historical article about events, people, or periods from the past"
    }

    type_desc = type_descriptions.get(article_type, type_descriptions["Story"])

    # Check if word bank is empty
    if not words or len(words) == 0:
        # Generate article based purely on Lexile level
        user_prompt = f"""Please generate an English reading article and 5 test questions based on the following information:

User Information:
- Age: {age} years old
- Lexile Level: {lexile} (grammar and sentence complexity indicator)
- Article Type: {article_type} - Create {type_desc}

Requirements:
1. Article length: 150-250 words
2. The article MUST be {type_desc}
3. Vocabulary and grammar difficulty should STRICTLY match the Lexile level {lexile}
4. Content should be age-appropriate, interesting, and educational for {age}-year-old students
5. Choose appropriate vocabulary and sentence structures based on Lexile {lexile}:
   - Lexile 200-400: Simple present/past tense, basic vocabulary, short sentences
   - Lexile 400-600: Introduction of complex sentences, common phrasal verbs
   - Lexile 600-800: More varied tenses, intermediate vocabulary, compound sentences
   - Lexile 800-1000: Advanced grammar structures, academic vocabulary
   - Lexile 1000+: Complex syntax, sophisticated vocabulary, nuanced expressions

5 Test Questions Requirements:
- 2 multiple choice questions (4 options A/B/C/D)
- 2 fill-in-the-blank questions (test vocabulary and grammar)
- 1 true/false question

Please return in JSON format:
{{
  "article": "article content here",
  "questions": [
    {{
      "type": "multiple_choice",
      "question": "question text",
      "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
      "correct_answer": "A"
    }},
    {{
      "type": "fill_blank",
      "question": "question text (use ___ for blank)",
      "correct_answer": "answer"
    }},
    {{
      "type": "true_false",
      "question": "question text",
      "correct_answer": true
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text."""
    else:
        # Generate article using word bank
        words_str = ", ".join(words[:50])  # Limit to first 50 words to avoid too long prompt
        if len(words) > 50:
            words_str += f" (and {len(words) - 50} more words)"

        user_prompt = f"""Please generate an English reading article and 5 test questions based on the following information:

User Information:
- Age: {age} years old
- Lexile Level: {lexile} (grammar and sentence complexity indicator)
- Article Type: {article_type} - Create {type_desc}

Word Bank: {words_str}

Requirements:
1. Article length: 150-250 words
2. The article MUST be {type_desc}
3. Must use at least 80% of the words from the word bank
4. Grammar difficulty should match the Lexile level
5. Content should be age-appropriate, interesting, and educational

5 Test Questions Requirements:
- 2 multiple choice questions (4 options A/B/C/D)
- 2 fill-in-the-blank questions (test vocabulary and grammar)
- 1 true/false question

Please return in JSON format:
{{
  "article": "article content here",
  "questions": [
    {{
      "type": "multiple_choice",
      "question": "question text",
      "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
      "correct_answer": "A"
    }},
    {{
      "type": "fill_blank",
      "question": "question text (use ___ for blank)",
      "correct_answer": "answer"
    }},
    {{
      "type": "true_false",
      "question": "question text",
      "correct_answer": true
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

    return system_prompt, user_prompt
