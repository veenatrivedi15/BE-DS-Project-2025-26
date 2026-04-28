import json
import re

def extract_losses():
    with open('ProjectMajor.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for i, cell in enumerate(nb.get('cells', [])):
        if 'outputs' in cell:
            text = ""
            for out in cell['outputs']:
                if 'text' in out:
                    text += "".join(out['text'])
            
            matches = re.findall(r'Epoch (\d+), Loss: ([\d\.]+)', text)
            if matches:
                source = "".join(cell.get('source', []))
                print(f"CELL_{i}")
                print(f"SOURCE_START: {source[:100]}")
                print(f"EPOCHS: {len(matches)}")
                print(f"LOSSES: {[float(m[1]) for m in matches]}")
                print("="*30)

extract_losses()
