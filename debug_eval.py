"""
Debug Utility: Test QA Evaluation Pipeline
Tests the transcript evaluation without running the full server.
"""

import os
import sys
import json
from datetime import datetime

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import evaluation components
from call_evaluator import CallEvaluator, CallMetadata

# Path to evaluations storage
evaluations_file = os.path.join(os.path.dirname(__file__), 'voice_call_evaluations.json')
transcripts_dir = os.path.join(os.path.dirname(__file__), 'voice_transcripts')


def load_transcript(session_id: str) -> dict:
    """Load a transcript file by session ID."""
    transcript_path = os.path.join(transcripts_dir, f'{session_id}.json')
    
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
    
    with open(transcript_path, 'r') as f:
        return json.load(f)


def evaluate_transcript(session_data: dict) -> dict:
    """Evaluate a transcript using the CallEvaluator."""
    
    # Create evaluator
    evaluator = CallEvaluator()
    
    # Build metadata
    metadata = CallMetadata(
        call_id=session_data.get('session_id', 'UNKNOWN'),
        agent_id="VOICE-AGENT",
        agent_name=session_data.get('agent_name', 'Priya'),
        city="Demo",
        timestamp=session_data.get('start_time', datetime.now().isoformat()),
        duration_seconds=session_data.get('duration_seconds', 0)
    )
    
    # Get formatted transcript
    transcript_text = session_data.get('formatted_transcript', '')
    
    if not transcript_text:
        print("⚠️ Warning: Empty transcript")
        return None
    
    # Run evaluation
    evaluation = evaluator.evaluate_call(transcript_text, metadata)
    
    return evaluation


def save_evaluation(evaluation: dict) -> None:
    """Save evaluation to the evaluations file."""
    evaluations = []
    
    # Load existing evaluations
    if os.path.exists(evaluations_file):
        with open(evaluations_file, 'r') as f:
            try:
                evaluations = json.load(f)
            except json.JSONDecodeError:
                evaluations = []
    
    # Add new evaluation
    evaluations.append(evaluation)
    
    # Save back
    with open(evaluations_file, 'w') as f:
        json.dump(evaluations, f, indent=2)
    
    print(f"✅ Saved evaluation to {evaluations_file}")


def test_evaluation(session_id: str = None):
    """Test evaluation on a specific transcript or the latest one."""
    
    # Find transcript to test
    if session_id:
        transcript_path = os.path.join(transcripts_dir, f'{session_id}.json')
    else:
        # Find the most recent transcript
        files = [f for f in os.listdir(transcripts_dir) if f.endswith('.json')]
        if not files:
            print("❌ No transcript files found in voice_transcripts/")
            return
        
        # Sort by modification time
        files.sort(key=lambda f: os.path.getmtime(os.path.join(transcripts_dir, f)), reverse=True)
        session_id = files[0].replace('.json', '')
        print(f"📂 Using most recent transcript: {session_id}")
    
    try:
        # Load transcript
        session_data = load_transcript(session_id)
        print(f"📝 Loaded session: {session_data['session_id']}")
        print(f"   Duration: {session_data.get('duration_seconds', 0)} seconds")
        print(f"   LLM Provider: {session_data.get('llm_provider', 'unknown')}")
        print(f"   Transcript length: {len(session_data.get('formatted_transcript', ''))} chars")
        
        # Run evaluation
        print("\n🔍 Running evaluation...")
        evaluation = evaluate_transcript(session_data)
        
        if evaluation:
            print("\n✅ Evaluation Successful!")
            print(f"   Overall Score: {evaluation['overall']['score']}")
            print(f"   Grade: {evaluation['overall']['grade']}")
            print(f"   Needs Supervisor Review: {evaluation['overall']['needs_supervisor_review']}")
            
            # Print pillar scores
            print("\n📊 Pillar Scores:")
            for pillar, data in evaluation['pillar_scores'].items():
                print(f"   • {pillar.replace('_', ' ').title()}: {data['score']}/100 (weight: {data['weight']})")
            
            # Print coaching insights
            insights = evaluation.get("coaching_insights", {})
            if insights.get("top_recommendations"):
                print("\n💡 Top Recommendations:")
                for rec in insights.get("top_recommendations", [])[:3]:
                    print(f"   • {rec}")
            
            # Save evaluation
            save_evaluation(evaluation)
        else:
            print("\n❌ Evaluation returned None")
            
    except FileNotFoundError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"\n❌ Evaluation crashed: {e}")
        import traceback
        traceback.print_exc()


def list_transcripts():
    """List all available transcripts."""
    if not os.path.exists(transcripts_dir):
        print("❌ voice_transcripts/ directory not found")
        return
    
    files = [f for f in os.listdir(transcripts_dir) if f.endswith('.json')]
    
    if not files:
        print("📂 No transcripts found")
        return
    
    print(f"📂 Found {len(files)} transcript(s):\n")
    
    for f in sorted(files):
        filepath = os.path.join(transcripts_dir, f)
        with open(filepath, 'r') as file:
            data = json.load(file)
        
        session_id = data.get('session_id', f.replace('.json', ''))
        duration = data.get('duration_seconds', 0)
        llm = data.get('llm_provider', 'unknown')
        timestamp = data.get('start_time', 'unknown')[:19] if data.get('start_time') else 'unknown'
        
        print(f"   {session_id} | {duration}s | {llm} | {timestamp}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug QA Evaluation Pipeline')
    parser.add_argument('--session', '-s', type=str, help='Session ID to evaluate')
    parser.add_argument('--list', '-l', action='store_true', help='List all transcripts')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Battery Smart - QA Evaluation Debugger")
    print("=" * 60)
    
    if args.list:
        list_transcripts()
    else:
        test_evaluation(args.session)
