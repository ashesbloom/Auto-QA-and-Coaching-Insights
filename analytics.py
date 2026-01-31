"""
Analytics Module for Auto-QA System
Provides aggregated insights, trends, and coaching recommendations.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from config import (
    COMPLAINT_CATEGORIES, 
    ANALYTICS_CONFIG, 
    SCORE_THRESHOLDS,
    PILLAR_WEIGHTS
)


class AnalyticsEngine:
    """
    Aggregates evaluation results to produce actionable insights.
    Tracks trends, identifies patterns, and generates coaching recommendations.
    """
    
    def __init__(self):
        self.evaluations = []
        self.agent_data = defaultdict(list)
        self.city_data = defaultdict(list)
        self.complaint_data = defaultdict(list)
    
    def add_evaluation(self, evaluation: Dict):
        """Add an evaluation result to the analytics pool."""
        self.evaluations.append(evaluation)
        
        # Index by agent
        agent_id = evaluation.get("metadata", {}).get("agent_id", "UNKNOWN")
        self.agent_data[agent_id].append(evaluation)
        
        # Index by city
        city = evaluation.get("metadata", {}).get("city", "Unknown")
        self.city_data[city].append(evaluation)
        
        # Index by complaint type
        issues = evaluation.get("detailed_breakdown", {}).get(
            "resolution_correctness", {}
        ).get("detected_issues", [])
        for issue in issues:
            self.complaint_data[issue].append(evaluation)
    
    def generate_analytics_report(self) -> Dict:
        """Generate comprehensive analytics report."""
        if not self.evaluations:
            return {"error": "No evaluations available for analysis"}
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_calls_analyzed": len(self.evaluations),
            "overview": self._generate_overview(),
            "pillar_analysis": self._analyze_pillars(),
            "complaint_distribution": self._analyze_complaints(),
            "agent_performance": self._analyze_agents(),
            "city_performance": self._analyze_cities(),
            "risk_summary": self._analyze_risks(),
            "coaching_priorities": self._generate_coaching_priorities(),
            "trends": self._analyze_trends()
        }
        
        return report
    
    def _generate_overview(self) -> Dict:
        """Generate high-level overview metrics."""
        scores = [e["overall"]["score"] for e in self.evaluations]
        
        needs_review = sum(
            1 for e in self.evaluations 
            if e["overall"]["needs_supervisor_review"]
        )
        
        grades = defaultdict(int)
        for e in self.evaluations:
            grades[e["overall"]["grade"]] += 1
        
        return {
            "average_score": round(sum(scores) / len(scores), 1),
            "min_score": min(scores),
            "max_score": max(scores),
            "calls_needing_review": needs_review,
            "review_percentage": round(needs_review / len(scores) * 100, 1),
            "grade_distribution": dict(grades),
            "score_distribution": {
                "excellent (90+)": sum(1 for s in scores if s >= 90),
                "good (75-89)": sum(1 for s in scores if 75 <= s < 90),
                "needs_improvement (60-74)": sum(1 for s in scores if 60 <= s < 75),
                "poor (40-59)": sum(1 for s in scores if 40 <= s < 60),
                "critical (<40)": sum(1 for s in scores if s < 40)
            }
        }
    
    def _analyze_pillars(self) -> Dict:
        """Analyze performance across each pillar."""
        pillar_scores = defaultdict(list)
        
        for e in self.evaluations:
            for pillar, data in e.get("pillar_scores", {}).items():
                pillar_scores[pillar].append(data["score"])
        
        analysis = {}
        for pillar, scores in pillar_scores.items():
            avg = sum(scores) / len(scores)
            analysis[pillar] = {
                "average_score": round(avg, 1),
                "min": min(scores),
                "max": max(scores),
                "below_threshold": sum(1 for s in scores if s < 70),
                "weight": PILLAR_WEIGHTS.get(pillar, 0),
                "impact": round(avg * PILLAR_WEIGHTS.get(pillar, 0), 1)
            }
        
        # Sort by impact (lowest first = needs most attention)
        sorted_pillars = sorted(
            analysis.items(), 
            key=lambda x: x[1]["impact"]
        )
        
        return {
            "pillar_details": analysis,
            "weakest_pillar": sorted_pillars[0][0] if sorted_pillars else None,
            "strongest_pillar": sorted_pillars[-1][0] if sorted_pillars else None
        }
    
    def _analyze_complaints(self) -> Dict:
        """Analyze complaint type distribution and handling."""
        complaint_counts = defaultdict(int)
        complaint_scores = defaultdict(list)
        
        for e in self.evaluations:
            issues = e.get("detailed_breakdown", {}).get(
                "resolution_correctness", {}
            ).get("detected_issues", [])
            
            for issue in issues:
                complaint_counts[issue] += 1
                complaint_scores[issue].append(e["overall"]["score"])
        
        analysis = {}
        for complaint, count in complaint_counts.items():
            scores = complaint_scores[complaint]
            analysis[complaint] = {
                "count": count,
                "percentage": round(count / len(self.evaluations) * 100, 1),
                "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
                "category_name": self._get_complaint_category_name(complaint)
            }
        
        # Sort by count
        sorted_complaints = sorted(
            analysis.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return {
            "by_type": analysis,
            "most_common": sorted_complaints[:5] if sorted_complaints else [],
            "lowest_handling_score": min(
                analysis.items(), 
                key=lambda x: x[1]["avg_score"]
            ) if analysis else None
        }
    
    def _get_complaint_category_name(self, issue_key: str) -> str:
        """Get human-readable category name."""
        for cat_key, cat_data in COMPLAINT_CATEGORIES.items():
            if issue_key in cat_key or cat_key in issue_key:
                return cat_data["name"]
        return issue_key.replace("_", " ").title()
    
    def _analyze_agents(self) -> Dict:
        """Analyze performance by agent."""
        agent_analysis = {}
        
        for agent_id, evals in self.agent_data.items():
            scores = [e["overall"]["score"] for e in evals]
            agent_name = evals[0].get("metadata", {}).get("agent_name", "Unknown")
            
            # Calculate pillar averages for this agent
            pillar_avgs = defaultdict(list)
            for e in evals:
                for pillar, data in e.get("pillar_scores", {}).items():
                    pillar_avgs[pillar].append(data["score"])
            
            weakest_pillar = min(
                pillar_avgs.items(),
                key=lambda x: sum(x[1]) / len(x[1])
            ) if pillar_avgs else (None, [])
            
            agent_analysis[agent_id] = {
                "agent_name": agent_name,
                "total_calls": len(evals),
                "average_score": round(sum(scores) / len(scores), 1),
                "min_score": min(scores),
                "max_score": max(scores),
                "calls_needing_review": sum(
                    1 for e in evals if e["overall"]["needs_supervisor_review"]
                ),
                "weakest_pillar": weakest_pillar[0],
                "weakest_pillar_avg": round(
                    sum(weakest_pillar[1]) / len(weakest_pillar[1]), 1
                ) if weakest_pillar[1] else 0
            }
        
        # Generate leaderboard
        leaderboard = sorted(
            agent_analysis.items(),
            key=lambda x: x[1]["average_score"],
            reverse=True
        )
        
        return {
            "by_agent": agent_analysis,
            "leaderboard": [
                {"rank": i+1, "agent_id": a[0], **a[1]} 
                for i, a in enumerate(leaderboard)
            ],
            "top_performer": leaderboard[0] if leaderboard else None,
            "needs_coaching": [
                a for a in leaderboard if a[1]["average_score"] < 70
            ]
        }
    
    def _analyze_cities(self) -> Dict:
        """Analyze performance by city/hub."""
        city_analysis = {}
        
        for city, evals in self.city_data.items():
            scores = [e["overall"]["score"] for e in evals]
            
            # Common issues in this city
            issue_counts = defaultdict(int)
            for e in evals:
                issues = e.get("detailed_breakdown", {}).get(
                    "resolution_correctness", {}
                ).get("detected_issues", [])
                for issue in issues:
                    issue_counts[issue] += 1
            
            city_analysis[city] = {
                "total_calls": len(evals),
                "average_score": round(sum(scores) / len(scores), 1),
                "min_score": min(scores),
                "max_score": max(scores),
                "common_issues": dict(
                    sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                ),
                "agents_count": len(set(
                    e.get("metadata", {}).get("agent_id") for e in evals
                ))
            }
        
        # Rank cities
        city_ranking = sorted(
            city_analysis.items(),
            key=lambda x: x[1]["average_score"],
            reverse=True
        )
        
        return {
            "by_city": city_analysis,
            "ranking": [
                {"rank": i+1, "city": c[0], **c[1]} 
                for i, c in enumerate(city_ranking)
            ],
            "best_city": city_ranking[0] if city_ranking else None,
            "underperforming_cities": [
                c for c in city_ranking if c[1]["average_score"] < 70
            ]
        }
    
    def _analyze_risks(self) -> Dict:
        """Analyze risk flags and supervisor alerts."""
        risk_counts = defaultdict(int)
        critical_calls = []
        
        for e in self.evaluations:
            alerts = e.get("supervisor_alerts", [])
            for alert in alerts:
                risk_counts[alert["category"]] += 1
            
            if e["overall"]["needs_supervisor_review"]:
                critical_calls.append({
                    "call_id": e.get("metadata", {}).get("call_id"),
                    "agent": e.get("metadata", {}).get("agent_name"),
                    "score": e["overall"]["score"],
                    "alerts": [a["category"] for a in alerts]
                })
        
        return {
            "risk_distribution": dict(risk_counts),
            "total_flagged_calls": len(critical_calls),
            "flagged_percentage": round(
                len(critical_calls) / len(self.evaluations) * 100, 1
            ),
            "critical_calls": critical_calls
        }
    
    def _generate_coaching_priorities(self) -> List[Dict]:
        """Generate prioritized coaching recommendations."""
        priorities = []
        
        # Analyze common weaknesses
        pillar_analysis = self._analyze_pillars()
        weakest = pillar_analysis.get("weakest_pillar")
        
        if weakest:
            priorities.append({
                "priority": 1,
                "area": weakest.replace("_", " ").title(),
                "type": "Team-wide Training",
                "reason": f"Lowest performing pillar across all agents",
                "recommended_action": f"Schedule team training session on {weakest.replace('_', ' ')}"
            })
        
        # Agent-specific coaching
        agent_analysis = self._analyze_agents()
        for agent in agent_analysis.get("needs_coaching", [])[:3]:
            priorities.append({
                "priority": 2,
                "area": agent[1]["weakest_pillar"],
                "type": "Individual Coaching",
                "agent": agent[1]["agent_name"],
                "reason": f"Average score {agent[1]['average_score']} below threshold",
                "recommended_action": f"1-on-1 coaching session focusing on {agent[1]['weakest_pillar']}"
            })
        
        # City-level issues
        city_analysis = self._analyze_cities()
        for city in city_analysis.get("underperforming_cities", [])[:2]:
            priorities.append({
                "priority": 3,
                "area": "City Hub Performance",
                "type": "Hub-level Intervention",
                "city": city[0],
                "reason": f"Hub average {city[1]['average_score']} below target",
                "recommended_action": f"Investigate systemic issues at {city[0]} hub"
            })
        
        return priorities
    
    def _analyze_trends(self) -> Dict:
        """Analyze score trends (placeholder for time-series data)."""
        # In production, this would compare against historical data
        return {
            "note": "Trend analysis requires historical data",
            "current_average": self._generate_overview()["average_score"],
            "sample_size": len(self.evaluations)
        }
    
    def print_analytics_summary(self, report: Dict) -> str:
        """Generate a formatted text summary of analytics."""
        lines = []
        
        lines.append("=" * 70)
        lines.append("              AUTO-QA ANALYTICS DASHBOARD")
        lines.append("=" * 70)
        lines.append(f"Generated: {report['generated_at']}")
        lines.append(f"Total Calls Analyzed: {report['total_calls_analyzed']}")
        lines.append("")
        
        # Overview
        overview = report["overview"]
        lines.append("-" * 70)
        lines.append("OVERVIEW METRICS")
        lines.append("-" * 70)
        lines.append(f"  Average Score: {overview['average_score']}/100")
        lines.append(f"  Score Range: {overview['min_score']} - {overview['max_score']}")
        lines.append(f"  Calls Needing Review: {overview['calls_needing_review']} ({overview['review_percentage']}%)")
        lines.append("")
        lines.append("  Score Distribution:")
        for bucket, count in overview["score_distribution"].items():
            bar = "#" * count * 2
            lines.append(f"    {bucket:25} {bar} ({count})")
        lines.append("")
        
        # Pillar Analysis
        pillars = report["pillar_analysis"]
        lines.append("-" * 70)
        lines.append("PILLAR PERFORMANCE")
        lines.append("-" * 70)
        for pillar, data in pillars["pillar_details"].items():
            status = "OK" if data["average_score"] >= 70 else "NEEDS ATTENTION"
            lines.append(f"  {pillar.replace('_', ' ').title():25} {data['average_score']:5.1f}/100  [{status}]")
        lines.append(f"\n  Weakest Pillar: {pillars['weakest_pillar']}")
        lines.append(f"  Strongest Pillar: {pillars['strongest_pillar']}")
        lines.append("")
        
        # Complaint Distribution
        complaints = report["complaint_distribution"]
        lines.append("-" * 70)
        lines.append("TOP COMPLAINT TYPES")
        lines.append("-" * 70)
        for complaint, data in complaints.get("most_common", [])[:5]:
            lines.append(f"  {complaint.replace('_', ' ').title():25} {data['count']} calls ({data['percentage']}%)")
        lines.append("")
        
        # Agent Leaderboard
        agents = report["agent_performance"]
        lines.append("-" * 70)
        lines.append("AGENT LEADERBOARD (Top 5)")
        lines.append("-" * 70)
        for agent in agents["leaderboard"][:5]:
            lines.append(f"  #{agent['rank']} {agent['agent_name']:20} Score: {agent['average_score']} ({agent['total_calls']} calls)")
        lines.append("")
        
        # City Performance
        cities = report["city_performance"]
        lines.append("-" * 70)
        lines.append("CITY HUB RANKING")
        lines.append("-" * 70)
        for city in cities["ranking"]:
            status = "OK" if city["average_score"] >= 70 else "BELOW TARGET"
            lines.append(f"  #{city['rank']} {city['city']:15} Score: {city['average_score']} [{status}]")
        lines.append("")
        
        # Risk Summary
        risks = report["risk_summary"]
        lines.append("-" * 70)
        lines.append("RISK & COMPLIANCE")
        lines.append("-" * 70)
        lines.append(f"  Total Flagged Calls: {risks['total_flagged_calls']} ({risks['flagged_percentage']}%)")
        if risks["risk_distribution"]:
            lines.append("  Risk Types Detected:")
            for risk_type, count in risks["risk_distribution"].items():
                lines.append(f"    - {risk_type}: {count}")
        lines.append("")
        
        # Coaching Priorities
        priorities = report["coaching_priorities"]
        lines.append("-" * 70)
        lines.append("COACHING PRIORITIES")
        lines.append("-" * 70)
        for i, priority in enumerate(priorities[:5], 1):
            lines.append(f"  {i}. [{priority['type']}] {priority['area']}")
            if "agent" in priority:
                lines.append(f"     Agent: {priority['agent']}")
            if "city" in priority:
                lines.append(f"     City: {priority['city']}")
            lines.append(f"     Action: {priority['recommended_action']}")
        lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
