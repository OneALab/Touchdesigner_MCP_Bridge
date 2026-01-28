# Claude Code Context - TouchDesigner MCP Bridge

## What This Is

An MCP (Model Context Protocol) bridge connecting Claude Code to TouchDesigner. You (Claude) can create operators, execute Python, query parameters, and build TD networks through this bridge.

## Installation Summary

**TouchDesigner side:**
1. Open TD → Create Text DAT → Paste `td_setup.py` → Run Script
2. Save the project

**Claude Code side:**
```bash
claude mcp add touchdesigner python "C:\path\to\mcp_server.py"
```

**Verify:** Open `http://127.0.0.1:9980/ping` in browser

## Architecture

```
Claude Code  <--MCP-->  mcp_server.py  <--HTTP:9980-->  TouchDesigner (webserverDAT)
```

- **mcp_server.py**: MCP server you connect through. Uses FastMCP. Translates tool calls to HTTP requests.
- **mcp_bridge.tox / td_setup.py**: Creates a webserverDAT inside TD at `/project1/mcp_bridge` that handles HTTP requests.

## Key Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server - your interface to TD |
| `td_setup.py` | Run inside TD to create the bridge |
| `mcp_bridge.tox` | Pre-built TD component (drag into projects) |
| `setup.py` | Interactive setup wizard for users |

## Available Tools

You have these MCP tools when connected:

- `td_ping` - Check connection
- `td_execute` - Run Python in TD (set `result` variable to return values)
- `td_list_operators` - List operators at a path
- `td_create_operator` - Create operators (limited types, use td_execute for others)
- `td_connect` - Connect operators
- `td_set_parameter` - Set parameter values
- `td_get_text` / `td_set_text` - Read/write Text DATs
- `td_get_extension` / `td_set_extension` - Manage COMP extensions

## Important Patterns

### Creating Operators

`td_create_operator` only supports these types:
```
timerCHOP, moviefileinTOP, constantTOP, switchTOP, nullTOP, infoCHOP,
selectCHOP, mergeCHOP, mathCHOP, renameCHOP, scriptCHOP, oscinDAT,
oscinCHOP, oscoutDAT, containerCOMP, baseCOMP, outTOP, outCHOP, textDAT, nullCHOP
```

For other types, use `td_execute`:
```python
bc = op('/project1/mycomp')
bc.create(videodeviceinTOP, 'webcam1')
bc.create(levelTOP, 'level1')
bc.create(cropTOP, 'crop1')
```

### Returning Values from td_execute

Set a variable named `result`:
```python
result = op('/project1/null1').width
```

### Extension Pattern (Storage-Based)

TD's native extension system can be buggy. Use storage pattern instead:
```python
# Create extension
bc = op('/project1/mycomp')
ext_dat = bc.op('MyExtension')
cls = ext_dat.module.MyExtensionClass
instance = cls(bc)
bc.store('ext', instance)

# Access extension
ext = bc.fetch('ext')
ext.MyMethod()
```

### Keyboard Callbacks

When setting up keyboardinCHOP callbacks:
1. Set `keyboard1.par.keys = 'space r e'` to track specific keys
2. Channel names will be `kspace`, `kr`, `ke` (prefixed with 'k')
3. Check with `if 'space' in channel.name` not `channel.name == 'space'`

## Testing the Bridge

1. Make sure TD is running with mcp_bridge
2. Test API in browser: `http://127.0.0.1:9980/ping`
3. Open Web UI: `http://127.0.0.1:9980/ui`
4. Use `td_ping` tool to verify connection

## Web UI System

The bridge includes a web-based UI that auto-generates controls from custom parameters.

### Accessing the Web UI

Open `http://127.0.0.1:9980/ui` in any browser. The UI will:
- Discover all COMPs with custom parameters
- Generate appropriate controls (sliders, toggles, menus, etc.)
- Send changes to TouchDesigner in real-time

### UI Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ui` | GET | Serve the web UI |
| `/ui/schema` | POST | Get parameter schema for a COMP |
| `/ui/discover` | POST | Find all COMPs with custom parameters |
| `/ui/set` | POST | Batch parameter changes |

### Parameter Style Mapping

| TD Style | HTML Control |
|----------|--------------|
| Float | Range slider + value display |
| Int | Range slider (step=1) |
| Toggle | Checkbox |
| Str/File/Folder | Text input |
| Menu/StrMenu | Dropdown select |
| Pulse | Button |
| RGB/RGBA | Color input (basic) |

### Example: Get UI Schema

```python
# Request
POST /ui/schema
{"path": "/project1/mycomp"}

# Response
{
  "success": true,
  "path": "/project1/mycomp",
  "name": "mycomp",
  "pages": [
    {
      "name": "Settings",
      "parameters": [
        {"name": "Speed", "style": "Float", "value": 1.0, "min": 0, "max": 10},
        {"name": "Active", "style": "Toggle", "value": 1}
      ]
    }
  ]
}
```

### UI Text DATs

The UI is stored in Text DATs within `/project1/mcp_bridge/`:
- `ui_index` - HTML template
- `ui_styles` - CSS styles
- `ui_app` - Main JavaScript application
- `ui_controls` - Parameter control rendering

You can edit these DATs to customize the UI appearance and behavior.

### WebSocket Real-Time Updates

The UI uses WebSockets for real-time parameter synchronization:

**Connection:** `ws://127.0.0.1:9980/ws`

**Message Types (Client → Server):**
- `subscribe` - Subscribe to parameter changes: `{"type": "subscribe", "paths": ["/project1/mycomp"]}`
- `set` - Set parameter value: `{"type": "set", "path": "/project1/mycomp", "parameter": "Speed", "value": 1.5}`
- `ping` - Keep-alive: `{"type": "ping"}`

**Message Types (Server → Client):**
- `connected` - Connection confirmed
- `subscribed` - Subscription confirmed with paths
- `change` - Parameter changed: `{"type": "change", "path": "...", "parameter": "...", "value": ...}`
- `error` - Error message

The web UI automatically connects via WebSocket and falls back to HTTP polling if WebSocket fails.

## Common Issues

- **"Unknown type" error**: The type isn't in td_create_operator's list. Use td_execute instead.
- **td_execute returns null**: The handler may need updating. Re-run td_setup.py in TD.
- **Parameters not received**: Some endpoints had body parsing issues. td_execute is most reliable.
- **Keyboard not triggering**: Check that the chopexecuteDAT's chop parameter points to the right keyboard CHOP.

## Development Guidelines

When working on this project, prioritize:

1. **User Experience**: The bridge should "just work." Minimize setup friction and provide clear feedback at every step.

2. **Error Handling**: Always validate inputs, catch exceptions, and return actionable error messages. Users should never see cryptic failures.

3. **Accuracy**: Test changes thoroughly. Verify operator creation, connections, and parameter setting actually work in TD before considering a feature complete.

4. **Practical Documentation**: Document what users actually need to know. Include working examples, common pitfalls, and troubleshooting steps. Avoid theoretical explanations without practical application.

5. **Defensive Coding**: Assume things will go wrong. Check if operators exist before connecting them. Verify paths are valid. Handle edge cases gracefully.

## Project Status

This is a standalone, shareable MCP bridge. Ready for GitHub distribution.
