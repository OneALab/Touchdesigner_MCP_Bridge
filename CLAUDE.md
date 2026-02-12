# Claude Code Context - TouchDesigner MCP Bridge

## What This Is

An MCP (Model Context Protocol) bridge connecting Claude Code to TouchDesigner. You (Claude) can create operators, execute Python, query parameters, and build TD networks through this bridge. A modular architecture allows extending the bridge with modules for presets, cues, web UI, StreamDeck, OSC, and more.

## Repo Location

```
c:\Users\onea\Dropbox (Personal)\TouchDesigner\_mcp_bridge
```

## Installation Summary

**TouchDesigner side:**
1. Open TD → Create Text DAT → Paste `td_setup.py` → Run Script
2. Then paste `module_loader.py` into another Text DAT → Run Script
3. Save the project

Both scripts are **non-destructive** — re-running them updates code without wiping stored data (presets, cues, StreamDeck config).

**Claude Code side:**
```bash
claude mcp add touchdesigner python "c:\Users\onea\Dropbox (Personal)\TouchDesigner\_mcp_bridge\mcp_server.py"
```

**Verify:** Open `http://127.0.0.1:9980/ping` in browser

## Architecture

```
Claude Code  <--MCP-->  mcp_server.py  <--HTTP:9980-->  TD Core (webserverDAT)
                                                              |
                                                         module_registry
                                                              |
                                            <--HTTP:9981-->  TD Module Port (webserverDAT)
                                                              |
                                              ┌───────────────┼───────────────┐
                                              │               │               │
                                           mod_ui         mod_cues      mod_streamdeck
                                           mod_presets    mod_osc       mod_preview
                                           mod_timeline   mod_dmx(*)   mod_midi(*)
                                                          mod_media(*)
```

**Ports:**
- **9980** — Core MCP endpoints (operator CRUD, execute, parameters, text, extensions, `/modules`)
- **9981** — Module endpoints (UI, cues, presets, StreamDeck config, previews, etc.)

**(*) = future modules, stubs only**

## Key Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server - your interface to TD (dual port: 9980 core, 9981 modules) |
| `td_setup.py` | Run inside TD to create the core bridge + module registry |
| `module_loader.py` | Run inside TD to discover and load modules from `modules/` |
| `loader_script.py` | GitHub loader - fetches core + modules, runs setup |
| `mcp_bridge.tox` | Pre-built TD component (drag into projects) |
| `setup.py` | Interactive setup wizard for users |
| `modules/` | All module directories |

## Module System

### Module Structure

Each module lives in `modules/mod_<name>/` with:
- `__init__.py` — Module manifest (name, version, prefix, dependencies, etc.)
- `handler.py` — HTTP endpoint handlers + optional TD setup
- `assets/` — Optional static files (HTML/CSS/JS)

### Module Manifest (`__init__.py`)

```python
MODULE = {
    'name': 'cues',
    'version': '1.0.0',
    'description': 'Cue system with snapshots, actions, and autofollow',
    'prefix': '/cues',           # HTTP route prefix on port 9981
    'dependencies': ['presets'],  # Other modules this depends on
    'td_setup': True,            # Whether this module creates TD operators
    'mcp_tools': ['td_cue_go', 'td_cue_next', 'td_cue_back', 'td_cue_list'],
}
```

### Module Handler (`handler.py`)

```python
def setup(bridge_op):
    """Called once when module loads. Create any TD operators."""
    pass

def on_request(uri, method, body, request, response):
    """Handle HTTP requests matching this module's prefix. Returns dict."""
    pass

# Optional:
def on_websocket_open(client):
def on_websocket_close(client):
def on_websocket_receive(client, message):
```

### Loaded Modules

| Module | Prefix | Description |
|--------|--------|-------------|
| mod_presets | `/presets` | Save/load/delete parameter presets for COMPs |
| mod_cues | `/cues` | Cue system with snapshots, actions, autofollow |
| mod_preview | `/preview` | TOP thumbnails, CHOP data graphs |
| mod_timeline | `/timeline` | Play/pause/stop/jump/rate/loop |
| mod_ui | `/ui` | Web-based parameter control UI |
| mod_osc | `/osc` | OSC in/out, Companion integration (port 7000) |
| mod_streamdeck | `/streamdeck` | StreamDeck config, pages, service control |
| mod_dmx | `/dmx` | DMX output (stub) |
| mod_midi | `/midi` | MIDI in/out (stub) |
| mod_media | `/media` | Media clip management (stub) |

### Creating a New Module

1. Create `modules/mod_yourmodule/__init__.py` with MODULE dict
2. Create `modules/mod_yourmodule/handler.py` with `on_request()` function
3. Optionally add `setup(bridge_op)` if you need TD operators
4. Module is auto-discovered and loaded by `module_loader.py`

## Available MCP Tools

### Core Tools (port 9980)
- `td_ping` — Check connection
- `td_execute` — Run Python in TD (set `result` variable to return values)
- `td_list_operators` — List operators at a path
- `td_create_operator` — Create operators (limited types, use td_execute for others)
- `td_connect` — Connect operators
- `td_set_parameter` — Set parameter values
- `td_get_text` / `td_set_text` — Read/write Text DATs
- `td_get_extension` / `td_set_extension` — Manage COMP extensions
- `td_modules_list` — List loaded modules

### Module Tools (port 9981)
- `td_cue_list` — List all cues
- `td_cue_go` — Execute a specific cue
- `td_cue_next` / `td_cue_back` — Navigate cues
- `td_preset_list` — List presets
- `td_preset_save` / `td_preset_load` — Save/load presets
- `td_timeline_control` — Play/pause/stop/jump timeline

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
2. Test core API: `http://127.0.0.1:9980/ping`
3. List modules: `http://127.0.0.1:9980/modules`
4. Open Web UI: `http://127.0.0.1:9981/ui`
5. Use `td_ping` tool to verify MCP connection

## Web UI System

The bridge includes a web-based UI on port 9981 that auto-generates controls from custom parameters.

### Accessing the Web UI

Open `http://127.0.0.1:9981/ui` in any browser. The UI has tabs for:
- **Controls** — Component tree + parameter sliders/toggles/inputs
- **Previews** — Live TOP thumbnails and CHOP data graphs
- **Presets** — Save/load/delete parameter presets
- **Cues** — Cue list with snapshot editor, actions, autofollow
- **Stream Deck** — Button grid config, service control, page management

### UI Assets

Static files live in `modules/mod_ui/assets/`:
- `index.html` — HTML template
- `styles.css` — CSS styles
- `app.js` — Main JavaScript application
- `controls.js` — Parameter control rendering
- `preview.js` — Preview rendering (TOP images, CHOP canvases)

### WebSocket Real-Time Updates

**Connection:** `ws://127.0.0.1:9981/ws`

**Message Types (Client → Server):**
- `subscribe` — Subscribe to parameter changes
- `set` — Set parameter value
- `ping` — Keep-alive

**Message Types (Server → Client):**
- `connected` — Connection confirmed
- `change` — Parameter changed
- `error` — Error message

## Common Issues

- **"Unknown type" error**: The type isn't in td_create_operator's list. Use td_execute instead.
- **td_execute returns null**: The handler may need updating. Re-run td_setup.py in TD.
- **Parameters not received**: Some endpoints had body parsing issues. td_execute is most reliable.
- **Modules not loading**: Check `http://127.0.0.1:9980/modules` for module status. Re-run module_loader.py.
- **"Cannot find modules directory"**: `module_loader.py` can't find the `modules/` folder. The `__file__` variable inside TD Text DATs resolves to the TD operator path (e.g. `C:\project1\...`), NOT the filesystem path. The loader uses `project.folder` (TD's project folder) and hardcoded fallback paths. If it fails, check that the repo path in the candidates list matches your actual location.
- **Web UI not loading**: Ensure port 9981 is active. Check the module_port webserverDAT in TD.

## TD-Specific Gotchas

- **`__file__` is broken in TD**: Inside a Text DAT, `__file__` resolves to the TD operator path (e.g. `C:\project1\mcp_module_loader\`), not a real filesystem path. Never use it for filesystem operations. Use `project.folder` or hardcoded paths instead.
- **`importlib` works**: Python's import system works in TD. `module_loader.py` adds the `modules/` dir to `sys.path` and uses `importlib.import_module()` to load handlers.
- **Storage pattern**: Use `bridge.store('key', value)` / `bridge.fetch('key')` to pass data between modules at runtime. The loaded_modules dict is stored this way for the router to access.
- **Non-destructive setup**: Both `td_setup.py` and all module `setup()` functions use "create if not exists" patterns. Re-running them is safe and preserves data.

## Development Guidelines

When working on this project, prioritize:

1. **User Experience**: The bridge should "just work." Minimize setup friction and provide clear feedback at every step.

2. **Error Handling**: Always validate inputs, catch exceptions, and return actionable error messages. Users should never see cryptic failures.

3. **Accuracy**: Test changes thoroughly. Verify operator creation, connections, and parameter setting actually work in TD before considering a feature complete.

4. **Practical Documentation**: Document what users actually need to know. Include working examples, common pitfalls, and troubleshooting steps.

5. **Defensive Coding**: Assume things will go wrong. Check if operators exist before connecting them. Verify paths are valid. Handle edge cases gracefully.

6. **Module Isolation**: Each module should be self-contained. Modules communicate through the bridge storage, not direct imports. Dependencies are declared in the manifest.

## Project Status

Modular architecture with core + 10 modules (7 functional, 3 stubs). Ready for GitHub distribution.
