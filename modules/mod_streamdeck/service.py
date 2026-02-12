#!/usr/bin/env python3
"""
Stream Deck Service for TouchDesigner MCP Bridge - Direct HID Mode

This standalone service connects to Elgato Stream Deck devices via USB HID
and sends commands to TouchDesigner via HTTP API.

Requirements:
    pip install streamdeck pillow requests

Windows: Requires LibUSB DLL from https://libusb.info
Linux: Requires udev rules for non-root access

Usage:
    python streamdeck_service.py [--host HOST] [--port PORT] [--poll SECONDS]
"""

import sys
import time
import json
import argparse
import threading
from pathlib import Path

def is_frozen():
    """Check if running as PyInstaller bundle."""
    return getattr(sys, 'frozen', False)

def pause_on_exit():
    """Pause before exit if running as frozen exe (so user can read errors)."""
    if is_frozen():
        print("\nPress Enter to exit...")
        try:
            input()
        except:
            pass

def fatal_error(message):
    """Print error and exit, pausing if frozen."""
    print(message)
    pause_on_exit()
    sys.exit(1)

try:
    import requests
except ImportError:
    fatal_error("ERROR: requests not installed. Run: pip install requests")

try:
    from StreamDeck.DeviceManager import DeviceManager
    from StreamDeck.Devices.StreamDeck import DialEventType, TouchscreenEventType
except ImportError:
    fatal_error("ERROR: streamdeck library not installed. Run: pip install streamdeck\n"
                "Windows users: Also need hidapi.dll in the same folder as the exe.\n"
                "Download from: https://github.com/libusb/hidapi/releases")

try:
    from PIL import Image, ImageDraw, ImageFont
    from StreamDeck.ImageHelpers import PILHelper
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: Pillow not installed. Button images disabled. Run: pip install pillow")


class StreamDeckService:
    """Service that bridges Stream Deck hardware to TouchDesigner."""

    def __init__(self, td_host='127.0.0.1', core_port=9980, ui_port=9981, poll_interval=0.5):
        self.td_host = td_host
        self.core_port = core_port
        self.ui_port = ui_port
        self.poll_interval = poll_interval

        self.core_api = f"http://{td_host}:{core_port}"
        self.ui_api = f"http://{td_host}:{ui_port}"

        self.devices = {}
        self.config = {}
        self.running = False
        self.config_lock = threading.Lock()

    def discover_devices(self):
        """Find and initialize all connected Stream Deck devices."""
        try:
            decks = DeviceManager().enumerate()
            print(f"Found {len(decks)} Stream Deck device(s)")

            for deck in decks:
                try:
                    deck.open()
                    deck.reset()

                    serial = deck.get_serial_number()
                    model = deck.deck_type()

                    self.devices[serial] = {
                        'deck': deck,
                        'model': model,
                        'key_count': deck.key_count(),
                        'has_dials': hasattr(deck, 'dial_count') and deck.dial_count() > 0,
                        'has_touchscreen': hasattr(deck, 'touchscreen_width')
                    }

                    print(f"  - {model} (serial: {serial})")
                    print(f"    Keys: {deck.key_count()}")

                    if self.devices[serial]['has_dials']:
                        print(f"    Dials: {deck.dial_count()}")

                    # Set up callbacks
                    deck.set_key_callback(lambda d, k, s: self._on_key(d, k, s))

                    if hasattr(deck, 'set_dial_callback'):
                        deck.set_dial_callback(lambda d, dial, evt, val: self._on_dial(d, dial, evt, val))

                    if hasattr(deck, 'set_touchscreen_callback'):
                        deck.set_touchscreen_callback(lambda d, evt, val: self._on_touch(d, evt, val))

                    # Set initial brightness
                    deck.set_brightness(80)

                except Exception as e:
                    print(f"  ERROR initializing device: {e}")

            return len(self.devices)

        except Exception as e:
            print(f"ERROR discovering devices: {e}")
            return 0

    def _get_serial(self, deck):
        """Get serial number from deck object."""
        try:
            return deck.get_serial_number()
        except:
            return 'unknown'

    def _get_button_config(self, serial, button_type, button_id):
        """Get button config - ONLY serial-specific, no fallback to default."""
        # Each device has its own unique configuration
        config_key = f"{serial}:{button_type}:{button_id}"
        return self.config.get(config_key)

    def _on_key(self, deck, key, pressed):
        """Handle button press events."""
        serial = self._get_serial(deck)

        with self.config_lock:
            button_config = self._get_button_config(serial, 'key', key)

        if pressed:
            # Show pressed state
            self._show_button_pressed(deck, key, button_config)

            if button_config:
                label = button_config.get('label', f'Button {key}')
                print(f"Button {key} pressed: {label}")
                self._execute_action(button_config)
            else:
                print(f"Button {key} pressed (no config)")
        else:
            # Button released - restore normal image
            self._restore_button_image(deck, key, button_config)

    def _show_button_pressed(self, deck, key, button_config):
        """Flash the button with pressed color."""
        if not HAS_PIL:
            return
        try:
            action = button_config.get('action', {}) if button_config else {}
            pressed_color = action.get('pressed_color', '#ffffff')  # Default white
            custom_label = button_config.get('label', '') if button_config else ''
            display_label = custom_label if custom_label else str(key + 1)
            use_large_number = not custom_label  # Large centered number if no custom label

            # Get text options - use black text on pressed (white bg) for contrast
            text_color = '#000000'  # Black text on pressed color for readability
            font_size = action.get('font_size') if isinstance(action, dict) and custom_label else None
            auto_size = action.get('auto_size', True) if isinstance(action, dict) else True
            wrap = action.get('wrap', True) if isinstance(action, dict) else True

            image = self._render_button_image(
                deck, display_label,
                bg_color=pressed_color,
                dimmed=use_large_number,  # Large number style when no label
                text_color=text_color,
                font_size=font_size,
                auto_size=auto_size,
                wrap=wrap
            )
            if image:
                deck.set_key_image(key, image)
        except Exception as e:
            print(f"Error showing pressed state: {e}")

    def _restore_button_image(self, deck, key, button_config):
        """Restore the button to its normal state."""
        if not HAS_PIL:
            return
        try:
            # Check if button has ANY config
            has_config = False
            label = ''
            bg_color = None
            text_color = None
            font_size = None
            auto_size = True
            wrap = True

            if button_config:
                label = button_config.get('label', '')
                action = button_config.get('action', {})
                if isinstance(action, dict):
                    bg_color = action.get('bg_color')
                    text_color = action.get('text_color')
                    font_size = action.get('font_size')
                    auto_size = action.get('auto_size', True)
                    wrap = action.get('wrap', True)
                action_type = button_config.get('action_type', '')
                has_config = bool(label or bg_color or action_type)

            display_label = label if label else str(key + 1)
            display_color = bg_color if bg_color else ('#2a2a3e' if not has_config else '#1a1a2e')
            use_large_number = not label  # Large centered number if no custom label

            image = self._render_button_image(
                deck, display_label,
                bg_color=display_color,
                dimmed=use_large_number,  # Large number style when no label
                text_color=text_color if label else None,  # Only use custom color for labels
                font_size=font_size if label else None,  # Only use custom size for labels
                auto_size=auto_size,
                wrap=wrap
            )
            if image:
                deck.set_key_image(key, image)
        except Exception as e:
            print(f"Error restoring button image: {e}")

    def _on_dial(self, deck, dial, event, value):
        """Handle dial events (Stream Deck+)."""
        serial = self._get_serial(deck)

        if event == DialEventType.TURN:
            with self.config_lock:
                dial_config = self._get_button_config(serial, 'dial_turn', dial)

            if dial_config:
                action = dial_config.get('action', {})
                if dial_config.get('action_type') == 'parameter':
                    # Increment/decrement based on rotation direction
                    step = action.get('step', 0.1)
                    delta = step if value > 0 else -step
                    self._increment_parameter(action.get('path'), action.get('param'), delta)
                    print(f"Dial {dial} turned: delta={delta}")
            else:
                print(f"Dial {dial} turned by {value} (no config)")

        elif event == DialEventType.PUSH:
            with self.config_lock:
                dial_config = self._get_button_config(serial, 'dial_push', dial)

            if dial_config:
                label = dial_config.get('label', f'Dial {dial}')
                print(f"Dial {dial} pushed: {label}")
                self._execute_action(dial_config)
            else:
                print(f"Dial {dial} pushed (no config)")

    def _on_touch(self, deck, event, value):
        """Handle touch strip events (Stream Deck+)."""
        serial = self._get_serial(deck)

        if event == TouchscreenEventType.SHORT:
            # Short tap on touch strip
            with self.config_lock:
                touch_config = self._get_button_config(serial, 'touch', 'tap')

            if touch_config:
                action = touch_config.get('action', {})
                if touch_config.get('action_type') == 'parameter':
                    # Map touch position to parameter value
                    x = value.get('x', 0)
                    width = value.get('width', 800)
                    normalized = x / width
                    min_val = action.get('min', 0)
                    max_val = action.get('max', 1)
                    new_value = min_val + normalized * (max_val - min_val)
                    self._set_parameter(action.get('path'), action.get('param'), new_value)
                    print(f"Touch strip: position={normalized:.2f}, value={new_value:.2f}")
                else:
                    self._execute_action(touch_config)
            else:
                print(f"Touch strip tapped at x={value.get('x', 0)} (no config)")

        elif event == TouchscreenEventType.DRAG:
            # Drag on touch strip for continuous control
            with self.config_lock:
                touch_config = self._get_button_config(serial, 'touch', 'drag')

            if touch_config and touch_config.get('action_type') == 'parameter':
                action = touch_config.get('action', {})
                x = value.get('x', 0)
                width = value.get('width', 800)
                normalized = x / width
                min_val = action.get('min', 0)
                max_val = action.get('max', 1)
                new_value = min_val + normalized * (max_val - min_val)
                self._set_parameter(action.get('path'), action.get('param'), new_value)

    def _execute_action(self, button_config):
        """Execute an action in TouchDesigner."""
        action_type = button_config.get('action_type', '')
        action = button_config.get('action', {})

        try:
            if action_type == 'preset':
                self._api_post(f'{self.ui_api}/presets/load', {
                    'name': action.get('preset_name', ''),
                    'comp_path': action.get('comp_path', '')
                })
                print(f"  -> Load preset: {action.get('preset_name')}")

            elif action_type == 'cue_next':
                self._api_post(f'{self.ui_api}/cues/next', {})
                print("  -> Cue: NEXT")

            elif action_type == 'cue_back':
                self._api_post(f'{self.ui_api}/cues/back', {})
                print("  -> Cue: BACK")

            elif action_type == 'cue_go':
                cue_id = action.get('cue_id', '')
                if cue_id:
                    self._api_post(f'{self.ui_api}/cues/go', {'id': cue_id})
                    print(f"  -> Cue GO: {cue_id}")

            elif action_type == 'parameter':
                path = action.get('path', '')
                param = action.get('param', '')
                value = action.get('value')
                self._set_parameter(path, param, value)
                print(f"  -> Set {path}.{param} = {value}")

            elif action_type == 'pulse':
                path = action.get('path', '')
                param = action.get('param', '')
                self._api_post(f'{self.ui_api}/ui/pulse', {
                    'path': path,
                    'parameter': param
                })
                print(f"  -> Pulse {path}.{param}")

            elif action_type == 'toggle':
                path = action.get('path', '')
                param = action.get('param', '')
                # Get current value first
                schema = self._api_post(f'{self.ui_api}/ui/schema', {'path': path})
                if schema and schema.get('success'):
                    for page in schema.get('pages', []):
                        for p in page.get('parameters', []):
                            if p['name'] == param:
                                new_val = not bool(p.get('value'))
                                self._set_parameter(path, param, int(new_val))
                                print(f"  -> Toggle {path}.{param} = {new_val}")
                                return

            elif action_type == 'python':
                code = action.get('code', '')
                if code:
                    self._api_post(f'{self.core_api}/execute', {'code': code})
                    print(f"  -> Execute Python")

            else:
                print(f"  -> Unknown action type: {action_type}")

        except Exception as e:
            print(f"  ERROR executing action: {e}")

    def _set_parameter(self, path, param, value):
        """Set a parameter value in TD."""
        self._api_post(f'{self.ui_api}/ui/set', {
            'changes': [{'path': path, 'parameter': param, 'value': value}]
        })

    def _increment_parameter(self, path, param, delta):
        """Increment a parameter by delta."""
        try:
            schema = self._api_post(f'{self.ui_api}/ui/schema', {'path': path})
            if schema and schema.get('success'):
                for page in schema.get('pages', []):
                    for p in page.get('parameters', []):
                        if p['name'] == param:
                            current = p.get('value', 0)
                            min_val = p.get('min', float('-inf'))
                            max_val = p.get('max', float('inf'))
                            new_val = max(min_val, min(max_val, current + delta))
                            self._set_parameter(path, param, new_val)
                            return
        except Exception as e:
            print(f"Error incrementing parameter: {e}")

    def _api_post(self, url, data, timeout=2):
        """Make a POST request to TD API."""
        try:
            resp = requests.post(url, json=data, timeout=timeout)
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"API timeout: {url}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"API connection error: {url}")
            return None
        except Exception as e:
            print(f"API error: {e}")
            return None

    def poll_config(self):
        """Fetch button configuration from TD."""
        try:
            resp = self._api_post(f'{self.ui_api}/streamdeck/config/get', {}, timeout=3)
            if resp and resp.get('success'):
                new_config = resp.get('config', {})
                with self.config_lock:
                    old_config = self.config
                    self.config = new_config

                    # Check if config actually changed (not just count, but content too)
                    config_changed = (old_config != new_config)

                # Log and return True if config changed
                if config_changed:
                    if len(new_config) > 0:
                        print(f"Config updated: {len(new_config)} button(s) configured")
                        for key in sorted(new_config.keys()):
                            cfg = new_config[key]
                            label = cfg.get('label', '(no label)')
                            action = cfg.get('action', {})
                            bg_color = action.get('bg_color', '(no color)') if isinstance(action, dict) else '(no color)'
                            print(f"  {key}: {cfg.get('action_type', '?')} | label='{label}' | bg={bg_color}")
                    else:
                        print("Config: no buttons configured yet")
                    return True  # Config changed, trigger image update
                return False  # Config same, no update needed
        except Exception as e:
            pass
        return False

    def poll_active_pages(self):
        """Fetch active pages for all devices and convert to config format."""
        try:
            resp = self._api_post(f'{self.ui_api}/streamdeck/pages/all-active', {}, timeout=3)
            if not resp or not resp.get('success'):
                return False

            active_pages = resp.get('active_pages', {})
            if not active_pages:
                return False

            new_config = {}
            for serial, page in active_pages.items():
                buttons = page.get('buttons', {})
                for btn_id, btn_data in buttons.items():
                    config_key = f"{serial}:key:{btn_id}"
                    new_config[config_key] = {
                        'device_serial': serial,
                        'button_id': btn_id,
                        'button_type': 'key',
                        'action_type': btn_data.get('action_type', ''),
                        'action': btn_data.get('action', {}),
                        'label': btn_data.get('label', ''),
                        'icon_path': btn_data.get('icon_path', '')
                    }

            with self.config_lock:
                old_config = self.config
                self.config = new_config
                config_changed = (old_config != new_config)

            if config_changed:
                page_names = [p.get('name', '?') for p in active_pages.values()]
                print(f"Pages updated: {', '.join(page_names)} ({len(new_config)} buttons)")
                return True

            return False
        except Exception as e:
            print(f"Error polling pages: {e}")
            return False

    def update_button_images(self):
        """Update button images on devices (if PIL available)."""
        if not HAS_PIL:
            print("  WARNING: PIL not available, cannot update button images")
            return

        with self.config_lock:
            config_copy = dict(self.config)

        print(f"  Updating images for {len(self.devices)} device(s)...")
        buttons_updated = 0
        buttons_failed = 0
        for serial, device_info in self.devices.items():
            deck = device_info['deck']
            key_count = device_info['key_count']
            print(f"    Device {serial}: {key_count} keys")

            for key in range(key_count):
                # ONLY use serial-specific config - NO fallback to 'default'
                # Each device gets its own unique configuration
                config_key = f"{serial}:key:{key}"
                button_config = config_copy.get(config_key)

                # Check if button has ANY config (action_type, label, or bg_color)
                has_config = False
                label = ''
                bg_color = None
                text_color = None
                font_size = None
                auto_size = True
                wrap = True

                if button_config:
                    label = button_config.get('label', '')
                    action = button_config.get('action', {})
                    if isinstance(action, dict):
                        bg_color = action.get('bg_color')
                        text_color = action.get('text_color')
                        font_size = action.get('font_size')
                        auto_size = action.get('auto_size', True)
                        wrap = action.get('wrap', True)
                    action_type = button_config.get('action_type', '')
                    # Button is configured if it has any of these
                    has_config = bool(label or bg_color or action_type)

                # For unconfigured buttons, show button number with dimmed style
                # Use large number style when showing default number (no custom label)
                display_label = label if label else str(key + 1)
                display_color = bg_color if bg_color else ('#2a2a3e' if not has_config else '#1a1a2e')
                use_large_number = not label  # Large centered number if no custom label

                try:
                    image = self._render_button_image(
                        deck, display_label,
                        bg_color=display_color,
                        dimmed=use_large_number,  # Large number style when no label
                        text_color=text_color if label else None,  # Only use custom color for labels
                        font_size=font_size if label else None,  # Only use custom size for labels
                        auto_size=auto_size,
                        wrap=wrap
                    )
                    if image:
                        deck.set_key_image(key, image)
                        buttons_updated += 1
                    else:
                        buttons_failed += 1
                except Exception as e:
                    print(f"  ERROR updating button {key}: {e}")
                    buttons_failed += 1

        print(f"  Result: {buttons_updated} updated, {buttons_failed} failed")

    def _render_button_image(self, deck, label, bg_color=None, active=False, dimmed=False,
                               text_color=None, font_size=None, auto_size=True, wrap=True):
        """Render a button image with label and optional styling."""
        if not HAS_PIL:
            return None

        try:
            # Get the key image format from the deck
            fmt = deck.key_image_format()
            size = (fmt['size'][0], fmt['size'][1])

            # Use custom bg color or default
            color = bg_color if bg_color else '#1a1a2e'
            img = Image.new('RGB', size, color=color)
            draw = ImageDraw.Draw(img)

            if active:
                draw.rectangle([0, 0, size[0]-1, size[1]-1], outline='#00ff00', width=3)

            # Text color: use custom, or dimmed gray for unconfigured, or white
            if text_color:
                fill_color = text_color
            elif dimmed:
                fill_color = '#666666'
            else:
                fill_color = 'white'

            # Font paths to try
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",  # Bold first for better visibility
                "C:/Windows/Fonts/arial.ttf",
                "arial.ttf",
                "Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]

            # Calculate font size
            if font_size:
                target_size = font_size
            elif dimmed:
                # Default numbers: 45% of button height (centered)
                target_size = int(size[1] * 0.45)
            else:
                # Configured buttons: start with reasonable size
                target_size = int(size[1] * 0.3)

            # Auto-size: shrink font to fit if needed
            if auto_size and label:
                font = None
                max_width = size[0] - 8  # Padding
                max_height = size[1] - 8

                while target_size > 8:
                    for font_path in font_paths:
                        try:
                            font = ImageFont.truetype(font_path, target_size)
                            break
                        except:
                            continue
                    if font is None:
                        font = ImageFont.load_default()
                        break

                    # Check if text fits (handle wrapping)
                    if wrap and len(label) > 6:
                        lines = self._wrap_text(label, font, max_width, draw)
                    else:
                        lines = [label]

                    # Calculate total height
                    total_height = 0
                    max_line_width = 0
                    for line in lines:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                        line_height = bbox[3] - bbox[1]
                        total_height += line_height
                        max_line_width = max(max_line_width, line_width)

                    if max_line_width <= max_width and total_height <= max_height:
                        break
                    target_size -= 2
            else:
                # No auto-size, just load font
                font = None
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, target_size)
                        break
                    except:
                        continue
                if font is None:
                    font = ImageFont.load_default()
                lines = [label] if label else ['']

            # Wrap text if needed
            if wrap and len(label) > 6:
                lines = self._wrap_text(label, font, size[0] - 8, draw)
            else:
                lines = [label]

            # Draw text centered
            center_x = size[0] // 2
            center_y = size[1] // 2

            if len(lines) == 1:
                # Single line: use anchor for true center
                draw.text((center_x, center_y), lines[0], font=font, fill=fill_color, anchor='mm')
            else:
                # Multiple lines: calculate total height and position
                line_heights = []
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_heights.append(bbox[3] - bbox[1])
                total_height = sum(line_heights)

                y = center_y - total_height // 2
                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    x = (size[0] - line_width) // 2
                    draw.text((x, y), line, font=font, fill=fill_color)
                    y += line_heights[i]

            # PILHelper.to_native_format handles rotation/flip/format conversion
            return PILHelper.to_native_format(deck, img)
        except Exception as e:
            print(f"    RENDER ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _wrap_text(self, text, font, max_width, draw):
        """Wrap text to fit within max_width."""
        words = text.split()
        if not words:
            return ['']

        lines = []
        current_line = words[0]

        for word in words[1:]:
            test_line = current_line + ' ' + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word

        lines.append(current_line)
        return lines

    def check_td_connection(self):
        """Check if TouchDesigner is reachable."""
        try:
            resp = requests.get(f'{self.core_api}/ping', timeout=2)
            return resp.status_code == 200
        except:
            return False

    def report_devices_to_td(self):
        """Report connected devices to TouchDesigner so UI can show them."""
        try:
            devices_list = []
            for serial, device_info in self.devices.items():
                devices_list.append({
                    'serial': serial,
                    'model': device_info['model'],
                    'key_count': device_info['key_count'],
                    'has_dials': device_info['has_dials'],
                    'has_touchscreen': device_info['has_touchscreen']
                })

            resp = self._api_post(f'{self.ui_api}/streamdeck/devices/report', {
                'devices': devices_list
            }, timeout=3)

            if resp and resp.get('success'):
                print(f"Reported {len(devices_list)} device(s) to TouchDesigner")
                return True
            return False
        except Exception as e:
            print(f"Failed to report devices: {e}")
            return False

    def run(self):
        """Main service loop."""
        print("\n" + "=" * 50)
        print("Stream Deck Service for TouchDesigner")
        print("=" * 50)
        print(f"TouchDesigner Core API: {self.core_api}")
        print(f"TouchDesigner UI API:   {self.ui_api}")
        print(f"Config poll interval:   {self.poll_interval}s")
        print("=" * 50 + "\n")

        # Check TD connection
        print("Checking TouchDesigner connection...")
        if self.check_td_connection():
            print("  TouchDesigner is running")
        else:
            print("  WARNING: TouchDesigner not reachable")
            print("  Make sure TD is running with mcp_bridge")

        # Discover devices
        print("\nDiscovering Stream Deck devices...")
        device_count = self.discover_devices()

        if device_count == 0:
            print("\nNo Stream Deck devices found!")
            print("Make sure:")
            print("  - Device is connected via USB")
            print("  - Elgato software is NOT running (conflicts with direct HID)")
            print("  - On Windows: hidapi.dll is in the same folder as the exe")
            print("  - On Linux: udev rules are configured")
            pause_on_exit()
            return

        print(f"\nService running with {device_count} device(s)")
        print("Press Ctrl+C to stop\n")

        # Report devices to TD so UI can show them
        self.report_devices_to_td()

        # Initial config poll and button image update
        print("Fetching initial config...")
        self.poll_config()
        print("Setting initial button images...")
        self.update_button_images()
        print("Initial setup complete.\n")

        self.running = True
        last_poll = time.time()
        last_image_update = time.time()
        last_device_report = time.time()

        try:
            while self.running:
                now = time.time()

                # Poll config periodically
                if now - last_poll >= self.poll_interval:
                    # Try pages first (new system), fall back to config (old system)
                    config_changed = self.poll_active_pages()
                    if not config_changed:
                        config_changed = self.poll_config()
                    if config_changed:
                        self.update_button_images()
                    last_poll = now

                # Update button images less frequently as backup
                if now - last_image_update >= 10.0:
                    self.update_button_images()
                    last_image_update = now

                # Re-report devices every 30 seconds (in case TD restarted)
                if now - last_device_report >= 30.0:
                    self.report_devices_to_td()
                    last_device_report = now

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nShutting down...")

        finally:
            self.running = False
            # Clean up devices
            for serial, device_info in self.devices.items():
                try:
                    deck = device_info['deck']
                    deck.reset()
                    deck.close()
                except:
                    pass
            print("Stream Deck service stopped")


def get_app_dir():
    """Get the directory where the app/script is located."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def load_config():
    """Load configuration from config.json if it exists."""
    config_path = get_app_dir() / 'config.json'
    defaults = {
        'td_host': '127.0.0.1',
        'core_port': 9980,
        'ui_port': 9981,
        'poll_interval': 2.0
    }

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            print(f"Loaded config from: {config_path}")
            # Merge file config with defaults (file config takes precedence)
            for key in defaults:
                if key in file_config:
                    defaults[key] = file_config[key]
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")
            print("Using default settings")

    return defaults


def main():
    # Load config file first
    config = load_config()

    parser = argparse.ArgumentParser(
        description='Stream Deck Service for TouchDesigner MCP Bridge'
    )
    parser.add_argument(
        '--host', default=None,
        help=f'TouchDesigner host address (default: {config["td_host"]})'
    )
    parser.add_argument(
        '--core-port', type=int, default=None,
        help=f'Core API port (default: {config["core_port"]})'
    )
    parser.add_argument(
        '--ui-port', type=int, default=None,
        help=f'UI API port (default: {config["ui_port"]})'
    )
    parser.add_argument(
        '--poll', type=float, default=None,
        help=f'Config poll interval in seconds (default: {config["poll_interval"]})'
    )
    parser.add_argument(
        '--config', default=None,
        help='Path to config.json (default: look in app directory)'
    )

    args = parser.parse_args()

    # CLI args override config file (only if explicitly provided)
    td_host = args.host if args.host is not None else config['td_host']
    core_port = args.core_port if args.core_port is not None else config['core_port']
    ui_port = args.ui_port if args.ui_port is not None else config['ui_port']
    poll_interval = args.poll if args.poll is not None else config['poll_interval']

    service = StreamDeckService(
        td_host=td_host,
        core_port=core_port,
        ui_port=ui_port,
        poll_interval=poll_interval
    )
    service.run()
    pause_on_exit()


if __name__ == '__main__':
    main()
