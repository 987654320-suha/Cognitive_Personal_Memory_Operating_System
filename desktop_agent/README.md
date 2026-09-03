# CogniSphere Desktop Agent — File & Memory Sync

The **CogniSphere Desktop Agent** runs locally on your Windows computer and synchronizes authorized local folders (Desktop, Documents, Downloads, Pictures, Videos, and custom folders) with your CogniSphere Memory OS.

---

## Architecture & Security

```
WINDOWS COMPUTER
  ├── User explicitly grants folder permissions
  ├── Local SHA-256 hash manifest prevents redundant uploads
  ├── Watchdog tracks real-time file creation, edits, and deletions
  ├── Offline resilient SQLite queue ensures no events are lost
       ↓  (HTTPS with secure X-Device-Token)
COGNISPHERE BACKEND (Render / Local)
  ├── Content-hash deduplication: Identical content across paths reuses memory
  ├── Ingestion: OCR, Text extraction, all-MiniLM-L6-v2 embeddings, ACMA/GAMA scoring
  ├── Persistent Storage: SQLite / PostgreSQL + FAISS + BM25
       ↓
COGNISPHERE FRONTEND (Next.js)
  └── Settings -> Connected Devices: View status, manage folders, pause/resume sync
```

### Privacy Guarantees
- **No Silent Scans**: The agent will never scan any folder without explicit user permission.
- **Privacy-Preserving Paths**: Absolute paths (like `C:\Users\Username\...`) are kept local; the cloud backend only stores relative location identifiers (e.g. `Documents/Report.pdf`).
- **No Secrets Stored in Frontend**: Device tokens are generated and verified on the backend.

---

## Quick Start on Windows

### Method 1: Using the Batch Launcher (Easiest)
Double-click:
```cmd
run_desktop_agent.bat
```
Or run from PowerShell/CMD:
```cmd
.\run_desktop_agent.bat
```

### Method 2: Python Command
```powershell
# Against local backend
python desktop_agent/agent.py --server http://localhost:8000

# Against production Render backend
python desktop_agent/agent.py --server https://cognisphere-backend-ya2y.onrender.com
```

---

## First Run Setup Wizard

When you start the agent for the first time, an interactive wizard prompts you to select which folders CogniSphere has permission to access:

```
==============================================================
  CogniSphere Desktop Agent — File & Memory Sync
==============================================================

Welcome to CogniSphere!
Choose which folders CogniSphere has permission to access:

  1. [ ] Documents (C:\Users\...\Documents)
  2. [ ] Desktop (C:\Users\...\Desktop)
  3. [ ] Downloads (C:\Users\...\Downloads)
  4. [ ] Pictures (C:\Users\...\Pictures)
  5. [ ] Videos (C:\Users\...\Videos)

Options:
  - Enter numbers separated by commas to toggle (e.g., 1, 2)
  - Enter 'c' to add a custom folder path
  - Press Enter to continue
```

---

## CLI Options

| Flag | Description |
|------|-------------|
| `--server <url>` | Backend URL (defaults to `https://cognisphere-backend-ya2y.onrender.com`) |
| `--status` | Prints paired device info, backend connectivity, and watched folders |
| `--scan-now` | Performs an immediate incremental scan and exits |
| `--add-folder <path>` | Authorizes and adds a custom folder to monitoring |
| `--headless` | Runs without interactive wizard (for automated/background runs) |
| `--enable-all-defaults` | Enables Documents, Desktop, Downloads, Pictures, Videos |

---

## Supported File Types

- **Documents**: `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.csv`, `.xlsx`, `.pptx`
- **Images**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp` (automatic OCR + object detection)
- **Extensible**: Add more file types via `desktop_agent/parsers.py` using `ParserRegistry.register(YourParser)`.
