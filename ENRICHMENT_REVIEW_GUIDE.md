# GEDCOM Enrichment Review System

## ✅ System Complete!

Interactive UI for reviewing and applying GEDCOM enrichments with full control over duplicates.

## 📋 Features

✅ **Side-by-side comparison** - See your data vs GEDCOM data
✅ **Selective imports** - Choose what to add (dates, parents, children)
✅ **Smart matching** - Automatic duplicate detection with confidence scores
✅ **Merge or create** - Decide for each relative: merge with existing or create new
✅ **Evidence display** - See why matches are suggested
✅ **Progress tracking** - Review queue with progress bar
✅ **Safe application** - Changes applied one at a time

## 🚀 How to Use

### Step 1: Generate Enrichment Queue

```bash
python3 generate_enrichment_queue.py
```

This will:
- Match persons between base.md and base.ged
- Find parents and children for each match
- Search for potential duplicates
- Generate: `data/enrichment_queue.json`

**Output:**
```
✓ Matched 98 persons
✓ Generated 82 enrichment entries
  - 79 parents to review
  - 165 children to review
```

### Step 2: Open Web Interface

```bash
python3 server.py
# Open: http://localhost:8001/web/
```

### Step 3: Review Matches

1. Click **"📦 Review GEDCOM Matches (82)"** button
2. For each match, you'll see:
   - **Left panel**: Your data from base.md
   - **Right panel**: GEDCOM data with new info marked ✨
   - **Personal data**: Checkboxes for birth/death dates to import
   - **Parents**: Options to merge with existing or create new
   - **Children**: Options to merge with existing or create new

### Step 4: Make Decisions

**For each parent/child:**

#### Option A: Merge with Existing Person
```
● MERGE with P0089 - Józef Surdey (95%) ⭐
  ✓ Name matches
  ✓ Birth year matches (1828)
  ✓ Already has Jan Surdey as father
  Will add: death_year: 1890
```
- **Recommended matches** (⭐ 85%+) are pre-selected
- Click to select if not pre-selected
- Will add missing data to existing person

#### Option B: Create New Person
```
● CREATE NEW person as P0526
```
- Creates a brand new person
- Use when no good match exists
- Avoids creating duplicates

### Step 5: Apply Changes

1. Review your selections
2. Click **"Apply Changes"**
3. Changes are saved immediately
4. Graph updates in real-time
5. Move to next match

## 🎯 Match Quality Indicators

**⭐ High Confidence (85-100%)**
- Pre-selected for you
- Strong evidence (name + birth year + family context)
- Safe to accept

**Medium Confidence (60-85%)**
- Not pre-selected
- Some evidence but needs verification
- Review carefully before selecting

**Create New (default when <60%)**
- No good matches found
- Pre-selected to avoid false merges

## 📊 Match Evidence

Evidence shown for each match:
- ✓ **Name matches** - Given name and surname identical
- ✓ **Birth year matches** - Exact or within 2 years
- ✓ **Already parent of siblings** - Strong family context
- ✓ **Age difference consistent** - Parent 15-60 years older
- ✓ **Gender matches** - M/F alignment
- ✓ **Death year matches** - Within 5 years

## 🔍 Example Review Session

### Match #3: Jan Surdey

**Your Data:**
- Birth: ~1800 (estimate)
- Death: ?
- Spouse: Helena Minda ✓

**GEDCOM Data:**
- Birth: 1802-03-15 ⭐ (exact date!)
- Death: 1856-12-20 ⭐
- Spouse: Helena Minda ✓

**Import Personal Data:**
- [✓] Add birth date → 1802-03-15
- [✓] Add death date → 1856-12-20

**Parents (2 found):**

1. **Father: Wojciech Surdey (b.~1776, d.1828)**
   - ⭐ Match found: P0010 - Wojciech Surdey (90%)
   - [●] MERGE with P0010 (pre-selected)
     - Already father of Józef Surdey
     - Birth year consistent
     - Will add: death_year: 1828
   - [ ] CREATE NEW as P0523

2. **Mother: Salomea Surdey née Niewczas (b.~1780)**
   - ⚠️ No strong matches found
   - [ ] MERGE with P0234 - Salomea Niewczas (45%)
   - [●] CREATE NEW as P0524 (pre-selected)

**Children (3 found):**

1. **Brygida Surdey (b.1826)**
   - ⭐ Match: P0003 - Brygida Surdey (95%)
   - [●] MERGE with P0003 (pre-selected)
     - Already has Jan as father
     - No new data needed

2. **Józef Surdey (b.1828, d.1890)**
   - ⭐ Match: P0089 - Józef Surdey (95%)
   - [●] MERGE with P0089 (pre-selected)
     - Will add: death_year: 1890

3. **Marianna Surdey (b.1834)**
   - ⚠️ Multiple matches found
   - [ ] MERGE with P0007 - Marianna Surdey (85%)
   - [ ] MERGE with P0156 - Marianna Surdey (70%)
   - [●] CREATE NEW as P0526 (pre-selected - too uncertain)

**Actions:**
- [Apply Changes] - Saves all selections
- [Skip This Match] - Move to next without changes

## 🛡️ Safety Features

✅ **Review before apply** - See all changes before saving
✅ **One at a time** - Process matches incrementally
✅ **No auto-merge** - You decide everything
✅ **Evidence shown** - Understand why matches are suggested
✅ **Confidence scores** - Know how reliable each match is
✅ **Can skip** - Don't like the options? Skip and move on
✅ **Real-time updates** - See changes in graph immediately

## 📈 Progress Tracking

```
[3 of 82] ▓▓▓░░░░░░░ 4%

Progress: 3/82 matches reviewed
```

## 💾 What Gets Saved

When you click "Apply Changes":

1. **Personal data** → Added to base person
2. **Parent merges** → Relationship added to existing person
3. **Parent creates** → New person + relationship created
4. **Child merges** → Relationship added to existing person
5. **Child creates** → New person + relationship created

**All changes save to:** `data/genealogy_complete.json`

## 🔄 Workflow Tips

### Best Practices:

1. **Trust the ⭐ recommendations** - High confidence matches are usually correct
2. **Review medium confidence** - Check evidence before accepting
3. **When in doubt, create new** - Easier to merge duplicates later than to unmerge
4. **Check evidence** - Especially for same-name people
5. **Skip uncertain matches** - Come back to them later
6. **Review in batches** - Don't have to do all 82 at once

### Common Patterns:

**Same name, different generations:**
```
Jan Surdey (I)  - b.1776 - grandfather
Jan Surdey (II) - b.1832 - son of Wojciech
Jan Surdey (III)- b.1847 - grandson
```
→ Evidence will show parent names to distinguish

**Same name, different families:**
```
Marianna Surdey - daughter of Jan
Marianna Zatorska (née Surdey) - married to Wincenty
```
→ Evidence will show spouses/parents to distinguish

## 🚨 If Something Goes Wrong

### Issue: Accidentally merged wrong persons

**Solution:** Use the web interface merge tool to undo:
1. Navigate to one of the incorrectly merged persons
2. The merge tool will show it was merged
3. Can manually fix or reprocess

### Issue: Created duplicate by mistake

**Solution:** Use merge tool to combine them:
1. Click "🔗 Merge Persons"
2. Select the duplicate
3. Choose which data to keep
4. Merge and save

### Issue: Want to start over

**Solution:** Backup and revert:
```bash
# Backup current state
cp data/genealogy_complete.json data/genealogy_backup.json

# Revert to previous
cp data/genealogy_backup.json data/genealogy_complete.json

# Or reprocess from scratch
python3 process_genealogy_v2.py
```

## 📊 Expected Results

After reviewing all 82 matches:

**Estimated additions:**
- ~50 new birth/death dates
- ~40 parent relationships (mix of merge + create)
- ~80 children relationships (mix of merge + create)
- ~20-30 new persons created
- Total: ~600-650 persons (up from 522)

**Data quality improvements:**
- More complete birth/death dates
- Better parent-child connections
- Fuller family trees
- Multi-generational links

## 🎉 Benefits

✅ **No accidental duplicates** - You control everything
✅ **Full context** - See family relationships to make good decisions
✅ **Incremental** - Review at your own pace
✅ **Safe** - Can skip uncertain matches
✅ **Transparent** - See exactly what will change
✅ **Efficient** - Pre-selected recommendations speed up review

---

**System Status:** ✅ Ready to use
**Queue Status:** 82 matches ready for review
**Next Step:** Open web interface and click "Review GEDCOM Matches"
