"""
Call Evaluator - Main Orchestrator
Evaluates customer support calls using the Five-Pillar Scoring Framework.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Import pillar evaluators
from pillars.script_adherence import ScriptAdherenceEvaluator
from pillars.resolution_correctness import ResolutionCorrectnessEvaluator
from pillars.sentiment_handling import SentimentHandlingEvaluator
from pillars.communication_quality import CommunicationQualityEvaluator
from pillars.risk_compliance import RiskComplianceEvaluator

from config import PILLAR_WEIGHTS, SCORE_THRESHOLDS, SUPERVISOR_ALERT_THRESHOLD


@dataclass
class CallMetadata:
    """Metadata for a call being evaluated."""
    call_id: str
    agent_id: str
    agent_name: str
    city: str
    timestamp: str
    duration_seconds: int = 0


class CallEvaluator:
    """
    Main orchestrator for evaluating customer support calls.
    Runs all 5 pillar evaluations and produces a weighted aggregate score.
    """
    
    def __init__(self):
        # Initialize all pillar evaluators
        self.script_evaluator = ScriptAdherenceEvaluator()
        self.resolution_evaluator = ResolutionCorrectnessEvaluator()
        self.sentiment_evaluator = SentimentHandlingEvaluator()
        self.communication_evaluator = CommunicationQualityEvaluator()
        self.risk_evaluator = RiskComplianceEvaluator()
        
        self.weights = PILLAR_WEIGHTS
        
        # Initialize VoiceAgent for AI insights (Lazy load or try-except)
        try:
            # Import here to avoid circular dependency issues if any
            from voice_agent import VoiceAgent
            self.ai_agent = VoiceAgent()
        except Exception as e:
            print(f"Warning: Could not initialize VoiceAgent for AI insights: {e}")
            self.ai_agent = None
    
    def evaluate_call(self, transcript: str, metadata: CallMetadata = None) -> Dict:
        """
        Evaluate a complete call transcript.
        
        Args:
            transcript: Full call transcript text
            metadata: Optional call metadata (agent, city, timestamp)
            
        Returns:
            Complete evaluation results with scores, breakdowns, and alerts
        """
        evaluation_time = datetime.now().isoformat()
        
        # Run all pillar evaluations
        script_result = self.script_evaluator.evaluate(transcript)
        resolution_result = self.resolution_evaluator.evaluate(transcript)
        sentiment_result = self.sentiment_evaluator.evaluate(transcript)
        communication_result = self.communication_evaluator.evaluate(transcript)
        risk_result = self.risk_evaluator.evaluate(transcript)
        
        # Calculate weighted aggregate score
        weighted_score = self._calculate_weighted_score(
            script_result["score"],
            resolution_result["score"],
            sentiment_result["score"],
            communication_result["score"],
            risk_result["score"]
        )
        
        # Determine grade
        grade = self._determine_grade(weighted_score)
        
        # Check if supervisor review is needed
        needs_supervisor = (
            risk_result["requires_review"] or 
            weighted_score < SUPERVISOR_ALERT_THRESHOLD
        )
        
        # Compile all recommendations (rule-based initially)
        all_recommendations = self._compile_recommendations(
            script_result, resolution_result, sentiment_result,
            communication_result, risk_result
        )
        
        # Generate AI-powered insights (Specific coaching & alerts)
        # Construct temporary score context for prompt
        score_context = {
            'metadata': {
                'agent_name': metadata.agent_name if metadata else "Unknown Agent"
            }
        }
        
        ai_insights = self._generate_ai_insights(transcript, score_context)
        
        # Merge AI insights if available, otherwise use rule-based
        if ai_insights:
            # Prepend AI recommendations to rule-based ones
            all_recommendations = ai_insights.get("recommendations", []) + all_recommendations
            
            # Override strengths/improvements if AI provided valid ones
            coaching = {
                "top_recommendations": all_recommendations[:5],
                "strengths": ai_insights.get("strengths", self._identify_strengths(
                    script_result, resolution_result, sentiment_result,
                    communication_result, risk_result
                )),
                "areas_for_improvement": ai_insights.get("improvements", self._identify_improvements(
                    script_result, resolution_result, sentiment_result,
                    communication_result, risk_result
                ))
            }
            
            # Merge supervisor alerts (AI + Rule-based)
            ai_alerts = ai_insights.get("supervisor_alerts", [])
            existing_alerts = risk_result.get("supervisor_alerts", [])
            # Deduplicate based on category
            existing_categories = {a['category'] for a in existing_alerts}
            for alert in ai_alerts:
                if alert['category'] not in existing_categories:
                    existing_alerts.append(alert)
                    
            supervisor_alerts = existing_alerts
        else:
            # Fallback to rule-based
            coaching = {
                "top_recommendations": all_recommendations[:5],
                "strengths": self._identify_strengths(
                    script_result, resolution_result, sentiment_result,
                    communication_result, risk_result
                ),
                "areas_for_improvement": self._identify_improvements(
                    script_result, resolution_result, sentiment_result,
                    communication_result, risk_result
                )
            }
            supervisor_alerts = risk_result.get("supervisor_alerts", [])
        
        # Build final evaluation report
        evaluation = {
            "evaluation_id": f"EVAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "evaluated_at": evaluation_time,
            "metadata": {
                "call_id": metadata.call_id if metadata else "UNKNOWN",
                "agent_id": metadata.agent_id if metadata else "UNKNOWN",
                "agent_name": metadata.agent_name if metadata else "Unknown Agent",
                "city": metadata.city if metadata else "Unknown",
                "timestamp": metadata.timestamp if metadata else "Unknown"
            },
            "overall": {
                "score": weighted_score,
                "grade": grade,
                "needs_supervisor_review": needs_supervisor or bool(supervisor_alerts)
            },
            "pillar_scores": {
                "script_adherence": {
                    "score": script_result["score"],
                    "weight": "30%",
                    "weighted_contribution": round(script_result["score"] * 0.30, 1)
                },
                "resolution_correctness": {
                    "score": resolution_result["score"],
                    "weight": "30%",
                    "weighted_contribution": round(resolution_result["score"] * 0.30, 1)
                },
                "sentiment_handling": {
                    "score": sentiment_result["score"],
                    "weight": "20%",
                    "weighted_contribution": round(sentiment_result["score"] * 0.20, 1)
                },
                "communication_quality": {
                    "score": communication_result["score"],
                    "weight": "10%",
                    "weighted_contribution": round(communication_result["score"] * 0.10, 1)
                },
                "risk_compliance": {
                    "score": risk_result["score"],
                    "weight": "10%",
                    "weighted_contribution": round(risk_result["score"] * 0.10, 1)
                }
            },
            "detailed_breakdown": {
                "script_adherence": script_result,
                "resolution_correctness": resolution_result,
                "sentiment_handling": sentiment_result,
                "communication_quality": communication_result,
                "risk_compliance": risk_result
            },
            "coaching_insights": coaching,
            "supervisor_alerts": supervisor_alerts
        }
        
        return evaluation

    def _generate_ai_insights(self, transcript: str, score_data: Dict) -> Optional[Dict]:
        """
        Generate specific coaching insights using LLM.
        Returns: {
            "strengths": [],
            "improvements": [],
            "recommendations": [],
            "supervisor_alerts": []
        }
        """
        try:
            # Use pre-initialized agent
            agent = self.ai_agent
            
            if not agent:
                return None
                
            if not (agent.client or (agent.model_type == 'gemini' and agent.model)):
                return None
                
            # Construct Prompt
            prompt = f"""
            You are a QA Supervisor for a battery swapping company. Evaluate this call transcript.
            
            TRANSCRIPT:
            {transcript[:4000]}  # Truncate if too long
            
            CONTEXT:
            - Agent: {score_data.get('metadata', {}).get('agent_name', 'Agent')}
            
            TASK:
            Provide a valid JSON response with specific observations. Do NOT include generic advice.
            Format:
            {{
                "strengths": ["Specific thing agent did well"],
                "improvements": ["Specific thing agent missed"],
                "recommendations": ["Actionable coaching tip"],
                "supervisor_alerts": [
                    {{"category": "Legal Threat", "severity": "high", "keywords_matched": ["sue"]}} 
                    // Only if LEGAL THREAT, HARASSMENT, or SCAM detected. Otherwise empty list.
                ]
            }}
            """
            
            response_text = ""
            
            # Call LLM
            if agent.client: # Groq
                # Use standard supported model
                model_name = "llama-3.3-70b-versatile"
                
                completion = agent.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a QA Supervisor. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                response_text = completion.choices[0].message.content
                
            elif agent.model_type == 'gemini': # Gemini
                 response = agent.model.generate_content(prompt)
                 response_text = response.text
            
            # Parse JSON
            import json
            # handle markdown code blocks if any
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
                
            return json.loads(response_text)
            
        except Exception as e:
            print(f"Error generating AI insights: {e}")
            return None
    
    def _calculate_weighted_score(self, script: float, resolution: float, 
                                   sentiment: float, communication: float, 
                                   risk: float) -> float:
        """Calculate the weighted aggregate score."""
        weighted = (
            script * self.weights["script_adherence"] +
            resolution * self.weights["resolution_correctness"] +
            sentiment * self.weights["sentiment_handling"] +
            communication * self.weights["communication_quality"] +
            risk * self.weights["risk_compliance"]
        )
        return round(weighted, 1)
    
    def _determine_grade(self, score: float) -> str:
        """Determine the grade based on score."""
        if score >= SCORE_THRESHOLDS["excellent"]:
            return "A - Excellent"
        elif score >= SCORE_THRESHOLDS["good"]:
            return "B - Good"
        elif score >= SCORE_THRESHOLDS["needs_improvement"]:
            return "C - Needs Improvement"
        elif score >= SCORE_THRESHOLDS["poor"]:
            return "D - Poor"
        else:
            return "F - Critical"
    
    def _compile_recommendations(self, *results) -> List[str]:
        """Compile all recommendations from pillar evaluations."""
        recommendations = []
        for result in results:
            if "recommendations" in result:
                recommendations.extend(result["recommendations"])
        return recommendations
    
    def _identify_strengths(self, *results) -> List[str]:
        """Identify areas where the agent performed well."""
        strengths = []
        
        for result in results:
            if result["score"] >= 80:
                pillar_name = result.get("pillar", "Unknown")
                strengths.append(f"{pillar_name}: Scored {result['score']}/100")
        
        return strengths if strengths else ["Keep working on all areas for improvement"]
    
    def _identify_improvements(self, *results) -> List[str]:
        """Identify areas that need improvement."""
        improvements = []
        
        for result in results:
            if result["score"] < 70:
                pillar_name = result.get("pillar", "Unknown")
                improvements.append(f"{pillar_name}: Scored {result['score']}/100 - needs attention")
        
        return improvements if improvements else ["Great job! Continue maintaining quality."]
    
    def generate_report(self, evaluation: Dict) -> str:
        """Generate a human-readable report from evaluation results."""
        report = []
        
        # Header
        report.append("=" * 60)
        report.append("           AUTO-QA CALL EVALUATION REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Metadata
        meta = evaluation["metadata"]
        report.append(f"📞 Call ID: {meta['call_id']}")
        report.append(f"👤 Agent: {meta['agent_name']} ({meta['agent_id']})")
        report.append(f"📍 City: {meta['city']}")
        report.append(f"🕐 Timestamp: {meta['timestamp']}")
        report.append("")
        
        # Overall Score
        overall = evaluation["overall"]
        report.append("-" * 60)
        score_emoji = "🌟" if overall["score"] >= 80 else ("✅" if overall["score"] >= 60 else "⚠️")
        report.append(f"{score_emoji} OVERALL SCORE: {overall['score']}/100 ({overall['grade']})")
        report.append("-" * 60)
        report.append("")
        
        # Pillar Breakdown
        report.append("📊 PILLAR SCORES:")
        report.append("")
        
        pillars = evaluation["pillar_scores"]
        for pillar_name, pillar_data in pillars.items():
            bar = self._generate_bar(pillar_data["score"])
            report.append(f"  {pillar_name.replace('_', ' ').title():25} {bar} {pillar_data['score']:5.1f}/100 (×{pillar_data['weight']})")
        
        report.append("")
        
        # Coaching Insights
        report.append("-" * 60)
        report.append("💡 COACHING INSIGHTS")
        report.append("-" * 60)
        
        if evaluation["coaching_insights"]["strengths"]:
            report.append("\n✅ Strengths:")
            for strength in evaluation["coaching_insights"]["strengths"]:
                report.append(f"   • {strength}")
        
        if evaluation["coaching_insights"]["areas_for_improvement"]:
            report.append("\n🔧 Areas for Improvement:")
            for area in evaluation["coaching_insights"]["areas_for_improvement"]:
                report.append(f"   • {area}")
        
        if evaluation["coaching_insights"]["top_recommendations"]:
            report.append("\n📝 Top Recommendations:")
            for i, rec in enumerate(evaluation["coaching_insights"]["top_recommendations"][:3], 1):
                report.append(f"   {i}. {rec[:100]}...")
        
        report.append("")
        
        # Supervisor Alerts
        if evaluation["supervisor_alerts"]:
            report.append("=" * 60)
            report.append("🚨 SUPERVISOR ALERTS")
            report.append("=" * 60)
            for alert in evaluation["supervisor_alerts"]:
                report.append(f"  ⚠️ {alert['category']}: {alert['severity'].upper()}")
                report.append(f"     Keywords: {', '.join(alert['keywords_matched'])}")
            report.append("")
        
        report.append("=" * 60)
        report.append(f"Report generated at: {evaluation['evaluated_at']}")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def _generate_bar(self, score: float, width: int = 20) -> str:
        """Generate a visual bar for the score."""
        filled = int((score / 100) * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"
