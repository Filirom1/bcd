# BCD Installation Guide

Complete installation instructions for BCD Library Management System.

## System Requirements

**Required**:
- Python 3.11 or higher
- 500 MB disk space
- Modern web browser (Chrome, Firefox, Safari, or Edge)

**Optional**:
- USB barcode scanner (HID keyboard mode)
- PostgreSQL database (for production deployments)

**Operating Systems**:
- Linux (tested on Ubuntu 20.04+, Debian 11+)
- macOS (tested on 11+)
- Windows 10/11

---

## Installation Options

### Option 1: Windows Portable Edition (Easiest for Windows)

For Windows users, a portable edition is available that requires no Python installation.

**Features**:
- No Python installation required
- No dependencies to install
- Self-contained executable
- Simple double-click to start
- Perfect for non-technical users

**Installation Steps**:
1. Download the latest BCD-vX.X.X-Windows.zip from GitHub Releases
2. Extract to your desired location (e.g., `C:\BCD`)
3. Double-click `bcd.exe` to launch
4. The application window opens automatically

**Directory Structure** (created on first run):
```
BCD-v1.0.0-Windows/
├── bcd.exe                     # Main application (double-click to launch)
├── config/                     # Configuration (.env file)
├── data/                       # Database (bcd.db) and user files
├── LICENSE                     # MIT License
└── README.md                   # Documentation
```

**Configuration** (`config/.env`, auto-created on first run — edit with any text editor):

| Setting | Default | Description |
|---------|---------|-------------|
| `API_HOST` | `127.0.0.1` | Bind address. Set to `0.0.0.0` for network access. |
| `API_PORT` | `8000` | Listen port. |
| `LOG_LEVEL` | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `ENVIRONMENT` | `production` | Set to `development` to enable hot reload. |
| `UI_MODE` | `webview` | Interface to launch: `webview` (native window), `browser` (system browser), or `godot` (Godot client). |
| `GODOT_CLIENT_PATH` | *(empty)* | Path to Godot client executable (required when `UI_MODE=godot`). Example: `BCD-Godot.exe` |
| `DATABASE_URL` | *(auto)* | Override the database path (absolute path recommended). |
| `BNF_API_URL` | *(BNF SRU)* | French National Library ISBN lookup endpoint. |
| `BNF_RATE_LIMIT` | `1` | BNF API requests per second. |

**CLI flags** (override `config/.env` for a single run):

```
bcd --host 0.0.0.0 --port 9000     # bind on all interfaces, port 9000
bcd --ui-mode browser              # open system browser
bcd --ui-mode godot                # launch Godot client (requires GODOT_CLIENT_PATH)
bcd --help                         # show all options
```

**Stopping the Application**:
- Close the application window

**Windows Defender SmartScreen**:
If you see "Windows protected your PC":
1. Click "More info"
2. Click "Run anyway"

**Network Access (Windows)**:
1. Edit `config/.env` and set `API_HOST=0.0.0.0`
2. Find your IP with `ipconfig` command
3. Allow port 8000 when Windows Firewall prompts
4. Access from other computers: `http://YOUR-IP:8000`

**Backup** (Windows Portable):
- Close the application first
- Copy entire `data/` folder to backup location
- To restore: Replace `data/` folder and relaunch

### Option 2: Python Installation (All Platforms)

---

## Quick Installation

### Step 1: Install Python

**Linux (Debian/Ubuntu)**:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**macOS**:
```bash
# Using Homebrew
brew install python@3.11
```

**Windows**:
- Download Python 3.11+ from https://www.python.org/downloads/
- Run installer
- Check "Add Python to PATH"

### Step 2: Download BCD

```bash
# Clone the repository or download and extract the ZIP file
git clone <repository-url> bcd
cd bcd
```

Or download ZIP and extract to a folder named `bcd`.

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate it
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -e "."
```

This will install all necessary packages (~100 MB download).

### Step 5: Initialize Database

```bash
alembic upgrade head
```

This creates the `bcd.db` database file with all tables.

### Step 6: Start the Server

```bash
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
```

You should see:
```
Starting BCD API + Web UI Server (Vue 3)
Serving web UI from: src/bcd_web_vue
Web UI: http://127.0.0.1:8000
API Docs: http://127.0.0.1:8000/api/v1/docs
```

### Step 7: Access BCD

Open your browser and go to: **http://127.0.0.1:8000**

**Success!** You should see the BCD library interface.

---

## Production Installation

For production use in a school environment.

### Option 1: SQLite (Default - Recommended for Small Schools)

SQLite is included and requires no additional setup. Perfect for:
- Single school library
- Up to 10,000 books
- Up to 500 students
- Simple backup (copy `bcd.db` file)

**No additional configuration needed.**

### Option 2: PostgreSQL (For Large Schools)

PostgreSQL provides better performance and concurrent access. Recommended for:
- Multiple libraries/branches
- More than 10,000 books
- More than 500 students
- High concurrent usage

**Installation**:

1. **Install PostgreSQL**:
   ```bash
   # Linux
   sudo apt install postgresql postgresql-contrib

   # macOS
   brew install postgresql
   ```

2. **Create database and user**:
   ```bash
   sudo -u postgres psql
   ```

   Then in PostgreSQL prompt:
   ```sql
   CREATE DATABASE bcd;
   CREATE USER bcd_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE bcd TO bcd_user;
   \q
   ```

3. **Configure BCD**:
   Create a `.env` file in the BCD directory:
   ```bash
   DATABASE_URL=postgresql://bcd_user:your_secure_password@localhost/bcd
   ```

4. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

### Running as a Service

**Linux (systemd)**:

Create `/etc/systemd/system/bcd.service`:
```ini
[Unit]
Description=BCD Library Management System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/bcd
Environment="PATH=/path/to/bcd/venv/bin"
ExecStart=/path/to/bcd/venv/bin/uvicorn src.bcd_api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable bcd
sudo systemctl start bcd
sudo systemctl status bcd
```

**Windows (NSSM)**:

1. Download NSSM from https://nssm.cc/
2. Open Command Prompt as Administrator
3. Run:
   ```cmd
   nssm install BCD "C:\path\to\bcd\venv\Scripts\python.exe" "-m uvicorn src.bcd_api.main:app --host 0.0.0.0 --port 8000"
   nssm set BCD AppDirectory "C:\path\to\bcd"
   nssm start BCD
   ```

### Network Access

To allow access from other computers on your network:

1. **Start server with network binding**:
   ```bash
   python -m uvicorn src.bcd_api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Find your computer's IP address**:
   ```bash
   # Linux/macOS
   ip addr show
   # or
   ifconfig

   # Windows
   ipconfig
   ```

   Look for something like `192.168.1.100`

3. **Access from other computers**:
   Open browser and go to: `http://192.168.1.100:8000`

**Firewall**:
- Linux: `sudo ufw allow 8000`
- Windows: Allow port 8000 in Windows Firewall

---

## Importing Initial Data

### Import Students

1. Prepare CSV file with columns: `StudentID,FirstName,LastName,Class`

Example `students.csv`:
```csv
StudentID,FirstName,LastName,Class
101,Amira,BENALI,CP-A
102,Lucas,DUBOIS,CP-A
103,Léa,MARTIN,CP-B
```

2. In BCD web interface:
   - Go to **Borrowers**
   - Click **Import**
   - Select your CSV file
   - Review and confirm

Or via CLI (Python installation only):
```bash
bcd-cli borrower import students.csv --api-url http://localhost:8000
```

### Import Books

1. Prepare Dublin Core CSV file

Example format:
```csv
dc.title,dc.creator,dc.identifier,dc.publisher,dc.date,dc.language,item.id
"Stuart Little","E.B. White","9782211234567","Gallimard Jeunesse","2010","fre","BCD001"
"Charlotte's Web","E.B. White","9782211234574","Gallimard Jeunesse","2011","fre","BCD002"
```

2. Import via the **Cataloging** page in the web interface, or via CLI (Python installation only):
```bash
bcd-cli catalog import-dc books.csv --api-url http://localhost:8000
```

---

## Barcode Scanner Setup

Most USB barcode scanners work automatically in "keyboard mode" (HID).

**To test your scanner**:
1. Open Notepad or any text editor
2. Scan a barcode
3. You should see numbers appear

**If it doesn't work**:
- Check USB connection
- Try different USB port
- Consult scanner manual to enable "keyboard mode"
- Some scanners require configuration barcode scanning

**Compatible scanners**:
- Most USB HID scanners
- Tested with Symbol LS2208, Zebra DS2208, Honeywell Voyager

---

## Troubleshooting

### "Address already in use" error

The server is already running. Either:
- Find and close the existing server window
- Or use a different port:
  ```bash
  python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8001
  ```

### "Module not found" error

Virtual environment not activated or dependencies not installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e "."
```

### Database errors

**"No such table"**:
```bash
alembic upgrade head
```

**"Database is locked" (SQLite only)**:
- Close all other connections to the database
- Or switch to PostgreSQL for better concurrency

### Can't access from other computers

1. Check server is listening on `0.0.0.0` not `127.0.0.1`
2. Check firewall allows port 8000
3. Verify computers are on same network
4. Try with computer's IP address instead of hostname

### Performance issues

**For SQLite**:
- Maximum ~50 concurrent users
- Database should be on SSD
- Regular VACUUM maintenance:
  ```bash
  sqlite3 bcd.db "VACUUM;"
  ```

**For PostgreSQL**:
- Increase `max_connections` in postgresql.conf
- Add database indexes (already included in migrations)
- Use connection pooling

---

## Backup and Restore

### Windows/Linux Portable Edition

**Create backup** — via the web interface:
1. Open BCD and go to **Settings**
2. Click **Create Backup** — a timestamped `.db` file is saved in the `backups/` folder

**Manual backup** (while the application is closed):
```bash
# Windows
xcopy data\ backup_data\ /E /I

# Linux
cp -r data/ backup_data/
```

**Restore**:
1. Close the application
2. Replace the `data/` folder with your backup
3. Relaunch `bcd.exe` / `./bcd`

### Python Installation

**Create backup**:
```bash
# CLI
bcd-cli admin backup

# API endpoint
curl -X POST http://127.0.0.1:8000/api/v1/admin/backup
```

**List backups**:
```bash
bcd-cli admin list-backups
```

**Restore from backup**:
```bash
bcd-cli admin restore backups/bcd_backup_20260205_143022.db --confirm
```

**Automated daily backup** (Linux):
Add to crontab (`crontab -e`):
```bash
0 21 * * * cd /path/to/bcd && /path/to/venv/bin/bcd-cli admin backup
```

### Manual Backup (Alternative — Python installation)

**Backup**:
```bash
cp data/bcd.db data/bcd_backup_$(date +%Y%m%d).db
```

**Restore**:
```bash
cp data/bcd_backup_20260205.db data/bcd.db
```

### PostgreSQL Backup

**Backup**:
```bash
pg_dump -U bcd_user bcd > bcd_backup_$(date +%Y%m%d).sql
```

**Restore**:
```bash
psql -U bcd_user bcd < bcd_backup_20260205.sql
```

---

## Upgrading BCD

### Option 1: Windows/Linux Portable Edition

#### Automatic update (recommended)

BCD checks for new releases on GitHub each time it starts (requires internet access; silently skipped when offline).

When a new version is available you will see a dialog in your OS language (French or English):

> **Mise à jour disponible** / **Update available**
> BCD vX.Y.Z est disponible. / BCD vX.Y.Z is available.
> Voulez-vous mettre à jour maintenant ? / Do you want to update now?
> [Oui / Yes] [Non / No]

Click **Oui** — BCD downloads the archive, replaces all its own files (`bcd.exe` / `bcd`, `_internal/`, `BCD-Kids.exe` / `BCD-Kids.x86_64`), and restarts automatically. Your `data/` and `config/` folders are never touched.

Database migrations run automatically on the restarted instance — no manual steps needed.

#### Manual update (fallback)

Use this if the automatic update fails or if the machine has no internet access.

1. **Create a backup** (Settings page in the web UI, or copy `data/` folder)

2. **Close the application**

3. **Download** the new `BCD-vX.X.X-Windows.zip` (or `.tar.gz` for Linux) from GitHub Releases

4. **Extract** to a new folder (e.g., `BCD-v1.1.0-Windows/`)

5. **Copy your data** from the old installation into the new folder:
   ```
   old-folder/config/  →  new-folder/config/
   old-folder/data/    →  new-folder/data/
   ```

6. **Launch** `bcd.exe` (Windows) or `./bcd` (Linux) from the new folder
   — migrations apply automatically on first launch

7. Verify the application works correctly, then delete the old folder

### Option 2: Python Installation

1. **Backup your database**:
   ```bash
   bcd-cli admin backup
   ```

2. **Stop the server**

3. **Update code**:
   ```bash
   git pull origin main
   # or download and extract new version
   ```

4. **Activate virtual environment**:
   ```bash
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

5. **Update dependencies**:
   ```bash
   pip install -e "." --upgrade
   ```

6. **Update frontend vendor files** (only if `vendor.json` changed):
   ```bash
   python scripts/download-vendor.py
   ```

7. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

8. **Restart server**

---

## Uninstalling BCD

1. **Stop the server**

2. **Backup data** (if you want to keep it):
   ```bash
   cp bcd.db ~/bcd_backup.db
   ```

3. **Remove BCD directory**:
   ```bash
   rm -rf /path/to/bcd
   ```

4. **(Optional) Remove PostgreSQL database**:
   ```bash
   sudo -u postgres psql
   DROP DATABASE bcd;
   DROP USER bcd_user;
   ```

---

## Getting Help

**Installation issues**:
- Check Python version: `python --version` (must be 3.11+)
- Check pip version: `pip --version`
- Review error messages carefully

**Documentation**:
- [README.md](README.md) - User guide
- [DEVELOPERS.md](DEVELOPERS.md) - Developer documentation
- API Documentation: http://localhost:8000/api/v1/docs

**Support**:
- Check existing issues on GitHub
- Contact your IT administrator
- Review logs in the terminal where server is running

---

## Security Considerations

**For local network use** (recommended):
- BCD has no built-in authentication
- Rely on network isolation (school LAN only)
- Use firewall to restrict external access

**For internet-facing deployments**:
- Add reverse proxy with authentication (nginx, Apache)
- Use HTTPS with SSL certificates
- Implement rate limiting
- Regular security updates

**Data protection**:
- Regular backups (see Backup section)
- Store backups securely off-site
- Limit access to database files
- Follow school data protection policies

---

## Next Steps

After installation:
1. Configure settings in **Settings** page
2. Import students (see Importing Initial Data)
3. Add your book collection
4. Train staff on basic operations
5. Set up regular backup schedule

**Ready to use BCD!** See [README.md](README.md) for user guide.
