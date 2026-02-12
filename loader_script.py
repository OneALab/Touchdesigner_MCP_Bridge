"""
MCP Bridge Loader - Loads core + modules from local repo or GitHub

Click the button in mcp_bridge_loader to run this script.
It will:
1. Load td_setup.py (core bridge) from local repo, GitHub, or cache
2. Load module_loader.py (module system) from local repo, GitHub, or cache
3. Load all module files from local repo, GitHub, or cache
4. Execute td_setup.py then module_loader.py to set up the complete bridge

Priority: local repo files > GitHub > cache
Cache location: %APPDATA%/TouchDesigner/mcp_bridge_cache/
"""
import os
import urllib.request
import ssl
import json

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/OneALab/Touchdesigner_MCP_Bridge/master"

# Known local repo locations (checked in order)
LOCAL_REPO_PATHS = [
    r"c:\Users\onea\Dropbox (Personal)\TouchDesigner\_mcp_bridge",
    os.path.join(os.path.expanduser("~"), "Dropbox (Personal)", "TouchDesigner", "_mcp_bridge"),
]

# Core files to fetch
CORE_FILES = {
    'td_setup.py': f"{GITHUB_RAW_BASE}/td_setup.py",
    'module_loader.py': f"{GITHUB_RAW_BASE}/module_loader.py",
}

# Module files to fetch (path relative to repo root -> URL)
MODULE_FILES = {
    # Presets
    'modules/mod_presets/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_presets/__init__.py",
    'modules/mod_presets/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_presets/handler.py",
    # Cues
    'modules/mod_cues/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_cues/__init__.py",
    'modules/mod_cues/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_cues/handler.py",
    # Preview
    'modules/mod_preview/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_preview/__init__.py",
    'modules/mod_preview/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_preview/handler.py",
    # Timeline
    'modules/mod_timeline/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_timeline/__init__.py",
    'modules/mod_timeline/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_timeline/handler.py",
    # UI
    'modules/mod_ui/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_ui/__init__.py",
    'modules/mod_ui/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_ui/handler.py",
    'modules/mod_ui/assets/index.html': f"{GITHUB_RAW_BASE}/modules/mod_ui/assets/index.html",
    'modules/mod_ui/assets/styles.css': f"{GITHUB_RAW_BASE}/modules/mod_ui/assets/styles.css",
    'modules/mod_ui/assets/app.js': f"{GITHUB_RAW_BASE}/modules/mod_ui/assets/app.js",
    'modules/mod_ui/assets/controls.js': f"{GITHUB_RAW_BASE}/modules/mod_ui/assets/controls.js",
    'modules/mod_ui/assets/preview.js': f"{GITHUB_RAW_BASE}/modules/mod_ui/assets/preview.js",
    # OSC
    'modules/mod_osc/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_osc/__init__.py",
    'modules/mod_osc/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_osc/handler.py",
    # StreamDeck
    'modules/mod_streamdeck/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_streamdeck/__init__.py",
    'modules/mod_streamdeck/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_streamdeck/handler.py",
    # DMX (stub)
    'modules/mod_dmx/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_dmx/__init__.py",
    'modules/mod_dmx/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_dmx/handler.py",
    # MIDI (stub)
    'modules/mod_midi/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_midi/__init__.py",
    'modules/mod_midi/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_midi/handler.py",
    # Media (stub)
    'modules/mod_media/__init__.py': f"{GITHUB_RAW_BASE}/modules/mod_media/__init__.py",
    'modules/mod_media/handler.py': f"{GITHUB_RAW_BASE}/modules/mod_media/handler.py",
}


def find_local_repo():
    """Find local repo directory."""
    # Try TD's project folder first
    try:
        pf = project.folder
        if pf:
            for candidate in [
                os.path.join(pf, '_mcp_bridge'),
                os.path.join(os.path.dirname(pf), '_mcp_bridge'),
                pf,
            ]:
                if os.path.exists(os.path.join(candidate, 'td_setup.py')):
                    return candidate
    except Exception:
        pass

    # Try known locations
    for path in LOCAL_REPO_PATHS:
        if os.path.exists(os.path.join(path, 'td_setup.py')):
            return path

    return None


def get_cache_dir():
    """Get platform-appropriate cache directory."""
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/Library/Application Support')
    cache_dir = os.path.join(base, 'TouchDesigner', 'mcp_bridge_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def load_from_local(filename, local_repo):
    """Load file from local repo."""
    if local_repo is None:
        return None
    local_path = os.path.join(local_repo, filename.replace('/', os.sep))
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def fetch_from_github(url):
    """Fetch file from GitHub."""
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=15, context=ctx) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"    GitHub fetch failed: {e}")
        return None


def load_from_cache(filename):
    """Load file from local cache."""
    cache_path = os.path.join(get_cache_dir(), filename.replace('/', os.sep))
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def save_to_cache(filename, content):
    """Save file to local cache."""
    cache_path = os.path.join(get_cache_dir(), filename.replace('/', os.sep))
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)


def fetch_file(filename, url, local_repo):
    """Load file: local repo first, then GitHub, then cache."""
    # 1. Try local repo (always preferred — has latest dev changes)
    content = load_from_local(filename, local_repo)
    if content:
        save_to_cache(filename, content)
        print(f"  + {filename} (local repo)")
        return content

    # 2. Try GitHub
    content = fetch_from_github(url)
    if content:
        save_to_cache(filename, content)
        print(f"  + {filename} (GitHub)")
        return content

    # 3. Try cache
    content = load_from_cache(filename)
    if content:
        print(f"  + {filename} (cache)")
        return content

    print(f"  x {filename} not available")
    return None


def run_setup():
    """Main entry point - load core + modules, set up complete bridge."""
    print("=" * 60)
    print("MCP Bridge Loader v2.0")
    print("=" * 60)

    # Find local repo
    local_repo = find_local_repo()
    if local_repo:
        print(f"Local repo: {local_repo}")
    else:
        print("Local repo not found, will fetch from GitHub")

    # Fetch core files
    print("-" * 60)
    print("Loading core files...")
    td_setup_code = fetch_file('td_setup.py', CORE_FILES['td_setup.py'], local_repo)
    module_loader_code = fetch_file('module_loader.py', CORE_FILES['module_loader.py'], local_repo)

    if not td_setup_code:
        print("ERROR: Cannot load td_setup.py")
        print("Check internet connection or download manually.")
        return

    if not module_loader_code:
        print("ERROR: Cannot load module_loader.py")
        print("Check internet connection or download manually.")
        return

    # Fetch module files
    print("-" * 60)
    print("Loading module files...")
    fetched_modules = {}
    for path, url in MODULE_FILES.items():
        content = fetch_file(path, url, local_repo)
        fetched_modules[path] = content

    available = sum(1 for v in fetched_modules.values() if v is not None)
    total = len(MODULE_FILES)
    print(f"  {available}/{total} module files loaded")

    # Write module files to cache directory for module_loader to use
    cache_dir = get_cache_dir()
    modules_base = os.path.join(cache_dir, 'modules')
    print(f"  Module cache: {modules_base}")

    # Run core setup
    print("-" * 60)
    print("Setting up core bridge...")
    try:
        exec(td_setup_code, globals())
        print("  + Core bridge created")
    except Exception as e:
        import traceback
        print(f"ERROR setting up core: {e}")
        traceback.print_exc()
        return

    # Run module loader
    print("-" * 60)
    print("Loading modules...")
    try:
        loader_globals = dict(globals())
        loader_globals['_cached_modules'] = fetched_modules
        loader_globals['_cache_dir'] = cache_dir
        exec(module_loader_code, loader_globals)
        print("  + Module loader executed")
    except Exception as e:
        import traceback
        print(f"WARNING: Module loader failed: {e}")
        traceback.print_exc()

    print("=" * 60)
    print("MCP Bridge setup complete!")
    print("")
    print("  Core API:  http://127.0.0.1:9980/ping")
    print("  Modules:   http://127.0.0.1:9980/modules")
    print("  Web UI:    http://127.0.0.1:9981/ui")
    print("")
    print("Core runs on port 9980, modules on port 9981.")
    print("=" * 60)


# Run when script is executed
run_setup()
