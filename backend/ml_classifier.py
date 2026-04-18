"""
Machine Learning Classifier Module
TF-IDF Vectorizer + SVM for ambiguity classification
"""

import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import MODEL_PATH, TRAINING_DATA, RANDOM_STATE, TEST_SIZE


class MLClassifier:
    """SVM-based classifier for legal clause ambiguity detection"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            stop_words='english',
            min_df=2,
            max_df=0.95
        )
        
        self.classifier = SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            probability=True,
            random_state=RANDOM_STATE
        )
        
        self.is_trained = False
        self.model_path = MODEL_PATH / 'svm_model.pkl'
        self.vectorizer_path = MODEL_PATH / 'tfidf_vectorizer.pkl'
    
    def prepare_features(self, texts: List[str]) -> np.ndarray:
        """Convert texts to TF-IDF features"""
        if self.is_trained:
            return self.vectorizer.transform(texts)
        else:
            return self.vectorizer.fit_transform(texts)
    
    def train(self, texts: List[str], labels: List[int]) -> Dict:
        """Train the SVM classifier"""
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, 
            test_size=TEST_SIZE, 
            random_state=RANDOM_STATE,
            stratify=labels
        )
        
        # Vectorize
        X_train_tfidf = self.vectorizer.fit_transform(X_train)
        X_test_tfidf = self.vectorizer.transform(X_test)
        
        # Train classifier
        self.classifier.fit(X_train_tfidf, y_train)
        self.is_trained = True
        
        # Evaluate
        y_pred = self.classifier.predict(X_test_tfidf)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # Save models
        self.save_model()
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
    
    def predict(self, texts: List[str]) -> List[Dict]:
        """Predict ambiguity for given texts"""
        if not self.is_trained:
            self.load_model()
        
        if not self.is_trained:
            # Return default predictions if no model
            return [{'label': 0, 'confidence': 0.5, 'is_ambiguous': False} for _ in texts]
        
        # Vectorize and predict
        X_tfidf = self.vectorizer.transform(texts)
        predictions = self.classifier.predict(X_tfidf)
        probabilities = self.classifier.predict_proba(X_tfidf)
        
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            results.append({
                'label': int(pred),
                'confidence': float(max(prob)),
                'is_ambiguous': bool(pred == 1),
                'probability_clear': float(prob[0]) if len(prob) > 0 else 0.5,
                'probability_ambiguous': float(prob[1]) if len(prob) > 1 else 0.5
            })
        
        return results
    
    def predict_single(self, text: str) -> Dict:
        """Predict ambiguity for a single text"""
        results = self.predict([text])
        return results[0]
    
    def save_model(self):
        """Save trained model and vectorizer to disk"""
        MODEL_PATH.mkdir(parents=True, exist_ok=True)
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.classifier, f)
        
        with open(self.vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        
        print(f"Model saved to {self.model_path}")
    
    def load_model(self) -> bool:
        """Load trained model and vectorizer from disk"""
        try:
            if self.model_path.exists() and self.vectorizer_path.exists():
                with open(self.model_path, 'rb') as f:
                    self.classifier = pickle.load(f)
                
                with open(self.vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                
                self.is_trained = True
                print("Model loaded successfully")
                return True
        except Exception as e:
            print(f"Error loading model: {e}")
        
        return False
    
    def train_from_csv(self, csv_path: str, text_column: str = 'text', label_column: str = 'label') -> Dict:
        """Train model from a CSV file"""
        df = pd.read_csv(csv_path)
        
        texts = df[text_column].tolist()
        labels = df[label_column].tolist()
        
        return self.train(texts, labels)


# Sample training data generator (for demo/testing)
def generate_sample_training_data() -> Tuple[List[str], List[int]]:
    """Generate sample training data for demonstration"""
    
    # Clear/unambiguous clauses (label = 0)
    clear_clauses = [
        "The Seller shall deliver the goods within 30 days of receiving payment.",
        "Payment is due on the first day of each month.",
        "The contract term is 12 months starting from January 1, 2026.",
        "The buyer must provide written notice 60 days before termination.",
        "The service fee is $500 per month, payable in advance.",
        "All disputes shall be resolved in the courts of New York.",
        "The warranty period is 24 months from the date of purchase.",
        "The licensee may use the software on up to 5 devices.",
    ]
    
    # Ambiguous clauses (label = 1)
    ambiguous_clauses = [
        "The seller shall deliver the goods within a reasonable time.",
        "Payment terms may be adjusted at the company's sole discretion.",
        "Services will be provided in a timely and satisfactory manner.",
        "The company reserves the right to modify these terms at any time.",
        "Adequate notice shall be given before any material changes.",
        "Best efforts will be made to resolve issues promptly.",
        "The product should generally meet industry standards.",
        "Compensation may be provided for substantial inconvenience.",
    ]
    
    texts = clear_clauses + ambiguous_clauses
    labels = [0] * len(clear_clauses) + [1] * len(ambiguous_clauses)
    
    return texts, labels
