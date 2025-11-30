"""
LocalInsight - Intelligent Local Data Analyst

A zero-code, privacy-safe, interactive data analysis tool powered by AgentScope.
Upload CSV/Excel files and ask questions to get interactive ECharts visualizations
and business insights.
"""

import os
import sys
import asyncio
import streamlit as st
import traceback
from pathlib import Path
from datetime import datetime

from agentscope.message import Msg
from agents import create_data_engineer_agent, create_business_analyst_agent


# Page configuration
st.set_page_config(
    page_title="LocalInsight - 智能数据分析师",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .analysis-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .stAlert {
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None
    if 'data_engineer' not in st.session_state:
        st.session_state.data_engineer = None
    if 'business_analyst' not in st.session_state:
        st.session_state.business_analyst = None
    if 'agents_initialized' not in st.session_state:
        st.session_state.agents_initialized = False


def initialize_agents(model_type: str, api_key: str, model_name: str = None):
    """Initialize the two agents with given configuration.

    Args:
        model_type (str): "dashscope" or "openai"
        api_key (str): API key for the model provider
        model_name (str): Optional model name override
    """
    try:
        with st.spinner("🤖 正在初始化 AI 智能体..."):
            # Create Data Engineer Agent
            st.session_state.data_engineer = create_data_engineer_agent(
                model_type=model_type,
                api_key=api_key,
                model_name=model_name,
                temperature=0.7,
                max_iters=10
            )

            # Create Business Analyst Agent
            st.session_state.business_analyst = create_business_analyst_agent(
                model_type=model_type,
                api_key=api_key,
                model_name=model_name,
                temperature=0.8
            )

            st.session_state.agents_initialized = True
            st.success("✅ AI 智能体初始化成功！")

    except Exception as e:
        st.error(f"❌ 初始化失败: {str(e)}")
        st.session_state.agents_initialized = False
        raise


async def run_analysis_pipeline(user_question: str, file_path: str) -> dict:
    """Run the two-agent analysis pipeline.

    Args:
        user_question (str): User's question about the data
        file_path (str): Path to the uploaded data file

    Returns:
        dict: Contains 'analysis' (str), 'engineer_log' (str), and 'success' (bool)
    """
    try:
        # Ensure temp directory exists
        os.makedirs("./temp", exist_ok=True)

        # Step 1: Data Engineer Agent processes data and creates visualization
        st.info("🔧 数据工程师正在处理数据...")

        engineer_msg = Msg(
            name="user",
            content=f"""数据文件路径: {file_path}

用户问题: {user_question}

请按照以下步骤完成任务:
1. 使用 read_data_schema 工具了解数据结构
2. 根据用户需求编写 Python 代码处理数据并生成 Pyecharts 可视化
3. 保存图表为 ./temp/visual_result.html
4. 使用 print() 输出关键统计指标
5. 使用 validate_html_output 验证文件生成成功
""",
            role="user"
        )

        # Call Data Engineer Agent
        engineer_response = await st.session_state.data_engineer(engineer_msg)

        # Extract execution log from engineer's response
        # The log contains all print() outputs from executed code
        engineer_log = extract_execution_log(engineer_response)

        # Check if visualization file was created
        viz_file_path = "./temp/visual_result.html"
        if not os.path.exists(viz_file_path):
            return {
                'analysis': f"**错误**: 数据工程师未能生成可视化文件。\n\n工程师输出:\n{engineer_response.content}",
                'engineer_log': engineer_log,
                'success': False
            }

        # Step 2: Business Analyst Agent analyzes the results
        st.info("📊 商业分析师正在分析数据...")

        analyst_msg = Msg(
            name="engineer",
            content=f"""用户问题: {user_question}

数据工程师执行日志:
{engineer_log}

请基于以上信息，为用户生成通俗易懂的商业分析报告。
""",
            role="assistant"
        )

        # Call Business Analyst Agent
        analyst_response = await st.session_state.business_analyst(analyst_msg)

        return {
            'analysis': analyst_response.content,
            'engineer_log': engineer_log,
            'success': True
        }

    except Exception as e:
        error_msg = f"分析过程中出现错误:\n\n{str(e)}\n\n{traceback.format_exc()}"
        return {
            'analysis': error_msg,
            'engineer_log': "",
            'success': False
        }


def extract_execution_log(engineer_msg: Msg) -> str:
    """Extract execution log (print outputs) from engineer's response.

    Args:
        engineer_msg (Msg): Response message from Data Engineer Agent

    Returns:
        str: Extracted execution log
    """
    content = engineer_msg.content

    # Try to extract content between "=== Output ===" markers
    if "=== Output ===" in content:
        parts = content.split("=== Output ===")
        if len(parts) > 1:
            # Get everything after the first marker
            log_part = parts[1].split("===")[0].strip()
            return log_part

    # Fallback: return full content
    return content


def display_chat_message(role: str, content: str):
    """Display a chat message with appropriate styling.

    Args:
        role (str): "user" or "assistant"
        content (str): Message content
    """
    with st.chat_message(role):
        st.markdown(content)


def main():
    """Main Streamlit application."""
    initialize_session_state()

    # Header
    st.markdown('<div class="main-header">📊 LocalInsight</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">智能本地数据分析师 - 零代码 · 隐私安全 · 交互式可视化</div>',
        unsafe_allow_html=True
    )

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ 配置")

        # Model provider selection
        model_type = st.selectbox(
            "选择模型提供商",
            ["dashscope", "openai"],
            help="DashScope (通义千问) 或 OpenAI (GPT)"
        )

        # API Key input
        api_key_label = "DashScope API Key" if model_type == "dashscope" else "OpenAI API Key"
        api_key_env = "DASHSCOPE_API_KEY" if model_type == "dashscope" else "OPENAI_API_KEY"

        # Try to get API key from environment
        default_api_key = os.environ.get(api_key_env, "")

        api_key = st.text_input(
            api_key_label,
            value=default_api_key,
            type="password",
            help=f"输入你的 {api_key_label}，或在 .env 文件中设置 {api_key_env}"
        )

        # Model name selection
        if model_type == "dashscope":
            model_name = st.selectbox(
                "选择模型",
                ["qwen-max", "qwen-plus", "qwen-turbo"],
                help="推荐使用 qwen-max 以获得最佳效果"
            )
        else:
            model_name = st.selectbox(
                "选择模型",
                ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                help="推荐使用 gpt-4 以获得最佳效果"
            )

        # Initialize agents button
        if st.button("🚀 初始化智能体", use_container_width=True):
            if not api_key:
                st.error(f"请先输入 {api_key_label}！")
            else:
                # Set environment variable
                os.environ[api_key_env] = api_key
                initialize_agents(model_type, api_key, model_name)

        # Status indicator
        if st.session_state.agents_initialized:
            st.success("✅ 智能体已就绪")
        else:
            st.warning("⚠️ 请先初始化智能体")

        st.divider()

        # File upload
        st.header("📁 上传数据")
        uploaded_file = st.file_uploader(
            "选择 CSV 或 Excel 文件",
            type=["csv", "xlsx", "xls"],
            help="支持 CSV 和 Excel 格式"
        )

        if uploaded_file is not None:
            # Save uploaded file
            os.makedirs("./temp", exist_ok=True)

            file_ext = os.path.splitext(uploaded_file.name)[1]
            file_path = f"./temp/data{file_ext}"

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.session_state.uploaded_file_path = file_path

            st.success(f"✅ 已上传: {uploaded_file.name}")
            st.info(f"文件大小: {uploaded_file.size / 1024:.2f} KB")

        st.divider()

        # Clear chat button
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.data_engineer:
                st.session_state.data_engineer.memory.clear()
            if st.session_state.business_analyst:
                st.session_state.business_analyst.memory.clear()
            st.rerun()

        # About section
        st.divider()
        st.markdown("""
        ### 关于 LocalInsight

        **特点**:
        - 🔒 **隐私安全**: 数据完全本地处理
        - 🎨 **交互式图表**: 基于 ECharts 的动态可视化
        - 🤖 **AI 驱动**: 双智能体协作分析
        - 💬 **对话式**: 自然语言提问

        **技术栈**:
        - AgentScope (多智能体框架)
        - Pyecharts (可视化)
        - Streamlit (Web界面)
        """)

    # Main content area
    if not st.session_state.agents_initialized:
        st.info("👈 请先在左侧配置并初始化智能体")
        st.markdown("""
        ### 快速开始

        1. **配置模型**
           - 选择模型提供商 (DashScope 或 OpenAI)
           - 输入 API Key
           - 选择模型版本

        2. **初始化智能体**
           - 点击"初始化智能体"按钮

        3. **上传数据**
           - 上传 CSV 或 Excel 文件

        4. **开始分析**
           - 在下方输入框提出问题
           - AI 会自动生成可视化和分析报告

        ### 示例问题

        - "分析各季度的销售趋势"
        - "对比不同产品类别的销售额"
        - "找出销售额最高的前5个地区"
        - "展示每月收入的变化情况"
        - "分析客户年龄分布"
        """)
        return

    if st.session_state.uploaded_file_path is None:
        st.info("👈 请先上传数据文件")
        return

    # Display chat history
    for message in st.session_state.messages:
        display_chat_message(message["role"], message["content"])

    # Chat input
    user_question = st.chat_input("请输入您的问题...")

    if user_question:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_question})
        display_chat_message("user", user_question)

        # Run analysis pipeline
        with st.spinner("🤔 AI 正在分析数据..."):
            try:
                # Run async pipeline
                result = asyncio.run(run_analysis_pipeline(
                    user_question,
                    st.session_state.uploaded_file_path
                ))

                if result['success']:
                    # Display visualization
                    viz_file_path = "./temp/visual_result.html"
                    if os.path.exists(viz_file_path):
                        st.markdown("### 📊 数据可视化")
                        with open(viz_file_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=600, scrolling=True)

                    # Display analysis
                    st.markdown("### 📈 分析报告")
                    st.markdown(f'<div class="analysis-box">{result["analysis"]}</div>',
                               unsafe_allow_html=True)

                    # Add assistant message to chat
                    assistant_message = f"### 📊 数据可视化\n\n已生成交互式图表（请查看上方）\n\n### 📈 分析报告\n\n{result['analysis']}"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_message
                    })

                    # Optional: Show engineer log in expander
                    if result['engineer_log']:
                        with st.expander("🔍 查看技术日志"):
                            st.code(result['engineer_log'], language="text")

                else:
                    # Error occurred
                    st.error("分析失败，请查看详细信息")
                    st.code(result['analysis'], language="text")

                    # Add error message to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ 分析失败\n\n{result['analysis']}"
                    })

            except Exception as e:
                error_msg = f"发生错误: {str(e)}\n\n{traceback.format_exc()}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ 发生错误\n\n{error_msg}"
                })


if __name__ == "__main__":
    main()
