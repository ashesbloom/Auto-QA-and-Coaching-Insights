/**
 * Battery Smart Voice Agent - Client-side JavaScript
 * Handles WebSocket connection, speech recognition, and audio playback
 */

// Socket.IO connection
let socket = null;
let sessionId = null;
let isInCall = false;
let isMuted = false;
let callStartTime = null;
let timerInterval = null;

// Speech Recognition
let recognition = null;
let isListening = false;

// Audio playback
const audioPlayer = document.getElementById('audio-player');
let audioQueue = [];
let isPlaying = false;

// DOM Elements
const statusIndicator = document.getElementById('status-indicator');
const statusText = statusIndicator.querySelector('.status-text');
const agentAvatar = document.getElementById('agent-avatar');
const callTimer = document.getElementById('call-timer');
const timerValue = document.getElementById('timer-value');
const transcript = document.getElementById('transcript');
const callBtn = document.getElementById('call-btn');
const endBtn = document.getElementById('end-btn');
const muteBtn = document.getElementById('mute-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeSocket();
    initializeSpeechRecognition();
    setupEventListeners();
});

/**
 * Initialize WebSocket connection
 */
function initializeSocket() {
    // Connect to voice server
    socket = io(window.location.origin, {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('Connected to voice server');
        updateStatus('connected', 'Connected - Ready to call');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from voice server');
        updateStatus('error', 'Disconnected');
        if (isInCall) {
            endCall();
        }
    });

    socket.on('error', (data) => {
        console.error('Socket error:', data);
        showError(data.message || 'Connection error');
    });

    socket.on('call_started', (data) => {
        console.log('Call started:', data);
        sessionId = data.session_id;
        addTranscriptEntry('agent', data.greeting);
    });

    socket.on('agent_response', (data) => {
        console.log('Agent response:', data);
        addTranscriptEntry('agent', data.text);
    });

    socket.on('audio_response', (data) => {
        console.log('Audio response received');
        playAudioResponse(data.audio, data.format);
    });

    socket.on('call_ended', (data) => {
        console.log('Call ended:', data);
        handleCallEnded(data);
    });
}

/**
 * Initialize Web Speech API for speech recognition
 */
function initializeSpeechRecognition() {
    // Check if Web Speech API is available
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.warn('Speech recognition not supported');
        showError('Speech recognition is not supported in this browser. Please use Chrome.');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-IN'; // Indian English

    recognition.onstart = () => {
        console.log('Speech recognition started');
        isListening = true;
    };

    recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        if (finalTranscript) {
            console.log('Final transcript:', finalTranscript);
            sendUserMessage(finalTranscript.trim());
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
            // Restart recognition if no speech detected
            if (isInCall && !isMuted) {
                restartRecognition();
            }
        } else if (event.error === 'not-allowed') {
            showError('Microphone access denied. Please allow microphone access to use voice features.');
        }
    };

    recognition.onend = () => {
        console.log('Speech recognition ended');
        isListening = false;
        // Restart if still in call
        if (isInCall && !isMuted) {
            restartRecognition();
        }
    };
}

/**
 * Restart speech recognition
 */
function restartRecognition() {
    if (recognition && !isListening && isInCall && !isMuted) {
        try {
            recognition.start();
        } catch (e) {
            console.log('Recognition already started');
        }
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    callBtn.addEventListener('click', startCall);
    endBtn.addEventListener('click', endCall);
    muteBtn.addEventListener('click', toggleMute);
}

/**
 * Start a voice call
 */
function startCall() {
    console.log('Starting call...');

    // Request microphone permission
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(() => {
            // Clear previous transcript
            transcript.innerHTML = '';

            // Start call
            socket.emit('start_call', {});

            // Update UI
            isInCall = true;
            callBtn.classList.add('hidden');
            endBtn.classList.remove('hidden');
            muteBtn.disabled = false;

            // Start timer
            callStartTime = new Date();
            callTimer.classList.add('active');
            timerInterval = setInterval(updateTimer, 1000);

            // Update status
            updateStatus('in-call', 'In Call');

            // Start speech recognition
            if (recognition) {
                recognition.start();
            }
        })
        .catch((err) => {
            console.error('Microphone access denied:', err);
            showError('Microphone access is required for voice calls. Please allow access and try again.');
        });
}

/**
 * End the current call
 */
function endCall() {
    console.log('Ending call...');

    // Stop speech recognition
    if (recognition && isListening) {
        recognition.stop();
    }

    // Stop timer
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    // Tell server to end call
    if (sessionId) {
        socket.emit('end_call', { session_id: sessionId });
    }

    // Update UI
    isInCall = false;
    sessionId = null;
    callBtn.classList.remove('hidden');
    endBtn.classList.add('hidden');
    muteBtn.disabled = true;
    muteBtn.classList.remove('muted');
    isMuted = false;

    // Update status
    updateStatus('connected', 'Call Ended - Ready for new call');
}

/**
 * Toggle mute
 */
function toggleMute() {
    isMuted = !isMuted;

    if (isMuted) {
        muteBtn.classList.add('muted');
        muteBtn.querySelector('.btn-text').textContent = 'Unmute';
        if (recognition && isListening) {
            recognition.stop();
        }
    } else {
        muteBtn.classList.remove('muted');
        muteBtn.querySelector('.btn-text').textContent = 'Mute';
        if (recognition && isInCall) {
            recognition.start();
        }
    }
}

/**
 * Send user message to server
 */
function sendUserMessage(text) {
    if (!text || !isInCall) return;

    console.log('Sending message:', text);

    // Add to transcript
    addTranscriptEntry('customer', text);

    // Send to server
    socket.emit('user_message', { text: text });
}

/**
 * Add entry to transcript
 */
function addTranscriptEntry(speaker, text) {
    // Remove placeholder
    const placeholder = transcript.querySelector('.transcript-placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const entry = document.createElement('div');
    entry.className = `transcript-entry ${speaker}`;
    entry.innerHTML = `
        <div class="transcript-speaker">${speaker === 'agent' ? '🤖 Agent' : '👤 You'}</div>
        <div class="transcript-bubble">${text}</div>
    `;

    transcript.appendChild(entry);
    transcript.scrollTop = transcript.scrollHeight;

    // Animate avatar when agent speaks
    if (speaker === 'agent') {
        agentAvatar.classList.add('speaking');
        setTimeout(() => {
            agentAvatar.classList.remove('speaking');
        }, 2000);
    }
}

/**
 * Play audio response
 */
function playAudioResponse(audioBase64, format) {
    try {
        // Convert base64 to blob
        const audioData = atob(audioBase64);
        const arrayBuffer = new ArrayBuffer(audioData.length);
        const uint8Array = new Uint8Array(arrayBuffer);

        for (let i = 0; i < audioData.length; i++) {
            uint8Array[i] = audioData.charCodeAt(i);
        }

        const blob = new Blob([uint8Array], { type: `audio/${format}` });
        const audioUrl = URL.createObjectURL(blob);

        // Play audio
        audioPlayer.src = audioUrl;
        audioPlayer.play().then(() => {
            agentAvatar.classList.add('speaking');
        }).catch(e => console.error('Audio play error:', e));

        audioPlayer.onended = () => {
            agentAvatar.classList.remove('speaking');
            URL.revokeObjectURL(audioUrl);
        };

    } catch (e) {
        console.error('Error playing audio:', e);
    }
}

/**
 * Update call timer
 */
function updateTimer() {
    if (!callStartTime) return;

    const elapsed = Math.floor((new Date() - callStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');

    timerValue.textContent = `${minutes}:${seconds}`;
}

/**
 * Update status indicator
 */
function updateStatus(status, text) {
    statusIndicator.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

/**
 * Handle call ended event
 */
function handleCallEnded(data) {
    // Add summary to transcript
    if (data.duration_seconds) {
        const summary = document.createElement('div');
        summary.className = 'transcript-entry';
        summary.innerHTML = `
            <div style="text-align: center; color: var(--gray); padding: 16px; font-size: 13px;">
                📞 Call ended · Duration: ${formatDuration(data.duration_seconds)}
            </div>
        `;
        transcript.appendChild(summary);
    }

    callTimer.classList.remove('active');
}

/**
 * Format duration in seconds to MM:SS
 */
function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Show error message
 */
function showError(message) {
    // Create toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        padding: 16px 24px;
        background: #1e293b;
        border: 1px solid rgba(239, 68, 68, 0.5);
        border-left: 4px solid #ef4444;
        border-radius: 12px;
        color: white;
        font-size: 14px;
        z-index: 1000;
        animation: fadeIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}
