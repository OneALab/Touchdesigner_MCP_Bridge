"""
MCP Bridge UI Module Loader - Fetches and loads ui_handler.py from GitHub

This script should be placed in a Text DAT inside the UI module.
When run, it will:
1. Fetch the latest ui_handler.py from GitHub
2. Cache it locally for offline use
3. Load the script into the handler DAT
4. Create static UI DATs if they don't exist

To use:
1. Place this in a Text DAT named 'loader' inside /project1/mcp_bridge/modules/ui
2. Run the script to set up the UI module
"""
import os
import urllib.request
import ssl

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/OneALab/Touchdesigner_MCP_Bridge/master"
UI_HANDLER_URL = f"{GITHUB_RAW_BASE}/ui_handler.py"

def get_cache_path(filename):
    """Get platform-appropriate cache directory."""
    if os.name == 'nt':  # Windows
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:  # macOS/Linux
        base = os.path.expanduser('~/Library/Application Support')
    cache_dir = os.path.join(base, 'TouchDesigner', 'mcp_bridge_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, filename)

def fetch_from_github(url):
    """Fetch file from GitHub."""
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=10, context=ctx) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch from GitHub: {e}")
        return None

def load_from_cache(filename):
    """Load file from local cache."""
    cache_path = get_cache_path(filename)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def save_to_cache(filename, content):
    """Save file to local cache."""
    cache_path = get_cache_path(filename)
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Cached {filename} to: {cache_path}")

def get_ui_module():
    """Get or create the UI module component."""
    # Check for modules container
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        print("ERROR: MCP bridge not found. Run td_setup.py first.")
        return None

    modules = bridge.op('modules')
    if modules is None:
        modules = bridge.create(baseCOMP, 'modules')
        modules.nodeX = 200
        modules.nodeY = 0
        print("Created modules container")

    ui = modules.op('ui')
    if ui is None:
        ui = modules.create(baseCOMP, 'ui')
        ui.nodeX = 0
        ui.nodeY = 0
        print("Created UI module")

    return ui

def setup_handler(ui_module, handler_code):
    """Set up the handler DAT with the UI handler code."""
    handler = ui_module.op('handler')
    if handler is None:
        handler = ui_module.create(textDAT, 'handler')
        handler.nodeX = 0
        handler.nodeY = 0

    handler.text = handler_code
    print("Handler DAT updated")
    return handler

def setup_static_dats(ui_module):
    """Create static DATs for UI assets if they don't exist."""
    # These will be populated from GitHub or use embedded defaults
    static_dats = {
        'ui_index': {'nodeX': 200, 'nodeY': 0, 'default': get_default_index()},
        'ui_styles': {'nodeX': 400, 'nodeY': 0, 'default': get_default_styles()},
        'ui_app': {'nodeX': 200, 'nodeY': -150, 'default': get_default_app()},
        'ui_controls': {'nodeX': 400, 'nodeY': -150, 'default': get_default_controls()},
        'ui_preview': {'nodeX': 600, 'nodeY': 0, 'default': get_default_preview()},
    }

    for name, config in static_dats.items():
        dat = ui_module.op(name)
        if dat is None:
            dat = ui_module.create(textDAT, name)
            dat.nodeX = config['nodeX']
            dat.nodeY = config['nodeY']
            dat.text = config['default']
            print(f"Created {name}")
        else:
            print(f"Found existing {name}")

    return True

def get_default_index():
    """Default HTML for ui_index."""
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

def get_default_styles():
    """Default CSS for ui_styles."""
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

def get_default_app():
    """Default JavaScript for ui_app."""
    return '''// MCP Bridge UI - Main Application
let ws = null;
let selectedComponent = null;
let components = [];

// Initialize
document.addEventListener('DOMContentLoaded', init);

async function init() {
    setupTabs();
    await loadComponents();
    connectWebSocket();
    loadProjectInfo();
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
        `<div class="component-item" data-path="${c.path}" onclick="selectComponent('${c.path}')">${c.name}</div>`
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
        const res = await fetch('/ui/schema?path=' + encodeURIComponent(path));
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
    for (const [pageName, params] of Object.entries(schema.pages || {})) {
        html += `<div class="param-group"><h4>${pageName}</h4>`;
        for (const param of params) {
            html += renderParameter(param);
        }
        html += '</div>';
    }
    container.innerHTML = html || '<p>No custom parameters</p>';
}

function renderParameter(param) {
    let control = '';
    const id = 'param-' + param.name;
    switch (param.style) {
        case 'Float':
        case 'Int':
            control = `<input type="range" id="${id}" min="${param.min}" max="${param.max}" step="${param.style === 'Int' ? 1 : 0.01}" value="${param.value}" onchange="setParameter('${param.name}', this.value)"><span id="${id}-val">${param.value}</span>`;
            break;
        case 'Toggle':
            control = `<input type="checkbox" id="${id}" ${param.value ? 'checked' : ''} onchange="setParameter('${param.name}', this.checked ? 1 : 0)">`;
            break;
        case 'Str':
            control = `<input type="text" id="${id}" value="${param.value || ''}" onchange="setParameter('${param.name}', this.value)">`;
            break;
        case 'Menu':
        case 'StrMenu':
            control = `<select id="${id}" onchange="setParameter('${param.name}', this.value)">${(param.menuLabels || []).map((label, i) => `<option value="${param.menuNames[i]}" ${param.value == param.menuNames[i] ? 'selected' : ''}>${label}</option>`).join('')}</select>`;
            break;
        case 'Pulse':
            control = `<button onclick="pulseParameter('${param.name}')">Pulse</button>`;
            break;
        default:
            control = `<input type="text" id="${id}" value="${param.value || ''}" onchange="setParameter('${param.name}', this.value)">`;
    }
    return `<div class="param-row"><span class="param-label">${param.label || param.name}</span><div class="param-control">${control}</div></div>`;
}

async function setParameter(name, value) {
    if (!selectedComponent) return;
    try {
        await fetch('/parameter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedComponent, name, value})
        });
        const valSpan = document.getElementById('param-' + name + '-val');
        if (valSpan) valSpan.textContent = value;
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
            body: JSON.stringify({path: selectedComponent, name, pulse: true})
        });
    } catch (e) {
        console.error('Failed to pulse parameter:', e);
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
            updateParameterUI(data.name, data.value);
        }
    };
}

function updateParameterUI(name, value) {
    const input = document.getElementById('param-' + name);
    if (input) {
        if (input.type === 'checkbox') input.checked = !!value;
        else input.value = value;
    }
    const valSpan = document.getElementById('param-' + name + '-val');
    if (valSpan) valSpan.textContent = value;
}

async function loadProjectInfo() {
    try {
        const res = await fetch('/ui/info');
        const info = await res.json();
        if (info.projectName) {
            document.getElementById('page-title').textContent = info.projectName;
            document.title = info.projectName;
        }
    } catch (e) {}
}'''

def get_default_controls():
    """Default JavaScript for ui_controls."""
    return '''// MCP Bridge UI - Parameter Controls
// Additional control utilities

function createSlider(param, container) {
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
        <span class="param-label">${param.label || param.name}</span>
        <div class="param-control">
            <input type="range" min="${param.min}" max="${param.max}" step="${param.style === 'Int' ? 1 : 0.01}" value="${param.value}">
            <span class="value-display">${param.value}</span>
        </div>
    `;
    const slider = row.querySelector('input');
    const display = row.querySelector('.value-display');
    slider.addEventListener('input', () => {
        display.textContent = slider.value;
    });
    slider.addEventListener('change', () => {
        setParameter(param.name, slider.value);
    });
    container.appendChild(row);
    return slider;
}'''

def get_default_preview():
    """Default JavaScript for ui_preview."""
    return '''// MCP Bridge UI - Preview Functions

let previewIntervals = [];

async function loadPreviews() {
    stopAllPreviews();
    const grid = document.getElementById('preview-grid');
    grid.innerHTML = '<p>Loading previews...</p>';

    try {
        const res = await fetch('/preview/discover');
        const data = await res.json();
        if (!data.success) {
            grid.innerHTML = '<p>No previewable operators found</p>';
            return;
        }

        grid.innerHTML = '';

        // TOP previews
        for (const top of data.tops || []) {
            createTopPreview(top, grid);
        }

        // CHOP indicators
        for (const chop of data.chops || []) {
            createChopIndicator(chop, grid);
        }
    } catch (e) {
        console.error('Failed to load previews:', e);
        grid.innerHTML = '<p>Error loading previews</p>';
    }
}

function createTopPreview(top, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'top-preview-wrapper';
    wrapper.innerHTML = `
        <div class="preview-header">${top.name} (${top.type})</div>
        <img class="top-preview" src="/preview/top?path=${encodeURIComponent(top.path)}&t=${Date.now()}">
    `;
    const img = wrapper.querySelector('img');
    const interval = setInterval(() => {
        img.src = `/preview/top?path=${encodeURIComponent(top.path)}&t=${Date.now()}`;
    }, 500);
    previewIntervals.push(interval);
    container.appendChild(wrapper);
}

function createChopIndicator(chop, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'chop-preview-wrapper';
    wrapper.innerHTML = `
        <div class="preview-header">${chop.name} (${chop.type})</div>
        <canvas class="chop-preview" width="300" height="80"></canvas>
    `;
    const canvas = wrapper.querySelector('canvas');
    const ctx = canvas.getContext('2d');

    async function draw() {
        try {
            const res = await fetch(`/preview/chop?path=${encodeURIComponent(chop.path)}`);
            const data = await res.json();
            if (data.error) return;

            ctx.fillStyle = '#161b22';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const colors = ['#58a6ff', '#f85149', '#3fb950', '#d29922'];
            (data.channels || []).forEach((ch, i) => {
                ctx.strokeStyle = colors[i % colors.length];
                ctx.beginPath();
                const vals = ch.values || [];
                vals.forEach((v, x) => {
                    const range = (ch.max - ch.min) || 1;
                    const y = canvas.height - ((v - ch.min) / range) * canvas.height;
                    const px = x * (canvas.width / vals.length);
                    x === 0 ? ctx.moveTo(px, y) : ctx.lineTo(px, y);
                });
                ctx.stroke();
            });
        } catch (e) {}
    }

    draw();
    const interval = setInterval(draw, 100);
    previewIntervals.push(interval);
    container.appendChild(wrapper);
}

function stopAllPreviews() {
    previewIntervals.forEach(i => clearInterval(i));
    previewIntervals = [];
}

// Load previews when tab is shown
document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[data-tab="previews"]').addEventListener('click', loadPreviews);
});'''

def run_ui_setup():
    """Main entry point - fetch, cache, and set up UI module."""
    print("=" * 60)
    print("MCP Bridge UI Module Loader")
    print("=" * 60)
    print(f"Fetching from: {UI_HANDLER_URL}")

    # Get or create UI module
    ui_module = get_ui_module()
    if ui_module is None:
        return

    # Try GitHub first
    handler_code = fetch_from_github(UI_HANDLER_URL)

    if handler_code:
        save_to_cache('ui_handler.py', handler_code)
        print("Successfully fetched latest UI handler from GitHub")
    else:
        # Fall back to cache
        handler_code = load_from_cache('ui_handler.py')
        if handler_code:
            print("Using cached version (GitHub unreachable)")
        else:
            print("ERROR: Cannot fetch from GitHub and no cached version available")
            print(f"Please manually download from: {UI_HANDLER_URL}")
            return

    # Set up the handler DAT
    print("-" * 60)
    print("Setting up handler DAT...")
    setup_handler(ui_module, handler_code)

    # Set up static DATs
    print("-" * 60)
    print("Setting up static UI DATs...")
    setup_static_dats(ui_module)

    print("=" * 60)
    print("UI Module setup complete!")
    print("Web UI: http://127.0.0.1:9980/ui")
    print("=" * 60)

# Run when script is executed
run_ui_setup()
