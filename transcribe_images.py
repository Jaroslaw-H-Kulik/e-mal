#!/usr/bin/env python3
"""
Local OCR script for transcribing handwritten church records.
Uses TrOCR (Microsoft's handwriting recognition model) - runs completely locally.

Usage:
    python3 transcribe_images.py
"""

import os
from pathlib import Path
from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# Directories
INPUT_DIR = Path("transcribe/in")
OUTPUT_DIR = Path("transcribe/out")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_model():
    """Load TrOCR model for handwritten text recognition"""
    print("Loading TrOCR model (handwritten)...")
    print("  (First run will download ~1GB model - this is normal)")

    # Use handwritten model (better for historical documents)
    processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-handwritten')
    model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-handwritten')

    # Use GPU if available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"  Model loaded on {device}")

    return processor, model, device

def process_image(image_path, processor, model, device):
    """Process a single image and extract text"""
    print(f"\n📄 Processing: {image_path.name}")

    # Load image
    image = Image.open(image_path).convert("RGB")

    # For large images, we may need to process in chunks
    # Church records typically have 3 records per page
    width, height = image.size
    print(f"  Image size: {width}x{height}px")

    # Split image into sections (assuming 3 records vertically)
    sections = []
    section_height = height // 3

    for i in range(3):
        top = i * section_height
        bottom = (i + 1) * section_height if i < 2 else height
        section = image.crop((0, top, width, bottom))
        sections.append(section)

    # Process each section
    all_text = []
    for i, section in enumerate(sections, 1):
        print(f"  Processing section {i}/3...")

        # Prepare image for model
        pixel_values = processor(section, return_tensors="pt").pixel_values.to(device)

        # Generate text
        generated_ids = model.generate(pixel_values, max_length=512)
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        if generated_text.strip():
            all_text.append(f"\n{generated_text.strip()}\n")

    return "\n".join(all_text)

def main():
    """Main transcription workflow"""
    print("=" * 70)
    print("Church Records Transcription - Local OCR")
    print("=" * 70)

    # Find all JPG files in input directory
    image_files = sorted(INPUT_DIR.glob("*.jpg"))

    if not image_files:
        print(f"\n⚠️  No JPG files found in {INPUT_DIR}")
        return

    print(f"\nFound {len(image_files)} image(s) to process:")
    for img in image_files:
        print(f"  - {img.name}")

    # Load model once
    processor, model, device = load_model()

    # Process each image
    for image_path in image_files:
        output_path = OUTPUT_DIR / f"{image_path.stem}.txt"

        # Skip if already processed
        if output_path.exists():
            print(f"\n⏭️  Skipping {image_path.name} (already processed)")
            continue

        try:
            # Extract text
            text = process_image(image_path, processor, model, device)

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)

            print(f"  ✅ Saved to: {output_path}")

        except Exception as e:
            print(f"  ❌ Error processing {image_path.name}: {e}")
            continue

    print("\n" + "=" * 70)
    print("✅ Transcription complete!")
    print(f"📁 Output files in: {OUTPUT_DIR}")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("  1. Review the transcribed text files")
    print("  2. Correct any OCR errors manually")
    print("  3. TrOCR may struggle with old handwriting - expect ~70-80% accuracy")
    print("  4. Consider using the transcribed text as a starting point for manual correction")

if __name__ == '__main__':
    main()
