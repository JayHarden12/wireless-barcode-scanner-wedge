# Scanner Server API

The scanner server is a small HTTP server that runs on the computer you want scans to appear on. A phone, or any device on the same network, sends it the text of a barcode. The server reads the barcode, then types or pastes the result into whichever window is active on that computer.

This guide covers every endpoint. To install and start the server, see the [README](README.md).

## Contents

- [Basics](#basics)
- [Send a scan](#send-a-scan): `GET|POST /scan`
- [How barcodes are read](#how-barcodes-are-read)
- [Send a test scan](#send-a-test-scan): `POST /api/test`
- [Get recent scans and settings](#get-recent-scans-and-settings): `GET /api/history`
- [Change how scans are typed](#change-how-scans-are-typed): `POST /api/config`
- [Stop the server](#stop-the-server): `POST /api/shutdown`
- [Pages](#pages): `GET /`, `GET /qr-generator`
- [Errors](#errors)
- [Security](#security)

## Basics

| | |
|---|---|
| **Base URL** | `http://<computer-ip>:5000`. The server prints its address when it starts, and shows it at `http://localhost:5000`. |
| **Port** | `5000`, set by `PORT` in `zoho_scanner_wedge.py`. |
| **Authentication** | None. See [Security](#security). |
| **Request bodies** | JSON, form data or plain text, depending on the endpoint. |
| **Responses** | JSON, except the two [pages](#pages). |
| **State** | Settings and scan history are kept in memory. Restarting the server clears the history and restores the default settings. |

## Send a scan

```
GET  /scan
POST /scan
```

Types or pastes a barcode into the active window on the computer. This is the endpoint a scanner app calls after each scan.

### Request

Send the barcode text in any one of these places. The server checks them in this order and uses the first one it finds.

| Where | Names it looks for, in order |
|---|---|
| JSON body | `content`, `barcode`, `data`, `text`, `scan`, `value`, `raw`, `code`, `qrcode` |
| Form data | `content`, `barcode`, `data`, `text`, `scan`, `value`, `raw` |
| Query string | `content`, `barcode`, `data`, `text`, `scan`, `value`, `q`, `code` |
| Plain body | The whole body, as UTF-8 text |

A JSON body that contains none of the listed names is sent on as the JSON text itself.

### Response

`200 OK`

```json
{
  "status": "success",
  "message": "Barcode parsed and injected successfully",
  "raw": "(01)04064035111908(11)241205(17)261205(10)LOT7731(30)10",
  "parsed": "LOT7731\t2024-12-05\t2026-12-05\t10",
  "fields": ["LOT7731", "2024-12-05", "2026-12-05", "10"],
  "fields_count": 4
}
```

| Field | Meaning |
|---|---|
| `raw` | The text received. |
| `parsed` | The text that is typed. See [How barcodes are read](#how-barcodes-are-read). |
| `fields` | `parsed` split at each tab. One item when there is no tab. |
| `fields_count` | The number of items in `fields`. |

The server replies before it types, so a `200` means the scan was received, not that typing succeeded. If nothing appears on the computer, see [Errors](#errors).

**Empty scan:** a request with no barcode text types nothing and returns a connection check instead. Scanner apps use this to test the address.

```json
{ "status": "success", "message": "Connection test successful! Wedge server is active and ready." }
```

### Examples

```bash
# Query string
curl "http://192.168.1.20:5000/scan?code=SKU-001"

# JSON
curl -X POST http://192.168.1.20:5000/scan \
  -H "Content-Type: application/json" \
  -d '{"content": "(01)04064035111908(17)261205(10)LOT7731"}'

# Plain text
curl -X POST http://192.168.1.20:5000/scan \
  -H "Content-Type: text/plain" \
  --data "+H123456/N77047/14D20300228"
```

## How barcodes are read

Medical and supply-chain barcodes pack several values into one code. The server unpacks the common formats into four tab-separated fields:

```
batch <tab> manufactured date <tab> expiry date <tab> quantity
```

Pasted into Excel, the four fields land in four columns. In a form, `tab_typing` mode moves through four fields.

| Barcode | Example | Typed as |
|---|---|---|
| GS1 with brackets | `(01)04064035111908(11)241205(17)261205(10)LOT7731(30)10` | `LOT7731` `2024-12-05` `2026-12-05` `10` |
| GS1 without brackets | `0104064035111908112412051726120510LOT7731` | `LOT7731` `2024-12-05` `2026-12-05` `1` |
| HIBC | `+H123456/N77047/14D20300228` | `N77047` ` ` `2030-02-28` `1` |
| Batch and date | `LOT55/2030-02-28` | `LOT55` ` ` `2030-02-28` `1` |
| Already tab-separated | `BN-0001⇥2026-07-22⇥2028-08-20⇥10` | Unchanged |
| Anything else | `SKU-001` | `SKU-001` |

**Rules:**
- **Dates** are written as `YYYY-MM-DD`. Two-digit years are read as 20xx.
- **Quantity** is `1` when the barcode doesn't include one.
- **Product codes** (GS1 `01`) and serial numbers (`21`) are read past, not typed.
- **Scanner prefixes** such as `]d2` or `]Q3` are removed.
- **Spreadsheet protection:** numbers of 11 or more digits, and text starting with `=` or `-`, get a leading `'`. This stops Excel turning them into rounded numbers or formulas.

## Send a test scan

```
POST /api/test
```

Waits a few seconds, then types a sample scan. Use it to check that typing works: call it, then click into the window you want to fill before the wait ends.

### Request

JSON body. Both fields are optional.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `text` | string | `BN-202608-0001⇥2026-07-22⇥2028-08-20⇥10` | What to type, as is. |
| `delay` | number | `3` | Seconds to wait before typing. |

### Response

`200 OK`

```json
{
  "status": "success",
  "message": "Test scan scheduled in 3.0 seconds. Switch to Excel or Zoho now!",
  "payload": "BN-202608-0001\t2026-07-22\t2028-08-20\t10"
}
```

Test scans aren't added to the history.

## Get recent scans and settings

```
GET /api/history
```

Returns the last 100 scans, newest first, with the current settings and the server's address.

### Response

`200 OK`

```json
{
  "history": [
    {
      "id": 3,
      "time": "21:16:30",
      "raw": "+H123456/N77047/14D20300228",
      "parsed": "N77047\t\t2030-02-28\t1",
      "is_tabbed": true,
      "fields": ["N77047", "", "2030-02-28", "1"],
      "ip": "192.168.1.31"
    }
  ],
  "config": { "mode": "clipboard_paste", "press_enter_at_end": true, "keystroke_delay": 0.03, "active_app_focus": false },
  "local_ip": "192.168.1.20",
  "port": 5000
}
```

| Field | Meaning |
|---|---|
| `id` | The scan's number since the server started. |
| `time` | When it arrived, in the computer's local time. |
| `is_tabbed` | Whether `parsed` has more than one field. |
| `ip` | The address of the device that sent it. |

`raw`, `parsed` and `fields` are as in [Send a scan](#send-a-scan).

## Change how scans are typed

```
POST /api/config
```

Changes the typing settings until the server restarts.

### Request

JSON body. Send only the settings you want to change.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `mode` | string | `clipboard_paste` | How text reaches the window. See below. |
| `press_enter_at_end` | boolean | `true` | Press Enter after each scan. In Excel this moves to the next row. |
| `keystroke_delay` | number | `0.03` | Seconds between typed keys, from `0` to `1`. Raise it for apps that drop fast typing. |

| `mode` | What it does | Best for |
|---|---|---|
| `clipboard_paste` | Copies the text and pastes it (Cmd+V or Ctrl+V). Replaces what was on the clipboard. | Excel, where one paste fills a row of columns. |
| `tab_typing` | Types each field and presses Tab between them. | Forms, such as Zoho Inventory. |
| `raw_typing` | Types the text key by key, tabs included. | Apps that block pasting. |

### Response

`200 OK`, with the settings now in use:

```json
{
  "status": "success",
  "config": { "mode": "tab_typing", "press_enter_at_end": false, "keystroke_delay": 0.03, "active_app_focus": false }
}
```

`400 Bad Request` if any value is invalid. Nothing is changed, not even the valid values in the same request, and `config` shows the settings still in use:

```json
{
  "status": "error",
  "message": "Unknown mode 'fast'. Use one of: tab_typing, clipboard_paste, raw_typing.",
  "config": { "mode": "clipboard_paste", "press_enter_at_end": true, "keystroke_delay": 0.03, "active_app_focus": false }
}
```

### Example

```bash
curl -X POST http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "tab_typing", "press_enter_at_end": false}'
```

## Stop the server

```
POST /api/shutdown
```

Stops the server straight away. The response arrives first:

```json
{ "status": "success", "message": "Server stopped successfully." }
```

## Pages

| Request | What it returns |
|---|---|
| `GET /` | The dashboard: the server's address, a setup QR code for the phone, live scan history and settings. |
| `GET /qr-generator` | The Batch QR Generator. Only from the computer running the server, because the generator can hold your product catalogue. Other devices get `403 Forbidden`. |

## Errors

| Status | When |
|---|---|
| `400 Bad Request` | `/api/config` was sent a value it can't use, such as an unknown `mode` or `"keystroke_delay": "fast"`. The response's `message` says which. |
| `403 Forbidden` | `/qr-generator` was requested from another device. |
| `404 Not Found` | The path doesn't exist. |
| `405 Method Not Allowed` | Wrong method, such as `GET /api/config`. |

Typing happens after the response, so typing problems never show up as HTTP errors. When a scan arrives but nothing is typed:

- **The window lost focus.** Text goes to whichever window is active on the computer when the scan arrives.
- **macOS blocked the typing.** In **System Settings → Privacy & Security → Accessibility**, allow the app that runs the server, such as Terminal.
- **Pasting is blocked.** Switch `mode` to `tab_typing` or `raw_typing`.

The server's console window shows a line for every scan it types.

## Security

The server has no password, and it types whatever it receives. Any device on the same network can therefore type into the computer, change the settings or stop the server.

- Run it only on a network you trust, such as your office Wi-Fi, never on public Wi-Fi.
- Stop it when you aren't scanning.
- Keep the active window on the app you're scanning into, not a terminal or browser address bar.
