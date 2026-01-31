"""
Speech-to-Text Handler for Battery Smart Voice Agent
Uses OpenAI Whisper for transcription.
"""

import os
import tempfile
import wave
import struct
from typing import Optional
import io

# Try to import Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Warning: openai-whisper not installed. Run: pip install openai-whisper")


class STTHandler:
    """
    Speech-to-Text handler using OpenAI Whisper.
    Converts audio to text for the voice agent.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the STT handler.
        
        Args:
            model_size: Whisper model size - "tiny", "base", "small", "medium", "large"
                       Smaller = faster, larger = more accurate
        """
        self.model_size = model_size
        self.model = None
        
        if WHISPER_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load the Whisper model."""
        try:
            print(f"Loading Whisper {self.model_size} model...")
            self.model = whisper.load_model(self.model_size)
            print("Whisper model loaded successfully!")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            self.model = None
    
    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> dict:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes (PCM 16-bit)
            sample_rate: Audio sample rate (default 16kHz)
            
        Returns:
            Dict with 'text', 'language', and 'confidence'
        """
        if not self.model:
            return {
                "text": "",
                "language": "en",
                "confidence": 0.0,
                "error": "Whisper model not loaded"
            }
        
        try:
            # Save audio to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                self._write_wav(tmp_file, audio_data, sample_rate)
            
            # Transcribe
            result = self.model.transcribe(
                tmp_path,
                language="en",  # Can be "hi" for Hindi or None for auto-detect
                fp16=False  # Use FP32 for CPU compatibility
            )
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "en"),
                "confidence": 1.0  # Whisper doesn't provide per-segment confidence
            }
            
        except Exception as e:
            return {
                "text": "",
                "language": "en",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def transcribe_file(self, file_path: str) -> dict:
        """
        Transcribe an audio file to text.
        
        Args:
            file_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            Dict with 'text', 'language', and 'segments'
        """
        if not self.model:
            return {
                "text": "",
                "language": "en",
                "segments": [],
                "error": "Whisper model not loaded"
            }
        
        try:
            result = self.model.transcribe(
                file_path,
                fp16=False
            )
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "en"),
                "segments": result.get("segments", [])
            }
            
        except Exception as e:
            return {
                "text": "",
                "language": "en",
                "segments": [],
                "error": str(e)
            }
    
    def _write_wav(self, file, audio_data: bytes, sample_rate: int):
        """Write audio data to WAV file."""
        # PCM 16-bit mono
        channels = 1
        sample_width = 2  # 16-bit = 2 bytes
        
        with wave.open(file, 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data)


class WebSTTHandler:
    """
    Browser-based Speech-to-Text using Web Speech API.
    This is a fallback when Whisper is not available.
    The actual transcription happens in the browser.
    """
    
    def __init__(self):
        """Initialize the web STT handler."""
        self.is_browser_based = True
    
    def get_client_config(self) -> dict:
        """
        Get configuration for browser-side speech recognition.
        
        Returns:
            Dict with client-side STT settings
        """
        return {
            "engine": "webkitSpeechRecognition",
            "language": "en-US",
            "continuous": True,
            "interimResults": True,
            "maxAlternatives": 1
        }


# Factory function to get the best available STT handler
def get_stt_handler(prefer_whisper: bool = True) -> STTHandler:
    """
    Get the best available STT handler.
    
    Args:
        prefer_whisper: If True, try to use Whisper first
        
    Returns:
        STTHandler instance
    """
    if prefer_whisper and WHISPER_AVAILABLE:
        return STTHandler(model_size="base")
    return WebSTTHandler()


# Test
if __name__ == "__main__":
    print("Testing STT Handler...")
    
    if WHISPER_AVAILABLE:
        handler = STTHandler(model_size="tiny")  # Use tiny for fast testing
        print(f"Whisper available: {handler.model is not None}")
    else:
        print("Whisper not available. Using Web Speech API fallback.")
        handler = WebSTTHandler()
        print(f"Client config: {handler.get_client_config()}")
