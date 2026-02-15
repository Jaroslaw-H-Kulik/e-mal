# Focus Mode & Bug Fixes

## 🐛 Bug Fixed: "Select for Merge" Not Working

**Problem:** JavaScript syntax error - used Python docstrings (`"""`) instead of JavaScript comments

**Fixed:**
```javascript
// Before (broken):
async saveMergeLogToServer() {
    """Save merge log to server automatically"""  // ← Python syntax!

// After (fixed):
async saveMergeLogToServer() {
    // Save merge log to server automatically
```

**Result:** ✅ "Select for Merge" button now works correctly

---

## 🎯 New Feature: Focus Mode

### What It Does

**When you click on a person:**
- Shows ONLY their network
- Includes direct connections (parents, children, spouse)
- Includes secondary connections (children's godparents, etc.)
- Hides everyone else
- Automatically focuses the camera

**When you click on empty space:**
- Shows full community network
- Restores all relationships
- Fits view to show everyone

### How to Use

**Focus on a person's network:**
1. Click on any person in the graph
2. Graph automatically filters to show only their network
3. Person details appear in side panel

**Return to full view:**
- Click on empty space in the graph, OR
- Click the ✕ button in person details panel, OR
- Click "↻ Reset View" button

### What's Included in Focus Mode

**Primary connections (direct):**
- Parents
- Children
- Spouse(s)
- Siblings
- Godchildren (as godparent)
- Godparents (as godchild)
- People they witnessed with

**Secondary connections (extended):**
- Children's spouses
- Children's godparents
- Siblings' children
- Parents' other children
- Godchildren's family

**Example:**

If you click on **Jan Surdey**:

```
Visible:
├── Jan Surdey (selected) ✓
├── Marianna Surdey (wife) ✓
├── Brygida Surdey (daughter) ✓
│   ├── Szczepan Słyk (Brygida's husband) ✓
│   └── Kazimierz Łapacz (godparent of Brygida's child) ✓
├── Józef Surdey (brother) ✓
└── Wojciech Surdey (father) ✓

Hidden:
└── Unrelated persons ✗
```

### Visual Behavior

**Focused View:**
- ✅ Selected person and network visible
- ✅ All relationships between them shown
- ✅ Camera focuses on selected person
- ✅ Smooth animation
- ✅ Scale: 1.5x zoom

**Full View:**
- ✅ Everyone visible
- ✅ All community relationships
- ✅ Camera fits to show all
- ✅ Current filter maintained (All/Families/Marriages/etc.)

### Use Cases

**1. Explore a Person's Family:**
```
Click on: Brygida Surdey
See: Her parents, siblings, spouses, children, and their families
```

**2. Understand Social Connections:**
```
Click on: Kazimierz Łapacz
See: Everyone he witnessed with, his godchildren, their families
```

**3. Study Generational Networks:**
```
Click on: Patriarch Jan Surdey
See: His descendants, their spouses, extended family
```

**4. Return to Overview:**
```
Click: Empty space
See: Full community network restored
```

## 🎮 Interaction Summary

| Action | Result |
|--------|--------|
| **Click person** | Focus on their network |
| **Click empty space** | Show full network |
| **Click ✕ (close details)** | Show full network |
| **Double-click person** | Focus + highlight (old behavior) |
| **Reset View button** | Show full network + reset filters |

## 🔧 Technical Details

### Focus Algorithm

```javascript
focusOnPersonNetwork(personId) {
    1. Start with selected person
    2. Add all directly connected people
    3. For each direct connection:
        - Add their connections
        - Include edges between visible nodes
    4. Hide all other nodes/edges
    5. Focus camera on selected person
}
```

### Performance

- ✅ Fast even with large networks
- ✅ Uses Set for O(1) lookups
- ✅ Efficient edge filtering
- ✅ Smooth animations

### View Filters Work Together

Focus mode respects current view filter:

```
1. Click "Families" view
2. Click on person
3. See only: Person + family connections (no marriages/godparents)

1. Click "Witnesses" view
2. Click on person
3. See only: Person + witness connections
```

## 📋 Files Changed

**`web/editor.js`** (v5):
- Fixed: Python docstrings → JavaScript comments
- Fixed: `saveMergeLogToServer()` syntax
- Fixed: `saveDataToServer()` syntax

**`web/app.js`** (v5):
- Added: `focusOnPersonNetwork(personId)` method
- Added: `showFullNetwork()` method
- Updated: Click handler to call focus mode
- Updated: Empty space click to restore full view
- Updated: Close details to restore full view

**`web/index.html`**:
- Updated: Cache-busting to v5

## 🚀 Try It Now

1. **Hard refresh:** `Cmd+Shift+R`
2. **Test merge button:**
   - Click on person
   - Click "🔗 Select for Merge"
   - Should see notification
3. **Test focus mode:**
   - Click on Jan Surdey
   - See only his network
   - Click empty space
   - See full network restored

## 💡 Tips

**To explore family trees:**
1. Click on oldest generation person
2. See their descendants + connections
3. Click on child to see their branch
4. Click empty space to see whole family

**To understand social networks:**
1. Click "Witnesses" view
2. Click on person
3. See who they witnessed with
4. Click empty space for full witness network

**To study a specific lineage:**
1. Click patriarch/matriarch
2. Focus shows multi-generational connections
3. Click through descendants
4. Each click shows that person's extended network

---

**Version:** 3.5 (Focus Mode + Bug Fix)
**Updated:** 2026-02-15
**Bug Status:** ✅ Select for Merge working
**Feature Status:** ✅ Focus Mode active
