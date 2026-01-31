"""
AWS Configuration Module
Handles AWS credentials and service configuration with local fallbacks.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AWSConfig:
    """AWS Configuration with environment-based settings."""
    
    # General AWS settings
    use_aws: bool = False
    use_aws_bedrock: bool = False  # Separate flag for Bedrock
    region: str = "us-east-1"
    
    # Credentials
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    
    # Bedrock settings
    bedrock_model: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    bedrock_streaming: bool = True
    
    # Polly settings
    polly_voice: str = "Kajal"
    polly_engine: str = "neural"
    polly_language: str = "en-IN"
    
    # S3 settings
    s3_bucket: str = "battery-smart-transcripts"
    s3_transcripts_prefix: str = "voice_transcripts/"
    s3_recordings_prefix: str = "raw_recordings/"
    
    # DynamoDB settings
    dynamodb_table_prefix: str = "BatterySmart_"
    
    # SNS settings
    sns_topic_arn: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> "AWSConfig":
        """Load configuration from environment variables."""
        use_aws = os.getenv("USE_AWS", "false").lower() == "true"
        use_aws_bedrock = os.getenv("USE_AWS_BEDROCK", "true").lower() == "true"
        
        # If USE_AWS is true but USE_AWS_BEDROCK is not set, check for Bedrock model
        if use_aws and os.getenv("USE_AWS_BEDROCK") is None:
            # Default to false if GEMINI_API_KEY is set
            use_aws_bedrock = not bool(os.getenv("GEMINI_API_KEY"))
        
        return cls(
            use_aws=use_aws,
            use_aws_bedrock=use_aws and use_aws_bedrock,
            region=os.getenv("AWS_REGION", "us-east-1"),
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            session_token=os.getenv("AWS_SESSION_TOKEN"),
            bedrock_model=os.getenv("AWS_BEDROCK_MODEL", "anthropic.claude-sonnet-4-20250514-v1:0"),
            bedrock_streaming=os.getenv("AWS_BEDROCK_STREAMING", "true").lower() == "true",
            polly_voice=os.getenv("AWS_POLLY_VOICE", "Kajal"),
            polly_engine=os.getenv("AWS_POLLY_ENGINE", "neural"),
            polly_language=os.getenv("AWS_POLLY_LANGUAGE", "en-IN"),
            s3_bucket=os.getenv("AWS_S3_BUCKET", "battery-smart-transcripts"),
            s3_transcripts_prefix=os.getenv("AWS_S3_TRANSCRIPTS_PREFIX", "voice_transcripts/"),
            s3_recordings_prefix=os.getenv("AWS_S3_RECORDINGS_PREFIX", "raw_recordings/"),
            dynamodb_table_prefix=os.getenv("AWS_DYNAMODB_TABLE_PREFIX", "BatterySmart_"),
            sns_topic_arn=os.getenv("AWS_SNS_TOPIC_ARN"),
        )
    
    def is_aws_available(self) -> bool:
        """Check if AWS credentials are configured."""
        return bool(self.use_aws and self.access_key_id and self.secret_access_key)
    
    def is_bedrock_available(self) -> bool:
        """Check if Bedrock should be used."""
        return bool(self.is_aws_available() and self.use_aws_bedrock)
    
    def is_polly_available(self) -> bool:
        """Check if Polly should be used (uses AWS but not Bedrock flag)."""
        return self.is_aws_available()
    
    def is_s3_available(self) -> bool:
        """Check if S3 should be used."""
        return bool(self.is_aws_available() and self.s3_bucket)


# Global configuration instance
_config: Optional[AWSConfig] = None


def get_aws_config() -> AWSConfig:
    """Get the global AWS configuration instance."""
    global _config
    if _config is None:
        _config = AWSConfig.from_environment()
    return _config


def reload_config() -> AWSConfig:
    """Reload configuration from environment."""
    global _config
    _config = AWSConfig.from_environment()
    return _config
