import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def get_clinical_bert_model():
    # Instantiate the clinical bert tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    model = AutoModelForSequenceClassification.from_pretrained(
        "emilyalsentzer/Bio_ClinicalBERT",
        num_labels=2
    )
    model.eval()
    return tokenizer, model
