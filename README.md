# Cursor Restore 🔄

Recover deleted files from Cursor's backup history on macOS. When Cursor accidentally deletes your project, this tool extracts file backups from Cursor's History folder and SQLite databases.

## Quick Start

```bash
# Restore files from the last 7 days (default)
python3 cursor_restore_mac.py -r ~/Projects/MyProject/

# Files will be restored to ./restoredFolder/
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd Cursor-Restore

# Make scripts executable
chmod +x cursor_restore_mac.py cursor_sqlite_explorer.py

# No dependencies required - uses Python 3.6+ standard library
```

## Usage Examples

### Restore Files from History

```bash
# Basic restore (last 7 days)
python3 cursor_restore_mac.py -r ~/Projects/MyProject/

# Restore from last 30 days
python3 cursor_restore_mac.py -r ~/Projects/MyProject/ -b 30

# Custom output directory
python3 cursor_restore_mac.py -r ~/Projects/MyProject/ -o ~/Desktop/recovered

# Specific date range
python3 cursor_restore_mac.py -r ~/Projects/MyProject/ \
  -s "2024-12-01 00:00:00" \
  -e "2024-12-12 23:59:59"

# Quiet mode (minimal output)
python3 cursor_restore_mac.py -r ~/Projects/MyProject/ -q
```

### Workspace Management

```bash
# List all available workspaces
python3 cursor_restore_mac.py --list-workspaces

# Example output:
# Workspace ID: 4cabb0722f5aa8d20b1096a3524eac2e
#   Path: /Users/name/Projects/MyApp
#   Database: ~/Library/Application Support/Cursor/User/workspaceStorage/.../state.vscdb
```

### Extract Code from Chat History

```bash
# Extract all code from Cursor chat conversations
python3 cursor_sqlite_explorer.py --extract-code

# Filter by project name
python3 cursor_sqlite_explorer.py --extract-code --filter "MyProject"

# Custom output directory
python3 cursor_sqlite_explorer.py --extract-code -o ~/Desktop/chat_code

# Explore a workspace-specific database
python3 cursor_sqlite_explorer.py \
  --db ~/Library/Application\ Support/Cursor/User/workspaceStorage/xxx/state.vscdb \
  --extract-code
```

### Database Exploration

```bash
# List all tables in the database
python3 cursor_sqlite_explorer.py --list-tables

# List all keys (with limit)
python3 cursor_sqlite_explorer.py --list-keys --limit 50

# Search for specific keys
python3 cursor_sqlite_explorer.py --search "bubbleId:%"

# Get value for a specific key
python3 cursor_sqlite_explorer.py --get-value "bubbleId:some-id-here"
```

## Command Line Options

### cursor_restore_mac.py

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--restore-path` | `-r` | **Required** - Directory path to restore | - |
| `--output-dir` | `-o` | Output directory for restored files | `restoredFolder` |
| `--days-back` | `-b` | Number of days to search back | `7` |
| `--start-time` | `-s` | Start timestamp (YYYY-MM-DD HH:MM:SS) | 7 days ago |
| `--end-time` | `-e` | End timestamp (YYYY-MM-DD HH:MM:SS) | Now |
| `--list-workspaces` | `-l` | List all workspaces and exit | - |
| `--quiet` | `-q` | Minimal output | - |
| `--history-dir` | `-d` | Custom history directory | Auto-detected |

### cursor_sqlite_explorer.py

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--extract-code` | `-e` | Extract code from chat conversations | - |
| `--filter` | `-f` | Filter conversations by text | - |
| `--output-dir` | `-o` | Output directory | `extracted_code` |
| `--list-tables` | `-t` | List all database tables | - |
| `--list-keys` | `-k` | List all keys | - |
| `--search` | `-s` | Search keys (SQL LIKE pattern) | - |
| `--get-value` | `-g` | Get value for specific key | - |
| `--db` | `-d` | Custom database path | Global state.vscdb |
| `--limit` | `-l` | Limit number of results | No limit |

## How It Works

### History Folder Method

1. Scans `~/Library/Application Support/Cursor/User/History/`
2. Reads `entries.json` files to find your files
3. Filters by directory path and timestamp range
4. Selects the latest version of each file
5. Restores files maintaining original directory structure

### SQLite Database Method

1. Connects to `state.vscdb` databases
2. Queries `cursorDiskKV` table for chat conversations
3. Extracts JSON data containing code snippets
4. Parses messages for code blocks
5. Saves extracted code to separate files

## File Locations (macOS)

| Description | Path |
|-------------|------|
| **History Folder** | `~/Library/Application Support/Cursor/User/History/` |
| **Global Database** | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |
| **Workspace Databases** | `~/Library/Application Support/Cursor/User/workspaceStorage/*/state.vscdb` |

## Example Output

```
Cursor History Restore Script for macOS
================================================================================
History directory: /Users/name/Library/Application Support/Cursor/User/History
Restore path: /Users/name/Projects/MyProject
Output directory: restoredFolder
Time range: 2024-12-05 10:30:00 to 2024-12-12 10:30:00

Scanning history directory...
Found: src/components/Button.tsx (from 2024-12-11 15:30:22)
Found: src/utils/helpers.ts (from 2024-12-10 09:46:41)
Found: README.md (from 2024-12-11 14:10:04)
Found: package.json (from 2024-12-11 15:30:25)

Processed 1,247 folders, found 42 matching files

Restoring files to: restoredFolder
Restored: src/components/Button.tsx
Restored: src/utils/helpers.ts
Restored: README.md
Restored: package.json

Successfully restored 42 files
================================================================================
Restore complete!
Total files restored: 42
```

## Troubleshooting

### No Files Found

**Try expanding the time range:**
```bash
python3 cursor_restore_mac.py -r ~/Projects/MyProject/ -b 30
```

**Verify the exact path:**
```bash
cd ~/Projects/MyProject
pwd  # Copy this exact path
python3 cursor_restore_mac.py -r "$(pwd)"
```

**Try chat history extraction:**
```bash
python3 cursor_sqlite_explorer.py --extract-code --filter "filename.py"
```

### Permission Denied

Grant Full Disk Access to Terminal:
1. System Settings → Privacy & Security → Full Disk Access
2. Add Terminal (or your terminal app)
3. Restart terminal and try again

### Database is Locked

Close Cursor before accessing databases:
```bash
killall Cursor
python3 cursor_sqlite_explorer.py --extract-code
```

### Finding Your Project Path

```bash
# Navigate to your project
cd ~/Projects/MyProject

# Get the absolute path
pwd

# Use the output with -r flag
python3 cursor_restore_mac.py -r /Users/name/Projects/MyProject/
```

## Pro Tips

1. **Start narrow, expand if needed**: Try 7 days first, then 30, then 90
2. **Use absolute paths**: Get them with `pwd` in your project directory
3. **Check multiple sources**: Try both History folder and chat extraction
4. **Multiple attempts**: Different date ranges may yield different results
5. **Backup restored files**: Review before reintegrating into your project

## What Gets Restored

- ✅ All file versions from History folder
- ✅ Original directory structure maintained
- ✅ Latest version within time range
- ✅ All file types (code, config, documentation, etc.)
- ✅ Code snippets from chat conversations (with SQLite explorer)

## Safety & Privacy

- **Read-only operations** - Original backups are never modified
- **Local only** - No data sent to external servers
- **You control** - You choose what to restore and where
- **Non-destructive** - Restored files go to a separate directory

## Recovery Strategy

If files aren't in Cursor's history:

1. **Time Machine**: macOS built-in backup
2. **Git**: Check remote repositories (`git log --all`)
3. **iCloud Drive**: If project was in iCloud
4. **Cursor Backup DB**: Try `.backup` database files
5. **Chat History**: Code might be in conversations

## Requirements

- Python 3.6 or higher
- macOS (tested on macOS 10.15+)
- Cursor editor installed with history/chat data

## License

See LICENSE file for details.

## Disclaimer

This tool is provided as-is for emergency file recovery. Always maintain regular backups using Git, Time Machine, or other backup solutions. Don't rely solely on Cursor's history for backup purposes.

---

**Emergency Recovery Checklist:**

1. ✅ Don't panic
2. ✅ Close Cursor to avoid further changes
3. ✅ Run restore tool: `python3 cursor_restore_mac.py -r ~/Projects/MyProject/`
4. ✅ Check restored files in `restoredFolder/`
5. ✅ Try chat extraction if files missing: `python3 cursor_sqlite_explorer.py --extract-code`
6. ✅ Expand time range if needed: add `-b 30` or `-b 90`
7. ✅ Review and reintegrate recovered files
8. ✅ Commit to Git immediately! 🙏
