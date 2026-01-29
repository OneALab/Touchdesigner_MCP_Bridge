"""
MCP Bridge Loader - Fetches core + UI module from GitHub

Click the button in mcp_bridge_loader to run this script.
It will:
1. Fetch td_setup.py (core bridge) from GitHub
2. Fetch ui_handler.py (UI module) from GitHub
3. Execute both to set up the complete bridge with Web UI

Cache location: %APPDATA%/TouchDesigner/mcp_bridge_cache/
"""
import os
import urllib.request
import ssl

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/OneALab/Touchdesigner_MCP_Bridge/master"

FILES = {
    'td_setup.py': f"{GITHUB_RAW_BASE}/td_setup.py",
    'ui_handler.py': f"{GITHUB_RAW_BASE}/ui_handler.py",
}

def get_cache_dir():
    """Get platform-appropriate cache directory."""
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/Library/Application Support')
    cache_dir = os.path.join(base, 'TouchDesigner', 'mcp_bridge_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def fetch_from_github(url):
    """Fetch file from GitHub."""
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=15, context=ctx) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"  Failed to fetch: {e}")
        return None

def load_from_cache(filename):
    """Load file from local cache."""
    cache_path = os.path.join(get_cache_dir(), filename)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def save_to_cache(filename, content):
    """Save file to local cache."""
    cache_path = os.path.join(get_cache_dir(), filename)
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)

def fetch_file(filename, url):
    """Fetch file from GitHub or cache."""
    print(f"  Fetching {filename}...")
    content = fetch_from_github(url)
    if content:
        save_to_cache(filename, content)
        print(f"  ✓ {filename} (from GitHub)")
        return content
    else:
        content = load_from_cache(filename)
        if content:
            print(f"  ✓ {filename} (from cache)")
            return content
        else:
            print(f"  ✗ {filename} not available")
            return None

def setup_ui_module(ui_handler_code):
    """Set up the UI module after core is running."""
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        print("ERROR: Core bridge not found")
        return False

    # Get or create modules container
    modules = bridge.op('modules')
    if modules is None:
        modules = bridge.create(baseCOMP, 'modules')
        modules.nodeX = 200
        modules.nodeY = 0

    # Get or create UI module
    ui = modules.op('ui')
    if ui is None:
        ui = modules.create(baseCOMP, 'ui')
        ui.nodeX = 0
        ui.nodeY = 0

    # Create handler DAT with ui_handler code
    handler = ui.op('handler')
    if handler is None:
        handler = ui.create(textDAT, 'handler')
        handler.nodeX = 0
        handler.nodeY = 0
    handler.text = ui_handler_code

    # Create static UI DATs with defaults
    create_ui_dats(ui)

    print("  ✓ UI module installed")
    return True

def create_ui_dats(ui):
    """Create the static UI DATs."""
    dats = {
        'ui_index': (200, 0, get_ui_index()),
        'ui_styles': (400, 0, get_ui_styles()),
        'ui_app': (200, -150, get_ui_app()),
        'ui_controls': (400, -150, get_ui_controls()),
        'ui_preview': (600, 0, get_ui_preview()),
    }
    for name, (x, y, content) in dats.items():
        dat = ui.op(name)
        if dat is None:
            dat = ui.create(textDAT, name)
            dat.nodeX = x
            dat.nodeY = y
            dat.text = content

def get_ui_index():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TouchDesigner Control</title>
    <link rel="stylesheet" href="/ui/styles">
</head>
<body>
    <header>
        <h1 id="page-title">TouchDesigner Control</h1>
        <nav class="tabs">
            <button class="tab active" data-tab="controls">Controls</button>
            <button class="tab" data-tab="previews">Previews</button>
            <button class="tab" data-tab="presets">Presets</button>
            <button class="tab" data-tab="cues">Cues</button>
        </nav>
        <div id="connection-status" class="status disconnected">
            <span class="indicator"></span>
            <span class="text">Disconnected</span>
        </div>
    </header>
    <main>
        <div id="tab-controls" class="tab-content active">
            <aside id="component-list">
                <h3>Components</h3>
                <div id="components"></div>
            </aside>
            <section id="parameter-panel">
                <h3 id="selected-component">Select a component</h3>
                <div id="parameters"></div>
            </section>
        </div>
        <div id="tab-previews" class="tab-content">
            <div class="preview-grid" id="preview-grid"></div>
        </div>
        <div id="tab-presets" class="tab-content">
            <div id="presets-panel"></div>
        </div>
        <div id="tab-cues" class="tab-content">
            <div id="cues-panel"></div>
        </div>
    </main>
    <script src="/ui/controls"></script>
    <script src="/ui/preview"></script>
    <script src="/ui/app"></script>
</body>
</html>'''

def get_ui_styles():
    return ''':root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79b8ff;
    --success: #3fb950;
    --error: #f85149;
    --border: #30363d;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
}
header {
    display: flex;
    align-items: center;
    padding: 1rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    gap: 2rem;
}
h1 { font-size: 1.25rem; font-weight: 600; }
.tabs { display: flex; gap: 0; flex: 1; }
.tab {
    padding: 0.5rem 1rem;
    background: var(--bg-tertiary);
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
}
.tab:hover { color: var(--text-primary); }
.tab.active {
    background: var(--bg-primary);
    color: var(--accent);
    border-bottom: 2px solid var(--accent);
}
.status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
}
.status .indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--error);
}
.status.connected .indicator { background: var(--success); }
main { display: flex; height: calc(100vh - 60px); }
.tab-content { display: none; width: 100%; }
.tab-content.active { display: flex; }
#component-list {
    width: 250px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    padding: 1rem;
    overflow-y: auto;
}
#component-list h3 { margin-bottom: 1rem; color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; }
.component-item {
    padding: 0.5rem;
    margin-bottom: 0.25rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
}
.component-item:hover { background: var(--bg-tertiary); }
.component-item.selected { background: var(--accent); color: var(--bg-primary); }
#parameter-panel { flex: 1; padding: 1rem; overflow-y: auto; }
.param-group { margin-bottom: 1.5rem; }
.param-group h4 { color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.5rem; }
.param-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
    padding: 0.5rem;
    background: var(--bg-secondary);
    border-radius: 4px;
}
.param-label { width: 120px; font-size: 0.875rem; }
.param-control { flex: 1; display: flex; align-items: center; gap: 0.5rem; }
input[type="range"] { flex: 1; }
input[type="text"], input[type="number"], select {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 0.375rem 0.5rem;
    border-radius: 4px;
}
button {
    background: var(--accent);
    color: var(--bg-primary);
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
}
button:hover { background: var(--accent-hover); }
.preview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
    padding: 1rem;
    width: 100%;
}
.top-preview-wrapper {
    background: var(--bg-secondary);
    border-radius: 8px;
    overflow: hidden;
}
.top-preview { width: 100%; display: block; }
.chop-preview { width: 100%; height: 80px; }'''

def get_ui_app():
    return '''let ws = null;
let selectedComponent = null;
let components = [];

document.addEventListener('DOMContentLoaded', init);

async function init() {
    setupTabs();
    await loadComponents();
    connectWebSocket();
}

function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
        });
    });
}

async function loadComponents() {
    try {
        const res = await fetch('/ui/discover');
        const data = await res.json();
        if (data.success) {
            components = data.components;
            renderComponentList();
        }
    } catch (e) {
        console.error('Failed to load components:', e);
    }
}

function renderComponentList() {
    const container = document.getElementById('components');
    container.innerHTML = components.map(c =>
        '<div class="component-item" data-path="' + c.path + '" onclick="selectComponent(\\'' + c.path + '\\')">' + c.name + '</div>'
    ).join('');
}

async function selectComponent(path) {
    selectedComponent = path;
    document.querySelectorAll('.component-item').forEach(el => {
        el.classList.toggle('selected', el.dataset.path === path);
    });
    await loadComponentParameters(path);
}

async function loadComponentParameters(path) {
    try {
        const res = await fetch('/ui/schema', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: path})
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('selected-component').textContent = data.name;
            renderParameters(data);
        }
    } catch (e) {
        console.error('Failed to load parameters:', e);
    }
}

function renderParameters(schema) {
    const container = document.getElementById('parameters');
    let html = '';
    for (const page of schema.pages || []) {
        html += '<div class="param-group"><h4>' + page.name + '</h4>';
        for (const param of page.parameters || []) {
            html += renderParameter(param);
        }
        html += '</div>';
    }
    container.innerHTML = html || '<p>No custom parameters</p>';
}

function renderParameter(param) {
    let control = '';
    const id = 'param-' + param.name;
    if (param.style === 'Float' || param.style === 'Int') {
        const step = param.style === 'Int' ? 1 : 0.01;
        control = '<input type="range" id="' + id + '" min="' + param.min + '" max="' + param.max + '" step="' + step + '" value="' + param.value + '" oninput="updateValue(this)" onchange="setParameter(\\'' + param.name + '\\', this.value)"><span id="' + id + '-val">' + param.value + '</span>';
    } else if (param.style === 'Toggle') {
        control = '<input type="checkbox" id="' + id + '" ' + (param.value ? 'checked' : '') + ' onchange="setParameter(\\'' + param.name + '\\', this.checked ? 1 : 0)">';
    } else if (param.style === 'Str') {
        control = '<input type="text" id="' + id + '" value="' + (param.value || '') + '" onchange="setParameter(\\'' + param.name + '\\', this.value)">';
    } else if (param.style === 'Pulse') {
        control = '<button onclick="pulseParameter(\\'' + param.name + '\\')">Pulse</button>';
    } else {
        control = '<input type="text" id="' + id + '" value="' + (param.value || '') + '" onchange="setParameter(\\'' + param.name + '\\', this.value)">';
    }
    return '<div class="param-row"><span class="param-label">' + (param.label || param.name) + '</span><div class="param-control">' + control + '</div></div>';
}

function updateValue(input) {
    const span = document.getElementById(input.id + '-val');
    if (span) span.textContent = input.value;
}

async function setParameter(name, value) {
    if (!selectedComponent) return;
    try {
        await fetch('/parameter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedComponent, name: name, value: value})
        });
    } catch (e) {
        console.error('Failed to set parameter:', e);
    }
}

async function pulseParameter(name) {
    if (!selectedComponent) return;
    try {
        await fetch('/parameter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedComponent, name: name, pulse: true})
        });
    } catch (e) {
        console.error('Failed to pulse:', e);
    }
}

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(protocol + '//' + location.host + '/ws');
    ws.onopen = () => {
        document.getElementById('connection-status').className = 'status connected';
        document.querySelector('#connection-status .text').textContent = 'Connected';
    };
    ws.onclose = () => {
        document.getElementById('connection-status').className = 'status disconnected';
        document.querySelector('#connection-status .text').textContent = 'Disconnected';
        setTimeout(connectWebSocket, 2000);
    };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'parameterChange' && data.path === selectedComponent) {
            const input = document.getElementById('param-' + data.name);
            if (input) {
                if (input.type === 'checkbox') input.checked = !!data.value;
                else input.value = data.value;
            }
            const span = document.getElementById('param-' + data.name + '-val');
            if (span) span.textContent = data.value;
        }
    };
}'''

def get_ui_controls():
    return '// Additional UI controls'

def get_ui_preview():
    return '''let previewIntervals = [];

async function loadPreviews() {
    stopAllPreviews();
    const grid = document.getElementById('preview-grid');
    grid.innerHTML = '<p>Loading...</p>';
    try {
        const res = await fetch('/preview/discover');
        const data = await res.json();
        if (!data.success) {
            grid.innerHTML = '<p>No previews found</p>';
            return;
        }
        grid.innerHTML = '';
        for (const top of data.tops || []) {
            createTopPreview(top, grid);
        }
    } catch (e) {
        grid.innerHTML = '<p>Error loading previews</p>';
    }
}

function createTopPreview(top, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'top-preview-wrapper';
    wrapper.innerHTML = '<div style="padding:0.5rem;font-size:0.75rem;">' + top.name + '</div><img class="top-preview" src="/preview/top?path=' + encodeURIComponent(top.path) + '&t=' + Date.now() + '">';
    const img = wrapper.querySelector('img');
    const interval = setInterval(() => {
        img.src = '/preview/top?path=' + encodeURIComponent(top.path) + '&t=' + Date.now();
    }, 500);
    previewIntervals.push(interval);
    container.appendChild(wrapper);
}

function stopAllPreviews() {
    previewIntervals.forEach(i => clearInterval(i));
    previewIntervals = [];
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('[data-tab="previews"]');
    if (btn) btn.addEventListener('click', loadPreviews);
});'''

def run_setup():
    """Main entry point - fetch core + UI, set up complete bridge."""
    print("=" * 60)
    print("MCP Bridge Loader")
    print("=" * 60)

    # Fetch files
    print("Fetching from GitHub...")
    td_setup = fetch_file('td_setup.py', FILES['td_setup.py'])
    ui_handler = fetch_file('ui_handler.py', FILES['ui_handler.py'])

    if not td_setup:
        print("ERROR: Cannot load td_setup.py")
        print("Check internet connection or download manually.")
        return

    # Run core setup
    print("-" * 60)
    print("Setting up core bridge...")
    try:
        exec(td_setup, globals())
        print("  ✓ Core bridge created")
    except Exception as e:
        import traceback
        print(f"ERROR setting up core: {e}")
        traceback.print_exc()
        return

    # Set up UI module
    print("-" * 60)
    print("Setting up UI module...")
    if ui_handler:
        try:
            setup_ui_module(ui_handler)
        except Exception as e:
            import traceback
            print(f"WARNING: UI module setup failed: {e}")
            traceback.print_exc()
    else:
        print("  (UI module not available - core only)")

    print("=" * 60)
    print("MCP Bridge setup complete!")
    print("  Core: http://127.0.0.1:9980/ping")
    print("  Web UI: http://127.0.0.1:9980/ui")
    print("=" * 60)

# Run when script is executed
run_setup()
