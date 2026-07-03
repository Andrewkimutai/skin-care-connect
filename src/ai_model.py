"""
ai_model.py
Loads the trained ResNet50-based classifier and runs inference on uploaded
skin lesion images.

IMPORTANT — MODEL LIMITATIONS
This classifier was trained on HAM10000, a class-imbalanced dataset
(~67% of samples are melanocytic nevi). Evaluation showed strong recall on
the majority class but low recall on minority classes, including Melanoma
(~3% recall on the held-out split — see docs/classification_report.txt).
This is a research/academic prototype and must NOT be treated as a
diagnostic tool. See the in-app disclaimer and README for details.
"""
import os
from pathlib import Path

import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR / "models" / "skin_disease_model.h5"))

CLASS_NAMES_VERBOSE = [
    'Actinic Keratosis', 'Basal Cell Carcinoma', 'Benign Keratosis',
    'Dermatofibroma', 'Melanoma', 'Melanocytic Nevi', 'Vascular Lesion'
]
IMAGE_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 30.0
SKIN_COLOR_THRESHOLD = 0.05
# --- End Configuration ---

_model = None


def load_model_once():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found at: {MODEL_PATH}. "
                "If deploying, make sure the .h5 file was included in the "
                "build (or set MODEL_PATH to point to it)."
            )
        _model = load_model(MODEL_PATH)
    return _model


def is_skin_color_heuristic(image, skin_color_threshold=SKIN_COLOR_THRESHOLD):
    """Cheap pre-filter: rejects obviously non-skin images before running
    the (much more expensive) CNN forward pass."""
    try:
        if isinstance(image, Image.Image):
            image = np.array(image)
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        lower_skin = np.array([0, 48, 80])
        upper_skin = np.array([20, 255, 255])
        skin_mask = cv2.inRange(hsv_image, lower_skin, upper_skin)
        total_pixels = image.shape[0] * image.shape[1]
        skin_pixels = cv2.countNonZero(skin_mask)
        return (skin_pixels / total_pixels) >= skin_color_threshold
    except Exception:
        return False


def preprocess_image_for_prediction(image, target_size=IMAGE_SIZE):
    try:
        if isinstance(image, Image.Image):
            image = np.array(image)
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        image = cv2.resize(image, target_size)
        image = image.astype(np.float32) / 255.0
        return np.expand_dims(image, axis=0)
    except Exception:
        return None


def predict_image(image):
    """
    Classify a single skin lesion image.
    Returns a dict with the prediction, per-class probabilities, and a
    plain-language recommendation. Always non-diagnostic in tone.
    """
    if not is_skin_color_heuristic(image):
        return {
            'predicted_class': 'Non-Skin Image',
            'predicted_class_code': 'non_skin',
            'confidence': 0.0,
            'all_predictions': {name: 0.0 for name in CLASS_NAMES_VERBOSE},
            'error': 'Image does not appear to contain significant skin-colored pixels.',
            'recommendation': 'Please upload a clear, well-lit photo of the skin area of concern.',
            'is_valid_prediction': False,
            'needs_appointment': False
        }

    try:
        model = load_model_once()
        processed_image = preprocess_image_for_prediction(image)
        if processed_image is None:
            return {'error': 'Failed to preprocess image.', 'is_valid_prediction': False,
                     'needs_appointment': False}

        predictions = model.predict(processed_image, verbose=0)
        predicted_class_idx = int(np.argmax(predictions[0]))
        confidence = float(predictions[0][predicted_class_idx] * 100)
        predicted_class_verbose = CLASS_NAMES_VERBOSE[predicted_class_idx]

        all_predictions = {
            CLASS_NAMES_VERBOSE[i]: float(predictions[0][i] * 100)
            for i in range(len(CLASS_NAMES_VERBOSE))
        }

        if confidence < CONFIDENCE_THRESHOLD:
            return {
                'predicted_class': 'Unclassified',
                'predicted_class_code': 'unclassified',
                'confidence': confidence,
                'all_predictions': all_predictions,
                'error': f'Confidence ({confidence:.2f}%) is below the threshold ({CONFIDENCE_THRESHOLD}%).',
                'recommendation': 'The model could not confidently classify this image. Please consult a dermatologist.',
                'is_valid_prediction': False,
                'needs_appointment': True
            }

        needs_appointment = False
        recommendation = f"The model's top match is {predicted_class_verbose} at {confidence:.2f}% confidence. "

        if predicted_class_verbose == "Melanoma":
            recommendation += ("This class is associated with higher risk. Please see a "
                                "dermatologist promptly for a professional evaluation — "
                                "this tool cannot diagnose you.")
            needs_appointment = True
        elif confidence < 60:
            recommendation += "Confidence is moderate — a dermatologist visit is recommended for confirmation."
            needs_appointment = True
        elif confidence < 80:
            recommendation += "Consider a dermatologist visit to confirm this result."
            needs_appointment = True
        else:
            recommendation += "Even at high model confidence, please have any concerning lesion reviewed by a professional."

        return {
            'predicted_class': predicted_class_verbose,
            'predicted_class_code': predicted_class_idx,
            'confidence': confidence,
            'all_predictions': all_predictions,
            'error': None,
            'recommendation': recommendation,
            'is_valid_prediction': True,
            'needs_appointment': needs_appointment
        }
    except Exception as e:
        return {'error': f"An error occurred during prediction: {str(e)}",
                'is_valid_prediction': False, 'needs_appointment': False}
