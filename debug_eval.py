
import os
import sys
import json
from datetime import datetime

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock dependencies
from unified_server import process_and_evaluate_transcript, voice_call_evaluations, evaluations_file

def test_evaluation():
    # Load the transcript file
    transcript_path = os.path.join(os.path.dirname(__file__), 'voice_transcripts', '1ba8cde0.json')
    
    if not os.path.exists(transcript_path):
        print(f"Transcript file not found: {transcript_path}")
        return

    with open(transcript_path, 'r') as f:
        session_data = json.load(f)

    print(f"Loaded session: {session_data['session_id']}")
    print(f"Transcript length: {len(session_data['formatted_transcript'])}")

    # Run evaluation
    print("\nStarting evaluation...")
    try:
        evaluation = process_and_evaluate_transcript(session_data)
        
        if evaluation:
            print("\n✅ Evaluation Successful!")
            print(f"Score: {evaluation['overall']['score']}")
            print(f"Grade: {evaluation['overall']['grade']}")
            
            # Check for AI insights
            insights = evaluation.get("coaching_insights", {})
            print("\nCoaching Insights:")
            for rec in insights.get("top_recommendations", []):
                print(f"  • {rec}")
            
            # Check if file was saved
            if os.path.exists(evaluations_file):
                print(f"✅ evaluations file exists: {evaluations_file}")
            else:
                print("❌ evaluations file does NOT exist")
        else:
            print("\n❌ Evaluation returned None")
            
    except Exception as e:
        print(f"\n❌ Evaluation crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_evaluation()
