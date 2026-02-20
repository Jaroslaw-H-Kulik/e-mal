# Frontend Migration to New Data Model - COMPLETE

## Migration Date
February 18, 2026

## Overview
Successfully migrated web/app.js, web/editor.js, and web/enrichment.js to work with the new event-centric data model (genealogy_new_model.json).

## Changes Summary

### web/app.js (PRIMARY FILE)
✅ Added helper functions:
- `formatFlexibleDate(dateObj)` - Formats flexible date objects
- `extractYear(dateObj)` - Extracts year from date object
- `getFullName(person)` - Returns formatted full name

✅ Updated data loading:
- Now loads from `genealogy_new_model.json`
- Added `places`, `event_participations`, `family_relationships`

✅ Field name mappings:
- `given_name` → `first_name`
- `surname` → `last_name`
- `birth_year_estimate` → `birth_date` (object)
- `death_year_estimate` → `death_date` (object)
- `occupations` (array) → `occupation` (string)
- `relationships` → `family_relationships`

✅ Relationship structure changes:
- `from_person/to_person` → `person_1_id/person_2_id`
- `type: 'biological_parent'` → `type: 'parent'` (mapped to display as 'biological_parent')
- `type: 'marriage'` → `type: 'spouse'` (mapped to display as 'marriage')

✅ Event handling:
- Now uses `event_participations` instead of direct event fields
- Built participation map for efficient lookups
- Witness edges created from participation data

✅ Updated methods:
- `setupUI()` - Uses `last_name`
- `createNetwork()` - Uses new date extraction and participations
- `getPersonTooltip()` - Uses helper functions
- `handleSearch()` - Uses `last_name` and helper functions
- `displaySearchResults()` - Uses helper functions
- `showPersonDetails()` - Uses `formatFlexibleDate()` and `getFullName()`
- `getFamily()` - Uses `family_relationships` with new structure
- `getGodrelations()` - Uses `event_participations` instead of relationships
- `getPersonEvents()` - Uses `event_participations` to find events
- `applyFilters()` - Uses `last_name` and `extractYear()`
- `updateStats()` - Uses `family_relationships` and `last_name`

### web/editor.js (EDITING FUNCTIONS)
✅ Updated all field references:
- `person.given_name` → `person.first_name` (all occurrences)
- `person.surname` → `person.last_name` (all occurrences)
- `person.birth_year_estimate` → `this.app.extractYear(person.birth_date)` (all occurrences)
- `person.death_year_estimate` → `this.app.extractYear(person.death_date)` (all occurrences)

✅ Updated `openEditModal()`:
- Loads values using new field names
- Extracts years from date objects

✅ Updated `savePersonEdit()`:
- Saves data in new structure
- Creates date objects with `{year, month, day, circa}`
- Uses `occupation` string instead of `occupations` array
- Updates network labels using helper functions

✅ Updated merge operations:
- `executeMerge()` updates `family_relationships` (not `relationships`)
- Uses `person_1_id/person_2_id` instead of `from_person/to_person`
- Updates `event_participations` instead of event fields

✅ Updated `saveDataToServer()`:
- Includes all new data structures: `places`, `event_participations`, `family_relationships`

✅ Updated relationship creation:
- Uses `family_relationships` structure
- Maps types for display (parent → biological_parent, spouse → marriage)
- Uses `person_1_id/person_2_id` in edges

✅ Updated node creation:
- Uses `getFullName()` helper
- Extracts years from date objects

### web/enrichment.js (ENRICHMENT REVIEW)
✅ Updated `renderPersonData()`:
- Handles both date objects and simple year values
- Uses `formatFlexibleDate()` for date objects
- Supports flexible date display

✅ Updated `renderRelative()`:
- Uses `app.getFullName(person)` for consistent naming

## Testing Checklist

Before considering this migration complete, verify:

### Basic Functionality
- [ ] Application loads without errors
- [ ] Network displays with correct person names
- [ ] Birth/death years display correctly in nodes
- [ ] Clicking person shows details panel

### Person Details
- [ ] Full name displays correctly
- [ ] Dates show in flexible format (with "circa" if applicable)
- [ ] Occupation displays (single value, not array)
- [ ] Parents list correctly with roles (father/mother)
- [ ] Children list correctly with birth years
- [ ] Siblings list correctly
- [ ] Spouses list correctly
- [ ] Godparents display from event participations
- [ ] Godchildren display from event participations

### Search & Filters
- [ ] Search by first name works
- [ ] Search by last name works
- [ ] Search by person ID works
- [ ] Surname filter works with last_name
- [ ] Year filter works with birth_date extraction

### Network Visualization
- [ ] Parent-child edges display (green, with arrows)
- [ ] Spouse edges display (red, no arrows)
- [ ] Witness edges display (gray, dashed)
- [ ] View filters work (all/families/marriages/godparents/witnesses)

### Editing
- [ ] Edit person modal opens with correct values
- [ ] Edit person saves correctly
- [ ] Network updates after edit
- [ ] Person details refresh after edit

### Merging
- [ ] Select two persons for merge
- [ ] Merge updates family_relationships
- [ ] Merge updates event_participations
- [ ] Merged person removed from network
- [ ] Kept person retains all relationships

### Statistics
- [ ] Total persons count correct
- [ ] Total events count correct
- [ ] Total relationships count correct (family_relationships)
- [ ] Total families count correct (unique last names)

## Known Limitations

1. **Date Precision**: Currently only year extraction is implemented in filters and some displays. Full date support (day/month) is available but not fully utilized everywhere.

2. **Occupation Display**: Changed from array to single string. Multiple occupations should be comma-separated in the single field.

3. **Place References**: Places are loaded but not yet displayed in person details (removed place_of_birth/place_of_death from person model - now derived from events).

4. **GEDCOM Integration**: Edit modal GEDCOM lookup fields may need adjustment for new date format.

## Rollback Instructions

If issues arise, to rollback:
1. Revert web/app.js, web/editor.js, web/enrichment.js to previous versions
2. Change data loading URL back to `genealogy_complete.json`
3. The old data model is still available

## Next Steps

After testing confirms everything works:
1. Update server endpoints to save to `genealogy_new_model.json`
2. Consider adding full date display support (day/month/year) in more places
3. Consider adding place information display in person details
4. Update GEDCOM enrichment to work with new model
5. Update any Python scripts that interact with the data

## Data Model Reference

### Person Object (New)
```json
{
  "id": "P001",
  "first_name": "Jan",
  "last_name": "Kowalski",
  "maiden_name": null,
  "gender": "M",
  "birth_date": {"year": 1850, "month": 5, "day": 10, "circa": false},
  "death_date": {"year": 1920, "month": null, "day": null, "circa": true},
  "occupation": "młynarz"
}
```

### Family Relationship (New)
```json
{
  "id": "FR001",
  "type": "parent",
  "person_1_id": "P001",
  "person_2_id": "P002"
}
```

### Event Participation (New)
```json
{
  "id": "EP001",
  "event_id": "E001",
  "person_id": "P001",
  "role": "child"
}
```

## Files Modified
- web/app.js
- web/editor.js
- web/enrichment.js

## Files Not Modified (may need future updates)
- server.py (save endpoints)
- serve.py (save endpoints)
- generate_enrichment_queue.py
- enrich_from_gedcom.py
