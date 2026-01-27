#!/usr/bin/env python3
"""
TouchDesigner MCP Bridge - Unified Setup Script

This script sets up both the TouchDesigner side and Claude Code side in one workflow.

Usage:
    python setup.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def find_dropbox_path():
    """Auto-detect the Dropbox folder path."""
    home = Path.home()

    # Method 1: Check Dropbox's info.json config file
    dropbox_info_paths = [
        home / ".dropbox" / "info.json",
        home / "AppData" / "Local" / "Dropbox" / "info.json",  # Windows
    ]

    for info_path in dropbox_info_paths:
        if info_path.exists():
            try:
                with open(info_path, 'r') as f:
                    info = json.load(f)
                    if 'personal' in info and 'path' in info['personal']:
                        return Path(info['personal']['path'])
                    if 'business' in info and 'path' in info['business']:
                        return Path(info['business']['path'])
            except (json.JSONDecodeError, KeyError):
                pass

    # Method 2: Check common locations
    common_paths = [
        home / "Dropbox (Personal)",
        home / "Dropbox",
        Path("C:/Users") / os.getenv("USERNAME", "user") / "Dropbox (Personal)",
        Path("C:/Users") / os.getenv("USERNAME", "user") / "Dropbox",
        Path("D:/Dropbox"),
        Path("D:/Dropbox (Personal)"),
    ]

    for path in common_paths:
        if path.exists() and path.is_dir():
            return path

    return None


def find_mcp_bridge(dropbox_path):
    """Find the _mcp_bridge folder within Dropbox."""
    if dropbox_path is None:
        return None

    possible_paths = [
        dropbox_path / "TouchDesigner" / "_mcp_bridge",
        dropbox_path / "touchdesigner" / "_mcp_bridge",
        dropbox_path / "TD" / "_mcp_bridge",
    ]

    for path in possible_paths:
        if path.exists() and (path / "mcp_server.py").exists():
            return path

    # Search more broadly (one level deep)
    try:
        for subdir in dropbox_path.iterdir():
            if subdir.is_dir():
                bridge_path = subdir / "_mcp_bridge"
                if bridge_path.exists() and (bridge_path / "mcp_server.py").exists():
                    return bridge_path
    except PermissionError:
        pass

    return None


def get_script_dir():
    """Get the directory where this script is located."""
    return Path(__file__).parent.resolve()


def test_touchdesigner_connection(timeout=2):
    """Test if TouchDesigner bridge is running and responding."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request("http://127.0.0.1:9980/ping")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('status') == 'ok'
    except:
        return False


def copy_to_clipboard(text):
    """Copy text to clipboard (cross-platform)."""
    try:
        # Try pyperclip first
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    # Platform-specific fallbacks
    if sys.platform == 'win32':
        try:
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            return True
        except:
            pass
    elif sys.platform == 'darwin':
        try:
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            return True
        except:
            pass
    else:  # Linux
        for cmd in ['xclip -selection clipboard', 'xsel --clipboard']:
            try:
                process = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
                return True
            except:
                pass

    return False


def open_file(path):
    """Open a file with the default application (cross-platform)."""
    path = str(path)
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', path])
    else:
        subprocess.run(['xdg-open', path])


def run_claude_mcp_add(bridge_path):
    """Run the claude mcp add command."""
    mcp_server = bridge_path / "mcp_server.py"
    cmd = [
        "claude", "mcp", "add", "touchdesigner", "--scope", "user",
        "--", "python", str(mcp_server)
    ]

    print(f"\nRunning: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except FileNotFoundError:
        return False, "Claude Code CLI not found. Make sure 'claude' is in your PATH."
    except Exception as e:
        return False, str(e)


def get_td_setup_code(bridge_path):
    """Read the td_setup.py code."""
    td_setup_path = bridge_path / "td_setup.py"
    if td_setup_path.exists():
        return td_setup_path.read_text()
    return None


def main():
    print("=" * 60)
    print("TouchDesigner MCP Bridge - Setup")
    print("=" * 60)

    # Step 1: Find the bridge folder
    print("\n[1/5] Locating MCP bridge folder...")

    script_dir = get_script_dir()
    if (script_dir / "mcp_server.py").exists():
        bridge_path = script_dir
        print(f"      Found: {bridge_path}")
    else:
        print("      Searching for Dropbox folder...")
        dropbox_path = find_dropbox_path()

        if dropbox_path:
            print(f"      Dropbox: {dropbox_path}")
            bridge_path = find_mcp_bridge(dropbox_path)
        else:
            bridge_path = None

        if bridge_path:
            print(f"      Bridge: {bridge_path}")
        else:
            print("      ERROR: Could not find _mcp_bridge folder.")
            print("      Run this script from within the _mcp_bridge folder.")
            sys.exit(1)

    # Step 2: Verify files exist
    print("\n[2/5] Verifying installation...")
    mcp_server = bridge_path / "mcp_server.py"
    tox_file = bridge_path / "mcp_bridge.tox"
    td_setup = bridge_path / "td_setup.py"

    if not mcp_server.exists():
        print(f"      ERROR: mcp_server.py not found")
        sys.exit(1)
    print(f"      mcp_server.py: OK")

    if tox_file.exists():
        print(f"      mcp_bridge.tox: OK")
    else:
        print(f"      mcp_bridge.tox: Not found (will use td_setup.py)")

    if td_setup.exists():
        print(f"      td_setup.py: OK")

    # Step 3: Check TouchDesigner connection
    print("\n[3/5] Checking TouchDesigner connection...")
    td_connected = test_touchdesigner_connection()

    if td_connected:
        print("      TouchDesigner bridge is RUNNING on port 9980")
        print("      Skipping TD setup - bridge already active")
    else:
        print("      TouchDesigner bridge not detected")
        print("\n      How would you like to set up TouchDesigner?")
        print("      1. Open mcp_bridge.tox (drag into your TD project)")
        print("      2. Copy td_setup.py to clipboard (paste into Text DAT, run)")
        print("      3. Skip TD setup for now")

        while True:
            choice = input("\n      Choice (1/2/3): ").strip()

            if choice == "1":
                if tox_file.exists():
                    print(f"\n      Opening: {tox_file}")
                    open_file(tox_file)
                    print("      Drag the mcp_bridge component into your TD project.")
                    input("      Press Enter when done...")
                else:
                    print("      ERROR: mcp_bridge.tox not found")
                    print("      Use option 2 instead")
                    continue
                break

            elif choice == "2":
                code = get_td_setup_code(bridge_path)
                if code and copy_to_clipboard(code):
                    print("\n      td_setup.py copied to clipboard!")
                    print("      In TouchDesigner:")
                    print("        1. Create a Text DAT")
                    print("        2. Paste (Ctrl+V)")
                    print("        3. Right-click > Run Script")
                    input("      Press Enter when done...")
                else:
                    print("      ERROR: Could not copy to clipboard")
                    print(f"      Manually copy from: {td_setup}")
                break

            elif choice == "3":
                print("      Skipping TD setup")
                break

            else:
                print("      Invalid choice. Enter 1, 2, or 3.")

    # Step 4: Configure Claude Code
    print("\n[4/5] Configure Claude Code")
    print("\n      How would you like to configure?")
    print("      1. Auto-configure (run 'claude mcp add' command)")
    print("      2. Show manual instructions")
    print("      3. Skip")

    while True:
        choice = input("\n      Choice (1/2/3): ").strip()

        if choice == "1":
            print("\n      Configuring Claude Code...")
            success, message = run_claude_mcp_add(bridge_path)
            if success:
                print("      SUCCESS! Claude Code configured.")
            else:
                print(f"      Failed: {message}")
                print("      Try manual configuration (option 2)")
            break

        elif choice == "2":
            print("\n      --- Manual Configuration ---")
            print(f"\n      Run this command:")
            print(f'      claude mcp add touchdesigner --scope user -- python "{mcp_server}"')
            print("\n      Or add to .mcp.json:")
            print('      {"mcpServers": {"touchdesigner": {"command": "python",')
            print(f'        "args": ["{mcp_server}"]')
            print('      }}}')
            break

        elif choice == "3":
            print("      Skipping Claude Code setup")
            break

        else:
            print("      Invalid choice. Enter 1, 2, or 3.")

    # Step 5: Verify
    print("\n[5/5] Verification")
    td_connected = test_touchdesigner_connection()
    if td_connected:
        print("      TouchDesigner bridge: CONNECTED")
    else:
        print("      TouchDesigner bridge: NOT CONNECTED")
        print("      (Start TD with the bridge to use MCP tools)")

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Restart Claude Code to load the MCP server")
    print("  2. Start TouchDesigner with the MCP bridge")
    print("  3. Test with: Ask Claude to 'ping TouchDesigner'")
    print("\n")


if __name__ == "__main__":
    main()
