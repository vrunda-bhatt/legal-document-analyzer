"""
Rule-Based Ambiguity Detection Module
Detects vague terms, passive voice, modal verbs, and other ambiguity indicators
"""

import re
from typing import List, Dict, Tuple


class AmbiguityDetector:
    """Rule-based detector for ambiguous and vague legal language"""
    
    def __init__(self):
        # Vague and ambiguous terms commonly found in legal documents
        self.vague_terms = [
            'reasonable', 'reasonably', 'adequate', 'adequately',
            'appropriate', 'appropriately', 'sufficient', 'sufficiently',
            'material', 'materially', 'substantial', 'substantially',
            'promptly', 'timely', 'soon', 'shortly',
            'best efforts', 'good faith', 'commercially reasonable',
            'as soon as practicable', 'from time to time',
            'including but not limited to', 'and/or',
            'etc', 'such as', 'among other things',
            'generally', 'typically', 'usually', 'normally',
            'may', 'might', 'could', 'should', 'would',
            'significant', 'significantly', 'approximately',
            'satisfactory', 'acceptable', 'unacceptable',
        ]
        
        # Risky phrases that may indicate loopholes
        self.loophole_indicators = [
            'at its sole discretion',
            'reserves the right',
            'without prior notice',
            'subject to change',
            'may be modified',
            'at any time',
            'without cause',
            'notwithstanding',
            'except as otherwise',
            'unless otherwise',
            'to the extent permitted',
            'shall not be liable',
            'in no event shall',
            'limitation of liability',
            'indemnify and hold harmless',
        ]
        
        # Passive voice patterns
        self.passive_patterns = [
            r'\b(?:is|are|was|were|been|being)\s+\w+ed\b',
            r'\b(?:is|are|was|were|been|being)\s+\w+en\b',
        ]
    
    def detect_vague_terms(self, text: str) -> List[Dict]:
        """Detect vague and ambiguous terms in text"""
        findings = []
        text_lower = text.lower()
        
        for term in self.vague_terms:
            if term in text_lower:
                # Find all occurrences
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                matches = pattern.finditer(text)
                
                for match in matches:
                    findings.append({
                        'type': 'vague_term',
                        'term': match.group(),
                        'position': match.start(),
                        'severity': 'medium',
                        'explanation': f'"{match.group()}" is subjective and may lead to different interpretations'
                    })
        
        return findings
    
    def detect_loopholes(self, text: str) -> List[Dict]:
        """Detect potential loophole indicators"""
        findings = []
        text_lower = text.lower()
        
        for phrase in self.loophole_indicators:
            if phrase in text_lower:
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                matches = pattern.finditer(text)
                
                for match in matches:
                    findings.append({
                        'type': 'loophole',
                        'term': match.group(),
                        'position': match.start(),
                        'severity': 'high',
                        'explanation': f'"{match.group()}" may create an unfair advantage or escape clause'
                    })
        
        return findings
    
    def detect_passive_voice(self, text: str) -> List[Dict]:
        """Detect passive voice constructions that obscure responsibility"""
        findings = []
        
        for pattern in self.passive_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                findings.append({
                    'type': 'passive_voice',
                    'term': match.group(),
                    'position': match.start(),
                    'severity': 'low',
                    'explanation': 'Passive voice may obscure who is responsible for an action'
                })
        
        return findings
    
    def detect_missing_definitions(self, text: str) -> List[Dict]:
        """Detect capitalized terms that may need definitions"""
        findings = []
        
        # Find capitalized multi-word phrases (potential defined terms)
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.finditer(pattern, text)
        
        # Common exclusions (not legal terms)
        exclusions = ['United States', 'New York', 'District Court']
        
        for match in matches:
            term = match.group()
            if term not in exclusions:
                findings.append({
                    'type': 'undefined_term',
                    'term': term,
                    'position': match.start(),
                    'severity': 'medium',
                    'explanation': f'"{term}" appears to be a defined term - verify it is properly defined'
                })
        
        return findings
    
    def calculate_ambiguity_score(self, findings: List[Dict]) -> float:
        """Calculate overall ambiguity score based on findings"""
        if not findings:
            return 0.0
        
        severity_weights = {
            'low': 1,
            'medium': 2,
            'high': 3
        }
        
        total_weight = sum(severity_weights.get(f['severity'], 1) for f in findings)
        max_possible = len(findings) * 3  # If all were high severity
        
        # Normalize to 0-100 scale
        score = min((total_weight / max(max_possible, 1)) * 100, 100)
        return round(score, 2)
    
    def analyze_clause(self, clause_text: str) -> Dict:
        """Perform complete rule-based analysis on a clause"""
        all_findings = []
        
        # Run all detection methods
        all_findings.extend(self.detect_vague_terms(clause_text))
        all_findings.extend(self.detect_loopholes(clause_text))
        all_findings.extend(self.detect_passive_voice(clause_text))
        all_findings.extend(self.detect_missing_definitions(clause_text))
        
        # Calculate ambiguity score
        ambiguity_score = self.calculate_ambiguity_score(all_findings)
        
        # Determine risk level
        if ambiguity_score >= 70:
            risk_level = 'high'
        elif ambiguity_score >= 40:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'findings': all_findings,
            'ambiguity_score': ambiguity_score,
            'risk_level': risk_level,
            'total_issues': len(all_findings)
        }
