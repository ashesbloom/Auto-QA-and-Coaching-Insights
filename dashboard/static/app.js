// Battery Smart Auto-QA Dashboard - JavaScript

// Global data storage
let dashboardData = {
    overview: null,
    pillars: null,
    agents: null,
    cities: null,
    complaints: null,
    risks: null,
    calls: null
};

// Current user
let currentUser = null;

// Charts
let scoreDistChart = null;
let pillarChart = null;
let complaintsChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadUserData();
    initNavigation();
    updateDate();
    loadAllData();
});

// Load current user data
async function loadUserData() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            currentUser = await response.json();
            updateUserUI();
        } else {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

// Update user UI elements
function updateUserUI() {
    if (!currentUser) return;

    const initials = currentUser.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);

    // Update header user menu
    const avatar = document.getElementById('user-avatar');
    const avatarLarge = document.getElementById('user-avatar-large');
    const headerName = document.getElementById('header-user-name');

    if (avatar) avatar.textContent = initials;
    if (avatarLarge) avatarLarge.textContent = initials;
    if (headerName) headerName.textContent = currentUser.name;

    // Update profile section
    loadProfile();
}

// Toggle user dropdown menu
function toggleUserMenu() {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const userMenu = document.querySelector('.user-menu');
    const dropdown = document.getElementById('user-dropdown');
    if (userMenu && dropdown && !userMenu.contains(e.target)) {
        dropdown.classList.remove('active');
    }
});

// Switch section from dropdown
function switchSection(sectionName) {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) dropdown.classList.remove('active');

    const navItem = document.querySelector(`.nav-item[data-section="${sectionName}"]`);
    if (navItem) navItem.click();
}

// Handle logout
async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        showToast('Logout failed', 'error');
    }
}

// Load profile data
function loadProfile() {
    if (!currentUser) return;

    const profileName = document.getElementById('profile-name');
    const profileEmail = document.getElementById('profile-email');
    const profileAvatar = document.getElementById('profile-avatar');
    const nameInput = document.getElementById('profile-name-input');
    const phoneInput = document.getElementById('profile-phone-input');
    const cityInput = document.getElementById('profile-city-input');
    const statSince = document.getElementById('stat-since');

    const initials = currentUser.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);

    if (profileName) profileName.textContent = currentUser.name;
    if (profileEmail) profileEmail.textContent = currentUser.email;
    if (profileAvatar) profileAvatar.textContent = initials;
    if (nameInput) nameInput.value = currentUser.name || '';
    if (phoneInput) phoneInput.value = currentUser.phone || '';
    if (cityInput) cityInput.value = currentUser.city || '';
    if (statSince && currentUser.created_at) {
        const date = new Date(currentUser.created_at);
        statSince.textContent = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }
}

// Handle profile update
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

        if (data.success || data.user) {
            currentUser = data.user || { ...currentUser, name, phone, city };
            updateUserUI();
            showToast('Profile updated successfully!', 'success');
        } else {
            showToast('Failed to update profile', 'error');
        }
    } catch (error) {
        showToast('Failed to update profile', 'error');
    }
}

// Toast notification
function showToast(message, type = 'success') {
    // Create toast if it doesn't exist
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        toast.innerHTML = '<span id="toast-message"></span>';
        document.body.appendChild(toast);
    }

    const toastMessage = document.getElementById('toast-message');
    if (toastMessage) toastMessage.textContent = message;

    toast.className = `toast active ${type}`;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// Navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;

            // Update nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Update section
            document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
            document.getElementById(section).classList.add('active');

            // Update title
            document.getElementById('page-title').textContent = item.querySelector('span:last-child').textContent;
        });
    });
}

// Update date display
function updateDate() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').textContent = now.toLocaleDateString('en-US', options);
}

// Load all data from API
async function loadAllData() {
    try {
        const [overview, pillars, agents, cities, complaints, risks, calls] = await Promise.all([
            fetch('/api/overview').then(r => r.json()),
            fetch('/api/pillars').then(r => r.json()),
            fetch('/api/agents').then(r => r.json()),
            fetch('/api/cities').then(r => r.json()),
            fetch('/api/complaints').then(r => r.json()),
            fetch('/api/risks').then(r => r.json()),
            fetch('/api/calls').then(r => r.json())
        ]);

        dashboardData = { overview, pillars, agents, cities, complaints, risks, calls };

        renderOverview();
        renderScorecards();
        renderAgentLeaderboard();
        renderCities();
        renderComplaints();
        renderAlerts();
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// Refresh data
function refreshData() {
    loadAllData();
}

// Render Overview Section
function renderOverview() {
    const data = dashboardData.overview;
    if (!data) return;

    // Update stat cards
    document.getElementById('total-calls').textContent = data.average_score ?
        Math.round(data.average_score * 10 / 10) : '-';

    // Calculate from score distribution
    const totalCalls = Object.values(data.score_distribution).reduce((a, b) => a + b, 0);
    document.getElementById('total-calls').textContent = totalCalls;
    document.getElementById('avg-score').textContent = data.average_score?.toFixed(1) || '-';
    document.getElementById('needs-review').textContent = data.calls_needing_review || 0;
    document.getElementById('excellent-calls').textContent = data.score_distribution?.['excellent (90+)'] || 0;

    // Render charts
    renderScoreDistChart(data.score_distribution);
    renderPillarChart();
}

// Score Distribution Chart
function renderScoreDistChart(distribution) {
    const ctx = document.getElementById('scoreDistChart');
    if (!ctx) return;

    if (scoreDistChart) scoreDistChart.destroy();

    const labels = ['Excellent (90+)', 'Good (75-89)', 'Needs Improvement (60-74)', 'Poor (40-59)', 'Critical (<40)'];
    const data = [
        distribution['excellent (90+)'] || 0,
        distribution['good (75-89)'] || 0,
        distribution['needs_improvement (60-74)'] || 0,
        distribution['poor (40-59)'] || 0,
        distribution['critical (<40)'] || 0
    ];

    scoreDistChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#10b981',
                    '#3b82f6',
                    '#f59e0b',
                    '#ef4444',
                    '#991b1b'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#94a3b8',
                        padding: 15
                    }
                }
            }
        }
    });
}

// Pillar Performance Chart
function renderPillarChart() {
    const ctx = document.getElementById('pillarChart');
    if (!ctx) return;

    const pillars = dashboardData.pillars?.pillar_details;
    if (!pillars) return;

    if (pillarChart) pillarChart.destroy();

    const labels = Object.keys(pillars).map(p => p.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
    const data = Object.values(pillars).map(p => p.average_score);

    pillarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Score',
                data: data,
                backgroundColor: [
                    '#6366f1',
                    '#10b981',
                    '#f59e0b',
                    '#3b82f6',
                    '#ef4444'
                ],
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(255,255,255,0.1)'
                    },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Render Scorecards Table
function renderScorecards() {
    const tbody = document.getElementById('calls-tbody');
    if (!tbody) return;

    const calls = dashboardData.calls || [];

    tbody.innerHTML = calls.map(call => {
        const scoreClass = call.score >= 90 ? 'excellent' :
            call.score >= 75 ? 'good' :
                call.score >= 60 ? 'needs-improvement' : 'poor';

        return `
            <tr>
                <td>${call.call_id}</td>
                <td>${call.agent_name}</td>
                <td>${call.city}</td>
                <td><span class="score-badge ${scoreClass}">${call.score}</span></td>
                <td>${call.grade}</td>
                <td>
                    <span class="status-badge ${call.needs_review ? 'review' : 'ok'}">
                        ${call.needs_review ? '⚠️ Review' : '✅ OK'}
                    </span>
                </td>
                <td>
                    <button class="view-btn" onclick="viewCallDetail('${call.call_id}')">View</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Render Agent Leaderboard
function renderAgentLeaderboard() {
    const container = document.getElementById('agent-leaderboard');
    if (!container) return;

    const leaderboard = dashboardData.agents?.leaderboard || [];

    container.innerHTML = leaderboard.map((agent, index) => `
        <div class="leaderboard-item ${index < 3 ? 'top-3' : ''}">
            <div class="rank">${agent.rank}</div>
            <div class="agent-info">
                <div class="agent-name">${agent.agent_name}</div>
                <div class="agent-meta">${agent.total_calls} calls · ${agent.city || 'Unknown'}</div>
            </div>
            <div class="agent-score">${agent.average_score}</div>
        </div>
    `).join('');
}

// Render Cities
function renderCities() {
    const container = document.getElementById('cities-grid');
    if (!container) return;

    const cities = dashboardData.cities?.by_city || {};

    container.innerHTML = Object.entries(cities).map(([city, data]) => `
        <div class="city-card">
            <div class="city-name">📍 ${city}</div>
            <div class="city-stat">
                <span class="city-stat-label">Total Calls</span>
                <span>${data.total_calls}</span>
            </div>
            <div class="city-stat">
                <span class="city-stat-label">Avg Score</span>
                <span>${data.average_score}</span>
            </div>
            <div class="city-stat">
                <span class="city-stat-label">Agents</span>
                <span>${data.agents_count}</span>
            </div>
        </div>
    `).join('');
}

// Render Complaints
function renderComplaints() {
    const container = document.getElementById('complaint-list');
    if (!container) return;

    const complaints = dashboardData.complaints?.by_type || {};

    // Render complaint chart
    renderComplaintsChart(complaints);

    // Render list
    container.innerHTML = Object.entries(complaints).map(([type, data]) => `
        <div class="complaint-item">
            <span class="complaint-name">${type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
            <span class="complaint-count">${data.count} calls (${data.percentage}%)</span>
        </div>
    `).join('');
}

// Complaints Chart
function renderComplaintsChart(complaints) {
    const ctx = document.getElementById('complaintsChart');
    if (!ctx) return;

    if (complaintsChart) complaintsChart.destroy();

    const labels = Object.keys(complaints).map(c => c.replace(/_/g, ' '));
    const data = Object.values(complaints).map(c => c.count);

    complaintsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Calls',
                data: data,
                backgroundColor: '#6366f1',
                borderRadius: 8
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Render Alerts
function renderAlerts() {
    const container = document.getElementById('alerts-container');
    const badge = document.getElementById('alert-count');
    if (!container) return;

    const risks = dashboardData.risks || {};
    const criticalCalls = risks.critical_calls || [];

    badge.textContent = criticalCalls.length;

    if (criticalCalls.length === 0) {
        container.innerHTML = `
            <div class="alert-card" style="border-color: #10b981">
                <div class="alert-icon">✅</div>
                <div class="alert-content">
                    <div class="alert-title">No Critical Alerts</div>
                    <div class="alert-meta">All calls are within acceptable parameters</div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = criticalCalls.map(call => `
        <div class="alert-card">
            <div class="alert-icon">🚨</div>
            <div class="alert-content">
                <div class="alert-title">${call.call_id}</div>
                <div class="alert-meta">
                    Agent: ${call.agent} · Score: ${call.score} · 
                    Issues: ${call.alerts?.join(', ') || 'Low score'}
                </div>
            </div>
            <button class="alert-action" onclick="viewCallDetail('${call.call_id}')">Review</button>
        </div>
    `).join('');
}

// View call detail in modal
async function viewCallDetail(callId) {
    const modal = document.getElementById('call-modal');
    const body = document.getElementById('modal-body');

    try {
        const data = await fetch(`/api/call/${callId}`).then(r => r.json());

        if (data.error) {
            body.innerHTML = `<p>Call not found</p>`;
        } else {
            body.innerHTML = `
                <h2 style="margin-bottom: 20px;">Call Evaluation: ${data.metadata.call_id}</h2>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
                    <div><strong>Agent:</strong> ${data.metadata.agent_name}</div>
                    <div><strong>City:</strong> ${data.metadata.city}</div>
                    <div><strong>Timestamp:</strong> ${data.metadata.timestamp}</div>
                    <div><strong>Overall Score:</strong> <span style="font-size: 24px; color: #6366f1">${data.overall.score}/100</span></div>
                </div>
                
                <h3 style="margin: 20px 0 12px;">Pillar Breakdown</h3>
                <div style="display: grid; gap: 12px;">
                    ${Object.entries(data.pillar_scores).map(([pillar, info]) => `
                        <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                            <span>${pillar.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                            <span style="font-weight: 600">${info.score}/100 (${info.weight})</span>
                        </div>
                    `).join('')}
                </div>
                
                ${data.coaching_insights?.top_recommendations?.length ? `
                    <h3 style="margin: 20px 0 12px;">Coaching Recommendations</h3>
                    <ul style="list-style: disc; padding-left: 20px; color: #94a3b8;">
                        ${data.coaching_insights.top_recommendations.slice(0, 3).map(rec => `
                            <li style="margin-bottom: 8px;">${rec}</li>
                        `).join('')}
                    </ul>
                ` : ''}
                
                ${data.supervisor_alerts?.length ? `
                    <h3 style="margin: 20px 0 12px; color: #ef4444;">⚠️ Supervisor Alerts</h3>
                    ${data.supervisor_alerts.map(alert => `
                        <div style="padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px; margin-bottom: 8px;">
                            <strong>${alert.category}</strong>: ${alert.keywords_matched?.join(', ')}
                        </div>
                    `).join('')}
                ` : ''}
            `;
        }

        modal.classList.add('active');
    } catch (error) {
        body.innerHTML = `<p>Error loading call details</p>`;
        modal.classList.add('active');
    }
}

// Close modal
function closeModal() {
    document.getElementById('call-modal').classList.remove('active');
}

// Close modal on outside click
document.getElementById('call-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'call-modal') closeModal();
});

// =============================================================================
// SCORECARDS AND COMPLAINTS INTEGRATION
// =============================================================================

// Render Scorecards Section (Voice Call Evaluations)
async function renderScorecards() {
    try {
        const response = await fetch('/api/evaluations');
        const data = await response.json();

        if (!data.success || !data.evaluations) {
            console.error('Failed to load evaluations');
            return;
        }

        const tbody = document.getElementById('calls-tbody');
        if (!tbody) return;

        if (data.evaluations.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #94a3b8;">
                        No voice call evaluations yet. Make a voice call to see QA results here!
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = data.evaluations.map(callEval => {
            // Color code based on score
            let scoreColor = '#10b981'; // Green
            if (callEval.overall_score < 60) scoreColor = '#ef4444'; // Red
            else if (callEval.overall_score < 80) scoreColor = '#f59e0b'; // Yellow

            // Status badge
            let statusBadge = '';
            if (callEval.needs_review) {
                statusBadge = '<span style="padding: 4px 8px; background: #ef4444; border-radius: 4px; font-size: 12px;">Review</span>';
            } else if (callEval.overall_score >= 80) {
                statusBadge = '<span style="padding: 4px 8px; background: #10b981; border-radius: 4px; font-size: 12px;">Excellent</span>';
            } else {
                statusBadge = '<span style="padding: 4px 8px; background: #6366f1; border-radius: 4px; font-size: 12px;">Good</span>';
            }

            return `
                <tr style="cursor: pointer;" onclick="viewEvaluationDetails('${callEval.evaluation_id}')">
                    <td>${callEval.call_id}</td>
                    <td>${callEval.agent_name}</td>
                    <td>${callEval.city}</td>
                    <td><span style="font-weight: 600; color: ${scoreColor}">${callEval.overall_score}/100</span></td>
                    <td>${callEval.grade}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="view-btn" onclick="viewEvaluationDetails('${callEval.evaluation_id}'); event.stopPropagation();">
                            View Details
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error rendering scorecards:', error);
    }
}

// Render Complaints Section
async function renderComplaints() {
    try {
        const response = await fetch('/api/complaints');
        const data = await response.json();

        if (!data.success || !data.complaints) {
            console.error('Failed to load complaints');
            return;
        }

        const container = document.getElementById('complaint-list');
        if (!container) return;

        if (data.complaints.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 60px; color: #94a3b8;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🎉</div>
                    <h3 style="margin-bottom: 8px;">No complaints yet!</h3>
                    <p>All voice calls are meeting quality standards.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.complaints.map(complaint => {
            // Severity color
            let severityColor = '#f59e0b';
            if (complaint.severity === 'high') severityColor = '#ef4444';
            else if (complaint.severity === 'low') severityColor = '#10b981';

            // Sentiment emoji
            let sentimentEmoji = '😐';
            if (complaint.sentiment === 'negative') sentimentEmoji = '😞';
            else if (complaint.sentiment === 'positive') sentimentEmoji = '😊';

            return `
                <div class="complaint-card" style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin-bottom: 16px; border-left: 4px solid ${severityColor};" onclick="viewEvaluationDetails('${complaint.evaluation_id}')">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                        <div>
                            <h3 style="margin: 0 0 4px 0; color: #f1f5f9;">${complaint.category}</h3>
                            <p style="margin: 0; font-size: 13px; color: #94a3b8;">
                                Call ID: ${complaint.call_id} • Agent: ${complaint.agent_name}
                            </p>
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-size: 20px;">${sentimentEmoji}</span>
                            <span style="padding: 4px 12px; background: ${severityColor}; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                                ${complaint.severity}
                            </span>
                        </div>
                    </div>
                    <p style="margin: 12px 0; color: #cbd5e1; line-height: 1.6;">
                        ${complaint.description}
                    </p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);">
                        <span style="font-size: 13px; color: #94a3b8;">
                            Score: <strong style="color: ${severityColor}">${complaint.score}/100</strong>
                        </span>
                        <span style="font-size: 13px; color: #94a3b8;">
                            ${new Date(complaint.timestamp).toLocaleString()}
                        </span>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error rendering complaints:', error);
    }
}

// View evaluation details in modal
async function viewEvaluationDetails(evaluationId) {
    const modal = document.getElementById('call-modal');
    const body = document.getElementById('modal-body');

    if (!modal || !body) return;

    body.innerHTML = '<p style="text-align: center;">Loading...</p>';
    modal.classList.add('active');

    try {
        const response = await fetch(`/api/evaluations/${evaluationId}`);
        const result = await response.json();

        if (!result.success || !result.evaluation) {
            body.innerHTML = '<p>Evaluation not found</p>';
            return;
        }

        const data = result.evaluation;

        // Reuse existing modal rendering from viewCallDetails function
        body.innerHTML = `
            <h2 style="margin-top: 0;">Evaluation ${evaluationId}</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; color: #94a3b8; font-size: 14px;">
                <div><strong>Call ID:</strong> ${data.metadata.call_id}</div>
                <div><strong>Agent:</strong> ${data.metadata.agent_name}</div>
                <div><strong>City:</strong> ${data.metadata.city}</div>
                <div><strong>Timestamp:</strong> ${data.metadata.timestamp}</div>
                <div><strong>Overall Score:</strong> <span style="font-size: 24px; color: #6366f1">${data.overall.score}/100</span></div>
                <div><strong>Grade:</strong> ${data.overall.grade}</div>
            </div>
            
            <h3 style="margin: 20px 0 12px;">Pillar Breakdown</h3>
            <div style="display: grid; gap: 12px;">
                ${Object.entries(data.pillar_scores).map(([pillar, info]) => `
                    <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                        <span>${pillar.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                        <span style="font-weight: 600">${info.score}/100 (×${info.weight})</span>
                    </div>
                `).join('')}
            </div>
            
            ${data.coaching_insights?.top_recommendations?.length ? `
                <h3 style="margin: 20px 0 12px;">Coaching Recommendations</h3>
                <ul style="list-style: disc; padding-left: 20px; color: #94a3b8;">
                    ${data.coaching_insights.top_recommendations.slice(0, 3).map(rec => `
                        <li style="margin-bottom: 8px;">${rec}</li>
                    `).join('')}
                </ul>
            ` : ''}
            
            ${data.supervisor_alerts?.length ? `
                <h3 style="margin: 20px 0 12px; color: #ef4444;">⚠️ Supervisor Alerts</h3>
                ${data.supervisor_alerts.map(alert => `
                    <div style="padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px; margin-bottom: 8px;">
                        <strong>${alert.category}</strong>: ${alert.keywords_matched?.join(', ')}
                    </div>
                `).join('')}
            ` : ''}
        `;

    } catch (error) {
        console.error('Error loading evaluation details:', error);
        body.innerHTML = '<p>Error loading evaluation details</p>';
    }
}
