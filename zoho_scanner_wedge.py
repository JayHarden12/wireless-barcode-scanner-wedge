#!/usr/bin/env python3
"""
Your Company • Zoho & Excel Wireless Barcode Scanner Wedge
---------------------------------------------------------------
Acts as a local HTTP server to receive scanned barcodes from Binary Eye
(or any mobile barcode scanner app) over Wi-Fi and instantly types or pastes
the barcode/batch data into your active window (Microsoft Excel, Zoho Inventory, etc.).

Usage:
    python3 zoho_scanner_wedge.py
"""

import sys
import os
import time
import socket
import json
import subprocess
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory, abort

# Initialize Flask
app = Flask(__name__)

# Server Configuration & State
CONFIG = {
    "mode": "clipboard_paste",  # "clipboard_paste" (Universal 100% paste), "tab_typing", "raw_typing"
    "press_enter_at_end": True, # Press Return/Enter after scanning (moves to next row in Excel)
    "keystroke_delay": 0.03,    # Small delay between keystrokes for smooth entry
    "active_app_focus": False   # Keep active foreground window
}

SCAN_HISTORY = []
MAX_HISTORY = 100

def get_local_ip():
    """Detect LAN Wi-Fi IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
        if ip and ip != '127.0.0.1':
            return ip
    except Exception:
        pass
    finally:
        s.close()

    # macOS Wi-Fi interface fallback (en0, en1) for offline LAN
    if sys.platform.startswith('darwin'):
        for iface in ['en0', 'en1', 'en2']:
            try:
                res = subprocess.run(['ipconfig', 'getifaddr', iface], capture_output=True, text=True, timeout=1)
                candidate = res.stdout.strip()
                if candidate and '.' in candidate and candidate != '127.0.0.1':
                    return candidate
            except Exception:
                pass

    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if host_ip and not host_ip.startswith('127.'):
            return host_ip
    except Exception:
        pass

    return '127.0.0.1'

LOCAL_IP = get_local_ip()
PORT = 5000


# ==================== CROSS-PLATFORM KEYSTROKE & PASTE INJECTION ENGINE ====================

import ctypes
import ctypes.util

IS_WINDOWS = sys.platform.startswith('win')
IS_MAC = sys.platform.startswith('darwin')

# -------------------- WINDOWS WIN32 ENGINE --------------------
if IS_WINDOWS:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulonglong)
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT)
        ]

    def win32_type_text(text: str, delay: float = 0.003):
        """Type unicode characters using Win32 SendInput."""
        for char in text:
            inp_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0))
            inp_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0))
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
            if delay > 0:
                time.sleep(delay)
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
            if delay > 0:
                time.sleep(delay)

    def win32_press_key(vk_code: int):
        """Press a virtual key code (0x09 = Tab, 0x0D = Enter)."""
        inp_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=0, time=0, dwExtraInfo=0))
        inp_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0))
        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        time.sleep(0.005)
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
        time.sleep(0.005)

    def win32_clipboard_paste(text: str):
        """Copy text to Windows clipboard and simulate Ctrl+V."""
        try:
            p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
            p.communicate(input=text.encode('utf-16le'))
            time.sleep(0.04)
        except Exception:
            pass

        # Send Ctrl+V (0x11 = VK_CONTROL, 0x56 = 'V')
        inp_ctrl_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0x11, wScan=0, dwFlags=0, time=0, dwExtraInfo=0))
        inp_v_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0x56, wScan=0, dwFlags=0, time=0, dwExtraInfo=0))
        inp_v_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0x56, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0))
        inp_ctrl_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0x11, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0))

        user32.SendInput(1, ctypes.byref(inp_ctrl_down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(inp_v_down), ctypes.sizeof(INPUT))
        time.sleep(0.01)
        user32.SendInput(1, ctypes.byref(inp_v_up), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(inp_ctrl_up), ctypes.sizeof(INPUT))

    def system_type_text(text: str, delay: float = 0.003):
        win32_type_text(text, delay)

    def system_press_tab():
        win32_press_key(0x09) # VK_TAB

    def system_press_return():
        win32_press_key(0x0D) # VK_RETURN

    def system_clipboard_paste(text: str):
        win32_clipboard_paste(text)

# -------------------- MACOS COREGRAPHICS ENGINE --------------------
elif IS_MAC:
    try:
        _app_services = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        _core_foundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library('CoreFoundation'))

        _CGEventSourceCreate = _app_services.CGEventSourceCreate
        _CGEventSourceCreate.restype = ctypes.c_void_p
        _CGEventSourceCreate.argtypes = [ctypes.c_int32]

        _CGEventCreateKeyboardEvent = _app_services.CGEventCreateKeyboardEvent
        _CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
        _CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]

        _CGEventKeyboardSetUnicodeString = _app_services.CGEventKeyboardSetUnicodeString
        _CGEventKeyboardSetUnicodeString.restype = None
        _CGEventKeyboardSetUnicodeString.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p]

        _CGEventSetFlags = _app_services.CGEventSetFlags
        _CGEventSetFlags.restype = None
        _CGEventSetFlags.argtypes = [ctypes.c_void_p, ctypes.c_uint64]

        _CGEventPost = _app_services.CGEventPost
        _CGEventPost.restype = None
        _CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

        _CFRelease = _core_foundation.CFRelease
        _CFRelease.restype = None
        _CFRelease.argtypes = [ctypes.c_void_p]

        HAS_QUARTZ = True
    except Exception as e:
        print(f"[Quartz Init Warning]: {e}", file=sys.stderr)
        HAS_QUARTZ = False

    kCGEventFlagMaskCommand = 0x00100000

    def macos_type_text(text: str, delay: float = 0.005):
        if HAS_QUARTZ:
            try:
                src = _CGEventSourceCreate(0)
                for char in text:
                    down = _CGEventCreateKeyboardEvent(src, 0, True)
                    up = _CGEventCreateKeyboardEvent(src, 0, False)
                    _CGEventKeyboardSetUnicodeString(down, len(char), char)
                    _CGEventKeyboardSetUnicodeString(up, len(char), char)
                    _CGEventPost(0, down)
                    if delay > 0:
                        time.sleep(delay)
                    _CGEventPost(0, up)
                    if delay > 0:
                        time.sleep(delay)
                    _CFRelease(down)
                    _CFRelease(up)
                _CFRelease(src)
                return
            except Exception as e:
                print(f"[Native Type Error]: {e}", file=sys.stderr)

        safe_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
        subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{safe_text}"'], capture_output=True)

    def macos_press_key(key_code: int):
        if HAS_QUARTZ:
            try:
                src = _CGEventSourceCreate(0)
                down = _CGEventCreateKeyboardEvent(src, key_code, True)
                up = _CGEventCreateKeyboardEvent(src, key_code, False)
                _CGEventPost(0, down)
                time.sleep(0.008)
                _CGEventPost(0, up)
                time.sleep(0.008)
                _CFRelease(down)
                _CFRelease(up)
                _CFRelease(src)
                return
            except Exception as e:
                print(f"[Native Key Error]: {e}", file=sys.stderr)

        subprocess.run(["osascript", "-e", f'tell application "System Events" to key code {key_code}'], capture_output=True)

    def macos_clipboard_paste(text: str):
        try:
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, close_fds=True)
            p.communicate(input=text.encode('utf-8'))
            time.sleep(0.04)

            if HAS_QUARTZ:
                try:
                    src = _CGEventSourceCreate(0)
                    down = _CGEventCreateKeyboardEvent(src, 9, True)  # 9 = 'v'
                    _CGEventSetFlags(down, kCGEventFlagMaskCommand)
                    up = _CGEventCreateKeyboardEvent(src, 9, False)
                    _CGEventPost(0, down)
                    time.sleep(0.01)
                    _CGEventPost(0, up)
                    time.sleep(0.01)
                    _CFRelease(down)
                    _CFRelease(up)
                    _CFRelease(src)
                    return
                except Exception as e:
                    print(f"[Quartz Paste Error]: {e}", file=sys.stderr)

            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'], capture_output=True)
        except Exception as e:
            print(f"[Clipboard Error]: {e}", file=sys.stderr)

    def system_type_text(text: str, delay: float = 0.005):
        macos_type_text(text, delay)

    def system_press_tab():
        macos_press_key(48) # 48 = Tab

    def system_press_return():
        macos_press_key(36) # 36 = Return

    def system_clipboard_paste(text: str):
        macos_clipboard_paste(text)

# -------------------- LINUX / FALLBACK ENGINE --------------------
else:
    def system_type_text(text: str, delay: float = 0.005):
        print(f"[Fallback Print]: {text}")

    def system_press_tab():
        pass

    def system_press_return():
        pass

    def system_clipboard_paste(text: str):
        print(f"[Fallback Paste]: {text}")

def parse_smart_barcode(raw_text: str) -> str:
    """
    Intelligently parses and sanitizes raw barcodes with special characters, HIBC, and GS1 Application Identifiers:
    - Strips AIM Symbology prefixes (]d2, ]Q3, ]C1, ]e0, etc.)
    - Handles HIBC & ANSI MH10.8.2 Medical formats (/14D Expiry, /16D Mfg, /$$ Lot)
      e.g. N77047/14D20300228 -> Batch: N77047, Expiry: 2030-02-28
      e.g. +H123456/N77047/14D20300228
      e.g. +H999/$$3260820LOT1234 -> Batch: LOT1234, Expiry: 2026-08-20
    - Handles GS1-128 with AI brackets: (01)...(11)...(17)...(10)...
    - Handles raw sequential GS1 AI digits: 01[GTIN] 11[Mfg] 17[Exp] 10[Batch]
    - Handles generic slash dates: BATCH123/2030-02-28 or BATCH123/20300228
    - Converts invisible ASCII control chars (\x1d, <GS>) into delimiters
    - Protects Excel against formula injection (=, +, -)
    """
    import re
    text = raw_text.strip().rstrip(',')
    if not text:
        return ""

    # 1. Already Tab-delimited
    if '\t' in text:
        return text

    # 2. Strip AIM Symbology Identifiers (e.g. ]d2 = DataMatrix GS1, ]Q3 = QR GS1, ]C1 = Code 128)
    text = re.sub(r'^\][a-zA-Z0-9]{2}', '', text)

    # 3. Clean non-printable ASCII control characters (ASCII 29 GS separator, etc.)
    text = text.replace('\x1d', '|').replace('\x1e', '|').replace('<GS>', '|')

    # 4. Check HIBC / ANSI MH10.8.2 Data Identifiers (/14D Expiry, /16D Mfg, /$$)
    if '14D' in text or '16D' in text or '$$' in text or (text.startswith('+') and '/' in text):
        exp_date = ""
        mfg_date = ""
        batch_no = ""
        qty_val = "1"

        # Extract 14D (Expiration Date: YYYYMMDD or YYMMDD)
        m_14d = re.search(r'(?:/|\+|^)14D([0-9]{8}|[0-9]{6})', text)
        if m_14d:
            d_str = m_14d.group(1)
            if len(d_str) == 8:
                exp_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
            elif len(d_str) == 6:
                exp_date = f"20{d_str[:2]}-{d_str[2:4]}-{d_str[4:6]}"

        # Extract 16D (Manufacturing Date: YYYYMMDD or YYMMDD)
        m_16d = re.search(r'(?:/|\+|^)16D([0-9]{8}|[0-9]{6})', text)
        if m_16d:
            d_str = m_16d.group(1)
            if len(d_str) == 8:
                mfg_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
            elif len(d_str) == 6:
                mfg_date = f"20{d_str[:2]}-{d_str[2:4]}-{d_str[4:6]}"

        # Extract standard HIBC $$ (e.g. +H123/$$3260820LOT1234)
        if '$$' in text:
            parts = re.split(r'/\$\$|\+\$\$|\$\$', text.lstrip('+'))
            sec_part = parts[1] if len(parts) > 1 else parts[0]
            if len(sec_part) >= 7 and sec_part[0] in ['3', '4', '5', '0', '1', '2'] and not exp_date:
                y, m, d = sec_part[1:3], sec_part[3:5], sec_part[5:7]
                exp_date = f"20{y}-{m}-{d}"
                batch_candidate = sec_part[7:]
                if batch_candidate and not batch_no:
                    batch_no = batch_candidate

        # Extract Batch / LOT from segments
        if not batch_no:
            clean_parts = [p for p in re.split(r'[/\+]+', text) if p and not p.startswith(('14D', '16D', '$$'))]
            for part in clean_parts:
                if part.startswith('L') and len(part) > 1 and not part.startswith('LOT'):
                    batch_no = part[1:]
                elif part.startswith('LOT'):
                    batch_no = part[3:]
            if not batch_no and clean_parts:
                batch_no = clean_parts[-1]

        if batch_no or exp_date or mfg_date:
            return f"{batch_no}\t{mfg_date}\t{exp_date}\t{qty_val}"

    # 5. Check GS1-128 with Bracketed Application Identifiers: (01)...(11)...(17)...(10)...
    if '(' in text and ')' in text:
        m_gtin = re.search(r'\(01\)([0-9a-zA-Z]{8,14})', text)
        m_mfg = re.search(r'\(11\)([0-9]{6})', text)
        m_exp = re.search(r'\(17\)([0-9]{6})', text)
        m_batch = re.search(r'\(10\)([0-9a-zA-Z\-_]+)', text)
        m_qty = re.search(r'\((?:30|37)\)([0-9]+)', text)

        mfg_date = f"20{m_mfg.group(1)[:2]}-{m_mfg.group(1)[2:4]}-{m_mfg.group(1)[4:6]}" if m_mfg else ""
        exp_date = f"20{m_exp.group(1)[:2]}-{m_exp.group(1)[2:4]}-{m_exp.group(1)[4:6]}" if m_exp else ""
        batch_no = m_batch.group(1) if m_batch else ""
        qty_val = m_qty.group(1) if m_qty else "1"
        if batch_no or exp_date or mfg_date:
            return f"{batch_no}\t{mfg_date}\t{exp_date}\t{qty_val}"

    # 6. Check Raw Sequential GS1 AI Digits (e.g. 010406403511190811241205172612051011712602)
    if text.startswith('01') and len(text) >= 16:
        mfg_date = ""
        exp_date = ""
        batch_no = ""
        qty_val = "1"
        pos = 16

        while pos < len(text):
            if text[pos] == '|':
                pos += 1
                continue
            ai = text[pos:pos+2]

            if ai == '11' and pos + 8 <= len(text):  # Mfg Date: YYMMDD
                y, m, d = text[pos+2:pos+4], text[pos+4:pos+6], text[pos+6:pos+8]
                mfg_date = f"20{y}-{m}-{d}"
                pos += 8
            elif ai == '17' and pos + 8 <= len(text):  # Exp Date: YYMMDD
                y, m, d = text[pos+2:pos+4], text[pos+4:pos+6], text[pos+6:pos+8]
                exp_date = f"20{y}-{m}-{d}"
                pos += 8
            elif ai == '10':  # Batch / LOT
                pos += 2
                rest = text[pos:]
                if '|' in rest:
                    batch_no = rest.split('|')[0]
                    pos += len(batch_no)
                else:
                    batch_no = rest
                    pos = len(text)
            elif ai == '21':  # Serial
                pos += 2
                rest = text[pos:]
                if '|' in rest:
                    pos += len(rest.split('|')[0])
                else:
                    pos = len(text)
            elif ai in ['30', '37']:  # Quantity
                pos += 2
                m_q = re.match(r'^[0-9]+', text[pos:])
                if m_q:
                    qty_val = m_q.group(0)
                    pos += len(qty_val)
                else:
                    pos += 1
            else:
                if not batch_no and pos + 2 < len(text):
                    batch_no = text[pos:]
                break

        if batch_no or exp_date or mfg_date:
            return f"{batch_no}\t{mfg_date}\t{exp_date}\t{qty_val}"

    # 7. Check generic slash-delimited date patterns e.g. BATCH123/2030-02-28 or BATCH123/20300228
    m_slash_date = re.search(r'([a-zA-Z0-9\-_]+)/(20[2-3][0-9][\-]?[0-1][0-9][\-]?[0-3][0-9])', text)
    if m_slash_date:
        b = m_slash_date.group(1)
        d = m_slash_date.group(2).replace('-', '')
        e_fmt = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        return f"{b}\t\t{e_fmt}\t1"

    # 8. Strip leading noise characters (~, *, #, _)
    cleaned = re.sub(r'^[~*#_]+', '', text)

    # 9. Protect pure numbers > 11 digits or formula-trigger characters from Excel corruption
    if cleaned.isdigit() and len(cleaned) >= 11:
        return f"'{cleaned}"
    if cleaned.startswith(('=', '+', '-')) and not cleaned.startswith('+'):
        return f"'{cleaned}"

    return cleaned

def inject_barcode_into_active_window(raw_text: str):
    """
    Intelligently injects scanned text into the currently active window
    (Excel, Zoho Inventory batch modal, text editor, etc.) on Windows or macOS.
    """
    clean_text = parse_smart_barcode(raw_text.strip('\r\n'))
    mode = CONFIG.get("mode", "clipboard_paste")
    press_enter = CONFIG.get("press_enter_at_end", True)
    delay = CONFIG.get("keystroke_delay", 0.02)

    print(f"\n[INJECT] >>> Received barcode payload: {repr(clean_text)} (Mode: {mode}, Platform: {sys.platform})")

    if mode == "clipboard_paste":
        # Fast Clipboard Paste: Copies tab-delimited text and triggers Cmd+V (macOS) or Ctrl+V (Windows)
        # In Excel, this automatically populates consecutive columns (A, B, C, D)!
        system_clipboard_paste(clean_text)
        if press_enter:
            time.sleep(0.05)
            system_press_return()
            
    elif mode == "tab_typing":
        # Smart Tab Typing: If tabs (\t) are present, types field -> Tab -> field -> Tab ...
        if '\t' in clean_text:
            fields = clean_text.split('\t')
            for i, field in enumerate(fields):
                system_type_text(field, delay)
                time.sleep(delay)
                if i < len(fields) - 1:
                    system_press_tab()
                    time.sleep(delay)
            if press_enter:
                time.sleep(delay)
                system_press_return()
        else:
            # Single value (SKU or Batch No)
            system_type_text(clean_text, delay)
            if press_enter:
                time.sleep(delay)
                system_press_return()
    else:
        # Raw typing
        system_type_text(clean_text, delay)
        if press_enter:
            time.sleep(delay)
            system_press_return()


# ==================== FLASK SERVER ROUTES ====================

@app.route('/scan', methods=['POST', 'GET'])
def handle_scan():
    """
    Receives scanned barcode text from Binary Eye or any webhook / POST / GET request.
    """
    barcode_text = ""

    # 1. Check JSON body
    if request.is_json:
        data = request.get_json(silent=True) or {}
        # Common keys used by barcode scanner apps
        for key in ['content', 'barcode', 'data', 'text', 'scan', 'value', 'raw', 'code', 'qrcode']:
            if key in data and data[key]:
                barcode_text = str(data[key])
                break
        if not barcode_text and data:
            barcode_text = json.dumps(data)

    # 2. Check Form Data
    if not barcode_text and request.form:
        for key in ['content', 'barcode', 'data', 'text', 'scan', 'value', 'raw']:
            if key in request.form:
                barcode_text = request.form[key]
                break

    # 3. Check Query Parameters (GET / POST)
    if not barcode_text and request.args:
        for key in ['content', 'barcode', 'data', 'text', 'scan', 'value', 'q', 'code']:
            if key in request.args:
                barcode_text = request.args[key]
                break

    # 4. Check Raw Data Body
    if not barcode_text and request.data:
        try:
            barcode_text = request.data.decode('utf-8', errors='ignore')
        except Exception:
            pass

    barcode_text = barcode_text.strip()

    if not barcode_text:
        # Binary Eye 'Test URL' probe or empty check
        return jsonify({
            "status": "success",
            "message": "Connection test successful! Wedge server is active and ready."
        }), 200

    # Parse and deconstruct barcode (GS1, HIBC, Tabbed, etc.)
    parsed_payload = parse_smart_barcode(barcode_text)
    is_tabbed = '\t' in parsed_payload
    fields_list = parsed_payload.split('\t') if is_tabbed else [parsed_payload]

    # Log entry
    entry = {
        "id": len(SCAN_HISTORY) + 1,
        "time": datetime.now().strftime("%H:%M:%S"),
        "raw": barcode_text,
        "parsed": parsed_payload,
        "is_tabbed": is_tabbed,
        "fields": fields_list,
        "ip": request.remote_addr
    }
    SCAN_HISTORY.insert(0, entry)
    if len(SCAN_HISTORY) > MAX_HISTORY:
        SCAN_HISTORY.pop()

    # Inject keystrokes in a background thread to return fast HTTP response to phone
    threading.Thread(target=inject_barcode_into_active_window, args=(parsed_payload,), daemon=True).start()

    return jsonify({
        "status": "success",
        "message": "Barcode parsed and injected successfully",
        "raw": barcode_text,
        "parsed": parsed_payload,
        "fields": fields_list,
        "fields_count": len(fields_list)
    }), 200


@app.route('/api/test', methods=['POST'])
def handle_test_scan():
    """Trigger a test barcode scan with custom text and optional countdown delay."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "BN-202608-0001\t2026-07-22\t2028-08-20\t10")
    delay_sec = float(data.get("delay", 3.0))

    def delayed_inject():
        time.sleep(delay_sec)
        inject_barcode_into_active_window(text)

    threading.Thread(target=delayed_inject, daemon=True).start()

    return jsonify({
        "status": "success",
        "message": f"Test scan scheduled in {delay_sec} seconds. Switch to Excel or Zoho now!",
        "payload": text
    })


@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify({
        "history": SCAN_HISTORY,
        "config": CONFIG,
        "local_ip": LOCAL_IP,
        "port": PORT
    })


@app.route('/api/shutdown', methods=['POST'])
def handle_shutdown():
    """Cleanly shut down the Flask server and terminate process."""
    def kill_process():
        time.sleep(0.3)
        os._exit(0)

    threading.Thread(target=kill_process, daemon=True).start()
    return jsonify({"status": "success", "message": "Server stopped successfully."})


MODES = ["tab_typing", "clipboard_paste", "raw_typing"]


def config_error(message):
    return jsonify({"status": "error", "message": message, "config": CONFIG}), 400


@app.route('/api/config', methods=['POST'])
def update_config():
    """Change typing settings. Every value is checked first, so a bad request changes nothing."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return config_error("Send the settings as a JSON object.")

    changes = {}
    if "mode" in data:
        if data["mode"] not in MODES:
            return config_error(f"Unknown mode {data['mode']!r}. Use one of: {', '.join(MODES)}.")
        changes["mode"] = data["mode"]
    if "press_enter_at_end" in data:
        if not isinstance(data["press_enter_at_end"], bool):
            return config_error("press_enter_at_end must be true or false.")
        changes["press_enter_at_end"] = data["press_enter_at_end"]
    if "keystroke_delay" in data:
        delay = data["keystroke_delay"]
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not 0 <= delay <= 1:
            return config_error("keystroke_delay must be a number of seconds from 0 to 1.")
        changes["keystroke_delay"] = float(delay)

    CONFIG.update(changes)
    return jsonify({"status": "success", "config": CONFIG})


QR_GENERATOR_FILE = "Zoho_Batch_QR_Generator.html"


@app.route('/qr-generator', methods=['GET'])
def qr_generator():
    """Open the batch QR generator kept next to this script. This computer only:
    it holds the product catalogue, so other devices on the network can't fetch it."""
    if request.remote_addr not in ('127.0.0.1', '::1'):
        abort(403)
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), QR_GENERATOR_FILE)


@app.route('/', methods=['GET'])
def index():
    """Web Dashboard for monitoring and quick configuration."""
    template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Your Company • Wireless Scanner Wedge Suite</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
:root {
    --bg-main: #090d16;
    --bg-surface: #0f172a;
    --bg-card: #1e293b;
    --border: rgba(255, 255, 255, 0.1);
    --accent-blue: #0284c7;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --font-main: 'Plus Jakarta Sans', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: var(--font-main);
    background-color: var(--bg-main);
    color: var(--text-primary);
    padding: 20px;
    min-height: 100vh;
}
.container { max-width: 1180px; margin: 0 auto; }
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    margin-bottom: 24px;
}
.brand-title { font-size: 20px; font-weight: 800; }
.badge {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-emerald);
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
}
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
@media(max-width: 860px) { .grid-2 { grid-template-columns: 1fr; } }
.card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
}
.card-title { font-size: 16px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.url-box {
    background: var(--bg-card);
    border: 1px dashed var(--accent-cyan);
    padding: 16px;
    border-radius: 10px;
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 700;
    color: var(--accent-cyan);
    text-align: center;
    margin-bottom: 16px;
    word-break: break-all;
}
.qr-wrap { display: flex; justify-content: center; margin: 16px 0; }
.qr-canvas { background: white; padding: 12px; border-radius: 12px; }
.btn {
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
    color: white;
    border: none;
    padding: 12px 18px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 13px;
    cursor: pointer;
    transition: transform 0.15s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
}
.btn:hover { transform: translateY(-1px); }
.btn-secondary {
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-primary);
}
.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.form-control {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: white;
    font-family: var(--font-main);
    font-size: 13px;
}
.table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 12px; }
.table th { text-align: left; padding: 10px; color: var(--text-secondary); border-bottom: 1px solid var(--border); font-size: 11px; }
.table td { padding: 10px; border-bottom: 1px solid var(--border); }
.tag {
    background: rgba(6, 182, 212, 0.15);
    color: var(--accent-cyan);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
}
.countdown-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.85);
    z-index: 1000;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}
.countdown-num { font-size: 80px; font-weight: 800; color: var(--accent-cyan); }
</style>
</head>
<body>

<div class="container">
    <div class="header">
        <div>
            <div class="brand-title">YOUR COMPANY • WIRELESS SCANNER WEDGE</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Receives scans from Binary Eye (Android) & auto-types directly into Excel or Zoho</div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <a href="/qr-generator" target="_blank" class="btn btn-secondary" style="width: auto; padding: 6px 12px; font-size: 11px; text-decoration: none;">
                🏷️ Batch Label Studio
            </a>
            <button onclick="stopServer()" class="btn" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; width: auto; padding: 6px 12px; font-size: 11px;">
                ⏹️ Quit Server
            </button>
            <div class="badge">● SERVER ACTIVE</div>
        </div>
    </div>

    <div class="grid-2">
        <!-- Left: Phone Connection & Setup -->
        <div class="card">
            <div class="card-title">📱 1. Connect Binary Eye (Android Phone)</div>
            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 14px;">
                Make sure your phone is connected to the same Wi-Fi network. Configure Binary Eye with this POST URL:
            </p>
            <div class="url-box" id="server-url-display">http://{{ local_ip }}:{{ port }}/scan</div>

            <div class="qr-wrap">
                <div id="qr-container" class="qr-canvas"></div>
            </div>
            <p style="font-size: 11px; text-align: center; color: var(--text-secondary);">
                Scan this QR code with Binary Eye to open or copy the URL.
            </p>

            <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                <strong>Binary Eye Setup Steps:</strong><br>
                1. Open <strong>Binary Eye</strong> on your Android phone.<br>
                2. Go to <strong>Settings ➔ Custom search / URL</strong>.<br>
                3. Set URL to: <code>http://{{ local_ip }}:{{ port }}/scan</code> (or scan QR code).<br>
                4. Select <strong>HTTP POST</strong> (Payload: <code>{"content": "{SCAN}"}</code>).<br>
                5. Scan any barcode — it will type into Excel / Zoho immediately!
            </div>
        </div>

        <!-- Right: Test Simulator & Wedge Settings -->
        <div class="card">
            <div class="card-title">⚡ 2. Test Keystroke Injection in Excel</div>
            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">
                Test typing directly into your Excel sheet without needing your phone. Click a test button, then switch to Excel within 3 seconds!
            </p>

            <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;">
                <button class="btn" onclick="triggerTestScan('BN-202608-0001\\t2026-07-22\\t2028-08-20\\t10')">
                    ⚡ Test Zoho Batch Row (Batch, Mfg, Exp, Qty)
                </button>
                <button class="btn btn-secondary" onclick="triggerTestScan('SKU-001')">
                    ⚡ Test Single SKU (SKU-001)
                </button>
            </div>

            <div class="card-title" style="font-size: 14px; margin-top: 20px; border-top: 1px solid var(--border); padding-top: 16px;">
                ⚙️ Wedge Typing Mode
            </div>
            <div class="form-group">
                <label class="form-label">Injection Mode</label>
                <select id="config-mode" class="form-control" onchange="saveConfig()">
                    <option value="tab_typing" {{ 'selected' if config.mode == 'tab_typing' }}>Smart Tab Typing (Types text, presses Tab between fields, Enter at end)</option>
                    <option value="clipboard_paste" {{ 'selected' if config.mode == 'clipboard_paste' }}>Fast Clipboard Paste (Copies tabbed string & presses Cmd+V)</option>
                    <option value="raw_typing" {{ 'selected' if config.mode == 'raw_typing' }}>Raw Keystroke Typing (Types string as-is)</option>
                </select>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer;">
                    <input type="checkbox" id="config-enter" {{ 'checked' if config.press_enter_at_end }} onchange="saveConfig()">
                    <span>Press Return/Enter after each scan (moves cursor to next Excel row)</span>
                </label>
            </div>
        </div>
    </div>

    <!-- Live Scanned Log Feed -->
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div class="card-title" style="margin-bottom: 0;">📋 Real-Time Scanned Feed (<span id="history-count">0</span>)</div>
            <button class="btn btn-secondary" onclick="fetchHistory()" style="width: auto; padding: 6px 14px; font-size: 11px;">🔄 Refresh</button>
        </div>

        <div style="overflow-x: auto;">
            <table class="table">
                <thead>
                    <tr>
                        <th style="width: 80px;">Time</th>
                        <th style="width: 140px;">Mode / Type</th>
                        <th>Scanned Barcode / Batch Fields</th>
                        <th style="width: 100px;">From IP</th>
                    </tr>
                </thead>
                <tbody id="history-table-body">
                    <tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">Waiting for scans from Binary Eye...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- 3-Second Switch Countdown Overlay -->
<div id="countdown-modal" class="countdown-overlay">
    <div style="font-size: 22px; font-weight: 700; margin-bottom: 10px;">Switch to Microsoft Excel or Zoho Now!</div>
    <div id="countdown-timer" class="countdown-num">3</div>
    <div style="font-size: 13px; color: var(--text-secondary); margin-top: 10px;">Click inside the target cell / field. Keystrokes will type automatically when counter hits 0.</div>
</div>

<script>
const SERVER_URL = "http://{{ local_ip }}:{{ port }}/scan";

window.addEventListener('DOMContentLoaded', () => {
    // Render QR Code of the endpoint URL
    new QRCode(document.getElementById("qr-container"), {
        text: SERVER_URL,
        width: 140,
        height: 140,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.M
    });

    // Start auto-refreshing history
    fetchHistory();
    setInterval(fetchHistory, 2000);
});

function triggerTestScan(textPayload) {
    const modal = document.getElementById('countdown-modal');
    const timerElem = document.getElementById('countdown-timer');
    modal.style.display = 'flex';
    let count = 3;
    timerElem.innerText = count;

    // Send test request with 3s delay
    fetch('/api/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textPayload, delay: 3.0 })
    });

    const interval = setInterval(() => {
        count--;
        if (count > 0) {
            timerElem.innerText = count;
        } else {
            clearInterval(interval);
            modal.style.display = 'none';
        }
    }, 1000);
}

function saveConfig() {
    const mode = document.getElementById('config-mode').value;
    const enter = document.getElementById('config-enter').checked;
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode, press_enter_at_end: enter })
    });
}

function fetchHistory() {
    fetch('/api/history')
        .then(res => res.json())
        .then(data => {
            document.getElementById('history-count').innerText = data.history.length;
            const tbody = document.getElementById('history-table-body');
            if (data.history.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">Waiting for scans from Binary Eye...</td></tr>';
                return;
            }
            tbody.innerHTML = data.history.map(item => {
                const fieldsHtml = item.fields.map(f => `<span class="tag">${escapeHtml(f)}</span>`).join(' ➔ ');
                return `
                    <tr>
                        <td style="font-family: var(--font-mono); color: var(--text-secondary);">${item.time}</td>
                        <td><span style="font-weight: 700; color: ${item.is_tabbed ? '#10b981' : '#38bdf8'}">${item.is_tabbed ? 'Tabbed Zoho Batch' : 'Single Value'}</span></td>
                        <td>${fieldsHtml}</td>
                        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">${item.ip}</td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => console.log(err));
}

function stopServer() {
    if (confirm("Are you sure you want to stop the Scanner Wedge server?")) {
        fetch('/api/shutdown', { method: 'POST' })
            .then(() => {
                document.body.innerHTML = `
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:85vh; text-align:center; font-family:sans-serif; color:#94a3b8; background:#090d16;">
                        <div style="font-size:56px; margin-bottom:16px;">🛑</div>
                        <h2 style="color:#f8fafc; font-size:24px; margin-bottom:10px;">Scanner Server Stopped</h2>
                        <p style="font-size:14px; max-width:440px; line-height:1.6; color:#94a3b8;">
                            The local wedge server has been terminated. You can safely close this browser window.<br><br>
                            To restart whenever you need to scan, simply double-click <strong style="color:#38bdf8;">Open_Scanner_Wedge_Web_App.command</strong> in your Product Scanner folder.
                        </p>
                    </div>
                `;
            })
            .catch(() => alert('Server stopped.'));
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}
</script>

</body>
</html>
"""
    # The mode list and Enter box show the settings the server is actually using
    return render_template_string(template, local_ip=LOCAL_IP, port=PORT, config=CONFIG)


# ==================== MAIN LAUNCHER ====================

def print_banner():
    print("=" * 72)
    print("  YOUR COMPANY • WIRELESS BARCODE SCANNER WEDGE (BINARY EYE)")
    print("=" * 72)
    print(f"  ⚡ Local Server Running on:  http://{LOCAL_IP}:{PORT}")
    print(f"  ⚡ Scanner Endpoint URL:    http://{LOCAL_IP}:{PORT}/scan")
    print(f"  ⚡ Web Monitoring UI:      http://localhost:{PORT}")
    print("-" * 72)
    print("  HOW TO USE:")
    print(f"  1. In Binary Eye (Android), set target POST URL to:")
    print(f"     http://{LOCAL_IP}:{PORT}/scan")
    print("  2. Open Microsoft Excel or Zoho Inventory and click the target cell/field.")
    print("  3. Scan any barcode/QR on your phone — it will instantly type/paste!")
    print("=" * 72)
    print("  Press Ctrl+C to stop the server.\n")

if __name__ == '__main__':
    print_banner()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
