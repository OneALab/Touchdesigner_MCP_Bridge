let ws = null;
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
    // Poll for parameter changes from TouchDesigner every 500ms
    setInterval(refreshCurrentParameters, 500);
}

async function refreshCurrentParameters() {
    if (!selectedComponent) return;
    // Only refresh if Controls tab is active
    const controlsTab = document.getElementById('tab-controls');
    if (!controlsTab || !controlsTab.classList.contains('active')) return;
    try {
        const res = await fetch('/ui/schema', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedComponent})
        });
        const data = await res.json();
        if (data.success) {
            // Update values without re-rendering entire UI
            for (const page of data.pages || []) {
                for (const param of page.parameters || []) {
                    const input = document.getElementById('param-' + param.name);
                    const valSpan = document.getElementById('param-' + param.name + '-val');
                    if (input && document.activeElement !== input) {
                        // Only update if user isn't actively editing this input
                        if (input.type === 'range' || input.type === 'number') {
                            input.value = param.value;
                        } else if (input.type === 'checkbox') {
                            input.checked = !!param.value;
                        } else if (input.tagName === 'SELECT') {
                            input.value = param.value;
                        } else {
                            input.value = param.value || '';
                        }
                    }
                    if (valSpan) valSpan.textContent = param.value;
                }
            }
        }
    } catch (e) {
        // Silently ignore refresh errors
    }
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
            if (tab.dataset.tab === 'streamdeck') loadStreamDeck();
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
        '<div class="component-item" data-path="' + c.path + '" onclick="selectComponent(`' + c.path + '`)">' + c.name + '</div>'
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
        control = '<input type="range" id="' + id + '" min="' + param.min + '" max="' + param.max + '" step="' + step + '" value="' + param.value + '" oninput="updateValue(this)" onchange="setParameter(`' + param.name + '`, this.value)"><span id="' + id + '-val">' + param.value + '</span>';
    } else if (param.style === 'Toggle') {
        control = '<input type="checkbox" id="' + id + '" ' + (param.value ? 'checked' : '') + ' onchange="setParameter(`' + param.name + '`, this.checked ? 1 : 0)">';
    } else if (param.style === 'Str') {
        control = '<input type="text" id="' + id + '" value="' + (param.value || '') + '" onchange="setParameter(`' + param.name + '`, this.value)">';
    } else if (param.style === 'Pulse') {
        control = '<button onclick="pulseParameter(`' + param.name + '`)">Pulse</button>';
    } else {
        control = '<input type="text" id="' + id + '" value="' + (param.value || '') + '" onchange="setParameter(`' + param.name + '`, this.value)">';
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
        await fetch('/ui/set', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({changes: [{path: selectedComponent, parameter: name, value: value}]})
        });
    } catch (e) {
        console.error('Failed to set parameter:', e);
    }
}

async function pulseParameter(name) {
    if (!selectedComponent) return;
    try {
        await fetch('/ui/pulse', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedComponent, parameter: name})
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
    try {
        // Load ALL presets (not filtered by component)
        const res = await fetch('/presets/list', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
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
    if (selectedComponent) {
        html += '<span class="preset-comp-label">Saving to: ' + selectedComponent.split('/').pop() + '</span>';
        html += '<input type="text" id="preset-name" placeholder="Preset name">';
        html += '<button onclick="savePreset()">Save Preset</button>';
    } else {
        html += '<span style="color:var(--text-secondary)">Select a component to save presets</span>';
    }
    html += '</div>';
    html += '<div class="preset-list">';
    if (presets.length === 0) {
        html += '<p>No presets saved</p>';
    } else {
        for (const preset of presets) {
            const compName = preset.comp_path.split('/').pop();
            html += '<div class="preset-item">';
            html += '<span class="preset-comp">' + compName + '</span>';
            html += '<span class="preset-name">' + preset.name + '</span>';
            html += '<button onclick="loadPresetFor(`' + preset.name + '`, `' + preset.comp_path + '`)">Load</button>';
            html += '<button class="danger" onclick="deletePresetFor(`' + preset.name + '`, `' + preset.comp_path + '`)">Delete</button>';
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

async function loadPresetFor(name, compPath) {
    try {
        console.log('Loading preset:', name, 'for', compPath);
        const res = await fetch('/presets/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, comp_path: compPath})
        });
        const data = await res.json();
        console.log('Load response:', data);
        if (data.success) {
            // Select the component and refresh its parameters
            await selectComponent(compPath);
            // Switch to Controls tab to show the loaded values
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector('.tab[data-tab="controls"]').classList.add('active');
            document.getElementById('tab-controls').classList.add('active');
            // Show brief confirmation
            const status = document.getElementById('connection-status');
            const origText = status.querySelector('.text').textContent;
            status.querySelector('.text').textContent = 'Preset loaded: ' + name;
            setTimeout(() => { status.querySelector('.text').textContent = origText; }, 2000);
        } else {
            alert('Failed to load: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Failed to load preset:', e);
        alert('Error loading preset: ' + e.message);
    }
}

async function deletePresetFor(name, compPath) {
    if (!confirm('Delete preset "' + name + '" for ' + compPath.split('/').pop() + '?')) return;
    try {
        await fetch('/presets/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, comp_path: compPath})
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
    html += '<button onclick="goCue(`next`)">GO NEXT</button>';
    html += '<button onclick="goCue(`back`)">GO BACK</button>';
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
            html += '<button onclick="moveCue(`' + cue.id + '`, `up`)">&#9650;</button>';
            html += '<button onclick="moveCue(`' + cue.id + '`, `down`)">&#9660;</button>';
            html += '</div>';
            html += '<span class="cue-index">' + cue.index + '</span>';
            html += '<span class="cue-name">' + cue.name + '</span>';
            if (cue.autofollow) html += '<span style="font-size:0.7rem;color:var(--text-secondary);">auto</span>';
            html += '<button onclick="goCue(`' + cue.id + '`)">GO</button>';
            html += '<button onclick="editCue(`' + cue.id + '`)">Edit</button>';
            html += '<button class="danger" onclick="deleteCue(`' + cue.id + '`)">Delete</button>';
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

    // Actions section
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
}

// === STREAM DECK ===
let sdConfig = {};
let sdProfiles = [];
let sdPages = [];  // New page-based system with device binding
let sdStatus = {};
let sdConnectedDevices = []; // Devices reported by the service
let sdSelectedDevice = 'default';
let sdSelectedButton = null;
let sdDeviceModel = 'standard'; // mini, standard, xl, plus, pedal
let sdServiceStatus = { running: false, pid: null, installed: false }; // Service status

const SD_MODELS = {
    mini: { name: 'Mini', keys: 6, cols: 3 },
    standard: { name: 'Standard/MK.2', keys: 15, cols: 5 },
    xl: { name: 'XL', keys: 32, cols: 8 },
    plus: { name: 'Plus', keys: 8, cols: 4, dials: 4 },
    neo: { name: 'Neo', keys: 8, cols: 4 },
    pedal: { name: 'Pedal', keys: 3, cols: 3 }
};

async function loadStreamDeck() {
    const panel = document.getElementById('streamdeck-panel');
    panel.innerHTML = '<p>Loading Stream Deck status...</p>';
    try {
        // Get status
        const statusRes = await fetch('/streamdeck/status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        sdStatus = await statusRes.json();

        if (!sdStatus.installed) {
            panel.innerHTML = '<div style="padding:2rem;text-align:center;"><h3>Stream Deck Module Not Installed</h3><p style="color:var(--text-secondary);margin:1rem 0;">Run td_setup.py in TouchDesigner to install the Stream Deck module.</p><p style="color:var(--text-secondary);font-size:0.875rem;">The module adds OSC receiver on port 7000 for Bitfocus Companion integration.</p></div>';
            return;
        }

        // Get config
        const configRes = await fetch('/streamdeck/config/get', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const configData = await configRes.json();
        sdConfig = configData.config || {};

        // Get profiles (legacy)
        const profilesRes = await fetch('/streamdeck/profiles/list', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const profilesData = await profilesRes.json();
        sdProfiles = profilesData.profiles || [];

        // Get pages (new system with device binding)
        const pagesRes = await fetch('/streamdeck/pages/list', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const pagesData = await pagesRes.json();
        sdPages = pagesData.pages || [];

        // Get connected devices (reported by service)
        const devicesRes = await fetch('/streamdeck/devices/list', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const devicesData = await devicesRes.json();
        sdConnectedDevices = devicesData.devices || [];

        // Get service status
        const serviceRes = await fetch('/streamdeck/service/status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const serviceData = await serviceRes.json();
        sdServiceStatus = serviceData || { running: false, pid: null, installed: false };

        // AUTO-SELECT first real device when devices are connected
        if (sdConnectedDevices.length > 0 && sdSelectedDevice === 'default') {
            const firstDevice = sdConnectedDevices[0];
            sdSelectedDevice = firstDevice.serial;
            const modelName = firstDevice.model.toLowerCase();
            if (modelName.includes('mini')) sdDeviceModel = 'mini';
            else if (modelName.includes('xl')) sdDeviceModel = 'xl';
            else if (modelName.includes('plus') || modelName.includes('+')) sdDeviceModel = 'plus';
            else if (modelName.includes('neo')) sdDeviceModel = 'neo';
            else if (modelName.includes('pedal')) sdDeviceModel = 'pedal';
            else sdDeviceModel = 'standard';
            console.log('Auto-selected device:', sdSelectedDevice, 'model:', sdDeviceModel);
        }

        renderStreamDeck();
    } catch (e) {
        console.error('Failed to load Stream Deck:', e);
        panel.innerHTML = '<p style="color:var(--error);">Error loading Stream Deck: ' + e.message + '</p>';
    }
}

function renderStreamDeck() {
    const panel = document.getElementById('streamdeck-panel');
    let html = '';

    // Header with status
    html += '<div class="streamdeck-header">';
    html += '<h3>Stream Deck Configuration</h3>';
    html += '<div class="streamdeck-status">';
    html += '<span class="status-badge ' + (sdStatus.osc_active ? 'active' : 'inactive') + '">';
    html += sdStatus.osc_active ? 'OSC Active (Port ' + sdStatus.osc_port + ')' : 'OSC Inactive';
    html += '</span>';
    html += '<span style="font-size:0.875rem;color:var(--text-secondary);">' + sdStatus.config_count + ' buttons configured</span>';
    html += '</div></div>';

    // Service control bar
    const configCount = Object.keys(sdConfig).length;
    const serviceRunning = sdServiceStatus.running;
    const serviceInstalled = sdServiceStatus.installed;

    html += '<div id="sd-service-status" style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 1rem;background:var(--bg-tertiary);border-radius:4px;margin-bottom:1rem;">';

    // Left side: status info
    html += '<div style="display:flex;gap:1rem;align-items:center;">';
    if (serviceRunning) {
        html += '<span style="font-size:0.875rem;color:var(--success);font-weight:600;">● Service Running</span>';
        if (sdServiceStatus.pid) {
            html += '<span style="font-size:0.75rem;color:var(--text-secondary);">PID: ' + sdServiceStatus.pid + '</span>';
        }
    } else if (serviceInstalled) {
        html += '<span style="font-size:0.875rem;color:var(--warning);">○ Service Stopped</span>';
    } else {
        html += '<span style="font-size:0.875rem;color:var(--error);">✕ Service Not Installed</span>';
    }
    html += '<span style="font-size:0.75rem;color:var(--text-secondary);">' + sdConnectedDevices.length + ' device(s) | ' + configCount + ' button(s)</span>';
    html += '</div>';

    // Right side: control buttons
    html += '<div style="display:flex;gap:0.5rem;align-items:center;">';
    if (serviceInstalled) {
        const autostart = sdServiceStatus.autostart;
        html += '<label style="display:flex;align-items:center;gap:0.25rem;font-size:0.75rem;cursor:pointer;">';
        html += '<input type="checkbox" onchange="toggleAutoStart(this.checked)" ' + (autostart ? 'checked' : '') + ' style="cursor:pointer;">';
        html += 'Auto-start</label>';
        html += '<span style="color:var(--text-secondary);">|</span>';

        if (serviceRunning) {
            html += '<button onclick="stopSdService()" style="padding:0.25rem 0.75rem;font-size:0.75rem;background:var(--error);">Stop Service</button>';
            html += '<button onclick="restartSdService()" style="padding:0.25rem 0.75rem;font-size:0.75rem;">Restart</button>';
        } else {
            html += '<button onclick="startSdService()" style="padding:0.25rem 0.75rem;font-size:0.75rem;background:var(--success);color:#000;">Start Service</button>';
        }
    } else {
        html += '<button onclick="showModeInfo(`direct`)" style="padding:0.25rem 0.75rem;font-size:0.75rem;">Setup Instructions</button>';
    }
    html += '<button onclick="loadStreamDeck()" style="padding:0.25rem 0.75rem;font-size:0.75rem;">↻ Refresh</button>';
    html += '</div>';
    html += '</div>';

    // Pages bar
    html += '<div class="streamdeck-profiles">';
    html += '<label>Pages:</label>';
    html += '<select id="sd-page-select" onchange="loadSdPage(this.value)">';
    html += '<option value="">(Live Config)</option>';

    const pagesByType = {};
    for (const p of sdPages) {
        const type = p.device_type || 'standard';
        if (!pagesByType[type]) pagesByType[type] = [];
        pagesByType[type].push(p);
    }
    for (const [type, pages] of Object.entries(pagesByType)) {
        html += '<optgroup label="' + type.toUpperCase() + '">';
        for (const p of pages) {
            const serialHint = p.device_serial ? ' [' + p.device_serial.substring(0, 6) + '...]' : '';
            html += '<option value="' + p.name + '">' + p.name + serialHint + '</option>';
        }
        html += '</optgroup>';
    }
    html += '</select>';
    html += '<input type="text" id="sd-page-name" placeholder="Page name" style="flex:0.5">';
    html += '<button onclick="saveSdPage()">Save Page</button>';
    html += '<button onclick="activateSdPage()" style="background:var(--accent);">Activate</button>';
    html += '<button onclick="deleteSdPage()" style="background:var(--error);">Delete</button>';
    html += '</div>';

    // Info about current device binding
    const deviceLabel = sdSelectedDevice === 'default' ? 'No device selected' : sdSelectedDevice.substring(0, 8) + '...';
    html += '<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:0.5rem;">';
    html += 'Save Page binds to: <strong>' + sdDeviceModel.toUpperCase() + '</strong>';
    if (sdSelectedDevice !== 'default') {
        html += ' + <strong>' + deviceLabel + '</strong>';
    }
    html += ' &nbsp;|&nbsp; Activate sends page to selected device';
    html += '</div>';

    // Quick page buttons for current device type
    const relevantPages = sdPages.filter(p =>
        p.device_type === sdDeviceModel &&
        (p.device_serial === '' || p.device_serial === sdSelectedDevice)
    );
    if (relevantPages.length > 0) {
        html += '<div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap;">';
        html += '<span style="font-size:0.75rem;color:var(--text-secondary);align-self:center;">Quick:</span>';
        for (let i = 0; i < Math.min(relevantPages.length, 8); i++) {
            const p = relevantPages[i];
            html += '<button onclick="loadSdPage(\`' + p.name + '\`)" style="padding:0.25rem 0.5rem;font-size:0.75rem;background:var(--bg-tertiary);">' + p.name + '</button>';
        }
        html += '</div>';
    }

    // Device and model selectors
    html += '<div class="streamdeck-config">';
    html += '<div style="display:flex;gap:1rem;margin-bottom:1rem;align-items:center;flex-wrap:wrap;">';

    html += '<div style="display:flex;align-items:center;gap:0.5rem;">';
    html += '<label style="font-size:0.875rem;">Model:</label>';
    html += '<select id="sd-model-select" onchange="changeSdModel(this.value)" style="padding:0.375rem;background:var(--bg-tertiary);border:1px solid var(--border);color:var(--text-primary);border-radius:4px;">';
    for (const [key, model] of Object.entries(SD_MODELS)) {
        html += '<option value="' + key + '"' + (sdDeviceModel === key ? ' selected' : '') + '>' + model.name + ' (' + model.keys + ' keys)</option>';
    }
    html += '</select>';
    html += '</div>';

    html += '<div style="display:flex;align-items:center;gap:0.5rem;">';
    html += '<label style="font-size:0.875rem;">Device:</label>';
    html += '<select id="sd-device-serial" onchange="changeSdDevice(this.value)" style="padding:0.375rem;background:var(--bg-tertiary);border:1px solid var(--border);color:var(--text-primary);border-radius:4px;min-width:200px;">';
    html += '<option value="default"' + (sdSelectedDevice === 'default' ? ' selected' : '') + '>-- Template (no device) --</option>';
    for (const dev of sdConnectedDevices) {
        const label = dev.model + ' (' + dev.serial.substring(0, 8) + '...)';
        html += '<option value="' + dev.serial + '"' + (sdSelectedDevice === dev.serial ? ' selected' : '') + '>' + label + ' - ' + dev.key_count + ' keys</option>';
    }
    html += '</select>';
    if (sdConnectedDevices.length === 0) {
        html += '<span style="font-size:0.75rem;color:var(--warning);margin-left:0.5rem;">No devices connected (start the service)</span>';
    } else {
        html += '<span style="font-size:0.75rem;color:var(--success);margin-left:0.5rem;">' + sdConnectedDevices.length + ' device(s) connected</span>';
    }
    html += '</div>';

    html += '<span style="font-size:0.75rem;color:var(--text-secondary);">Each device has its own unique configuration. Select the device you want to configure.</span>';
    html += '</div>';

    const model = SD_MODELS[sdDeviceModel];
    html += '<h4>Button Grid (' + model.name + ' - ' + model.keys + ' keys)</h4>';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">';
    html += '<span style="font-size:0.75rem;color:var(--text-secondary);">Click a button to configure its action</span>';
    html += '<button onclick="clearAllSdButtons()" style="background:var(--error);padding:0.25rem 0.75rem;font-size:0.75rem;">Clear All Buttons</button>';
    html += '</div>';

    const gridClass = 'grid-' + model.keys;
    html += '<div class="button-grid ' + gridClass + '" style="grid-template-columns:repeat(' + model.cols + ', 1fr);max-width:' + (model.cols * 105) + 'px;">';
    for (let i = 0; i < model.keys; i++) {
        const configKey = sdSelectedDevice + ':key:' + i;
        const btnConfig = sdConfig[configKey];
        const isConfigured = btnConfig && btnConfig.action_type;
        const bgColor = btnConfig && btnConfig.action && btnConfig.action.bg_color ? btnConfig.action.bg_color : '';
        const bgStyle = bgColor ? 'background:' + bgColor + ';' : '';
        html += '<div class="sd-button' + (isConfigured ? ' configured' : '') + '" data-key="' + i + '" onclick="editSdButton(' + i + ')" style="' + bgStyle + '">';
        html += '<span class="btn-index">' + (i + 1) + '</span>';
        if (isConfigured) {
            html += '<span class="btn-label">' + (btnConfig.label || '') + '</span>';
            html += '<span class="btn-action">' + btnConfig.action_type + '</span>';
        } else {
            html += '<span class="btn-label" style="color:var(--text-secondary);">Empty</span>';
        }
        html += '</div>';
    }
    html += '</div>';

    // Dials for Stream Deck Plus
    if (model.dials) {
        html += '<h4 style="margin-top:1.5rem;">Dials (' + model.dials + ')</h4>';
        html += '<div class="dial-grid">';
        for (let i = 0; i < model.dials; i++) {
            const turnKey = sdSelectedDevice + ':dial_turn:' + i;
            const pushKey = sdSelectedDevice + ':dial_push:' + i;
            const hasTurn = sdConfig[turnKey] && sdConfig[turnKey].action_type;
            const hasPush = sdConfig[pushKey] && sdConfig[pushKey].action_type;
            html += '<div class="sd-dial' + ((hasTurn || hasPush) ? ' configured' : '') + '" onclick="editSdDial(' + i + ')">';
            html += '<span style="font-size:0.7rem;color:var(--text-secondary);">Dial ' + (i + 1) + '</span>';
            if (hasTurn) html += '<span style="font-size:0.65rem;color:var(--accent);">Turn</span>';
            if (hasPush) html += '<span style="font-size:0.65rem;color:var(--success);">Push</span>';
            html += '</div>';
        }
        html += '</div>';
    }

    // Quick actions reference
    html += '<div style="margin-top:2rem;padding:1rem;background:var(--bg-secondary);border-radius:8px;">';
    html += '<h4 style="margin:0 0 0.5rem 0;color:var(--text-secondary);">Available Actions</h4>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(200px, 1fr));gap:0.5rem;font-size:0.875rem;">';
    html += '<div><strong>preset</strong> - Load a saved preset</div>';
    html += '<div><strong>cue_next</strong> - Go to next cue</div>';
    html += '<div><strong>cue_back</strong> - Go to previous cue</div>';
    html += '<div><strong>cue_go</strong> - Go to specific cue</div>';
    html += '<div><strong>parameter</strong> - Set parameter value</div>';
    html += '<div><strong>pulse</strong> - Pulse a parameter</div>';
    html += '<div><strong>toggle</strong> - Toggle parameter on/off</div>';
    html += '<div><strong>python</strong> - Run Python code</div>';
    html += '</div></div>';

    html += '</div>';

    panel.innerHTML = html;
}

function changeSdModel(model) {
    sdDeviceModel = model;
    renderStreamDeck();
}

function changeSdDevice(serial) {
    sdSelectedDevice = serial.trim() || 'default';

    if (serial !== 'default') {
        const device = sdConnectedDevices.find(d => d.serial === serial);
        if (device) {
            const modelName = device.model.toLowerCase();
            if (modelName.includes('mini')) sdDeviceModel = 'mini';
            else if (modelName.includes('xl')) sdDeviceModel = 'xl';
            else if (modelName.includes('plus') || modelName.includes('+')) sdDeviceModel = 'plus';
            else if (modelName.includes('neo')) sdDeviceModel = 'neo';
            else if (modelName.includes('pedal')) sdDeviceModel = 'pedal';
            else sdDeviceModel = 'standard';
        }
    }

    renderStreamDeck();
}

function editSdDial(dialIndex) {
    const turnKey = sdSelectedDevice + ':dial_turn:' + dialIndex;
    const pushKey = sdSelectedDevice + ':dial_push:' + dialIndex;
    const turnConfig = sdConfig[turnKey] || {};
    const pushConfig = sdConfig[pushKey] || {};

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    let html = '<div class="modal">';
    html += '<h3>Configure Dial ' + (dialIndex + 1) + '</h3>';

    html += '<div style="margin-bottom:1rem;padding:0.75rem;background:var(--bg-tertiary);border-radius:4px;">';
    html += '<h4 style="margin:0 0 0.5rem 0;font-size:0.875rem;">Turn Action (increment/decrement)</h4>';
    html += '<div class="modal-field"><label>Component Path</label>';
    html += '<input type="text" id="sd-dial-turn-path" value="' + ((turnConfig.action && turnConfig.action.path) || '') + '" placeholder="/project1/mycomp"></div>';
    html += '<div class="modal-field"><label>Parameter Name</label>';
    html += '<input type="text" id="sd-dial-turn-param" value="' + ((turnConfig.action && turnConfig.action.param) || '') + '"></div>';
    html += '<div class="modal-field"><label>Step Size</label>';
    html += '<input type="number" id="sd-dial-turn-step" value="' + ((turnConfig.action && turnConfig.action.step) || 0.1) + '" step="0.01"></div>';
    html += '</div>';

    html += '<div style="padding:0.75rem;background:var(--bg-tertiary);border-radius:4px;">';
    html += '<h4 style="margin:0 0 0.5rem 0;font-size:0.875rem;">Push Action</h4>';
    html += '<div class="modal-field"><label>Action Type</label>';
    html += '<select id="sd-dial-push-type">';
    html += '<option value="">-- None --</option>';
    html += '<option value="toggle"' + (pushConfig.action_type === 'toggle' ? ' selected' : '') + '>Toggle Parameter</option>';
    html += '<option value="pulse"' + (pushConfig.action_type === 'pulse' ? ' selected' : '') + '>Pulse Parameter</option>';
    html += '</select></div>';
    html += '<div class="modal-field"><label>Component Path</label>';
    html += '<input type="text" id="sd-dial-push-path" value="' + ((pushConfig.action && pushConfig.action.path) || '') + '" placeholder="/project1/mycomp"></div>';
    html += '<div class="modal-field"><label>Parameter Name</label>';
    html += '<input type="text" id="sd-dial-push-param" value="' + ((pushConfig.action && pushConfig.action.param) || '') + '"></div>';
    html += '</div>';

    html += '<div class="modal-actions">';
    html += '<button onclick="this.closest(`.modal-overlay`).remove()">Cancel</button>';
    html += '<button onclick="saveSdDial(' + dialIndex + ')">Save</button>';
    html += '</div>';
    html += '</div>';

    overlay.innerHTML = html;
    document.body.appendChild(overlay);
}

async function saveSdDial(dialIndex) {
    const turnPath = document.getElementById('sd-dial-turn-path').value;
    const turnParam = document.getElementById('sd-dial-turn-param').value;
    const turnStep = parseFloat(document.getElementById('sd-dial-turn-step').value) || 0.1;

    const pushType = document.getElementById('sd-dial-push-type').value;
    const pushPath = document.getElementById('sd-dial-push-path').value;
    const pushParam = document.getElementById('sd-dial-push-param').value;

    try {
        if (turnPath && turnParam) {
            await fetch('/streamdeck/config/set', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    device_serial: sdSelectedDevice,
                    button_id: dialIndex,
                    button_type: 'dial_turn',
                    action_type: 'parameter',
                    action: { path: turnPath, param: turnParam, step: turnStep },
                    label: 'Dial ' + (dialIndex + 1)
                })
            });
        }

        if (pushType && pushPath && pushParam) {
            await fetch('/streamdeck/config/set', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    device_serial: sdSelectedDevice,
                    button_id: dialIndex,
                    button_type: 'dial_push',
                    action_type: pushType,
                    action: { path: pushPath, param: pushParam },
                    label: 'Dial ' + (dialIndex + 1) + ' Push'
                })
            });
        }

        document.querySelector('.modal-overlay').remove();
        await loadStreamDeck();
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

function showModeInfo(mode) {
    if (mode === 'direct') {
        alert(`Direct HID Mode:

1. Install dependencies: pip install streamdeck pillow requests
2. Close Elgato software (conflicts with HID access)
3. Run: python streamdeck_service.py

The service will poll config from TouchDesigner and execute actions.`);
    } else {
        alert(`Companion Mode:

1. Install Bitfocus Companion (bitfocus.io/companion)
2. Add "Generic OSC" connection: Host 127.0.0.1, Port 7000
3. Use "Export for Companion" to get OSC addresses
4. Configure buttons in Companion to send OSC messages`);
    }
}

function editSdButton(keyIndex) {
    sdSelectedButton = keyIndex;
    const configKey = sdSelectedDevice + ':key:' + keyIndex;
    const btnConfig = sdConfig[configKey] || {};

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    let html = '<div class="modal">';
    html += '<h3>Configure Button ' + (keyIndex + 1) + '</h3>';

    html += '<div class="modal-field">';
    html += '<label>Label (shown on button)</label>';
    html += '<input type="text" id="sd-btn-label" value="' + (btnConfig.label || '') + '">';
    html += '</div>';

    html += '<div class="modal-field">';
    html += '<label>Background Color</label>';
    html += '<div style="display:flex;gap:0.5rem;align-items:center;">';
    const bgColor = (btnConfig.action && btnConfig.action.bg_color) || '#1a1a2e';
    html += '<input type="color" id="sd-btn-bgcolor" value="' + bgColor + '" style="width:50px;height:30px;padding:0;border:none;cursor:pointer;">';
    html += '<input type="text" id="sd-btn-bgcolor-text" value="' + bgColor + '" style="flex:1;" onchange="document.getElementById(`sd-btn-bgcolor`).value=this.value">';
    html += '<button type="button" onclick="document.getElementById(`sd-btn-bgcolor`).value=`#1a1a2e`;document.getElementById(`sd-btn-bgcolor-text`).value=`#1a1a2e`" style="padding:0.25rem 0.5rem;">Reset</button>';
    html += '</div>';
    html += '</div>';

    html += '<div class="modal-field">';
    html += '<label>Pressed Color (flash on press)</label>';
    html += '<div style="display:flex;gap:0.5rem;align-items:center;">';
    const pressedColor = (btnConfig.action && btnConfig.action.pressed_color) || '#ffffff';
    html += '<input type="color" id="sd-btn-pressedcolor" value="' + pressedColor + '" style="width:50px;height:30px;padding:0;border:none;cursor:pointer;">';
    html += '<input type="text" id="sd-btn-pressedcolor-text" value="' + pressedColor + '" style="flex:1;" onchange="document.getElementById(`sd-btn-pressedcolor`).value=this.value">';
    html += '<button type="button" onclick="document.getElementById(`sd-btn-pressedcolor`).value=`#ffffff`;document.getElementById(`sd-btn-pressedcolor-text`).value=`#ffffff`" style="padding:0.25rem 0.5rem;">Reset</button>';
    html += '</div>';
    html += '</div>';

    html += '<div class="modal-field">';
    html += '<label>Text Color</label>';
    html += '<div style="display:flex;gap:0.5rem;align-items:center;">';
    const textColor = (btnConfig.action && btnConfig.action.text_color) || '#ffffff';
    html += '<input type="color" id="sd-btn-textcolor" value="' + textColor + '" style="width:50px;height:30px;padding:0;border:none;cursor:pointer;">';
    html += '<input type="text" id="sd-btn-textcolor-text" value="' + textColor + '" style="flex:1;" onchange="document.getElementById(`sd-btn-textcolor`).value=this.value">';
    html += '<button type="button" onclick="document.getElementById(`sd-btn-textcolor`).value=`#ffffff`;document.getElementById(`sd-btn-textcolor-text`).value=`#ffffff`" style="padding:0.25rem 0.5rem;">Reset</button>';
    html += '</div>';
    html += '</div>';

    html += '<div class="modal-field">';
    html += '<label>Font Size</label>';
    html += '<div style="display:flex;gap:0.5rem;align-items:center;">';
    const fontSize = (btnConfig.action && btnConfig.action.font_size) || '';
    const autoSize = (btnConfig.action && btnConfig.action.auto_size !== undefined) ? btnConfig.action.auto_size : true;
    html += '<input type="number" id="sd-btn-fontsize" value="' + fontSize + '" placeholder="Auto" style="width:60px;" min="8" max="72">';
    html += '<label style="display:flex;align-items:center;gap:0.25rem;margin:0;"><input type="checkbox" id="sd-btn-autosize"' + (autoSize ? ' checked' : '') + '> Auto-size to fit</label>';
    html += '</div>';
    html += '</div>';

    html += '<div class="modal-field">';
    const wrapText = (btnConfig.action && btnConfig.action.wrap !== undefined) ? btnConfig.action.wrap : true;
    html += '<label style="display:flex;align-items:center;gap:0.5rem;margin:0;"><input type="checkbox" id="sd-btn-wrap"' + (wrapText ? ' checked' : '') + '> Wrap text</label>';
    html += '</div>';

    html += '<div class="modal-field">';
    html += '<label>Action Type</label>';
    html += '<select id="sd-btn-action-type" onchange="updateSdActionFields()">';
    html += '<option value="">-- Select --</option>';
    html += '<option value="preset"' + (btnConfig.action_type === 'preset' ? ' selected' : '') + '>Load Preset</option>';
    html += '<option value="cue_next"' + (btnConfig.action_type === 'cue_next' ? ' selected' : '') + '>Cue Next</option>';
    html += '<option value="cue_back"' + (btnConfig.action_type === 'cue_back' ? ' selected' : '') + '>Cue Back</option>';
    html += '<option value="cue_go"' + (btnConfig.action_type === 'cue_go' ? ' selected' : '') + '>Cue Go (specific)</option>';
    html += '<option value="parameter"' + (btnConfig.action_type === 'parameter' ? ' selected' : '') + '>Set Parameter</option>';
    html += '<option value="pulse"' + (btnConfig.action_type === 'pulse' ? ' selected' : '') + '>Pulse Parameter</option>';
    html += '<option value="toggle"' + (btnConfig.action_type === 'toggle' ? ' selected' : '') + '>Toggle Parameter</option>';
    html += '<option value="python"' + (btnConfig.action_type === 'python' ? ' selected' : '') + '>Python Code</option>';
    html += '</select>';
    html += '</div>';

    html += '<div id="sd-action-fields">';
    html += renderSdActionFields(btnConfig);
    html += '</div>';

    html += '<div class="modal-actions">';
    html += '<button onclick="clearSdButton(' + keyIndex + ')">Clear</button>';
    html += '<button onclick="this.closest(`.modal-overlay`).remove()">Cancel</button>';
    html += '<button onclick="saveSdButton(' + keyIndex + ')">Save</button>';
    html += '</div>';
    html += '</div>';

    overlay.innerHTML = html;
    document.body.appendChild(overlay);
}

function renderSdActionFields(config) {
    const action = config.action || {};
    const actionType = config.action_type || '';
    let html = '';

    switch(actionType) {
        case 'preset':
            html += '<div class="modal-field"><label>Preset Name</label>';
            html += '<input type="text" id="sd-action-preset-name" value="' + (action.preset_name || '') + '"></div>';
            html += '<div class="modal-field"><label>Component Path</label>';
            html += '<input type="text" id="sd-action-comp-path" value="' + (action.comp_path || '') + '" placeholder="/project1/mycomp"></div>';
            break;
        case 'cue_go':
            html += '<div class="modal-field"><label>Cue ID</label>';
            html += '<input type="text" id="sd-action-cue-id" value="' + (action.cue_id || '') + '"></div>';
            break;
        case 'parameter':
        case 'pulse':
        case 'toggle':
            html += '<div class="modal-field"><label>Component Path</label>';
            html += '<input type="text" id="sd-action-path" value="' + (action.path || '') + '" placeholder="/project1/mycomp"></div>';
            html += '<div class="modal-field"><label>Parameter Name</label>';
            html += '<input type="text" id="sd-action-param" value="' + (action.param || '') + '"></div>';
            if (actionType === 'parameter') {
                html += '<div class="modal-field"><label>Value</label>';
                html += '<input type="text" id="sd-action-value" value="' + (action.value !== undefined ? action.value : '') + '"></div>';
            }
            break;
        case 'python':
            html += '<div class="modal-field"><label>Python Code</label>';
            html += '<textarea id="sd-action-code">' + (action.code || '') + '</textarea></div>';
            break;
    }

    return html;
}

function updateSdActionFields() {
    const actionType = document.getElementById('sd-btn-action-type').value;
    const container = document.getElementById('sd-action-fields');
    container.innerHTML = renderSdActionFields({ action_type: actionType, action: {} });
}

async function saveSdButton(keyIndex) {
    const label = document.getElementById('sd-btn-label').value;
    const actionType = document.getElementById('sd-btn-action-type').value;
    const bgColor = document.getElementById('sd-btn-bgcolor').value;
    const pressedColor = document.getElementById('sd-btn-pressedcolor').value;
    const textColor = document.getElementById('sd-btn-textcolor').value;
    const fontSizeVal = document.getElementById('sd-btn-fontsize').value;
    const fontSize = fontSizeVal ? parseInt(fontSizeVal) : null;
    const autoSize = document.getElementById('sd-btn-autosize').checked;
    const wrap = document.getElementById('sd-btn-wrap').checked;

    if (!actionType) {
        alert('Please select an action type');
        return;
    }

    let action = {
        bg_color: bgColor,
        pressed_color: pressedColor,
        text_color: textColor,
        font_size: fontSize,
        auto_size: autoSize,
        wrap: wrap
    };
    switch(actionType) {
        case 'preset':
            action.preset_name = document.getElementById('sd-action-preset-name').value;
            action.comp_path = document.getElementById('sd-action-comp-path').value;
            break;
        case 'cue_go':
            action.cue_id = document.getElementById('sd-action-cue-id').value;
            break;
        case 'parameter':
            action.path = document.getElementById('sd-action-path').value;
            action.param = document.getElementById('sd-action-param').value;
            action.value = document.getElementById('sd-action-value').value;
            break;
        case 'pulse':
        case 'toggle':
            action.path = document.getElementById('sd-action-path').value;
            action.param = document.getElementById('sd-action-param').value;
            break;
        case 'python':
            action.code = document.getElementById('sd-action-code').value;
            break;
    }

    try {
        const res = await fetch('/streamdeck/config/set', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                device_serial: sdSelectedDevice,
                button_id: keyIndex,
                button_type: 'key',
                action_type: actionType,
                action: action,
                label: label
            })
        });
        const data = await res.json();
        if (data.success) {
            document.querySelector('.modal-overlay').remove();
            await loadStreamDeck();
        } else {
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function clearSdButton(keyIndex) {
    if (!confirm('Clear this button configuration?')) return;
    try {
        const res = await fetch('/streamdeck/config/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                device_serial: sdSelectedDevice,
                button_id: keyIndex,
                button_type: 'key'
            })
        });
        const data = await res.json();
        document.querySelector('.modal-overlay').remove();
        await loadStreamDeck();
        console.log('Button ' + (keyIndex + 1) + ' cleared. Hardware syncing...');
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function clearAllSdButtons() {
    const model = SD_MODELS[sdDeviceModel];
    const deviceLabel = sdSelectedDevice === 'default' ? 'all devices (default)' : sdSelectedDevice;
    if (!confirm('Clear ALL ' + model.keys + ' button configurations for ' + deviceLabel + '?')) return;
    try {
        for (let i = 0; i < model.keys; i++) {
            await fetch('/streamdeck/config/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    device_serial: sdSelectedDevice,
                    button_id: i,
                    button_type: 'key'
                })
            });
        }
        if (model.dials) {
            for (let i = 0; i < model.dials; i++) {
                await fetch('/streamdeck/config/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        device_serial: sdSelectedDevice,
                        button_id: i,
                        button_type: 'dial_turn'
                    })
                });
                await fetch('/streamdeck/config/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        device_serial: sdSelectedDevice,
                        button_id: i,
                        button_type: 'dial_push'
                    })
                });
            }
        }
        await loadStreamDeck();
    } catch (e) {
        alert('Error clearing buttons: ' + e.message);
    }
}

async function saveSdProfile() {
    const name = document.getElementById('sd-profile-name').value.trim();
    if (!name) { alert('Enter a profile name'); return; }
    try {
        const res = await fetch('/streamdeck/profiles/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.success) {
            alert('Profile saved: ' + name);
            document.getElementById('sd-profile-name').value = '';
            await loadStreamDeck();
        } else {
            alert('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function loadSdProfile(name) {
    if (!name) {
        await loadStreamDeck();
        return;
    }
    try {
        const panel = document.getElementById('streamdeck-panel');
        const oldHtml = panel.innerHTML;
        panel.innerHTML = '<p style="text-align:center;padding:2rem;">Loading page "' + name + '"...</p>';

        const res = await fetch('/streamdeck/profiles/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.success) {
            await loadStreamDeck();
            console.log('Page "' + name + '" loaded - ' + data.button_count + ' buttons. Hardware syncing...');
        } else {
            panel.innerHTML = oldHtml;
            alert('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteSdProfile() {
    const select = document.getElementById('sd-profile-select');
    const name = select.value;
    if (!name) {
        alert('Select a profile/page to delete first');
        return;
    }
    if (!confirm('Delete profile "' + name + '"?')) return;
    try {
        const res = await fetch('/streamdeck/profiles/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.success) {
            await loadStreamDeck();
        } else {
            alert('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function exportCompanion() {
    try {
        const res = await fetch('/streamdeck/export/companion', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const data = await res.json();
        if (data.success) {
            const exportData = data.companion_config;
            const json = JSON.stringify(exportData, null, 2);

            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

            let html = '<div class="modal" style="max-width:600px;">';
            html += '<h3>Companion Export</h3>';
            html += '<p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:1rem;">Configure these OSC messages in Bitfocus Companion:</p>';
            html += '<div class="export-section">';
            html += '<h4>OSC Settings</h4>';
            html += '<p style="font-size:0.875rem;">Host: ' + exportData.td_osc_host + ', Port: ' + exportData.td_osc_port + '</p>';
            html += '</div>';

            if (exportData.buttons && exportData.buttons.length > 0) {
                html += '<div class="export-section">';
                html += '<h4>Button OSC Addresses</h4>';
                for (const btn of exportData.buttons) {
                    html += '<div style="padding:0.5rem;background:var(--bg-tertiary);margin-bottom:0.5rem;border-radius:4px;">';
                    html += '<strong>Button ' + (parseInt(btn.button_id) + 1) + ': ' + btn.label + '</strong><br>';
                    html += '<code style="font-size:0.75rem;">' + btn.osc_address + ' ' + JSON.stringify(btn.osc_args) + '</code>';
                    html += '</div>';
                }
                html += '</div>';
            }

            html += '<div class="export-section">';
            html += '<h4>Full JSON (for reference)</h4>';
            html += '<pre id="companion-json">' + json + '</pre>';
            html += '</div>';

            html += '<div class="modal-actions">';
            html += '<button onclick="navigator.clipboard.writeText(document.getElementById(`companion-json`).textContent);alert(`Copied!`)">Copy JSON</button>';
            html += '<button onclick="this.closest(`.modal-overlay`).remove()">Close</button>';
            html += '</div>';
            html += '</div>';

            overlay.innerHTML = html;
            document.body.appendChild(overlay);
        } else {
            alert('Export failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

// === NEW PAGE SYSTEM FUNCTIONS ===

async function saveSdPage() {
    const name = document.getElementById('sd-page-name').value.trim();
    if (!name) { alert('Enter a page name'); return; }

    const buttons = {};
    for (const [key, config] of Object.entries(sdConfig)) {
        if (key.startsWith(sdSelectedDevice + ':key:')) {
            const btnId = key.split(':')[2];
            buttons[btnId] = {
                label: config.label || '',
                action_type: config.action_type || '',
                action: config.action || {},
                icon_path: config.icon_path || ''
            };
        }
    }

    try {
        const res = await fetch('/streamdeck/pages/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: name,
                device_type: sdDeviceModel,
                device_serial: sdSelectedDevice !== 'default' ? sdSelectedDevice : '',
                buttons: buttons
            })
        });
        const data = await res.json();
        if (data.success) {
            alert('Page saved: ' + name + ' (bound to ' + sdDeviceModel.toUpperCase() + ')');
            document.getElementById('sd-page-name').value = '';
            await loadStreamDeck();
        } else {
            alert('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function loadSdPage(name) {
    if (!name) {
        await loadStreamDeck();
        return;
    }
    try {
        const panel = document.getElementById('streamdeck-panel');
        panel.innerHTML = '<p style="text-align:center;padding:2rem;">Loading page "' + name + '"...</p>';

        const res = await fetch('/streamdeck/pages/get', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (!data.success || !data.page) {
            alert('Page not found: ' + name);
            await loadStreamDeck();
            return;
        }

        const page = data.page;
        const buttons = page.buttons || {};

        for (const [key, config] of Object.entries(sdConfig)) {
            if (key.startsWith(sdSelectedDevice + ':key:')) {
                await fetch('/streamdeck/config/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        device_serial: sdSelectedDevice,
                        button_id: key.split(':')[2],
                        button_type: 'key'
                    })
                });
            }
        }

        for (const [btnId, btnConfig] of Object.entries(buttons)) {
            if (btnConfig.action_type) {
                await fetch('/streamdeck/config/set', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        device_serial: sdSelectedDevice,
                        button_id: btnId,
                        button_type: 'key',
                        action_type: btnConfig.action_type,
                        action: btnConfig.action,
                        label: btnConfig.label || ''
                    })
                });
            }
        }

        await loadStreamDeck();
        console.log('Page "' + name + '" loaded to device ' + sdSelectedDevice);
    } catch (e) {
        alert('Error: ' + e.message);
        await loadStreamDeck();
    }
}

async function activateSdPage() {
    const select = document.getElementById('sd-page-select');
    const pageName = select.value;
    if (!pageName) {
        alert('Select a page to activate');
        return;
    }
    if (sdSelectedDevice === 'default') {
        alert('Select a specific device first');
        return;
    }

    try {
        const res = await fetch('/streamdeck/pages/activate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                device_serial: sdSelectedDevice,
                page_name: pageName
            })
        });
        const data = await res.json();
        if (data.success) {
            alert('Page "' + pageName + '" activated on device');
            await loadSdPage(pageName);
        } else {
            alert('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteSdPage() {
    const select = document.getElementById('sd-page-select');
    const name = select.value;
    if (!name) {
        alert('Select a page to delete first');
        return;
    }
    if (!confirm('Delete page "' + name + '"?')) return;

    try {
        const res = await fetch('/streamdeck/pages/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.success) {
            await loadStreamDeck();
        } else {
            alert('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

// Service control functions
async function startSdService() {
    try {
        const res = await fetch('/streamdeck/service/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const data = await res.json();
        if (data.success) {
            await loadStreamDeck();
        } else {
            alert('Failed to start service: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function stopSdService() {
    try {
        const res = await fetch('/streamdeck/service/stop', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const data = await res.json();
        if (data.success) {
            await loadStreamDeck();
        } else {
            alert('Failed to stop service: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function restartSdService() {
    try {
        const res = await fetch('/streamdeck/service/restart', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: '{}'
        });
        const data = await res.json();
        if (data.success) {
            await loadStreamDeck();
        } else {
            alert('Failed to restart service: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function toggleAutoStart(enabled) {
    try {
        const res = await fetch('/streamdeck/service/autostart', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ enabled: enabled })
        });
        const data = await res.json();
        if (data.success) {
            sdServiceStatus.autostart = enabled;
            console.log('Auto-start ' + (enabled ? 'enabled' : 'disabled'));
        } else {
            alert('Failed to set auto-start: ' + (data.error || 'Unknown error'));
            await loadStreamDeck();
        }
    } catch (e) {
        alert('Error: ' + e.message);
        await loadStreamDeck();
    }
}