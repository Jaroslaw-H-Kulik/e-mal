# Auto-Persist System Guide

## Overview

The genealogy editor now **automatically saves all changes** to the project files. No more manual downloads or uploads!

## ✅ What's New

### 1. Auto-Save Merge Log
- ✅ Merges automatically saved to `data/merge_log.json`
- ✅ No manual file copying required
- ✅ Accumulates across sessions
- ✅ Parser auto-applies on reprocessing

### 2. Auto-Save Data
- ✅ All edits saved to `data/genealogy_complete.json`
- ✅ Immediate persistence
- ✅ No export button needed (but still available)

### 3. Complete Relationship Migration
- ✅ All relationships transferred during merge
- ✅ All events updated (child, father, mother, etc.)
- ✅ Witness arrays updated
- ✅ Godparent arrays updated
- ✅ Network graph updated instantly

### 4. Witness Relationships on Graph
- ✅ Witness connections now visible
- ✅ Dashed gray lines
- ✅ Filter view: "Witnesses" button
- ✅ Shows social network connections

## 🚀 How It Works

### New Server Architecture

**Old way:**
```bash
python3 -m http.server 8001  # Read-only
```

**New way:**
```bash
python3 server.py  # Read + Write capability
```

The new server:
- Serves static files (HTML, JS, CSS)
- Accepts POST requests to save data
- Auto-saves to `data/` directory
- Handles CORS for API calls

### Auto-Save Flow

**When you merge persons:**

1. **User action:** Select 2 persons → Click "Merge"
2. **System processes:**
   - Updates all relationships
   - Updates all events
   - Removes merged person from network
   - Clears search results
3. **Auto-save happens:**
   - POST to `/api/save-merge-log` → saves `data/merge_log.json`
   - POST to `/api/save-data` → saves `data/genealogy_complete.json`
4. **User sees:** Success notification

**No manual steps required!**

## 🎯 Complete Workflow

### Merge Duplicates (Auto-Persist)

1. **Start server:**
   ```bash
   python3 server.py
   ```

2. **Open browser:**
   ```
   http://localhost:8001/web/
   ```

3. **Merge duplicates:**
   - Search "Brygida"
   - Select Brygida Surdey
   - Click "🔗 Select for Merge"
   - Select Brygida Słyk
   - Click "🔗 Select for Merge"
   - Modal auto-opens
   - Click "Merge Persons"
   - **Done! Auto-saved to project files**

4. **Verify:**
   ```bash
   cat data/merge_log.json
   ```

### Reprocess Base.md

When you update `base.md` and need to reprocess:

```bash
python3 process_genealogy_v2.py
```

**Output:**
```
✓ Loaded 2 merge records from data/merge_log.json
  These duplicates will be automatically merged after parsing

Reading: base.md
...

Applying known merges...
  Merging Brygida Słyk (P0125) → Brygida Surdey (P0003)
  Merging Brygida Kruk (P0287) → Brygida Surdey (P0003)
✓ Applied 2 merges from log

✓ Exported 490 persons
```

**Result:** Clean data, no duplicates!

5. **Refresh browser:** `Cmd+Shift+R`

## 📊 Witness Relationships on Graph

### How to View

**Filter by relationship type:**
- Click "All" - Show everything
- Click "Families" - Only parent-child
- Click "Marriages" - Only marriages
- Click "Godparents" - Only godparent relationships
- Click "**Witnesses**" - **Only witness connections** (NEW!)

**What you see:**
- Gray dashed lines between witnesses
- Shows who witnessed events together
- Social network connections
- Community relationships

**Example:**
```
Jan Surdey -------- (witnessed together) -------- Kazimierz Łapacz
    |                                                      |
  (father)                                             (witness)
    |                                                      |
 Brygida                                            Multiple events
```

### Legend

| Line Style | Relationship | Color |
|-----------|--------------|-------|
| Solid green → | Parent-Child | Green |
| Solid red | Marriage | Red |
| Solid orange | Godparent | Orange |
| **Dashed gray** | **Witness** | **Gray** |

## 🔧 What Migrates During Merge

When you merge Person B into Person A:

**Relationships:**
```javascript
// Before:
B → parent → C
B → married → D

// After:
A → parent → C  (transferred)
A → married → D  (transferred)
B deleted
```

**Events:**
```javascript
// Birth event:
father: B → father: A
mother: B → mother: A
child: B → child: A

// Death event:
deceased: B → deceased: A

// Marriage event:
groom: B → groom: A
bride: B → bride: A

// Arrays:
witnesses: [X, B, Y] → witnesses: [X, A, Y]
godparents: [B, Z] → godparents: [A, Z]
```

**Network:**
- Node B removed from graph
- All edges reconnect to A
- Position recalculated
- Witness connections updated

## 📁 File Structure

```
mal/
├── server.py                    # NEW: Server with write capability
├── base.md                      # Source data
├── process_genealogy_v2.py      # Parser (auto-applies merges)
├── data/
│   ├── merge_log.json          # AUTO-SAVED merge records
│   ├── genealogy_complete.json # AUTO-SAVED complete data
│   ├── persons.json
│   ├── events.json
│   └── relationships.json
└── web/
    ├── index.html              # (updated: witness button)
    ├── app.js                  # (updated: witness edges, v4)
    ├── editor.js               # (updated: auto-save, v4)
    └── style.css               # (updated: witness legend)
```

## 🎮 Server API Endpoints

### POST /api/save-merge-log

**Request:**
```json
{
  "merges": [
    {
      "kept_person": "P0003",
      "merged_person": "P0125",
      "kept_name": "Brygida Surdey",
      "merged_name": "Brygida Słyk",
      "timestamp": "2026-02-14T..."
    }
  ],
  "last_updated": "2026-02-14T..."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Data saved successfully"
}
```

**Side effect:** Updates `data/merge_log.json`

### POST /api/save-data

**Request:**
```json
{
  "persons": {...},
  "events": {...},
  "relationships": {...},
  "metadata": {...}
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Data saved successfully"
}
```

**Side effect:** Overwrites `data/genealogy_complete.json`

## 🔍 Verification

### Check Merge Log

```bash
cat data/merge_log.json | python3 -m json.tool
```

**Look for:**
- `total_merges` count
- Each merge has `kept_name` and `merged_name`
- Recent `last_updated` timestamp

### Check Data File

```bash
cat data/genealogy_complete.json | python3 -m json.tool | head -20
```

**Look for:**
- `metadata.total_persons` decreased after merge
- Merged person ID not in `persons` object
- Kept person has all relationships

### Check Console Logs

**Browser console (F12):**
```
✓ Merge log saved to data/merge_log.json
✓ Data saved to data/genealogy_complete.json
```

**Server console:**
```
✓ Saved merge log: 2 total merges
✓ Saved genealogy data: 490 persons
```

## 🚨 Troubleshooting

### Auto-save not working

**Check server type:**
```bash
# Wrong (old):
python3 -m http.server 8001

# Correct (new):
python3 server.py
```

**Check server logs:**
```bash
# Should see:
======================================================================
Genealogy Editor Server
======================================================================
Server running at: http://localhost:8001/
```

**Check browser console:**
- Open F12 → Console
- Look for errors after merge
- Should see "✓ Merge log saved..."

### Server not starting

```bash
# Kill any process on port 8001
lsof -ti:8001 | xargs kill -9

# Start new server
python3 server.py
```

### Merge not saving

**Check file permissions:**
```bash
ls -la data/
# Should be writable
```

**Check CORS errors:**
- Open browser console
- If CORS error, server needs restart

### Witness edges not showing

**Try:**
1. Hard refresh: `Cmd+Shift+R`
2. Check cache-busting: `editor.js?v=4`
3. Click "Witnesses" button
4. Check console for errors

## 📋 Commands Reference

```bash
# Start server (with write capability)
python3 server.py

# Stop server
lsof -ti:8001 | xargs kill -9

# Reprocess with auto-merge
python3 process_genealogy_v2.py

# View merge log
cat data/merge_log.json | python3 -m json.tool

# Backup before reprocessing
cp data/genealogy_complete.json data/backup.json

# Check server status
lsof -ti:8001 && echo "Server running" || echo "Server not running"
```

## 🎁 Benefits

**Before:**
1. Merge persons in browser
2. Click "Export Data"
3. Download 2 files
4. Copy to `data/` directory
5. Reprocess
6. Hope you didn't forget a step

**After:**
1. Merge persons in browser
2. **Done!** Everything auto-saved
3. Reprocess anytime
4. Merges automatically applied

**Time saved:** ~2 minutes per merge session
**Error prevention:** No more forgotten uploads
**Simplicity:** One-click merge, automatic persistence

---

**Server:** `server.py` (port 8001)
**Auto-save:** Merge log + Complete data
**Witness graph:** Enabled with dashed lines
**Version:** 3.0 (auto-persist)
**Updated:** 2026-02-14
