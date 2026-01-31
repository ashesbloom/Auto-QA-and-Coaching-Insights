"""
Communication Quality Evaluator (10% weight)
Evaluates: Clarity, tone, professionalism
"""

from typing import Dict, List
import sys
sys.path.append('..')
from config import COMMUNICATION_QUALITY


class CommunicationQualityEvaluator:
    """
    Evaluates the quality of communication from the agent.
    Checks for clarity, professional tone, and avoidance of negative patterns.
    """
    
    def __init__(self):
        self.quality_indicators = COMMUNICATION_QUALITY
        self.max_score = 100
    
    def evaluate(self, transcript: str) -> Dict:
        """
        Evaluate communication quality for a call transcript.
        
        Args:
            transcript: Full call transcript
            
        Returns:
            Dict with score, breakdown, and evidence
        """
        transcript_lower = transcript.lower()
        
        results = {
            "pillar": "Communication Quality",
            "weight": "10%",
            "score": 0,
            "max_score": self.max_score,
            "positive_indicators": [],
            "negative_indicators": [],
            "jargon_detected": [],
            "evidence": [],
            "recommendations": []
        }
        
        # Check positive indicators (adds points)
        positive_score = self._check_positive_indicators(transcript_lower, results)
        
        # Check negative indicators (deducts points)
        negative_score = self._check_negative_indicators(transcript_lower, results)
        
        # Check for jargon usage (deducts points)
        jargon_score = self._check_jargon(transcript_lower, results)
        
        # Check for interruption patterns
        interruption_score = self._check_interruptions(transcript_lower, results)
        
        # Calculate final score
        # Start with base score of 70, then adjust
        base_score = 70
        score = base_score + positive_score - negative_score - jargon_score - interruption_score
        results["score"] = max(0, min(100, round(score, 1)))
        
        # Build evidence summary
        results["evidence"] = self._build_evidence(results)
        
        return results
    
    def _check_positive_indicators(self, transcript: str, results: Dict) -> float:
        """Check for positive communication indicators."""
        found = []
        for indicator in self.quality_indicators["positive_indicators"]:
            if indicator in transcript:
                found.append(indicator)
        
        results["positive_indicators"] = found
        # Each positive indicator adds 5 points, max 20
        return min(len(found) * 5, 20)
    
    def _check_negative_indicators(self, transcript: str, results: Dict) -> float:
        """Check for negative communication patterns."""
        found = []
        for indicator in self.quality_indicators["negative_indicators"]:
            if indicator in transcript:
                found.append(indicator)
        
        results["negative_indicators"] = found
        
        if found:
            results["recommendations"].append(
                f"Avoid phrases like: {', '.join(found[:2])}. These can sound dismissive or unprofessional."
            )
        
        # Each negative indicator deducts 10 points
        return len(found) * 10
    
    def _check_jargon(self, transcript: str, results: Dict) -> float:
        """Check for technical jargon that should be avoided."""
        found = []
        for jargon in self.quality_indicators["jargon_to_avoid"]:
            if jargon in transcript:
                found.append(jargon)
        
        results["jargon_detected"] = found
        
        if found:
            results["recommendations"].append(
                "Avoid technical jargon when speaking to customers. "
                f"Consider simpler alternatives for: {', '.join(found)}"
            )
        
        # Each jargon term deducts 5 points
        return len(found) * 5
    
    def _check_interruptions(self, transcript: str, results: Dict) -> float:
        """Check for signs of interruption."""
        interruption_count = 0
        for pattern in self.quality_indicators["interruption_patterns"]:
            if pattern in transcript:
                interruption_count += 1
        
        if interruption_count > 0:
            results["recommendations"].append(
                "Allow customers to finish speaking before responding. "
                "Signs of interruption were detected in this call."
            )
        
        # Each interruption pattern deducts 8 points
        return interruption_count * 8
    
    def _build_evidence(self, results: Dict) -> List[Dict]:
        """Build evidence list for the evaluation."""
        evidence = []
        
        if results["positive_indicators"]:
            evidence.append({
                "category": "Positive Communication",
                "status": "✅",
                "examples": results["positive_indicators"][:3]
            })
        
        if results["negative_indicators"]:
            evidence.append({
                "category": "Negative Patterns",
                "status": "❌",
                "examples": results["negative_indicators"]
            })
        
        if results["jargon_detected"]:
            evidence.append({
                "category": "Technical Jargon",
                "status": "⚠️",
                "examples": results["jargon_detected"]
            })
        
        return evidence
    
    def get_detailed_feedback(self, results: Dict) -> str:
        """Generate human-readable feedback from evaluation results."""
        feedback = []
        feedback.append(f"💬 COMMUNICATION QUALITY: {results['score']}/100")
        feedback.append("-" * 40)
        
        if results["positive_indicators"]:
            feedback.append(f"✅ Positive signals: {', '.join(results['positive_indicators'][:3])}")
        
        if results["negative_indicators"]:
            feedback.append(f"❌ Negative patterns: {', '.join(results['negative_indicators'])}")
        
        if results["jargon_detected"]:
            feedback.append(f"⚠️ Jargon detected: {', '.join(results['jargon_detected'])}")
        
        if results["recommendations"]:
            feedback.append("\n💡 Recommendations:")
            for rec in results["recommendations"]:
                feedback.append(f"  • {rec}")
        
        return "\n".join(feedback)
