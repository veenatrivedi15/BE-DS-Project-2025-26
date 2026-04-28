import torch
import torch.nn as nn

class EHRModel(nn.Module):
    def __init__(self, input_features=6):
        super(EHRModel, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_features, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.3),
            
            # Predicts binary state (e.g. Mortality/Expire Flag or Cancer Risk)
            nn.Linear(64, 2)  
        )

    def forward(self, x):
        return self.net(x)

def get_ehr_model():
    model = EHRModel(input_features=6)
    model.eval()
    return model
