"""
Training Script for SVM Classifier
Trains the TF-IDF + SVM model on the legal clauses dataset
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ml_classifier import MLClassifier
from backend.config import TRAINING_DATA


def main():
    print("=" * 60)
    print("  SVM Model Training - Legal Clause Ambiguity Detection")
    print("=" * 60)
    
    # Initialize classifier
    classifier = MLClassifier()
    
    # Path to training data
    csv_path = TRAINING_DATA / 'legal_clauses.csv'
    
    if not csv_path.exists():
        print(f"\nERROR: Training data not found at {csv_path}")
        return
    
    print(f"\nTraining data: {csv_path}")
    
    # Train the model
    print("\nTraining SVM classifier...")
    print("-" * 40)
    
    results = classifier.train_from_csv(
        str(csv_path),
        text_column='text',
        label_column='label'
    )
    
    # Display results
    print(f"\nAccuracy: {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
    print(f"Training samples: {results['train_size']}")
    print(f"Test samples: {results['test_size']}")
    
    print("\nClassification Report:")
    print("-" * 40)
    
    report = results['classification_report']
    print(f"  {'Class':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
    print(f"  {'-'*50}")
    
    for label in ['0', '1']:
        if label in report:
            r = report[label]
            label_name = 'Clear' if label == '0' else 'Ambiguous'
            print(f"  {label_name:<15} {r['precision']:<12.4f} {r['recall']:<12.4f} {r['f1-score']:<12.4f}")
    
    print(f"\n  {'Macro Avg':<15} {report['macro avg']['precision']:<12.4f} {report['macro avg']['recall']:<12.4f} {report['macro avg']['f1-score']:<12.4f}")
    print(f"  {'Weighted Avg':<15} {report['weighted avg']['precision']:<12.4f} {report['weighted avg']['recall']:<12.4f} {report['weighted avg']['f1-score']:<12.4f}")
    
    print("\n" + "=" * 60)
    print("  Model saved successfully!")
    print(f"  SVM Model: models/svm_model.pkl")
    print(f"  Vectorizer: models/tfidf_vectorizer.pkl")
    print("=" * 60)


if __name__ == '__main__':
    main()
