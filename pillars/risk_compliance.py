"""
Risk & Compliance Evaluator (10% weight)
Evaluates: Red flag detection, violation tracking, supervisor alerts
"""

from typing import Dict, List, Tuple
import sys
sys.path.append('..')
from config import RISK_FLAGS


class RiskComplianceEvaluator:
    """
    Evaluates risk factors and compliance issues in calls.
    Detects legal threats, safety issues, abuse, and policy violations.
    Generates supervisor alerts for critical issues.
    """
    
    def __init__(self):
        self.risk_flags = RISK_FLAGS
        self.max_score = 100
    
    def evaluate(self, transcript: str) -> Dict:
        """
        Evaluate risk and compliance for a call transcript.
        
        Args:
            transcript: Full call transcript
            
        Returns:
            Dict with score, flags detected, and supervisor alerts
        """
        transcript_lower = transcript.lower()
        
        results = {
            "pillar": "Risk & Compliance",
            "weight": "10%",
            "score": 0,
            "max_score": self.max_score,
            "flags_detected": [],
            "supervisor_alerts": [],
            "severity_level": "none",
            "requires_review": False,
            "evidence": [],
            "recommendations": []
        }
        
        # Check each risk category
        all_flags = []
        critical_count = 0
        high_count = 0
        
        for category, config in self.risk_flags.items():
            detected = self._check_risk_category(transcript_lower, category, config)
            
            if detected["found"]:
                all_flags.append(detected)
                
                if config["severity"] == "critical":
                    critical_count += 1
                elif config["severity"] == "high":
                    high_count += 1
                
                if config["requires_supervisor"]:
                    results["supervisor_alerts"].append({
                        "category": category.replace("_", " ").title(),
                        "severity": config["severity"],
                        "keywords_matched": detected["matched_keywords"],
                        "action_required": "Immediate supervisor review"
                    })
        
        results["flags_detected"] = all_flags
        
        # Determine overall severity
        if critical_count > 0:
            results["severity_level"] = "critical"
            results["requires_review"] = True
        elif high_count > 0:
            results["severity_level"] = "high"
            results["requires_review"] = True
        elif len(all_flags) > 0:
            results["severity_level"] = "medium"
        else:
            results["severity_level"] = "none"
        
        # Calculate score (higher = better = fewer issues)
        # Start at 100, deduct for each flag
        score = 100
        score -= critical_count * 30
        score -= high_count * 15
        score -= (len(all_flags) - critical_count - high_count) * 5
        results["score"] = max(0, score)
        
        # Build evidence
        results["evidence"] = self._build_evidence(all_flags, results)
        
        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(all_flags)
        
        return results
    
    def _check_risk_category(self, transcript: str, category: str, config: Dict) -> Dict:
        """Check if a risk category is present in the transcript."""
        matched_keywords = []
        
        for keyword in config["keywords"]:
            if keyword in transcript:
                matched_keywords.append(keyword)
        
        return {
            "category": category,
            "found": len(matched_keywords) > 0,
            "matched_keywords": matched_keywords,
            "severity": config["severity"],
            "requires_supervisor": config["requires_supervisor"]
        }
    
    def _build_evidence(self, flags: List[Dict], results: Dict) -> List[Dict]:
        """Build evidence list for the evaluation."""
        evidence = []
        
        if not flags:
            evidence.append({
                "status": "✅",
                "message": "No risk flags or compliance issues detected"
            })
        else:
            for flag in flags:
                severity_emoji = {
                    "critical": "🚨",
                    "high": "⚠️",
                    "medium": "⚡"
                }
                evidence.append({
                    "status": severity_emoji.get(flag["severity"], "⚡"),
                    "category": flag["category"].replace("_", " ").title(),
                    "severity": flag["severity"],
                    "keywords": flag["matched_keywords"]
                })
        
        return evidence
    
    def _generate_recommendations(self, flags: List[Dict]) -> List[str]:
        """Generate recommendations based on detected flags."""
        recommendations = []
        
        for flag in flags:
            if flag["category"] == "legal_threats":
                recommendations.append(
                    "Legal threat detected. In future calls, acknowledge the customer's frustration, "
                    "do not argue, and offer to escalate to a supervisor proactively."
                )
            elif flag["category"] == "safety_issues":
                recommendations.append(
                    "Safety concern mentioned. Always take safety reports seriously, "
                    "document details, and escalate to the safety team immediately."
                )
            elif flag["category"] == "compliance_violation":
                recommendations.append(
                    "Potential compliance issue detected. Avoid making promises or offers "
                    "that aren't part of official policy."
                )
            elif flag["category"] == "churn_risk":
                recommendations.append(
                    "Customer indicated potential churn. Focus on understanding their core issue "
                    "and offer retention-focused solutions within your authority."
                )
        
        return recommendations
    
    def get_supervisor_alert(self, results: Dict) -> str:
        """Generate a supervisor alert message if needed."""
        if not results["requires_review"]:
            return None
        
        alert = []
        alert.append("=" * 50)
        alert.append("🚨 SUPERVISOR ALERT: CALL REQUIRES REVIEW")
        alert.append("=" * 50)
        alert.append(f"Severity Level: {results['severity_level'].upper()}")
        alert.append("")
        
        for alert_item in results["supervisor_alerts"]:
            alert.append(f"Issue: {alert_item['category']}")
            alert.append(f"Keywords: {', '.join(alert_item['keywords_matched'])}")
            alert.append(f"Action: {alert_item['action_required']}")
            alert.append("-" * 30)
        
        return "\n".join(alert)
    
    def get_detailed_feedback(self, results: Dict) -> str:
        """Generate human-readable feedback from evaluation results."""
        feedback = []
        feedback.append(f"🛡️ RISK & COMPLIANCE: {results['score']}/100")
        feedback.append("-" * 40)
        
        if results["flags_detected"]:
            feedback.append(f"Severity Level: {results['severity_level'].upper()}")
            feedback.append(f"Requires Supervisor Review: {'Yes' if results['requires_review'] else 'No'}")
            
            for flag in results["flags_detected"]:
                emoji = "🚨" if flag["severity"] == "critical" else "⚠️"
                feedback.append(f"{emoji} {flag['category'].replace('_', ' ').title()}: "
                              f"{', '.join(flag['matched_keywords'])}")
        else:
            feedback.append("✅ No risk flags or compliance issues detected")
        
        if results["recommendations"]:
            feedback.append("\n💡 Recommendations:")
            for rec in results["recommendations"]:
                feedback.append(f"  • {rec}")
        
        return "\n".join(feedback)
