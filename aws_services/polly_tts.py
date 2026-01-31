"""
AWS Polly TTS Handler with Streaming Support

Provides high-quality Neural text-to-speech using AWS Polly
with streaming for low-latency voice applications.

Features:
- Neural voices for professional quality
- Streaming audio for immediate playback
- SSML support for natural speech patterns
- Indian English voices (Kajal, Aditi)
"""

import os
import io
import logging
from typing import Generator, Optional, Union
from dataclasses import dataclass

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


# Available Polly voices for Indian English
POLLY_VOICES = {
    "kajal": {
        "voice_id": "Kajal",
        "engine": "neural",
        "language_code": "en-IN",
        "gender": "Female",
        "description": "Premium Indian English female voice"
    },
    "aditi": {
        "voice_id": "Aditi",
        "engine": "standard",
        "language_code": "en-IN",
        "gender": "Female",
        "description": "Standard Indian English female voice"
    }
}


@dataclass
class AudioChunk:
    """A chunk of audio data."""
    data: bytes
    content_type: str
    is_final: bool = False


class PollyTTS:
    """
    AWS Polly TTS client with streaming support.
    
    Provides high-quality neural text-to-speech with streaming
    for low-latency voice applications.
    """
    
    def __init__(
        self,
        voice_id: str = "Kajal",
        engine: str = "neural",
        language_code: str = "en-IN",
        output_format: str = "mp3",
        sample_rate: str = "24000",
        region: str = None
    ):
        """
        Initialize Polly TTS client.
        
        Args:
            voice_id: Polly voice ID (Kajal or Aditi for Indian English)
            engine: 'neural' for premium quality, 'standard' for basic
            language_code: Language code (en-IN for Indian English)
            output_format: Audio format (mp3, ogg_vorbis, pcm)
            sample_rate: Audio sample rate
            region: AWS region
        """
        self.voice_id = voice_id
        self.engine = engine
        self.language_code = language_code
        self.output_format = output_format
        self.sample_rate = sample_rate
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.client = None
        
        # Set content type based on format
        self.content_type = {
            'mp3': 'audio/mpeg',
            'ogg_vorbis': 'audio/ogg',
            'pcm': 'audio/pcm'
        }.get(output_format, 'audio/mpeg')
        
        if BOTO3_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Polly client."""
        try:
            config = Config(
                retries={'max_attempts': 2, 'mode': 'adaptive'},
                connect_timeout=5,
                read_timeout=30
            )
            
            self.client = boto3.client(
                'polly',
                region_name=self.region,
                config=config
            )
            logger.info(f"Polly client initialized with voice: {self.voice_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Polly client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Polly is available and configured."""
        return self.client is not None
    
    def synthesize_speech(self, text: str, use_ssml: bool = False) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize (plain text or SSML)
            use_ssml: Whether text is SSML formatted
            
        Returns:
            Audio data as bytes
        """
        if not self.client:
            raise RuntimeError("Polly client not initialized")
        
        # Build request
        request_params = {
            "Engine": self.engine,
            "LanguageCode": self.language_code,
            "OutputFormat": self.output_format,
            "SampleRate": self.sample_rate,
            "Text": text,
            "TextType": "ssml" if use_ssml else "text",
            "VoiceId": self.voice_id
        }
        
        try:
            response = self.client.synthesize_speech(**request_params)
            
            # Read audio stream
            audio_stream = response['AudioStream']
            audio_data = audio_stream.read()
            audio_stream.close()
            
            return audio_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Polly API error: {error_code} - {e}")
            raise
    
    def synthesize_speech_streaming(
        self, 
        text: str, 
        chunk_size: int = 4096,
        use_ssml: bool = False
    ) -> Generator[AudioChunk, None, None]:
        """
        Synthesize speech with streaming output.
        
        Args:
            text: Text to synthesize
            chunk_size: Size of audio chunks to yield
            use_ssml: Whether text is SSML formatted
            
        Yields:
            AudioChunk objects containing audio data
        """
        if not self.client:
            raise RuntimeError("Polly client not initialized")
        
        request_params = {
            "Engine": self.engine,
            "LanguageCode": self.language_code,
            "OutputFormat": self.output_format,
            "SampleRate": self.sample_rate,
            "Text": text,
            "TextType": "ssml" if use_ssml else "text",
            "VoiceId": self.voice_id
        }
        
        try:
            response = self.client.synthesize_speech(**request_params)
            audio_stream = response['AudioStream']
            
            while True:
                chunk = audio_stream.read(chunk_size)
                if not chunk:
                    break
                yield AudioChunk(
                    data=chunk,
                    content_type=self.content_type,
                    is_final=False
                )
            
            # Send final marker
            yield AudioChunk(
                data=b'',
                content_type=self.content_type,
                is_final=True
            )
            
            audio_stream.close()
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Polly streaming error: {error_code} - {e}")
            raise
    
    def text_to_ssml(self, text: str, rate: str = "medium", pitch: str = "medium") -> str:
        """
        Convert plain text to SSML with prosody controls.
        
        Args:
            text: Plain text to convert
            rate: Speech rate (x-slow, slow, medium, fast, x-fast)
            pitch: Voice pitch (x-low, low, medium, high, x-high)
            
        Returns:
            SSML formatted text
        """
        # Escape special XML characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        
        ssml = f'''<speak>
    <prosody rate="{rate}" pitch="{pitch}">
        {text}
    </prosody>
</speak>'''
        
        return ssml
    
    def add_emphasis(self, text: str, level: str = "moderate") -> str:
        """
        Add emphasis to text for SSML.
        
        Args:
            text: Text to emphasize
            level: Emphasis level (strong, moderate, reduced)
            
        Returns:
            SSML emphasis markup
        """
        return f'<emphasis level="{level}">{text}</emphasis>'
    
    def add_pause(self, duration_ms: int = 500) -> str:
        """
        Add a pause for SSML.
        
        Args:
            duration_ms: Pause duration in milliseconds
            
        Returns:
            SSML break markup
        """
        return f'<break time="{duration_ms}ms"/>'


class PollyTTSHandler:
    """
    High-level TTS handler that integrates with the voice agent.
    Provides the same interface as the Edge TTS handler for drop-in replacement.
    """
    
    def __init__(
        self,
        voice: str = "kajal",
        region: str = None
    ):
        """
        Initialize Polly TTS handler.
        
        Args:
            voice: Voice name (kajal or aditi)
            region: AWS region
        """
        voice_config = POLLY_VOICES.get(voice.lower(), POLLY_VOICES["kajal"])
        
        self.polly = PollyTTS(
            voice_id=voice_config["voice_id"],
            engine=voice_config["engine"],
            language_code=voice_config["language_code"],
            region=region
        )
        
        self.voice_name = voice_config["voice_id"]
    
    def is_available(self) -> bool:
        """Check if Polly is available."""
        return self.polly.is_available()
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio (async wrapper).
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio bytes (MP3)
        """
        # Polly is synchronous, but we wrap for async compatibility
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.polly.synthesize_speech, 
            text
        )
    
    def synthesize_sync(self, text: str) -> bytes:
        """
        Synthesize text to audio (synchronous).
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio bytes (MP3)
        """
        return self.polly.synthesize_speech(text)
    
    def synthesize_streaming(
        self, 
        text: str, 
        chunk_size: int = 4096
    ) -> Generator[bytes, None, None]:
        """
        Synthesize with streaming output.
        
        Args:
            text: Text to synthesize
            chunk_size: Audio chunk size
            
        Yields:
            Audio data chunks
        """
        for chunk in self.polly.synthesize_speech_streaming(text, chunk_size):
            if chunk.data:
                yield chunk.data


# Fallback to Edge TTS when Polly is unavailable
class FallbackTTSHandler:
    """
    Fallback TTS handler that uses Edge TTS when Polly is unavailable.
    """
    
    def __init__(self):
        self.polly_handler = None
        self.edge_handler = None
        
        # Try Polly first
        if BOTO3_AVAILABLE:
            try:
                self.polly_handler = PollyTTSHandler()
                if self.polly_handler.is_available():
                    logger.info("Using AWS Polly for TTS")
                    return
            except Exception as e:
                logger.warning(f"Polly initialization failed: {e}")
                self.polly_handler = None
        
        # Fall back to Edge TTS
        try:
            from speech.tts_handler import TTSHandler
            self.edge_handler = TTSHandler()
            logger.info("Using Edge TTS as fallback")
        except ImportError:
            logger.warning("Neither Polly nor Edge TTS available")
    
    def is_available(self) -> bool:
        """Check if any TTS is available."""
        if self.polly_handler and self.polly_handler.is_available():
            return True
        return self.edge_handler is not None
    
    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio."""
        if self.polly_handler and self.polly_handler.is_available():
            return await self.polly_handler.synthesize(text)
        elif self.edge_handler:
            return await self.edge_handler.synthesize(text)
        else:
            raise RuntimeError("No TTS handler available")
    
    def synthesize_sync(self, text: str) -> bytes:
        """Synthesize text to audio (sync)."""
        if self.polly_handler and self.polly_handler.is_available():
            return self.polly_handler.synthesize_sync(text)
        elif self.edge_handler:
            import asyncio
            return asyncio.run(self.edge_handler.synthesize(text))
        else:
            raise RuntimeError("No TTS handler available")
