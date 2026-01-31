"""
Voice Server for Battery Smart Voice Agent
Flask server with WebSocket support for real-time voice communication.
"""

import os
import sys
import json
import asyncio
import base64
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import uuid

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_agent import VoiceAgent, VoiceSessionManager

# Check for TTS availability
try:
    from speech.tts_handler import TTSHandler, EDGE_TTS_AVAILABLE
except ImportError:
    EDGE_TTS_AVAILABLE = False
    TTSHandler = None

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'voice_dashboard'),
            static_folder=os.path.join(BASE_DIR, 'voice_dashboard', 'static'))

app.secret_key = 'battery-smart-voice-agent-2024'

# Initialize SocketIO with CORS
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Voice session manager
session_manager = VoiceSessionManager(api_key=os.getenv('GEMINI_API_KEY'))

# Active socket sessions
socket_sessions = {}

# Transcript storage
transcripts_dir = os.path.join(BASE_DIR, 'voice_transcripts')
os.makedirs(transcripts_dir, exist_ok=True)


# =============================================================================
# REST API ROUTES
# =============================================================================

@app.route('/')
def index():
    """Voice agent home page."""
    return render_template('index.html')


@app.route('/api/voice/status')
def voice_status():
    """Get voice agent status."""
    return jsonify({
        "status": "online",
        "llm_available": bool(os.getenv('GEMINI_API_KEY') or os.getenv('GROQ_API_KEY')),
        "tts_available": EDGE_TTS_AVAILABLE,
        "active_sessions": len(socket_sessions)
    })


@app.route('/api/voice/transcripts')
def list_transcripts():
    """List all saved transcripts."""
    transcripts = []
    for filename in os.listdir(transcripts_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(transcripts_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                transcripts.append({
                    "session_id": data.get("session_id"),
                    "start_time": data.get("start_time"),
                    "duration_seconds": data.get("duration_seconds"),
                    "filename": filename
                })
    return jsonify(transcripts)


@app.route('/api/voice/transcript/<session_id>')
def get_transcript(session_id):
    """Get a specific transcript."""
    file_path = os.path.join(transcripts_dir, f"{session_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Transcript not found"}), 404


# =============================================================================
# WEBSOCKET EVENTS
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection."""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to Battery Smart Voice Agent'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    print(f"Client disconnected: {request.sid}")
    
    # End any active session
    if request.sid in socket_sessions:
        session_id = socket_sessions[request.sid].get('session_id')
        if session_id:
            try:
                session_data = session_manager.end_session(session_id)
                save_transcript(session_data)
            except:
                pass
        del socket_sessions[request.sid]


@socketio.on('start_call')
def handle_start_call(data):
    """Start a new voice call session."""
    print(f"Starting call for {request.sid}")
    
    try:
        # Create new session
        session_id, greeting = session_manager.create_session()
        
        # Store session info
        socket_sessions[request.sid] = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat()
        }
        
        # Send greeting
        emit('call_started', {
            'session_id': session_id,
            'greeting': greeting
        })
        
        # Generate TTS for greeting if available
        if EDGE_TTS_AVAILABLE and TTSHandler:
            asyncio.run(send_tts_audio(greeting))
        
    except Exception as e:
        print(f"Error starting call: {e}")
        emit('error', {'message': str(e)})


@socketio.on('user_message')
def handle_user_message(data):
    """Process user message (from speech-to-text)."""
    message = data.get('text', '')
    if not message:
        return
    
    session_info = socket_sessions.get(request.sid)
    if not session_info:
        emit('error', {'message': 'No active session'})
        return
    
    session_id = session_info.get('session_id')
    
    try:
        # Get agent response
        response = session_manager.process_message(session_id, message)
        
        # Send response
        emit('agent_response', {
            'text': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Generate TTS if available
        if EDGE_TTS_AVAILABLE and TTSHandler:
            asyncio.run(send_tts_audio(response))
        
    except Exception as e:
        print(f"Error processing message: {e}")
        emit('error', {'message': str(e)})


@socketio.on('end_call')
def handle_end_call(data):
    """End the current voice call."""
    session_info = socket_sessions.get(request.sid)
    if not session_info:
        emit('error', {'message': 'No active session'})
        return
    
    session_id = session_info.get('session_id')
    
    try:
        # End session and get data
        session_data = session_manager.end_session(session_id)
        
        # Save transcript
        save_transcript(session_data)
        
        # Clean up socket session
        del socket_sessions[request.sid]
        
        # Send confirmation
        emit('call_ended', {
            'session_id': session_id,
            'duration_seconds': session_data.get('duration_seconds'),
            'transcript': session_data.get('formatted_transcript')
        })
        
    except Exception as e:
        print(f"Error ending call: {e}")
        emit('error', {'message': str(e)})


@socketio.on('audio_data')
def handle_audio_data(data):
    """Handle incoming audio data (for server-side STT)."""
    # This is for future implementation with server-side Whisper
    # Currently using browser-based Web Speech API
    pass


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def send_tts_audio(text: str):
    """Generate and send TTS audio to client."""
    try:
        handler = TTSHandler("indian_female")
        audio_data = await handler.synthesize(text)
        
        if audio_data:
            # Encode as base64 for sending via WebSocket
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            emit('audio_response', {
                'audio': audio_base64,
                'format': 'mp3'
            })
    except Exception as e:
        print(f"TTS Error: {e}")


def save_transcript(session_data: dict):
    """Save transcript to file."""
    session_id = session_data.get('session_id')
    if not session_id:
        return
    
    file_path = os.path.join(transcripts_dir, f"{session_id}.json")
    with open(file_path, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"Saved transcript: {file_path}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Battery Smart Voice Agent Server")
    print("=" * 60)
    llm_key_available = os.getenv('GEMINI_API_KEY') or os.getenv('GROQ_API_KEY')
    print(f"LLM API Key: {'Set' if llm_key_available else 'Not set'}")
    print(f"TTS Available: {EDGE_TTS_AVAILABLE}")
    print("=" * 60)
    
    # Run on port 5001 to avoid conflict with main unified server
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
