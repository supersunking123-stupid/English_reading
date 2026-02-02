# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI-powered English learning system that generates personalized reading materials and comprehension questions based on user age, Lexile reading level, custom word banks, and article type preferences. The application supports multiple AI providers through a unified interface and has been migrated from Gradio to Streamlit.

## Environment Setup

**Python Version**: Python 3.12

**Virtual Environment**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Start Streamlit web interface (default port 7860)
streamlit run app.py --server.port=7860 --server.address=0.0.0.0
```

The application will be accessible at `http://0.0.0.0:7860`

**Legacy Gradio Version**: The original Gradio version is preserved in `app_gradio.py` for reference.

## API Configuration

**Required**: Create a `.key_env` file in the project root with API credentials:

```ini
[ALIYUN]
API_KEY = your_dashscope_key
API_BASE = https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME = qwen-max,qwen-plus,qwen-turbo

[NVIDIA]
API_KEY = your_nvidia_key
API_BASE = https://integrate.api.nvidia.com/v1
MODEL_NAME = nvidia/llama-3.1-nemotron-70b-instruct

[DeepSeek]
API_KEY = your_deepseek_key
API_BASE = https://api.deepseek.com/v1
MODEL_NAME = deepseek-chat

[ANTIG]
API_KEY = your_antig_key
API_BASE = http://192.168.237.1:8045/v1
MODEL_NAME = antig
```

**Configuration Details**:
- The `.key_env` file uses INI format and is parsed by `core/global_config.py:load_global_api_config()`
- Section names (ALIYUN, NVIDIA, DeepSeek, ANTIG) are displayed as-is in the UI
- `MODEL_NAME` can be comma-separated for multiple models, or left for dynamic API query
- Each section is mapped to a provider type (dashscope, openai) internally

## Architecture

### UI Framework - Streamlit

The application uses **Streamlit** for the web interface:

- **State Management**: `st.session_state` for all application state (replaces global variables)
- **Tab Navigation**: Four main tabs - User Management, Word Bank, Start Learning, Learning History
- **Event Handling**: Inline button handlers with `st.button()` and `on_change` callbacks
- **Dynamic Updates**: `st.rerun()` for UI refresh when needed

### Multi-AI Provider System

The application uses an adapter pattern to support multiple AI providers:

- **Base**: `AIClient` abstract class in `core/ai_client.py` defines the `generate()` interface
- **Implementations**: `AnthropicClient`, `OpenAIClient`, `DashScopeClient` implement provider-specific APIs
- **Factory**: `get_client()` creates appropriate client based on provider type
- **Dynamic Model Discovery**: `fetch_available_models()` queries API providers for available models
- **OpenAI-Compatible APIs**: NVIDIA, DeepSeek, and ANTIG all use `OpenAIClient` with custom `base_url` parameters

### Configuration Loading Flow

1. **Global config** (`.key_env`) is loaded once at startup via `init_session_state()`
2. **Provider selection** displays section names from `.key_env` (e.g., ALIYUN, NVIDIA)
3. **Model list** is dynamically fetched via API for OpenAI-compatible providers
4. **User preferences** are saved and restored per user (`users/{username}/preferences.txt`)

### User Data Structure

User data is stored in `users/{username}/` directories:
- `user_info.txt` - Age and lexile_level (key: value format)
- `word_bank.txt` - One word per line
- `preferences.txt` - Last selected AI provider and model
- `log/YYYY-MM-DD/` - Directory containing timestamped logs (JSON format)
  - `article_*.json` - Generated articles (not yet completed)
  - `test_*.json` - Completed tests with answers and evaluation

### Content Generation Pipeline

1. User selects:
   - Article type (Story, Science, Nature, History)
   - AI provider and model
2. System loads user profile and word bank
3. `generate_article_and_questions()` (`core/content_generator.py`) creates:
   - Article incorporating word bank at appropriate Lexile level and type
   - 5 comprehension questions (2 multiple choice, 2 fill-in-blank, 1 true/false)
4. System saves article log immediately (`save_article_log()`)
5. User answers questions (optional)
6. `evaluate_answers()` (`core/evaluator.py`) scores responses and provides feedback
7. Results saved to `users/{username}/log/{date}/test_{timestamp}.json`

### Document Export System

The `core/document_exporter.py` module handles Word document generation:

- **create_article_document()**: Generates practice worksheet (article + questions)
- **create_article_with_answers_document()**: Generates complete results with feedback
- **Features**:
  - Article text: 14pt Arial (larger for readability)
  - Questions: 12pt Arial with proper formatting
  - Multiple choice questions include all options in bullet format
  - Automatic inclusion of correct answers and feedback in results

### Logging System

Two-tier logging system:

**Generated Logs** (`article_*.json`):
- Status: `"generated"`
- Saved when article is created
- Contains: article, questions, article_type
- No answers or evaluation

**Completed Logs** (`test_*.json`):
- Status: `"completed"`
- Saved when answers are submitted
- Contains: article, questions, answers, score, feedback, article_type

### Prompt System

Prompts are centralized in `prompts/` directory:
- `article_generation.py` - Article and question generation prompts with article type support
- `evaluation.py` - Answer evaluation prompts

## Key Features

### User Management
- Create and select users
- Configure age and Lexile level
- Automatic user data loading on selection

### Word Bank Management
- Add/edit custom vocabulary
- Automatic deduplication
- Optional (can generate articles without word bank)

### AI Provider Selection
- Display provider names from `.key_env` section headers
- Dynamic model list fetched from API
- Remember last selection per user
- Model list caching for performance

### Article Type Selection
- **Story**: Narrative with characters and plot
- **Science**: Scientific concepts and phenomena
- **Nature**: Animals, plants, environmental topics
- **History**: Historical events, people, periods

### Learning History
- View all generated articles (completed or not)
- Status indicators: 📝 Generated vs ✅ Completed
- Download any historical record as .docx
- Full detail view with questions and feedback

### Document Export
- Download practice worksheets (.docx)
- Download complete results with evaluation
- Available from Learning tab and History tab
- Professional formatting with larger article text

## Key Dependencies

- **UI Framework**: `streamlit` (primary web interface)
- **AI Services**: `anthropic`, `openai`, `dashscope`
- **Document Generation**: `python-docx`, `lxml`
- **Config Parsing**: `configparser` for `.key_env` INI format
- **Data**: `pandas`, `numpy` (available but not heavily used currently)

## Important Implementation Details

**OpenAI-Compatible Providers**: When adding new OpenAI-compatible providers, add them to `provider_mapping` in `core/global_config.py` with `'openai'` as the value. The system will automatically use `OpenAIClient` with the provider's custom `API_BASE`.

**Lexile Levels**: Lexile is a reading difficulty metric (200-1700). Articles are generated to match the user's Lexile level, with word bank vocabulary incorporated naturally.

**Word Bank Behavior**: If word bank is empty, articles are generated purely based on Lexile level and article type without vocabulary constraints.

**Session State Keys**:
- `current_user`, `current_article`, `current_questions`, `current_client`
- `user_age`, `user_lexile`, `word_bank_text`
- `selected_provider`, `selected_model`, `cached_models`
- `log_list`, `last_evaluation`, `last_answers`

**Model Caching**: Models are cached per provider in `st.session_state.cached_models` to avoid repeated API calls. Use the "🔄 Refresh Models" button to reload.

## File Structure

```
.
├── app.py                      # Main Streamlit application
├── app_gradio.py              # Legacy Gradio version (backup)
├── config.py                   # Configuration constants
├── .key_env                   # API credentials (not committed)
├── core/
│   ├── ai_client.py           # AI provider adapters and model fetching
│   ├── content_generator.py  # Article and question generation
│   ├── evaluator.py           # Answer evaluation and logging
│   ├── log_manager.py         # Log retrieval and formatting
│   ├── user_manager.py        # User CRUD and preferences
│   ├── word_bank.py           # Word bank management
│   ├── global_config.py       # Global API configuration loader
│   └── document_exporter.py   # Word document generation
├── prompts/
│   ├── article_generation.py # Article generation prompts
│   └── evaluation.py          # Evaluation prompts
└── users/
    └── {username}/
        ├── user_info.txt
        ├── word_bank.txt
        ├── preferences.txt
        └── log/
            └── YYYY-MM-DD/
                ├── article_*.json
                └── test_*.json
```

## Development Notes

- Always use `st.session_state` for state management in Streamlit
- Call `st.rerun()` when state changes require UI refresh
- Use unique `key` parameters for Streamlit widgets to avoid conflicts
- Article and test logs are separate to preserve all generated content
- Multiple choice questions must include `options` field for proper display
