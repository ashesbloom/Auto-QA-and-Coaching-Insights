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

    // =========================================================================
    // TRANSFER CALL HANDLER: When AI decides to transfer to human agent
    // =========================================================================
    socket.on('transfer_call', (data) => {
        console.log('='.repeat(60));
        console.log('🔄 TRANSFER_CALL EVENT RECEIVED!');
        console.log('🔄 Transfer data:', JSON.stringify(data, null, 2));
        console.log('='.repeat(60));
        
        try {
            handleCallTransfer(data);
        } catch (error) {
            console.error('❌ ERROR handling transfer_call:', error);
        }
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
 * Handle call transfer to human agent using Jitsi Meet
 */
function handleCallTransfer(data) {
    console.log('=== TRANSFER HANDLER CALLED ===');
    console.log('Handling call transfer:', data);
    
    try {
        // Generate unique room name - avoid dashes and special chars to prevent lobby mode
        const roomName = `bsmart${data.session_id}${Date.now()}`;
        const jitsiUrl = `https://meet.jit.si/${roomName}`;
        console.log('Generated Jitsi URL:', jitsiUrl);
        
        // Update status to show transfer in progress
        updateStatus('transferring', 'Connecting to human agent...');
        
        // Add transfer notice to transcript
        const transcriptEl = document.getElementById('transcript');
        if (transcriptEl) {
            const transferNotice = document.createElement('div');
            transferNotice.className = 'transcript-entry transfer-notice';
            transferNotice.innerHTML = `
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1)); border-radius: 12px; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px;">🔄</div>
                    <div style="color: #60a5fa; font-weight: 600; font-size: 15px;">Connecting to Human Agent</div>
                    <div style="color: var(--gray); font-size: 13px; margin-top: 4px;">
                        ${data.reason === 'customer_request' ? 'As per your request' : 'For better assistance'}
                    </div>
                </div>
            `;
            transcriptEl.appendChild(transferNotice);
            transcriptEl.scrollTop = transcriptEl.scrollHeight;
        }
        
        console.log('About to call showJitsiTransferModal...');
        // Show transfer modal with Jitsi room
        showJitsiTransferModal(data, roomName, jitsiUrl);
        console.log('showJitsiTransferModal completed');
    } catch (error) {
        console.error('❌ ERROR in handleCallTransfer:', error);
    }
}

/**
 * Show transfer modal with Jitsi Meet room
 */
function showJitsiTransferModal(data, roomName, jitsiUrl) {
    console.log('=== showJitsiTransferModal STARTED ===');
    
    // FIRST: Send room link to server for agent notification (before creating iframe)
    console.log('🔍 Socket check - socket exists:', !!socket);
    console.log('🔍 Socket check - socket.connected:', socket ? socket.connected : 'N/A');
    console.log('🔍 Socket check - socket.id:', socket ? socket.id : 'N/A');
    
    try {
        if (socket && socket.connected) {
            const transferData = {
                session_id: data.session_id,
                room_name: roomName,
                room_url: jitsiUrl,
                reason: data.reason
            };
            console.log('📤 Emitting agent_transfer_room with data:', JSON.stringify(transferData));
            
            socket.emit('agent_transfer_room', transferData);
            console.log('✅ agent_transfer_room event emitted successfully');
        } else {
            console.error('❌ Socket not connected! Attempting reconnect...');
            if (socket) {
                socket.connect();
                // Use a small delay and emit
                setTimeout(() => {
                    if (socket.connected) {
                        console.log('🔄 Reconnected, sending agent_transfer_room...');
                        socket.emit('agent_transfer_room', {
                            session_id: data.session_id,
                            room_name: roomName,
                            room_url: jitsiUrl,
                            reason: data.reason
                        });
                    }
                }, 500);
            }
        }
    } catch (emitError) {
        console.error('❌ Error emitting agent_transfer_room:', emitError);
    }
    
    // Log for agent to see
    console.log('='.repeat(60));
    console.log('🔔 AGENT JOIN LINK:', jitsiUrl);
    console.log('='.repeat(60));
    
    // Open Jitsi in a new tab (required for WebRTC on non-HTTPS pages)
    window.customerJitsiWindow = window.open(jitsiUrl + '#config.prejoinPageEnabled=false&config.startWithVideoMuted=true&userInfo.displayName="Customer"', '_blank', 'width=800,height=600');
    
    if (window.customerJitsiWindow) {
        console.log('✅ Customer Jitsi window opened successfully');
        
        // Update status
        updateStatus('in-call', 'Voice call opened in new tab');
        
        // Show notification in transcript
        const transcriptEl = document.getElementById('transcript');
        if (transcriptEl) {
            const callNotice = document.createElement('div');
            callNotice.className = 'transcript-entry transfer-notice';
            callNotice.innerHTML = `
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.1)); border-radius: 12px; margin: 16px 0;">
                    <div style="font-size: 32px; margin-bottom: 8px;">📞</div>
                    <div style="color: #10b981; font-weight: 600; font-size: 15px;">Voice Call Opened in New Tab</div>
                    <div style="color: var(--gray); font-size: 13px; margin-top: 4px;">
                        Allow microphone access in the new window to speak with the agent.
                    </div>
                </div>
            `;
            transcriptEl.appendChild(callNotice);
            transcriptEl.scrollTop = transcriptEl.scrollHeight;
        }
        
        // Check periodically if the window is closed
        const checkWindow = setInterval(() => {
            if (window.customerJitsiWindow && window.customerJitsiWindow.closed) {
                console.log('📴 Customer Jitsi window was closed');
                clearInterval(checkWindow);
                updateStatus('connected', 'Call ended');
            }
        }, 2000);
    } else {
        console.error('❌ Failed to open Jitsi window - popup blocked?');
        // Show fallback modal with link
        showJitsiFallbackModal(jitsiUrl);
    }
}

/**
 * Show fallback modal when popup is blocked
 */
function showJitsiFallbackModal(jitsiUrl) {
    // Remove existing modal if any
    const existingModal = document.getElementById('transfer-modal');
    if (existingModal) existingModal.remove();
    
    const modal = document.createElement('div');
    modal.id = 'transfer-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.95);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;
    
    modal.innerHTML = `
        <div style="text-align: center; padding: 40px; background: rgba(30, 41, 59, 0.9); border-radius: 16px; max-width: 500px;">
            <div style="font-size: 64px; margin-bottom: 20px;">⚠️</div>
            <h3 style="color: #fbbf24; margin-bottom: 12px;">Popup Blocked</h3>
            <p style="color: #94a3b8; margin-bottom: 20px;">Please allow popups or click below to join the call:</p>
            <a href="${jitsiUrl}#config.prejoinPageEnabled=false&config.startWithVideoMuted=true&userInfo.displayName=Customer" 
               target="_blank" 
               style="display: inline-block; padding: 16px 32px; background: linear-gradient(135deg, #10b981, #059669); color: white; text-decoration: none; border-radius: 12px; font-weight: bold; font-size: 16px;">
               Join Voice Call
            </a>
            <button onclick="document.getElementById('transfer-modal').remove()" 
                    style="display: block; margin: 20px auto 0; padding: 10px 20px; background: transparent; border: 1px solid #64748b; color: #64748b; border-radius: 8px; cursor: pointer;">
                Close
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
    console.log('✅ Fallback modal displayed');
}
 * Copy room link to clipboard
 */
function copyRoomLink(url) {
    navigator.clipboard.writeText(url).then(() => {
        // Show success feedback
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        btn.style.background = '#10b981';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        // Fallback: select the text
        const linkEl = document.getElementById('room-link');
        if (linkEl) {
            const range = document.createRange();
            range.selectNode(linkEl);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
        }
    });
}

/**
 * End the transfer call
 */
function endTransferCall() {
    // Close Jitsi window if open
    if (window.customerJitsiWindow && !window.customerJitsiWindow.closed) {
        try {
            window.customerJitsiWindow.close();
        } catch (e) {}
    }
    window.customerJitsiWindow = null;
    
    // Remove fallback modal if present
    const modal = document.getElementById('transfer-modal');
    if (modal) modal.remove();
    
    updateStatus('connected', 'Call ended');
    
    const endNotice = document.createElement('div');
    endNotice.className = 'transcript-entry';
    endNotice.innerHTML = `
        <div style="text-align: center; padding: 16px; background: rgba(100, 116, 139, 0.1); border-radius: 12px; margin: 16px 0;">
            <span style="font-size: 24px;">📞</span>
            <div style="color: var(--gray); font-weight: 600; margin-top: 8px;">Call with human agent ended</div>
        </div>
    `;
    transcript.appendChild(endNotice);
    transcript.scrollTop = transcript.scrollHeight;
}

/**
 * Cancel the transfer and return to AI
 */
function cancelTransfer() {
    const modal = document.getElementById('transfer-modal');
    if (modal) modal.remove();
    
    updateStatus('speaking', 'Connected to AI Agent');
    addTranscriptEntry('system', 'Transfer cancelled. Continuing with AI agent.');
}

/**
 * Simulate transfer completion (for demo)
 */
function simulateTransferComplete() {
    const modal = document.getElementById('transfer-modal');
    if (modal) modal.remove();
    
    updateStatus('speaking', 'Connected to Human Agent');
    
    const connectedNotice = document.createElement('div');
    connectedNotice.className = 'transcript-entry';
    connectedNotice.innerHTML = `
        <div style="text-align: center; padding: 16px; background: rgba(16, 185, 129, 0.1); border-radius: 12px; margin: 16px 0; border: 1px solid rgba(16, 185, 129, 0.3);">
            <span style="font-size: 24px;">✅</span>
            <div style="color: #10b981; font-weight: 600; margin-top: 8px;">Connected to Human Agent</div>
            <div style="color: var(--gray); font-size: 12px; margin-top: 4px;">You are now speaking with a customer care executive</div>
        </div>
    `;
    transcript.appendChild(connectedNotice);
    transcript.scrollTop = transcript.scrollHeight;
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
