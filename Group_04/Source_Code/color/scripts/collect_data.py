#!/usr/bin/env python3
"""
Helper script to collect and prepare real data for training.

This script helps you:
1. Collect responses from test.html using "Export Responses"
2. Create labels.csv for user ground truth
3. Optionally create ground_truth.csv for expected answers
4. Retrain the model with real data
"""

import csv
import sys
from pathlib import Path

def create_sample_labels_csv(output_path: Path):
    """Create a sample labels.csv file."""
    sample_data = [
        {"session_id": "session_001", "user_label": "Normal"},
        {"session_id": "session_002", "user_label": "Normal"},
        {"session_id": "session_003", "user_label": "Protanopia"},
        {"session_id": "session_004", "user_label": "Deuteranopia"},
        {"session_id": "session_005", "user_label": "Tritanopia"},
    ]
    
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['session_id', 'user_label'])
        writer.writeheader()
        writer.writerows(sample_data)
    
    print(f"Created sample labels.csv at {output_path}")
    print("Edit this file to match your actual user sessions and labels.")

def create_sample_ground_truth_csv(output_path: Path):
    """Create a sample ground_truth.csv file."""
    sample_data = [
        {"plate_id": 1, "expected_normal_answer": 12},
        {"plate_id": 2, "expected_normal_answer": 8},
        {"plate_id": 3, "expected_normal_answer": 6},
        {"plate_id": 4, "expected_normal_answer": 29},
        {"plate_id": 5, "expected_normal_answer": 57},
        {"plate_id": 6, "expected_normal_answer": 5},
        {"plate_id": 7, "expected_normal_answer": 3},
        {"plate_id": 8, "expected_normal_answer": 15},
        {"plate_id": 9, "expected_normal_answer": 74},
        {"plate_id": 10, "expected_normal_answer": 2},
    ]
    
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['plate_id', 'expected_normal_answer'])
        writer.writeheader()
        writer.writerows(sample_data)
    
    print(f"Created sample ground_truth.csv at {output_path}")
    print("Edit this file with the correct answers for each plate.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/collect_data.py <command>")
        print("Commands:")
        print("  init-labels     - Create sample labels.csv")
        print("  init-ground     - Create sample ground_truth.csv")
        print("  train           - Train with real data (requires responses.csv)")
        return
    
    command = sys.argv[1]
    
    if command == "init-labels":
        create_sample_labels_csv(Path("labels.csv"))
    elif command == "init-ground":
        create_sample_ground_truth_csv(Path("ground_truth.csv"))
    elif command == "train":
        responses_csv = Path("responses.csv")
        if not responses_csv.exists():
            print("Error: responses.csv not found. Run the test and export responses first.")
            return
        
        labels_csv = Path("labels.csv") if Path("labels.csv").exists() else None
        ground_truth_csv = Path("ground_truth.csv") if Path("ground_truth.csv").exists() else None
        
        print("Training with real data...")
        print(f"Responses: {responses_csv}")
        print(f"Labels: {labels_csv}")
        print(f"Ground truth: {ground_truth_csv}")
        
        # Run the training script
        import subprocess
        cmd = [
            "python", "scripts/train_response_model.py",
            "web/plates_manifest.json",
            "web/weights.json",
            str(responses_csv)
        ]
        if labels_csv:
            cmd.append(str(labels_csv))
        if ground_truth_csv:
            cmd.append(str(ground_truth_csv))
        
        subprocess.run(cmd)
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()





