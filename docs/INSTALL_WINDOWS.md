# Install WisperNext on Windows

[Back to README](../README.md)

You need Windows 10 or 11, 64-bit Python 3.12 or 3.13, Git, an internet connection,
and a [Groq API key](https://console.groq.com/keys). Windows 11 is the tested platform.
WisperNext currently installs from source; a production installer is not available.
The application is free and open source. Groq's Free Plan supports the required models
within its [usage limits](https://console.groq.com/docs/rate-limits). A paid Groq plan
may incur charges under Groq's [billing terms](https://console.groq.com/docs/billing-faqs).

## Download and install

Open PowerShell. For every code block below, click its copy button, paste it into PowerShell, and
press Enter.

### 1. Download WisperNext

```powershell
git clone https://github.com/teremno/WisperNext.git
cd WisperNext
```

### 2. Create the Python environment

For Python 3.13:

```powershell
py -3.13 -m venv .venv
```

If this succeeds, continue to step 3.

If Python 3.13 is unavailable and you have Python 3.12, use this command instead:

```powershell
py -3.12 -m venv .venv
```

Python 3.14 and later are not supported yet.

### 3. Install the application

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

When the last line says `Successfully installed wispernext`, installation is complete.

## Create a Groq API key

1. Open the official [Groq API Keys page](https://console.groq.com/keys).
2. Create a Groq account or sign in.
3. Click **Create API Key**, give it any name, then copy the new key.
4. Keep the key private. Do not send it to anyone or add it to a file in the project.

## Store the API key safely in Windows

Run these commands one at a time in the same PowerShell window:

```powershell
$secureKey = Read-Host "Enter your Groq API key" -AsSecureString
```

PowerShell now displays `Enter your Groq API key:`. Paste the key you copied, then press Enter.
The characters are hidden on purpose.

```powershell
$env:WISPER_GROQ_API_KEY = [Net.NetworkCredential]::new("", $secureKey).Password
```

```powershell
.\.venv\Scripts\python.exe .\scripts\migrate_groq_key_to_credential_manager.py
```

When PowerShell shows `"status": "stored_and_verified"`, the key is saved safely. Finally run:

```powershell
Remove-Item Env:WISPER_GROQ_API_KEY
```

The key is stored in Windows Credential Manager, not in application settings or diagnostic logs.

## Launch WisperNext

```powershell
.\.venv\Scripts\pythonw.exe -m wispernext
```

Press Enter once. PowerShell does not show a success message; after a few seconds, the floating
microphone button and a system-tray icon appear. You may then close PowerShell. Use the floating
button or `F8`; right-click the button, or use the system-tray icon, to open Settings.

If the floating button is ever hidden by a display, sleep, or desktop change, open the system-tray
menu and select **Show microphone button**. WisperNext also repairs hidden, off-screen, and lost
always-on-top state automatically.

Create a desktop shortcut with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_development_shortcut.ps1
```
