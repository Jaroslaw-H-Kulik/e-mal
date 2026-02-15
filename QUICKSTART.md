# Quick Start Guide

## Overview

This project transforms Polish genealogical records (1826-1914) into a structured, queryable database.

## Files

- `base.md` - Original source data (Polish genealogical records)
- `process_genealogy.py` - Parser (run first)
- `query_genealogy.py` - Query tool
- `validate_data.py` - Data quality checker
- `data/` - Output JSON files

## Quick Start

### 1. Process the Data

```bash
python3 process_genealogy.py
```

**Output:**
- 621 persons
- 298 events (178 births, 116 deaths, 4 marriages)
- 315 relationships
- Files in `data/` directory

### 2. Query the Database

```bash
python3 query_genealogy.py
```

**Shows examples of:**
- Finding persons by name
- Getting family information
- Finding relationships between people

### 3. Validate Data Quality

```bash
python3 validate_data.py
```

**Checks:**
- Data integrity
- Temporal consistency
- Completeness metrics
- Interesting patterns

## Python API Examples

### Find a Person

```python
from query_genealogy import GenealogyQuery

query = GenealogyQuery('data/')

# Search by name
matches = query.find_person_by_name("Jan Surdey")
for person in matches:
    print(f"{person['id']}: {person['given_name']} {person['surname']}")
```

### Get Family Information

```python
# Get parents
parents = query.get_parents("P0001")
print(f"Father: {parents['father']}")
print(f"Mother: {parents['mother']}")

# Get children
children = query.get_children("P0001")
for child_id in children:
    child = query.get_person(child_id)
    print(f"Child: {child['given_name']}")

# Get siblings
siblings = query.get_siblings("P0001")
```

### Find Relationships

```python
# Find relationship path
path = query.find_relationship_path("P0001", "P0110")

# Describe relationship
description = query.describe_relationship("P0001", "P0110")
print(description)
# Output: "Jan Surdey (child) → Brygida Surdey (parent) → Szczepan Słyk"
```

### Get Complete Summary

```python
# Print detailed person summary
query.print_person_summary("P0001")
```

**Output includes:**
- Full name, birth/death years
- Parents
- Spouse(s)
- Children with birth years
- Siblings
- All events involving this person

### Search by Surname

```python
# Find all persons with surname "Surdey"
surdeys = query.search_by_surname("Surdey")
print(f"Found {len(surdeys)} persons")

for person in surdeys:
    print(f"{person['given_name']} (b.{person.get('birth_year_estimate', '?')})")
```

### Get Events

```python
# Get all events for a person
events = query.get_all_events_for_person("P0001")

for event in events:
    print(f"{event['date']['year']}: {event['type']} - {event['original_text'][:50]}...")
```

## Example Queries

### "Who are the children of Brygida Słyk?"

```python
brygidas = query.find_person_by_name("Brygida Słyk")
brygida_id = brygidas[0]['id']

children = query.get_children(brygida_id)
for child_id in children:
    child = query.get_person(child_id)
    print(f"{child['given_name']} {child['surname']} (b.{child.get('birth_year_estimate', '?')})")
```

### "What's the relationship between Person A and Person B?"

```python
person_a = "P0001"  # Jan Surdey
person_b = "P0110"  # Szczepan Słyk

relationship = query.describe_relationship(person_a, person_b)
print(relationship)
```

### "Who were the most frequent godparents?"

```python
from collections import defaultdict

godparent_counts = defaultdict(int)
for rel in query.relationships.values():
    if rel['type'] == 'godparent':
        godparent_counts[rel['from_person']] += 1

# Top 5
for pid, count in sorted(godparent_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
    person = query.get_person(pid)
    print(f"{person['given_name']} {person['surname']}: {count} times")
```

### "Find all events in 1855"

```python
year = 1855
events_1855 = [e for e in query.events.values() if e['date']['year'] == year]

print(f"Events in {year}: {len(events_1855)}")
for event in events_1855:
    print(f"{event['type']}: {event['original_text'][:60]}...")
```

## Data Files

### persons.json
```json
{
  "P0001": {
    "id": "P0001",
    "given_name": "Jan",
    "surname": "Surdey",
    "gender": "M",
    "birth_year_estimate": 1782,
    "death_year_estimate": 1857
  }
}
```

### events.json
```json
{
  "E0001": {
    "id": "E0001",
    "type": "birth",
    "date": {"year": 1826},
    "location": {"parish": "Grzybowa Góra"},
    "child": "P0003",
    "father": "P0001",
    "mother": "P0002"
  }
}
```

### relationships.json
```json
{
  "R0001": {
    "id": "R0001",
    "type": "biological_parent",
    "from_person": "P0001",
    "to_person": "P0003",
    "role": "father",
    "evidence": ["E0001"]
  }
}
```

## Next Steps

1. **Manual Disambiguation**: Review `data/disambiguation_report.json` for duplicate person candidates

2. **Import to Graph Database**:
   ```cypher
   // Neo4j example
   LOAD CSV WITH HEADERS FROM 'file:///persons.json' AS row
   CREATE (p:Person {id: row.id, name: row.given_name + ' ' + row.surname})
   ```

3. **Visualization**: Use the relationship data to create family trees or network graphs

4. **Export**: Convert to GEDCOM format for genealogy software

## Troubleshooting

### "Module not found"
Make sure you're in the project directory:
```bash
cd /Users/kulikj01/Desktop/git/mein/mal
```

### "File not found"
Run `process_genealogy.py` first to generate the data files.

### "Person not found"
Check the person ID. Use `find_person_by_name()` to search.

## Support

See `README.md` for detailed documentation.

See `IMPLEMENTATION_SUMMARY.md` for technical details.

---

**Quick Reference**

| Task | Command |
|------|---------|
| Parse data | `python3 process_genealogy.py` |
| Query data | `python3 query_genealogy.py` |
| Validate | `python3 validate_data.py` |
| Find person | `query.find_person_by_name("Name")` |
| Get family | `query.get_children(person_id)` |
| Find relation | `query.describe_relationship(a, b)` |
