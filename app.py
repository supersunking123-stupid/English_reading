"""
English Learning Application - Streamlit Interface
"""

import streamlit as st
import json
from typing import List, Dict, Any, Optional

from config import DEFAULT_AGE, DEFAULT_LEXILE
from core.user_manager import (
    list_users, create_user, load_user_info, save_user_info, user_exists,
    save_user_preferences, load_user_preferences
)
from core.word_bank import (
    load_words, save_words, deduplicate_words, add_words, get_word_count
)
from core.ai_client import get_client, load_api_config, save_api_config, fetch_available_models
from core.content_generator import generate_article_and_questions
from core.evaluator import evaluate_answers, save_test_log, save_article_log
from core.log_manager import get_user_logs, format_log_for_display, get_score_history
from core.global_config import load_global_api_config, get_model_base_url
from core.document_exporter import create_article_document, create_article_with_answers_document
from datetime import datetime


def init_session_state():
    """Initialize session state variables."""
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'current_article' not in st.session_state:
        st.session_state.current_article = None
    if 'current_questions' not in st.session_state:
        st.session_state.current_questions = None
    if 'current_client' not in st.session_state:
        st.session_state.current_client = None
    if 'global_api_config' not in st.session_state:
        st.session_state.global_api_config = load_global_api_config()
    if 'user_age' not in st.session_state:
        st.session_state.user_age = DEFAULT_AGE
    if 'user_lexile' not in st.session_state:
        st.session_state.user_lexile = DEFAULT_LEXILE
    if 'word_bank_text' not in st.session_state:
        st.session_state.word_bank_text = ""
    if 'word_bank_key' not in st.session_state:
        st.session_state.word_bank_key = 0
    if 'log_list' not in st.session_state:
        st.session_state.log_list = []
    if 'selected_provider' not in st.session_state:
        st.session_state.selected_provider = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = None
    if 'cached_models' not in st.session_state:
        st.session_state.cached_models = {}  # Cache models per provider
    if 'last_evaluation' not in st.session_state:
        st.session_state.last_evaluation = None
    if 'last_answers' not in st.session_state:
        st.session_state.last_answers = None


def get_api_config_display():
    """Generate API configuration display text."""
    global_api_config = st.session_state.global_api_config

    if not global_api_config:
        return "❌ 未找到API配置文件 / No API configuration found\n\n请在项目根目录创建 `.key_env` 文件 / Please create `.key_env` file in project root"

    lines = ["### ✅ 已加载全局API配置 / Global API Configuration Loaded\n"]

    for section_name, config in global_api_config.items():
        models = config.get('models', [])
        provider_type = config.get('provider_type', 'unknown')
        lines.append(f"**{section_name}** (类型: {provider_type})")
        lines.append(f"- 可用模型数 / Available models: {len(models)}")
        for model in models:
            lines.append(f"  - {model}")
        lines.append("")

    return "\n".join(lines)


def load_user_data(username):
    """Load user data when user is selected."""
    if not username:
        return

    st.session_state.current_user = username

    # Load user info
    info = load_user_info(username)
    st.session_state.user_age = info.get('age', DEFAULT_AGE) if info else DEFAULT_AGE
    st.session_state.user_lexile = info.get('lexile_level', DEFAULT_LEXILE) if info else DEFAULT_LEXILE

    # Load word bank
    words = load_words(username)
    st.session_state.word_bank_text = "\n".join(words)

    # Load user preferences (last selected provider and model)
    prefs = load_user_preferences(username)
    if prefs:
        st.session_state.selected_provider = prefs.get('provider')
        st.session_state.selected_model = prefs.get('model')


def main():
    """Main Streamlit application."""
    # Page config
    st.set_page_config(
        page_title="English Learning System",
        page_icon="🎓",
        layout="wide"
    )

    # Initialize session state
    init_session_state()

    # Header
    st.title("🎓 English Learning System")
    st.markdown("AI-powered English reading practice with personalized content generation")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 User Management",
        "📚 Word Bank",
        "✏️ Start Learning",
        "📊 Learning History"
    ])

    # Tab 1: User Management
    with tab1:
        st.markdown("## 用户管理 / User Management")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📋 选择已有用户 / Select Existing User")
            users = list_users()

            # Determine default index
            if users:
                if st.session_state.current_user and st.session_state.current_user in users:
                    default_index = users.index(st.session_state.current_user)
                else:
                    default_index = 0
                    # Auto-load first user on initial load
                    if not st.session_state.current_user:
                        load_user_data(users[0])
            else:
                default_index = 0

            selected_user = st.selectbox(
                "选择用户 / Select User",
                options=users,
                index=default_index,
                key="user_selector"
            )

            # Load user data when selection changes
            if selected_user and selected_user != st.session_state.current_user:
                load_user_data(selected_user)
                st.rerun()

            if st.button("🔄 刷新用户列表 / Refresh"):
                st.rerun()

        with col2:
            st.markdown("### ➕ 创建新用户 / Create New User")
            new_username = st.text_input(
                "新用户名 / New Username",
                placeholder="例如: student1",
                key="new_user_input"
            )

            if st.button("✨ 创建用户 / Create User", type="primary"):
                if not new_username or not new_username.strip():
                    st.error("Please enter a username")
                elif user_exists(new_username.strip()):
                    st.error(f"✗ User '{new_username}' already exists! Please choose a different name.")
                else:
                    create_user(new_username.strip())
                    st.session_state.current_user = new_username.strip()
                    st.success(f"✓ Created new user: {new_username}")
                    st.rerun()

        # User status
        if st.session_state.current_user:
            word_count = get_word_count(st.session_state.current_user)
            st.info(f"✓ 已加载用户 / Loaded user: {st.session_state.current_user} ({word_count} words)")

        st.markdown("---")
        st.markdown("### ⚙️ 用户配置 / User Configuration")

        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input(
                "年龄 / Age",
                min_value=1,
                max_value=100,
                value=st.session_state.user_age,
                step=1,
                help="学生年龄",
                key="age_input"
            )

        with col2:
            lexile = st.number_input(
                "蓝思值 / Lexile Level",
                min_value=200,
                max_value=1700,
                value=st.session_state.user_lexile,
                step=50,
                help="阅读难度等级 (200-1700)",
                key="lexile_input"
            )

        if st.button("💾 保存配置 / Save Profile", type="primary"):
            if not st.session_state.current_user:
                st.error("⚠️ 请先选择或创建用户 / Please select or create a user first")
            else:
                try:
                    # Save user info
                    save_user_info(st.session_state.current_user, int(age), int(lexile))
                    st.session_state.user_age = int(age)
                    st.session_state.user_lexile = int(lexile)

                    # Save words
                    if st.session_state.word_bank_text:
                        words = [w.strip() for w in st.session_state.word_bank_text.split('\n') if w.strip()]
                        save_words(st.session_state.current_user, words)
                    else:
                        save_words(st.session_state.current_user, [])

                    word_count = get_word_count(st.session_state.current_user)
                    st.success(f"✓ 已保存用户配置 / Saved profile for {st.session_state.current_user} ({word_count} words in bank)")
                except Exception as e:
                    st.error(f"✗ 保存出错 / Error saving profile: {str(e)}")

        st.markdown("---")
        st.markdown("### 🔑 API 配置信息 / API Configuration")
        st.markdown(get_api_config_display())

    # Tab 2: Word Bank
    with tab2:
        word_bank = st.text_area(
            "单词库 / Word Bank (one word per line)",
            value=st.session_state.word_bank_text,
            height=400,
            placeholder="apple\nbanana\ncomputer",
            help="留空则完全依据蓝思值生成文章 / Leave empty to generate articles based purely on Lexile level",
            key=f"word_bank_area_{st.session_state.word_bank_key}"
        )

        # Update session state
        st.session_state.word_bank_text = word_bank

        col1, col2 = st.columns([1, 4])

        with col1:
            if st.button("🔧 Remove Duplicates", key="remove_duplicates_btn"):
                if not st.session_state.current_user:
                    st.error("Please select a user first")
                else:
                    # First save current text area content to file
                    words = [w.strip() for w in word_bank.split('\n') if w.strip()]
                    save_words(st.session_state.current_user, words)
                    # Then deduplicate
                    removed = deduplicate_words(st.session_state.current_user)
                    # Reload the deduplicated words
                    words = load_words(st.session_state.current_user)
                    st.session_state.word_bank_text = "\n".join(words)
                    st.session_state.word_bank_key += 1
                    st.success(f"✓ Removed {removed} duplicate words")
                    st.rerun()

    # Tab 3: Learning
    with tab3:
        # Article type selection
        st.markdown("### 📝 文章类型 / Article Type")
        article_type = st.selectbox(
            "选择文章类型 / Select Article Type",
            options=["Story", "Science", "Nature", "History"],
            index=0,
            help="故事 / 科学 / 自然 / 历史",
            key="article_type_select"
        )

        st.markdown("---")
        st.markdown("### 🤖 AI 配置 / AI Configuration")

        col1, col2 = st.columns(2)

        with col1:
            if st.session_state.global_api_config:
                # Show section names from .key_env (e.g., ALIYUN, NVIDIA, DeepSeek, ANTIG)
                providers = list(st.session_state.global_api_config.keys())
                provider = st.selectbox(
                    "AI Provider",
                    options=providers,
                    index=providers.index(st.session_state.selected_provider) if st.session_state.selected_provider in providers else 0,
                    key="provider_select"
                )
                st.session_state.selected_provider = provider
            else:
                st.error("No API configuration found")
                provider = None

        with col2:
            if provider and st.session_state.global_api_config:
                # Fetch models dynamically via API
                if provider not in st.session_state.cached_models:
                    with st.spinner(f"Loading models for {provider}..."):
                        provider_config = st.session_state.global_api_config[provider]
                        provider_type = provider_config.get('provider_type')
                        api_key = provider_config.get('api_key')
                        base_url = provider_config.get('api_base')

                        # Fetch available models from API
                        models = fetch_available_models(provider_type, api_key, base_url)
                        st.session_state.cached_models[provider] = models
                else:
                    models = st.session_state.cached_models[provider]

                if models:
                    model = st.selectbox(
                        "Model",
                        options=models,
                        index=models.index(st.session_state.selected_model) if st.session_state.selected_model in models else 0,
                        key="model_select"
                    )
                    st.session_state.selected_model = model

                    # Add refresh button to reload models
                    if st.button("🔄 Refresh Models"):
                        del st.session_state.cached_models[provider]
                        st.rerun()
                else:
                    st.warning(f"No models available for {provider}")
                    model = None
            else:
                model = None

        if st.button("🚀 Generate Article & Questions", type="primary"):
            if not st.session_state.current_user:
                st.error("⚠️ 请先选择用户 / Please select a user first")
            elif not provider or not model:
                st.error("⚠️ 请选择AI提供商和模型 / Please select AI provider and model")
            else:
                with st.spinner("Generating content..."):
                    try:
                        # Load user info and words
                        info = load_user_info(st.session_state.current_user)
                        if not info:
                            st.error("⚠️ 请先保存用户配置 / Please save user profile first")
                        else:
                            words = load_words(st.session_state.current_user)

                            # Get config for selected provider
                            if provider not in st.session_state.global_api_config:
                                st.error(f"✗ 未找到 {provider} 的API配置 / API config not found for {provider}")
                            else:
                                provider_config = st.session_state.global_api_config[provider]
                                api_key = provider_config.get('api_key')
                                provider_type = provider_config.get('provider_type')

                                if not api_key:
                                    st.error(f"✗ 未找到 {provider} 的API密钥 / API key not found for {provider}")
                                else:
                                    # Get base URL if exists
                                    base_url = get_model_base_url(st.session_state.global_api_config, provider, model)

                                    # Create AI client using provider_type (dashscope, openai, etc.)
                                    st.session_state.current_client = get_client(provider_type, model, api_key, base_url)

                                    # Generate content with article type
                                    result = generate_article_and_questions(
                                        words, info['age'], info['lexile_level'],
                                        st.session_state.current_client,
                                        article_type=article_type
                                    )

                                    if not result:
                                        st.error("✗ Failed to generate content")
                                    else:
                                        st.session_state.current_article = result['article']
                                        st.session_state.current_questions = result['questions']

                                        # Reset evaluation when generating new content
                                        st.session_state.last_evaluation = None
                                        st.session_state.last_answers = None

                                        # Save article log (before answering)
                                        save_article_log(
                                            st.session_state.current_user,
                                            result['article'],
                                            result['questions'],
                                            article_type
                                        )

                                        # Save user preferences
                                        save_user_preferences(st.session_state.current_user, provider, model)

                                        word_info = f"({len(words)} words used)" if words else f"(no word bank, difficulty based on Lexile {info['lexile_level']})"
                                        st.success(f"✓ 内容生成成功！/ Content generated successfully! {word_info}")
                    except Exception as e:
                        st.error(f"✗ 错误 / Error: {str(e)}")

        # Display article
        if st.session_state.current_article:
            st.text_area(
                "Article",
                value=st.session_state.current_article,
                height=300,
                disabled=True
            )

            # Add download button for article and questions (before answering)
            if st.session_state.current_questions and not st.session_state.last_evaluation:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"english_practice_{timestamp}.docx"

                doc_stream = create_article_document(
                    st.session_state.current_article,
                    st.session_state.current_questions
                )

                st.download_button(
                    label="📥 Download Article & Questions",
                    data=doc_stream,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

        # Display questions
        if st.session_state.current_questions:
            st.markdown("## Questions")

            answers = []
            for i, q in enumerate(st.session_state.current_questions):
                st.markdown(f"**Question {i+1}** ({q['type']})")
                st.markdown(q['question'])

                # Display options for multiple choice questions
                if q['type'] == 'multiple_choice' and 'options' in q:
                    st.markdown("**Options:**")
                    for option in q['options']:
                        st.markdown(f"- {option}")
                    st.markdown("")

                answer = st.text_input(
                    "Your Answer",
                    key=f"answer_{i}",
                    placeholder="Enter your answer (e.g., A, B, C, or D for multiple choice)"
                )
                answers.append(answer)
                st.markdown("---")

            if st.button("📝 Submit Answers", type="primary"):
                if not st.session_state.current_client:
                    st.error("Please generate content first")
                else:
                    try:
                        with st.spinner("Evaluating answers..."):
                            # Evaluate answers
                            evaluation = evaluate_answers(
                                st.session_state.current_questions,
                                answers,
                                st.session_state.current_client
                            )

                            if not evaluation:
                                st.error("✗ Failed to evaluate answers")
                            else:
                                # Save evaluation and answers to session state
                                st.session_state.last_evaluation = evaluation
                                st.session_state.last_answers = answers

                                # Save test log (with answers and evaluation)
                                save_test_log(
                                    st.session_state.current_user,
                                    st.session_state.current_article,
                                    st.session_state.current_questions,
                                    answers,
                                    evaluation,
                                    st.session_state.get('article_type_select', 'Story')
                                )

                                # Display results
                                st.success("✓ Answers submitted and evaluated!")

                                st.markdown(f"# Test Results")
                                st.markdown(f"**Score: {evaluation['score']}/100**")

                                st.markdown("## Item Analysis")
                                for i, analysis in enumerate(evaluation['item_analysis'], 1):
                                    correct = analysis.get('correct', False)
                                    status = "✓" if correct else "✗"
                                    st.markdown(f"{status} **Question {i}**: {analysis.get('feedback', 'N/A')}")

                                st.markdown("## Overall Feedback")
                                st.markdown(evaluation['overall_feedback'])

                                st.markdown("## Suggestions")
                                st.markdown(evaluation['suggestions'])

                                # Add download button for results
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = f"english_practice_results_{timestamp}.docx"

                                doc_stream = create_article_with_answers_document(
                                    st.session_state.current_article,
                                    st.session_state.current_questions,
                                    answers,
                                    evaluation
                                )

                                st.download_button(
                                    label="📥 Download Full Results",
                                    data=doc_stream,
                                    file_name=filename,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key="download_results"
                                )
                    except Exception as e:
                        st.error(f"✗ Error: {str(e)}")

    # Tab 4: History
    with tab4:
        st.text_input(
            "Username",
            value=st.session_state.current_user or "",
            disabled=True,
            key="history_username"
        )

        if st.button("📖 Load History"):
            if not st.session_state.current_user:
                st.error("Please select a user first")
            else:
                logs = get_user_logs(st.session_state.current_user)

                if not logs:
                    st.warning("No test history found")
                    st.session_state.log_list = []
                else:
                    # Create list of log summaries
                    log_choices = []
                    for log in logs:
                        timestamp = log.get('timestamp', 'Unknown')
                        score = log.get('score', 'N/A')
                        log_choices.append(f"{timestamp} - Score: {score}/100")

                    st.session_state.log_list = logs
                    st.success(f"Found {len(logs)} test records")

        if st.session_state.log_list:
            # Create radio options
            log_options = []
            for log in st.session_state.log_list:
                timestamp = log.get('timestamp', 'Unknown')
                status = log.get('status', 'completed')
                article_type = log.get('article_type', 'N/A')

                if status == 'generated':
                    label = f"{timestamp} - {article_type} - 📝 Generated (Not completed)"
                else:
                    score = log.get('score', 'N/A')
                    label = f"{timestamp} - {article_type} - ✅ Score: {score}/100"

                log_options.append(label)

            selected_log = st.radio(
                "Select Record",
                options=log_options,
                key="log_selector"
            )

            if selected_log:
                # Find the selected log
                selected_log_data = None
                for i, log_option in enumerate(log_options):
                    if log_option == selected_log:
                        selected_log_data = st.session_state.log_list[i]
                        st.markdown(format_log_for_display(selected_log_data))
                        break

                # Add download button for the selected log
                if selected_log_data:
                    timestamp_str = selected_log_data.get('timestamp', 'Unknown').replace(':', '-').replace(' ', '_')
                    status = selected_log_data.get('status', 'completed')
                    article_type = selected_log_data.get('article_type', 'N/A')

                    st.markdown("---")
                    st.markdown("### 📥 Download Options")

                    if status == 'generated':
                        # For generated articles (not completed), download article and questions only
                        filename = f"english_practice_{article_type}_{timestamp_str}.docx"

                        doc_stream = create_article_document(
                            selected_log_data.get('article', ''),
                            selected_log_data.get('questions', [])
                        )

                        st.download_button(
                            label="📥 Download Article & Questions",
                            data=doc_stream,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_generated_{timestamp_str}"
                        )
                    else:
                        # For completed tests, download full results
                        filename = f"english_results_{article_type}_{timestamp_str}.docx"

                        # Create evaluation dict from log data
                        evaluation = {
                            'score': selected_log_data.get('score', 0),
                            'item_analysis': selected_log_data.get('item_analysis', []),
                            'overall_feedback': selected_log_data.get('overall_feedback', ''),
                            'suggestions': selected_log_data.get('suggestions', '')
                        }

                        doc_stream = create_article_with_answers_document(
                            selected_log_data.get('article', ''),
                            selected_log_data.get('questions', []),
                            selected_log_data.get('user_answers', []),
                            evaluation
                        )

                        st.download_button(
                            label="📥 Download Full Results",
                            data=doc_stream,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_completed_{timestamp_str}"
                        )


if __name__ == "__main__":
    main()
