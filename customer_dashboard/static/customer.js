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
        // Fetch regular logs and voice logs
        const [regularLogsRes, voiceLogsRes] = await Promise.all([
            fetch('/api/call-logs'),
            fetch('/api/voice-call-logs')
        ]);

        const regularLogs = await regularLogsRes.json();
        const voiceLogsData = await voiceLogsRes.json();
        const voiceLogs = voiceLogsData.success ? voiceLogsData.logs : [];

        // Map voice logs to common format
        const formattedVoiceLogs = voiceLogs.map(log => ({
            id: log.id,
            type: 'voice-call',
            subject: log.title || 'Voice Call',
            status: log.status,
            duration: log.duration,
            timestamp: log.date,
            satisfaction_score: log.rating,
            transcript: log.transcript,
            is_voice: true
        }));

        // Combine and sort by date (newest first)
        allCallLogs = [...regularLogs, ...formattedVoiceLogs].sort((a, b) =>
            new Date(b.timestamp) - new Date(a.timestamp)
        );

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

    container.innerHTML = logs.map(log => {
        let icon = '💬';
        if (log.type === 'call') icon = '📞';
        if (log.type === 'voice-call') icon = '🎙️';

        return `
        <div class="log-item" onclick="showTranscript('${log.id}')">
            <div class="log-icon ${log.type}">${icon}</div>
            <div class="log-info">
                <h4>${log.subject}</h4>
                <p>${log.status} • ${log.duration}</p>
            </div>
            <div class="log-meta">
                <div class="date">${formatDate(log.timestamp)}</div>
                ${log.satisfaction_score ?
                `<div class="log-rating">${'⭐'.repeat(log.satisfaction_score)}</div>` : ''}
            </div>
            <div class="log-actions">
                <button class="log-action-btn" onclick="event.stopPropagation(); showTranscript('${log.id}')">📝 Transcript</button>
            </div>
        </div>
    `}).join('');
}

function showTranscript(callId) {
    const log = allCallLogs.find(l => l.id === callId);
    if (!log) return;

    const transcriptContent = document.getElementById('transcript-content');

    // Handle voice transcript array
    if (log.is_voice && Array.isArray(log.transcript)) {
        transcriptContent.innerHTML = log.transcript.map(entry => `
            <div class="voice-transcript-entry ${entry.speaker.toLowerCase()}">
                <div class="voice-transcript-speaker">${entry.speaker}</div>
                <div class="voice-transcript-bubble">${entry.text}</div>
            </div>
        `).join('');
    } else {
        // Handle regular text transcript
        transcriptContent.textContent = log.transcript || 'No transcript available';
    }

    document.getElementById('transcript-modal').classList.remove('hidden');
}

function closeTranscriptModal() {
    document.getElementById('transcript-modal').classList.add('hidden');
}

function downloadTranscript() {
    const contentText = document.getElementById('transcript-content').innerText;
    const blob = new Blob([contentText], { type: 'text/plain' });
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
    voiceSocket = io({
        transports: ['websocket', 'polling']
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

    voiceSocket.on('call_ended', (data) => {
        console.log('Call ended:', data);
        cleanupVoiceCall();
        showToast('Call ended. Duration: ' + formatVoiceTime(data.duration_seconds || 0), 'info');
    });

    voiceSocket.on('error', (data) => {
        console.error('Voice error:', data.message);
        showToast('Error: ' + data.message, 'error');
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
    // Calculate call duration before cleanup
    const duration = voiceCallStartTime ? Math.floor((new Date() - voiceCallStartTime) / 1000) : 0;

    // Get transcript content before cleanup
    const transcriptEl = document.getElementById('voice-transcript');
    let transcriptEntries = [];
    transcriptEl.querySelectorAll('.voice-transcript-entry').forEach(entry => {
        const speaker = entry.classList.contains('agent') ? 'Agent' : 'Customer';
        const text = entry.querySelector('.voice-transcript-bubble').textContent;
        transcriptEntries.push({ speaker, text });
    });

    // Store last call data for feedback
    lastVoiceCallData = {
        duration: duration,
        transcript: transcriptEntries,
        name: voiceUserName,
        phone: voiceUserPhone,
        timestamp: new Date().toISOString()
    };

    if (voiceSocket && voiceSocket.connected) {
        voiceSocket.emit('end_call', {});
    }
    cleanupVoiceCall();

    // Show feedback modal
    showVoiceFeedbackModal();
}

/**
 * Clean up voice call resources
 */
function cleanupVoiceCall() {
    voiceCallActive = false;

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
// VOICE FEEDBACK FUNCTIONALITY
// =============================================================================

let lastVoiceCallData = null;
let voiceFeedbackRating = 0;
let voiceFeedbackTags = [];

/**
 * Show the voice feedback modal
 */
function showVoiceFeedbackModal() {
    // Reset feedback state
    voiceFeedbackRating = 0;
    voiceFeedbackTags = [];

    // Reset stars
    document.querySelectorAll('#voice-feedback-stars .star').forEach(star => {
        star.classList.remove('active');
    });

    // Reset tags
    document.querySelectorAll('#voice-feedback-tags .feedback-tag').forEach(tag => {
        tag.classList.remove('selected');
    });

    // Reset comments
    document.getElementById('voice-feedback-comments').value = '';

    // Initialize star click handlers
    document.querySelectorAll('#voice-feedback-stars .star').forEach(star => {
        star.onclick = function () {
            voiceFeedbackRating = parseInt(this.dataset.rating);
            updateVoiceFeedbackStars();
        };
    });

    // Initialize tag click handlers
    document.querySelectorAll('#voice-feedback-tags .feedback-tag').forEach(tag => {
        tag.onclick = function () {
            this.classList.toggle('selected');
            const tagValue = this.dataset.tag;
            if (voiceFeedbackTags.includes(tagValue)) {
                voiceFeedbackTags = voiceFeedbackTags.filter(t => t !== tagValue);
            } else {
                voiceFeedbackTags.push(tagValue);
            }
        };
    });

    // Show modal
    document.getElementById('voice-feedback-modal').classList.remove('hidden');
}

/**
 * Update star display based on rating
 */
function updateVoiceFeedbackStars() {
    document.querySelectorAll('#voice-feedback-stars .star').forEach(star => {
        const rating = parseInt(star.dataset.rating);
        if (rating <= voiceFeedbackRating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

/**
 * Submit voice feedback and save call log
 */
function submitVoiceFeedback() {
    const comments = document.getElementById('voice-feedback-comments').value.trim();

    // Create call log entry
    const callLog = {
        id: 'VC-' + Date.now(),
        type: 'voice-call',
        title: 'AI Voice Call',
        date: lastVoiceCallData?.timestamp || new Date().toISOString(),
        duration: formatVoiceTime(lastVoiceCallData?.duration || 0),
        status: 'completed',
        rating: voiceFeedbackRating,
        feedbackTags: voiceFeedbackTags,
        feedbackComments: comments,
        transcript: lastVoiceCallData?.transcript || [],
        customerName: lastVoiceCallData?.name || 'Customer',
        customerPhone: lastVoiceCallData?.phone || ''
    };

    // Save to server
    saveVoiceCallLog(callLog);

    // Close modal
    closeVoiceFeedbackModal();

    showToast('Thank you for your feedback!', 'success');
}

/**
 * Skip feedback and just save the call log
 */
function skipVoiceFeedback() {
    // Create call log entry without feedback
    const callLog = {
        id: 'VC-' + Date.now(),
        type: 'voice-call',
        title: 'AI Voice Call',
        date: lastVoiceCallData?.timestamp || new Date().toISOString(),
        duration: formatVoiceTime(lastVoiceCallData?.duration || 0),
        status: 'completed',
        rating: 0,
        feedbackTags: [],
        feedbackComments: '',
        transcript: lastVoiceCallData?.transcript || [],
        customerName: lastVoiceCallData?.name || 'Customer',
        customerPhone: lastVoiceCallData?.phone || ''
    };

    // Save to server
    saveVoiceCallLog(callLog);

    // Close modal
    closeVoiceFeedbackModal();
}

/**
 * Close feedback modal
 */
function closeVoiceFeedbackModal() {
    document.getElementById('voice-feedback-modal').classList.add('hidden');
    lastVoiceCallData = null;
}

/**
 * Save voice call log to server
 */
async function saveVoiceCallLog(callLog) {
    try {
        const response = await fetch('/api/voice-call-log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(callLog)
        });

        if (response.ok) {
            console.log('Voice call log saved');
            // Refresh call logs if on that tab
            loadCallLogs();
        }
    } catch (error) {
        console.error('Failed to save voice call log:', error);
    }
}

