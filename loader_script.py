"""
MCP Bridge Loader - Fetches and runs td_setup.py from GitHub

This script should be placed in a Text DAT inside mcp_bridge_loader.tox.
When run, it will:
1. Fetch the latest td_setup.py from GitHub
2. Cache it locally for offline use
3. Execute the script to set up the MCP bridge

To use:
1. Create a Text DAT named 'loader' inside mcp_bridge_loader
2. Paste this script
3. Set the Text DAT's 'Run' parameter to True, or right-click and Run Script
"""
import os
import urllib.request
import ssl

GITHUB_RAW_URL = "https://raw.githubusercontent.com/OneALab/Touchdesigner_MCP_Bridge/master/td_setup.py"

def get_cache_path():
    """Get platform-appropriate cache directory."""
    if os.name == 'nt':  # Windows
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:  # macOS/Linux
        base = os.path.expanduser('~/Library/Application Support')
    cache_dir = os.path.join(base, 'TouchDesigner', 'mcp_bridge_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, 'td_setup.py')

def fetch_from_github():
    """Fetch td_setup.py from GitHub."""
    try:
        # Create SSL context that works with most systems
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(GITHUB_RAW_URL, timeout=10, context=ctx) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch from GitHub: {e}")
        return None

def load_from_cache():
    """Load td_setup.py from local cache."""
    cache_path = get_cache_path()
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def save_to_cache(content):
    """Save td_setup.py to local cache."""
    cache_path = get_cache_path()
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Cached to: {cache_path}")

def run_setup():
    """Main entry point - fetch, cache, and run td_setup.py."""
    print("=" * 60)
    print("MCP Bridge Loader")
    print("=" * 60)
    print(f"Fetching from: {GITHUB_RAW_URL}")

    # Try GitHub first
    content = fetch_from_github()

    if content:
        save_to_cache(content)
        print("Successfully fetched latest version from GitHub")
    else:
        # Fall back to cache
        content = load_from_cache()
        if content:
            print("Using cached version (GitHub unreachable)")
        else:
            print("ERROR: Cannot fetch from GitHub and no cached version available")
            print(f"Please manually download from: {GITHUB_RAW_URL}")
            print("Or ensure you have internet connectivity for first run.")
            return

    # Execute the setup script
    print("-" * 60)
    print("Running td_setup.py...")
    print("-" * 60)
    try:
        exec(content, globals())
        print("=" * 60)
        print("MCP Bridge setup complete!")
        print("Test: http://127.0.0.1:9980/ping")
        print("Web UI: http://127.0.0.1:9980/ui")
        print("=" * 60)
    except Exception as e:
        import traceback
        print(f"ERROR running td_setup.py: {e}")
        traceback.print_exc()

# Run when script is executed
run_setup()
