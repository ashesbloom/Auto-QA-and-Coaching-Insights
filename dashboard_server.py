"""
Dashboard Server for Auto-QA System
Flask-based web dashboard for viewing QA analytics.
"""

from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime
import os
import sys

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from call_evaluator import CallEvaluator, CallMetadata
from analytics import AnalyticsEngine
from sample_transcripts import ALL_TRANSCRIPTS, SAMPLE_METADATA

app = Flask(__name__, template_folder='dashboard/templates', static_folder='dashboard/static')

# Global analytics instance with sample data
analytics_engine = AnalyticsEngine()
evaluator = CallEvaluator()
all_evaluations = []

def initialize_sample_data():
    """Load sample data into analytics engine."""
    global all_evaluations
    
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
        
        evaluation = evaluator.evaluate_call(transcript, meta)
        all_evaluations.append(evaluation)
        analytics_engine.add_evaluation(evaluation)

# Initialize on startup
initialize_sample_data()


@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/overview')
def api_overview():
    """API endpoint for overview metrics."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['overview'])


@app.route('/api/pillars')
def api_pillars():
    """API endpoint for pillar analysis."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['pillar_analysis'])


@app.route('/api/agents')
def api_agents():
    """API endpoint for agent leaderboard."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['agent_performance'])


@app.route('/api/cities')
def api_cities():
    """API endpoint for city performance."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['city_performance'])


@app.route('/api/complaints')
def api_complaints():
    """API endpoint for complaint distribution."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['complaint_distribution'])


@app.route('/api/risks')
def api_risks():
    """API endpoint for risk summary."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['risk_summary'])


@app.route('/api/coaching')
def api_coaching():
    """API endpoint for coaching priorities."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['coaching_priorities'])


@app.route('/api/calls')
def api_calls():
    """API endpoint for all evaluated calls."""
    calls = []
    for eval in all_evaluations:
        calls.append({
            'call_id': eval['metadata']['call_id'],
            'agent_name': eval['metadata']['agent_name'],
            'city': eval['metadata']['city'],
            'timestamp': eval['metadata']['timestamp'],
            'score': eval['overall']['score'],
            'grade': eval['overall']['grade'],
            'needs_review': eval['overall']['needs_supervisor_review'],
            'alerts': len(eval.get('supervisor_alerts', []))
        })
    return jsonify(calls)


@app.route('/api/call/<call_id>')
def api_call_detail(call_id):
    """API endpoint for detailed call evaluation."""
    for eval in all_evaluations:
        if eval['metadata']['call_id'] == call_id:
            return jsonify(eval)
    return jsonify({'error': 'Call not found'}), 404


@app.route('/api/full-report')
def api_full_report():
    """API endpoint for full analytics report."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report)


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  Battery Smart Auto-QA Dashboard")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)
