# TouchDesigner MCP Bridge

Connect [Claude Code](https://claude.ai/code) (or any MCP-compatible LLM) to a running TouchDesigner instance. Build TD networks, execute Python, query parameters, and create operators - all through natural language.

## What is this?

This is an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that bridges Claude Code and TouchDesigner. It allows Claude to:

- Create and connect operators
- Execute Python code inside TD
- Query real parameter names and values
- Build complete networks interactively
- Debug errors from the textport
- Manage extensions and custom parameters

## Quick Start

### 1. Clone or Download

```bash
git clone https://github.com/OneALab/Touchdesigner_MCP_Bridge.git
cd Touchdesigner_MCP_Bridge
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up TouchDesigner

**Option A: Auto-Updating Loader (Recommended)**
1. Open TouchDesigner
2. Drag `mcp_bridge_loader.tox` into your project
3. The loader automatically fetches the latest `td_setup.py` from GitHub
4. Works offline using a local cache after first run
5. Save your project

**Option B: Static Component**
1. Open TouchDesigner
2. Drag `mcp_bridge.tox` into your project
3. Save your project

**Option C: Run setup script manually**
1. Open TouchDesigner
2. Create a Text DAT
3. Paste contents of `td_setup.py`
4. Right-click → Run Script

### 4. Configure Claude Code

```bash
claude mcp add touchdesigner -- python /path/to/mcp_server.py
```

Replace `/path/to/` with the actual path to where you cloned this repo.

### 5. Restart Claude Code

Restart Claude Code to load the new MCP server.

### 6. Test It

In Claude Code, say: "Ping TouchDesigner"

## Alternative: Interactive Setup

Run the guided setup wizard:

```bash
python setup.py
```

This will walk you through both TouchDesigner and Claude Code configuration.

## Available Tools

### Core Tools
| Tool | Description |
|------|-------------|
| `td_ping` | Check if TouchDesigner is connected |
| `td_list_operators` | List operators at a path |
| `td_get_operator_info` | Get full operator details and parameters |
| `td_execute` | Run Python code in TouchDesigner |
| `td_create_operator` | Create a new operator |
| `td_set_parameter` | Set a parameter value |
| `td_connect` | Connect two operators |
| `td_delete_operator` | Delete an operator |
| `td_disconnect` | Disconnect an operator's input |
| `td_find_operators` | Search for operators by pattern |

### Text DAT Tools
| Tool | Description |
|------|-------------|
| `td_get_text` | Read content from a Text DAT |
| `td_set_text` | Write content to a Text DAT |
| `td_run_script` | Execute a Text DAT as Python |

### Extension Development
| Tool | Description |
|------|-------------|
| `td_get_extension` | Get extension code from a COMP |
| `td_set_extension` | Set/update extension code on a COMP |
| `td_create_extension` | Create extension with boilerplate |
| `td_promote_parameter` | Add custom parameter to a COMP |

### Package Management
| Tool | Description |
|------|-------------|
| `td_pip_install` | Install pip package in TD's Python |
| `td_list_packages` | List installed packages |
| `td_import_check` | Check if module can be imported |

### Debugging
| Tool | Description |
|------|-------------|
| `td_get_errors` | Get recent errors from textport |
| `td_get_cook_time` | Get operator performance info |

## Web UI

The bridge includes a browser-based control panel that auto-generates controls from custom parameters.

**Open:** `http://127.0.0.1:9980/ui`

- Discovers all COMPs with custom parameters
- Generates sliders, toggles, menus, buttons automatically
- Changes update TouchDesigner in real-time

To test: Create a baseCOMP, add custom parameters (Customize Component), then refresh the web UI.

## Example Usage

Once connected, you can ask Claude things like:

- "Create a movie file in TOP and connect it to a null"
- "What parameters does the noise TOP have?"
- "Write a script that randomizes the color of constant1"
- "Debug why my CHOP execute isn't triggering"
- "Build me an audio-reactive visual system"

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Claude Code   │  MCP    │   mcp_server.py │  HTTP   │  TouchDesigner  │
│   (LLM Client)  │◄───────►│   (MCP Server)  │◄───────►│  (Web Server)   │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                              port 9980
```

- **mcp_server.py**: MCP server that Claude Code connects to
- **mcp_bridge.tox**: TouchDesigner component with HTTP handler
- **td_setup.py**: Alternative script to create the bridge manually

## Troubleshooting

### "Cannot connect to TouchDesigner"
- Make sure TouchDesigner is running
- Check that `/project1/mcp_bridge/webserver` exists and is active
- Verify port 9980 is not blocked by firewall
- Test: `http://127.0.0.1:9980/ping` in a browser

### MCP server not found in Claude Code
- Restart Claude Code after configuration
- Check the path in your MCP settings
- Make sure Python is in your PATH
- Test: `python mcp_server.py` directly to see errors

### td_execute returns null for results
- Re-run `td_setup.py` in TouchDesigner to update the handler
- Or drag in a fresh `mcp_bridge.tox`

## Files

| File | Description |
|------|-------------|
| `mcp_server.py` | MCP server that Claude Code connects to |
| `mcp_bridge_loader.tox` | Auto-updating loader (fetches latest from GitHub) |
| `mcp_bridge.tox` | Pre-built TD component (static version) |
| `td_setup.py` | Script to create the bridge in TD |
| `loader_script.py` | Source for the loader (reference only) |
| `setup.py` | Interactive setup wizard |
| `requirements.txt` | Python dependencies |

## Requirements

- TouchDesigner 2023+ (tested on 2024.x)
- Python 3.10+
- Claude Code (or any MCP-compatible client)

## Contributing

Pull requests welcome! Please test changes with both the .tox and td_setup.py methods.

## License

MIT License - see [LICENSE](LICENSE) for details.
