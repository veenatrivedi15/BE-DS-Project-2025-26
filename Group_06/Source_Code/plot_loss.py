import json
import re
import matplotlib.pyplot as plt

def extract_and_plot():
    with open('ProjectMajor.ipynb', 'r', encoding='utf-8') as f:
        notebook = json.load(f)
        
    all_output_text = ""
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = "".join(cell.get('source', []))
            
            for out in cell.get('outputs', []):
                if 'text' in out:
                    all_output_text += "".join(out.get('text', [])) + "\n"
    
    # The multimodal model training output looks like:
    # Epoch 1, Loss: 0....
    # Epoch 2, Loss: 0....
    # We know there are multiple models trained.
    # The multimodal model has exactly 5 epochs based on notebook_code.py line 680 (for epoch in range(5):)
    # The NLP model also has 5 epochs line 778.
    # Let's uniquely identify multimodal if possible, or just parse all 'Epoch X, Loss: Y'
    
    blocks = re.split(r'Epoch 1, Loss:', all_output_text)
    for block in blocks[1:]:
        text = "Epoch 1, Loss:" + block
        matches = re.findall(r'Epoch (\d+), Loss: ([\d\.]+)', text)
        if len(matches) == 5: # found a 5-epoch training loop block
            # there are two 5-epoch blocks: Multimodal and NLP.
            # print it out
            print("Found block with 5 epochs:", matches)
            # NLP model loss might be large or small, multimodal too.
            # Let's plot both just in case and save.
        elif matches:
            pass # other blocks

extract_and_plot()
