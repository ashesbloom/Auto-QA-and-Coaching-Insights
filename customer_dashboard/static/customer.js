/**
 * Battery Smart Customer Dashboard - JavaScript
 * Handles all client-side functionality
 */

// =============================================================================
// GLOBAL STATE
// =============================================================================

let currentUser = null;
let currentCallId = null;
let callTimer = null;
let callSeconds = 0;
let selectedRating = 0;
let selectedTags = [];
let allCallLogs = [];

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    setupEventListeners();
    setMinDate();
});

function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.dataset.tab;
            switchTab(tab);
        });
    });

    // Rating stars
    document.querySelectorAll('.star').forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.dataset.rating);
            updateStars();
        });
    });

    // Feedback tags
    document.querySelectorAll('.tag').forEach(tag => {
        tag.addEventListener('click', () => {
            tag.classList.toggle('active');
            const tagValue = tag.dataset.tag;
            if (selectedTags.includes(tagValue)) {
                selectedTags = selectedTags.filter(t => t !== tagValue);
            } else {
                selectedTags.push(tagValue);
            }
        });
    });
}

function setMinDate() {
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('call-date');
    if (dateInput) {
        dateInput.min = today;
    }
}

// =============================================================================
// AUTHENTICATION
// =============================================================================

async function checkAuthStatus() {
    // Auth is already handled by the server-side login page
    // Just load user data and initialize dashboard
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            currentUser = await response.json();
            initializeDashboard();
        } else {
            // Not authenticated, redirect to login
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login';
    }
}

function initializeDashboard() {
    // Update user info in header
    if (currentUser) {
        document.getElementById('user-greeting').textContent = `Hello, ${currentUser.name}`;
        const initials = currentUser.name.split(' ').map(n => n[0]).join('').toUpperCase();
        document.getElementById('user-initials').textContent = initials;
    }
    loadDashboardData();
}

function showLogin() {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('signup-form').classList.add('hidden');
}

function showSignup() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('signup-form').classList.remove('hidden');
}

async function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            showDashboard();
            loadDashboardData();
            showToast('Welcome back!', 'success');
        } else {
            showToast(data.error || 'Login failed', 'error');
        }
    } catch (error) {
        showToast('Login failed. Please try again.', 'error');
    }
}

async function handleSignup(event) {
    event.preventDefault();

    const name = document.getElementById('signup-name').value;
    const email = document.getElementById('signup-email').value;
    const phone = document.getElementById('signup-phone').value;
    const password = document.getElementById('signup-password').value;

    try {
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, phone, password })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            showDashboard();
            loadDashboardData();
            showToast('Account created successfully!', 'success');
        } else {
            showToast(data.error || 'Signup failed', 'error');
        }
    } catch (error) {
        showToast('Signup failed. Please try again.', 'error');
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        showToast('Logout failed', 'error');
    }
}

// =============================================================================
// NAVIGATION
// =============================================================================

function switchTab(tab) {
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.tab === tab) {
            item.classList.add('active');
        }
    });

    // Update tab sections
    document.querySelectorAll('.tab-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`tab-${tab}`).classList.add('active');

    // Update page title
    const titles = {
        home: 'Welcome Back!',
        chat: 'Chat Support',
        schedule: 'Schedule a Call',
        logs: 'Call History',
        tickets: 'My Tickets',
        notifications: 'Notifications',
        profile: 'My Profile'
    };
    document.getElementById('page-title').textContent = titles[tab] || 'Dashboard';

    // Load tab-specific data
    if (tab === 'logs') loadCallLogs();
    if (tab === 'tickets') loadTickets();
    if (tab === 'notifications') loadNotifications();
    if (tab === 'profile') loadProfile();
    if (tab === 'schedule') loadScheduledCalls();
}

// =============================================================================
// DASHBOARD DATA
// =============================================================================

async function loadDashboardData() {
    loadNotificationCount();
    loadRecentActivity();
    loadProfile();
}

async function loadNotificationCount() {
    try {
        const response = await fetch('/api/notifications/unread-count');
        const data = await response.json();

        const badge = document.getElementById('notif-badge');
        const dot = document.getElementById('notif-dot');

        if (data.count > 0) {
            badge.textContent = data.count;
            badge.classList.remove('hidden');
            dot.classList.add('active');
        } else {
            badge.classList.add('hidden');
            dot.classList.remove('active');
        }
    } catch (error) {
        console.error('Error loading notification count:', error);
    }
}

async function loadRecentActivity() {
    try {
        const response = await fetch('/api/call-logs');
        const logs = await response.json();

        const container = document.getElementById('recent-activity-list');

        if (logs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <h4>No recent activity</h4>
                    <p>Start a chat or schedule a call to get support</p>
                </div>
            `;
            return;
        }

        container.innerHTML = logs.slice(0, 3).map(log => `
            <div class="activity-item">
                <div class="activity-icon">${log.type === 'call' ? '📞' : '💬'}</div>
                <div class="activity-info">
                    <h4>${log.subject}</h4>
                    <p>${log.status}</p>
                </div>
                <span class="activity-time">${formatDate(log.timestamp)}</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// =============================================================================
// CHAT
// =============================================================================

function handleChatKeypress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    // Add user message
    addChatMessage(message, 'user');
    input.value = '';

    // Show typing indicator
    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        // Remove typing indicator and add bot response
        removeTypingIndicator();
        addChatMessage(data.response, 'bot', data.timestamp);
    } catch (error) {
        removeTypingIndicator();
        addChatMessage('Sorry, I encountered an error. Please try again.', 'bot');
    }
}

function sendQuickReply(message) {
    document.getElementById('chat-input').value = message;
    sendMessage();
}

function addChatMessage(content, type, timestamp = null) {
    const container = document.getElementById('chat-messages');
    const time = timestamp || new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `
        <div class="message-content">${content}</div>
        <span class="message-time">${time}</span>
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typing-indicator';
    typingDiv.className = 'message bot';
    typingDiv.innerHTML = `
        <div class="message-content">
            <span class="typing-dots">Typing...</span>
        </div>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

// =============================================================================
// CALL SCHEDULING
// =============================================================================

async function handleScheduleCall(event) {
    event.preventDefault();

    const date = document.getElementById('call-date').value;
    const time = document.getElementById('call-time').value;
    const phone = document.getElementById('call-phone').value;
    const issue = document.getElementById('call-issue').value;

    try {
        const response = await fetch('/api/schedule-call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, time, phone, issue })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Call scheduled successfully!', 'success');
            document.getElementById('schedule-form').reset();
            loadScheduledCalls();
            loadNotificationCount();
        } else {
            showToast('Failed to schedule call', 'error');
        }
    } catch (error) {
        showToast('Failed to schedule call', 'error');
    }
}

async function loadScheduledCalls() {
    try {
        const response = await fetch('/api/schedule-call');
        const calls = await response.json();

        const container = document.getElementById('scheduled-calls-list');

        if (calls.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📅</div>
                    <h4>No scheduled calls</h4>
                    <p>Schedule your first call above</p>
                </div>
            `;
            return;
        }

        container.innerHTML = calls.map(call => `
            <div class="scheduled-item">
                <div class="scheduled-info">
                    <h4>${formatDate(call.date)} at ${call.time}</h4>
                    <p>${call.issue || 'General inquiry'}</p>
                </div>
                ${call.status === 'scheduled' ?
                `<button class="start-call-btn" onclick="startSimulatedCall('${call.id}')">Start Call</button>` :
                `<span class="scheduled-status ${call.status}">${call.status}</span>`
            }
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading scheduled calls:', error);
    }
}

function startSimulatedCall(callId) {
    currentCallId = callId;
    callSeconds = 0;

    // Show call modal
    document.getElementById('call-modal').classList.remove('hidden');
    document.getElementById('call-status').textContent = 'Connecting...';
    document.getElementById('call-transcript-live').innerHTML = '';

    // Simulate connection
    setTimeout(() => {
        document.getElementById('call-status').textContent = 'Connected';
        startCallTimer();
        simulateConversation();
    }, 2000);
}

function startCallTimer() {
    callTimer = setInterval(() => {
        callSeconds++;
        const mins = Math.floor(callSeconds / 60).toString().padStart(2, '0');
        const secs = (callSeconds % 60).toString().padStart(2, '0');
        document.getElementById('call-timer').textContent = `${mins}:${secs}`;
    }, 1000);
}

function simulateConversation() {
    const transcript = document.getElementById('call-transcript-live');
    const lines = [
        { speaker: 'Agent', text: 'Thank you for calling Battery Smart. I\'m your AI assistant. How may I help you today?', delay: 1000 },
        { speaker: 'You', text: 'Hi, I scheduled this call about a battery issue.', delay: 3000 },
        { speaker: 'Agent', text: 'I\'d be happy to help! Can you please describe the issue you\'re facing?', delay: 5000 },
        { speaker: 'You', text: 'My battery wouldn\'t unlock at the station yesterday.', delay: 8000 },
        { speaker: 'Agent', text: 'I apologize for the inconvenience. Let me check your account... I can see there was a temporary issue. It\'s been resolved now.', delay: 11000 },
        { speaker: 'Agent', text: 'As a goodwill gesture, I\'ve added ₹50 credit to your wallet. Is there anything else I can help with?', delay: 14000 }
    ];

    lines.forEach(line => {
        setTimeout(() => {
            transcript.innerHTML += `<strong>${line.speaker}:</strong> ${line.text}<br><br>`;
            transcript.scrollTop = transcript.scrollHeight;
        }, line.delay);
    });
}

async function endCall() {
    clearInterval(callTimer);

    document.getElementById('call-status').textContent = 'Call ended';

    // Simulate call completion
    try {
        const response = await fetch(`/api/simulate-call/${currentCallId}`, {
            method: 'POST'
        });
        const data = await response.json();

        // Close modal after a moment
        setTimeout(() => {
            document.getElementById('call-modal').classList.add('hidden');
            showFeedbackModal(data.call_id);
            loadCallLogs();
            loadScheduledCalls();
        }, 1000);
    } catch (error) {
        document.getElementById('call-modal').classList.add('hidden');
        showToast('Call ended', 'success');
    }
}

// =============================================================================
// CALL LOGS
// =============================================================================

async function loadCallLogs() {
    try {
        const response = await fetch('/api/call-logs');
        allCallLogs = await response.json();

        renderCallLogs(allCallLogs);
    } catch (error) {
        console.error('Error loading call logs:', error);
    }
}

function filterLogs() {
    const filter = document.getElementById('log-filter').value;

    let filtered = allCallLogs;
    if (filter !== 'all') {
        filtered = allCallLogs.filter(log => log.type === filter);
    }

    renderCallLogs(filtered);
}

function renderCallLogs(logs) {
    const container = document.getElementById('call-logs-list');

    if (logs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <h4>No call history</h4>
                <p>Your call and chat history will appear here</p>
            </div>
        `;
        return;
    }

    container.innerHTML = logs.map(log => `
        <div class="log-item" onclick="showTranscript('${log.id}')">
            <div class="log-icon ${log.type}">${log.type === 'call' ? '📞' : '💬'}</div>
            <div class="log-info">
                <h4>${log.subject}</h4>
                <p>${log.status} • ${formatDuration(log.duration)}</p>
            </div>
            <div class="log-meta">
                <div class="date">${formatDate(log.timestamp)}</div>
                ${log.satisfaction_score ?
            `<div class="log-rating">${'⭐'.repeat(log.satisfaction_score)}</div>` : ''}
            </div>
            <div class="log-actions">
                <button class="log-action-btn" onclick="event.stopPropagation(); showTranscript('${log.id}')">📝 Transcript</button>
                ${log.needs_feedback ?
            `<button class="log-action-btn feedback" onclick="event.stopPropagation(); showFeedbackModal('${log.id}')">⭐ Feedback</button>` : ''}
            </div>
        </div>
    `).join('');
}

function showTranscript(callId) {
    const log = allCallLogs.find(l => l.id === callId);
    if (!log) return;

    document.getElementById('transcript-content').textContent = log.transcript || 'No transcript available';
    document.getElementById('transcript-modal').classList.remove('hidden');
}

function closeTranscriptModal() {
    document.getElementById('transcript-modal').classList.add('hidden');
}

function downloadTranscript() {
    const content = document.getElementById('transcript-content').textContent;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'transcript.txt';
    a.click();
    URL.revokeObjectURL(url);
}

// =============================================================================
// FEEDBACK
// =============================================================================

function showFeedbackModal(callId) {
    currentCallId = callId;
    selectedRating = 0;
    selectedTags = [];

    // Reset UI
    updateStars();
    document.querySelectorAll('.tag').forEach(t => t.classList.remove('active'));
    document.getElementById('feedback-comment').value = '';

    document.getElementById('feedback-modal').classList.remove('hidden');
}

function closeFeedbackModal() {
    document.getElementById('feedback-modal').classList.add('hidden');
}

function updateStars() {
    document.querySelectorAll('.star').forEach(star => {
        const rating = parseInt(star.dataset.rating);
        if (rating <= selectedRating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

async function submitFeedback() {
    if (selectedRating === 0) {
        showToast('Please select a rating', 'error');
        return;
    }

    const comment = document.getElementById('feedback-comment').value;

    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_id: currentCallId,
                rating: selectedRating,
                tags: selectedTags,
                comment
            })
        });

        const data = await response.json();

        if (data.success) {
            closeFeedbackModal();
            showToast('Thank you for your feedback!', 'success');
            loadCallLogs();
        }
    } catch (error) {
        showToast('Failed to submit feedback', 'error');
    }
}

// =============================================================================
// TICKETS
// =============================================================================

async function loadTickets() {
    try {
        const response = await fetch('/api/tickets');
        const tickets = await response.json();

        const container = document.getElementById('tickets-list');

        if (tickets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🎫</div>
                    <h4>No tickets</h4>
                    <p>Create a ticket if you need ongoing support</p>
                </div>
            `;
            return;
        }

        container.innerHTML = tickets.map(ticket => `
            <div class="ticket-item">
                <div class="ticket-priority ${ticket.priority}"></div>
                <div class="ticket-info">
                    <h4>${ticket.subject}</h4>
                    <p>${ticket.category} • Created ${formatDate(ticket.created_at)}</p>
                </div>
                <span class="ticket-status ${ticket.status}">${formatStatus(ticket.status)}</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading tickets:', error);
    }
}

function showCreateTicketModal() {
    document.getElementById('ticket-modal').classList.remove('hidden');
}

function closeTicketModal() {
    document.getElementById('ticket-modal').classList.add('hidden');
}

async function handleCreateTicket(event) {
    event.preventDefault();

    const subject = document.getElementById('ticket-subject').value;
    const category = document.getElementById('ticket-category').value;
    const priority = document.getElementById('ticket-priority').value;
    const description = document.getElementById('ticket-description').value;

    try {
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject, category, priority, description })
        });

        const data = await response.json();

        if (data.success) {
            closeTicketModal();
            document.getElementById('create-ticket-form').reset();
            showToast('Ticket created successfully!', 'success');
            loadTickets();
        }
    } catch (error) {
        showToast('Failed to create ticket', 'error');
    }
}

// =============================================================================
// NOTIFICATIONS
// =============================================================================

async function loadNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const notifications = await response.json();

        const container = document.getElementById('notifications-list');

        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔔</div>
                    <h4>No notifications</h4>
                    <p>You're all caught up!</p>
                </div>
            `;
            return;
        }

        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            danger: '🚨'
        };

        container.innerHTML = notifications.map(notif => `
            <div class="notification-item ${notif.read ? '' : 'unread'}">
                <div class="notification-icon ${notif.type}">${icons[notif.type] || 'ℹ️'}</div>
                <div class="notification-content">
                    <p>${notif.message}</p>
                    <span>${formatDate(notif.time)}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

async function markAllRead() {
    try {
        await fetch('/api/notifications/mark-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: ['all'] })
        });

        loadNotifications();
        loadNotificationCount();
        showToast('All notifications marked as read', 'success');
    } catch (error) {
        showToast('Failed to mark notifications', 'error');
    }
}

// =============================================================================
// PROFILE
// =============================================================================

async function loadProfile() {
    try {
        const response = await fetch('/api/profile');
        const profile = await response.json();

        // Update header
        document.getElementById('profile-name').textContent = profile.name;
        document.getElementById('profile-email').textContent = profile.email;

        const initials = profile.name.split(' ').map(n => n[0]).join('').toUpperCase();
        document.getElementById('profile-avatar').textContent = initials;

        // Update form
        document.getElementById('profile-name-input').value = profile.name;
        document.getElementById('profile-phone-input').value = profile.phone || '';
        document.getElementById('profile-city-input').value = profile.city || '';

        // Update stats
        document.getElementById('stat-plan').textContent = profile.plan || 'Basic';
        document.getElementById('stat-since').textContent = formatDate(profile.created_at);
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function handleProfileUpdate(event) {
    event.preventDefault();

    const name = document.getElementById('profile-name-input').value;
    const phone = document.getElementById('profile-phone-input').value;
    const city = document.getElementById('profile-city-input').value;

    try {
        const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, phone, city })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            showToast('Profile updated successfully!', 'success');

            // Update header
            document.getElementById('user-greeting').textContent = `Hello, ${name}`;
            const initials = name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('user-initials').textContent = initials;

            loadProfile();
        }
    } catch (error) {
        showToast('Failed to update profile', 'error');
    }
}

// =============================================================================
// UTILITIES
// =============================================================================

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatStatus(status) {
    const statuses = {
        open: 'Open',
        in_progress: 'In Progress',
        resolved: 'Resolved',
        closed: 'Closed'
    };
    return statuses[status] || status;
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    toast.className = `toast ${type}`;
    toastMessage.textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// =============================================================================
// VOICE CALL FUNCTIONALITY
// =============================================================================

let voiceSocket = null;
let voiceCallActive = false;
let voiceCallStartTime = null;
let voiceTimerInterval = null;
let voiceRecognition = null;
let voiceIsMuted = false;
let voiceUserName = '';
let voiceUserPhone = '';

/**
 * Start a voice call with the AI agent
 */
function startVoiceCall() {
    const nameInput = document.getElementById('voice-name');
    const phoneInput = document.getElementById('voice-phone');

    // Validate inputs
    if (!nameInput.value.trim()) {
        showToast('Please enter your name', 'error');
        nameInput.focus();
        return;
    }

    if (!phoneInput.value.trim() || phoneInput.value.length < 10) {
        showToast('Please enter a valid 10-digit mobile number', 'error');
        phoneInput.focus();
        return;
    }

    voiceUserName = nameInput.value.trim();
    voiceUserPhone = phoneInput.value.trim();

    // Request microphone permission
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(() => {
            initVoiceCall();
        })
        .catch((err) => {
            console.error('Microphone access denied:', err);
            showToast('Microphone access is required for voice calls', 'error');
        });
}

/**
 * Initialize the voice call connection
 */
function initVoiceCall() {
    // Connect to voice server on same origin (integrated into main server)
    // Prefer polling first then upgrade to websocket for better compatibility
    voiceSocket = io({
        transports: ['polling', 'websocket'],
        upgrade: true,
        rememberUpgrade: true
    });

    voiceSocket.on('connect', () => {
        console.log('Connected to voice server');
        voiceSocket.emit('start_call', {
            name: voiceUserName,
            phone: voiceUserPhone
        });
    });

    voiceSocket.on('connected', (data) => {
        console.log('Voice server connected:', data.message);
    });

    voiceSocket.on('call_started', (data) => {
        console.log('Call started:', data.session_id);
        voiceCallActive = true;

        // Update UI
        document.getElementById('voice-call-form').classList.add('hidden');
        document.getElementById('voice-call-active').classList.remove('hidden');
        document.getElementById('voice-transcript').innerHTML = '';

        // Add greeting to transcript
        addVoiceTranscript('agent', data.greeting);

        // Start timer
        voiceCallStartTime = new Date();
        voiceTimerInterval = setInterval(updateVoiceTimer, 1000);

        // Initialize speech recognition
        initSpeechRecognition();

        showToast('Call connected!', 'success');
    });

    voiceSocket.on('agent_response', (data) => {
        addVoiceTranscript('agent', data.text);

        // Show speaking animation
        const avatar = document.getElementById('voice-avatar');
        avatar.classList.add('speaking');
        setTimeout(() => avatar.classList.remove('speaking'), 2000);
    });

    voiceSocket.on('audio_response', (data) => {
        playVoiceAudio(data.audio);
    });

    voiceSocket.on('transfer_call', (data) => {
        console.log('Transferring to live agent:', data);
        showToast(data.message || 'Connecting to live agent...', 'info');
        
        // Store session info for WebRTC
        window.transferSessionId = data.session_id;
        window.transferReason = data.reason;
        
        // Stop AI Speech Recognition - we'll use a new one for the human call
        if (voiceRecognition) {
            try { voiceRecognition.stop(); } catch(e){}
            voiceRecognition = null;
        }

        // Update Voice UI to show "Live Agent" state
        const avatar = document.getElementById('voice-avatar');
        if (avatar) {
            avatar.innerHTML = '<span>👤</span>';
            avatar.style.background = 'linear-gradient(135deg, #3b82f6, #2563eb)';
        }
        const agentName = document.querySelector('.agent-details h4');
        if (agentName) agentName.textContent = "Live Support Agent";

        const agentStatus = document.querySelector('.agent-details .agent-status');
        if (agentStatus) agentStatus.textContent = "Finding available agent...";
        
        // Show transcript container for the human call
        showTransferTranscript();
        
        // Notify server to find an agent - include a simple room identifier
        const roomName = `webrtc_${data.session_id}_${Date.now()}`;
        console.log('📤 Requesting agent transfer...');
        voiceSocket.emit('agent_transfer_room', {
            room_url: roomName,  // Not a real URL, just an identifier
            room_name: roomName,
            session_id: data.session_id,
            reason: data.reason
        });
    });
    
    // =========================================================================
    // WEBRTC HANDLERS FOR SEAMLESS VOICE CONNECTION
    // =========================================================================
    
    // When agent is ready, start WebRTC connection
    voiceSocket.on('agent_ready_for_call', async (data) => {
        console.log('🎯 Agent ready for call:', data);
        
        // Ignore if we already have an active WebRTC connection (multiple agents responded)
        if (window.peerConnection) {
            console.log('⚠️ Ignoring - already have an active WebRTC connection');
            return;
        }
        
        showToast('Agent connected! Starting voice call...', 'success');
        
        const agentStatus = document.querySelector('.agent-details .agent-status');
        if (agentStatus) agentStatus.textContent = "Connected to " + (data.agent_id || 'Agent');
        
        // Store agent socket ID for signaling
        window.agentSocketId = data.agent_sid;
        window.transferSessionId = data.session_id;
        
        // Start WebRTC connection as the caller (customer initiates)
        await startWebRTCCall(data.agent_sid, data.session_id);
    });
    
    // Handle WebRTC answer from agent
    voiceSocket.on('webrtc_answer', async (data) => {
        console.log('📡 Received WebRTC answer from agent');
        if (window.peerConnection && data.answer) {
            try {
                await window.peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
                console.log('✅ Remote description set successfully');
                
                // Process any pending ICE candidates
                if (window.pendingIceCandidates && window.pendingIceCandidates.length > 0) {
                    console.log(`📡 Processing ${window.pendingIceCandidates.length} pending ICE candidates`);
                    for (const candidate of window.pendingIceCandidates) {
                        try {
                            await window.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
                        } catch (e) {
                            console.error('Error adding queued ICE candidate:', e);
                        }
                    }
                    window.pendingIceCandidates = [];
                }
            } catch (e) {
                console.error('Error setting remote description:', e);
            }
        }
    });
    
    // Queue for ICE candidates that arrive before remote description is set
    window.pendingIceCandidates = [];
    
    // Handle ICE candidates from agent
    voiceSocket.on('webrtc_ice_candidate', async (data) => {
        if (data.candidate) {
            // Check if peer connection exists and has remote description
            if (window.peerConnection && window.peerConnection.remoteDescription) {
                try {
                    await window.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
                } catch (e) {
                    console.error('Error adding ICE candidate:', e);
                }
            } else {
                // Queue the candidate for later
                console.log('⏳ Queuing ICE candidate (remote description not set yet)');
                window.pendingIceCandidates.push(data.candidate);
            }
        }
    });
    
    // Handle hangup from agent
    voiceSocket.on('webrtc_hangup', (data) => {
        console.log('📴 Agent ended the call');
        endWebRTCCall();
        showToast('Agent ended the call', 'info');
    });
    
    // Receive transcripts from agent
    voiceSocket.on('call_transcript', (data) => {
        console.log('📝 Received transcript:', data);
        addTransferTranscriptEntry(data.speaker, data.text);
    });

    voiceSocket.on('call_ended', (data) => {
        console.log('Call ended:', data);
        cleanupVoiceCall();
        
        // Show call duration toast
        showToast('Call ended. Duration: ' + formatVoiceTime(data.duration_seconds || 0), 'info');
        
        // Show evaluation score if available
        if (data.evaluation && data.evaluation.score) {
            setTimeout(() => {
                showToast(`Call Score: ${data.evaluation.score}/100 (${data.evaluation.grade})`, 'success');
            }, 1500);
        }
        
        // Show feedback modal for the call
        if (data.call_id) {
            setTimeout(() => {
                showFeedbackModal(data.call_id);
            }, 2500);
        }
        
        // Refresh call logs to show the new entry
        setTimeout(() => {
            loadCallLogs();
        }, 3000);
    });

    voiceSocket.on('error', (data) => {
        console.error('Voice error:', data.message);
        showToast('Error: ' + data.message, 'error');
    });
    
    // Handle no agents available
    voiceSocket.on('no_agents_available', (data) => {
        console.log('⚠️ No agents available:', data);
        showToast(data.message || 'All agents are busy. Please wait...', 'warning');
        
        // Update avatar status
        const agentStatus = document.querySelector('.agent-details .agent-status');
        if (agentStatus) agentStatus.textContent = "Waiting for agent...";
    });

    voiceSocket.on('disconnect', () => {
        console.log('Disconnected from voice server');
        if (voiceCallActive) {
            cleanupVoiceCall();
            showToast('Call disconnected', 'warning');
        }
    });
}

/**
 * Initialize Web Speech API for speech recognition
 */
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.warn('Speech Recognition not supported');
        showToast('Speech recognition not supported in this browser. Use Chrome for best experience.', 'warning');
        return;
    }

    voiceRecognition = new SpeechRecognition();
    voiceRecognition.continuous = true;
    voiceRecognition.interimResults = true;
    voiceRecognition.lang = 'en-IN';

    let finalTranscript = '';

    voiceRecognition.onresult = (event) => {
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript = transcript;

                // Send to server
                if (voiceSocket && voiceSocket.connected && finalTranscript.trim()) {
                    addVoiceTranscript('customer', finalTranscript.trim());
                    voiceSocket.emit('user_message', { text: finalTranscript.trim() });
                    finalTranscript = '';
                }
            } else {
                interimTranscript += transcript;
            }
        }
    };

    voiceRecognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
            // Restart if no speech detected
            if (voiceCallActive && !voiceIsMuted) {
                try { voiceRecognition.start(); } catch (e) { }
            }
        }
    };

    voiceRecognition.onend = () => {
        // Restart if call is still active
        if (voiceCallActive && !voiceIsMuted) {
            try { voiceRecognition.start(); } catch (e) { }
        }
    };

    // Start listening
    try {
        voiceRecognition.start();
    } catch (e) {
        console.error('Failed to start speech recognition:', e);
    }
}

/**
 * Add entry to voice transcript
 */
function addVoiceTranscript(speaker, text) {
    const transcript = document.getElementById('voice-transcript');
    const entry = document.createElement('div');
    entry.className = `voice-transcript-entry ${speaker}`;
    entry.innerHTML = `
        <div class="voice-transcript-speaker">${speaker === 'agent' ? '🤖 Priya' : '👤 You'}</div>
        <div class="voice-transcript-bubble">${text}</div>
    `;
    transcript.appendChild(entry);
    transcript.scrollTop = transcript.scrollHeight;
}

/**
 * Play TTS audio response
 */
function playVoiceAudio(base64Audio) {
    try {
        const audioPlayer = document.getElementById('voice-audio-player');
        const audioBlob = base64ToBlob(base64Audio, 'audio/mp3');
        const audioUrl = URL.createObjectURL(audioBlob);

        audioPlayer.src = audioUrl;
        audioPlayer.play().catch(e => console.log('Audio play failed:', e));

        // Show speaking animation
        const avatar = document.getElementById('voice-avatar');
        avatar.classList.add('speaking');

        audioPlayer.onended = () => {
            avatar.classList.remove('speaking');
            URL.revokeObjectURL(audioUrl);
        };
    } catch (e) {
        console.error('Failed to play audio:', e);
    }
}

/**
 * Convert base64 to Blob
 */
function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

/**
 * Toggle mute state
 */
function toggleVoiceMute() {
    voiceIsMuted = !voiceIsMuted;
    const muteBtn = document.getElementById('voice-mute');

    if (voiceIsMuted) {
        muteBtn.classList.add('muted');
        muteBtn.innerHTML = '<span>🔇</span><span>Unmute</span>';
        if (voiceRecognition) {
            try { voiceRecognition.stop(); } catch (e) { }
        }
        showToast('Microphone muted', 'info');
    } else {
        muteBtn.classList.remove('muted');
        muteBtn.innerHTML = '<span>🎤</span><span>Mute</span>';
        if (voiceRecognition && voiceCallActive) {
            try { voiceRecognition.start(); } catch (e) { }
        }
        showToast('Microphone unmuted', 'info');
    }
}

/**
 * End the voice call
 */
function endVoiceCall() {
    if (voiceSocket && voiceSocket.connected) {
        voiceSocket.emit('end_call', {});
    }
    cleanupVoiceCall();
}

/**
 * Clean up voice call resources
 */
function cleanupVoiceCall() {
    voiceCallActive = false;

    // Dispose Jitsi
    if (window.currentJitsiApi) {
        try { window.currentJitsiApi.dispose(); } catch(e){}
        window.currentJitsiApi = null;
    }

    // Stop speech recognition
    if (voiceRecognition) {
        try { voiceRecognition.stop(); } catch (e) { }
        voiceRecognition = null;
    }

    // Stop timer
    if (voiceTimerInterval) {
        clearInterval(voiceTimerInterval);
        voiceTimerInterval = null;
    }

    // Disconnect socket
    if (voiceSocket) {
        voiceSocket.disconnect();
        voiceSocket = null;
    }

    // Reset UI
    document.getElementById('voice-call-form').classList.remove('hidden');
    document.getElementById('voice-call-active').classList.add('hidden');
    
    // Cleanup Video
    const videoContainer = document.getElementById('live-agent-video');
    if (videoContainer) videoContainer.classList.add('hidden');
    const jitsiContainer = document.getElementById('jitsi-meet-container');
    if (jitsiContainer) jitsiContainer.innerHTML = '';

    document.getElementById('voice-timer').textContent = '00:00';
    document.getElementById('voice-mute').classList.remove('muted');
    document.getElementById('voice-mute').innerHTML = '<span>🎤</span><span>Mute</span>';
    voiceIsMuted = false;
}

/**
 * Update voice call timer
 */
function updateVoiceTimer() {
    if (!voiceCallStartTime) return;

    const elapsed = Math.floor((new Date() - voiceCallStartTime) / 1000);
    document.getElementById('voice-timer').textContent = formatVoiceTime(elapsed);
}

/**
 * Format seconds to MM:SS
 */
function formatVoiceTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// =============================================================================
// WEBRTC FUNCTIONS FOR CUSTOMER-AGENT VOICE CALLS
// =============================================================================

/**
 * Start WebRTC call to agent
 */
async function startWebRTCCall(agentSocketId, sessionId) {
    console.log('🎙️ Starting WebRTC call to agent:', agentSocketId);
    
    // Check if mediaDevices is available (requires HTTPS or localhost)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('❌ getUserMedia not available - need HTTPS or localhost');
        showToast('Microphone access requires a secure connection (localhost or HTTPS)', 'error');
        const agentStatus = document.querySelector('.agent-details .agent-status');
        if (agentStatus) agentStatus.textContent = "Connection error - need HTTPS";
        return;
    }
    
    try {
        // Get user's microphone
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        window.localStream = stream;
        console.log('✅ Got local audio stream');
        
        // Create peer connection with STUN servers
        const config = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
        
        window.peerConnection = new RTCPeerConnection(config);
        
        // Add local audio track to connection
        stream.getTracks().forEach(track => {
            window.peerConnection.addTrack(track, stream);
        });
        
        // Handle incoming audio from agent
        window.peerConnection.ontrack = (event) => {
            console.log('🔊 Received remote audio stream from agent');
            const remoteAudio = document.getElementById('remote-agent-audio') || createRemoteAudio();
            remoteAudio.srcObject = event.streams[0];
            remoteAudio.play().catch(e => console.log('Auto-play blocked:', e));
        };
        
        // Handle ICE candidates
        window.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                voiceSocket.emit('webrtc_ice_candidate', {
                    session_id: sessionId,
                    candidate: event.candidate,
                    target_sid: agentSocketId
                });
            }
        };
        
        // Connection state changes
        window.peerConnection.onconnectionstatechange = () => {
            console.log('WebRTC connection state:', window.peerConnection.connectionState);
            const agentStatus = document.querySelector('.agent-details .agent-status');
            
            switch (window.peerConnection.connectionState) {
                case 'connected':
                    if (agentStatus) agentStatus.textContent = "🟢 Connected";
                    showToast('Voice call connected!', 'success');
                    // Start speech recognition for transcription
                    startTransferSpeechRecognition(sessionId, agentSocketId);
                    break;
                case 'disconnected':
                case 'failed':
                    if (agentStatus) agentStatus.textContent = "🔴 Disconnected";
                    endWebRTCCall();
                    break;
            }
        };
        
        // Create and send offer
        const offer = await window.peerConnection.createOffer();
        await window.peerConnection.setLocalDescription(offer);
        
        voiceSocket.emit('webrtc_offer', {
            session_id: sessionId,
            offer: offer,
            target_sid: agentSocketId
        });
        console.log('📤 Sent WebRTC offer to agent');
        
    } catch (error) {
        console.error('❌ WebRTC Error:', error);
        showToast('Error accessing microphone: ' + error.message, 'error');
    }
}

/**
 * Create hidden audio element for remote stream
 */
function createRemoteAudio() {
    const audio = document.createElement('audio');
    audio.id = 'remote-agent-audio';
    audio.autoplay = true;
    audio.style.display = 'none';
    document.body.appendChild(audio);
    return audio;
}

/**
 * End WebRTC call
 */
function endWebRTCCall() {
    console.log('📴 Ending WebRTC call');
    
    // Stop local stream
    if (window.localStream) {
        window.localStream.getTracks().forEach(track => track.stop());
        window.localStream = null;
    }
    
    // Close peer connection
    if (window.peerConnection) {
        window.peerConnection.close();
        window.peerConnection = null;
    }
    
    // Stop transcription
    if (window.transferRecognition) {
        try { window.transferRecognition.stop(); } catch(e) {}
        window.transferRecognition = null;
    }
    
    // Remove remote audio
    const remoteAudio = document.getElementById('remote-agent-audio');
    if (remoteAudio) remoteAudio.remove();
    
    // Update UI
    const agentStatus = document.querySelector('.agent-details .agent-status');
    if (agentStatus) agentStatus.textContent = "Call ended";
    
    // Notify server
    if (window.agentSocketId && window.transferSessionId) {
        voiceSocket.emit('webrtc_hangup', {
            session_id: window.transferSessionId,
            target_sid: window.agentSocketId
        });
    }
    
    // Hide transcript container after a delay
    setTimeout(() => {
        const transcriptContainer = document.getElementById('transfer-transcript-container');
        if (transcriptContainer) transcriptContainer.remove();
    }, 3000);
}

/**
 * Start speech recognition for transcription during transfer call
 */
function startTransferSpeechRecognition(sessionId, agentSocketId) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('Speech Recognition not supported');
        return;
    }
    
    window.transferRecognition = new SpeechRecognition();
    window.transferRecognition.continuous = true;
    window.transferRecognition.interimResults = false;
    window.transferRecognition.lang = 'en-IN';
    
    window.transferRecognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                const text = event.results[i][0].transcript.trim();
                if (text) {
                    console.log('🎤 Customer said:', text);
                    // Add to local transcript
                    addTransferTranscriptEntry('customer', text);
                    // Send to agent
                    voiceSocket.emit('call_transcript', {
                        session_id: sessionId,
                        text: text,
                        speaker: 'customer',
                        target_sid: agentSocketId
                    });
                }
            }
        }
    };
    
    window.transferRecognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error !== 'no-speech') {
            // Try to restart
            setTimeout(() => {
                if (window.transferRecognition && window.peerConnection?.connectionState === 'connected') {
                    try { window.transferRecognition.start(); } catch(e) {}
                }
            }, 1000);
        }
    };
    
    window.transferRecognition.onend = () => {
        // Restart if still in call
        if (window.peerConnection?.connectionState === 'connected') {
            try { window.transferRecognition.start(); } catch(e) {}
        }
    };
    
    try {
        window.transferRecognition.start();
        console.log('🎤 Started transcription for transfer call');
    } catch(e) {
        console.error('Failed to start speech recognition:', e);
    }
}

/**
 * Show transcript container for transfer call
 */
function showTransferTranscript() {
    // Check if already exists
    if (document.getElementById('transfer-transcript-container')) return;
    
    const container = document.createElement('div');
    container.id = 'transfer-transcript-container';
    container.style.cssText = `
        position: fixed;
        bottom: 100px;
        right: 20px;
        width: 350px;
        max-height: 300px;
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        overflow: hidden;
        z-index: 1000;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    `;
    
    container.innerHTML = `
        <div style="padding: 12px 16px; background: linear-gradient(135deg, #3b82f6, #2563eb); display: flex; justify-content: space-between; align-items: center;">
            <span style="color: white; font-weight: 600;">📝 Live Transcript</span>
            <button onclick="endWebRTCCall()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">End Call</button>
        </div>
        <div id="transfer-transcript" style="padding: 12px; max-height: 250px; overflow-y: auto; font-size: 13px;"></div>
    `;
    
    document.body.appendChild(container);
}

/**
 * Add entry to transfer transcript
 */
function addTransferTranscriptEntry(speaker, text) {
    const transcript = document.getElementById('transfer-transcript');
    if (!transcript) return;
    
    const entry = document.createElement('div');
    entry.style.cssText = `
        margin-bottom: 8px;
        padding: 8px 12px;
        border-radius: 8px;
        background: ${speaker === 'customer' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)'};
        border-left: 3px solid ${speaker === 'customer' ? '#10b981' : '#3b82f6'};
    `;
    
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    entry.innerHTML = `
        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">
            ${speaker === 'customer' ? '👤 You' : '🎧 Agent'} • ${time}
        </div>
        <div style="color: #e2e8f0;">${text}</div>
    `;
    
    transcript.appendChild(entry);
    transcript.scrollTop = transcript.scrollHeight;
}