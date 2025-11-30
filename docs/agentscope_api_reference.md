# AgentScope API Reference Documentation

> **Version**: Based on AgentScope main branch (latest)
> **Official Docs**: https://doc.agentscope.io/
> **GitHub**: https://github.com/agentscope-ai/agentscope

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Message System](#message-system)
3. [Model Configuration](#model-configuration)
4. [Agents](#agents)
5. [Toolkit & Tools](#toolkit--tools)
6. [Memory System](#memory-system)
7. [Multi-Agent Orchestration](#multi-agent-orchestration)
8. [Best Practices](#best-practices)

---

## Core Concepts

### Architecture Overview

```
┌─────────────┐
│   Message   │  Communication protocol between agents
└──────┬──────┘
       │
       ↓
┌─────────────┐     ┌──────────────┐
│    Agent    │────→│    Model     │  LLM provider (DashScope/OpenAI)
└──────┬──────┘     └──────────────┘
       │
       ↓
┌─────────────┐     ┌──────────────┐
│   Toolkit   │────→│    Memory    │  Conversation history
└─────────────┘     └──────────────┘
```

### Key Principles

- **Transparency**: All prompts, API calls, and workflows are visible
- **Modularity**: Components are independent and composable
- **Async-First**: Full async/await support throughout
- **Model-Agnostic**: Write once, deploy across different LLMs

---

## Message System

### `Msg` Class

The core communication unit in AgentScope.

#### Constructor

```python
from agentscope.message import Msg

Msg(
    name: str,                                    # Sender identifier
    content: str | list[ContentBlock],            # Message content
    role: Literal["user", "assistant", "system"], # Sender role
    metadata: dict | None = None,                 # Optional structured data
    timestamp: str | None = None,                 # Auto-generated if None
    invocation_id: str | None = None              # API call tracking ID
)
```

#### Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `to_dict()` | `dict` | Serialize message to JSON dictionary |
| `from_dict(json_data)` | `Msg` | Deserialize from JSON (class method) |
| `has_content_blocks(block_type=None)` | `bool` | Check if message has content blocks |
| `get_text_content()` | `str` | Extract pure text from message |
| `get_content_blocks(block_type=None)` | `list` | Get typed content blocks |

#### Usage Examples

```python
# Simple text message
msg = Msg(
    name="user",
    content="分析2024年的销售数据",
    role="user"
)

# Message with metadata
msg = Msg(
    name="assistant",
    content="分析完成",
    role="assistant",
    metadata={
        "total_sales": 1000000,
        "chart_path": "./temp/chart.html"
    }
)

# Serialize and restore
msg_dict = msg.to_dict()
restored_msg = Msg.from_dict(msg_dict)

# Extract text
text = msg.get_text_content()
```

#### Role Types

- **`"user"`**: Client/requester initiating interaction
- **`"assistant"`**: Agent providing responses
- **`"system"`**: Framework-level instructions or context

---

## Model Configuration

### Supported Providers

- **DashScope** (Alibaba Qwen models)
- **OpenAI** (GPT models)
- **Anthropic** (Claude models)
- **Google Gemini**
- **Ollama** (Local models)

### `DashScopeChatModel`

#### Constructor

```python
from agentscope.models import DashScopeChatModel

DashScopeChatModel(
    model_name: str,                    # e.g., "qwen-max", "qwen-turbo"
    api_key: str,                       # DashScope API key
    stream: bool = False,               # Enable streaming responses
    generate_kwargs: dict | None = None # Additional parameters
)
```

#### Usage Example

```python
import os

model = DashScopeChatModel(
    model_name="qwen-max",
    api_key=os.environ["DASHSCOPE_API_KEY"],
    stream=False,
    generate_kwargs={
        "temperature": 0.7,
        "max_tokens": 2000,
        "top_p": 0.9
    }
)
```

### `OpenAIChatModel`

#### Constructor

```python
from agentscope.models import OpenAIChatModel

OpenAIChatModel(
    model_name: str,                    # e.g., "gpt-4", "gpt-3.5-turbo"
    api_key: str,                       # OpenAI API key
    stream: bool = False,
    client_kwargs: dict | None = None,  # Custom endpoint configuration
    generate_kwargs: dict | None = None
)
```

#### Usage Example

```python
# Standard OpenAI
model = OpenAIChatModel(
    model_name="gpt-4",
    api_key=os.environ["OPENAI_API_KEY"]
)

# Custom endpoint (e.g., local server)
model = OpenAIChatModel(
    model_name="gpt-4",
    api_key="dummy",
    client_kwargs={"base_url": "http://localhost:8000/v1"}
)
```

---

## Agents

### `ReActAgent`

Agent that implements the ReAct (Reasoning + Acting) pattern. Best for tasks requiring step-by-step problem solving with tool usage.

#### Constructor

```python
from agentscope.agents import ReActAgent
from agentscope.prompt import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory

ReActAgent(
    name: str,                          # Agent identifier
    sys_prompt: str,                    # System instruction
    model: ModelWrapperBase,            # LLM model instance
    formatter: PromptFormatter,         # Prompt formatter matching model
    toolkit: Toolkit | None = None,     # Tool collection
    memory: MemoryBase | None = None,   # Conversation memory
    long_term_memory: MemoryBase | None = None,  # Persistent memory
    max_iters: int = 10,               # Max reasoning iterations
    verbose: bool = True                # Enable logging
)
```

#### Usage Example

```python
from agentscope.agents import ReActAgent
from agentscope.models import DashScopeChatModel
from agentscope.prompt import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.utils import Toolkit

# Create model
model = DashScopeChatModel(
    model_name="qwen-max",
    api_key=os.environ["DASHSCOPE_API_KEY"]
)

# Create toolkit
toolkit = Toolkit()
toolkit.register_tool_function(my_tool_function)

# Create agent
agent = ReActAgent(
    name="DataEngineer",
    sys_prompt="""You are a data engineer expert in Python and Pyecharts.

    Task:
    1. Use read_data_schema to understand data structure
    2. Write Python code to process data and create visualizations
    3. Save output as ./temp/visual_result.html
    4. Print key statistics using print()

    Constraints:
    - Convert Pandas Series to Python list using .tolist()
    - No plt.show(), no network access
    """,
    model=model,
    formatter=DashScopeChatFormatter(),
    toolkit=toolkit,
    memory=InMemoryMemory(),
    max_iters=10
)

# Invoke agent (async)
response = await agent(msg)

# Or synchronous
import asyncio
response = asyncio.run(agent(msg))
```

#### How ReActAgent Works

1. **Think**: LLM analyzes the problem and decides next action
2. **Act**: Calls tool or generates response
3. **Observe**: Gets tool execution result
4. **Repeat**: Loops until task is complete or max_iters reached

### `AgentBase`

Base agent class for creating custom agents or simple conversational agents without tools.

#### Constructor

```python
from agentscope.agents import AgentBase

AgentBase(
    name: str,
    sys_prompt: str,
    model: ModelWrapperBase,
    formatter: PromptFormatter,
    memory: MemoryBase | None = None
)
```

#### Usage Example

```python
analyst = AgentBase(
    name="BusinessAnalyst",
    sys_prompt="""You are a senior business analyst.

    You will receive execution logs from the data engineer.
    Provide business insights in plain language, not code details.
    Remind users to interact with the generated charts.
    """,
    model=model,
    formatter=DashScopeChatFormatter(),
    memory=InMemoryMemory()
)

# Invoke
response = await analyst(msg)
```

### Custom Agent Creation

For advanced use cases, inherit from `AgentBase` and implement:

```python
from agentscope.agents import AgentBase
from agentscope.message import Msg

class MyCustomAgent(AgentBase):
    async def reply(self, msg: Msg | list[Msg] | None) -> Msg:
        """Generate response to input message"""
        # Add to memory
        await self.memory.add(msg)

        # Format prompt
        prompt = await self.formatter.format([
            {"role": "system", "content": self.sys_prompt},
            *await self.memory.get_memory()
        ])

        # Call model
        response = await self.model(prompt)

        # Return message
        return Msg(
            name=self.name,
            content=response.content,
            role="assistant"
        )

    async def observe(self, msg: Msg) -> None:
        """Process incoming message"""
        await self.memory.add(msg)

    async def handle_interrupt(self, interrupt_msg: str) -> Msg:
        """Handle user interruption"""
        return Msg(
            name=self.name,
            content=f"Interrupted: {interrupt_msg}",
            role="assistant"
        )
```

---

## Toolkit & Tools

### Tool Function Requirements

All tool functions must:

1. Return `ToolResponse` object
2. Have complete docstring (LLM reads it)
3. Use type hints for all parameters

### `ToolResponse` Class

```python
from agentscope.service import ToolResponse

ToolResponse(
    content: str,                    # Tool execution result
    is_success: bool = True,         # Execution status
    is_interrupted: bool = False,    # Whether interrupted
    metadata: dict | None = None     # Additional data
)
```

### Tool Definition Template

```python
from agentscope.service import ToolResponse
import pandas as pd

def read_data_schema(file_path: str) -> ToolResponse:
    """Read CSV file schema and first 5 rows

    This tool reads a CSV file and returns its structure information
    including column names, data types, and sample data.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        ToolResponse: JSON string containing schema information
    """
    try:
        # Read data
        df = pd.read_csv(file_path, nrows=5)

        # Prepare schema info
        schema_info = {
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "sample_data": df.to_dict('records'),
            "shape": {"rows": len(df), "cols": len(df.columns)}
        }

        # Return success response
        return ToolResponse(
            content=json.dumps(schema_info, ensure_ascii=False, indent=2),
            is_success=True,
            metadata={"file_path": file_path}
        )

    except Exception as e:
        # Return error response
        return ToolResponse(
            content=f"Error reading file: {str(e)}",
            is_success=False,
            metadata={"error_type": type(e).__name__}
        )
```

### Async Tool Example

```python
async def async_api_call(query: str) -> ToolResponse:
    """Call external API asynchronously

    Args:
        query (str): Search query

    Returns:
        ToolResponse: API response data
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.example.com?q={query}") as resp:
                data = await resp.json()
                return ToolResponse(
                    content=json.dumps(data),
                    is_success=True
                )
    except Exception as e:
        return ToolResponse(
            content=str(e),
            is_success=False
        )
```

### `Toolkit` Class

Manages tool functions and generates JSON schemas for LLMs.

#### Methods

```python
from agentscope.utils import Toolkit

toolkit = Toolkit()

# Register tool function
toolkit.register_tool_function(
    func: Callable,                      # Tool function
    preset_kwargs: dict | None = None,   # Pre-set parameters (e.g., API keys)
    group_name: str | None = None        # Optional group for organization
)

# Create tool group
toolkit.create_tool_group(
    group_name: str,
    active: bool = True
)

# Update group status
toolkit.update_tool_groups(
    group_names: list[str],
    active: bool
)
```

#### Usage Example

```python
toolkit = Toolkit()

# Register simple tool
toolkit.register_tool_function(read_data_schema)

# Register with preset parameters
toolkit.register_tool_function(
    api_call_tool,
    preset_kwargs={"api_key": os.environ["API_KEY"]}
)

# Group management
toolkit.create_tool_group(group_name="data_tools", active=True)
toolkit.register_tool_function(
    read_csv,
    group_name="data_tools"
)
toolkit.register_tool_function(
    write_csv,
    group_name="data_tools"
)

# Activate/deactivate groups
toolkit.update_tool_groups(group_names=["data_tools"], active=True)
```

### Built-in Tools

AgentScope provides several built-in tools:

```python
from agentscope.service import (
    execute_python_code,      # Execute Python code in sandbox
    execute_shell_command,    # Execute shell commands
    read_text_file,          # Read text files
    write_text_file,         # Write text files
)
```

**⚠️ Security Warning**: `execute_python_code` and `execute_shell_command` can be dangerous. Always validate input before use.

---

## Memory System

### `InMemoryMemory`

Short-term conversation memory stored in RAM.

```python
from agentscope.memory import InMemoryMemory

memory = InMemoryMemory(
    config: dict | None = None  # Optional configuration
)

# Methods
await memory.add(msg: Msg)                    # Add message to memory
await memory.get_memory() -> list[dict]       # Get all messages
await memory.clear()                          # Clear memory
```

### Usage in Agents

```python
agent = ReActAgent(
    name="Agent",
    sys_prompt="...",
    model=model,
    formatter=formatter,
    memory=InMemoryMemory()  # Each agent has independent memory
)
```

---

## Multi-Agent Orchestration

### Pattern 1: Sequential Pipeline

Agents execute one after another.

```python
from agentscope.message import Msg

# Create initial message
msg = Msg(name="user", content="Analyze sales data", role="user")

# Step 1: Data engineer processes data
engineer_response = await data_engineer(msg)

# Step 2: Analyst analyzes results
analyst_msg = Msg(
    name="engineer",
    content=f"Engineer output: {engineer_response.content}",
    role="assistant"
)
analyst_response = await business_analyst(analyst_msg)

# Final output
print(analyst_response.content)
```

### Pattern 2: MsgHub (Message Hub)

For multi-agent conversations with shared context.

```python
from agentscope.msghub import MsgHub

# Create message hub
hub = MsgHub(
    participants=[agent1, agent2, agent3],
    announcement=Msg(
        name="system",
        content="Discussion topic: Q4 sales strategy",
        role="system"
    )
)

# Broadcast message to all participants
hub.broadcast(user_msg)

# Dynamic participant management
hub.add_participant(new_agent)
hub.delete_participant(old_agent)

# Get conversation history
messages = hub.get_history()
```

### Pattern 3: Conditional Routing

Route messages based on content or logic.

```python
async def route_message(msg: Msg):
    """Route message to appropriate agent"""
    content_lower = msg.content.lower()

    if "visualize" in content_lower or "chart" in content_lower:
        response = await data_engineer(msg)
    elif "analyze" in content_lower or "insight" in content_lower:
        response = await business_analyst(msg)
    else:
        response = await general_agent(msg)

    return response
```

---

## Best Practices

### 1. System Prompt Engineering

**DO**:
```python
sys_prompt = """You are a data engineer expert in Python and Pyecharts.

TASK:
1. Use read_data_schema tool to understand data structure
2. Write complete Python code to process data
3. Generate visualization and save as ./temp/visual_result.html

CONSTRAINTS:
- Convert Pandas Series to list using .tolist() before passing to Pyecharts
- Print all key statistics using print()
- DO NOT use plt.show()
- DO NOT access network

CODE EXAMPLE:
```python
import pandas as pd
from pyecharts.charts import Bar

df = pd.read_csv(file_path)
x_data = df['category'].tolist()  # Important: convert to list
y_data = df['sales'].tolist()

bar = Bar()
bar.add_xaxis(x_data)
bar.add_yaxis("Sales", y_data)
bar.render("./temp/visual_result.html")

print(f"Total sales: {sum(y_data)}")
```
"""
```

**DON'T**:
```python
sys_prompt = "You are a helpful assistant."  # Too vague
```

### 2. Tool Design

**DO**:
- Keep tools focused on single responsibility
- Always return `ToolResponse`
- Provide detailed docstrings
- Handle errors gracefully

**DON'T**:
- Return raw strings or dicts (use `ToolResponse`)
- Create tools that do too many things
- Forget error handling

### 3. Error Handling

```python
def safe_tool(param: str) -> ToolResponse:
    """Safe tool with comprehensive error handling"""
    try:
        # Validate input
        if not param:
            raise ValueError("Parameter cannot be empty")

        # Execute logic
        result = process(param)

        # Return success
        return ToolResponse(
            content=result,
            is_success=True
        )

    except ValueError as e:
        return ToolResponse(
            content=f"Validation error: {str(e)}",
            is_success=False,
            metadata={"error_type": "ValidationError"}
        )

    except Exception as e:
        return ToolResponse(
            content=f"Unexpected error: {str(e)}",
            is_success=False,
            metadata={"error_type": type(e).__name__}
        )
```

### 4. Security Considerations

For `execute_python_code` or similar dangerous operations:

```python
import re

def execute_python_safe(code: str) -> ToolResponse:
    """Execute Python code with security checks"""
    # Dangerous patterns
    dangerous_patterns = [
        r'\bos\.system\b',
        r'\bsubprocess\b',
        r'\beval\b',
        r'\bexec\b',
        r'\b__import__\b',
        r'\bopen\(.+[\'"]w[\'"]\)',  # Writing to arbitrary files
        r'\brm\s',
        r'\bdel\s',
    ]

    # Check for dangerous operations
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            return ToolResponse(
                content=f"Security Error: Dangerous operation detected: {pattern}",
                is_success=False
            )

    # Execute in restricted environment
    try:
        # Use exec with limited globals
        exec_globals = {
            'pd': pd,
            'np': np,
            'pyecharts': pyecharts,
            '__builtins__': {}  # Restrict built-ins
        }
        exec(code, exec_globals)

        return ToolResponse(
            content="Code executed successfully",
            is_success=True
        )
    except Exception as e:
        return ToolResponse(
            content=f"Execution error: {str(e)}",
            is_success=False
        )
```

### 5. Async Best Practices

```python
# DO: Use async/await consistently
async def run_pipeline():
    msg = Msg(name="user", content="...", role="user")
    response1 = await agent1(msg)
    response2 = await agent2(response1)
    return response2

# Run from synchronous context
result = asyncio.run(run_pipeline())

# DON'T: Mix sync and async incorrectly
# ❌ response = agent(msg)  # Missing await
```

### 6. Memory Management

```python
# DO: Clear memory when starting new conversation
agent.memory.clear()

# DO: Limit memory size for long conversations
class LimitedMemory(InMemoryMemory):
    def __init__(self, max_size=50):
        super().__init__()
        self.max_size = max_size

    async def add(self, msg: Msg):
        await super().add(msg)
        messages = await self.get_memory()
        if len(messages) > self.max_size:
            # Keep only recent messages
            self.messages = messages[-self.max_size:]
```

### 7. Prompt Formatter Selection

**Important**: Formatter must match model type!

```python
# ✅ CORRECT
model = DashScopeChatModel(...)
agent = ReActAgent(
    model=model,
    formatter=DashScopeChatFormatter()  # Match!
)

# ✅ CORRECT
model = OpenAIChatModel(...)
agent = ReActAgent(
    model=model,
    formatter=OpenAIChatFormatter()  # Match!
)

# ❌ WRONG
model = DashScopeChatModel(...)
agent = ReActAgent(
    model=model,
    formatter=OpenAIChatFormatter()  # Mismatch!
)
```

### 8. Logging and Debugging

```python
# Enable verbose logging
agent = ReActAgent(
    name="Agent",
    verbose=True,  # Enable logging
    ...
)

# Use logging module
import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.info("Agent created successfully")
```

---

## Common Pitfalls

### ❌ Pitfall 1: Forgetting to Convert Pandas Types

```python
# ❌ WRONG: Pyecharts doesn't accept Pandas Series
bar.add_yaxis("Sales", df['sales'])  # Will fail!

# ✅ CORRECT: Convert to Python list
bar.add_yaxis("Sales", df['sales'].tolist())
```

### ❌ Pitfall 2: Not Using ToolResponse

```python
# ❌ WRONG
def my_tool(x: int) -> str:
    return "result"  # Agent won't recognize this!

# ✅ CORRECT
def my_tool(x: int) -> ToolResponse:
    return ToolResponse(content="result", is_success=True)
```

### ❌ Pitfall 3: Incomplete Docstrings

```python
# ❌ WRONG: LLM can't understand tool purpose
def process_data(file_path):
    """Process data"""
    ...

# ✅ CORRECT: Clear, detailed docstring
def process_data(file_path: str) -> ToolResponse:
    """Read and process CSV data file

    This tool reads a CSV file, cleans the data by removing
    null values, and returns summary statistics.

    Args:
        file_path (str): Absolute path to the CSV file

    Returns:
        ToolResponse: JSON string with summary statistics including
                     mean, median, and standard deviation
    """
    ...
```

### ❌ Pitfall 4: Ignoring Async Context

```python
# ❌ WRONG: Running async code without await
def main():
    msg = Msg(...)
    response = agent(msg)  # Missing await!

# ✅ CORRECT: Proper async handling
async def main():
    msg = Msg(...)
    response = await agent(msg)

# Run from sync context
asyncio.run(main())
```

---

## Quick Reference Cheat Sheet

```python
# 1. Import essentials
from agentscope.agent import ReActAgent, AgentBase
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.tool import ToolResponse, Toolkit

# 2. Create model
model = DashScopeChatModel(
    model_name="qwen-max",
    api_key=os.environ["DASHSCOPE_API_KEY"]
)

# 3. Define tool
def my_tool(param: str) -> ToolResponse:
    """Tool description

    Args:
        param (str): Parameter description
    """
    return ToolResponse(content="result", is_success=True)

# 4. Create toolkit
toolkit = Toolkit()
toolkit.register_tool_function(my_tool)

# 5. Create agent
agent = ReActAgent(
    name="MyAgent",
    sys_prompt="You are...",
    model=model,
    formatter=DashScopeChatFormatter(),
    toolkit=toolkit,
    memory=InMemoryMemory()
)

# 6. Invoke agent
msg = Msg(name="user", content="Question", role="user")
response = await agent(msg)

# 7. Access response
print(response.content)
```

---

## Project-Specific Mapping

For the **LocalInsight** project:

| Component | AgentScope Class | Configuration |
|-----------|------------------|---------------|
| Data Engineer Agent | `ReActAgent` | With toolkit (read_data_schema, execute_python_safe) |
| Business Analyst Agent | `AgentBase` | No toolkit, only conversational |
| Communication | `Msg` | Sequential pipeline (Engineer → Analyst) |
| Model | `DashScopeChatModel` | qwen-max with temperature=0.7 |
| Tools | Custom functions | All return `ToolResponse` |
| Memory | `InMemoryMemory` | Per-session, cleared on new upload |

---

## Additional Resources

- **Official Documentation**: https://doc.agentscope.io/
- **GitHub Repository**: https://github.com/agentscope-ai/agentscope
- **Examples Directory**: https://github.com/agentscope-ai/agentscope/tree/main/examples
- **API Reference**: https://doc.agentscope.io/api/

---

**Last Updated**: 2025-11-30
**Verified Against**: AgentScope main branch (latest)
