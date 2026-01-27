# Claude Code Context - TouchDesigner MCP Bridge

## What This Is

An MCP (Model Context Protocol) bridge connecting Claude Code to TouchDesigner. You (Claude) can create operators, execute Python, query parameters, and build TD networks through this bridge.

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
2. Test in browser: `http://127.0.0.1:9980/ping`
3. Use `td_ping` tool to verify connection

## Common Issues

- **"Unknown type" error**: The type isn't in td_create_operator's list. Use td_execute instead.
- **td_execute returns null**: The handler may need updating. Re-run td_setup.py in TD.
- **Parameters not received**: Some endpoints had body parsing issues. td_execute is most reliable.
- **Keyboard not triggering**: Check that the chopexecuteDAT's chop parameter points to the right keyboard CHOP.

## Project Status

This is a standalone, shareable MCP bridge. Ready for GitHub distribution.
The original book scanner project that used this bridge was abandoned due to camera hardware issues (C920 autofocus problems).
