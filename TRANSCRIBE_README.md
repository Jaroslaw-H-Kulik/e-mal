# Church Records Transcription - Local OCR Setup

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements_transcribe.txt
```

**Note**: First run will download ~1GB TrOCR model from Hugging Face (one-time only).

### 2. Run Transcription

```bash
python3 transcribe_images.py
```

This will:
- Process all JPG files in `transcribe/in/`
- Save text files to `transcribe/out/`
- Skip already processed files

### 3. Review Output

Check `transcribe/out/*.txt` files and manually correct any OCR errors.

---

## How It Works

### Technology: TrOCR
- **Model**: Microsoft's TrOCR-large-handwritten
- **Type**: Transformer-based OCR (state-of-the-art for handwriting)
- **Runs**: 100% locally (no API calls, no internet after model download)
- **Size**: ~1GB model (downloads once, cached locally)

### Processing Strategy
1. **Split image** into 3 sections (assuming 3 records per page)
2. **Process each section** separately with TrOCR
3. **Combine results** into single text file
4. **Save** with same filename as source image

---

## Expected Accuracy

### For Handwritten Historical Documents:
- **TrOCR**: ~70-80% accuracy
- **Why lower?**: Model trained on modern handwriting, not 19th-century Polish script

### Reality Check:
✅ **Will recognize**: Most letters, numbers, common words
⚠️ **May struggle with**:
- Old Polish orthography (ósm vs ósem)
- Cursive flourishes
- Faded ink
- Similar letters (l/ł, c/ć)

### Best Use:
Use TrOCR output as a **starting point**, then manually correct:
- 70% accuracy = 30 minutes correction vs. 3 hours from scratch
- Still 6x faster than pure manual transcription

---

## Alternative: Manual Correction Workflow

If OCR quality is too low:

1. **Open image side-by-side** with text file
2. **Correct line-by-line** (much faster with reference)
3. **Keep consistent format** with existing files

---

## Performance

### Speed:
- **CPU**: ~2-3 minutes per image
- **GPU** (if available): ~30 seconds per image

### GPU Acceleration (Optional):
If you have NVIDIA GPU:
```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

---

## Troubleshooting

### Error: "No module named 'transformers'"
```bash
pip3 install transformers
```

### Error: "Killed" or memory issues
Reduce image size before processing:
```python
# In transcribe_images.py, after loading image:
if width > 2000:
    image = image.resize((2000, int(height * 2000 / width)))
```

### Poor quality results
Try alternative approach:
1. Use Google Cloud Vision API (free tier script available)
2. Or continue manual transcription (highest quality)

---

## File Organization

```
transcribe/
├── in/                       # Input JPG files
│   ├── 939V-T69C-VK.jpg     # To process
│   ├── 939V-T69C-8T.jpg     # To process
│   └── 939V-T69H-NH.jpg     # To process
│
├── out/                      # Output TXT files (OCR results)
│   ├── 939V-T69C-VK.txt     # Generated
│   ├── 939V-T69C-8T.txt     # Generated
│   └── 939V-T69H-NH.txt     # Generated
│
├── 939V-T69Z-9C.txt         # Manual transcriptions (reference quality)
└── 939V-T69H-B1.txt         # Manual transcriptions (reference quality)
```

---

## Next Steps (After Transcription)

Once you have all text files:

### Step 2: Data Extraction
Parse structured data from text:
- Extract dates, names, locations
- Normalize to consistent format
- Store in database/JSON

### Step 3: Integration
Load into genealogy app for visualization

---

## Tips for Manual Correction

1. **Use find/replace** for common OCR errors:
   - `o godzinie` vs `O godzinie`
   - `działo` vs `dziato`

2. **Reference your existing files** for format:
   ```
   Działo się w Wsi Mirzec dnia dwunastego Lutego...
   ```

3. **Common patterns** in church records:
   - Name: `[First] [Last]`
   - Age: `lat [number] mający/mającej`
   - Place: `w [Village] zamieszkały`
   - Parents: `z [Maiden name]`

4. **Preserve structure**:
   - Record number at top
   - Full text of record
   - Priest signature at bottom
   - Blank line between records

---

## Cost Comparison

| Method | Time | Cost | Accuracy |
|--------|------|------|----------|
| Manual | 3h/image | $0 | 100% |
| TrOCR (local) | 3min/image + 30min correction | $0 | 95% final |
| GPT-4 Vision | 2min/image + 5min correction | $0.20 | 98% final |

**Recommendation**: TrOCR local + manual correction = Best balance of speed and cost for 3 images.
