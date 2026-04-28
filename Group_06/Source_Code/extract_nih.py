import pandas as pd
import os
import shutil
import argparse

def extract_lung_cancer_images(csv_path, source_dir, target_dir, max_images=1000):
    print("==============================================")
    print("   NIH Dataset Lung Cancer Extraction Script")
    print("==============================================")
    
    # NIH uses "Mass" or "Nodule" as primary visual indicators for lung tumors
    print(f"Loading CSV from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Error: Cannot find CSV file at {csv_path}")
        print("Please make sure you downloaded Data_Entry_2017.csv from Kaggle and put it there.")
        return

    # Filter rows containing 'Mass' or 'Nodule' in the 'Finding Labels' column
    cancer_df = df[df['Finding Labels'].str.contains('Mass|Nodule', na=False, case=False)]
    
    print(f"Found {len(cancer_df)} potential lung cancer/tumor images in the CSV.")
    print(f"Extracting up to {max_images} of them...")
    
    os.makedirs(target_dir, exist_ok=True)
    
    count = 0
    not_found = 0
    
    for idx, row in cancer_df.iterrows():
        if count >= max_images:
            break
            
        img_name = row['Image Index']
        
        # Searching for the image in the source directory
        # Users might extract NIH into one huge folder or multiple 'images_XX' subfolders.
        # Let's search recursively if it's not in the base directory.
        src_path = os.path.join(source_dir, img_name)
        
        if not os.path.exists(src_path):
            found_in_sub = False
            for root, dirs, files in os.walk(source_dir):
                if img_name in files:
                    src_path = os.path.join(root, img_name)
                    found_in_sub = True
                    break
            
            if not found_in_sub:
                not_found += 1
                continue
                
        dst_path = os.path.join(target_dir, img_name)
        
        # Only copy if it hasn't been copied already
        if not os.path.exists(dst_path):
            shutil.copy(src_path, dst_path)
            
        count += 1
        
        if count % 100 == 0:
            print(f"... Copied {count}/{max_images} images")
            
    print("\n✅ Extraction complete!")
    print(f"Successfully copied {count} actual Cancer/Tumor images to '{target_dir}'.")
    
    if not_found > 0:
        print(f"\n⚠️ Warning: {not_found} images listed in the CSV were NOT found on your hard drive.")
        print("This usually means you haven't extracted all 12 of the .tar.gz image files from Kaggle yet.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract NIH Mass/Nodule images")
    parser.add_argument("--csv", default="data/raw_nih/Data_Entry_2017.csv", help="Path to Data_Entry_2017.csv")
    parser.add_argument("--source", default="data/raw_nih", help="Folder containing extracted NIH images")
    parser.add_argument("--target", default="data/train/Lung Cancer", help="Output directory")
    parser.add_argument("--count", type=int, default=1000, help="Number of images to copy")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"❌ Error: Source directory '{args.source}' does not exist.")
        print("Please create this folder and put the extracted NIH images and CSV inside it.")
    else:
        extract_lung_cancer_images(args.csv, args.source, args.target, args.count)
