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
    """Set up the UI module with its own webserver on port 9981."""
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        print("ERROR: Core bridge not found")
        return False

    # Create UI container directly under mcp_bridge (not in modules/)
    ui = bridge.op('ui')
    if ui is None:
        ui = bridge.create(baseCOMP, 'ui')
        ui.nodeX = 300
        ui.nodeY = 0

    # Create handler DAT with ui_handler code
    handler = ui.op('handler')
    if handler is None:
        handler = ui.create(textDAT, 'handler')
        handler.nodeX = 0
        handler.nodeY = 0
    handler.text = ui_handler_code

    # Create UI's own webserver on port 9981
    webserver = ui.op('webserver')
    if webserver is None:
        webserver = ui.create(webserverDAT, 'webserver')
        webserver.nodeX = 0
        webserver.nodeY = -150

    webserver.par.port = 9981
    webserver.par.active = True
    webserver.par.callbacks = 'handler'

    # Create static UI DATs with defaults
    create_ui_dats(ui)

    print("  ✓ UI module installed on port 9981")
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
    <link rel="stylesheet" href="/ui/styles.css">
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
            <div id="presets-panel" class="full-panel"></div>
        </div>
        <div id="tab-cues" class="tab-content">
            <div id="cues-panel" class="full-panel"></div>
        </div>
    </main>
    <script src="/ui/controls.js"></script>
    <script src="/ui/preview.js"></script>
    <script src="/ui/app.js"></script>
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
.tab-content { display: none; width: 100%; overflow: hidden; }
.tab-content.active { display: flex; }
.full-panel { width: 100%; overflow-y: auto; }
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
    padding: 1rem;
    width: 100%;
    overflow-y: auto;
}
.preview-grid-inner {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
}
.preview-grid-inner.chop-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}
.top-preview-wrapper, .chop-preview-wrapper {
    background: var(--bg-secondary);
    border-radius: 8px;
    overflow: hidden;
}
.preview-label {
    padding: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
}
.chop-type { opacity: 0.6; }
.top-preview { width: 100%; display: block; }
.chop-canvas { width: 100%; height: 100px; display: block; }
/* Presets */
.preset-controls {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
}
.preset-controls input {
    flex: 1;
    padding: 0.5rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    border-radius: 4px;
}
.preset-list {
    padding: 1rem;
}
.preset-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background: var(--bg-secondary);
    border-radius: 4px;
}
.preset-name { flex: 1; }
/* Cues */
.cue-controls {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
}
.cue-list {
    padding: 1rem;
}
.cue-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    background: var(--bg-secondary);
    border-radius: 4px;
}
.cue-index {
    width: 30px;
    text-align: center;
    font-weight: bold;
    color: var(--accent);
}
.cue-name { flex: 1; }
button.danger {
    background: var(--error);
}
button.danger:hover {
    background: #da3633;
}
/* Cue Editor */
.cue-editor {
    padding: 1rem;
    max-width: 600px;
}
.cue-editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.cue-editor-header h3 { margin: 0; }
.cue-editor-body { display: flex; flex-direction: column; gap: 1rem; }
.cue-field {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.cue-field label { min-width: 100px; }
.cue-field input[type="text"], .cue-field input[type="number"] {
    flex: 1;
    padding: 0.5rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    border-radius: 4px;
}
.cue-snapshot-list {
    background: var(--bg-secondary);
    border-radius: 4px;
    padding: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
}
.cue-snapshot-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.cue-snapshot-item:last-child { border-bottom: none; }
.snapshot-param-count {
    font-size: 0.75rem;
    color: var(--text-secondary);
}
.cue-editor-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
}
/* Tree View */
.tree-container { padding: 0.5rem 0; }
.tree-item {
    display: flex;
    align-items: center;
    padding: 0.25rem 0;
    cursor: default;
}
.tree-toggle {
    width: 16px;
    text-align: center;
    cursor: pointer;
    color: var(--text-secondary);
    user-select: none;
}
.tree-spacer { width: 16px; }
.tree-label {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
}
.tree-label:hover { background: var(--bg-tertiary); }
.tree-label.has-params { color: var(--text-primary); }
.tree-label.selected { background: var(--accent); color: var(--bg-primary); }
.tree-children { margin-left: 8px; }
.tree-children.collapsed { display: none; }
.param-count {
    font-size: 0.7rem;
    color: var(--text-secondary);
    margin-left: 0.25rem;
}
/* Current Cue Indicator */
.cue-item.current {
    border-left: 3px solid var(--success);
    background: rgba(63, 185, 80, 0.1);
}
.cue-item.current .cue-index { color: var(--success); }
/* Cue Reorder Buttons */
.cue-reorder {
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.cue-reorder button {
    padding: 2px 6px;
    font-size: 0.7rem;
    background: var(--bg-tertiary);
}
.cue-reorder button:hover { background: var(--accent); }
/* Cue Actions Editor */
.cue-actions-section {
    margin-top: 1rem;
    border-top: 1px solid var(--border);
    padding-top: 1rem;
}
.actions-list { margin: 0.5rem 0; }
.action-item {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background: var(--bg-tertiary);
    border-radius: 4px;
    align-items: center;
}
.action-type-badge {
    background: var(--accent);
    color: var(--bg-primary);
    padding: 0.125rem 0.375rem;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
}
.action-item input, .action-item select, .action-item textarea {
    flex: 1;
    min-width: 100px;
    padding: 0.375rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    border-radius: 4px;
    font-size: 0.875rem;
}
.action-item textarea {
    min-height: 60px;
    font-family: monospace;
    resize: vertical;
}
.action-add {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}
.action-add select { padding: 0.375rem; }'''

def get_ui_app():
    return '''let ws = null;
let selectedComponent = null;
let components = [];
let componentTree = null;
let presets = [];
let cues = [];
let currentCueIndex = 0;

document.addEventListener('DOMContentLoaded', init);

async function init() {
    setupTabs();
    await loadProjectInfo();
    await loadComponentTree();
    connectWebSocket();
}

async function loadProjectInfo() {
    try {
        const res = await fetch('/ui/info', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
        const info = await res.json();
        const title = info.projectName || 'TouchDesigner Control';
        document.getElementById('page-title').textContent = title;
        document.title = title;
    } catch (e) {
        console.error('Failed to load project info:', e);
    }
}

function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            // Load content for specific tabs
            if (tab.dataset.tab === 'previews') loadPreviews();
            if (tab.dataset.tab === 'presets') loadPresets();
            if (tab.dataset.tab === 'cues') loadCues();
        });
    });
}

async function loadComponentTree() {
    try {
        const res = await fetch('/ui/components/tree', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: '/project1', max_depth: 5})
        });
        const data = await res.json();
        if (data.success && data.tree) {
            componentTree = data.tree;
            renderComponentTree();
        } else {
            // Fallback to flat list
            await loadComponents();
        }
    } catch (e) {
        console.error('Failed to load component tree:', e);
        await loadComponents();
    }
}

async function loadComponents() {
    try {
        const res = await fetch('/ui/discover');
        const data = await res.json();
        if (data.success) {
            components = data.components;
            renderComponentListFlat();
        }
    } catch (e) {
        console.error('Failed to load components:', e);
    }
}

function renderComponentListFlat() {
    const container = document.getElementById('components');
    container.innerHTML = components.map(c =>
        '<div class="component-item" data-path="' + c.path + '" onclick="selectComponent(\\'' + c.path + '\\')">' + c.name + '</div>'
    ).join('');
}

function renderComponentTree() {
    const container = document.getElementById('components');
    container.innerHTML = '<div class="tree-container"></div>';
    const treeContainer = container.querySelector('.tree-container');
    if (componentTree && componentTree.children) {
        componentTree.children.forEach(child => {
            renderTreeNode(child, treeContainer, 0);
        });
    }
}

function renderTreeNode(node, container, depth) {
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.style.paddingLeft = (depth * 16) + 'px';

    const hasChildren = node.children && node.children.length > 0;
    const hasParams = node.paramCount > 0;

    let html = '';
    if (hasChildren) {
        html += '<span class="tree-toggle" onclick="toggleTreeNode(this)">&#9654;</span>';
    } else {
        html += '<span class="tree-spacer"></span>';
    }
    html += '<span class="tree-label' + (hasParams ? ' has-params' : '') + '" data-path="' + node.path + '">' + node.name + '</span>';
    if (hasParams) {
        html += '<span class="param-count">(' + node.paramCount + ')</span>';
    }
    item.innerHTML = html;

    if (hasParams) {
        item.querySelector('.tree-label').onclick = function() { selectComponent(node.path); };
    }

    container.appendChild(item);

    if (hasChildren) {
        const childContainer = document.createElement('div');
        childContainer.className = 'tree-children collapsed';
        node.children.forEach(child => {
            renderTreeNode(child, childContainer, depth + 1);
        });
        container.appendChild(childContainer);
    }
}

function toggleTreeNode(toggle) {
    const item = toggle.parentElement;
    const childContainer = item.nextElementSibling;
    if (childContainer && childContainer.classList.contains('tree-children')) {
        childContainer.classList.toggle('collapsed');
        toggle.innerHTML = childContainer.classList.contains('collapsed') ? '&#9654;' : '&#9660;';
    }
}

async function selectComponent(path) {
    selectedComponent = path;
    // Update selection in flat list
    document.querySelectorAll('.component-item').forEach(el => {
        el.classList.toggle('selected', el.dataset.path === path);
    });
    // Update selection in tree view
    document.querySelectorAll('.tree-label').forEach(el => {
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
}

// === PRESETS ===
async function loadPresets() {
    if (!selectedComponent) {
        document.getElementById('presets-panel').innerHTML = '<p>Select a component first</p>';
        return;
    }
    try {
        const res = await fetch('/presets/list', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({comp_path: selectedComponent})
        });
        const data = await res.json();
        presets = data.presets || [];
        renderPresets();
    } catch (e) {
        console.error('Failed to load presets:', e);
    }
}

function renderPresets() {
    const panel = document.getElementById('presets-panel');
    let html = '<div class="preset-controls">';
    html += '<input type="text" id="preset-name" placeholder="Preset name">';
    html += '<button onclick="savePreset()">Save Preset</button>';
    html += '</div>';
    html += '<div class="preset-list">';
    if (presets.length === 0) {
        html += '<p>No presets saved</p>';
    } else {
        for (const preset of presets) {
            html += '<div class="preset-item">';
            html += '<span class="preset-name">' + preset.name + '</span>';
            html += '<button onclick="loadPreset(\\'' + preset.name + '\\')">Load</button>';
            html += '<button class="danger" onclick="deletePreset(\\'' + preset.name + '\\')">Delete</button>';
            html += '</div>';
        }
    }
    html += '</div>';
    panel.innerHTML = html;
}

async function savePreset() {
    if (!selectedComponent) return;
    const name = document.getElementById('preset-name').value.trim();
    if (!name) { alert('Enter a preset name'); return; }
    try {
        const res = await fetch('/presets/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, comp_path: selectedComponent})
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('preset-name').value = '';
            await loadPresets();
        } else {
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Failed to save preset:', e);
    }
}

async function loadPreset(name) {
    if (!selectedComponent) return;
    try {
        const res = await fetch('/presets/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, comp_path: selectedComponent})
        });
        const data = await res.json();
        if (data.success) {
            await loadComponentParameters(selectedComponent);
        } else {
            alert('Failed to load: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Failed to load preset:', e);
    }
}

async function deletePreset(name) {
    if (!selectedComponent) return;
    if (!confirm('Delete preset "' + name + '"?')) return;
    try {
        await fetch('/presets/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, comp_path: selectedComponent})
        });
        await loadPresets();
    } catch (e) {
        console.error('Failed to delete preset:', e);
    }
}

// === CUES ===
async function loadCues() {
    try {
        const res = await fetch('/cues/list', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
        const data = await res.json();
        cues = data.cues || [];
        currentCueIndex = data.current_index || 0;
        renderCues();
    } catch (e) {
        console.error('Failed to load cues:', e);
    }
}

function renderCues() {
    const panel = document.getElementById('cues-panel');
    let html = '<div class="cue-controls">';
    html += '<button onclick="addCue()">Add Cue</button>';
    html += '<button onclick="goCue(\\'next\\')">GO NEXT</button>';
    html += '<button onclick="goCue(\\'back\\')">GO BACK</button>';
    html += '</div>';
    html += '<div class="cue-list">';
    if (cues.length === 0) {
        html += '<p>No cues</p>';
    } else {
        for (let i = 0; i < cues.length; i++) {
            const cue = cues[i];
            const isCurrent = cue.index === currentCueIndex;
            html += '<div class="cue-item' + (isCurrent ? ' current' : '') + '" data-id="' + cue.id + '" data-index="' + cue.index + '">';
            html += '<div class="cue-reorder">';
            html += '<button onclick="moveCue(\\'' + cue.id + '\\', \\'up\\')">&#9650;</button>';
            html += '<button onclick="moveCue(\\'' + cue.id + '\\', \\'down\\')">&#9660;</button>';
            html += '</div>';
            html += '<span class="cue-index">' + cue.index + '</span>';
            html += '<span class="cue-name">' + cue.name + '</span>';
            if (cue.autofollow) html += '<span style="font-size:0.7rem;color:var(--text-secondary);">auto</span>';
            html += '<button onclick="goCue(\\'' + cue.id + '\\')">GO</button>';
            html += '<button onclick="editCue(\\'' + cue.id + '\\')">Edit</button>';
            html += '<button class="danger" onclick="deleteCue(\\'' + cue.id + '\\')">Delete</button>';
            html += '</div>';
        }
    }
    html += '</div>';
    panel.innerHTML = html;
}

async function moveCue(id, direction) {
    const cue = cues.find(c => c.id === id);
    if (!cue) return;

    const newIndex = direction === 'up' ? cue.index - 1 : cue.index + 1;
    if (newIndex < 1 || newIndex > cues.length) return;

    try {
        const res = await fetch('/cues/reorder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id: id, new_index: newIndex })
        });
        const data = await res.json();
        if (data.success) {
            await loadCues();
        }
    } catch (e) {
        console.error('Failed to move cue:', e);
    }
}

async function addCue() {
    const name = prompt('Cue name:', 'Cue ' + (cues.length + 1));
    if (!name) return;
    try {
        const snapshotRes = await fetch('/cues/snapshot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({parent_path: '/project1', max_depth: 3})
        });
        const snapshotData = await snapshotRes.json();
        const res = await fetch('/cues/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, snapshot: snapshotData.snapshot || {}, actions: []})
        });
        await loadCues();
    } catch (e) {
        console.error('Failed to add cue:', e);
    }
}

async function goCue(idOrAction) {
    try {
        let endpoint = '/cues/go';
        let body = {};
        if (idOrAction === 'next') {
            endpoint = '/cues/next';
        } else if (idOrAction === 'back') {
            endpoint = '/cues/back';
        } else {
            body = {id: idOrAction};
        }
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success && data.cue) {
            currentCueIndex = data.cue.index;
            updateCueListDisplay();
        }
    } catch (e) {
        console.error('Failed to go cue:', e);
    }
}

function updateCueListDisplay() {
    document.querySelectorAll('.cue-item').forEach(item => {
        const itemIndex = parseInt(item.dataset.index);
        item.classList.toggle('current', itemIndex === currentCueIndex);
    });
}

let editingCue = null;

async function editCue(id) {
    const cue = cues.find(c => c.id === id);
    if (!cue) return;
    editingCue = cue;
    renderCueEditor(cue);
}

function renderCueEditor(cue) {
    const panel = document.getElementById('cues-panel');
    let html = '<div class="cue-editor">';
    html += '<div class="cue-editor-header">';
    html += '<h3>Edit Cue: ' + cue.name + '</h3>';
    html += '<button onclick="closeCueEditor()">Close</button>';
    html += '</div>';
    html += '<div class="cue-editor-body">';
    html += '<div class="cue-field"><label>Name:</label><input type="text" id="cue-name" value="' + cue.name + '"></div>';
    html += '<div class="cue-field"><label>Duration (s):</label><input type="number" id="cue-duration" value="' + (cue.duration || 0) + '" step="0.1" min="0"></div>';
    html += '<div class="cue-field"><label><input type="checkbox" id="cue-autofollow" ' + (cue.autofollow ? 'checked' : '') + '> Auto-follow (go to next cue after duration)</label></div>';

    // Snapshot section
    html += '<h4>Snapshot Components</h4>';
    html += '<div class="cue-snapshot-list">';
    const snapshot = cue.snapshot || {};
    if (Object.keys(snapshot).length === 0) {
        html += '<p>No components in snapshot</p>';
    } else {
        for (const [path, data] of Object.entries(snapshot)) {
            const enabled = data.enabled !== false;
            const paramCount = Object.keys(data.params || {}).length;
            html += '<div class="cue-snapshot-item">';
            html += '<label><input type="checkbox" class="snapshot-enabled" data-path="' + path + '" ' + (enabled ? 'checked' : '') + '> ' + path.split('/').pop() + '</label>';
            html += '<span class="snapshot-param-count">' + paramCount + ' params</span>';
            html += '</div>';
        }
    }
    html += '</div>';

    // Actions section (the critical gap!)
    html += '<div class="cue-actions-section">';
    html += '<h4>Actions</h4>';
    html += '<p style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:0.5rem;">Actions run after snapshot is applied</p>';
    html += '<div class="actions-list" id="actions-list">';
    const actions = cue.actions || [];
    if (actions.length === 0) {
        html += '<p style="font-size:0.875rem;color:var(--text-secondary);">No actions defined</p>';
    } else {
        for (let i = 0; i < actions.length; i++) {
            html += renderActionItem(actions[i], i);
        }
    }
    html += '</div>';
    html += '<div class="action-add">';
    html += '<select id="new-action-type">';
    html += '<option value="python">Python Code</option>';
    html += '<option value="osc">OSC Message</option>';
    html += '<option value="timeline">Timeline Control</option>';
    html += '<option value="parameter">Set Parameter</option>';
    html += '</select>';
    html += '<button onclick="addAction()">Add Action</button>';
    html += '</div>';
    html += '</div>';

    html += '<div class="cue-editor-actions">';
    html += '<button onclick="updateSnapshot()">Update Snapshot</button>';
    html += '<button onclick="saveCueChanges()">Save Changes</button>';
    html += '</div>';
    html += '</div></div>';
    panel.innerHTML = html;
}

function renderActionItem(action, index) {
    let html = '<div class="action-item" data-index="' + index + '">';

    switch(action.type) {
        case 'python':
            html += '<span class="action-type-badge">Python</span>';
            html += '<textarea class="action-code" placeholder="Python code..." onchange="updateAction(' + index + ', this)">' + (action.code || '') + '</textarea>';
            break;
        case 'osc':
            html += '<span class="action-type-badge">OSC</span>';
            html += '<input type="text" class="osc-address" placeholder="/address" value="' + (action.address || '') + '" onchange="updateAction(' + index + ', this)">';
            html += '<input type="text" class="osc-args" placeholder="args (comma-sep)" value="' + ((action.args || []).join(',')) + '" onchange="updateAction(' + index + ', this)">';
            html += '<input type="text" class="osc-host" placeholder="host" value="' + (action.host || '127.0.0.1') + '" onchange="updateAction(' + index + ', this)" style="width:100px">';
            html += '<input type="number" class="osc-port" placeholder="port" value="' + (action.port || 7000) + '" onchange="updateAction(' + index + ', this)" style="width:70px">';
            break;
        case 'timeline':
            html += '<span class="action-type-badge">Timeline</span>';
            html += '<select class="timeline-action" onchange="updateAction(' + index + ', this)">';
            html += '<option value="play"' + (action.action === 'play' ? ' selected' : '') + '>Play</option>';
            html += '<option value="pause"' + (action.action === 'pause' ? ' selected' : '') + '>Pause</option>';
            html += '<option value="stop"' + (action.action === 'stop' ? ' selected' : '') + '>Stop</option>';
            html += '<option value="jump_frame"' + (action.action === 'jump_frame' ? ' selected' : '') + '>Jump to Frame</option>';
            html += '</select>';
            html += '<input type="number" class="timeline-frame" placeholder="Frame #" value="' + (action.frame || '') + '" onchange="updateAction(' + index + ', this)" style="width:80px;' + (action.action !== 'jump_frame' ? 'display:none' : '') + '">';
            break;
        case 'parameter':
            html += '<span class="action-type-badge">Param</span>';
            html += '<input type="text" class="param-path" placeholder="/project1/comp" value="' + (action.path || '') + '" onchange="updateAction(' + index + ', this)">';
            html += '<input type="text" class="param-name" placeholder="param name" value="' + (action.parameter || '') + '" onchange="updateAction(' + index + ', this)" style="width:100px">';
            html += '<input type="text" class="param-value" placeholder="value" value="' + (action.value !== undefined ? action.value : '') + '" onchange="updateAction(' + index + ', this)" style="width:80px">';
            break;
        default:
            html += '<span class="action-type-badge">' + action.type + '</span>';
            html += '<span>Unknown action type</span>';
    }

    html += '<button class="danger" onclick="removeAction(' + index + ')" style="padding:0.25rem 0.5rem">X</button>';
    html += '</div>';
    return html;
}

function addAction() {
    if (!editingCue) return;
    const type = document.getElementById('new-action-type').value;
    const actions = editingCue.actions || [];

    let newAction = { type: type };
    switch(type) {
        case 'python':
            newAction.code = '';
            break;
        case 'osc':
            newAction.address = '/cue';
            newAction.args = [];
            newAction.host = '127.0.0.1';
            newAction.port = 7000;
            break;
        case 'timeline':
            newAction.action = 'play';
            break;
        case 'parameter':
            newAction.path = '';
            newAction.parameter = '';
            newAction.value = '';
            break;
    }

    actions.push(newAction);
    editingCue.actions = actions;
    renderCueEditor(editingCue);
}

function removeAction(index) {
    if (!editingCue) return;
    const actions = editingCue.actions || [];
    actions.splice(index, 1);
    editingCue.actions = actions;
    renderCueEditor(editingCue);
}

function updateAction(index, element) {
    if (!editingCue) return;
    const actions = editingCue.actions || [];
    if (!actions[index]) return;

    const action = actions[index];
    const item = element.closest('.action-item');

    switch(action.type) {
        case 'python':
            action.code = item.querySelector('.action-code').value;
            break;
        case 'osc':
            action.address = item.querySelector('.osc-address').value;
            const argsStr = item.querySelector('.osc-args').value;
            action.args = argsStr ? argsStr.split(',').map(s => s.trim()) : [];
            action.host = item.querySelector('.osc-host').value || '127.0.0.1';
            action.port = parseInt(item.querySelector('.osc-port').value) || 7000;
            break;
        case 'timeline':
            action.action = item.querySelector('.timeline-action').value;
            action.frame = parseInt(item.querySelector('.timeline-frame').value) || 1;
            // Show/hide frame input based on action
            const frameInput = item.querySelector('.timeline-frame');
            frameInput.style.display = action.action === 'jump_frame' ? '' : 'none';
            break;
        case 'parameter':
            action.path = item.querySelector('.param-path').value;
            action.parameter = item.querySelector('.param-name').value;
            action.value = item.querySelector('.param-value').value;
            break;
    }
}

function closeCueEditor() {
    editingCue = null;
    renderCues();
}

async function updateSnapshot() {
    if (!editingCue) return;
    try {
        const res = await fetch('/cues/snapshot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({parent_path: '/project1', max_depth: 3})
        });
        const data = await res.json();
        if (data.success) {
            editingCue.snapshot = data.snapshot;
            renderCueEditor(editingCue);
        }
    } catch (e) {
        console.error('Failed to update snapshot:', e);
    }
}

async function saveCueChanges() {
    if (!editingCue) return;
    const name = document.getElementById('cue-name').value.trim();
    const duration = parseFloat(document.getElementById('cue-duration').value) || 0;
    const autofollow = document.getElementById('cue-autofollow').checked;

    // Update enabled state from checkboxes
    const snapshot = editingCue.snapshot || {};
    document.querySelectorAll('.snapshot-enabled').forEach(cb => {
        const path = cb.dataset.path;
        if (path && snapshot[path]) {
            snapshot[path].enabled = cb.checked;
        }
    });

    try {
        const res = await fetch('/cues/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                id: editingCue.id,
                name: name,
                duration: duration,
                autofollow: autofollow,
                snapshot: snapshot,
                actions: editingCue.actions || []
            })
        });
        const data = await res.json();
        if (data.success) {
            alert('Cue saved successfully!');
            editingCue = null;
            await loadCues();
        } else {
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Failed to save cue:', e);
    }
}

async function deleteCue(id) {
    if (!confirm('Delete this cue?')) return;
    try {
        await fetch('/cues/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id})
        });
        await loadCues();
    } catch (e) {
        console.error('Failed to delete cue:', e);
    }
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
        const res = await fetch('/preview/discover', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
        const data = await res.json();
        if (!data.success) {
            grid.innerHTML = '<p>No previews found</p>';
            return;
        }
        grid.innerHTML = '';

        // TOPs section
        if (data.tops && data.tops.length > 0) {
            const topSection = document.createElement('div');
            topSection.innerHTML = '<h3 style="margin:1rem;color:var(--text-secondary);">TOPs</h3>';
            grid.appendChild(topSection);
            const topGrid = document.createElement('div');
            topGrid.className = 'preview-grid-inner';
            for (const top of data.tops) {
                createTopPreview(top, topGrid);
            }
            grid.appendChild(topGrid);
        }

        // CHOPs section
        if (data.chops && data.chops.length > 0) {
            const chopSection = document.createElement('div');
            chopSection.innerHTML = '<h3 style="margin:1rem;color:var(--text-secondary);">CHOPs</h3>';
            grid.appendChild(chopSection);
            const chopGrid = document.createElement('div');
            chopGrid.className = 'preview-grid-inner chop-grid';
            for (const chop of data.chops) {
                createChopPreview(chop, chopGrid);
            }
            grid.appendChild(chopGrid);
        }

        if ((!data.tops || data.tops.length === 0) && (!data.chops || data.chops.length === 0)) {
            grid.innerHTML = '<p>No TOPs or CHOPs found</p>';
        }
    } catch (e) {
        grid.innerHTML = '<p>Error loading previews: ' + e + '</p>';
    }
}

function createTopPreview(top, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'top-preview-wrapper';
    wrapper.innerHTML = '<div class="preview-label">' + top.name + '</div><img class="top-preview" src="/preview/top?path=' + encodeURIComponent(top.path) + '&t=' + Date.now() + '">';
    const img = wrapper.querySelector('img');
    const interval = setInterval(() => {
        img.src = '/preview/top?path=' + encodeURIComponent(top.path) + '&t=' + Date.now();
    }, 500);
    previewIntervals.push(interval);
    container.appendChild(wrapper);
}

function createChopPreview(chop, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'chop-preview-wrapper';
    wrapper.innerHTML = '<div class="preview-label">' + chop.name + ' <span class="chop-type">(' + chop.type + ')</span></div><canvas class="chop-canvas" width="300" height="100"></canvas>';
    const canvas = wrapper.querySelector('canvas');
    const ctx = canvas.getContext('2d');
    const colors = ['#58a6ff', '#f85149', '#3fb950', '#d29922', '#a371f7', '#f778ba'];

    async function drawChop() {
        try {
            const res = await fetch('/preview/chop', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: chop.path, max_samples: 100})
            });
            const data = await res.json();
            if (!data.success || !data.channels) return;

            ctx.fillStyle = '#161b22';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            data.channels.forEach((ch, i) => {
                if (!ch.values || ch.values.length === 0) return;
                ctx.strokeStyle = colors[i % colors.length];
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                const range = (ch.max - ch.min) || 1;
                ch.values.forEach((v, x) => {
                    const px = (x / ch.values.length) * canvas.width;
                    const py = canvas.height - ((v - ch.min) / range) * canvas.height;
                    x === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                });
                ctx.stroke();
            });

            // Draw channel names
            ctx.font = '10px sans-serif';
            data.channels.forEach((ch, i) => {
                ctx.fillStyle = colors[i % colors.length];
                ctx.fillText(ch.name, 4, 12 + i * 12);
            });
        } catch (e) {
            ctx.fillStyle = '#f85149';
            ctx.fillText('Error', 10, 20);
        }
    }

    drawChop();
    const interval = setInterval(drawChop, 100);
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
    print("")
    print("  Core API:  http://127.0.0.1:9980/ping")
    print("  Web UI:    http://127.0.0.1:9981/ui")
    print("")
    print("Core and UI run on separate webservers.")
    print("=" * 60)

# Run when script is executed
run_setup()
