# Genealogy Editor Guide

## 🎉 New Features Added!

### 1. **Improved Gender Classification** ✅
- **100% of persons now have gender assigned**
- Uses Polish naming rules: names ending in 'a' are typically female
- Automatic classification during data processing

### 2. **Edit Person Information** ✏️
- Click on any person in the network
- Click the "Edit" button in the person details panel
- Modify:
  - Given name
  - Surname
  - Maiden name
  - Gender
  - Birth year (estimate)
  - Death year (estimate)
  - Occupations
- Changes are tracked and can be exported

### 3. **Merge Duplicate Persons** 🔗
- Identify duplicates (e.g., Brygida Kruk = Brygida Słyk = Brygida Surdey)
- Two ways to merge:

  **Method A: From Person Details**
  1. Click on first person
  2. Click "Select for Merge"
  3. Click on second person
  4. Click "Select for Merge"
  5. Toolbar shows "Merge Persons" button
  6. Review and confirm merge

  **Method B: From Toolbar**
  1. Click "🔗 Merge Persons" in toolbar
  2. Click first person → "Select"
  3. Click second person → "Select"
  4. Review both persons
  5. Click "Merge Persons"
  6. Confirm action

- **What happens during merge:**
  - Primary person is kept
  - All relationships point to primary person
  - All events reference primary person
  - Secondary person is removed
  - Change is logged

### 4. **Track and Export Changes** 💾
- All edits and merges are tracked
- Click "📋 View Changes" to see history
- Click "💾 Export Data" to download:
  - Updated persons.json
  - Updated events.json
  - Updated relationships.json
  - Complete change log
  - Timestamp of export

## 🎯 Common Use Cases

### Fix Duplicate Person (Brygida Example)

**Problem:** Brygida appears as multiple persons:
- Brygida Surdey (birth name, P0003)
- Brygida Słyk (married name, after marrying Szczepan)
- Brygida Kruk (second marriage, after marrying Jędrzej)

**Solution:**

1. **Find all Brygidas:**
   - Search for "Brygida"
   - Note their person IDs

2. **Determine primary:**
   - Usually the earliest (birth) record
   - Brygida Surdey (P0003) is primary

3. **Merge first duplicate:**
   - Click on Brygida Surdey (P0003)
   - Click "Select for Merge"
   - Search and click on Brygida Słyk
   - Click "Select for Merge"
   - Click "🔗 Merge Persons" in toolbar
   - Review and confirm
   - Brygida Słyk now merged into Brygida Surdey

4. **Merge second duplicate:**
   - Repeat for Brygida Kruk
   - Merge into Brygida Surdey

5. **Update maiden name if needed:**
   - Click on merged Brygida Surdey
   - Click "Edit"
   - Update surname to reflect current status
   - Add note about marriages

6. **Export changes:**
   - Click "💾 Export Data"
   - Save the file

### Correct Wrong Information

**Example:** Fix birth year

1. Click on person
2. Click "Edit"
3. Update birth year
4. Click "Save Changes"
5. Network updates automatically
6. Change is logged

### Bulk Corrections

**Example:** Merge multiple Jans

1. Open "🔗 Merge Persons"
2. For each Jan:
   - Search and identify
   - Determine which to keep
   - Merge one by one
3. Track all changes
4. Export when done

## 📊 Data Management

### Viewing Changes
- Click "📋 View Changes"
- See list of all edits and merges
- Each change shows:
  - Type (edit/merge)
  - Person ID(s)
  - Timestamp
  - Old and new data

### Exporting Data
- Click "💾 Export Data"
- Downloads JSON file with:
  - All current persons
  - All events (updated)
  - All relationships (updated)
  - Complete change log
- File format: `genealogy_edited_[timestamp].json`

### Importing Back
To use the edited data:
1. Export your changes
2. Backup original `data/` folder
3. Replace `data/genealogy_complete.json` with exported file
4. Refresh browser
5. Changes persist

## 🚨 Important Notes

### Before Merging:
- ✅ **DO:** Verify it's the same person
- ✅ **DO:** Check birth/death years match
- ✅ **DO:** Look at family relationships
- ❌ **DON'T:** Merge based on name alone
- ❌ **DON'T:** Merge different generations

### Merge is Permanent:
- Changes are immediate
- Secondary person is removed
- All references updated
- Can't undo (except by reloading original data)
- **Always export before major changes!**

### Best Practices:
1. **Start with obvious duplicates**
   - Same person with different married names
   - Spelling variations of same person

2. **Work systematically**
   - One family at a time
   - Document your decisions
   - Export after each family

3. **Keep backups**
   - Export original data first
   - Export after each major change
   - Keep multiple versions

4. **Verify relationships**
   - Check parent-child links
   - Verify spouse connections
   - Confirm witness/godparent roles

## 🔍 Tips & Tricks

### Finding Duplicates:
1. Search by surname (filter)
2. Look for same given name
3. Check birth years (within 5 years)
4. Compare family members
5. Look at event dates

### Identifying Same Person:
- **Strong evidence:**
  - Same parents
  - Same spouse
  - Same children
  - Same birth year (±2 years)
  - Same house number
  - Witness in same events

- **Weak evidence:**
  - Same first name only
  - Similar age
  - Same village

### Polish Name Changes:
- Women take husband's surname
- "z d." = maiden name
- Multiple marriages = multiple surnames
- Use maiden name in merge notes

## 🎨 UI Features

### Person Details Panel:
- **Edit button** (✏️) - Opens edit form
- **Select for Merge** (🔗) - Adds to merge queue

### Toolbar:
- **🔗 Merge Persons** - Opens merge interface
- **📋 View Changes** - Shows change history
- **💾 Export Data** - Downloads current state

### Notifications:
- ✅ Green = Success
- ⚠️ Orange = Warning
- ❌ Red = Error
- ℹ️ Blue = Info

### Modals:
- Click outside to close
- X button to close
- Esc key to close (coming soon)

## 📝 Example Workflow

### Complete Family Correction:

1. **Identify family:** Surdey family
2. **Search:** "Surdey"
3. **Find duplicates:**
   - Jan Surdey appears 4 times
   - Check birth years
   - Jan (b.1782) - patriarch
   - Jan (b.1794) - different person
   - Jan (b.1832) - son
   - Jan (b.1855) - grandson

4. **Verify generations:**
   - Check parent-child links
   - Confirm spouses
   - Review event timeline

5. **No merge needed** - different persons

6. **Edit for clarity:**
   - Add disambiguating notes
   - Correct any wrong years
   - Update occupations

7. **Move to women:**
   - Brygida Surdey → Słyk → Kruk
   - **Merge these!**

8. **Export changes**

## 🆘 Troubleshooting

### "Person not found" error:
- Refresh page
- Check console (F12)
- Verify person ID exists

### Merge button disabled:
- Need exactly 2 persons selected
- Select one more person

### Changes not saving:
- Check browser console
- Ensure no errors
- Export to save permanently

### Network not updating:
- Hard refresh (Cmd+Shift+R)
- Clear browser cache
- Restart server

## 🎓 Advanced Features

### Keyboard Shortcuts (coming soon):
- `E` - Edit selected person
- `M` - Select for merge
- `Esc` - Close modal
- `Ctrl+S` - Save changes

### Batch Operations (coming soon):
- Merge multiple at once
- Bulk edit fields
- Find similar persons
- Auto-suggest merges

### Collaboration (future):
- Share changes
- Review system
- Conflict resolution
- Multi-user editing

---

## 🚀 Quick Start

1. **Open web interface:** http://localhost:8001/web/
2. **Hard refresh:** Cmd+Shift+R
3. **Find Brygida:** Search "Brygida"
4. **Click Edit:** Try editing her info
5. **Try Merge:** Select two Brygidas for merge
6. **Export:** Save your changes!

---

**Version:** 1.0
**Updated:** 2026-02-14
**Gender Classification:** 100% (291 Male, 201 Female, 0 Unknown)
