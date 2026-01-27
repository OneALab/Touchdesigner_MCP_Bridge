#!/usr/bin/env python3
"""
TouchDesigner MCP Server
Connects Claude Code to a running TouchDesigner instance via HTTP API
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from mcp.server.fastmcp import FastMCP

# Configuration
TD_HOST = "http://127.0.0.1:9980"

mcp = FastMCP("touchdesigner")


def td_request(endpoint: str, data: dict = None) -> dict:
    """Make a request to the TouchDesigner HTTP API."""
    url = f"{TD_HOST}{endpoint}"

    try:
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
        else:
            req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {"error": f"Cannot connect to TouchDesigner at {TD_HOST}. Make sure TD is running with the bridge server. Error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def td_ping() -> str:
    """Check if TouchDesigner is running and the bridge is active."""
    result = td_request("/ping")
    return json.dumps(result, indent=2)


@mcp.tool()
def td_list_operators(path: str = "/project1") -> str:
    """
    List all operators under a given path in TouchDesigner.

    Args:
        path: The path to list operators from (default: "/" for root)
    """
    result = td_request("/operators", {"path": path})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_get_operator_info(path: str) -> str:
    """
    Get detailed information about an operator including all its parameters.

    Args:
        path: The full path to the operator (e.g., "/project1/moviefilein1")
    """
    result = td_request("/operator/info", {"path": path})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_get_operator_parameters(op_type: str) -> str:
    """
    Get all available parameters for an operator type.
    Use this to discover correct parameter names before creating operators.

    Args:
        op_type: The operator type (e.g., "timerCHOP", "moviefileinTOP")
    """
    result = td_request("/operator/parameters", {"type": op_type})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_execute(code: str) -> str:
    """
    Execute Python code inside TouchDesigner.
    Set a variable named 'result' to return a value.

    Args:
        code: Python code to execute in TouchDesigner's Python environment

    Example:
        code = "result = op('/project1/timer1').par.length.eval()"
    """
    result = td_request("/execute", {"code": code})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_create_operator(parent: str, op_type: str, name: str, parameters: dict = None) -> str:
    """
    Create a new operator in TouchDesigner.

    Args:
        parent: Parent path where operator will be created (e.g., "/project1")
        op_type: Type of operator to create (e.g., "timerCHOP", "nullTOP")
        name: Name for the new operator
        parameters: Optional dict of parameter names and values to set

    Available types: timerCHOP, moviefileinTOP, constantTOP, switchTOP, nullTOP,
                    infoCHOP, selectCHOP, mergeCHOP, mathCHOP, renameCHOP,
                    scriptCHOP, oscinDAT, oscinCHOP, oscoutDAT, datexecDAT,
                    containerCOMP, baseCOMP, outTOP, outCHOP, textDAT, webserverDAT
    """
    result = td_request("/create", {
        "parent": parent,
        "type": op_type,
        "name": name,
        "parameters": parameters or {}
    })
    return json.dumps(result, indent=2)


@mcp.tool()
def td_set_parameter(path: str, parameter: str, value: str) -> str:
    """
    Set a parameter value on an operator.

    Args:
        path: Path to the operator (e.g., "/project1/timer1")
        parameter: Parameter name (e.g., "play", "length")
        value: Value to set
    """
    result = td_request("/set", {
        "path": path,
        "parameter": parameter,
        "value": value
    })
    return json.dumps(result, indent=2)


@mcp.tool()
def td_connect(from_path: str, to_path: str, from_index: int = 0, to_index: int = 0) -> str:
    """
    Connect two operators.

    Args:
        from_path: Path to source operator
        to_path: Path to destination operator
        from_index: Output connector index on source (default: 0)
        to_index: Input connector index on destination (default: 0)
    """
    result = td_request("/connect", {
        "from": from_path,
        "to": to_path,
        "from_index": from_index,
        "to_index": to_index
    })
    return json.dumps(result, indent=2)


@mcp.tool()
def td_delete_operator(path: str) -> str:
    """
    Delete an operator from the network.

    Args:
        path: Path to the operator to delete (e.g., "/project1/null1")
    """
    result = td_request("/delete", {"path": path})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_disconnect(path: str, input_index: int = 0) -> str:
    """
    Disconnect an input on an operator.

    Args:
        path: Path to the operator to disconnect
        input_index: Input connector index to disconnect (default: 0)
    """
    result = td_request("/disconnect", {
        "path": path,
        "input_index": input_index
    })
    return json.dumps(result, indent=2)


# === Text DAT Tools ===

@mcp.tool()
def td_get_text(path: str) -> str:
    """
    Get the text content of a Text DAT.

    Args:
        path: Path to the Text DAT (e.g., "/project1/text1")
    """
    result = td_request("/text/get", {"path": path})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_set_text(path: str, content: str) -> str:
    """
    Set the text content of a Text DAT.

    Args:
        path: Path to the Text DAT
        content: Text content to set
    """
    result = td_request("/text/set", {"path": path, "content": content})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_run_script(path: str) -> str:
    """
    Run a Text DAT as a Python script.

    Args:
        path: Path to the Text DAT containing Python code
    """
    result = td_request("/text/run", {"path": path})
    return json.dumps(result, indent=2)


# === Extension Tools ===

@mcp.tool()
def td_get_extension(path: str) -> str:
    """
    Get the extension code and info for a COMP.

    Args:
        path: Path to the COMP with an extension
    """
    result = td_request("/extension/get", {"path": path})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_set_extension(path: str, code: str, name: str = "Ext") -> str:
    """
    Set or update extension code on a COMP.

    Args:
        path: Path to the COMP
        code: Python extension class code
        name: Extension class name (default: "Ext")
    """
    result = td_request("/extension/set", {
        "path": path,
        "code": code,
        "name": name
    })
    return json.dumps(result, indent=2)


@mcp.tool()
def td_create_extension(path: str, class_name: str = "Ext", methods: list = None) -> str:
    """
    Create a new extension on a COMP with boilerplate code.

    Args:
        path: Path to the COMP
        class_name: Name for the extension class (default: "Ext")
        methods: Optional list of method names to stub out
    """
    result = td_request("/extension/create", {
        "path": path,
        "class_name": class_name,
        "methods": methods or []
    })
    return json.dumps(result, indent=2)


@mcp.tool()
def td_promote_parameter(comp_path: str, param_name: str, label: str = None, page: str = "Custom") -> str:
    """
    Add a custom parameter to a COMP.

    Args:
        comp_path: Path to the COMP
        param_name: Parameter name (lowercase, no spaces)
        label: Display label (default: param_name)
        page: Parameter page name (default: "Custom")
    """
    result = td_request("/extension/promote", {
        "path": comp_path,
        "param_name": param_name,
        "label": label or param_name,
        "page": page
    })
    return json.dumps(result, indent=2)


# === Package Management Tools ===

@mcp.tool()
def td_pip_install(package: str) -> str:
    """
    Install a pip package into TouchDesigner's Python environment.

    Args:
        package: Package name (e.g., "numpy", "requests==2.28.0")
    """
    result = td_request("/pip/install", {"package": package})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_list_packages() -> str:
    """
    List installed pip packages in TouchDesigner's Python environment.
    """
    result = td_request("/pip/list")
    return json.dumps(result, indent=2)


@mcp.tool()
def td_import_check(module: str) -> str:
    """
    Check if a Python module can be imported in TouchDesigner.

    Args:
        module: Module name to check (e.g., "numpy", "cv2")
    """
    result = td_request("/pip/check", {"module": module})
    return json.dumps(result, indent=2)


# === Debugging Tools ===

@mcp.tool()
def td_get_errors() -> str:
    """
    Get recent Python errors from TouchDesigner's textport.
    """
    result = td_request("/debug/errors")
    return json.dumps(result, indent=2)


@mcp.tool()
def td_get_cook_time(path: str) -> str:
    """
    Get cook time and performance info for an operator.

    Args:
        path: Path to the operator to profile
    """
    result = td_request("/debug/cooktime", {"path": path})
    return json.dumps(result, indent=2)


@mcp.tool()
def td_find_operators(pattern: str = "*", op_type: str = None, parent: str = "/project1") -> str:
    """
    Find operators matching a pattern.

    Args:
        pattern: Name pattern with wildcards (e.g., "null*", "*video*")
        op_type: Optional operator type filter (e.g., "baseCOMP", "nullTOP")
        parent: Parent path to search in (default: "/project1")
    """
    result = td_request("/find", {
        "pattern": pattern,
        "op_type": op_type,
        "parent": parent
    })
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
