# Merge Workflow Guide

## Overview

The genealogy editor now has a complete merge system that:
1. ✅ **Removes merged entities** from search results immediately
2. ✅ **Transfers all relationships** to the kept person
3. ✅ **Persists merge records** to prevent recreating duplicates when reprocessing

## The Problem Solved

**Before:** When you merged duplicates (e.g., Brygida Kruk → Brygida Surdey), the old entity would:
- Still appear in search results
- Be recreated if you reprocessed base.md
- Lose its relationships

**Now:** Merged entities are:
- Immediately removed from search results
- Have all relationships transferred to the kept person
- Recorded in a merge log that prevents recreation

## Complete Workflow

### Step 1: Identify Duplicates in Web Interface

1. Open: http://localhost:8001/web/
2. Search for the name (e.g., "Brygida")
3. Identify duplicate persons:
   - Brygida Surdey (P0003) - birth name
   - Brygida Słyk - after first marriage
   - Brygida Kruk - after second marriage

### Step 2: Merge Duplicates

**Option A: From Person Details**
1. Click on Brygida Surdey (primary)
2. Click "🔗 Select for Merge"
3. Search and click on Brygida Słyk
4. Click "🔗 Select for Merge"
5. Modal auto-opens with both persons
6. Click "Merge Persons"
7. Confirm action

**Option B: From Toolbar**
1. Click "🔗 Merge Persons" in toolbar
2. Click first person, then "Select"
3. Click second person, then "Select"
4. Click "Merge Persons"
5. Confirm action

### Step 3: Verify Merge

After merging:
- ✅ Search results automatically refresh (merged person removed)
- ✅ Network updates (merged node removed)
- ✅ Relationships transferred to kept person
- ✅ Success notification appears

### Step 4: Export Merge Log

**IMPORTANT:** After merging, export your changes!

1. Click "💾 Export Data" in toolbar
2. **Two files download:**
   - `genealogy_edited_[timestamp].json` - Full updated data
   - `merge_log_[timestamp].json` - Merge records only

### Step 5: Save Merge Log for Reprocessing

To prevent duplicates when reprocessing base.md:

1. Locate the downloaded `merge_log_[timestamp].json`
2. **Copy it to:** `data/merge_log.json` (remove timestamp)
3. Now when you run the parser, it will auto-apply these merges!

```bash
# Example:
cp ~/Downloads/merge_log_1708028471234.json data/merge_log.json
```

### Step 6: Reprocess Base.md with Auto-Merge

When you need to reprocess the source data:

```bash
python3 process_genealogy_v2.py
```

**What happens:**
1. Parser loads `data/merge_log.json`
2. Parses base.md normally
3. **Automatically merges** known duplicates
4. Exports clean data without duplicates!

**Output:**
```
✓ Loaded 3 merge records from data/merge_log.json
  These duplicates will be automatically merged after parsing

Reading: base.md

Applying known merges...
  Merging Brygida Słyk (P0125) → Brygida Surdey (P0003)
  Merging Brygida Kruk (P0287) → Brygida Surdey (P0003)
✓ Applied 2 merges from log

✓ Exported 490 persons (was 492 before merges)
```

## Merge Log Format

The `merge_log.json` file structure:

```json
{
  "instructions": "This file contains merge records...",
  "merges": [
    {
      "kept_person": "P0003",
      "merged_person": "P0125",
      "kept_name": "Brygida Surdey",
      "merged_name": "Brygida Słyk",
      "timestamp": "2026-02-14T15:30:00.000Z"
    }
  ],
  "total_merges": 1,
  "last_updated": "2026-02-14T15:30:00.000Z"
}
```

**Key fields:**
- `kept_name` / `merged_name` - Used for matching (IDs change between runs)
- `timestamp` - When merge was performed
- `total_merges` - Count for verification

## Best Practices

### 1. Export After Each Merge Session

After merging multiple persons:
1. Click "💾 Export Data"
2. Save both files
3. Copy `merge_log_*.json` to `data/merge_log.json`

### 2. Accumulate Merge Records

If you already have a merge log:
1. Open existing `data/merge_log.json`
2. Export new merges from web interface
3. **Manually combine** the `merges` arrays
4. Update `total_merges` count

**Example combining:**
```json
{
  "merges": [
    ...existing merges...,
    ...new merges...
  ],
  "total_merges": 10
}
```

### 3. Verify After Auto-Merge

After reprocessing with merge log:
1. Check console output for merge confirmations
2. Verify person count decreased appropriately
3. Open web interface and search for merged names
4. Confirm only kept persons appear

### 4. Keep Backups

Before reprocessing:
```bash
# Backup current data
cp data/genealogy_complete.json data/genealogy_complete.backup.json

# Then reprocess
python3 process_genealogy_v2.py
```

## Troubleshooting

### "Could not find person" Warning

```
⚠ Could not find person: Brygida Słyk
```

**Causes:**
- Name spelling changed in base.md
- Person was already merged in a previous run
- Manual edit changed the name

**Solution:**
- Check person still exists in base.md
- Verify name spelling matches exactly
- Remove obsolete merge records from log

### Search Still Shows Merged Person

**Try:**
1. Hard refresh browser: `Cmd+Shift+R`
2. Clear search and search again
3. Restart web server

### Merges Not Applied During Parsing

**Check:**
1. File is named exactly `data/merge_log.json`
2. JSON format is valid (use validator)
3. Console shows "✓ Loaded X merge records"

### Duplicate Persons Still Appear

**If parser couldn't match:**
- Name spelling must match exactly
- Check for extra spaces or characters
- Person must exist in parsed data

## Example: Complete Brygida Merge

**Starting state:** 3 Brygidas in database
- P0003: Brygida Surdey (b. 1804)
- P0125: Brygida Słyk (married to Szczepan)
- P0287: Brygida Kruk (married to Jędrzej)

**Step 1: Merge #1 (Słyk → Surdey)**
1. Open web interface
2. Select both persons
3. Merge Słyk into Surdey
4. Export data → `merge_log_1.json`

**Step 2: Merge #2 (Kruk → Surdey)**
1. Select Kruk and Surdey
2. Merge Kruk into Surdey
3. Export data → `merge_log_2.json`

**Step 3: Combine Logs**
```bash
# Manually combine or use the accumulated export
cp ~/Downloads/merge_log_2.json data/merge_log.json
```

**Step 4: Reprocess**
```bash
python3 process_genealogy_v2.py
```

**Result:**
- Only P0003 (Brygida Surdey) remains
- All relationships from Słyk and Kruk transferred
- All events reference Surdey
- Person count: 492 → 490

**Step 5: Refresh Web Interface**
```bash
# Browser: Cmd+Shift+R
# Search "Brygida" → Only one result!
```

## Technical Details

### What Gets Updated During Merge

**Persons:**
- Merged person deleted from `persons` dict
- Kept person retains all original data

**Relationships:**
- All `from_person` references updated
- All `to_person` references updated

**Events:**
- `child`, `father`, `mother` fields updated
- `deceased`, `groom`, `bride` fields updated
- `witnesses` and `godparents` arrays updated

**Network:**
- Merged node removed from vis.js network
- Edges automatically reconnect to kept node

### Matching Logic

When applying merges from log:
```python
for merge in merge_log:
    # Match by full name (since IDs change)
    kept = find_person_by_name(merge['kept_name'])
    merged = find_person_by_name(merge['merged_name'])

    if both_found:
        transfer_all_references(merged → kept)
        delete(merged)
```

**Why names, not IDs?**
- Person IDs are generated during parsing (P0001, P0002...)
- Same person gets different IDs each run
- Names are stable across parsing runs

## Files Reference

| File | Purpose | Location |
|------|---------|----------|
| `base.md` | Source data | Root directory |
| `merge_log.json` | Persistent merge records | `data/` |
| `gender_review.json` | Gender corrections | `data/` |
| `genealogy_complete.json` | Parsed output | `data/` |
| `genealogy_edited_[ts].json` | Export with changes | Downloads |
| `merge_log_[ts].json` | Export merge records | Downloads |

## Commands Reference

```bash
# Reprocess with merge log
python3 process_genealogy_v2.py

# Start web server
python3 -m http.server 8001

# Copy merge log
cp ~/Downloads/merge_log_*.json data/merge_log.json

# Backup before reprocessing
cp data/genealogy_complete.json data/genealogy_complete.backup.json

# View merge log
cat data/merge_log.json | python3 -m json.tool
```

---

**Last Updated:** 2026-02-14
**Version:** 2.0 (with persistent merge support)
