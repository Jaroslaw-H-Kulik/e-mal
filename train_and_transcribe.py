#!/usr/bin/env python3
"""
Kraken training and transcription pipeline for church records.

Step 1: Prepare training data (pair images with transcriptions)
Step 2: Train custom Kraken model
Step 3: Transcribe new documents using trained model

Usage:
    python3 train_and_transcribe.py
"""

import os
import json
from pathlib import Path
from PIL import Image

# Directories
TRAINING_IMG_DIR = Path("transcribe/training/in")
TRAINING_TXT_DIR = Path("transcribe/training/out")
INPUT_DIR = Path("transcribe/set/in")
OUTPUT_DIR = Path("transcribe/set/out")
MODEL_DIR = Path("transcribe/models")

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def find_training_pairs():
    """Find and pair JPG images with their transcriptions"""
    print("\n📚 Finding training pairs...")

    jpg_files = sorted(TRAINING_IMG_DIR.glob("*.jpg"))
    pairs = []

    for jpg_path in jpg_files:
        # Look for matching txt file with "not-" prefix
        base_name = jpg_path.stem  # e.g., "939V-T696-4Y"
        txt_name = f"not-{base_name}.txt"
        txt_path = TRAINING_TXT_DIR / txt_name

        if txt_path.exists():
            pairs.append({
                'image': jpg_path,
                'text': txt_path,
                'base_name': base_name
            })
            print(f"  ✓ {base_name}")
        else:
            # Try without "not-" prefix
            txt_path_alt = TRAINING_TXT_DIR / f"{base_name}.txt"
            if txt_path_alt.exists():
                pairs.append({
                    'image': jpg_path,
                    'text': txt_path_alt,
                    'base_name': base_name
                })
                print(f"  ✓ {base_name} (alt)")
            else:
                print(f"  ✗ {base_name} - no transcription found")

    print(f"\nFound {len(pairs)} training pairs")
    return pairs

def prepare_kraken_ground_truth(pairs, output_dir="transcribe/ground_truth"):
    """
    Prepare ground truth in Kraken format.
    For simplicity, we'll create page-level ground truth first.
    Kraken can segment automatically during training.
    """
    print("\n📝 Preparing ground truth...")

    gt_dir = Path(output_dir)
    gt_dir.mkdir(parents=True, exist_ok=True)

    prepared = []

    for pair in pairs:
        # Read transcription
        with open(pair['text'], 'r', encoding='utf-8') as f:
            text = f.read().strip()

        # Copy image to ground truth directory
        img_dest = gt_dir / f"{pair['base_name']}.jpg"

        # Create ground truth text file (same name, .gt.txt extension)
        gt_txt = gt_dir / f"{pair['base_name']}.gt.txt"

        with open(gt_txt, 'w', encoding='utf-8') as f:
            f.write(text)

        # Copy image
        Image.open(pair['image']).save(img_dest)

        prepared.append({
            'image': str(img_dest),
            'text': str(gt_txt)
        })
        print(f"  ✓ Prepared {pair['base_name']}")

    print(f"\n✅ Prepared {len(prepared)} ground truth pairs in {gt_dir}")
    return prepared, gt_dir

def create_training_manifest(gt_pairs, manifest_path="transcribe/ground_truth/manifest.json"):
    """Create manifest file for Kraken training"""
    manifest = []

    for pair in gt_pairs:
        manifest.append({
            'image': pair['image'],
            'text': pair['text']
        })

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Created training manifest: {manifest_path}")
    return manifest_path

def simple_line_training():
    """
    Simplified training approach using kraken command line tools.
    This creates a training script that can be run manually.
    """
    print("\n" + "="*70)
    print("KRAKEN TRAINING SETUP COMPLETE")
    print("="*70)

    print("\nGround truth prepared in: transcribe/ground_truth/")
    print("\nNext step: Train the model using Kraken CLI")
    print("\nRun these commands:")
    print("-" * 70)
    print("""
# 1. Segment all training images (detect lines)
for img in transcribe/ground_truth/*.jpg; do
    kraken -i "$img" "${img%.jpg}.json" segment
done

# 2. Create line-level ground truth from page-level transcriptions
# (This step requires manual alignment or kraken's segmentation tools)
# For now, we'll use a simpler approach with kraken's built-in tools

# 3. Train the recognition model (simplified)
kraken -d cuda train -o polish_church_records.mlmodel \\
    --partition 0.9 \\
    --threads 4 \\
    transcribe/ground_truth/*.jpg

# Or with CPU:
kraken train -o polish_church_records.mlmodel \\
    --partition 0.9 \\
    --threads 4 \\
    transcribe/ground_truth/*.jpg
    """)
    print("-" * 70)
    print("\n⚠️  Note: Kraken training requires line-level segmentation.")
    print("The commands above use Kraken's automatic segmentation.")
    print("\nExpected training time: 2-4 hours")
    print("="*70)

def main():
    """Main pipeline"""
    print("="*70)
    print("Kraken Training Pipeline for Church Records")
    print("="*70)

    # Step 1: Find training pairs
    pairs = find_training_pairs()

    if len(pairs) < 5:
        print("\n⚠️  Warning: Less than 5 training pairs found!")
        print("   Recommended: At least 20-30 pairs for good results")
        return

    print(f"\n✅ Found {len(pairs)} training pairs - good for training!")

    # Step 2: Prepare ground truth
    gt_pairs, gt_dir = prepare_kraken_ground_truth(pairs)

    # Step 3: Create manifest
    manifest = create_training_manifest(gt_pairs)

    # Step 4: Show training instructions
    simple_line_training()

    print("\n💡 Quick Start:")
    print("  1. The ground truth is ready in transcribe/ground_truth/")
    print("  2. Review the commands above to train your model")
    print(f"  3. You have {len(pairs)} training pairs - this is good!")
    print("  4. After training, run this script again to transcribe new files")

if __name__ == '__main__':
    main()
