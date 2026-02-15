# Genealogical Database - Web UI Guide

## 🌐 Interactive Web Interface

This web interface provides an interactive way to explore the genealogical data from Grzybowa Góra parish (1826-1914).

## Features

### 🔍 Search & Query
- **Name Search**: Search by first name, surname, or person ID
- **Advanced Filters**: Filter by surname and year range
- **Real-time Results**: Instant search results with person details

### 👥 Network Visualization
- **Interactive Graph**: Visual representation of the entire community
- **Color-coded Nodes**:
  - 🔵 Blue = Male
  - 🔴 Pink = Female
  - ⚫ Gray = Unknown gender
- **Relationship Lines**:
  - 🟢 Green arrows = Parent → Child
  - 🔴 Red = Marriage
  - 🟡 Orange = Godparent relationship

### 📊 View Modes
- **All**: Show all relationships
- **Families**: Show only parent-child relationships
- **Marriages**: Show only marriage connections
- **Godparents**: Show only godparent relationships

### 📝 Person Details
Click any person to see:
- Full name with birth/death years
- Parents, siblings, spouse(s), children
- Complete event timeline
- Original Polish records
- Clickable links to related persons

## Quick Start

### 1. Start the Server

```bash
python3 serve.py
```

The server will:
- Start on `http://localhost:8000`
- Automatically open your browser
- Serve the web interface and data files

### 2. Explore the Data

**Welcome Screen:**
- See community statistics at the top
- View the entire network visualization
- Use the legend to understand colors and connections

**Search for Someone:**
1. Type a name in the search bar (e.g., "Jan Surdey")
2. Click on a result to see details
3. The network will zoom to that person

**View Person Details:**
1. Click any node in the network
2. See full family information on the right
3. Click on family members to navigate
4. View all events involving this person

**Filter the View:**
1. Check "Filter by surname" and select a family
2. Enter year range to see people from specific period
3. Click "Apply Filters" to update the view

**Change Perspective:**
1. Click view buttons (All/Families/Marriages/Godparents)
2. Network shows only selected relationship type
3. Use this to focus on specific connections

### 3. Navigation Tips

**Mouse Controls:**
- **Click**: Select a person
- **Double-click**: Focus on person and immediate connections
- **Drag**: Pan the view
- **Scroll**: Zoom in/out
- **Hover**: See person tooltip

**Keyboard Controls:**
- **Arrow keys**: Pan the view
- **+/-**: Zoom in/out
- **Enter**: Search

**Reset Everything:**
- Click "↻ Reset View" to clear all filters
- Returns to full network view

## Example Queries

### Find the Surdey Family

1. Search for "Surdey"
2. Multiple results will appear
3. Click on "Jan Surdey (P0001)" - the patriarch
4. See his daughter Brygida born 1826
5. Click on Brygida to see her marriage to Szczepan Słyk
6. View their children in the detail panel

### Explore a Specific Year

1. Set year range: 1855-1855
2. Click "Apply Filters"
3. See only people born in 1855
4. Click on individuals to see events from that year

### View Marriage Network

1. Click "Marriages" button
2. Network shows only married couples
3. See which families are connected by marriage
4. Useful for understanding social connections

### Find Godparent Relationships

1. Click "Godparents" button
2. See who served as godparents
3. Identifies influential community members
4. Shows social networks beyond blood relations

## Data Visualization

### Network Layout

The visualization uses **force-directed layout**:
- Related people are pulled together
- Unrelated people are pushed apart
- Natural clustering shows family groups
- Lines show relationship types

### Node Sizes

All nodes are the same size for clarity. Information is conveyed through:
- **Color**: Gender
- **Label**: Name and years
- **Position**: Relationship proximity

### Edge Patterns

- **Arrows**: Parent → Child direction
- **Thickness**: Relationship strength (future feature)
- **Color**: Relationship type

## Technical Details

### Browser Requirements

- Modern browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- Minimum 1280x720 screen resolution

### Performance

- **621 persons** displayed as network nodes
- **315 relationships** shown as connections
- **298 events** available in detail views
- Smooth rendering with physics simulation
- Search is instant (no server queries)

### Data Loading

All data is loaded once at startup:
- `genealogy_complete.json` (~334KB)
- Cached in browser memory
- No database queries needed
- Works offline after initial load

## Troubleshooting

### "Cannot load data"

**Problem**: Data files not found

**Solution**:
```bash
# Generate data files first
python3 process_genealogy.py

# Then start server
python3 serve.py
```

### Network is too crowded

**Solutions**:
1. Use filters to show fewer people
2. Change view mode (Families/Marriages)
3. Double-click a person to focus
4. Zoom in to see details

### Person details not showing

**Problem**: Clicking doesn't work

**Solution**:
1. Make sure you click directly on a node (circle)
2. Check browser console for errors (F12)
3. Refresh the page

### Server won't start

**Problem**: Port 8000 already in use

**Solution**:
```bash
# Option 1: Stop other server on port 8000
lsof -ti:8000 | xargs kill

# Option 2: Edit serve.py and change PORT = 8001
```

## File Structure

```
mal/
├── web/
│   ├── index.html          # Main UI
│   ├── style.css           # Styling
│   └── app.js              # Application logic
├── data/
│   ├── genealogy_complete.json   # Complete dataset
│   ├── persons.json              # Person registry
│   ├── events.json               # Event records
│   └── relationships.json        # Relationship graph
├── serve.py                # Web server
└── WEB_UI_GUIDE.md        # This file
```

## Advanced Features

### URL Parameters (Future)

Direct links to specific persons:
```
http://localhost:8000/?person=P0001
```

### Export Views (Future)

- Download network as image
- Export filtered list as CSV
- Generate family tree PDF

### Timeline View (Future)

- See events chronologically
- Filter by event type
- Animated timeline playback

## API Integration

The web UI can be extended to query the Python API:

```javascript
// Example: Add custom query
async function findRelationship(personA, personB) {
    const response = await fetch(`/api/relationship?a=${personA}&b=${personB}`);
    return await response.json();
}
```

## Privacy & Data

- All data is historical public records (1826-1914)
- No personal data of living persons
- Data stored locally, no cloud uploads
- No tracking or analytics

## Support

**Common Issues:**
- See `README.md` for data structure
- See `QUICKSTART.md` for Python API
- See `IMPLEMENTATION_SUMMARY.md` for technical details

**Need Help?**
- Check browser console (F12) for errors
- Verify data files are generated
- Ensure Python 3.6+ is installed

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search box |
| `Enter` | Execute search |
| `Esc` | Close person details |
| `R` | Reset view |
| `+/-` | Zoom in/out |
| `Arrows` | Pan view |

## Credits

**Technology Stack:**
- [vis.js](https://visjs.org/) - Network visualization
- Vanilla JavaScript - No framework overhead
- HTML5 + CSS3 - Modern web standards

**Data Source:**
- Parish records from Grzybowa Góra (1826-1914)
- Parsed and structured by `process_genealogy.py`

---

**Version:** 1.0
**Last Updated:** 2026-02-14
**License:** For genealogical research purposes

Enjoy exploring your family history! 🌳
