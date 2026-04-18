import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Paths
UPLOAD_FOLDER = BASE_DIR / 'data' / 'uploads'
RESULTS_FOLDER = BASE_DIR / 'data' / 'results'
TRAINING_DATA = BASE_DIR / 'data' / 'training'
MODEL_PATH = BASE_DIR / 'models'

# Create folders if not exist
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, TRAINING_DATA, MODEL_PATH]:
    folder.mkdir(parents=True, exist_ok=True)

# Model configurations
SPACY_MODEL = 'en_core_web_sm'
LEGAL_BERT_MODEL = 'nlpaueb/legal-bert-base-uncased'

# Flask configurations
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

# ML parameters
RANDOM_STATE = 42
TEST_SIZE = 0.2
