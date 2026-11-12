# 📱 Your Company • Wireless Barcode Scanner Wedge Guide
### Using iPhone (iOS) or Android to Auto-Type into Microsoft Excel & Zoho Inventory

This setup turns your smartphone (iPhone or Android) into a **wireless 2D barcode & QR scanner wedge**. Whenever you scan a barcode or QR code on your phone, it automatically sends an HTTP request over Wi-Fi to your computer, which instantly types or pastes the batch numbers, expiry dates, quantities, or SKUs directly into your active window (**Microsoft Excel** or **Zoho Inventory**).

---

## 🚀 1. Quick Start (Running the Server)

1. Open your Terminal on Mac and run:
   ```bash
   python3 "Product Scanner/zoho_scanner_wedge.py"
   # Or launch directly with Open_Scanner_Wedge_Web_App.command
   ```
2. The terminal will display your Mac's local Wi-Fi IP and port:
   ```
   ========================================================================
     YOUR COMPANY • WIRELESS BARCODE SCANNER WEDGE
   ========================================================================
     ⚡ Local Server Running on:  http://10.0.0.25:5000
     ⚡ Scanner Endpoint URL:    http://10.0.0.25:5000/scan
     ⚡ Web Monitoring UI:      http://localhost:5000
   ========================================================================
   ```
3. Open `http://localhost:5000` in your web browser to see the live scanner feed and the on-screen setup QR code.

---

## 🤖 2A. Configuring on Android (Binary Eye)

1. Download & open **Binary Eye** (free & open-source on Google Play Store or F-Droid).
2. Tap the **Settings icon (⚙️)** in the top-right corner.
3. Tap **"Custom search / URL"** or **"Open URL automatically"** / **"Barcode Actions"**:
   * **Target URL**:
     ```
     http://10.0.0.25:5000/scan
     ```
     *(Note: Replace with your Mac's Wi-Fi IP shown on the dashboard or terminal)*
   * **Request Method**: `POST` (or `GET`)
   * **Payload Format**: `JSON` or `Raw text`
     ```json
     {"content": "{SCAN}"}
     ```
   * **Automatic Action**: Set to **"Send automatically on scan"** (so you don't have to tap confirm after each scan).

> 💡 **Shortcut**: You can also point Binary Eye directly at the setup QR code displayed on `http://localhost:5000` to quickly test the connection!

---

## 🍏 2B. Configuring on iOS (iPhone)

You have two simple options on iPhone:

### Method 1: Apple Shortcuts (Recommended — Zero App Install)
Uses the iPhone's pre-installed **Shortcuts** app and native camera:
1. Open the **Shortcuts** app on your iPhone.
2. Tap the **`+`** icon (top right) to create a new shortcut. Name it **"Scanner Wedge"**.
3. Add action: **"Scan QR/Barcode"** (under Documents / Camera).
4. Add action: **"Get Contents of URL"**:
   * **URL**: `http://10.0.0.25:5000/scan` *(replace with your Mac's Wi-Fi IP shown on the dashboard)*
   * Tap the arrow / details dropdown:
     * **Method**: `POST`
     * **Request Body**: `JSON`
     * Add Field: Key = `content`, Value = select **QR/Barcode** variable from step 3.
5. Tap the Share icon ➔ **"Add to Home Screen"**.
> 💡 **Continuous Rapid Scanning**: Wrap actions 3 & 4 inside a **"Repeat"** block (e.g., Repeat 20 times) to scan multiple products consecutively without tapping every time!

---

### Method 2: Dedicated iOS App (Continuous Auto-Scan)

#### Option A: **QRbot** (Free on App Store)
1. Install **QRbot - QR & Barcode Reader** from the iOS App Store.
2. Go to **Settings (⚙️)** ➔ **Custom Search / Action URL**.
3. Set the custom URL:
   ```text
   http://10.0.0.25:5000/scan?content={CODE}
   ```
4. Turn on **"Open URL automatically"** (or continuous scan mode).
5. Any scan will instantly fire to your computer without requiring confirmation.

#### Option B: **Quick Scan** (Free & Open Source on App Store)
1. Install **Quick Scan - QR Code Reader** (by Daniel Gauthier) from the App Store.
2. Go to **Settings** ➔ **Actions & Webhooks**.
3. Add Webhook:
   * **URL**: `http://10.0.0.25:5000/scan`
   * **Method**: `POST` (JSON body `{"content": "{value}"}`)
4. Enable **"Auto-trigger action on scan"**.

---

## 📊 3. Testing with Microsoft Excel (Step-by-Step)

1. Open **Microsoft Excel** (or Google Sheets / Apple Numbers) and create a new blank worksheet with columns:
   * **Column A**: Batch Number
   * **Column B**: Manufactured Date
   * **Column C**: Expiry Date
   * **Column D**: Quantity
2. Click inside cell **A2** (the first row to receive data).
3. Scan a Tab-delimited QR code generated from [Zoho_Batch_QR_Generator.html](Zoho_Batch_QR_Generator.html) (or the **Batch QR Generator** button in the web app) using Binary Eye:
   * *Example payload*: `BN-202608-0001\t2026-07-22\t2028-08-20\t10`
4. **Watch Excel auto-fill**:
   * Cell **A2** gets `BN-202608-0001`
   * Cell **B2** gets `2026-07-22`
   * Cell **C2** gets `2028-08-20`
   * Cell **D2** gets `10`
   * The cursor automatically presses `Return / Enter` to drop to cell **A3** for your next scan!

---

## ⚡ 4. Using in Zoho Inventory (Purchases & Batch Entry)

When entering incoming shipments, vendor bills, or physical count sheets in Zoho Inventory:
1. In Zoho Inventory, open your **Bill / Purchase Receive / Add Batch Details** popup.
2. Click inside the **Batch Number** input box.
3. Aim Binary Eye at the product label sticker or screen.
4. Binary Eye sends the scan, and the server automatically fills **Batch # ➔ Mfg Date ➔ Expiry Date ➔ Quantity** across the row simultaneously without manual typing!

---

## ⚙️ 5. Customizing Injection Modes

On the web dashboard (`http://localhost:5000`), you can adjust the injection behavior:

| Mode | Best For | Description |
| :--- | :--- | :--- |
| **Smart Tab Typing (Default)** | **Zoho Modal & Excel** | Types each field, presses the `Tab` key (48) to jump to the next input cell, and presses `Return` (36) at the end. |
| **Fast Clipboard Paste** | **Large Excel Sheets** | Copies the tab-separated string to the macOS clipboard and triggers `Cmd+V` (instantly splits across columns A, B, C, D). |
| **Raw Keystrokes** | **Single SKUs / Barcodes** | Types the scanned string as-is without splitting. |

---

## 🛠️ 6. Troubleshooting & Wi-Fi Tips

* **Phone can't connect?**
  * Ensure your Android phone and Mac are connected to the **same Wi-Fi network**.
  * Check your Mac's firewall in *System Settings ➔ Network ➔ Firewall* to make sure Python is allowed to accept incoming local connections.
* **Typing too fast or missing fields?**
  * You can adjust the keystroke delay on the web dashboard or inside `zoho_scanner_wedge.py` (`CONFIG["keystroke_delay"] = 0.05`).
