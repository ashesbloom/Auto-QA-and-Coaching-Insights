"""
Script Adherence Evaluator (30% weight)
Evaluates: Greeting execution, identity verification, proper closure
"""

import re
from typing import Dict, List, Tuple
import sys
sys.path.append('..')
from config import REQUIRED_SCRIPT_ELEMENTS


class ScriptAdherenceEvaluator:
    """
    Evaluates whether the agent followed the required call script.
    Checks for mandatory elements like greeting, verification, and closing.
    """
    
    def __init__(self):
        self.script_elements = REQUIRED_SCRIPT_ELEMENTS
        self.max_score = 100
    
    def evaluate(self, transcript: str, agent_segments: List[str] = None) -> Dict:
        """
        Evaluate script adherence for a call transcript.
        
        Args:
            transcript: Full call transcript
            agent_segments: Optional list of agent-only statements
            
        Returns:
            Dict with score, breakdown, and evidence
        """
        transcript_lower = transcript.lower()
        
        results = {
            "pillar": "Script Adherence",
            "weight": "30%",
            "score": 0,
            "max_score": self.max_score,
            "breakdown": [],
            "evidence": [],
            "recommendations": []
        }
        
        total_points = 0
        max_points = sum(elem["points"] for elem in self.script_elements.values())
        
        for element_name, config in self.script_elements.items():
            element_result = self._check_element(
                transcript_lower, 
                element_name, 
                config
            )
            
            results["breakdown"].append(element_result)
            
            if element_result["found"]:
                total_points += config["points"]
                results["evidence"].append({
                    "element": element_name,
                    "status": "✅ Present",
                    "matched_phrase": element_result["matched_phrase"],
                    "points_earned": config["points"]
                })
            else:
                results["evidence"].append({
                    "element": element_name,
                    "status": "❌ Missing",
                    "matched_phrase": None,
                    "points_lost": config["points"]
                })
                results["recommendations"].append(
                    f"Include {config['description'].lower()} in your calls"
                )
        
        # Calculate normalized score (0-100)
        results["score"] = round((total_points / max_points) * 100, 1)
        results["points_earned"] = total_points
        results["points_possible"] = max_points
        
        return results
    
    def _check_element(self, transcript: str, element_name: str, config: Dict) -> Dict:
        """Check if a script element is present in the transcript."""
        for keyword in config["keywords"]:
            if keyword.lower() in transcript:
                return {
                    "element": element_name,
                    "description": config["description"],
                    "found": True,
                    "matched_phrase": keyword,
                    "points": config["points"]
                }
        
        return {
            "element": element_name,
            "description": config["description"],
            "found": False,
            "matched_phrase": None,
            "points": 0
        }
    
    def get_detailed_feedback(self, results: Dict) -> str:
        """Generate human-readable feedback from evaluation results."""
        feedback = []
        feedback.append(f"📋 SCRIPT ADHERENCE: {results['score']}/100")
        feedback.append("-" * 40)
        
        for item in results["breakdown"]:
            status = "✅" if item["found"] else "❌"
            feedback.append(f"{status} {item['description']}: {item['points']} pts")
        
        if results["recommendations"]:
            feedback.append("\n💡 Recommendations:")
            for rec in results["recommendations"]:
                feedback.append(f"  • {rec}")
        
        return "\n".join(feedback)
