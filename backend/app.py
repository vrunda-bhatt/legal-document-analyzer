"""
Flask API for Legal Document Ambiguity Detection
Main application entry point
"""

import os
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (
    UPLOAD_FOLDER, RESULTS_FOLDER, 
    MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS
)
from backend.preprocessor import LegalTextPreprocessor
from backend.ambiguity_detector import AmbiguityDetector
from backend.ml_classifier import MLClassifier
# SemanticAnalyzer imported lazily to avoid Keras/TF compatibility issues at startup


# Initialize Flask app
app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

# Initialize components
preprocessor = LegalTextPreprocessor()
ambiguity_detector = AmbiguityDetector()
ml_classifier = MLClassifier()
semantic_analyzer = None  # Lazy load due to model size


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_semantic_analyzer():
    """Lazy load semantic analyzer"""
    global semantic_analyzer
    if semantic_analyzer is None:
        try:
            from backend.semantic_analyzer import SemanticAnalyzer
            semantic_analyzer = SemanticAnalyzer()
        except Exception as e:
            print(f"Warning: Could not load SemanticAnalyzer: {e}")
            semantic_analyzer = None
    return semantic_analyzer


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and analysis"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PDF, TXT'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    saved_filename = f"{timestamp}_{filename}"
    file_path = Path(app.config['UPLOAD_FOLDER']) / saved_filename
    file.save(str(file_path))
    
    # Process document
    try:
        result = analyze_document(str(file_path))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/analyze', methods=['POST'])
def analyze_text():
    """Analyze text directly (without file upload)"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text = data['text']
    
    try:
        result = analyze_text_content(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/compare-documents', methods=['POST'])
def compare_documents():
    """Compare two uploaded documents and return side-by-side risk analysis"""
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({'error': 'Please upload both documents'}), 400

    file1 = request.files['file1']
    file2 = request.files['file2']

    if file1.filename == '' or file2.filename == '':
        return jsonify({'error': 'Please select both files'}), 400

    if not allowed_file(file1.filename) or not allowed_file(file2.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PDF, TXT'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file1_name = secure_filename(file1.filename)
    file2_name = secure_filename(file2.filename)

    file1_path = Path(app.config['UPLOAD_FOLDER']) / f"{timestamp}_doc1_{file1_name}"
    file2_path = Path(app.config['UPLOAD_FOLDER']) / f"{timestamp}_doc2_{file2_name}"

    file1.save(str(file1_path))
    file2.save(str(file2_path))

    try:
        result1 = analyze_document(str(file1_path), save_csv=False)
        result2 = analyze_document(str(file2_path), save_csv=False)

        score1 = result1['overall_risk_score']
        score2 = result2['overall_risk_score']

        if score1 > score2:
            higher_risk_document = 'document_1'
            higher_risk_filename = result1['filename']
        elif score2 > score1:
            higher_risk_document = 'document_2'
            higher_risk_filename = result2['filename']
        else:
            higher_risk_document = 'tie'
            higher_risk_filename = None

        return jsonify({
            'document_1': result1,
            'document_2': result2,
            'higher_risk_document': higher_risk_document,
            'higher_risk_filename': higher_risk_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def analyze_document(file_path: str, save_csv: bool = True) -> dict:
    """Main analysis pipeline for uploaded document"""
    # Step 1: Preprocess document
    processed = preprocessor.preprocess_document(file_path)
    
    # Step 2: Analyze each clause
    analyzed_clauses = []
    
    for clause_data in processed['clauses']:
        clause_text = clause_data['text']
        
        # Rule-based analysis
        rule_analysis = ambiguity_detector.analyze_clause(clause_text)
        
        # ML prediction
        ml_prediction = ml_classifier.predict_single(clause_text)
        
        # Combine results: weight rule-based (60%) + ML (40%)
        # ML score: use ambiguous probability if predicted ambiguous, else invert
        ml_score = ml_prediction['probability_ambiguous'] * 100 if ml_prediction['is_ambiguous'] else (1 - ml_prediction['probability_clear']) * 100
        combined_score = (rule_analysis['ambiguity_score'] * 0.6) + (ml_score * 0.4)
        
        analyzed_clauses.append({
            'id': clause_data['id'],
            'label': clause_data.get('label', str(clause_data['id'])),
            'text': clause_text,
            'rule_based': rule_analysis,
            'ml_prediction': ml_prediction,
            'combined_score': round(combined_score, 2),
            'final_risk_level': determine_risk_level(combined_score)
        })
    
    # Sort by risk (highest first)
    analyzed_clauses.sort(key=lambda x: x['combined_score'], reverse=True)
    
    if save_csv:
        save_results(analyzed_clauses, file_path)

    overall_risk_score = round(
        sum(c['combined_score'] for c in analyzed_clauses) / len(analyzed_clauses), 2
    ) if analyzed_clauses else 0.0

    return {
        'filename': Path(file_path).name,
        'total_clauses': len(analyzed_clauses),
        'high_risk_count': sum(1 for c in analyzed_clauses if c['final_risk_level'] == 'high'),
        'medium_risk_count': sum(1 for c in analyzed_clauses if c['final_risk_level'] == 'medium'),
        'low_risk_count': sum(1 for c in analyzed_clauses if c['final_risk_level'] == 'low'),
        'overall_risk_score': overall_risk_score,
        'overall_risk_level': determine_risk_level(overall_risk_score),
        'clauses': analyzed_clauses
    }


def analyze_text_content(text: str) -> dict:
    """Analyze text content directly"""
    # Segment text into clauses
    clauses = preprocessor.segment_into_clauses(preprocessor.clean_text(text))
    
    analyzed_clauses = []
    
    for i, clause_text in enumerate(clauses):
        # Rule-based analysis
        rule_analysis = ambiguity_detector.analyze_clause(clause_text)
        
        # ML prediction
        ml_prediction = ml_classifier.predict_single(clause_text)
        
        # Combine results: weight rule-based (60%) + ML (40%)
        ml_score = ml_prediction['probability_ambiguous'] * 100 if ml_prediction['is_ambiguous'] else (1 - ml_prediction['probability_clear']) * 100
        combined_score = (rule_analysis['ambiguity_score'] * 0.6) + (ml_score * 0.4)
        
        analyzed_clauses.append({
            'id': i + 1,
            'label': str(i + 1),  # Sequential numbering for manual text input
            'text': clause_text,
            'rule_based': rule_analysis,
            'ml_prediction': ml_prediction,
            'combined_score': round(combined_score, 2),
            'final_risk_level': determine_risk_level(combined_score)
        })
    
    # Sort by risk (highest first)
    analyzed_clauses.sort(key=lambda x: x['combined_score'], reverse=True)
    
    overall_risk_score = round(
        sum(c['combined_score'] for c in analyzed_clauses) / len(analyzed_clauses), 2
    ) if analyzed_clauses else 0.0

    return {
        'total_clauses': len(analyzed_clauses),
        'high_risk_count': sum(1 for c in analyzed_clauses if c['final_risk_level'] == 'high'),
        'medium_risk_count': sum(1 for c in analyzed_clauses if c['final_risk_level'] == 'medium'),
        'low_risk_count': sum(1 for c in analyzed_clauses if c['final_risk_level'] == 'low'),
        'overall_risk_score': overall_risk_score,
        'overall_risk_level': determine_risk_level(overall_risk_score),
        'clauses': analyzed_clauses
    }


def determine_risk_level(score: float) -> str:
    """Determine risk level from combined score"""
    if score >= 70:
        return 'high'
    elif score >= 40:
        return 'medium'
    else:
        return 'low'


def save_results(clauses: list, source_file: str):
    """Save analysis results to CSV"""
    df = pd.DataFrame([
        {
            'clause_id': c['id'],
            'text': c['text'],
            'rule_based_score': c['rule_based']['ambiguity_score'],
            'ml_confidence': c['ml_prediction']['confidence'],
            'combined_score': c['combined_score'],
            'risk_level': c['final_risk_level'],
            'issues_count': c['rule_based']['total_issues']
        }
        for c in clauses
    ])
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    source_name = Path(source_file).stem
    result_path = RESULTS_FOLDER / f"{source_name}_{timestamp}_results.csv"
    df.to_csv(result_path, index=False)


if __name__ == '__main__':
    # Load ML model if available
    ml_classifier.load_model()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
