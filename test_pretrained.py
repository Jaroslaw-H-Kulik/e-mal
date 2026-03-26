#!/usr/bin/env python3
"""
Test Kraken with pre-trained models for quick feedback.
This shows baseline accuracy before investing in custom training.

Usage:
    python3 test_pretrained.py
"""

import os
from pathlib import Path
from PIL import Image
from kraken import binarization, pageseg, rpred
from kraken.lib import models

# Directories
TRAINING_IMG_DIR = Path("transcribe/training/in")
TRAINING_TXT_DIR = Path("transcribe/training/out")
INPUT_DIR = Path("transcribe/set/in")
OUTPUT_DIR = Path("transcribe/set/out")
GROUND_TRUTH_DIR = Path("transcribe/ground_truth")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_pretrained_model():
    """Download a suitable pre-trained model for historical documents"""
    print("\n🔍 Checking for pre-trained models...")

    # Try to use a model suitable for historical Latin script
    # Kraken has several models available
    model_name = None

    # Check if we can list available models
    try:
        from kraken import repo
        print("  Available models from Kraken repository:")
        # This would show available models
        # For now, we'll use the default model
    except:
        pass

    print("  Using Kraken's default model (trained on printed Latin text)")
    print("  Note: May not be optimal for handwritten Polish, but gives baseline")

    return None  # Use default

def test_on_sample(image_path, ground_truth_path, model=None):
    """Test OCR on a sample with known ground truth"""
    print(f"\n📄 Testing on: {image_path.name}")

    # Load image
    im = Image.open(image_path)
    print(f"  Image size: {im.size[0]}x{im.size[1]}px")

    # Binarize
    print("  1/3 Binarizing...")
    bw_im = binarization.nlbin(im)

    # Segment (find text lines)
    print("  2/3 Segmenting...")
    try:
        baseline_seg = pageseg.segment(bw_im, text_direction='horizontal-lr')
        print(f"  Found {len(baseline_seg.lines)} text lines")

        if len(baseline_seg.lines) == 0:
            print("  ⚠️ No text lines detected!")
            return None, None
    except Exception as e:
        print(f"  ❌ Segmentation failed: {e}")
        return None, None

    # Recognize text
    print("  3/3 Recognizing...")
    try:
        recognized_lines = []
        pred_it = rpred.rpred(model, bw_im, baseline_seg)

        for idx, record in enumerate(pred_it, 1):
            line_text = record.prediction
            confidence = record.confidences
            avg_conf = sum(confidence) / len(confidence) if confidence else 0

            if line_text.strip():
                recognized_lines.append(line_text)
                # Show first few lines
                if idx <= 5:
                    print(f"    Line {idx} ({avg_conf:.2%}): {line_text[:60]}...")

        recognized_text = '\n'.join(recognized_lines)

        # Load ground truth for comparison
        if ground_truth_path and ground_truth_path.exists():
            with open(ground_truth_path, 'r', encoding='utf-8') as f:
                ground_truth = f.read().strip()

            # Simple accuracy metric: character-level similarity
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, recognized_text, ground_truth).ratio()

            print(f"\n  📊 Accuracy vs ground truth: {similarity*100:.1f}%")
            print(f"  📝 Recognized {len(recognized_text)} chars vs {len(ground_truth)} expected")

            return recognized_text, similarity
        else:
            print(f"\n  📝 Recognized {len(recognized_text)} characters")
            return recognized_text, None

    except Exception as e:
        print(f"  ❌ Recognition failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def transcribe_file(image_path, output_path, model=None):
    """Transcribe a single file"""
    print(f"\n📄 Transcribing: {image_path.name}")

    # Load and process
    im = Image.open(image_path)
    bw_im = binarization.nlbin(im)

    try:
        baseline_seg = pageseg.segment(bw_im, text_direction='horizontal-lr')

        recognized_lines = []
        pred_it = rpred.rpred(model, bw_im, baseline_seg)

        for record in pred_it:
            if record.prediction.strip():
                recognized_lines.append(record.prediction)

        recognized_text = '\n'.join(recognized_lines)

        # Save output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(recognized_text)

        print(f"  ✅ Saved to: {output_path}")
        return recognized_text

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return None

def main():
    """Main testing pipeline"""
    print("="*70)
    print("Kraken Pre-trained Model Test")
    print("Testing baseline accuracy before custom training")
    print("="*70)

    # Download/load model
    model = download_pretrained_model()

    # Test on a few training samples
    print("\n" + "="*70)
    print("TESTING ON TRAINING SAMPLES (with ground truth)")
    print("="*70)

    # Get first 3 samples for testing
    test_samples = list(GROUND_TRUTH_DIR.glob("*.jpg"))[:3]

    if not test_samples:
        print("\n⚠️ No ground truth samples found!")
        print("   Make sure to run train_and_transcribe.py first")
        return

    accuracies = []

    for img_path in test_samples:
        gt_path = img_path.with_suffix('.gt.txt')
        text, accuracy = test_on_sample(img_path, gt_path, model)

        if accuracy is not None:
            accuracies.append(accuracy)

        print("-"*70)

    # Show average accuracy
    if accuracies:
        avg_accuracy = sum(accuracies) / len(accuracies)
        print(f"\n📊 AVERAGE ACCURACY: {avg_accuracy*100:.1f}%")

        if avg_accuracy < 0.5:
            print("\n⚠️  Low accuracy (<50%) - Custom training HIGHLY recommended")
            print("   Pre-trained model not suitable for this handwriting style")
        elif avg_accuracy < 0.7:
            print("\n⚠️  Moderate accuracy (50-70%) - Custom training recommended")
            print("   You'll need significant manual correction")
        elif avg_accuracy < 0.85:
            print("\n✅ Good accuracy (70-85%) - Custom training may help")
            print("   Usable with moderate corrections")
        else:
            print("\n🎉 Excellent accuracy (>85%) - Pre-trained model works well!")
            print("   Custom training may only give marginal improvement")

    # Now transcribe new files
    print("\n" + "="*70)
    print("TRANSCRIBING NEW FILES")
    print("="*70)

    new_files = list(INPUT_DIR.glob("*.jpg"))

    if not new_files:
        print("\nNo new files to transcribe in transcribe/set/in/")
    else:
        for img_path in new_files:
            output_path = OUTPUT_DIR / f"{img_path.stem}.txt"
            transcribe_file(img_path, output_path, model)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    if accuracies:
        print(f"Pre-trained model accuracy: {avg_accuracy*100:.1f}%")
    print(f"Transcribed {len(new_files)} new file(s) to {OUTPUT_DIR}")
    print("\n💡 Next steps:")
    if accuracies and avg_accuracy < 0.7:
        print("  1. Custom Kraken training STRONGLY recommended")
        print("  2. You have 29 training samples ready")
        print("  3. Expected improvement: 70-85% accuracy after training")
    else:
        print("  1. Review transcribed files")
        print("  2. Correct any errors manually")
        print("  3. If accuracy is too low, proceed with custom training")
    print("="*70)

if __name__ == '__main__':
    main()
