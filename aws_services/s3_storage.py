"""
AWS S3 Storage Handler

Provides S3 storage for voice transcripts and call recordings
with automatic fallback to local filesystem when S3 is unavailable.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Union
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Check for boto3
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. Run: pip install boto3")


class S3Storage:
    """
    S3 storage handler with local filesystem fallback.
    
    Provides consistent interface for storing transcripts and recordings
    whether using S3 or local files.
    """
    
    def __init__(
        self,
        bucket_name: str = None,
        prefix: str = "",
        local_fallback_dir: str = None,
        region: str = None
    ):
        """
        Initialize S3 storage handler.
        
        Args:
            bucket_name: S3 bucket name (uses AWS_S3_BUCKET env var if not provided)
            prefix: Key prefix for all objects
            local_fallback_dir: Local directory for fallback storage
            region: AWS region
        """
        self.bucket_name = bucket_name or os.getenv('AWS_S3_BUCKET', '')
        self.prefix = prefix
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.client = None
        self.use_s3 = False
        
        # Set up local fallback directory
        if local_fallback_dir:
            self.local_dir = Path(local_fallback_dir)
        else:
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.local_dir = base_dir / 'voice_transcripts'
        
        self.local_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize S3 if available and configured
        if BOTO3_AVAILABLE and self.bucket_name:
            self._initialize_s3()
    
    def _initialize_s3(self):
        """Initialize S3 client."""
        try:
            config = Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                connect_timeout=5,
                read_timeout=30
            )
            
            self.client = boto3.client(
                's3',
                region_name=self.region,
                config=config
            )
            
            # Verify bucket access
            self.client.head_bucket(Bucket=self.bucket_name)
            self.use_s3 = True
            logger.info(f"S3 storage initialized: {self.bucket_name}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"S3 bucket not found: {self.bucket_name}")
            elif error_code == '403':
                logger.warning(f"Access denied to S3 bucket: {self.bucket_name}")
            else:
                logger.warning(f"S3 initialization error: {e}")
            self.use_s3 = False
            
        except Exception as e:
            logger.warning(f"S3 client error: {e}")
            self.use_s3 = False
    
    def is_s3_enabled(self) -> bool:
        """Check if S3 storage is being used."""
        return self.use_s3
    
    def _get_s3_key(self, filename: str) -> str:
        """Get full S3 key with prefix."""
        if self.prefix:
            return f"{self.prefix.rstrip('/')}/{filename}"
        return filename
    
    def _get_local_path(self, filename: str) -> Path:
        """Get local file path."""
        return self.local_dir / filename
    
    # =========================================================================
    # JSON Operations (for transcripts)
    # =========================================================================
    
    def save_json(self, filename: str, data: Dict) -> str:
        """
        Save JSON data to storage.
        
        Args:
            filename: File name (e.g., 'session_123.json')
            data: Dictionary to save
            
        Returns:
            Storage location (S3 URI or local path)
        """
        json_str = json.dumps(data, indent=2, default=str)
        
        if self.use_s3:
            try:
                key = self._get_s3_key(filename)
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=json_str.encode('utf-8'),
                    ContentType='application/json'
                )
                location = f"s3://{self.bucket_name}/{key}"
                logger.debug(f"Saved JSON to S3: {location}")
                return location
                
            except ClientError as e:
                logger.error(f"S3 save error: {e}, falling back to local")
        
        # Local fallback
        local_path = self._get_local_path(filename)
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        logger.debug(f"Saved JSON locally: {local_path}")
        return str(local_path)
    
    def load_json(self, filename: str) -> Optional[Dict]:
        """
        Load JSON data from storage.
        
        Args:
            filename: File name to load
            
        Returns:
            Dictionary or None if not found
        """
        if self.use_s3:
            try:
                key = self._get_s3_key(filename)
                response = self.client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                content = response['Body'].read().decode('utf-8')
                return json.loads(content)
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.debug(f"JSON not found in S3: {filename}")
                else:
                    logger.error(f"S3 load error: {e}")
        
        # Local fallback
        local_path = self._get_local_path(filename)
        if local_path.exists():
            with open(local_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def list_json_files(self, prefix: str = "") -> List[str]:
        """
        List JSON files in storage.
        
        Args:
            prefix: Additional prefix to filter by
            
        Returns:
            List of filenames
        """
        files = []
        
        if self.use_s3:
            try:
                full_prefix = self._get_s3_key(prefix)
                paginator = self.client.get_paginator('list_objects_v2')
                
                for page in paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=full_prefix
                ):
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        if key.endswith('.json'):
                            # Remove prefix to get just filename
                            filename = key.replace(self.prefix, '').lstrip('/')
                            files.append(filename)
                
                return files
                
            except ClientError as e:
                logger.error(f"S3 list error: {e}")
        
        # Local fallback
        for path in self.local_dir.glob(f"{prefix}*.json"):
            files.append(path.name)
        
        return files
    
    # =========================================================================
    # Binary Operations (for audio recordings)
    # =========================================================================
    
    def save_audio(self, filename: str, audio_data: bytes, content_type: str = "audio/mpeg") -> str:
        """
        Save audio data to storage.
        
        Args:
            filename: File name (e.g., 'recording_123.mp3')
            audio_data: Audio bytes
            content_type: MIME type
            
        Returns:
            Storage location
        """
        if self.use_s3:
            try:
                key = self._get_s3_key(filename)
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=audio_data,
                    ContentType=content_type
                )
                location = f"s3://{self.bucket_name}/{key}"
                logger.debug(f"Saved audio to S3: {location}")
                return location
                
            except ClientError as e:
                logger.error(f"S3 audio save error: {e}, falling back to local")
        
        # Local fallback
        local_path = self._get_local_path(filename)
        with open(local_path, 'wb') as f:
            f.write(audio_data)
        logger.debug(f"Saved audio locally: {local_path}")
        return str(local_path)
    
    def load_audio(self, filename: str) -> Optional[bytes]:
        """
        Load audio data from storage.
        
        Args:
            filename: File name to load
            
        Returns:
            Audio bytes or None if not found
        """
        if self.use_s3:
            try:
                key = self._get_s3_key(filename)
                response = self.client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                return response['Body'].read()
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    logger.error(f"S3 audio load error: {e}")
        
        # Local fallback
        local_path = self._get_local_path(filename)
        if local_path.exists():
            with open(local_path, 'rb') as f:
                return f.read()
        
        return None
    
    def delete(self, filename: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            filename: File name to delete
            
        Returns:
            True if deleted successfully
        """
        if self.use_s3:
            try:
                key = self._get_s3_key(filename)
                self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                logger.debug(f"Deleted from S3: {key}")
                return True
                
            except ClientError as e:
                logger.error(f"S3 delete error: {e}")
        
        # Local fallback
        local_path = self._get_local_path(filename)
        if local_path.exists():
            local_path.unlink()
            logger.debug(f"Deleted locally: {local_path}")
            return True
        
        return False
    
    def get_presigned_url(self, filename: str, expiration: int = 3600) -> Optional[str]:
        """
        Get a presigned URL for downloading a file.
        
        Args:
            filename: File name
            expiration: URL expiration in seconds
            
        Returns:
            Presigned URL or None if not using S3
        """
        if not self.use_s3:
            return None
        
        try:
            key = self._get_s3_key(filename)
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            logger.error(f"Presigned URL error: {e}")
            return None


class TranscriptStorage(S3Storage):
    """
    Specialized storage handler for voice transcripts.
    """
    
    def __init__(self, bucket_name: str = None, region: str = None):
        super().__init__(
            bucket_name=bucket_name,
            prefix=os.getenv('AWS_S3_TRANSCRIPTS_PREFIX', 'voice_transcripts/'),
            local_fallback_dir=None,  # Uses default voice_transcripts dir
            region=region
        )
    
    def save_transcript(self, session_id: str, transcript_data: Dict) -> str:
        """
        Save a voice session transcript.
        
        Args:
            session_id: Session ID
            transcript_data: Transcript data dictionary
            
        Returns:
            Storage location
        """
        filename = f"{session_id}.json"
        return self.save_json(filename, transcript_data)
    
    def load_transcript(self, session_id: str) -> Optional[Dict]:
        """
        Load a voice session transcript.
        
        Args:
            session_id: Session ID
            
        Returns:
            Transcript data or None
        """
        filename = f"{session_id}.json"
        return self.load_json(filename)
    
    def list_transcripts(self, limit: int = 100) -> List[Dict]:
        """
        List recent transcripts.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of transcript metadata
        """
        files = self.list_json_files()[:limit]
        transcripts = []
        
        for filename in files:
            session_id = filename.replace('.json', '')
            data = self.load_json(filename)
            if data:
                transcripts.append({
                    'session_id': session_id,
                    'start_time': data.get('start_time'),
                    'duration_seconds': data.get('duration_seconds'),
                    'agent_name': data.get('agent_name')
                })
        
        return transcripts


class RecordingStorage(S3Storage):
    """
    Specialized storage handler for call recordings.
    """
    
    def __init__(self, bucket_name: str = None, region: str = None):
        super().__init__(
            bucket_name=bucket_name,
            prefix=os.getenv('AWS_S3_RECORDINGS_PREFIX', 'raw_recordings/'),
            local_fallback_dir=None,
            region=region
        )
    
    def save_recording(
        self, 
        call_id: str, 
        audio_data: bytes, 
        format: str = "mp3"
    ) -> str:
        """
        Save a call recording.
        
        Args:
            call_id: Call ID
            audio_data: Audio bytes
            format: Audio format (mp3, wav)
            
        Returns:
            Storage location
        """
        content_type = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg'
        }.get(format, 'audio/mpeg')
        
        filename = f"{call_id}.{format}"
        return self.save_audio(filename, audio_data, content_type)
    
    def get_recording_url(self, call_id: str, format: str = "mp3") -> Optional[str]:
        """
        Get a presigned URL for a recording.
        
        Args:
            call_id: Call ID
            format: Audio format
            
        Returns:
            Presigned URL or None
        """
        filename = f"{call_id}.{format}"
        return self.get_presigned_url(filename)
