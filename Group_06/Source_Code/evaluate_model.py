import os
import io
import sys
from models.cnn_model import get_cnn_model, preprocess_image, predict_cnn

model = get_cnn_model()

with open('eval_out.txt', 'w', encoding='utf-8') as f:
    f.write("Evaluating 5 images from each test class:\n")
    for cls in sorted(os.listdir('data/test/')):
        cls_path = os.path.join('data/test', cls)
        if not os.path.isdir(cls_path): continue
        imgs = os.listdir(cls_path)[:5]
        f.write(f"\n--- True Class: {cls} ---\n")
        print(f"Processing {cls}...")
        for img in imgs:
            tensor, _ = preprocess_image(os.path.join(cls_path, img))
            results, _ = predict_cnn(model, tensor)
            p = results[0]
            f.write(f"{img}: Pred = {p['condition']} ({p['probability']}%)\n")

print("Done evaluating.")
