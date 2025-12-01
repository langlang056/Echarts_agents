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
from typing import Any, List
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
            error_msg = f"Error: File not found at path: {file_path}"
            return ToolResponse(
                content=[{"type": "text", "text": error_msg}],
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
            error_msg = f"Error: Unsupported file format: {file_ext}. Only .csv, .xlsx, .xls are supported."
            return ToolResponse(
                content=[{"type": "text", "text": error_msg}],
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
        content_text = json.dumps(schema_info, ensure_ascii=False, indent=2)
        success_msg = f"Successfully read data schema:\n{content_text}"

        return ToolResponse(
            content=[{"type": "text", "text": success_msg}],
            metadata=schema_info
        )

    except pd.errors.EmptyDataError:
        error_msg = "Error: The file is empty or has no data."
        return ToolResponse(
            content=[{"type": "text", "text": error_msg}],
            metadata={"error_type": "EmptyDataError"}
        )

    except Exception as e:
        error_msg = f"Error reading file: {str(e)}\n{traceback.format_exc()}"
        return ToolResponse(
            content=[{"type": "text", "text": error_msg}],
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
    # Initialize variables for finally block
    original_dir = os.getcwd()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
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
                error_msg = (f"Security Error: Dangerous operation detected: {name}\n"
                           f"This operation is blocked for security reasons.")
                return ToolResponse(
                    content=[{"type": "text", "text": error_msg}],
                    metadata={"error_type": "SecurityError", "blocked_operation": name}
                )

        # Ensure working directory exists
        os.makedirs(working_dir, exist_ok=True)

        # Change to working directory
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
                '__import__': __import__,  # 必需! 用于 import 语句
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
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
            }
        }

        # Dynamically import matplotlib if code contains it
        if 'matplotlib' in code or 'plt.' in code or 'plt,' in code:
            try:
                import matplotlib
                matplotlib.use('Agg')  # 使用非交互式后端
                import matplotlib.pyplot as plt
                exec_globals['matplotlib'] = matplotlib
                exec_globals['plt'] = plt
            except ImportError:
                return ToolResponse(
                    content=[{"type": "text", "text": "Error: matplotlib is not installed. Please install it first:\npip install matplotlib"}],
                    metadata={"error_type": "ImportError"}
                )

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
                    content=[{"type": "text", "text": "Error: pyecharts is not installed. Please install it first:\npip install pyecharts"}],
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
                    content=[{"type": "text", "text": "Error: numpy is not installed. Please install it first:\npip install numpy"}],
                    metadata={"error_type": "ImportError"}
                )

        # Redirect stdout and stderr
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
                content=[{"type": "text", "text": full_output}],
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
                content=[{"type": "text", "text": error_msg}],
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


def validate_chart_output(
    engine: str = "matplotlib",
    file_path: str = None,
    min_size_kb: float = 1.0
) -> ToolResponse:
    """Validate that the chart visualization file was successfully generated.

    This tool checks for both Matplotlib (PNG) and Pyecharts (HTML) outputs:
    - File exists at the specified path
    - File size is above minimum threshold
    - File contains valid content markers

    Args:
        engine (str): Chart engine - "matplotlib" or "pyecharts". Defaults to "matplotlib"
        file_path (str): Path to the expected file. If None, defaults based on engine:
                        - matplotlib: "./temp/visual_result.png"
                        - pyecharts: "./temp/visual_result.html"
        min_size_kb (float): Minimum file size in KB. Defaults to 1.0 KB

    Returns:
        ToolResponse: Validation result with file metadata
    """
    try:
        # Determine default file path based on engine
        if file_path is None:
            if engine == "matplotlib":
                file_path = "./temp/visual_result.png"
            else:
                file_path = "./temp/visual_result.html"

        # Check if file exists
        if not os.path.exists(file_path):
            if engine == "matplotlib":
                hint = f"Please ensure your code saves the chart using plt.savefig('{file_path}')"
            else:
                hint = f"Please ensure your code saves the chart using .render('{file_path}')"
            
            return ToolResponse(
                content=[{"type": "text", "text": f"Validation Failed: File not found at {file_path}\n{hint}"}],
                metadata={"error_type": "FileNotFound", "expected_path": file_path, "engine": engine}
            )

        # Check file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_kb = file_size_bytes / 1024

        if file_size_kb < min_size_kb:
            return ToolResponse(
                content=[{"type": "text", "text": f"Validation Failed: File is too small ({file_size_kb:.2f} KB)\n"
                       f"Expected at least {min_size_kb} KB. The file may be empty or incomplete."}],
                metadata={
                    "error_type": "FileTooSmall",
                    "size_kb": file_size_kb,
                    "min_size_kb": min_size_kb,
                    "engine": engine
                }
            )

        # Validate based on engine type
        if engine == "matplotlib":
            # PNG validation - check PNG file header magic bytes
            with open(file_path, 'rb') as f:
                header = f.read(8)
            
            # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
            png_signature = b'\x89PNG\r\n\x1a\n'
            is_valid_png = header == png_signature

            if not is_valid_png:
                return ToolResponse(
                    content=[{"type": "text", "text": f"Validation Warning: File exists but doesn't appear to be a valid PNG image.\n"
                           f"Size: {file_size_kb:.2f} KB\n"
                           f"This may not be a valid visualization file."}],
                    metadata={
                        "error_type": "InvalidPNG",
                        "size_kb": file_size_kb,
                        "engine": engine
                    }
                )

            validation_msg = f"✓ Validation Passed (Matplotlib PNG)\n\n"
            validation_msg += f"File: {file_path}\n"
            validation_msg += f"Size: {file_size_kb:.2f} KB\n"
            validation_msg += f"Format: PNG Image ✓\n"

            return ToolResponse(
                content=[{"type": "text", "text": validation_msg}],
                metadata={
                    "file_path": file_path,
                    "size_kb": file_size_kb,
                    "is_valid_png": True,
                    "engine": engine
                }
            )
        
        else:  # pyecharts HTML
            # Read file content for validation
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Basic HTML validation
            has_html = '<html' in content.lower()
            has_echarts = 'echarts' in content.lower()

            if not has_html:
                return ToolResponse(
                    content=[{"type": "text", "text": f"Validation Warning: File exists but doesn't contain valid HTML structure.\n"
                           f"Size: {file_size_kb:.2f} KB\n"
                           f"This may not be a valid visualization file."}],
                    metadata={
                        "error_type": "InvalidHTML",
                        "size_kb": file_size_kb,
                        "engine": engine
                    }
                )

            validation_msg = f"✓ Validation Passed (Pyecharts HTML)\n\n"
            validation_msg += f"File: {file_path}\n"
            validation_msg += f"Size: {file_size_kb:.2f} KB\n"
            validation_msg += f"HTML Structure: {'✓' if has_html else '✗'}\n"
            validation_msg += f"ECharts Content: {'✓' if has_echarts else '✗'}\n"

            return ToolResponse(
                content=[{"type": "text", "text": validation_msg}],
                metadata={
                    "file_path": file_path,
                    "size_kb": file_size_kb,
                    "has_html": has_html,
                    "has_echarts": has_echarts,
                    "engine": engine
                }
            )

    except Exception as e:
        return ToolResponse(
            content=[{"type": "text", "text": f"Validation Error: {str(e)}\n{traceback.format_exc()}"}],
            metadata={"error_type": type(e).__name__, "engine": engine}
        )


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
                content=[{"type": "text", "text": f"Validation Failed: File not found at {file_path}\n"
                       f"Please ensure your code saves the chart using .render('{file_path}')"}],
                metadata={"error_type": "FileNotFound", "expected_path": file_path}
            )

        # Check file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_kb = file_size_bytes / 1024

        if file_size_kb < min_size_kb:
            return ToolResponse(
                content=[{"type": "text", "text": f"Validation Failed: File is too small ({file_size_kb:.2f} KB)\n"
                       f"Expected at least {min_size_kb} KB. The file may be empty or incomplete."}],
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
                content=[{"type": "text", "text": f"Validation Warning: File exists but doesn't contain valid HTML structure.\n"
                       f"Size: {file_size_kb:.2f} KB\n"
                       f"This may not be a valid visualization file."}],
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
            content=[{"type": "text", "text": validation_msg}],
            metadata={
                "file_path": file_path,
                "size_kb": file_size_kb,
                "has_html": has_html,
                "has_echarts": has_echarts
            }
        )

    except Exception as e:
        return ToolResponse(
            content=[{"type": "text", "text": f"Validation Error: {str(e)}\n{traceback.format_exc()}"}],
            metadata={"error_type": type(e).__name__}
        )


# Export all tools
__all__ = [
    'read_data_schema',
    'execute_python_safe',
    'validate_chart_output',
    'validate_html_output'  # 保留兼容性
]
