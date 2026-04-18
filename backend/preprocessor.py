"""
Text Preprocessing and Clause Segmentation Module
Uses spaCy and NLTK for legal text processing
"""

import spacy
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
import re
from typing import List, Dict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import SPACY_MODEL


class LegalTextPreprocessor:
    """Preprocessor for legal documents - clause segmentation and text cleaning"""
    
    def __init__(self):
        # Load spaCy model
        self.nlp = spacy.load(SPACY_MODEL)
        
        # Load NLTK resources
        self.stop_words = set(stopwords.words('english'))
        
        # Legal clause indicators
        self.clause_indicators = [
            r'\d+\.\d+',  # Numbered clauses like 1.1, 2.3
            r'\d+\)',     # Numbered like 1), 2)
            r'\([a-z]\)', # Lettered like (a), (b)
            r'^[A-Z][A-Z\s]+:',  # SECTION HEADERS:
            r'(?:Section|Article|Clause)\s+\d+',  # Section 1, Article 2
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file"""
        from PyPDF2 import PdfReader
        
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize legal text"""
        # Normalize whitespace but preserve newlines for segmentation
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Remove special characters but keep legal punctuation and $ for prices
        text = re.sub(r'[^\w\s.,;:()"\'\-$@/]', '', text)
        return text.strip()
    
    def extract_clause_labels(self, text: str) -> List[tuple]:
        """Extract clauses with their document labels (e.g., '4.1', '5.3')"""
        clause_tuples = []  # List of (label, text) tuples
        
        # Pattern to match clause numbers at line start: 4.1, 5.3, 1), (a), etc.
        patterns = [
            (r'^(\d+\.\d+)\s+', 'dotted'),        # 4.1 text
            (r'^(\d+)\)\s+', 'paren'),             # 1) text
            (r'^\(([a-z])\)\s+', 'letter'),       # (a) text
        ]
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            matched = False
            # Try to extract label from start of line
            for pattern, ptype in patterns:
                match = re.match(pattern, line)
                if match:
                    label = match.group(1)
                    clause_text = line[match.end():].strip()
                    if len(clause_text.split()) > 5:  # Only keep meaningful clauses
                        clause_tuples.append((label, clause_text))
                    matched = True
                    break
            
            # If no label found, skip or use generic numbering
            if not matched and len(line.split()) > 5:
                # Can still process text-only clauses without labels
                pass
        
        return clause_tuples
    
    def segment_into_clauses(self, text: str) -> List[str]:
        """Segment legal document into individual clauses (returns text only)"""
        clauses = []
        
        # Step 1: Split by newlines first (user often separates clauses by line)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Step 2: If multiple non-empty lines exist, treat each line as potential clause(s)
        if len(lines) > 1:
            for line in lines:
                # Further split each line by sentences if it contains multiple
                sentences = sent_tokenize(line)
                clauses.extend(sentences)
        else:
            # Single block of text - try numbered patterns first
            pattern = r'(?=(?:^|\s)\d+\.\d+\s|\d+\)\s|(?:Section|Article|Clause)\s+\d+)'
            segments = re.split(pattern, text)
            
            if len(segments) > 1:
                clauses = [s.strip() for s in segments if s.strip()]
            else:
                # Fall back to sentence-based segmentation
                sentences = sent_tokenize(text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        clauses.append(sentence)
        
        # Filter out very short segments (less than 5 words)
        clauses = [c for c in clauses if len(c.split()) > 5]
        
        return clauses
    
    def extract_linguistic_features(self, text: str) -> Dict:
        """Extract linguistic features using spaCy"""
        doc = self.nlp(text)
        
        features = {
            'tokens': [token.text for token in doc],
            'pos_tags': [(token.text, token.pos_) for token in doc],
            'entities': [(ent.text, ent.label_) for ent in doc.ents],
            'noun_chunks': [chunk.text for chunk in doc.noun_chunks],
            'has_passive': self._detect_passive_voice(doc),
            'modal_verbs': self._extract_modal_verbs(doc),
            'negations': self._extract_negations(doc),
        }
        
        return features
    
    def _detect_passive_voice(self, doc) -> bool:
        """Detect passive voice constructions"""
        for token in doc:
            if token.dep_ == 'nsubjpass':
                return True
        return False
    
    def _extract_modal_verbs(self, doc) -> List[str]:
        """Extract modal verbs (may, might, could, should, etc.)"""
        modals = ['may', 'might', 'could', 'should', 'would', 'can', 'shall']
        found = [token.text.lower() for token in doc if token.text.lower() in modals]
        return found
    
    def _extract_negations(self, doc) -> List[str]:
        """Extract negation words"""
        negations = [token.text for token in doc if token.dep_ == 'neg']
        return negations
    
    def preprocess_document(self, file_path: str) -> Dict:
        """Main preprocessing pipeline for a legal document"""
        # Extract text based on file type
        if file_path.endswith('.pdf'):
            text = self.extract_text_from_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        # Clean text
        cleaned_text = self.clean_text(text)
        
        # Try to extract clauses with labels first
        clause_tuples = self.extract_clause_labels(cleaned_text)
        
        # Extract features for each clause
        processed_clauses = []
        if clause_tuples:
            # Use labeled clauses
            for label, clause_text in clause_tuples:
                features = self.extract_linguistic_features(clause_text)
                processed_clauses.append({
                    'id': label,
                    'label': label,
                    'text': clause_text,
                    'features': features
                })
        else:
            # Fall back to generic numbering if no labels found
            clauses = self.segment_into_clauses(cleaned_text)
            for i, clause in enumerate(clauses):
                features = self.extract_linguistic_features(clause)
                processed_clauses.append({
                    'id': i + 1,
                    'label': str(i + 1),
                    'text': clause,
                    'features': features
                })
        
        return {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'clauses': processed_clauses,
            'total_clauses': len(processed_clauses)
        }
