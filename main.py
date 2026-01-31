"""
Auto-QA System - Main Demo Script
Demonstrates the enhanced Five-Pillar call evaluation system with analytics.
"""

import sys
import io
from typing import Dict, List

# Fix encoding for Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from call_evaluator import CallEvaluator, CallMetadata
from analytics import AnalyticsEngine
from sample_transcripts import ALL_TRANSCRIPTS, SAMPLE_METADATA


def run_demo():
    """Run the enhanced Auto-QA system demo with analytics."""
    
    print("\n" + "=" * 70)
    print("        BATTERY SMART AUTO-QA SYSTEM v2.0")
    print("        Five-Pillar Call Evaluation + Analytics")
    print("=" * 70)
    
    evaluator = CallEvaluator()
    analytics = AnalyticsEngine()
    
    # Evaluate all sample transcripts
    print("\n[1/3] EVALUATING SAMPLE CALLS...")
    print("-" * 70)
    
    evaluations = []
    for call_type, transcript in ALL_TRANSCRIPTS.items():
        metadata = SAMPLE_METADATA.get(call_type, {})
        
        meta = CallMetadata(
            call_id=metadata.get("call_id", f"CALL-{call_type}"),
            agent_id=metadata.get("agent_id", "UNKNOWN"),
            agent_name=metadata.get("agent_name", "Unknown Agent"),
            city=metadata.get("city", "Unknown"),
            timestamp=metadata.get("timestamp", "Unknown"),
            duration_seconds=metadata.get("duration_seconds", 0)
        )
        
        # Evaluate
        evaluation = evaluator.evaluate_call(transcript, meta)
        evaluations.append(evaluation)
        
        # Add to analytics
        analytics.add_evaluation(evaluation)
        
        # Print summary
        score = evaluation["overall"]["score"]
        grade = evaluation["overall"]["grade"]
        review = "**REVIEW**" if evaluation["overall"]["needs_supervisor_review"] else ""
        
        print(f"  {call_type:20} | Score: {score:5.1f} | {grade:20} {review}")
    
    print("-" * 70)
    print(f"  Total calls evaluated: {len(evaluations)}")
    
    # Show detailed breakdown for one call
    print("\n" + "=" * 70)
    print("[2/3] DETAILED EVALUATION EXAMPLE (Billing Issue)")
    print("=" * 70)
    
    billing_eval = evaluations[2]  # Billing call
    print_detailed_evaluation(billing_eval)
    
    # Generate and display analytics
    print("\n" + "=" * 70)
    print("[3/3] ANALYTICS DASHBOARD")
    print("=" * 70)
    
    analytics_report = analytics.generate_analytics_report()
    summary = analytics.print_analytics_summary(analytics_report)
    print(summary)
    
    print("\n" + "=" * 70)
    print("                    DEMO COMPLETE")
    print("=" * 70)


def print_detailed_evaluation(evaluation: Dict):
    """Print detailed breakdown of a single evaluation."""
    
    meta = evaluation["metadata"]
    overall = evaluation["overall"]
    
    print(f"\nCall ID: {meta['call_id']}")
    print(f"Agent: {meta['agent_name']} ({meta['agent_id']})")
    print(f"City: {meta['city']}")
    print(f"Timestamp: {meta['timestamp']}")
    
    print(f"\n>>> OVERALL SCORE: {overall['score']}/100 ({overall['grade']})")
    
    if overall["needs_supervisor_review"]:
        print(">>> STATUS: FLAGGED FOR SUPERVISOR REVIEW")
    
    print("\n--- PILLAR BREAKDOWN ---")
    for pillar, data in evaluation["pillar_scores"].items():
        bar = create_bar(data["score"])
        print(f"  {pillar.replace('_', ' ').title():25} {bar} {data['score']:5.1f}")
    
    print("\n--- COACHING INSIGHTS ---")
    
    if evaluation["coaching_insights"]["strengths"]:
        print("\nStrengths:")
        for s in evaluation["coaching_insights"]["strengths"][:3]:
            print(f"  + {s}")
    
    if evaluation["coaching_insights"]["areas_for_improvement"]:
        print("\nAreas for Improvement:")
        for a in evaluation["coaching_insights"]["areas_for_improvement"][:3]:
            print(f"  - {a}")
    
    if evaluation["coaching_insights"]["top_recommendations"]:
        print("\nTop Recommendations:")
        for i, rec in enumerate(evaluation["coaching_insights"]["top_recommendations"][:3], 1):
            # Truncate long recommendations
            rec_short = rec[:80] + "..." if len(rec) > 80 else rec
            print(f"  {i}. {rec_short}")
    
    if evaluation["supervisor_alerts"]:
        print("\n--- SUPERVISOR ALERTS ---")
        for alert in evaluation["supervisor_alerts"]:
            print(f"  [!] {alert['category']}: {', '.join(alert['keywords_matched'])}")


def create_bar(score: float, width: int = 20) -> str:
    """Create a visual progress bar."""
    filled = int((score / 100) * width)
    empty = width - filled
    return f"[{'#' * filled}{'-' * empty}]"





def evaluate_single_call(transcript: str, 
                         agent_name: str = "Unknown Agent",
                         agent_id: str = "UNKNOWN",
                         city: str = "Unknown") -> Dict:
    """Evaluate a single call transcript."""
    
    evaluator = CallEvaluator()
    
    metadata = CallMetadata(
        call_id="SINGLE-EVAL",
        agent_id=agent_id,
        agent_name=agent_name,
        city=city,
        timestamp="Manual evaluation"
    )
    
    return evaluator.evaluate_call(transcript, metadata)


def run_batch_analytics(transcripts: list, metadata_list: list = None) -> Dict:
    """Run analytics on a batch of transcripts."""
    
    evaluator = CallEvaluator()
    analytics = AnalyticsEngine()
    
    for i, transcript in enumerate(transcripts):
        if metadata_list and i < len(metadata_list):
            meta_dict = metadata_list[i]
            meta = CallMetadata(**meta_dict)
        else:
            meta = CallMetadata(
                call_id=f"BATCH-{i+1}",
                agent_id="UNKNOWN",
                agent_name="Unknown",
                city="Unknown",
                timestamp="Batch processing"
            )
        
        evaluation = evaluator.evaluate_call(transcript, meta)
        analytics.add_evaluation(evaluation)
    
    return analytics.generate_analytics_report()


if __name__ == "__main__":
    run_demo()
