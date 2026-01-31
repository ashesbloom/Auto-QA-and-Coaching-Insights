"""
Resolution Correctness Evaluator (30% weight)
Evaluates: SOP alignment, policy compliance, accurate solutions
"""

from typing import Dict, List, Optional
import sys
sys.path.append('..')
from config import BATTERY_SMART_SOPS


class ResolutionCorrectnessEvaluator:
    """
    Evaluates whether the agent provided the correct resolution
    according to Battery Smart's Standard Operating Procedures.
    """
    
    def __init__(self):
        self.sops = BATTERY_SMART_SOPS
        self.max_score = 100
    
    def evaluate(self, transcript: str, detected_issue: str = None) -> Dict:
        """
        Evaluate resolution correctness for a call transcript.
        
        Args:
            transcript: Full call transcript
            detected_issue: Optional pre-identified issue type
            
        Returns:
            Dict with score, breakdown, and evidence
        """
        transcript_lower = transcript.lower()
        
        results = {
            "pillar": "Resolution Correctness",
            "weight": "30%",
            "score": 0,
            "max_score": self.max_score,
            "detected_issues": [],
            "sop_compliance": [],
            "evidence": [],
            "recommendations": []
        }
        
        # Detect what issues are being discussed
        detected_issues = self._detect_issues(transcript_lower)
        results["detected_issues"] = detected_issues
        
        if not detected_issues:
            # No specific issue detected, give neutral score
            results["score"] = 70
            results["evidence"].append({
                "note": "No specific SOP-related issue detected in transcript",
                "assumption": "General inquiry handled"
            })
            return results
        
        total_score = 0
        issue_count = 0
        
        for issue_type in detected_issues:
            issue_count += 1
            sop = self.sops[issue_type]
            
            # Check if correct responses were provided
            compliance_result = self._check_sop_compliance(
                transcript_lower, 
                issue_type, 
                sop
            )
            results["sop_compliance"].append(compliance_result)
            total_score += compliance_result["score"]
            
            # Add evidence
            results["evidence"].append({
                "issue": issue_type,
                "sop_followed": compliance_result["steps_followed"],
                "correct_response_given": compliance_result["correct_response_found"],
                "score": compliance_result["score"]
            })
            
            # Add recommendations if needed
            if not compliance_result["correct_response_found"]:
                results["recommendations"].append(
                    f"For '{issue_type.replace('_', ' ')}' issues, ensure you mention: "
                    f"{', '.join(sop['correct_responses'][:2])}"
                )
        
        # Average score across all detected issues
        results["score"] = round(total_score / issue_count, 1) if issue_count > 0 else 70
        
        return results
    
    def _detect_issues(self, transcript: str) -> List[str]:
        """Detect which issue types are present in the transcript."""
        detected = []
        for issue_type, sop in self.sops.items():
            for keyword in sop["issue_keywords"]:
                if keyword in transcript:
                    if issue_type not in detected:
                        detected.append(issue_type)
                    break
        return detected
    
    def _check_sop_compliance(self, transcript: str, issue_type: str, sop: Dict) -> Dict:
        """Check if the agent followed the SOP for a specific issue."""
        steps_followed = []
        correct_response_found = False
        score = 0
        
        # Check for correct responses (worth 70% of this pillar's score)
        for response in sop["correct_responses"]:
            if response.lower() in transcript:
                correct_response_found = True
                score += 70
                break
        
        # Check for required steps mentioned (worth 30% of this pillar's score)
        step_score = 30 / len(sop["required_steps"])
        for step in sop["required_steps"]:
            # Simple keyword matching for step verification
            step_keywords = step.lower().split()
            if any(kw in transcript for kw in step_keywords if len(kw) > 3):
                steps_followed.append(step)
                score += step_score
        
        return {
            "issue_type": issue_type,
            "steps_followed": steps_followed,
            "steps_required": sop["required_steps"],
            "correct_response_found": correct_response_found,
            "score": min(score, 100)
        }
    
    def get_detailed_feedback(self, results: Dict) -> str:
        """Generate human-readable feedback from evaluation results."""
        feedback = []
        feedback.append(f"🎯 RESOLUTION CORRECTNESS: {results['score']}/100")
        feedback.append("-" * 40)
        
        if results["detected_issues"]:
            feedback.append(f"Issues Detected: {', '.join(results['detected_issues'])}")
            
            for compliance in results["sop_compliance"]:
                status = "✅" if compliance["correct_response_found"] else "❌"
                feedback.append(f"\n{status} {compliance['issue_type'].replace('_', ' ').title()}:")
                feedback.append(f"   Correct solution provided: {compliance['correct_response_found']}")
                feedback.append(f"   Steps followed: {len(compliance['steps_followed'])}/{len(compliance['steps_required'])}")
        else:
            feedback.append("No specific SOP issues detected")
        
        if results["recommendations"]:
            feedback.append("\n💡 Recommendations:")
            for rec in results["recommendations"]:
                feedback.append(f"  • {rec}")
        
        return "\n".join(feedback)
