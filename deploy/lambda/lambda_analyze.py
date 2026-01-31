"""
Lambda Function: Analyze Transcript
Triggered when a voice transcript is uploaded to S3.
Uses AWS Bedrock to evaluate call quality using the Five-Pillar framework.
"""

import json
import os
import boto3
from typing import Dict, List
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')
sns = boto3.client('sns')

# Environment variables
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'BatterySmart_CallQA_Results')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')


def handler(event, context):
    """
    Main Lambda handler.
    Triggered by S3 ObjectCreated event on voice_transcripts/ prefix.
    """
    print(f"Event: {json.dumps(event)}")
    
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        print(f"Processing transcript: s3://{bucket}/{key}")
        
        try:
            # Load transcript from S3
            transcript_data = load_transcript(bucket, key)
            
            # Analyze with Bedrock
            evaluation = analyze_transcript(transcript_data)
            
            # Store results in DynamoDB
            store_results(evaluation)
            
            # Send supervisor alert if needed
            if should_alert_supervisor(evaluation):
                send_supervisor_alert(evaluation)
            
            print(f"Successfully processed: {evaluation['call_id']}")
            
        except Exception as e:
            print(f"Error processing {key}: {e}")
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Transcripts processed successfully'})
    }


def load_transcript(bucket: str, key: str) -> Dict:
    """Load transcript JSON from S3."""
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    return json.loads(content)


def analyze_transcript(transcript_data: Dict) -> Dict:
    """
    Analyze transcript using AWS Bedrock.
    Returns structured evaluation following Five-Pillar framework.
    """
    session_id = transcript_data.get('session_id', 'UNKNOWN')
    formatted_transcript = transcript_data.get('formatted_transcript', '')
    
    # Build analysis prompt
    prompt = build_analysis_prompt(formatted_transcript)
    
    # Call Bedrock
    response = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        inferenceConfig={
            "maxTokens": 2048,
            "temperature": 0.1
        }
    )
    
    # Parse response
    response_text = response['output']['message']['content'][0]['text']
    
    try:
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        evaluation_json = json.loads(response_text[json_start:json_end])
    except (json.JSONDecodeError, ValueError):
        # Fallback evaluation
        evaluation_json = {
            "overall_score": 50,
            "violation_flags": ["analysis_error"],
            "summary_insight": "Unable to fully analyze transcript"
        }
    
    # Build final evaluation
    evaluation = {
        "call_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": transcript_data.get('agent_name', 'UNKNOWN'),
        "transcript_text": formatted_transcript[:10000],  # Limit size
        "duration_seconds": transcript_data.get('duration_seconds', 0),
        "overall_score": evaluation_json.get('overall_score', 0),
        "pillar_scores": {
            "script_adherence": evaluation_json.get('script_adherence', 0),
            "resolution_correctness": evaluation_json.get('resolution_correctness', 0),
            "sentiment_handling": evaluation_json.get('sentiment_handling', 0),
            "communication_quality": evaluation_json.get('communication_quality', 0),
            "risk_compliance": evaluation_json.get('risk_compliance', 0)
        },
        "violation_flags": evaluation_json.get('violation_flags', []),
        "summary_insight": evaluation_json.get('summary_insight', ''),
        "llm_provider": "bedrock"
    }
    
    return evaluation


def build_analysis_prompt(transcript: str) -> str:
    """Build the prompt for Bedrock analysis."""
    return f"""Analyze this customer support call transcript for Battery Smart (electric vehicle battery swap company) and score it according to the Five-Pillar QA framework.

TRANSCRIPT:
{transcript}

Evaluate the call and respond with a JSON object containing:
1. overall_score: 0-100 score
2. script_adherence: 0-100 (did agent follow greeting, verification, closing scripts?)
3. resolution_correctness: 0-100 (did agent follow SOPs for the issue type?)
4. sentiment_handling: 0-100 (empathy, de-escalation, customer satisfaction)
5. communication_quality: 0-100 (clarity, professionalism, tone)
6. risk_compliance: 0-100 (avoided legal issues, safety concerns addressed)
7. violation_flags: array of strings listing any policy violations
8. summary_insight: brief 1-2 sentence summary of call quality

BATTERY SMART SOPs:
- Battery locked: Ask for restart, offer station visit
- Billing issues: Explain refund timeline (3-7 days)
- Swap station: Guide to app for nearest location
- Subscription: Explain all plan options

Respond ONLY with valid JSON:"""


def store_results(evaluation: Dict):
    """Store evaluation results in DynamoDB."""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    # Convert sets to lists for DynamoDB compatibility
    item = {
        'call_id': evaluation['call_id'],
        'timestamp': evaluation['timestamp'],
        'agent_id': evaluation['agent_id'],
        'transcript_text': evaluation['transcript_text'],
        'duration_seconds': evaluation['duration_seconds'],
        'overall_score': int(evaluation['overall_score']),
        'pillar_scores': evaluation['pillar_scores'],
        'violation_flags': evaluation['violation_flags'],
        'summary_insight': evaluation['summary_insight'],
        'llm_provider': evaluation['llm_provider']
    }
    
    table.put_item(Item=item)
    print(f"Stored evaluation for call_id: {evaluation['call_id']}")


def should_alert_supervisor(evaluation: Dict) -> bool:
    """Determine if supervisor alert is needed."""
    # Alert if score < 60 or there are violation flags
    if evaluation['overall_score'] < 60:
        return True
    
    if evaluation['violation_flags']:
        return True
    
    return False


def send_supervisor_alert(evaluation: Dict):
    """Send alert to supervisor via SNS."""
    if not SNS_TOPIC_ARN:
        print("SNS topic not configured, skipping alert")
        return
    
    message = f"""
⚠️ QA ALERT: Call Requires Review

Call ID: {evaluation['call_id']}
Agent: {evaluation['agent_id']}
Score: {evaluation['overall_score']}/100
Duration: {evaluation['duration_seconds']} seconds

Violations: {', '.join(evaluation['violation_flags']) or 'None'}

Summary: {evaluation['summary_insight']}

Please review this call in the QA dashboard.
"""
    
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"QA Alert: Call {evaluation['call_id']} - Score {evaluation['overall_score']}",
        Message=message
    )
    
    print(f"Sent supervisor alert for call_id: {evaluation['call_id']}")
