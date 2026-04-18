"""
Semantic Analysis Module using Legal-BERT
For deep contextual understanding of legal text
"""

import torch
from typing import List, Dict, Optional
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import LEGAL_BERT_MODEL


class SemanticAnalyzer:
    """Legal-BERT based semantic analyzer for legal text"""
    
    def __init__(self, use_legal_bert: bool = True):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_legal_bert = use_legal_bert
        
        # Initialize models (lazy loading)
        self._legal_bert_tokenizer = None
        self._legal_bert_model = None
        self._sentence_model = None
    
    @property
    def legal_bert_tokenizer(self):
        """Lazy load Legal-BERT tokenizer"""
        if self._legal_bert_tokenizer is None:
            print("Loading Legal-BERT tokenizer...")
            self._legal_bert_tokenizer = AutoTokenizer.from_pretrained(LEGAL_BERT_MODEL)
        return self._legal_bert_tokenizer
    
    @property
    def legal_bert_model(self):
        """Lazy load Legal-BERT model"""
        if self._legal_bert_model is None:
            print("Loading Legal-BERT model...")
            self._legal_bert_model = AutoModel.from_pretrained(LEGAL_BERT_MODEL)
            self._legal_bert_model.to(self.device)
            self._legal_bert_model.eval()
        return self._legal_bert_model
    
    @property
    def sentence_model(self):
        """Lazy load sentence transformer model"""
        if self._sentence_model is None:
            print("Loading Sentence Transformer...")
            # Use a general model or legal-specific if available
            self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._sentence_model
    
    def get_legal_bert_embedding(self, text: str) -> np.ndarray:
        """Get Legal-BERT embedding for a text"""
        # Tokenize
        inputs = self.legal_bert_tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            max_length=512,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get embeddings
        with torch.no_grad():
            outputs = self.legal_bert_model(**inputs)
            # Use [CLS] token embedding
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        
        return embedding.flatten()
    
    def get_sentence_embedding(self, text: str) -> np.ndarray:
        """Get sentence embedding using sentence-transformers"""
        embedding = self.sentence_model.encode(text)
        return embedding
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        emb1 = self.get_sentence_embedding(text1)
        emb2 = self.get_sentence_embedding(text2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def find_similar_clauses(self, target_clause: str, all_clauses: List[str], top_k: int = 3) -> List[Dict]:
        """Find most similar clauses to a target clause"""
        target_emb = self.get_sentence_embedding(target_clause)
        all_embeddings = [self.get_sentence_embedding(c) for c in all_clauses]
        
        similarities = []
        for i, emb in enumerate(all_embeddings):
            sim = np.dot(target_emb, emb) / (np.linalg.norm(target_emb) * np.linalg.norm(emb))
            similarities.append({
                'index': i,
                'clause': all_clauses[i],
                'similarity': float(sim)
            })
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_k]
    
    def detect_contradictions(self, clauses: List[str], threshold: float = 0.3) -> List[Dict]:
        """Detect potential contradictions between clauses"""
        # This is a simplified approach - looks for clauses that are somewhat similar
        # but contain opposing terms
        
        contradictions = []
        opposing_terms = [
            ('shall', 'shall not'),
            ('must', 'must not'),
            ('will', 'will not'),
            ('can', 'cannot'),
            ('allow', 'prohibit'),
            ('include', 'exclude'),
        ]
        
        for i, clause1 in enumerate(clauses):
            for j, clause2 in enumerate(clauses):
                if i >= j:
                    continue
                
                # Check semantic similarity
                similarity = self.calculate_similarity(clause1, clause2)
                
                # If somewhat similar, check for opposing terms
                if similarity > threshold:
                    for pos, neg in opposing_terms:
                        if (pos in clause1.lower() and neg in clause2.lower()) or \
                           (neg in clause1.lower() and pos in clause2.lower()):
                            contradictions.append({
                                'clause1_index': i,
                                'clause2_index': j,
                                'clause1': clause1,
                                'clause2': clause2,
                                'similarity': similarity,
                                'potential_conflict': f'{pos} vs {neg}'
                            })
        
        return contradictions
    
    def analyze_clause_semantics(self, clause: str) -> Dict:
        """Perform semantic analysis on a single clause"""
        # Get embeddings
        embedding = self.get_sentence_embedding(clause)
        
        # Analyze semantic features
        analysis = {
            'embedding_norm': float(np.linalg.norm(embedding)),
            'embedding_mean': float(np.mean(embedding)),
            'embedding_std': float(np.std(embedding)),
        }
        
        # Check against standard legal phrases for context
        standard_phrases = {
            'confidentiality': 'The parties agree to keep all information confidential.',
            'termination': 'Either party may terminate this agreement with written notice.',
            'liability': 'Neither party shall be liable for indirect damages.',
            'indemnification': 'The party shall indemnify and hold harmless the other party.',
        }
        
        context_similarities = {}
        for context, phrase in standard_phrases.items():
            sim = self.calculate_similarity(clause, phrase)
            context_similarities[context] = round(sim, 3)
        
        analysis['context_classification'] = max(context_similarities, key=context_similarities.get)
        analysis['context_scores'] = context_similarities
        
        return analysis
