#!/usr/bin/env python3
"""
Kraken OCR script for historical church records.
Kraken is specifically designed for historical manuscripts and documents.

Usage:
    python3 transcribe_kraken.py
"""

import os
from pathlib import Path
from PIL import Image
from kraken import binarization, pageseg, rpred
from kraken.lib import models

# Directories
INPUT_DIR = Path("transcribe/in")
OUTPUT_DIR = Path("transcribe/out")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def list_available_models():
    """Show available Kraken models"""
    print("\n📚 Available Kraken Models:")
    print("  - Default model: Works for Latin script (including Polish)")
    print("  - You can also download specialized models from:")
    print("    https://zenodo.org/communities/ocr_models")
    print()

def process_image_with_kraken(image_path, model_name=None):
    """Process image using Kraken OCR"""
    print(f"\n📄 Processing: {image_path.name}")

    # Load image
    im = Image.open(image_path)
    print(f"  Image size: {im.size[0]}x{im.size[1]}px")

    # Step 1: Binarization (convert to black & white for better OCR)
    print("  1/3 Binarizing image...")
    bw_im = binarization.nlbin(im)

    # Step 2: Layout analysis (detect text regions and lines)
    print("  2/3 Analyzing layout (detecting text lines)...")
    try:
        # Use default segmentation
        seg_result = pageseg.segment(bw_im, text_direction='horizontal-lr')

        # Show detected lines
        num_lines = len(seg_result['lines'])
        print(f"    Found {num_lines} text lines")

        if num_lines == 0:
            print("    ⚠️  No text lines detected!")
            return None

    except Exception as e:
        print(f"    ⚠️  Layout analysis failed: {e}")
        return None

    # Step 3: Text recognition
    print("  3/3 Recognizing text...")
    try:
        # Load default model (or specified model)
        if model_name:
            print(f"    Using model: {model_name}")
            model = models.load_any(model_name)
        else:
            print("    Using default model (Latin script)")
            model = None  # Kraken will use default

        # Recognize text
        results = []
        pred_it = rpred.rpred(model, bw_im, seg_result)

        for idx, record in enumerate(pred_it, 1):
            line_text = record.prediction
            if line_text.strip():
                results.append(line_text)
                print(f"    Line {idx}: {line_text[:60]}{'...' if len(line_text) > 60 else ''}")

        if not results:
            print("    ⚠️  No text recognized!")
            return None

        return '\n'.join(results)

    except Exception as e:
        print(f"    ❌ Text recognition failed: {e}")
        return None

def main():
    """Main transcription workflow"""
    print("=" * 70)
    print("Church Records Transcription - Kraken OCR")
    print("(Specialized for historical documents)")
    print("=" * 70)

    list_available_models()

    # Find all JPG files
    image_files = sorted(INPUT_DIR.glob("*.jpg"))

    if not image_files:
        print(f"\n⚠️  No JPG files found in {INPUT_DIR}")
        return

    print(f"Found {len(image_files)} image(s) to process:")
    for img in image_files:
        print(f"  - {img.name}")

    # Process each image
    success_count = 0
    fail_count = 0

    for image_path in image_files:
        output_path = OUTPUT_DIR / f"{image_path.stem}.txt"

        # Skip if already processed
        if output_path.exists():
            existing_size = output_path.stat().st_size
            if existing_size > 100:  # Only skip if file has substantial content
                print(f"\n⏭️  Skipping {image_path.name} (already processed, {existing_size} bytes)")
                continue

        try:
            # Extract text with Kraken
            text = process_image_with_kraken(image_path)

            if text:
                # Save to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)

                print(f"  ✅ Saved to: {output_path} ({len(text)} chars)")
                success_count += 1
            else:
                print(f"  ⚠️  No text extracted for {image_path.name}")
                # Save empty file to mark as attempted
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("# No text detected by Kraken OCR\n")
                fail_count += 1

        except Exception as e:
            print(f"  ❌ Error processing {image_path.name}: {e}")
            fail_count += 1
            continue

    print("\n" + "=" * 70)
    print(f"✅ Processing complete!")
    print(f"   Success: {success_count} files")
    print(f"   Failed:  {fail_count} files")
    print(f"📁 Output files in: {OUTPUT_DIR}")
    print("=" * 70)

    if success_count > 0:
        print("\n💡 Next steps:")
        print("  1. Review the transcribed text files")
        print("  2. Compare with your manual transcriptions")
        print("  3. Kraken is better than TrOCR for historical docs")
        print("  4. You may still need manual correction (~80-85% accuracy expected)")
    else:
        print("\n⚠️  No successful transcriptions!")
        print("  Possible issues:")
        print("  - Images may need preprocessing (contrast adjustment)")
        print("  - Handwriting may be too difficult for automated OCR")
        print("  - Consider using specialized trained models for 19th century Polish")

if __name__ == '__main__':
    main()
