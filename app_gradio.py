"""
English Learning Application - Main Gradio Interface
"""

import gradio as gr
import json
from typing import List, Dict, Any, Optional

from config import DEFAULT_AGE, DEFAULT_LEXILE
from core.user_manager import (
    list_users, create_user, load_user_info, save_user_info, user_exists
)
from core.word_bank import (
    load_words, save_words, deduplicate_words, add_words, get_word_count
)
from core.ai_client import get_client, load_api_config, save_api_config
from core.content_generator import generate_article_and_questions
from core.evaluator import evaluate_answers, save_test_log
from core.log_manager import get_user_logs, format_log_for_display, get_score_history
from core.global_config import load_global_api_config, get_model_base_url


# Global state
current_user = None
current_article = None
current_questions = None
current_client = None
global_api_config = None  # Will be loaded at startup


def get_api_config_display():
    """Generate API configuration display text."""
    global global_api_config

    if not global_api_config:
        return "❌ 未找到API配置文件 / No API configuration found\n\n请在项目根目录创建 `.key_env` 文件 / Please create `.key_env` file in project root"

    lines = ["### ✅ 已加载全局API配置 / Global API Configuration Loaded\n"]

    for provider, config in global_api_config.items():
        models = config.get('models', [])
        lines.append(f"**{provider.upper()}**")
        lines.append(f"- 可用模型数 / Available models: {len(models)}")
        for model in models:
            lines.append(f"  - {model}")
        lines.append("")

    return "\n".join(lines)


def refresh_user_list():
    """Get list of users for dropdown."""
    users = list_users()
    return gr.Dropdown(choices=users, value=users[0] if users else None)


def handle_user_selection(username):
    """Handle existing user selection."""
    global current_user

    if not username:
        return "⚠️ 请选择用户 / Please select a user", DEFAULT_AGE, DEFAULT_LEXILE, ""

    current_user = username

    # Load existing user
    info = load_user_info(username)
    age = info.get('age', DEFAULT_AGE) if info else DEFAULT_AGE
    lexile = info.get('lexile_level', DEFAULT_LEXILE) if info else DEFAULT_LEXILE

    word_count = get_word_count(username)
    words_text = "\n".join(load_words(username))

    return (
        f"✓ 已加载用户 / Loaded user: {username} ({word_count} words)",
        age,  # Return as number, not string
        lexile,  # Return as number, not string
        words_text
    )


def handle_create_user(new_username):
    """Handle new user creation."""
    global current_user

    if not new_username or not new_username.strip():
        return "Please enter a username", gr.update(), ""

    new_username = new_username.strip()

    if user_exists(new_username):
        return f"✗ User '{new_username}' already exists! Please choose a different name.", gr.update(), ""

    # Create new user
    create_user(new_username)
    current_user = new_username

    # Refresh user list
    users = list_users()

    return (
        f"✓ Created new user: {new_username}",
        gr.update(choices=users, value=new_username),
        ""
    )


def save_user_profile(username, age, lexile, words_text):
    """Save user profile information."""
    if not username or username.strip() == "":
        return "⚠️ 请先选择或创建用户 / Please select or create a user first"

    try:
        username = username.strip()

        # Save user info
        age_int = int(age) if age else DEFAULT_AGE
        lexile_int = int(lexile) if lexile else DEFAULT_LEXILE
        save_user_info(username, age_int, lexile_int)

        # Save words
        if words_text:
            words = [w.strip() for w in words_text.split('\n') if w.strip()]
            save_words(username, words)
        else:
            save_words(username, [])

        word_count = get_word_count(username)
        return f"✓ 已保存用户配置 / Saved profile for {username} ({word_count} words in bank)"
    except Exception as e:
        return f"✗ 保存出错 / Error saving profile: {str(e)}"


def handle_deduplicate(username):
    """Deduplicate words in word bank."""
    if not username:
        return "Please select a user first", ""

    removed = deduplicate_words(username)
    words_text = "\n".join(load_words(username))
    return f"✓ Removed {removed} duplicate words", words_text


def get_provider_models():
    """Get available providers and models from global API config."""
    global global_api_config

    if not global_api_config:
        return gr.update(choices=[]), gr.update(choices=[])

    providers = list(global_api_config.keys())
    return gr.update(choices=providers, value=providers[0] if providers else None), gr.update(choices=[])


def update_model_choices(provider):
    """Update model choices based on selected provider."""
    global global_api_config

    if not provider or not global_api_config:
        return gr.update(choices=[])

    if provider in global_api_config and 'models' in global_api_config[provider]:
        models = global_api_config[provider]['models']
        return gr.update(choices=models, value=models[0] if models else None)

    return gr.update(choices=[])


def generate_content(username, provider, model):
    """Generate article and questions."""
    global current_article, current_questions, current_client, global_api_config

    if not username:
        return "⚠️ 请先选择用户 / Please select a user first", "", gr.update(visible=False), None, None, None, None, None

    if not provider or not model:
        return "⚠️ 请选择AI提供商和模型 / Please select AI provider and model", "", gr.update(visible=False), None, None, None, None, None

    try:
        # Load user info and words
        info = load_user_info(username)
        if not info:
            return "⚠️ 请先保存用户配置 / Please save user profile first", "", gr.update(visible=False), None, None, None, None, None

        words = load_words(username)

        # Get API key from global config
        if not global_api_config or provider not in global_api_config:
            return f"✗ 未找到 {provider} 的API配置 / API config not found for {provider}", "", gr.update(visible=False), None, None, None, None, None

        if 'api_key' not in global_api_config[provider]:
            return f"✗ 未找到 {provider} 的API密钥 / API key not found for {provider}", "", gr.update(visible=False), None, None, None, None, None

        api_key = global_api_config[provider]['api_key']

        # Get base URL if exists
        base_url = get_model_base_url(global_api_config, provider, model)

        # Create AI client
        current_client = get_client(provider, model, api_key, base_url)

        # Generate content
        result = generate_article_and_questions(
            words, info['age'], info['lexile_level'], current_client
        )

        if not result:
            return "✗ Failed to generate content", "", gr.update(visible=False), None, None, None

        current_article = result['article']
        current_questions = result['questions']

        # Build question UI components
        question_components = []
        for i, q in enumerate(current_questions):
            question_components.append(f"**Question {i+1}** ({q['type']})\n\n{q['question']}")

        word_info = f"({len(words)} words used)" if words else "(no word bank, difficulty based on Lexile {info['lexile_level']})"
        return (
            f"✓ 内容生成成功！/ Content generated successfully! {word_info}",
            current_article,
            gr.update(visible=True),
            *question_components
        )

    except Exception as e:
        return f"✗ 错误 / Error: {str(e)}", "", gr.update(visible=False), None, None, None, None, None


def submit_answers(username, ans1, ans2, ans3, ans4, ans5):
    """Submit and evaluate answers."""
    global current_article, current_questions, current_client

    if not current_questions or not current_client:
        return "Please generate content first", ""

    try:
        user_answers = [ans1, ans2, ans3, ans4, ans5]

        # Evaluate answers
        evaluation = evaluate_answers(current_questions, user_answers, current_client)

        if not evaluation:
            return "✗ Failed to evaluate answers", ""

        # Save log
        save_test_log(username, current_article, current_questions, user_answers, evaluation)

        # Format results
        result_text = f"# Test Results\n\n**Score: {evaluation['score']}/100**\n\n"
        result_text += f"## Item Analysis\n\n"

        for i, analysis in enumerate(evaluation['item_analysis'], 1):
            correct = analysis.get('correct', False)
            status = "✓" if correct else "✗"
            result_text += f"{status} **Question {i}**: {analysis.get('feedback', 'N/A')}\n\n"

        result_text += f"## Overall Feedback\n\n{evaluation['overall_feedback']}\n\n"
        result_text += f"## Suggestions\n\n{evaluation['suggestions']}"

        return "✓ Answers submitted and evaluated!", result_text

    except Exception as e:
        return f"✗ Error: {str(e)}", ""


def load_history(username):
    """Load test history for user."""
    if not username:
        return "Please select a user first", []

    logs = get_user_logs(username)

    if not logs:
        return "No test history found", []

    # Create list of log summaries
    log_choices = []
    for log in logs:
        timestamp = log.get('timestamp', 'Unknown')
        score = log.get('score', 'N/A')
        log_choices.append(f"{timestamp} - Score: {score}/100")

    return f"Found {len(logs)} test records", log_choices


def display_log_detail(username, selected_log):
    """Display detailed log."""
    if not username or not selected_log:
        return "Please select a log entry"

    logs = get_user_logs(username)

    # Find the selected log by timestamp
    for log in logs:
        timestamp = log.get('timestamp', 'Unknown')
        score = log.get('score', 'N/A')
        log_label = f"{timestamp} - Score: {score}/100"

        if log_label == selected_log:
            return format_log_for_display(log)

    return "Log not found"


def init_global_config():
    """Initialize global API configuration."""
    global global_api_config
    global_api_config = load_global_api_config()

    if global_api_config:
        print("✓ 成功加载全局API配置 / Global API configuration loaded successfully")
        print(f"可用提供商 / Available providers: {list(global_api_config.keys())}")
        for provider, config in global_api_config.items():
            models = config.get('models', [])
            print(f"  - {provider}: {len(models)} model(s)")
    else:
        print("⚠️ 未找到.key_env文件或格式错误 / .key_env file not found or invalid format")
        print("请在项目根目录创建.key_env文件 / Please create .key_env file in project root")


# Initialize global API configuration BEFORE building Gradio interface
init_global_config()


# Build Gradio interface
with gr.Blocks(title="English Learning System", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🎓 English Learning System")
    gr.Markdown("AI-powered English reading practice with personalized content generation")

    with gr.Tabs():
        # Tab 1: User Management
        with gr.Tab("👤 User Management"):
            gr.Markdown("## 用户管理 / User Management")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📋 选择已有用户 / Select Existing User")
                    user_dropdown = gr.Dropdown(
                        choices=list_users(),
                        label="选择用户 / Select User",
                        interactive=True
                    )
                    refresh_btn = gr.Button("🔄 刷新用户列表 / Refresh", size="sm")

                with gr.Column():
                    gr.Markdown("### ➕ 创建新用户 / Create New User")
                    new_user_input = gr.Textbox(
                        label="新用户名 / New Username",
                        placeholder="例如: student1",
                        interactive=True
                    )
                    create_user_btn = gr.Button("✨ 创建用户 / Create User", variant="primary")

            user_status = gr.Textbox(label="状态 / Status", interactive=False)

            gr.Markdown("---")
            gr.Markdown("### ⚙️ 用户配置 / User Configuration")

            with gr.Row():
                with gr.Column():
                    age_input = gr.Number(
                        label="年龄 / Age",
                        value=DEFAULT_AGE,
                        precision=0,
                        info="学生年龄"
                    )
                    lexile_input = gr.Number(
                        label="蓝思值 / Lexile Level",
                        value=DEFAULT_LEXILE,
                        precision=0,
                        info="阅读难度等级 (200-1700)"
                    )

            save_profile_btn = gr.Button("💾 保存配置 / Save Profile", variant="primary")
            save_status = gr.Textbox(label="保存状态 / Save Status", interactive=False)

            gr.Markdown("---")
            gr.Markdown("### 🔑 API 配置信息 / API Configuration")
            api_status = gr.Markdown("正在加载... / Loading...")

        # Tab 2: Word Bank
        with gr.Tab("📚 Word Bank"):
            word_bank_box = gr.TextArea(
                label="单词库 / Word Bank (one word per line)",
                placeholder="apple\nbanana\ncomputer",
                lines=15,
                info="留空则完全依据蓝思值生成文章 / Leave empty to generate articles based purely on Lexile level"
            )

            with gr.Row():
                dedupe_btn = gr.Button("🔧 Remove Duplicates")
                dedupe_status = gr.Textbox(label="Status", interactive=False)

        # Tab 3: Learning
        with gr.Tab("✏️ Start Learning"):
            with gr.Row():
                provider_dropdown = gr.Dropdown(label="AI Provider", choices=[])
                model_dropdown = gr.Dropdown(label="Model", choices=[])

            generate_btn = gr.Button("🚀 Generate Article & Questions", variant="primary")
            gen_status = gr.Textbox(label="Status", interactive=False)

            article_box = gr.Textbox(label="Article", lines=10, interactive=False)

            with gr.Column(visible=False) as questions_section:
                gr.Markdown("## Questions")

                q1_text = gr.Markdown()
                a1_input = gr.Textbox(label="Your Answer", placeholder="Enter your answer")

                q2_text = gr.Markdown()
                a2_input = gr.Textbox(label="Your Answer", placeholder="Enter your answer")

                q3_text = gr.Markdown()
                a3_input = gr.Textbox(label="Your Answer", placeholder="Enter your answer")

                q4_text = gr.Markdown()
                a4_input = gr.Textbox(label="Your Answer", placeholder="Enter your answer")

                q5_text = gr.Markdown()
                a5_input = gr.Textbox(label="Your Answer", placeholder="Enter your answer")

                submit_btn = gr.Button("📝 Submit Answers", variant="primary")

            submit_status = gr.Textbox(label="Status", interactive=False)
            results_box = gr.Markdown()

        # Tab 4: History
        with gr.Tab("📊 Learning History"):
            history_user = gr.Textbox(label="Username", interactive=False)
            load_history_btn = gr.Button("📖 Load History")
            history_status = gr.Textbox(label="Status", interactive=False)

            log_selector = gr.Radio(label="Select Test Record", choices=[])
            log_detail = gr.Markdown()

    # Event handlers
    refresh_btn.click(
        fn=lambda: gr.update(choices=list_users()),
        outputs=user_dropdown
    )

    create_user_btn.click(
        fn=handle_create_user,
        inputs=new_user_input,
        outputs=[user_status, user_dropdown, new_user_input]
    )

    user_dropdown.change(
        fn=handle_user_selection,
        inputs=user_dropdown,
        outputs=[user_status, age_input, lexile_input, word_bank_box]
    )

    save_profile_btn.click(
        fn=save_user_profile,
        inputs=[user_dropdown, age_input, lexile_input, word_bank_box],
        outputs=save_status
    )

    dedupe_btn.click(
        fn=handle_deduplicate,
        inputs=user_dropdown,
        outputs=[dedupe_status, word_bank_box]
    )

    provider_dropdown.change(
        fn=update_model_choices,
        inputs=provider_dropdown,
        outputs=model_dropdown
    )

    generate_btn.click(
        fn=generate_content,
        inputs=[user_dropdown, provider_dropdown, model_dropdown],
        outputs=[gen_status, article_box, questions_section, q1_text, q2_text, q3_text, q4_text, q5_text]
    )

    submit_btn.click(
        fn=submit_answers,
        inputs=[user_dropdown, a1_input, a2_input, a3_input, a4_input, a5_input],
        outputs=[submit_status, results_box]
    )

    # History tab
    user_dropdown.change(
        fn=lambda x: x,
        inputs=user_dropdown,
        outputs=history_user
    )

    load_history_btn.click(
        fn=load_history,
        inputs=history_user,
        outputs=[history_status, log_selector]
    )

    log_selector.change(
        fn=display_log_detail,
        inputs=[history_user, log_selector],
        outputs=log_detail
    )

    # Load API configuration on app startup
    app.load(
        fn=lambda: (get_api_config_display(), *get_provider_models()),
        outputs=[api_status, provider_dropdown, model_dropdown]
    )


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)
