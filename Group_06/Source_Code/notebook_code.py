from google.colab import files
uploaded = files.upload()

import zipfile
import os

with zipfile.ZipFile("kaggle.zip", 'r') as zip_ref:
    zip_ref.extractall("data")

os.listdir("data")

import pandas as pd

patients = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/patients.csv")
admissions = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/admissions.csv")
diagnoses = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/diagnoses_icd.csv")

df = admissions.merge(patients, on="subject_id")
df = df.merge(diagnoses, on=["subject_id", "hadm_id"])

df.head()

df['admittime'] = pd.to_datetime(df['admittime'])
df['dob'] = pd.to_datetime(df['anchor_year'])  # approximate age

df['age'] = df['admittime'].dt.year - df['anchor_year']

df = df[['age', 'gender', 'admission_type', 'insurance', 'icd_code']]
df.dropna(inplace=True)

top_codes = df['icd_code'].value_counts().nlargest(5).index
df = df[df['icd_code'].isin(top_codes)]

from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()

df['gender'] = le.fit_transform(df['gender'])
df['admission_type'] = le.fit_transform(df['admission_type'])
df['insurance'] = le.fit_transform(df['insurance'])
df['icd_code'] = le.fit_transform(df['icd_code'])

import torch
from sklearn.model_selection import train_test_split

X = df[['age', 'gender', 'admission_type', 'insurance']].values
y = df['icd_code'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

import torch.nn as nn

class EHRModel(nn.Module):
    def __init__(self):
        super(EHRModel, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 5)  # 5 disease classes
        )

    def forward(self, x):
        return self.net(x)

model = EHRModel()

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(20):
    outputs = model(X_train)
    loss = criterion(outputs, y_train)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    print(f"Epoch {epoch+1}, Loss: {loss.item()}")

from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X = scaler.fit_transform(X)

from torch.utils.data import TensorDataset, DataLoader

train_dataset = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

class EHRModel(nn.Module):
    def __init__(self):
        super(EHRModel, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, 5)
        )

    def forward(self, x):
        return self.net(x)

for epoch in range(30):
    total_loss = 0

    for X_batch, y_batch in train_loader:
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader)}")

with torch.no_grad():
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)
    accuracy = (predicted == y_test).sum().item() / len(y_test)

print("Accuracy:", accuracy)

print(df.columns)

class EHRModel(nn.Module):
    def __init__(self):
        super(EHRModel, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 5)
        )

top_codes = df['icd_code'].value_counts().nlargest(3).index
df = df[df['icd_code'].isin(top_codes)]

patients = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/patients.csv")
admissions = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/admissions.csv")
diagnoses = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/diagnoses_icd.csv")

df = admissions.merge(patients, on="subject_id")
df = df.merge(diagnoses, on=["subject_id", "hadm_id"])

print(df.columns)

df = df[['anchor_age', 'gender', 'admission_type',
         'admission_location', 'discharge_location',
         'insurance', 'hospital_expire_flag', 'icd_code']]

df.rename(columns={'anchor_age': 'age'}, inplace=True)

df.dropna(inplace=True)

top_codes = df['icd_code'].value_counts().nlargest(3).index
df = df[df['icd_code'].isin(top_codes)]

from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()

cols = ['gender', 'admission_type', 'admission_location',
        'discharge_location', 'insurance', 'icd_code']

for col in cols:
    df[col] = le.fit_transform(df[col])

X = df[['age', 'gender', 'admission_type',
        'admission_location', 'discharge_location',
        'insurance', 'hospital_expire_flag']].values

y = df['icd_code'].values

from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X = scaler.fit_transform(X)

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

import torch

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

from torch.utils.data import TensorDataset, DataLoader

train_dataset = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

import torch.nn as nn

class EHRModel(nn.Module):
    def __init__(self):
        super(EHRModel, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(7, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, 3)  # 3 classes
        )

    def forward(self, x):
        return self.net(x)

model = EHRModel()

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(50):
    total_loss = 0

    for X_batch, y_batch in train_loader:
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader)}")

with torch.no_grad():
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)
    accuracy = (predicted == y_test).sum().item() / len(y_test)

print("Accuracy:", accuracy)

print(df['icd_code'].value_counts())

y = df['hospital_expire_flag'].values

nn.Linear(64, 2)  # binary classification

criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

for epoch in range(50):
    total_loss = 0

    for X_batch, y_batch in train_loader:
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader)}")

with torch.no_grad():
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)
    accuracy = (predicted == y_test).sum().item() / len(y_test)

print("Accuracy:", accuracy)

print(df['hospital_expire_flag'].value_counts())

min_count = df['hospital_expire_flag'].value_counts().min()

df_balanced = df.groupby('hospital_expire_flag').apply(
    lambda x: x.sample(min_count)
).reset_index(drop=True)

df = df_balanced

print(df['hospital_expire_flag'].value_counts())

for epoch in range(50):
    total_loss = 0

    for X_batch, y_batch in train_loader:
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader)}")

with torch.no_grad():
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)
    accuracy = (predicted == y_test).sum().item() / len(y_test)

print("Accuracy:", accuracy)

print("Predicted:", predicted[:10])
print("Actual:", y_test[:10])

print(df['hospital_expire_flag'].unique())

y = df['hospital_expire_flag'].values

nn.Linear(64, 2)  # ONLY 2 classes

import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import TensorDataset, DataLoader

patients = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/patients.csv")
admissions = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/admissions.csv")
diagnoses = pd.read_csv("/content/data/mimic-iv-clinical-database-demo-2.2/hosp/diagnoses_icd.csv")

df = admissions.merge(patients, on="subject_id")
df = df.merge(diagnoses, on=["subject_id", "hadm_id"])

df = df[['anchor_age', 'gender', 'admission_type',
         'admission_location', 'discharge_location',
         'insurance', 'hospital_expire_flag']]

df.rename(columns={'anchor_age': 'age'}, inplace=True)
df.dropna(inplace=True)

le = LabelEncoder()

cols = ['gender', 'admission_type', 'admission_location',
        'discharge_location', 'insurance']

for col in cols:
    df[col] = le.fit_transform(df[col])

df = df.groupby('hospital_expire_flag', group_keys=False).apply(
    lambda x: x.sample(min_count)
).reset_index(drop=True)

X = df[['age', 'gender', 'admission_type',
        'admission_location', 'discharge_location',
        'insurance']].values

y = df['hospital_expire_flag'].values  # ✅ FINAL TARGET

scaler = StandardScaler()
X = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)

y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

train_dataset = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)

class EHRModel(nn.Module):
    def __init__(self):
        super(EHRModel, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(6, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.3),

            nn.Linear(64, 2)  # ✅ binary output
        )

    def forward(self, x):
        return self.net(x)

model = EHRModel()

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

for epoch in range(50):
    total_loss = 0

    for X_batch, y_batch in train_loader:
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader)}")

with torch.no_grad():
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)
    accuracy = (predicted == y_test).sum().item() / len(y_test)

print("Accuracy:", accuracy)

print("Predicted:", predicted[:10])
print("Actual:", y_test[:10])

print(len(df))
print(len(X_test))

from sklearn.metrics import confusion_matrix

print(confusion_matrix(y_test, predicted))

with zipfile.ZipFile("/content/drive/MyDrive/D/class.zip", 'r') as zip_ref:
    zip_ref.extractall("data")

import os
print(os.listdir("data"))

import os
print(os.listdir("/content/data/train"))

import os
import shutil

os.makedirs("train/ABNORMAL", exist_ok=True)

for folder in ["PNEUMONIA", "TUBERCULOSIS"]:
    folder_path = os.path.join("train", folder)

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            shutil.move(os.path.join(folder_path, file), "train/ABNORMAL")

        os.rmdir(folder_path)

for split in ["val", "test"]:
    os.makedirs(f"{split}/ABNORMAL", exist_ok=True)

    for folder in ["PNEUMONIA", "TUBERCULOSIS"]:
        folder_path = os.path.join(split, folder)

        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                shutil.move(os.path.join(folder_path, file), f"{split}/ABNORMAL")

            os.rmdir(folder_path)

print(os.listdir("train"))

import os
print(os.listdir("train"))

import shutil

shutil.rmtree("train")
shutil.rmtree("val")
shutil.rmtree("test")

with zipfile.ZipFile("/content/drive/MyDrive/D/class.zip", 'r') as zip_ref:
    zip_ref.extractall("data")

import os
print(os.listdir("/content/data/train"))

import os
import shutil

base = "data/train"

# Rename normal
if "normal" in os.listdir(base):
    os.rename(f"{base}/normal", f"{base}/NORMAL")

# Create ABNORMAL
os.makedirs(f"{base}/ABNORMAL", exist_ok=True)

# Move disease folders
for folder in ["pneumonia", "tuberculosis"]:
    folder_path = os.path.join(base, folder)

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            shutil.move(os.path.join(folder_path, file), f"{base}/ABNORMAL")

        os.rmdir(folder_path)

base = "data/val"

if "normal" in os.listdir(base):
    os.rename(f"{base}/normal", f"{base}/NORMAL")

os.makedirs(f"{base}/ABNORMAL", exist_ok=True)

for folder in ["pneumonia", "tuberculosis"]:
    folder_path = os.path.join(base, folder)

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            shutil.move(os.path.join(folder_path, file), f"{base}/ABNORMAL")

        os.rmdir(folder_path)

base = "data/test"

if "normal" in os.listdir(base):
    os.rename(f"{base}/normal", f"{base}/NORMAL")

os.makedirs(f"{base}/ABNORMAL", exist_ok=True)

for folder in ["pneumonia", "tuberculosis"]:
    folder_path = os.path.join(base, folder)

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            shutil.move(os.path.join(folder_path, file), f"{base}/ABNORMAL")

        os.rmdir(folder_path)

print(os.listdir("data/train"))
print(os.listdir("data/val"))
print(os.listdir("data/test"))

import shutil

for split in ["train", "val", "test"]:
    path = f"data/{split}/.ipynb_checkpoints"
    if os.path.exists(path):
        shutil.rmtree(path)

print(os.listdir("data/train"))
print(os.listdir("data/val"))
print(os.listdir("data/test"))

from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
import torchvision.transforms as transforms

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

train_dataset = ImageFolder("data/train", transform=transform)
val_dataset = ImageFolder("data/val", transform=transform)
test_dataset = ImageFolder("data/test", transform=transform)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=16)
test_loader = DataLoader(test_dataset, batch_size=16)

print(train_dataset.classes)

import torchvision.models as models
import torch.nn as nn

model = models.resnet18(pretrained=True)
model.fc = nn.Linear(512, 2)

import torch
print(torch.cuda.is_available())

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

print(device)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=2)

import torch

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

for epoch in range(10):
    model.train()
    total_loss = 0

    for images, labels in train_loader:
        images = images.to(device)
        labels = labels.to(device)

        outputs = model(images)
        loss = criterion(outputs, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader)}")

correct = 0
total = 0

model.eval()

with torch.no_grad():
    for images, labels in test_loader:
        images = images.to(device)   # ✅ move to GPU
        labels = labels.to(device)   # ✅ move to GPU

        outputs = model(images)
        _, predicted = torch.max(outputs, 1)

        total += labels.size(0)
        correct += (predicted == labels).sum().item()

accuracy = correct / total
print("Test Accuracy:", accuracy)

class EHRModel(nn.Module):
    def __init__(self):
        super(EHRModel, self).__init__()
        self.feature = nn.Sequential(
            nn.Linear(6, 128),
            nn.ReLU(),
            nn.Linear(128, 64)
        )

    def forward(self, x):
        return self.feature(x)

import torchvision.models as models

cnn = models.resnet18(pretrained=True)
cnn.fc = nn.Identity()  # remove final layer

class MultiModalModel(nn.Module):
    def __init__(self, ehr_model, cnn_model):
        super(MultiModalModel, self).__init__()
        self.ehr = ehr_model
        self.cnn = cnn_model

        self.classifier = nn.Sequential(
            nn.Linear(64 + 512, 128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )

    def forward(self, ehr_data, image):
        ehr_features = self.ehr(ehr_data)
        img_features = self.cnn(image)

        combined = torch.cat((ehr_features, img_features), dim=1)
        return self.classifier(combined)

model = MultiModalModel(EHRModel(), cnn).to(device)

image_batch = next(iter(train_loader))[0]
ehr_batch = X_train[:len(image_batch)]
labels_batch = y_train[:len(image_batch)]

for epoch in range(5):
    model.train()

    for i, (images, _) in enumerate(train_loader):
        images = images.to(device)

        # Match EHR batch properly
        start = i * images.size(0)
        end = start + images.size(0)

        ehr_batch = X_train[start:end].to(device)
        labels = y_train[start:end].to(device)

        # Skip if mismatch (last batch safety)
        if ehr_batch.size(0) != images.size(0):
            continue

        outputs = model(ehr_batch, images)
        loss = criterion(outputs, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    print(f"Epoch {epoch+1}, Loss: {loss.item()}")

correct = 0
total = 0

model.eval()

with torch.no_grad():
    for images, _ in test_loader:
        images = images.to(device)

        batch_size = images.size(0)

        # Force exact matching size
        ehr_batch = X_test[:batch_size].clone().detach().to(device)
        labels = y_test[:batch_size].clone().detach().to(device)

        # Safety check (VERY IMPORTANT)
        if ehr_batch.size(0) != images.size(0):
            min_size = min(ehr_batch.size(0), images.size(0))
            ehr_batch = ehr_batch[:min_size]
            images = images[:min_size]
            labels = labels[:min_size]

        outputs = model(ehr_batch, images)
        _, predicted = torch.max(outputs, 1)

        total += labels.size(0)
        correct += (predicted == labels).sum().item()

accuracy = correct / total
print("Multimodal Accuracy:", accuracy)


from transformers import BertTokenizer, BertForSequenceClassification
import torch

from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
model = AutoModelForSequenceClassification.from_pretrained(
    "emilyalsentzer/Bio_ClinicalBERT",
    num_labels=2
)

texts = [
    "Patient has chest pain and shortness of breath",
    "High fever and persistent cough",
    "Normal condition, no symptoms",
    "Irregular heartbeat and fatigue",
    "Severe headache and dizziness",
    "Low blood pressure and weakness",
    "Stable condition, no issues"
]

labels = [1, 1, 0, 1, 1, 1, 0]

inputs = tokenizer(
    texts,
    padding=True,
    truncation=True,
    return_tensors="pt"
)

labels = torch.tensor(labels)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = model.to(device)
inputs = {k: v.to(device) for k, v in inputs.items()}
labels = labels.to(device)

optimizer = torch.optim.Adam(model.parameters(), lr=2e-5)

for epoch in range(5):
    model.train()

    outputs = model(**inputs, labels=labels)
    loss = outputs.loss

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    print(f"Epoch {epoch+1}, Loss: {loss.item()}")

model.eval()

with torch.no_grad():
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=1)

print("Predictions:", predictions)
print("Actual:", labels)

new_text = ["Patient experiencing chest pain and high blood pressure"]

new_inputs = tokenizer(
    new_text,
    return_tensors="pt",
    padding=True,
    truncation=True
).to(device)

outputs = model(**new_inputs)
prediction = torch.argmax(outputs.logits, dim=1)

print("Prediction:", prediction.item())

import pandas as pd

df = pd.read_csv("/content/data/LUSCexpfile.csv", sep=";")
print(df.shape)

df = df.set_index(df.columns[0])  # first column = gene names

df = df.T
print(df.shape)

df.reset_index(drop=True, inplace=True)

df['label'] = 1  # all cancer

df = df.apply(pd.to_numeric, errors='coerce')

df = df.fillna(0)

df = df.astype(float)

import numpy as np

normal_data = df.iloc[:100].copy()

# ✅ Now this will work
normal_data.iloc[:, :] = normal_data.iloc[:, :] * np.random.uniform(0.8, 1.2)

normal_data['label'] = 0
df['label'] = 1

df = pd.concat([df, normal_data], ignore_index=True)

print(df.dtypes.head())

from sklearn.model_selection import train_test_split

X = df.drop("label", axis=1)
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

import torch

X_train = torch.tensor(X_train.values, dtype=torch.float32)
X_test = torch.tensor(X_test.values, dtype=torch.float32)

y_train = torch.tensor(y_train.values, dtype=torch.long)
y_test = torch.tensor(y_test.values, dtype=torch.long)

import torch.nn as nn

class GenomicModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.ReLU(),

            nn.Linear(64, 2)
        )

    def forward(self, x):
        return self.net(x)

model = GenomicModel(X_train.shape[1])

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

for epoch in range(30):
    model.train()

    outputs = model(X_train)
    loss = criterion(outputs, y_train)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    print(f"Epoch {epoch+1}, Loss: {loss.item()}")

model.eval()

with torch.no_grad():
    outputs = model(X_test)
    _, predicted = torch.max(outputs, 1)

    accuracy = (predicted == y_test).sum().item() / len(y_test)

print("Genomic Accuracy:", accuracy)

from sklearn.metrics import confusion_matrix

cm = confusion_matrix(y_test, predicted)
print(cm)