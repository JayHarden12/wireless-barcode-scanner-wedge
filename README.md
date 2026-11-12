# Wireless Barcode Scanner Wedge

Turns a phone into a wireless barcode and QR scanner for your computer. Scan with the phone, and the code is typed or pasted into whatever window is active on the computer: Microsoft Excel, Zoho Inventory or anything else.

It also includes a **Batch QR Generator** for Zoho Inventory purchases: upload a purchase order CSV, give each line a batch number and expiry date, and print QR labels that scan straight into Zoho.

## What's here

| File | What it does |
|---|---|
| `zoho_scanner_wedge.py` | The scanner server (Mac and Windows). Receives scans over Wi-Fi and types them into the active window. |
| `Open_Scanner_Wedge_Web_App.command` | Mac launcher: double-click to start the server and open its web page. |
| `Zoho_Batch_QR_Generator.html` | Batch QR and label generator. Opens from the server's web page, or directly in a browser. |
| `BINARY_EYE_SCANNER_GUIDE.md` | Setting up the phone (Binary Eye on Android, or iPhone) and Excel. |
| `Windows_Version/` | The same tool packaged for Windows, with its own launchers and setup guide. |

## Quick start

1. Install Python 3 and Flask: `pip install flask`
2. Start the server: double-click `Open_Scanner_Wedge_Web_App.command` (Mac) or `Windows_Version/Scanner_Wedge.bat` (Windows).
3. Open `http://localhost:5000` and follow the on-screen steps to point your phone's scanner app at the computer.

The product catalogue in the QR generator starts empty. Upload a CSV of your products to fill it. "Your Company" in the labels and headings is a placeholder for your own name.

## Use on a trusted network only

The server has no password. While it runs, any device on the same Wi-Fi network can send it text, and it will type that text into whatever window is active on the computer. Run it only on a network you trust, and stop it when you're not scanning.
