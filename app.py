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
from agents import (
    create_data_engineer_agent,
    create_business_analyst_agent,
    create_router_agent,
    create_general_agent
)


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
    /* GitHub Dark Mode Theme */
    
    /* Global Background & Text */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6, .main-header {
        color: #c9d1d9 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #8b949e !important;
        margin-bottom: 2rem;
        text-align: center;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Inputs (Text Input, Selectbox, etc) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    
    /* Buttons (GitHub Green) */
    .stButton button {
        background-color: #238636;
        color: #ffffff;
        border: 1px solid rgba(240, 246, 252, 0.1);
        border-radius: 6px;
        font-weight: 600;
        transition: 0.2s;
    }
    .stButton button:hover {
        background-color: #2ea043;
        border-color: rgba(240, 246, 252, 0.1);
        color: #ffffff;
    }
    
    /* Analysis Box (Card Style) */
    .analysis-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 1.5rem;
        color: #c9d1d9;
    }
    
    /* Code Blocks */
    code {
        background-color: #161b22 !important;
        color: #c9d1d9 !important;
        border-radius: 6px;
        border: 1px solid #30363d;
    }
    
    /* Links */
    a {
        color: #58a6ff !important;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: transparent;
    }
    div[data-testid="stChatMessageContent"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        color: #c9d1d9;
        border-radius: 6px;
    }
    
    /* File Uploader */
    section[data-testid="stFileUploader"] {
        background-color: #161b22;
        border: 1px dashed #30363d;
        border-radius: 6px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #161b22;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    
    /* Divider */
    hr {
        border-color: #30363d;
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
    if 'router_agent' not in st.session_state:
        st.session_state.router_agent = None
    if 'general_agent' not in st.session_state:
        st.session_state.general_agent = None
    if 'agents_initialized' not in st.session_state:
        st.session_state.agents_initialized = False


def initialize_agents(model_type: str, api_key: str, model_name: str = None):
    """Initialize all agents with given configuration.

    Args:
        model_type (str): "dashscope" or "openai"
        api_key (str): API key for the model provider
        model_name (str): Optional model name override
    """
    try:
        with st.spinner("🤖 正在初始化 AI 智能体..."):
            # Create Router Agent (cheaper model)
            st.session_state.router_agent = create_router_agent(
                model_type=model_type,
                api_key=api_key,
                model_name="qwen-turbo" if model_type == "dashscope" else "gpt-3.5-turbo",
                temperature=0.1
            )

            # Create General Agent (mid-tier model)
            st.session_state.general_agent = create_general_agent(
                model_type=model_type,
                api_key=api_key,
                model_name="qwen-plus" if model_type == "dashscope" else "gpt-3.5-turbo",
                temperature=0.3
            )

            # Create Data Engineer Agent
            st.session_state.data_engineer = create_data_engineer_agent(
                model_type=model_type,
                api_key=api_key,
                model_name=model_name,
                temperature=0.3,
                max_iters=15
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


def extract_agent_content(agent_response) -> str:
    """Extract and clean content from agent response.
    
    Args:
        agent_response: Agent response object with content attribute
        
    Returns:
        str: Cleaned content string
    """
    content = agent_response.content
    
    # Handle list format (AgentScope format)
    if isinstance(content, list):
        content = '\n'.join(
            item.get('text', str(item)) if isinstance(item, dict) else str(item)
            for item in content
        )
    elif not isinstance(content, str):
        content = str(content)
    
    # Remove markdown code blocks if present
    content = content.strip()
    
    # Remove ```markdown wrapper
    if content.startswith('```markdown'):
        content = content[len('```markdown'):].strip()
    
    # Remove generic ``` wrapper
    if content.startswith('```'):
        content = content[3:].strip()
    if content.endswith('```'):
        content = content[:-3].strip()
    
    return content


async def run_analysis_pipeline(user_question: str, file_path: str) -> dict:
    """Run the intelligent routing pipeline.

    Args:
        user_question (str): User's question about the data
        file_path (str): Path to the uploaded data file

    Returns:
        dict: Contains 'analysis' (str), 'route' (str), 'engineer_log' (str), 
              'has_visualization' (bool), and 'success' (bool)
    """
    try:
        import json
        import re
        
        # Ensure temp directory exists
        os.makedirs("./temp", exist_ok=True)

        # Step 1: Router Agent decides the route
        st.info("🧭 正在分析问题类型...")

        router_msg = Msg(
            name="user",
            content=f"""用户问题: {user_question}

数据文件路径: {file_path}

请判断这个问题是否需要生成可视化图表。
""",
            role="user"
        )

        # Call Router Agent
        router_response = await st.session_state.router_agent(router_msg)
        
        # Extract content from response
        router_content = extract_agent_content(router_response)
        
        # Parse router decision (extract JSON from response)
        route_decision = parse_router_decision(router_content)
        
        # Get engine type
        engine = route_decision.get('engine', 'matplotlib')
        
        # Debug: Show route decision
        engine_label = "Matplotlib (静态)" if engine == "matplotlib" else "Pyecharts (交互)"
        st.info(f"🔍 路由决策: {route_decision['route']} | 图表引擎: {engine_label} | 原因: {route_decision['reason']}")
        
        # Step 2: Route based on decision
        if route_decision["route"] == "general":
            # Simple question - use General Agent
            st.info(f"💬 检测到简单问题：{route_decision['reason']}")
            
            general_msg = Msg(
                name="user",
                content=f"""用户问题: {user_question}

数据文件路径: {file_path}

请回答用户的问题。
""",
                role="user"
            )
            
            # Call General Agent
            general_response = await st.session_state.general_agent(general_msg)
            
            # Extract and clean content
            general_content = extract_agent_content(general_response)
            
            return {
                'analysis': general_content,
                'route': 'general',
                'engineer_log': '',
                'has_visualization': False,
                'success': True
            }
        
        else:
            # Visualization needed - use DataEngineer + BusinessAnalyst
            engine_label = "Matplotlib (静态)" if engine == "matplotlib" else "Pyecharts (交互)"
            st.info(f"📊 需要生成可视化：{route_decision['reason']} | 引擎: {engine_label}")
            
            # Step 3: Data Engineer Agent processes data and creates visualization
            st.info("🔧 数据工程师正在处理数据...")

            # Determine output file based on engine
            if engine == "matplotlib":
                output_file = "./temp/visual_result.png"
                validate_hint = "validate_chart_output(engine='matplotlib')"
            else:
                output_file = "./temp/visual_result.html"
                validate_hint = "validate_chart_output(engine='pyecharts')"

            engineer_msg = Msg(
                name="user",
                content=f"""任务：为以下问题生成可视化

数据文件：{file_path}
用户问题：{user_question}
图表引擎：{engine}

执行步骤（立即执行，不要解释）：
1. read_data_schema - 读取数据结构
2. execute_python_safe - 使用 {engine} 生成图表并保存到 {output_file}
3. {validate_hint} - 验证文件

现在开始执行！
""",
                role="user"
            )

            # Call Data Engineer Agent
            engineer_response = await st.session_state.data_engineer(engineer_msg)

            # Extract execution log from engineer's response
            engineer_log = extract_execution_log(engineer_response)

            # Check if visualization file was created
            viz_file_path = output_file
            if not os.path.exists(viz_file_path):
                return {
                    'analysis': f"**错误**: 数据工程师未能生成可视化文件。\n\n工程师输出:\n{engineer_response.content}",
                    'route': 'visualization',
                    'engine': engine,
                    'engineer_log': engineer_log,
                    'has_visualization': False,
                    'success': False
                }

            # Step 4: Business Analyst Agent analyzes the results
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

            # Extract and clean content
            analyst_content = extract_agent_content(analyst_response)

            return {
                'analysis': analyst_content,
                'route': 'visualization',
                'engine': engine,
                'viz_file_path': viz_file_path,
                'engineer_log': engineer_log,
                'has_visualization': True,
                'success': True
            }

    except Exception as e:
        error_msg = f"分析过程中出现错误:\n\n{str(e)}\n\n{traceback.format_exc()}"
        return {
            'analysis': error_msg,
            'route': 'error',
            'engine': 'matplotlib',
            'engineer_log': "",
            'has_visualization': False,
            'success': False
        }


def parse_router_decision(response_content: str) -> dict:
    """Parse router agent's decision from response content.
    
    Args:
        response_content (str): Router agent's response
        
    Returns:
        dict: Parsed decision with 'route', 'engine', and 'reason' keys
    """
    try:
        import json
        import re
        
        # Ensure we have a string
        if not isinstance(response_content, str):
            response_content = str(response_content)
        
        # Remove markdown code blocks if present
        content_cleaned = response_content.strip()
        
        # Remove ```json and ``` markers
        if '```json' in content_cleaned:
            content_cleaned = re.sub(r'```json\s*', '', content_cleaned)
            content_cleaned = re.sub(r'```\s*$', '', content_cleaned)
        elif '```' in content_cleaned:
            content_cleaned = re.sub(r'```\s*', '', content_cleaned)
        
        # Try to extract JSON from response
        # Look for JSON pattern in the response
        json_pattern = r'\{[^{}]*"route"[^{}]*\}'
        matches = re.findall(json_pattern, content_cleaned, re.DOTALL)
        
        if matches:
            # Parse the last JSON match (most likely the final decision)
            for match in reversed(matches):
                try:
                    decision = json.loads(match)
                    
                    # Validate required keys
                    if 'route' in decision:
                        route_value = str(decision['route']).lower().strip()
                        
                        # Normalize route value
                        if route_value in ['general', 'simple', '简单', '简单问题']:
                            route_value = 'general'
                        elif route_value in ['visualization', 'visual', 'chart', '可视化', '图表']:
                            route_value = 'visualization'
                        
                        # Parse engine field (default to matplotlib)
                        engine_value = str(decision.get('engine', 'matplotlib')).lower().strip()
                        if engine_value not in ['matplotlib', 'pyecharts']:
                            engine_value = 'matplotlib'
                        
                        return {
                            'route': route_value,
                            'engine': engine_value,
                            'reason': decision.get('reason', '未提供原因')
                        }
                except json.JSONDecodeError:
                    continue
        
        # Fallback: keyword-based detection
        content_lower = response_content.lower()
        if 'general' in content_lower or '简单问题' in response_content or '不需要' in response_content:
            return {
                'route': 'general',
                'engine': 'matplotlib',
                'reason': '检测到简单问题（基于关键词）'
            }
        else:
            # Check for interactive chart request
            engine = 'matplotlib'
            if '交互' in response_content or 'interactive' in content_lower or 'pyecharts' in content_lower:
                engine = 'pyecharts'
            
            return {
                'route': 'visualization',
                'engine': engine,
                'reason': '需要可视化（默认路由）'
            }
    
    except Exception as e:
        # Default to visualization on parse error
        import traceback
        error_detail = traceback.format_exc()
        print(f"路由解析错误详情: {error_detail}")  # Debug print
        
        return {
            'route': 'visualization',
            'engine': 'matplotlib',
            'reason': f'路由解析失败，默认使用可视化路径（错误：{str(e)}）'
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
            if st.session_state.router_agent:
                st.session_state.router_agent.memory.clear()
            if st.session_state.general_agent:
                st.session_state.general_agent.memory.clear()
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
        - 🤖 **智能路由**: 自动识别问题类型，优化响应
        - 💬 **对话式**: 自然语言提问

        **技术栈**:
        - AgentScope (多智能体框架)
        - Pyecharts (可视化)
        - Streamlit (Web界面)
        
        **智能体架构**:
        - 🧭 路由Agent: 判断问题类型
        - 💬 通用Agent: 处理简单问题
        - 🔧 数据工程师: 生成可视化
        - 📊 商业分析师: 解读结果
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

        **简单问题（快速回答）**:
        - "这张表有哪些字段？"
        - "数据有多少行？"
        - "总销售额是多少？"
        - "销售额的平均值是多少？"
        
        **复杂分析（生成图表）**:
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
                    # Check if visualization was generated
                    if result.get('has_visualization', False):
                        # Get engine and file path
                        engine = result.get('engine', 'matplotlib')
                        viz_file_path = result.get('viz_file_path', './temp/visual_result.png')
                        
                        # Display visualization based on engine type
                        if os.path.exists(viz_file_path):
                            st.markdown("### 📊 数据可视化")
                            
                            if engine == "matplotlib":
                                # Display PNG image
                                st.image(viz_file_path, use_container_width=True)
                            else:
                                # Display interactive HTML chart
                                with open(viz_file_path, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                st.components.v1.html(html_content, height=600, scrolling=True)

                        # Display analysis
                        st.markdown("### 📈 分析报告")
                        st.markdown(f'<div class="analysis-box">{result["analysis"]}</div>',
                                   unsafe_allow_html=True)

                        # Add assistant message to chat
                        chart_type = "静态图表" if engine == "matplotlib" else "交互式图表"
                        assistant_message = f"### 📊 数据可视化\n\n已生成{chart_type}（请查看上方）\n\n### 📈 分析报告\n\n{result['analysis']}"
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": assistant_message
                        })

                        # Optional: Show engineer log in expander
                        if result.get('engineer_log'):
                            with st.expander("🔍 查看技术日志"):
                                st.code(result['engineer_log'], language="text")
                    
                    else:
                        # Simple question - no visualization
                        st.markdown("### 💬 回答")
                        st.markdown(f'<div class="analysis-box">{result["analysis"]}</div>',
                                   unsafe_allow_html=True)

                        # Add assistant message to chat
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result['analysis']
                        })

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
