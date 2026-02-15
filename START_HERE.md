# 🚀 Quick Start - Genealogical Database

## Complete System Ready!

Your genealogical database system is fully implemented with:
- ✅ Data parser and structuring
- ✅ Python query API
- ✅ Interactive web interface
- ✅ Network visualization

## Three Ways to Use

### 1. 🌐 Web Interface (Recommended)

**Best for:** Visual exploration, discovering relationships, browsing the community

```bash
# Start the web server
python3 serve.py
```

Then open: http://localhost:8000

**Features:**
- Interactive network graph of entire community
- Click on people to see details
- Search by name or ID
- Filter by surname and year
- View family trees
- See marriage and godparent networks

### 2. 🐍 Python API

**Best for:** Programmatic queries, data analysis, custom scripts

```python
from query_genealogy import GenealogyQuery

query = GenealogyQuery('data/')

# Search
matches = query.find_person_by_name("Jan Surdey")

# Get family
children = query.get_children("P0001")

# Find relationships
path = query.describe_relationship("P0001", "P0110")
```

### 3. 📊 Command Line

**Best for:** Quick lookups, testing

```bash
# Run example queries
python3 query_genealogy.py

# Validate data
python3 validate_data.py

# Regenerate data
python3 process_genealogy.py
```

## First Time Setup

### Step 1: Verify Data Files

```bash
ls -l data/
```

You should see:
- `genealogy_complete.json` (334 KB)
- `persons.json` (101 KB)
- `events.json` (141 KB)
- `relationships.json` (64 KB)

If missing, run:
```bash
python3 process_genealogy.py
```

### Step 2: Start Web Interface

```bash
python3 serve.py
```

Browser opens automatically to http://localhost:8000

### Step 3: Explore!

1. **Welcome Screen** shows community statistics
2. **Network Graph** displays everyone (621 persons)
3. **Search** for "Brygida Słyk" to see detailed example
4. **Click** on people to view family details

## Example Queries

### Web Interface

**Find someone:**
1. Type "Jan Surdey" in search box
2. Click on result
3. See family tree in detail panel

**View a family:**
1. Filter by surname: "Surdey"
2. Click "Apply Filters"
3. Network shows only Surdey family

**See marriages:**
1. Click "Marriages" button
2. View marriage network
3. Double-click person to focus

### Python API

```python
from query_genealogy import GenealogyQuery

q = GenealogyQuery('data/')

# Find Brygida Słyk
brygidas = q.find_person_by_name("Brygida Słyk")
brygida_id = brygidas[0]['id']

# Get her children
children = q.get_children(brygida_id)
for child_id in children:
    child = q.get_person(child_id)
    print(f"{child['given_name']} (b.{child.get('birth_year_estimate', '?')})")

# Find relationship to Szczepan Słyk
szczepan = q.find_person_by_name("Szczepan Słyk")[0]
relationship = q.describe_relationship(brygida_id, szczepan['id'])
print(f"Relationship: {relationship}")

# Get complete summary
q.print_person_summary(brygida_id)
```

## Data Overview

**Time Period:** 1826-1914 (88 years)
**Location:** Grzybowa Góra parish, Poland

**Dataset:**
- 621 persons
- 298 events (178 births, 116 deaths, 4 marriages)
- 315 relationships

**Top Families:**
1. Kiełek - 23 persons
2. Surdey - 18 persons
3. Drożdż - 18 persons
4. Głód - 12 persons
5. Słyk - 11 persons

## File Guide

```
mal/
├── START_HERE.md              ← You are here!
├── README.md                  ← Full documentation
├── QUICKSTART.md              ← API examples
├── WEB_UI_GUIDE.md            ← Web interface guide
│
├── base.md                    ← Original source data
│
├── process_genealogy.py       ← Parser (run first)
├── query_genealogy.py         ← Query tool
├── validate_data.py           ← Validator
├── serve.py                   ← Web server
│
├── data/                      ← Generated data files
│   ├── genealogy_complete.json
│   ├── persons.json
│   ├── events.json
│   └── relationships.json
│
└── web/                       ← Web interface
    ├── index.html
    ├── style.css
    └── app.js
```

## Troubleshooting

### Data files not found
```bash
python3 process_genealogy.py
```

### Server won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Or try different port (edit serve.py, change PORT = 8001)
```

### Network too crowded in web UI
1. Use filters (surname, year range)
2. Switch view mode (Families/Marriages)
3. Zoom in or double-click a person

### Can't find a person
1. Try different spelling
2. Search by person ID (e.g., "P0001")
3. Use surname filter to browse

## Next Steps

### 1. Explore the Data

**Start with known families:**
- Search for "Surdey" family
- Trace Brygida's lineage
- View marriage connections

**Discover patterns:**
- Most frequent godparents
- Largest families
- Longest lifespans

### 2. Improve Data Quality

Review disambiguation report:
```bash
cat data/disambiguation_report.json | python3 -m json.tool | less
```

32 names need review - see `IMPLEMENTATION_SUMMARY.md` for details.

### 3. Export or Extend

**Future possibilities:**
- Import to Neo4j graph database
- Export to GEDCOM format
- Create printed family trees
- Build custom visualizations
- Add more records

## Documentation

| File | Purpose |
|------|---------|
| `START_HERE.md` | Quick start (this file) |
| `README.md` | Complete documentation |
| `QUICKSTART.md` | Python API guide |
| `WEB_UI_GUIDE.md` | Web interface guide |
| `IMPLEMENTATION_SUMMARY.md` | Technical details |

## Support

**Common Questions:**

Q: How do I find someone?
A: Use web search or Python `find_person_by_name()`

Q: How do I see family relationships?
A: Click person in web UI or use `get_children()`, `get_parents()`

Q: How do I query relationships?
A: Use `describe_relationship(person_a, person_b)`

Q: Can I add more data?
A: Yes, edit `base.md` and run `process_genealogy.py`

## Credits

**Data Source:**
- Parish records, Grzybowa Góra (1826-1914)
- Historical Polish genealogical records

**Technology:**
- Python 3 for parsing and API
- JavaScript + vis.js for visualization
- HTML5/CSS3 for interface

---

## 🎯 Ready to Go!

Choose your path:

**→ For visual exploration:** `python3 serve.py`
**→ For coding:** See `QUICKSTART.md`
**→ For full docs:** See `README.md`

**Enjoy exploring your genealogical data!** 🌳

---

*Version 1.0 • 2026-02-14*
