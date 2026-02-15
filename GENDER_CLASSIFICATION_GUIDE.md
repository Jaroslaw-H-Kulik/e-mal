# Gender Classification Guide

## Overview

The parser uses Polish naming rules to automatically classify genders:
- Names ending in 'a', 'ia', 'ja' → Female
- Names ending in consonants → Male
- Names ending in other vowels (e, i, o, u, y) → Male (lower confidence)

## Classification Results

**Current status:** 492 persons, 100% classified
- 293 Male
- 199 Female
- 0 Unknown

**Uncertain classifications:** 171 (35% of total)
- 5 unique names with LOW confidence (need review)
- 51 unique names with MEDIUM confidence (optional review)

## Low Confidence Names (Please Review)

These names need your attention:

| Name | Classified As | Count | Reason |
|------|--------------|-------|---------|
| **Alojzy** | Male | 1 | Name ending in 'y' |
| **Ambroży** | Male | 13 | Name ending in 'y' |
| **Konstanty** | Male | 4 | Name ending in 'y' |
| **Walenty** | Male | 11 | Name ending in 'y' |
| **Xi** | Male | 2 | Name ending in 'i' (possibly abbreviation?) |

## Medium Confidence Names (Common Ones)

Top 20 most frequent names classified with medium confidence:

| Name | Gender | Count | Notes |
|------|--------|-------|-------|
| Jacek | Male | 23 | Ends in 'k' |
| Ludwik | Male | 14 | Ends in 'k' |
| Karol | Male | 13 | Ends in 'l' |
| Teofil | Male | 6 | Ends in 'l' |
| Julianna | Female | 5 | Ends in 'a' |
| Kacper | Male | 5 | Ends in 'r' |
| Erazm | Male | 5 | Ends in 'm' |
| Wiktoria | Female | 4 | Ends in 'a' |
| Bernard | Male | 3 | Ends in 'd' |
| Gertruda | Female | 3 | Ends in 'a' |

## How to Review and Correct

### Step 1: Open the Review File

Open `data/gender_review.json` in your text editor.

### Step 2: Find Names to Correct

The file contains all uncertain classifications. Example entry:

```json
{
  "given_name": "Walenty",
  "surname": "Nobis",
  "inferred_gender": "M",
  "confidence": "low",
  "reason": "Name ending in vowel \"y\": Walenty",
  "birth_year": null,
  "year_context": 1855,
  "maiden_name": null
}
```

### Step 3: Add Corrections

If you disagree with the classification, add a `"corrected_gender"` field:

```json
{
  "given_name": "Walenty",
  "surname": "Nobis",
  "inferred_gender": "M",
  "confidence": "low",
  "reason": "Name ending in vowel \"y\": Walenty",
  "birth_year": null,
  "year_context": 1855,
  "maiden_name": null,
  "corrected_gender": "M"
}
```

**Valid values:** `"M"` (Male) or `"F"` (Female)

### Step 4: Save and Reprocess

1. Save `gender_review.json`
2. Run: `python3 process_genealogy_v2.py`
3. Parser will apply your corrections automatically
4. New data will be exported to `data/genealogy_complete.json`

### Step 5: Refresh Web Interface

After reprocessing:
1. Hard refresh browser: `Cmd+Shift+R`
2. Changes will appear in the visualization

## Notes on Polish Names

### Names Ending in 'y'
Common male names in Polish that end in 'y':
- Walenty (Valentine)
- Konstanty (Constantine)
- Ambroży (Ambrose)
- Alojzy (Aloysius)

These are typically male but marked as "low confidence" because the 'y' ending is less common.

### Compound Names
Names like "Jan Kapistran" are handled by analyzing the first part:
- "Jan" is clearly male
- Classification: Male (high confidence)

### Diminutives and Variants
- Kuba → Male (diminutive of Jakub/Jacob)
- Xi → Possibly abbreviation? (marked low confidence)

## Quick Reference

**Files:**
- `data/gender_review.json` - Review and correction file
- `process_genealogy_v2.py` - Parser script
- `data/genealogy_complete.json` - Output (used by web interface)

**Commands:**
```bash
# Reprocess with corrections
python3 process_genealogy_v2.py

# View summary
cat data/gender_review.json | grep -A 8 "confidence"

# Start web server
python3 -m http.server 8001
```

**Web Interface:**
http://localhost:8001/web/

---

**Last Updated:** 2026-02-14
**Total Persons:** 492
**Classification Rate:** 100%
**Uncertain:** 171 (35%)
