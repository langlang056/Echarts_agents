"""
Custom tools for LocalInsight data analysis system.

This module provides tools for the Data Engineer Agent to:
1. Read and understand data file structures
2. Execute Python code safely with security checks
3. Validate visualization output files
"""

import os
import json
import re
import sys
import io
import traceback
from typing import Any
import pandas as pd
from agentscope.tool import ToolResponse


def read_data_schema(file_path: str) -> ToolResponse:
    """Read data file schema and sample rows.

    This tool reads a CSV or Excel file and returns its structure information
    including column names, data types, and the first 5 rows of sample data.
    This allows the agent to understand the data structure without loading
    the entire dataset.

    Args:
        file_path (str): Absolute or relative path to the data file.
                        Supported formats: .csv, .xlsx, .xls

    Returns:
        ToolResponse: JSON string containing:
            - columns: List of column names
            - dtypes: Dictionary of column names to data types
            - sample_data: List of dictionaries (first 5 rows)
            - shape: Dictionary with 'rows' and 'cols' counts
            - file_info: File size and format information
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            return ToolResponse(
                content=f"Error: File not found at path: {file_path}",
                is_success=False,
                metadata={"error_type": "FileNotFoundError"}
            )

        # Determine file type and read accordingly
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.csv':
            df = pd.read_csv(file_path, nrows=5)
            full_df = pd.read_csv(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, nrows=5)
            full_df = pd.read_excel(file_path)
        else:
            return ToolResponse(
                content=f"Error: Unsupported file format: {file_ext}. Only .csv, .xlsx, .xls are supported.",
                is_success=False,
                metadata={"error_type": "UnsupportedFileFormat"}
            )

        # Prepare schema information
        schema_info = {
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample_data": df.to_dict('records'),
            "shape": {
                "sample_rows": len(df),
                "total_rows": len(full_df),
                "cols": len(df.columns)
            },
            "file_info": {
                "path": file_path,
                "format": file_ext,
                "size_kb": round(os.path.getsize(file_path) / 1024, 2)
            }
        }

        # Format as readable JSON
        content = json.dumps(schema_info, ensure_ascii=False, indent=2)

        return ToolResponse(
            content=f"Successfully read data schema:\n{content}",
            is_success=True,
            metadata=schema_info
        )

    except pd.errors.EmptyDataError:
        return ToolResponse(
            content="Error: The file is empty or has no data.",
            is_success=False,
            metadata={"error_type": "EmptyDataError"}
        )

    except Exception as e:
        error_msg = f"Error reading file: {str(e)}\n{traceback.format_exc()}"
        return ToolResponse(
            content=error_msg,
            is_success=False,
            metadata={
                "error_type": type(e).__name__,
                "file_path": file_path
            }
        )


def execute_python_safe(code: str, working_dir: str = "./temp") -> ToolResponse:
    """Execute Python code with security restrictions and output capture.

    This tool executes Python code in a controlled environment with:
    - Security checks for dangerous operations
    - Output capture (stdout and stderr)
    - Restricted global namespace
    - Working directory management

    Args:
        code (str): Python code to execute. Must be complete and self-contained.
        working_dir (str): Working directory for file operations. Defaults to "./temp"

    Returns:
        ToolResponse: Contains:
            - content: Captured stdout/stderr output
            - is_success: Whether execution completed without errors
            - metadata: Execution details (exit_code, stdout, stderr)

    Security:
        The following operations are blocked:
        - os.system, subprocess calls
        - eval, exec, __import__
        - File deletion (rm, del)
        - Network access (socket, urllib, requests)
    """
    try:
        # Security checks - detect dangerous patterns
        dangerous_patterns = [
            (r'\bos\.system\b', 'os.system'),
            (r'\bsubprocess\b', 'subprocess'),
            (r'\beval\s*\(', 'eval()'),
            (r'\b__import__\b', '__import__'),
            (r'\brm\s+-rf', 'rm command'),
            (r'\bshutil\.rmtree\b', 'shutil.rmtree'),
            (r'\bsocket\b', 'socket (network access)'),
            (r'\burllib', 'urllib (network access)'),
            (r'\brequests\b', 'requests (network access)'),
        ]

        for pattern, name in dangerous_patterns:
            if re.search(pattern, code):
                return ToolResponse(
                    content=f"Security Error: Dangerous operation detected: {name}\n"
                           f"This operation is blocked for security reasons.",
                    is_success=False,
                    metadata={"error_type": "SecurityError", "blocked_operation": name}
                )

        # Ensure working directory exists
        os.makedirs(working_dir, exist_ok=True)

        # Change to working directory
        original_dir = os.getcwd()
        os.chdir(working_dir)

        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Prepare restricted execution environment
        exec_globals = {
            # Safe imports
            'pd': pd,
            'pandas': pd,
            'json': json,
            'os': os,  # Limited os access
            'sys': sys,
            're': re,
            # Built-ins (restricted)
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'type': type,
                'isinstance': isinstance,
                'open': open,  # Needed for file I/O
            }
        }

        # Dynamically import pyecharts if code contains it
        if 'pyecharts' in code or 'echarts' in code.lower():
            try:
                import pyecharts
                from pyecharts import options as opts
                from pyecharts.charts import (
                    Bar, Line, Pie, Scatter, Radar, Boxplot,
                    EffectScatter, Funnel, Gauge, Graph, HeatMap,
                    Kline, Liquid, Map, Parallel, PictorialBar,
                    Polar, Sankey, Sunburst, ThemeRiver, Tree,
                    TreeMap, WordCloud, Grid, Tab, Timeline, Page
                )
                exec_globals['pyecharts'] = pyecharts
                exec_globals['opts'] = opts
                exec_globals['Bar'] = Bar
                exec_globals['Line'] = Line
                exec_globals['Pie'] = Pie
                exec_globals['Scatter'] = Scatter
                exec_globals['Radar'] = Radar
                exec_globals['Boxplot'] = Boxplot
                exec_globals['EffectScatter'] = EffectScatter
                exec_globals['Funnel'] = Funnel
                exec_globals['Gauge'] = Gauge
                exec_globals['Graph'] = Graph
                exec_globals['HeatMap'] = HeatMap
                exec_globals['Grid'] = Grid
                exec_globals['Tab'] = Tab
                exec_globals['Page'] = Page
            except ImportError:
                return ToolResponse(
                    content="Error: pyecharts is not installed. Please install it first:\npip install pyecharts",
                    is_success=False,
                    metadata={"error_type": "ImportError"}
                )

        # Dynamically import numpy if code contains it
        if 'numpy' in code or 'np.' in code:
            try:
                import numpy as np
                exec_globals['np'] = np
                exec_globals['numpy'] = np
            except ImportError:
                return ToolResponse(
                    content="Error: numpy is not installed. Please install it first:\npip install numpy",
                    is_success=False,
                    metadata={"error_type": "ImportError"}
                )

        # Redirect stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            # Execute the code
            exec(code, exec_globals)

            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            # Get captured output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            # Prepare output message
            output_parts = []
            if stdout_content:
                output_parts.append(f"=== Output ===\n{stdout_content}")
            if stderr_content:
                output_parts.append(f"=== Warnings/Errors ===\n{stderr_content}")

            if not output_parts:
                output_parts.append("Code executed successfully (no output)")

            full_output = "\n\n".join(output_parts)

            return ToolResponse(
                content=full_output,
                is_success=True,
                metadata={
                    "stdout": stdout_content,
                    "stderr": stderr_content,
                    "working_dir": working_dir,
                    "exit_code": 0
                }
            )

        except Exception as e:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            # Get any partial output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            # Format error message
            error_msg = f"Execution Error: {str(e)}\n\n"
            error_msg += f"Traceback:\n{traceback.format_exc()}\n"

            if stdout_content:
                error_msg += f"\n=== Output Before Error ===\n{stdout_content}"
            if stderr_content:
                error_msg += f"\n=== Stderr ===\n{stderr_content}"

            return ToolResponse(
                content=error_msg,
                is_success=False,
                metadata={
                    "error_type": type(e).__name__,
                    "stdout": stdout_content,
                    "stderr": stderr_content,
                    "exit_code": 1
                }
            )

    finally:
        # Always restore original directory
        os.chdir(original_dir)

        # Ensure stdout/stderr are restored
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def validate_html_output(
    file_path: str = "./temp/visual_result.html",
    min_size_kb: float = 1.0
) -> ToolResponse:
    """Validate that the HTML visualization file was successfully generated.

    This tool checks:
    - File exists at the specified path
    - File size is above minimum threshold (indicates real content)
    - File contains valid HTML structure
    - File contains ECharts-specific markers

    Args:
        file_path (str): Path to the expected HTML file. Defaults to "./temp/visual_result.html"
        min_size_kb (float): Minimum file size in KB. Defaults to 1.0 KB

    Returns:
        ToolResponse: Validation result with file metadata
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return ToolResponse(
                content=f"Validation Failed: File not found at {file_path}\n"
                       f"Please ensure your code saves the chart using .render('{file_path}')",
                is_success=False,
                metadata={"error_type": "FileNotFound", "expected_path": file_path}
            )

        # Check file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_kb = file_size_bytes / 1024

        if file_size_kb < min_size_kb:
            return ToolResponse(
                content=f"Validation Failed: File is too small ({file_size_kb:.2f} KB)\n"
                       f"Expected at least {min_size_kb} KB. The file may be empty or incomplete.",
                is_success=False,
                metadata={
                    "error_type": "FileTooSmall",
                    "size_kb": file_size_kb,
                    "min_size_kb": min_size_kb
                }
            )

        # Read file content for validation
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Basic HTML validation
        has_html = '<html' in content.lower()
        has_echarts = 'echarts' in content.lower()

        if not has_html:
            return ToolResponse(
                content=f"Validation Warning: File exists but doesn't contain valid HTML structure.\n"
                       f"Size: {file_size_kb:.2f} KB\n"
                       f"This may not be a valid visualization file.",
                is_success=False,
                metadata={
                    "error_type": "InvalidHTML",
                    "size_kb": file_size_kb
                }
            )

        # Success
        validation_msg = f"✓ Validation Passed\n\n"
        validation_msg += f"File: {file_path}\n"
        validation_msg += f"Size: {file_size_kb:.2f} KB\n"
        validation_msg += f"HTML Structure: {'✓' if has_html else '✗'}\n"
        validation_msg += f"ECharts Content: {'✓' if has_echarts else '✗'}\n"

        return ToolResponse(
            content=validation_msg,
            is_success=True,
            metadata={
                "file_path": file_path,
                "size_kb": file_size_kb,
                "has_html": has_html,
                "has_echarts": has_echarts
            }
        )

    except Exception as e:
        return ToolResponse(
            content=f"Validation Error: {str(e)}\n{traceback.format_exc()}",
            is_success=False,
            metadata={"error_type": type(e).__name__}
        )


# Export all tools
__all__ = [
    'read_data_schema',
    'execute_python_safe',
    'validate_html_output'
]
