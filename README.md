# Wireless Barcode Scanner Wedge

Use your phone as a barcode scanner for your computer. Scan a barcode with the phone, and the result is typed into whatever is open on the computer: an Excel sheet, a Zoho Inventory form or any other app.

It reads the barcodes found on medical and pharmaceutical stock (GS1 and HIBC), and splits them into batch number, manufactured date, expiry date and quantity. Receiving a delivery into a spreadsheet becomes one scan per line instead of four typed fields.

It also includes a **Batch QR Generator**: upload a purchase order, give each line a batch number and expiry date, and print QR labels that scan straight back in.

## How it works

```
 Phone scanner app  ──Wi-Fi──▶  Scanner server  ──keystrokes──▶  Active window
 (Binary Eye, etc.)   HTTP      (this computer)                  (Excel, Zoho…)
```

1. The scanner app on the phone sends each scan to the server over your local network.
2. The server reads the barcode and works out its fields.
3. It pastes or types the result into the window that's active on the computer.

Nothing leaves your network, and there is no account or cloud service.

## Requirements

- A Mac or Windows computer with **Python 3** and **Flask** (`pip install flask`)
- A phone with a scanner app that can send scans to a web address, such as [Binary Eye](https://github.com/markusfisch/BinaryEye) on Android
- The phone and computer on the same Wi-Fi network

## Quick start

1. **Start the server.**
   - Mac: double-click `Open_Scanner_Wedge_Web_App.command`.
   - Windows: double-click `Windows_Version/Scanner_Wedge.bat`.

   The server opens its dashboard at `http://localhost:5000`.
2. **Connect the phone.** On the dashboard, scan the setup QR code with the phone, or enter the address it shows (for example `http://192.168.1.20:5000/scan`) in your scanner app's "send to URL" setting.
3. **Allow typing on a Mac.** In **System Settings → Privacy & Security → Accessibility**, allow Terminal. macOS blocks the typing otherwise.
4. **Scan.** Click into the cell or field you want filled, then scan with the phone.

The full phone and Excel setup is in [BINARY_EYE_SCANNER_GUIDE.md](BINARY_EYE_SCANNER_GUIDE.md), and the Windows setup in [Windows_Version/WINDOWS_SETUP_GUIDE.md](Windows_Version/WINDOWS_SETUP_GUIDE.md).

## Choosing how scans are typed

Pick a typing mode on the dashboard:

| Mode on the dashboard | Use it for |
|---|---|
| **Fast Clipboard Paste** | Excel. One paste fills batch, dates and quantity across four columns. |
| **Smart Tab Typing** | Forms such as Zoho Inventory, moving to the next field after each value. |
| **Raw Keystroke Typing** | Apps that block pasting. |

The server starts in **Fast Clipboard Paste**, and goes back to it when restarted.

## Batch QR Generator

Open it with the **Batch QR Generator** button on the dashboard, or open `Zoho_Batch_QR_Generator.html` in a browser. It works offline.

- Upload a purchase order CSV to give every line a batch number, manufactured date and expiry date.
- Print a QR label for each batch. Scanned back in, a label fills batch, dates and quantity in one go.
- Its product catalogue starts empty. Upload a CSV of your products to fill it.

"Your Company" in the labels and headings is a placeholder for your own name.

## For developers

Other apps and scripts can send scans, change settings and read the scan history over HTTP. See the [API guide](API.md).

## Security

The server has no password. While it runs, any device on the same network can send it text, and it will type that text into the computer. Use it only on a network you trust, such as your office Wi-Fi, and stop it when you aren't scanning. More in [API.md](API.md#security).

## What's in this repo

| Path | What it is |
|---|---|
| `zoho_scanner_wedge.py` | The scanner server, for Mac and Windows |
| `Open_Scanner_Wedge_Web_App.command` | Mac launcher |
| `Zoho_Batch_QR_Generator.html` | Batch QR Generator |
| `API.md` | HTTP API guide |
| `BINARY_EYE_SCANNER_GUIDE.md` | Phone and Excel setup |
| `Windows_Version/` | Windows package: launchers, setup guide and copies of the server and generator |
