# Genealogical Data Structuring - Project Summary

## Overview

This project transforms unstructured Polish genealogical records from the parish of Grzybowa Góra (1826-1914) into a structured JSON format suitable for graph database import and relationship analysis.

## Source Data

**Input File:** `base.md`
- Time period: 1826-1914
- Parish: Grzybowa Góra
- Record types: Birth (narodziny/urodzenia), Death (zejścia), Marriage (śluby)
- Language: Polish (historical)

## Output Files

All output files are located in the `data/` directory:

### Core Data Files

1. **`genealogy_complete.json`** - Combined file containing all data
   - Persons registry
   - Events catalog
   - Relationships graph
   - Metadata

2. **`persons.json`** - Person registry (621 persons)
   - Unique ID for each person (P0001, P0002, etc.)
   - Names (given name, surname, maiden name)
   - Gender (M/F/U for unknown)
   - Birth/death year estimates
   - Occupations
   - Confidence levels

3. **`events.json`** - Events catalog (298 events)
   - Unique ID for each event (E0001, E0002, etc.)
   - Event type: birth, death, marriage
   - Date information (year, month, day when available)
   - Location (house number, parish)
   - Participants (parents, children, deceased, spouses)
   - Witnesses and godparents
   - Original Polish text preserved

4. **`relationships.json`** - Relationship graph (315 relationships)
   - Unique ID for each relationship (R0001, R0002, etc.)
   - Relationship types:
     - `biological_parent` (father/mother)
     - `marriage` (spouse)
     - `godparent` (godfather/godmother)
   - Evidence references (event IDs)
   - Confidence levels

### Analysis Files

5. **`statistics.json`** - Summary statistics
   - Total counts (persons, events, relationships)
   - Breakdown by type
   - Most common surnames
   - Data completeness metrics

6. **`disambiguation_report.json`** - Duplicate detection
   - Names with multiple person IDs
   - Candidate information for disambiguation
   - 32 names requiring disambiguation

## Data Structure

### Person Schema

```json
{
  "id": "P0001",
  "given_name": "Jan",
  "surname": "Surdey",
  "maiden_name": "Minda",
  "gender": "M",
  "birth_year_estimate": 1782,
  "death_year_estimate": 1857,
  "confidence": "high",
  "occupations": ["młynarz"],
  "disambiguation_notes": "Jan Surdey age 50 in 1826"
}
```

### Event Schema (Birth)

```json
{
  "id": "E0001",
  "type": "birth",
  "date": {
    "year": 1826,
    "month": 2,
    "day": 15,
    "certainty": "exact"
  },
  "location": {
    "house_number": "13",
    "village": null,
    "parish": "Grzybowa Góra"
  },
  "source_line": 2,
  "original_text": "Jan Surdey i Helena z d. Minda...",
  "child": "P0003",
  "father": "P0001",
  "mother": "P0002",
  "witnesses": ["P0004", "P0005"],
  "godparents": ["P0006", "P0007"]
}
```

### Relationship Schema

```json
{
  "id": "R0001",
  "type": "biological_parent",
  "from_person": "P0001",
  "to_person": "P0003",
  "role": "father",
  "evidence": ["E0001"],
  "confidence": "high"
}
```

## Statistics Summary

### Current Parsing Results

- **Total Persons:** 621
- **Total Events:** 298
  - Births: 178
  - Deaths: 116
  - Marriages: 4
- **Total Relationships:** 315
  - Biological parent: 173
  - Godparent: 138
  - Marriage: 4

### Gender Distribution

- Male: 51
- Female: 41
- Unknown: 529 (many witnesses, godparents lack gender indicators)

### Data Completeness

- Persons with birth year estimate: 257 (41%)
- Persons with death year estimate: 101 (16%)
- Persons with occupations: 25 (4%)

### Most Common Surnames

1. Unknown: 93 (children/women before surname extraction)
2. Kiełek: 23
3. Surdey: 18
4. Drożdż: 18
5. Głód: 12
6. Słyk: 11
7. Myszka: 11
8. Niewczas: 9
9. Łęcki: 9
10. Kozik: 9

## Usage

### Processing the Data

```bash
python3 process_genealogy.py
```

This reads `base.md` and generates all JSON files in the `data/` directory.

### Querying the Data

```bash
python3 query_genealogy.py
```

Example queries:
- Find person by name
- Get parents, children, siblings, spouse
- Find relationship path between two people
- Get all events for a person
- Search by surname

### Python API Example

```python
from query_genealogy import GenealogyQuery

query = GenealogyQuery('data/')

# Find person
matches = query.find_person_by_name("Brygida Słyk")

# Get children
children = query.get_children("P0001")

# Find relationship
path = query.find_relationship_path("P0001", "P0003")
relationship = query.describe_relationship("P0001", "P0003")

# Print person summary
query.print_person_summary("P0001")
```

## Known Issues and Disambiguation Needs

### Duplicate Persons

The system identified **32 names with multiple person IDs** that require disambiguation:

**High Priority:**
- **Jan Surdey** - 4 instances (b.1782, b.1794, b.1875, b.1881)
- **Wawrzyniec Surdey** - 3 instances (b.1813, b.1829, b.1854)
- **Wincenty Zatorski** - 3 instances (b.1804, b.1830, b.1824)

**Common Names:**
- Marianna Unknown - 4 instances (likely different women)
- Jan Unknown - 3 instances
- Agnieszka Unknown - 3 instances

### Data Quality Notes

1. **"Unknown" Surnames:** Many persons have "Unknown" as surname because:
   - Women's surnames before marriage extraction needs improvement
   - Children mentioned only by first name
   - Witnesses listed with abbreviated names

2. **Gender Unknown:** 529 persons (85%) have unknown gender because:
   - Witnesses and godparents often lack gender indicators
   - Historical Polish naming doesn't always indicate gender clearly
   - Parser needs improvement to infer from context

3. **Missing Birth/Death Years:** Only 41% have birth year estimates because:
   - Ages not always mentioned in records
   - First/last appearances don't always have age information
   - Cross-referencing between events needs enhancement

## Future Enhancements

### Phase 2: Improved Disambiguation
- Interactive disambiguation tool
- Machine learning-based person matching
- Cross-event age consistency checking
- Generational cohort analysis

### Phase 3: Graph Database Import
- Neo4j import scripts
- Cypher query examples
- Graph visualization

### Phase 4: Web Interface
- Search and browse interface
- Family tree visualization
- Timeline view
- Export to GEDCOM format

## Technical Details

### Parser Features

The parser (`process_genealogy.py`) includes:
- Multi-format date parsing
- Polish text handling (UTF-8)
- Age extraction from parenthetical text
- Maiden name extraction (z d. pattern)
- Occupation detection
- Relationship inference from roles
- Witness and godparent tracking

### Disambiguation Strategy

Current automatic merging rules:
1. Same name + birth year within 5 years → likely same person
2. Same name + same spouse → same person
3. Same name + same parents → same person

Requires manual review:
- Multiple persons with same name and distant time periods
- Insufficient context to determine uniqueness

## Example Queries

### Find all children of a specific couple

```python
# Jan Surdey (P0001) and Helena (P0002)
children = query.get_children("P0001")
for child_id in children:
    child = query.get_person(child_id)
    print(f"{child['given_name']} {child['surname']}")
```

### Find relationship between two people

```python
relationship = query.describe_relationship("P0001", "P0110")
print(relationship)
# Output: Jan Surdey (child) → Brygida Surdey (parent) → Szczepan Słyk
```

### Get complete family tree

```python
query.print_person_summary("P0001")
# Outputs: parents, spouse, children, siblings, events
```

## Data Validation

### Integrity Checks Performed

- ✅ All person IDs referenced in events exist
- ✅ All person IDs referenced in relationships exist
- ✅ No temporal impossibilities (parent younger than child)
- ✅ Birth/death years consistent with event years
- ✅ Original text preserved for all events

### Known Data Gaps

- Some records have "X" or "NN" for unknown names
- Some house numbers are "?" or "X"
- Some dates only have year (no month/day)
- Some events lack witnesses (damaged records)

## Contributing

To improve the data quality:

1. Review `disambiguation_report.json`
2. Manually verify duplicate candidates
3. Update person IDs in events where disambiguation is clear
4. Add notes to `disambiguation_notes` field
5. Submit corrections

## License

Data is historical public record. Parser code is available for genealogical research purposes.

## Contact

For questions about the data structure or to report issues, please open an issue in the repository.

---

**Last Updated:** 2026-02-14
**Parser Version:** 1.0
**Data Version:** 2026-02-14
