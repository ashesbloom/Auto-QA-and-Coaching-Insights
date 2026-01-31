"""
Sentiment Handling Evaluator (20% weight)
Evaluates: De-escalation effectiveness, empathy signals, sentiment trajectory
"""

from typing import Dict, List, Tuple
import sys
sys.path.append('..')
from config import SENTIMENT_KEYWORDS


class SentimentHandlingEvaluator:
    """
    Evaluates how well the agent handled customer sentiment.
    Tracks sentiment trajectory (start vs end) and empathy signals.
    """
    
    def __init__(self):
        self.keywords = SENTIMENT_KEYWORDS
        self.max_score = 100
    
    def evaluate(self, transcript: str) -> Dict:
        """
        Evaluate sentiment handling for a call transcript.
        
        Args:
            transcript: Full call transcript
            
        Returns:
            Dict with score, trajectory analysis, and evidence
        """
        results = {
            "pillar": "Sentiment Handling",
            "weight": "20%",
            "score": 0,
            "max_score": self.max_score,
            "sentiment_trajectory": {},
            "empathy_analysis": {},
            "escalation_risk": {},
            "evidence": [],
            "recommendations": []
        }
        
        # Split transcript into segments for trajectory analysis
        segments = self._split_into_segments(transcript)
        
        # Analyze sentiment at start, middle, and end
        trajectory = self._analyze_trajectory(segments)
        results["sentiment_trajectory"] = trajectory
        
        # Check for empathy signals from agent
        empathy = self._analyze_empathy(transcript)
        results["empathy_analysis"] = empathy
        
        # Check for escalation signals
        escalation = self._analyze_escalation(transcript)
        results["escalation_risk"] = escalation
        
        # Calculate score based on trajectory, empathy, and escalation handling
        score = self._calculate_sentiment_score(trajectory, empathy, escalation)
        results["score"] = score
        
        # Build evidence
        results["evidence"] = self._build_evidence(trajectory, empathy, escalation)
        
        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(trajectory, empathy, escalation)
        
        return results
    
    def _split_into_segments(self, transcript: str) -> Dict[str, str]:
        """Split transcript into start, middle, and end segments."""
        lines = transcript.split('\n')
        total_lines = len(lines)
        
        if total_lines < 3:
            return {
                "start": transcript,
                "middle": transcript,
                "end": transcript
            }
        
        third = total_lines // 3
        return {
            "start": '\n'.join(lines[:third]),
            "middle": '\n'.join(lines[third:2*third]),
            "end": '\n'.join(lines[2*third:])
        }
    
    def _analyze_trajectory(self, segments: Dict[str, str]) -> Dict:
        """Analyze sentiment trajectory across call segments."""
        trajectory = {}
        
        for segment_name, text in segments.items():
            text_lower = text.lower()
            
            positive_count = sum(1 for kw in self.keywords["positive"] if kw in text_lower)
            negative_count = sum(1 for kw in self.keywords["negative"] if kw in text_lower)
            
            if positive_count > negative_count:
                sentiment = "positive"
            elif negative_count > positive_count:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            trajectory[segment_name] = {
                "sentiment": sentiment,
                "positive_signals": positive_count,
                "negative_signals": negative_count
            }
        
        # Determine trajectory direction
        start_sentiment = trajectory["start"]["sentiment"]
        end_sentiment = trajectory["end"]["sentiment"]
        
        sentiment_values = {"negative": -1, "neutral": 0, "positive": 1}
        start_val = sentiment_values[start_sentiment]
        end_val = sentiment_values[end_sentiment]
        
        if end_val > start_val:
            trajectory["direction"] = "improving"  # Good!
            trajectory["trajectory_score"] = 100
        elif end_val < start_val:
            trajectory["direction"] = "declining"  # Bad!
            trajectory["trajectory_score"] = 30
        else:
            trajectory["direction"] = "stable"
            trajectory["trajectory_score"] = 70
        
        return trajectory
    
    def _analyze_empathy(self, transcript: str) -> Dict:
        """Analyze empathy signals in the transcript."""
        transcript_lower = transcript.lower()
        
        empathy_found = []
        for phrase in self.keywords["empathy_phrases"]:
            if phrase in transcript_lower:
                empathy_found.append(phrase)
        
        empathy_count = len(empathy_found)
        
        if empathy_count >= 3:
            empathy_level = "high"
            empathy_score = 100
        elif empathy_count >= 1:
            empathy_level = "moderate"
            empathy_score = 70
        else:
            empathy_level = "low"
            empathy_score = 30
        
        return {
            "level": empathy_level,
            "phrases_found": empathy_found,
            "count": empathy_count,
            "score": empathy_score
        }
    
    def _analyze_escalation(self, transcript: str) -> Dict:
        """Analyze escalation signals and how they were handled."""
        transcript_lower = transcript.lower()
        
        escalation_signals = []
        for signal in self.keywords["escalation_signals"]:
            if signal in transcript_lower:
                escalation_signals.append(signal)
        
        has_escalation = len(escalation_signals) > 0
        
        # If there was escalation, check if it was de-escalated
        # (presence of empathy + positive ending = successful de-escalation)
        de_escalation_indicators = sum(
            1 for kw in self.keywords["empathy_phrases"] 
            if kw in transcript_lower
        )
        
        if has_escalation:
            if de_escalation_indicators >= 2:
                handling = "well_handled"
                handling_score = 90
            elif de_escalation_indicators >= 1:
                handling = "partially_handled"
                handling_score = 60
            else:
                handling = "poorly_handled"
                handling_score = 30
        else:
            handling = "no_escalation"
            handling_score = 80
        
        return {
            "has_escalation": has_escalation,
            "signals_detected": escalation_signals,
            "handling": handling,
            "score": handling_score
        }
    
    def _calculate_sentiment_score(self, trajectory: Dict, empathy: Dict, escalation: Dict) -> float:
        """Calculate overall sentiment handling score."""
        # Weight: 40% trajectory, 35% empathy, 25% escalation handling
        score = (
            trajectory["trajectory_score"] * 0.40 +
            empathy["score"] * 0.35 +
            escalation["score"] * 0.25
        )
        return round(score, 1)
    
    def _build_evidence(self, trajectory: Dict, empathy: Dict, escalation: Dict) -> List[Dict]:
        """Build evidence list for the evaluation."""
        evidence = []
        
        evidence.append({
            "category": "Sentiment Trajectory",
            "start": trajectory["start"]["sentiment"],
            "end": trajectory["end"]["sentiment"],
            "direction": trajectory["direction"],
            "assessment": "✅ Good" if trajectory["direction"] == "improving" else 
                         ("⚠️ Attention needed" if trajectory["direction"] == "declining" else "➖ Neutral")
        })
        
        evidence.append({
            "category": "Empathy Signals",
            "level": empathy["level"],
            "examples": empathy["phrases_found"][:3] if empathy["phrases_found"] else ["None detected"]
        })
        
        if escalation["has_escalation"]:
            evidence.append({
                "category": "Escalation Handling",
                "escalation_detected": True,
                "signals": escalation["signals_detected"],
                "handling_quality": escalation["handling"]
            })
        
        return evidence
    
    def _generate_recommendations(self, trajectory: Dict, empathy: Dict, escalation: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if trajectory["direction"] == "declining":
            recommendations.append(
                "Customer sentiment declined during the call. Focus on addressing concerns earlier "
                "and checking in with the customer before ending the call."
            )
        
        if empathy["level"] == "low":
            recommendations.append(
                "Increase use of empathy phrases like 'I understand' and 'I apologize for the inconvenience' "
                "to show customers you care about their experience."
            )
        
        if escalation["handling"] == "poorly_handled":
            recommendations.append(
                "When customers show escalation signals (asking for manager, expressing strong dissatisfaction), "
                "acknowledge their frustration before attempting to resolve the issue."
            )
        
        return recommendations
    
    def get_detailed_feedback(self, results: Dict) -> str:
        """Generate human-readable feedback from evaluation results."""
        feedback = []
        feedback.append(f"💭 SENTIMENT HANDLING: {results['score']}/100")
        feedback.append("-" * 40)
        
        traj = results["sentiment_trajectory"]
        direction_emoji = {"improving": "📈", "declining": "📉", "stable": "➡️"}
        feedback.append(f"Trajectory: {traj['start']['sentiment']} → {traj['end']['sentiment']} "
                       f"{direction_emoji.get(traj['direction'], '')}")
        
        emp = results["empathy_analysis"]
        feedback.append(f"Empathy Level: {emp['level'].title()} ({emp['count']} signals)")
        
        esc = results["escalation_risk"]
        if esc["has_escalation"]:
            feedback.append(f"Escalation: Detected, {esc['handling'].replace('_', ' ').title()}")
        
        if results["recommendations"]:
            feedback.append("\n💡 Recommendations:")
            for rec in results["recommendations"]:
                feedback.append(f"  • {rec}")
        
        return "\n".join(feedback)
