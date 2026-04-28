import io
import base64
import numpy as np
import cv2
import torch
from pytorch_grad_cam import HiResCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

def generate_gradcam(model, input_tensor, rgb_image, target_category_idx=None):
    # Select the target layer corresponding to the last convolutional layer of ResNet18
    target_layers = [model.resnet.layer4[-1]]
    
    # Construct the CAM object
    # We use HiResCAM which is mathematically proven to align correctly compared to standard GradCAM
    cam = HiResCAM(model=model, target_layers=target_layers)

    # If no category index is provided (or if predicting top), 
    # pytorch-grad-cam will automatically use the highest scoring category
    targets = None 
    if target_category_idx is not None:
        targets = [ClassifierOutputTarget(target_category_idx)]

    # Generate the heatmap covering the spatial features
    # Enable test-time augmentation mapping and eigen smoothing for sharper, on-target localization
    grayscale_cam = cam(input_tensor=input_tensor, targets=targets, aug_smooth=True, eigen_smooth=True)[0, :]
    
    # Original image needs to be float [0, 1] for show_cam_on_image
    rgb_image_resized = cv2.resize(np.array(rgb_image), (224, 224))
    rgb_image_float = np.float32(rgb_image_resized) / 255
    
    # Overlay heatmap onto the RGB image
    visualization = show_cam_on_image(rgb_image_float, grayscale_cam, use_rgb=True)
    
    # Convert image to base64 for direct HTML rendering
    is_success, buffer = cv2.imencode(".png", cv2.cvtColor(visualization, cv2.COLOR_RGB2BGR))
    io_buf = io.BytesIO(buffer)
    base64_img = base64.b64encode(io_buf.getvalue()).decode('utf-8')
    
    return base64_img, grayscale_cam
