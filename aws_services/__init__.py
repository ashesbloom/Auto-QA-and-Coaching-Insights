"""
AWS Services Abstraction Layer for Battery Smart Auto-QA System

This module provides AWS service integrations with automatic fallback
to local implementations when AWS is not configured.

Environment Variables:
- USE_AWS: Set to 'true' to enable AWS services (default: false)
- AWS_REGION: AWS region for services (default: us-east-1)
- AWS_S3_BUCKET: S3 bucket for transcripts storage
- AWS_DYNAMODB_TABLE_PREFIX: Prefix for DynamoDB tables
- AWS_BEDROCK_MODEL: Bedrock model ID (default: anthropic.claude-3-haiku-20240307-v1:0)
- AWS_POLLY_VOICE: Polly voice ID (default: Kajal)
"""

from .config import AWSConfig, is_aws_enabled
from .bedrock_llm import BedrockLLM
from .polly_tts import PollyTTS
from .s3_storage import S3Storage

__all__ = [
    'AWSConfig',
    'is_aws_enabled',
    'BedrockLLM',
    'PollyTTS',
    'S3Storage'
]
