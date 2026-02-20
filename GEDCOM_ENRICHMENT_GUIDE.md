# GEDCOM Enrichment Guide

## ✅ Enrichment Complete!

Successfully enriched genealogical data from MyHeritage GEDCOM export (base.ged).

## 📊 Results Summary

### Data Growth
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Persons** | 490 | **683** | **+193** (+39%) |
| **Relationships** | 371 | **631** | **+260** (+70%) |
| **Events** | 308 | 308 | - |

### Enrichment Details
- ✅ **82 persons matched** between existing data and GEDCOM
- ✅ **28 birth dates added** to existing persons
- ✅ **26 death dates added** to existing persons
- ✅ **124 parent relationships added**
- ✅ **181 child relationships added**
- ✅ **193 new persons imported** from GEDCOM
- ✅ **260 new relationships created**

## 🎯 What Was Enriched

### 1. Birth/Death Dates
Existing persons missing dates were enriched from GEDCOM:
```
Jan Surdey: added death year 1856
Helena Surdey: added death year 1859
Kazimierz Łapacz: added birth year 1794
```

### 2. Parent Relationships
Found parents in GEDCOM and added relationships:
- 124 parent-child links established
- Connects existing persons to their GEDCOM parents

### 3. Children Relationships
Found children in GEDCOM for existing persons:
- 181 parent-child links established
- Direct children only (no grandchildren as requested)

### 4. New Persons
Added 193 persons from GEDCOM who weren't in original data:
- Parents of existing persons
- Children of existing persons
- Extended family members

## 📁 Files

**Input:**
- `base.ged` - MyHeritage GEDCOM export (3,075 individuals)
- `data/genealogy_complete.json` - Original data (490 persons)

**Output:**
- `data/genealogy_enriched.json` - Enriched data (683 persons)

**Script:**
- `enrich_from_gedcom.py` - Enrichment tool

## 🔍 Matching Logic

The script matched persons between datasets using:

**Primary match criteria:**
1. Exact given name match
2. Exact surname match
3. Birth year similarity (±5 years = boost score)

**Score system:**
- Base match (name): 100 points
- Birth year exact match: +50 points
- Birth year ±2 years: +30 points
- Birth year ±5 years: +10 points
- Birth year >5 years off: -20 points

**Threshold:** Only matched if score ≥ 100

**Result:** 82 high-confidence matches

## 📈 Relationship Types

**After enrichment:**
- `biological_parent`: 480 (was 196) - **+284 relationships!**
- `marriage`: 87 (unchanged - inferred from births)
- `godparent`: 64 (unchanged - from church records)

**Total:** 631 relationships

## 🚀 How to Use Enriched Data

### Option 1: Review Before Applying (Recommended)

**Review enriched data:**
```bash
# Check new persons
cat data/genealogy_enriched.json | python3 << 'EOF'
import json, sys
data = json.load(sys.stdin)
new_persons = [p for p in data['persons'].values()
               if p.get('data_quality') == 'from_gedcom']
print(f"New persons: {len(new_persons)}\n")
for p in new_persons[:20]:
    print(f"{p['given_name']} {p['surname']} "
          f"({p.get('birth_year_estimate', '?')}-{p.get('death_year_estimate', '?')})")
EOF

# Check enriched existing persons
cat data/genealogy_enriched.json | python3 << 'EOF'
import json, sys
data = json.load(sys.stdin)
for p in list(data['persons'].values())[:20]:
    if p.get('birth_year_estimate') or p.get('death_year_estimate'):
        print(f"{p.get('id')}: {p['given_name']} {p['surname']} "
              f"({p.get('birth_year_estimate', '?')}-{p.get('death_year_estimate', '?')})")
EOF
```

**If satisfied, apply:**
```bash
cp data/genealogy_enriched.json data/genealogy_complete.json
```

### Option 2: Apply Immediately

```bash
cp data/genealogy_enriched.json data/genealogy_complete.json
```

### Option 3: Keep Both

Keep enriched as separate dataset:
```bash
# Original stays: data/genealogy_complete.json
# Enriched at: data/genealogy_enriched.json

# Use enriched in web interface:
cd web
ln -sf ../data/genealogy_enriched.json ../data/genealogy_complete.json
```

## 🌐 View in Web Interface

After applying enriched data:

```bash
# Start server
python3 server.py

# Open browser
# http://localhost:8001/web/

# Hard refresh
# Cmd+Shift+R
```

**What you'll see:**
- 193 new persons in network
- Many more parent-child connections
- More complete family trees
- Birth/death dates for more persons

## 🔍 Verification Queries

**Check specific person enrichment:**
```bash
cat data/genealogy_enriched.json | python3 << 'EOF'
import json, sys
data = json.load(sys.stdin)

# Find Jan Surdey
jan = next((p for p in data['persons'].values()
           if p['given_name'] == 'Jan' and p['surname'] == 'Surdey'), None)

if jan:
    print(f"Jan Surdey ({jan['id']}):")
    print(f"  Birth: {jan.get('birth_year_estimate', 'Unknown')}")
    print(f"  Death: {jan.get('death_year_estimate', 'Unknown')}")

    # Find relationships
    parents = [r for r in data['relationships'].values()
              if r['to_person'] == jan['id'] and r['type'] == 'biological_parent']
    print(f"  Parents: {len(parents)}")

    children = [r for r in data['relationships'].values()
               if r['from_person'] == jan['id'] and r['type'] == 'biological_parent']
    print(f"  Children: {len(children)}")
EOF
```

**Find persons with most children:**
```bash
cat data/genealogy_enriched.json | python3 << 'EOF'
import json, sys
from collections import Counter

data = json.load(sys.stdin)

# Count children per person
children_count = Counter()
for r in data['relationships'].values():
    if r['type'] == 'biological_parent':
        children_count[r['from_person']] += 1

# Top 10 parents
print("Persons with most children:")
for person_id, count in children_count.most_common(10):
    p = data['persons'][person_id]
    print(f"  {p['given_name']} {p['surname']}: {count} children")
EOF
```

**List new persons by surname:**
```bash
cat data/genealogy_enriched.json | python3 << 'EOF'
import json, sys
from collections import defaultdict

data = json.load(sys.stdin)

new_persons = [p for p in data['persons'].values()
               if p.get('data_quality') == 'from_gedcom']

by_surname = defaultdict(list)
for p in new_persons:
    by_surname[p['surname']].append(p)

print("New persons by surname:")
for surname in sorted(by_surname.keys()):
    print(f"\n{surname}: {len(by_surname[surname])} persons")
    for p in by_surname[surname][:3]:
        print(f"  {p['given_name']} "
              f"({p.get('birth_year_estimate', '?')}-{p.get('death_year_estimate', '?')})")
    if len(by_surname[surname]) > 3:
        print(f"  ... and {len(by_surname[surname])-3} more")
EOF
```

## ⚙️ Re-run Enrichment

If you update base.ged or want to re-enrich:

```bash
python3 enrich_from_gedcom.py
```

**The script:**
1. Parses base.ged again
2. Loads current data/genealogy_complete.json
3. Matches and enriches
4. Exports to data/genealogy_enriched.json

**Note:** Always backs up to genealogy_enriched.json first for review.

## 🎯 Matching Strategy

**Why 82 matches out of 490?**

The script uses strict matching (exact name + birth year similarity) to avoid false positives.

**Reasons for non-matches:**
- Name spelling variations (Marianna vs Maria)
- Maiden names vs married names
- Birth year estimates off by >5 years
- Persons not in GEDCOM file

**To improve matches:**
- Manually review genealogy_enriched.json
- Use merge tool in web interface for duplicates
- Update birth year estimates for better matching

## 📋 Quality Indicators

**Person data quality field:**
- `from_gedcom` - Newly added from GEDCOM
- (no field) - Original person, may be enriched

**Relationship evidence:**
- `gedcom_import` - From GEDCOM enrichment
- Event IDs - From church records

## 🔄 Integration with Existing Workflow

**Enriched data works with:**
- ✅ Merge tool (merge duplicates as usual)
- ✅ Edit tool (edit person details)
- ✅ Focus mode (click person to see network)
- ✅ Auto-persist (changes saved automatically)
- ✅ Witness relationships (displayed on graph)

**Reprocessing:**
```bash
# If you reprocess base.md:
python3 process_genealogy_v2.py

# Then re-enrich from GEDCOM:
python3 enrich_from_gedcom.py

# Apply enriched data:
cp data/genealogy_enriched.json data/genealogy_complete.json
```

## 🎁 Benefits

**Before enrichment:**
- 490 persons
- Limited parent-child links
- Many missing dates
- Incomplete family trees

**After enrichment:**
- ✅ 683 persons (+39%)
- ✅ 480 parent-child links (was 196)
- ✅ 28 additional birth dates
- ✅ 26 additional death dates
- ✅ Much more complete family trees
- ✅ Multi-generational connections visible

## 🚨 Important Notes

**New person IDs:**
- Start at P5001 to avoid conflicts
- Original persons keep their IDs (P0001-P0490)

**No grandchildren added:**
- As requested, only direct children
- Grandchildren would require separate run

**Relationships are one-way:**
- `biological_parent` goes from parent to child
- Query both directions to find siblings

**GEDCOM source:**
- MyHeritage export (3,075 individuals)
- Your extended family tree
- May include distant relatives

---

**Enrichment Date:** 2026-02-15
**Source:** base.ged (MyHeritage)
**Tool:** enrich_from_gedcom.py
**Output:** data/genealogy_enriched.json

**Total Enrichment:** +193 persons, +260 relationships, +54 dates
