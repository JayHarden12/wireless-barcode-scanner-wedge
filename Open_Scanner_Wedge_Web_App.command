#!/bin/bash
# ==============================================================================
#  YOUR COMPANY • WIRELESS SCANNER WEDGE LAUNCHER
#  Starts the local server and opens the web app.
#  Closing this terminal window or pressing Ctrl+C will terminate the server.
# ==============================================================================

# Move to the script's directory (works wherever this folder is placed)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Ensure any previous hanging instance is terminated
pkill -f "zoho_scanner_wedge.py" 2>/dev/null || true
sleep 0.5

# Open Web App in default browser after 1.2 second delay
(sleep 1.2 && open "http://localhost:5000") &

# Run Python Scanner Server in foreground (Press Ctrl+C or close window to quit)
python3 "$DIR/zoho_scanner_wedge.py"

# Cleanup when script finishes
pkill -f "zoho_scanner_wedge.py" 2>/dev/null || true

