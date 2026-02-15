#!/bin/bash

# Simple bash script to start the web server
cd /Users/kulikj01/Desktop/git/mein/mal

echo "======================================================================"
echo "Genealogical Database - Starting Web Server"
echo "======================================================================"
echo ""

# Check if data exists
if [ ! -f "data/genealogy_complete.json" ]; then
    echo "ERROR: Data file not found!"
    echo "Please run: python3 process_genealogy.py"
    exit 1
fi

echo "✓ Data files found"
echo "✓ Starting server on port 8000"
echo ""
echo "Open your browser and go to:"
echo "  → http://localhost:8000/web/"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================================================"
echo ""

# Start Python HTTP server
python3 -m http.server 8000
