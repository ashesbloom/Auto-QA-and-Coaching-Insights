"""
Text-to-Speech Handler for Battery Smart Voice Agent
Uses AWS Polly (preferred) or Edge TTS (fallback) for natural-sounding speech synthesis.

Priority:
1. AWS Polly Neural (Kajal voice) - Professional quality, low latency
2. Edge TTS (Neerja voice) - Free fallback for local development
"""

import asyncio
import os
import tempfile
from typing import Optional, AsyncGenerator, Generator
import io

# Try to import AWS Polly
try:
    from aws_services.polly_tts import PollyTTS, PollyTTSHandler
    from aws_services.config import is_aws_enabled
    POLLY_AVAILABLE = True
except ImportError:
    POLLY_AVAILABLE = False
    is_aws_enabled = lambda: False

# Try to import edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("Warning: edge-tts not installed. Run: pip install edge-tts")


class TTSHandler:
    """
    Text-to-Speech handler using AWS Polly (preferred) or Microsoft Edge TTS (fallback).
    
    Priority:
    1. AWS Polly Neural (if USE_AWS=true and credentials available)
    2. Edge TTS (free, high-quality fallback)
    """
    
    # Professional female voices for customer support
    VOICES = {
        "indian_female": "en-IN-NeerjaNeural",      # Indian English female
        "indian_male": "en-IN-PrabhatNeural",        # Indian English male
        "american_female": "en-US-JennyNeural",      # American English female
        "british_female": "en-GB-SoniaNeural",       # British English female
        "hindi_female": "hi-IN-SwaraNeural",         # Hindi female
        "hindi_male": "hi-IN-MadhurNeural"           # Hindi male
    }
    
    # Polly voice mapping
    POLLY_VOICES = {
        "indian_female": "Kajal",   # Neural, premium quality
        "indian_male": "Aditi",     # Standard (no male neural in en-IN)
    }
    
    def __init__(self, voice: str = "indian_female", use_polly: bool = None):
        """
        Initialize the TTS handler.
        
        Args:
            voice: Voice preset name from VOICES dict
            use_polly: Force Polly usage. If None, auto-detects based on USE_AWS env var.
        """
        self.voice_preset = voice
        self.voice = self.VOICES.get(voice, self.VOICES["indian_female"])
        self.rate = "+0%"  # Speech rate adjustment
        self.pitch = "+0Hz"  # Pitch adjustment
        
        self.polly_handler = None
        self.use_polly = False
        
        # Determine which TTS to use
        if use_polly is None:
            use_polly = is_aws_enabled() if POLLY_AVAILABLE else False
        
        if use_polly and POLLY_AVAILABLE:
            self._initialize_polly(voice)
    
    def _initialize_polly(self, voice: str):
        """Initialize AWS Polly TTS."""
        try:
            polly_voice = self.POLLY_VOICES.get(voice, "Kajal")
            self.polly_handler = PollyTTSHandler(voice=polly_voice.lower())
            
            if self.polly_handler.is_available():
                self.use_polly = True
                print(f"TTS: Using AWS Polly ({polly_voice})")
            else:
                print("TTS: Polly not available, using Edge TTS")
                self.polly_handler = None
        except Exception as e:
            print(f"Polly initialization failed: {e}")
            self.polly_handler = None
    
    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio data as bytes (MP3 format)
        """
        # Try Polly first
        if self.polly_handler and self.use_polly:
            try:
                return await self.polly_handler.synthesize(text)
            except Exception as e:
                print(f"Polly TTS error: {e}, falling back to Edge TTS")
        
        # Edge TTS fallback
        if not EDGE_TTS_AVAILABLE:
            return b""
        
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return b""
    
    def synthesize_sync(self, text: str) -> bytes:
        """
        Synchronous wrapper for synthesize.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio data as bytes
        """
        # Polly has a sync method
        if self.polly_handler and self.use_polly:
            try:
                return self.polly_handler.synthesize_sync(text)
            except Exception as e:
                print(f"Polly sync error: {e}")
        
        # Edge TTS via asyncio
        return asyncio.run(self.synthesize(text))
    
    def synthesize_streaming(self, text: str) -> Generator[bytes, None, None]:
        """
        Stream audio chunks for real-time playback.
        Synchronous generator for easier integration.
        
        Args:
            text: Text to speak
            
        Yields:
            Audio chunks as bytes
        """
        # Polly streaming
        if self.polly_handler and self.use_polly:
            try:
                yield from self.polly_handler.synthesize_streaming(text)
                return
            except Exception as e:
                print(f"Polly streaming error: {e}")
        
        # Edge TTS fallback (non-streaming, returns full audio)
        audio = self.synthesize_sync(text)
        if audio:
            yield audio
    
    async def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """
        Convert text to speech and save to file.
        
        Args:
            text: Text to speak
            output_path: Path to save audio file
            
        Returns:
            True if successful
        """
        if not EDGE_TTS_AVAILABLE:
            return False
        
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            await communicate.save(output_path)
            return True
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return False
    
    async def stream_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream audio chunks for real-time playback.
        
        Args:
            text: Text to speak
            
        Yields:
            Audio chunks as bytes
        """
        if not EDGE_TTS_AVAILABLE:
            return
        
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
                    
        except Exception as e:
            print(f"TTS Stream Error: {e}")
    
    def synthesize_sync(self, text: str) -> bytes:
        """
        Synchronous wrapper for synthesize.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio data as bytes
        """
        return asyncio.run(self.synthesize(text))
    
    def set_voice(self, voice_name: str):
        """
        Change the voice.
        
        Args:
            voice_name: Voice preset name or full voice ID
        """
        if voice_name in self.VOICES:
            self.voice = self.VOICES[voice_name]
        else:
            self.voice = voice_name
    
    def set_rate(self, rate: int):
        """
        Set speech rate.
        
        Args:
            rate: Rate adjustment (-100 to +100 percent)
        """
        sign = "+" if rate >= 0 else ""
        self.rate = f"{sign}{rate}%"
    
    def set_pitch(self, pitch: int):
        """
        Set speech pitch.
        
        Args:
            pitch: Pitch adjustment in Hz (-50 to +50)
        """
        sign = "+" if pitch >= 0 else ""
        self.pitch = f"{sign}{pitch}Hz"
    
    @staticmethod
    async def list_voices() -> list:
        """
        List all available voices.
        
        Returns:
            List of voice dictionaries
        """
        if not EDGE_TTS_AVAILABLE:
            return []
        
        try:
            voices = await edge_tts.list_voices()
            return voices
        except Exception as e:
            print(f"Error listing voices: {e}")
            return []


# Synchronous wrapper class for easier use
class TTSHandlerSync:
    """Synchronous wrapper for TTSHandler."""
    
    def __init__(self, voice: str = "indian_female"):
        self.handler = TTSHandler(voice)
    
    def synthesize(self, text: str) -> bytes:
        """Convert text to speech synchronously."""
        return asyncio.run(self.handler.synthesize(text))
    
    def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """Save speech to file synchronously."""
        return asyncio.run(self.handler.synthesize_to_file(text, output_path))
    
    def set_voice(self, voice_name: str):
        """Change the voice."""
        self.handler.set_voice(voice_name)


# Test
if __name__ == "__main__":
    print("Testing TTS Handler...")
    
    if EDGE_TTS_AVAILABLE:
        async def test():
            handler = TTSHandler("indian_female")
            
            # Test synthesis
            text = "Thank you for calling Battery Smart! My name is Priya. How may I help you today?"
            print(f"Synthesizing: {text}")
            
            audio = await handler.synthesize(text)
            print(f"Generated {len(audio)} bytes of audio")
            
            # Save to file
            output_file = "test_speech.mp3"
            success = await handler.synthesize_to_file(text, output_file)
            if success:
                print(f"Saved to {output_file}")
        
        asyncio.run(test())
    else:
        print("Edge TTS not available. Install with: pip install edge-tts")
