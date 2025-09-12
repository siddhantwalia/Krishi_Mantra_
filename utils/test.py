import os
import torch
import torch.nn as nn
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
from pathlib import Path


def load_model(checkpoint_path, num_classes, device):
    from torchvision.models import ResNet50_Weights
    model = models.resnet50(weights=None)  # no pretrained weights at load
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)

    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model = model.to(device)
    model.eval()
    return model


def evaluate_model(model, dataloader, device):
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            correct += (preds == labels).sum().item()
            total += labels.size(0)

    acc = correct / total
    return acc


def main(data_dir, checkpoint_path, num_classes=38, batch_size=32):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    # ✅ Same transforms as validation in train.py
    data_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    dataset = datasets.ImageFolder(os.path.join(data_dir, "val"), data_transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=4)

    print(f"Loaded {len(dataset)} validation images across {len(dataset.classes)} classes")

    # Load model + checkpoint
    model = load_model(checkpoint_path, num_classes, device)

    # Evaluate
    acc = evaluate_model(model, dataloader, device)
    print(f"Validation Accuracy: {acc:.4f}")


if __name__ == "__main__":
    data_dir = "archive/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)"
    checkpoint_path = "checkpoints/plant_disease_best.pth"   # 🔹 Change if needed
    main(data_dir, checkpoint_path, num_classes=38, batch_size=32)
