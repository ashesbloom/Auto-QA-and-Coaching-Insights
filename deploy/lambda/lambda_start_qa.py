"""
Lambda Function: Start QA Process
Triggered when audio recording is uploaded to S3.
Starts AWS Transcribe job for speech-to-text conversion.
"""

import json
import os
import boto3
from datetime import datetime
import uuid

# Initialize AWS clients
s3 = boto3.client('s3')
transcribe = boto3.client('transcribe')

# Environment variables
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', '')


def handler(event, context):
    """
    Main Lambda handler.
    Triggered by S3 ObjectCreated event on raw_recordings/ prefix.
    """
    print(f"Event: {json.dumps(event)}")
    
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Only process audio files
        if not key.endswith(('.mp3', '.wav', '.mp4', '.flac', '.ogg')):
            print(f"Skipping non-audio file: {key}")
            continue
        
        print(f"Starting transcription for: s3://{bucket}/{key}")
        
        try:
            # Extract call ID from filename
            filename = os.path.basename(key)
            call_id = os.path.splitext(filename)[0]
            
            # Start transcription job
            job_name = start_transcription_job(bucket, key, call_id)
            
            print(f"Started transcription job: {job_name}")
            
        except Exception as e:
            print(f"Error processing {key}: {e}")
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Transcription jobs started'})
    }


def start_transcription_job(bucket: str, key: str, call_id: str) -> str:
    """
    Start AWS Transcribe job with speaker diarization.
    
    Returns:
        Job name
    """
    job_name = f"BatterySmart_{call_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Determine media format from extension
    extension = os.path.splitext(key)[1].lower()
    media_format = {
        '.mp3': 'mp3',
        '.wav': 'wav',
        '.mp4': 'mp4',
        '.flac': 'flac',
        '.ogg': 'ogg'
    }.get(extension, 'mp3')
    
    # Output location for transcript
    output_key = f"voice_transcripts/{call_id}.json"
    
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={
            'MediaFileUri': f"s3://{bucket}/{key}"
        },
        MediaFormat=media_format,
        LanguageCode='en-IN',  # Indian English
        Settings={
            'ShowSpeakerLabels': True,
            'MaxSpeakerLabels': 2,  # Agent and Customer
            'ShowAlternatives': False
        },
        OutputBucketName=bucket,
        OutputKey=output_key
    )
    
    return job_name


def get_transcription_result(job_name: str) -> dict:
    """
    Get transcription job result.
    Note: This is for reference - actual result is written to S3 by Transcribe.
    """
    response = transcribe.get_transcription_job(
        TranscriptionJobName=job_name
    )
    
    status = response['TranscriptionJob']['TranscriptionJobStatus']
    
    if status == 'COMPLETED':
        transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
        return {
            'status': 'COMPLETED',
            'transcript_uri': transcript_uri
        }
    elif status == 'FAILED':
        return {
            'status': 'FAILED',
            'error': response['TranscriptionJob'].get('FailureReason', 'Unknown error')
        }
    else:
        return {
            'status': status
        }
