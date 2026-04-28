import torch
import torch.nn as nn
import torchvision.models as models

class MultiModalModel(nn.Module):
    def __init__(self, ehr_model, cnn_model, genomic_model):
        super(MultiModalModel, self).__init__()
        # Strip final classification layers to extract raw feature embeddings
        self.ehr = ehr_model
        self.cnn = cnn_model
        self.genomic = genomic_model
        
        # EHR (64) + ResNet18 (512) + Genomic (64) = 640
        self.classifier = nn.Sequential(
            nn.Linear(64 + 512 + 64, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 4) # Expanded to 4 classes to include Lung Cancer
        )

    def forward(self, ehr_data, image_tensor, genomic_data):
        ehr_features = self.ehr(ehr_data)
        img_features = self.cnn(image_tensor)
        genomic_features = self.genomic(genomic_data)

        # Multimodal Fusion (Concatenation of Vectors)
        combined = torch.cat((ehr_features, img_features, genomic_features), dim=1)
        return self.classifier(combined)

def get_multimodal_model(ehr_base, cnn_base, genomic_base):
    # Initializes the fused architecture
    model = MultiModalModel(ehr_base, cnn_base, genomic_base)
    model.eval()
    return model
