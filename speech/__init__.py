"""
Speech module for Battery Smart Voice Agent.
Provides speech-to-text and text-to-speech handlers.
"""

from .stt_handler import STTHandler, WebSTTHandler, get_stt_handler, WHISPER_AVAILABLE
from .tts_handler import TTSHandler, TTSHandlerSync, EDGE_TTS_AVAILABLE

__all__ = [
    'STTHandler',
    'WebSTTHandler', 
    'get_stt_handler',
    'TTSHandler',
    'TTSHandlerSync',
    'WHISPER_AVAILABLE',
    'EDGE_TTS_AVAILABLE'
]
