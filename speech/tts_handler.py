"""
Text-to-Speech Handler for Battery Smart Voice Agent
Uses Edge TTS for natural-sounding speech synthesis.
"""

import asyncio
import os
import tempfile
from typing import Optional, AsyncGenerator
import io

# Try to import edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("Warning: edge-tts not installed. Run: pip install edge-tts")


class TTSHandler:
    """
    Text-to-Speech handler using Microsoft Edge TTS.
    Free, high-quality, neural voices.
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
    
    def __init__(self, voice: str = "indian_female"):
        """
        Initialize the TTS handler.
        
        Args:
            voice: Voice preset name from VOICES dict
        """
        self.voice = self.VOICES.get(voice, self.VOICES["indian_female"])
        self.rate = "+0%"  # Speech rate adjustment
        self.pitch = "+0Hz"  # Pitch adjustment
    
    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio data as bytes (MP3 format)
        """
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
