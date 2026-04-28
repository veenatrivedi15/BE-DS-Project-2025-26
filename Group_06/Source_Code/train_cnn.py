import os
import zipfile
import shutil
import torch
import torch.nn as nn

# Prevent VRAM fragmentation on small GPUs like GTX 1650 (4GB)
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
import torchvision.models as models
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from torch.cuda.amp import GradScaler, autocast  # Mixed precision for ~50% VRAM savings

def setup_dataset():
    zip_path = "data/class.zip"
    extract_dir = "data/extracted"
    
    # Check if already extracted
    if not os.path.exists("data/train"):
        print(f"Extracting {zip_path}... This may take a few minutes (3.2GB).")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("data")
        print("Extraction complete.")

    classes_required = ["Normal", "Pneumonia", "Tuberculosis", "Lung Cancer"]
    
    # Restructure folders to exactly match our 4-class requirement
    splits = ["train", "val", "test"]
    for split in splits:
        base = os.path.join("data", split)
        if not os.path.exists(base): continue
        
        # Standardize naming to our UI expectations
        for folder in os.listdir(base):
            if folder.lower() == 'normal' and folder != 'Normal':
                os.rename(os.path.join(base, folder), os.path.join(base, "Normal"))
            elif folder.lower() == 'pneumonia' and folder != 'Pneumonia':
                os.rename(os.path.join(base, folder), os.path.join(base, "Pneumonia"))
            elif folder.lower() == 'tuberculosis' and folder != 'Tuberculosis':
                os.rename(os.path.join(base, folder), os.path.join(base, "Tuberculosis"))
        
        # Check for our new Lung Cancer images
        cancer_path = os.path.join(base, "Lung Cancer")
        if not os.path.exists(cancer_path) or len(os.listdir(cancer_path)) == 0:
            if split == "train":
                print(f"\n⚠️ WARNING: '{cancer_path}' is missing or empty!")
                print("Make sure you run `python extract_nih.py` before training!\n")
            os.makedirs(cancer_path, exist_ok=True)

def train_model():
    # 1. Hardware Detection — GPU ONLY mode
    if not torch.cuda.is_available():
        print("❌ ERROR: No CUDA GPU detected. Training requires a GPU.")
        print("Fix options:")
        print("  1. Install CUDA PyTorch: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
        print("  2. Make sure your NVIDIA drivers are up to date.")
        print("  3. If you only have a CPU, remove this check and set num_workers=0.")
        exit(1)
    device = torch.device("cuda")
    print(f"--- Training on GPU: {torch.cuda.get_device_name(0)} ---")

    # 2. Image Transformations (Enhanced with Data Augmentation)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5), # 50% chance to flip image left/right
        transforms.RandomRotation(15),          # Randomly rotate up to 15 degrees
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    print("Loading datasets into memory for GPU processing...")
    train_dataset = ImageFolder("data/train", transform=transform)
    # Batch size reduced from 16 → 8 to fit within 4GB VRAM of GTX 1650.
    # AMP (mixed precision) further halves VRAM usage, so effective throughput
    # remains comparable to batch=16 in full precision.
    train_loader = DataLoader(
        train_dataset,
        batch_size=8,       # GTX 1650 safe: 8 with AMP ≈ same throughput as 16 FP32
        shuffle=True,
        num_workers=0,
        pin_memory=False    # pin_memory=True can spike VRAM on 4GB cards
    )

    # 3. Model Architecture (4 classes)
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, 4) # 4 Web App Classes
    model = model.to(device)

    # 4. Mathematical Bias Elimination (Class Weights)
    # Tuberculosis has 8.5x more images than Lung Cancer. We penalize the AI mathematically
    # to force it to treat the 1,010 Lung Cancer images identically to the 8,500 TB images.
    class_counts = torch.tensor([
        len(os.listdir(os.path.join("data/train", c))) 
        for c in train_dataset.classes
    ], dtype=torch.float32)
    
    total_samples = class_counts.sum()
    class_weights = total_samples / (len(train_dataset.classes) * class_counts)
    class_weights = class_weights.to(device)
    
    print(f"Applying Anti-Bias Weights: {class_weights}")

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

    # Mixed precision scaler — automatically manages FP16/FP32 casting
    scaler = GradScaler()

    start_epoch = 0
    epochs = 10
    os.makedirs("models", exist_ok=True)
    checkpoint_path = "models/cnn_checkpoint.pth"

    if os.path.exists(checkpoint_path):
        print(f"Found existing checkpoint. Loading saved weights and optimizer state...")
        checkpoint = torch.load(checkpoint_path, weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        # Also restore scaler state if present (backward compatible)
        if 'scaler_state_dict' in checkpoint:
            scaler.load_state_dict(checkpoint['scaler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        print(f"Resuming training from Epoch {start_epoch+1}")
    else:
        print(f"Starting {epochs} Epochs of training from scratch...")
    
    for epoch in range(start_epoch, epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for i, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)

            # zero_grad BEFORE the forward pass so stale gradients don't
            # sit in VRAM during the forward+backward computation
            optimizer.zero_grad()

            # AMP autocast: forward pass runs in FP16 → ~50% VRAM savings
            with autocast():
                outputs = model(images)
                loss = criterion(outputs, labels)

            # Scaler handles the backward pass safely in FP16
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Print batch progress for massive datasets
            if (i+1) % 50 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Step [{i+1}/{len(train_loader)}], Loss: {loss.item():.4f}")

        acc = 100 * correct / total
        print(f"> Epoch {epoch+1} Completed: Avg Loss {total_loss/len(train_loader):.4f}, Accuracy {acc:.2f}%")

        # Free any cached VRAM before the next epoch starts
        torch.cuda.empty_cache()

        # Save checkpoint after every epoch (includes scaler state for AMP)
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scaler_state_dict': scaler.state_dict(),
        }, checkpoint_path)
        print(f"Checkpoint successfully saved for Epoch {epoch+1}!")

    # 4. Save Final Weights
    os.makedirs("models", exist_ok=True)
    save_path = "models/trained_cnn.pth"
    torch.save(model.state_dict(), save_path)
    print(f"\n✅ SUCCESS! Fully trained GPU weights saved directly to {save_path}")
    print("Restart your Flask web server and it will automatically use these weights!")

if __name__ == "__main__":
    print("Preparing GPU Dataset extraction pipeline...")
    setup_dataset()
    train_model()
