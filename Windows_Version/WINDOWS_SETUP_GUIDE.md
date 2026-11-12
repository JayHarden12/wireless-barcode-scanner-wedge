# 🖥️ Your Company • Windows Setup Guide
### Wireless Barcode Scanner Wedge & Zoho Batch Automation

This guide explains how to run the **Your Company Wireless Scanner Wedge** on any **Windows PC** (Windows 10, 11, or Windows Server).

---

## 📦 What's Inside the Windows Package (`Windows_Version/` folder)

* **`Scanner_Wedge.bat`**: 1-Click launcher (double-click to start!).
* **`Scanner_Wedge_Silent.vbs`**: Silent background launcher.
* **`zoho_scanner_wedge.py`**: Cross-platform Python server engine (with native Win32 `SendInput` and `Ctrl+V` injection).
* **`Zoho_Batch_QR_Generator.html`**: Offline Batch QR & Label Generator.

---

## ⚡ Quick 3-Step Setup on Windows

### Step 1: Install Python (One-Time Setup)
1. Download Python for Windows from: **https://www.python.org/downloads/**
2. Run the installer and **IMPORTANT**: Make sure to check the box:  
   ☑️ **"Add Python to PATH"** at the bottom of the first setup screen!
3. Click **Install Now**.

---

### Step 2: Launch the Scanner Wedge
1. Open the `Windows_Version` folder on your Windows PC.
2. **Double-click `Scanner_Wedge.bat`**.
   * It will automatically verify Python and install `flask` if needed.
   * It will open your web browser to the dashboard: `http://localhost:5000`.
   * It displays your Windows PC's local Wi-Fi IP (e.g. `http://192.168.1.50:5000/scan`).

---

### Step 3: Configure Binary Eye on Android
1. Open **Binary Eye** on your phone (make sure phone is on the same Wi-Fi as the PC).
2. Go to **Settings ➔ Forward scans** (Toggle **ON**).
3. Set **URL to forward to**:
   ```text
   http://YOUR_WINDOWS_IP:5000/scan
   ```
   *(Or scan the setup QR code displayed on your PC screen!)*
4. Set **Request type**: `POST application/json`.
5. Tap **Test URL** to confirm connection.

---

## 🎯 How to Use in Excel & Zoho Inventory

### In Microsoft Excel for Windows:
1. Open your Excel workbook.
2. Click inside any cell (e.g. `A2`).
3. Aim Binary Eye at any product box, GS1 medical barcode, or printed label.
4. **Result**: It automatically populates:
   $$\mathbf{Batch\ Number}\quad\rightarrow\quad\mathbf{Mfg\ Date}\quad\rightarrow\quad\mathbf{Expiry\ Date}\quad\rightarrow\quad\mathbf{Quantity}$$
   and moves down to the next row!

### In Zoho Inventory:
1. Open **Purchases ➔ Bills ➔ + New Bill** (or **Purchase Receives**).
2. Add an expiring item and click **Add Batch Details**.
3. Click inside the **Batch Number** input box.
4. Scan the product on your phone — it auto-fills all 4 modal fields simultaneously!

---

## ⏹️ How to Quit the Server on Windows
* Click the red **`⏹️ Quit Server`** button in the top right of the web dashboard (`http://localhost:5000`).
* Or simply close the Command Prompt window.
