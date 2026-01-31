"""
Unified Dashboard Server for Battery Smart Auto-QA System
Flask-based web server with role-based access for Admin and Customer dashboards.
Includes integrated Voice Agent with WebSocket support.
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
from functools import wraps
import json
from datetime import datetime
import os
import sys
import uuid
import base64
import asyncio

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from call_evaluator import CallEvaluator, CallMetadata
from analytics import AnalyticsEngine
from sample_transcripts import ALL_TRANSCRIPTS, SAMPLE_METADATA

# Import voice agent
from voice_agent import VoiceAgent, VoiceSessionManager

# Check for TTS availability
try:
    from speech.tts_handler import TTSHandler, EDGE_TTS_AVAILABLE
except ImportError:
    EDGE_TTS_AVAILABLE = False
    TTSHandler = None

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=BASE_DIR,
            static_folder=os.path.join(BASE_DIR, 'dashboard', 'static'),
            static_url_path='/static')
app.secret_key = 'battery-smart-unified-secret-2024'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Voice session manager
voice_session_manager = VoiceSessionManager(api_key=os.getenv('GEMINI_API_KEY'))

# Active socket sessions for voice
voice_socket_sessions = {}

# Transcript storage directory
voice_transcripts_dir = os.path.join(BASE_DIR, 'voice_transcripts')
os.makedirs(voice_transcripts_dir, exist_ok=True)

# =============================================================================
# USERS DATABASE (In-Memory with Role-Based Access)
# =============================================================================

users_db = {
    # Admin users
    "admin@batterysmart.com": {
        "id": "ADM-001",
        "name": "Admin User",
        "email": "admin@batterysmart.com",
        "password": "admin123",
        "phone": "9999999999",
        "city": "Bangalore",
        "role": "admin",
        "created_at": "2024-01-01"
    },
    "supervisor@batterysmart.com": {
        "id": "ADM-002",
        "name": "QA Supervisor",
        "email": "supervisor@batterysmart.com",
        "password": "super123",
        "phone": "9999999998",
        "city": "Mumbai",
        "role": "admin",
        "created_at": "2024-01-01"
    },
    # Customer users
    "demo@batterysmart.com": {
        "id": "USR-001",
        "name": "Demo User",
        "email": "demo@batterysmart.com",
        "password": "demo123",
        "phone": "9876543210",
        "city": "Bangalore",
        "plan": "Pro",
        "role": "customer",
        "created_at": "2024-01-01"
    },
    "customer@batterysmart.com": {
        "id": "USR-002",
        "name": "Rajesh Kumar",
        "email": "customer@batterysmart.com",
        "password": "cust123",
        "phone": "9876543211",
        "city": "Mumbai",
        "plan": "Basic",
        "role": "customer",
        "created_at": "2024-01-05"
    }
}

# =============================================================================
# ADMIN DATA - QA Analytics
# =============================================================================

analytics_engine = AnalyticsEngine()
evaluator = CallEvaluator()
all_evaluations = []

def initialize_sample_data():
    """Load sample data into analytics engine."""
    global all_evaluations
    
    for call_type, transcript in ALL_TRANSCRIPTS.items():
        metadata = SAMPLE_METADATA.get(call_type, {})
        meta = CallMetadata(
            call_id=metadata.get("call_id", f"CALL-{call_type}"),
            agent_id=metadata.get("agent_id", "UNKNOWN"),
            agent_name=metadata.get("agent_name", "Unknown Agent"),
            city=metadata.get("city", "Unknown"),
            timestamp=metadata.get("timestamp", "Unknown"),
            duration_seconds=metadata.get("duration_seconds", 0)
        )
        
        evaluation = evaluator.evaluate_call(transcript, meta)
        all_evaluations.append(evaluation)
        analytics_engine.add_evaluation(evaluation)

# Initialize on startup
initialize_sample_data()

# =============================================================================
# VOICE CALL EVALUATIONS STORAGE
# =============================================================================

# File path for persistent storage
evaluations_file = os.path.join(os.path.dirname(__file__), 'voice_call_evaluations.json')

# In-memory list of voice call evaluations
voice_call_evaluations = []

# Load existing evaluations from file
if os.path.exists(evaluations_file):
    try:
        with open(evaluations_file, 'r') as f:
            voice_call_evaluations = json.load(f)
        print(f"Loaded {len(voice_call_evaluations)} voice call evaluations from storage")
    except Exception as e:
        print(f"Error loading voice call evaluations: {e}")
        voice_call_evaluations = []

# =============================================================================
# CUSTOMER DATA (In-Memory)
# =============================================================================

call_logs_db = {
    "USR-001": [
        {
            "id": "CALL-001",
            "type": "chat",
            "subject": "Battery unlock issue",
            "status": "resolved",
            "timestamp": "2024-01-15 10:30:00",
            "duration": 245,
            "satisfaction_score": 4,
            "transcript": "Customer: My battery is locked...\nAgent: Let me help you with that..."
        },
        {
            "id": "CALL-002",
            "type": "call",
            "subject": "Billing inquiry",
            "status": "resolved",
            "timestamp": "2024-01-14 14:20:00",
            "duration": 180,
            "satisfaction_score": 5,
            "transcript": "Customer: I was charged twice...\nAgent: I apologize for the inconvenience..."
        }
    ],
    "USR-002": []
}

tickets_db = {
    "USR-001": [
        {
            "id": "TKT-001",
            "subject": "Refund not received",
            "category": "billing",
            "status": "in_progress",
            "priority": "high",
            "created_at": "2024-01-16 09:00:00",
            "updated_at": "2024-01-16 15:30:00",
            "description": "Refund of Rs. 500 not credited after 7 days",
            "history": [
                {"time": "2024-01-16 09:00:00", "action": "Ticket created"},
                {"time": "2024-01-16 15:30:00", "action": "Assigned to billing team"}
            ]
        }
    ],
    "USR-002": []
}

notifications_db = {
    "USR-001": [
        {"id": "NTF-001", "type": "info", "message": "Welcome to Battery Smart!", "read": True, "time": "2024-01-01 10:00:00"},
        {"id": "NTF-002", "type": "success", "message": "Your subscription has been renewed", "read": True, "time": "2024-01-10 08:00:00"},
        {"id": "NTF-003", "type": "warning", "message": "Scheduled call reminder for tomorrow 10 AM", "read": False, "time": "2024-01-15 18:00:00"}
    ],
    "USR-002": [
        {"id": "NTF-001", "type": "info", "message": "Welcome to Battery Smart!", "read": False, "time": "2024-01-05 10:00:00"}
    ]
}

scheduled_calls_db = {}
feedback_db = []
chat_history_db = {}

# =============================================================================
# AUTHENTICATION DECORATORS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login_page'))
        if session.get('user_role') != 'admin':
            if request.is_json:
                return jsonify({"error": "Admin access required"}), 403
            return redirect(url_for('customer_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login_page'))
        if session.get('user_role') != 'customer':
            if request.is_json:
                return jsonify({"error": "Customer access required"}), 403
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# PUBLIC ROUTES
# =============================================================================

@app.route('/')
def home():
    """Redirect to login or appropriate dashboard."""
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('customer_dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """Unified login page."""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('dashboard/templates/login.html')

# =============================================================================
# AUTH API ENDPOINTS
# =============================================================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Handle login with role detection."""
    data = request.get_json()
    email = data.get('email', '').lower()
    password = data.get('password', '')
    
    if email in users_db and users_db[email]['password'] == password:
        user = users_db[email]
        session['user_id'] = user['id']
        session['user_email'] = email
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": email,
                "role": user['role']
            },
            "redirect": "/admin" if user['role'] == 'admin' else "/customer"
        })
    
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    """Handle customer signup (customers only)."""
    data = request.get_json()
    email = data.get('email', '').lower()
    
    if email in users_db:
        return jsonify({"success": False, "error": "Email already exists"}), 400
    
    user_id = f"USR-{len([u for u in users_db.values() if u['role'] == 'customer']) + 1:03d}"
    users_db[email] = {
        "id": user_id,
        "name": data.get('name', ''),
        "email": email,
        "password": data.get('password', ''),
        "phone": data.get('phone', ''),
        "city": data.get('city', 'Unknown'),
        "plan": "Basic",
        "role": "customer",
        "created_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Initialize empty data for new user
    call_logs_db[user_id] = []
    tickets_db[user_id] = []
    notifications_db[user_id] = [
        {"id": "NTF-001", "type": "info", "message": "Welcome to Battery Smart!", "read": False, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ]
    
    session['user_id'] = user_id
    session['user_email'] = email
    session['user_name'] = data.get('name', '')
    session['user_role'] = 'customer'
    
    return jsonify({
        "success": True,
        "user": {"id": user_id, "name": data.get('name', ''), "email": email, "role": "customer"},
        "redirect": "/customer"
    })

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Handle logout."""
    session.clear()
    return jsonify({"success": True})

@app.route('/api/auth/me')
@login_required
def api_me():
    """Get current user info."""
    email = session.get('user_email')
    user = users_db.get(email, {})
    return jsonify({
        "id": user.get('id'),
        "name": user.get('name'),
        "email": email,
        "phone": user.get('phone'),
        "city": user.get('city'),
        "plan": user.get('plan'),
        "role": user.get('role'),
        "created_at": user.get('created_at')
    })

# =============================================================================
# ADMIN DASHBOARD ROUTES
# =============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin QA dashboard page."""
    return render_template('dashboard/templates/dashboard.html')


# Admin API Endpoints (existing functionality)
@app.route('/api/admin/overview')
@admin_required
def api_overview():
    """API endpoint for overview metrics."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['overview'])

@app.route('/api/admin/pillars')
@admin_required
def api_pillars():
    """API endpoint for pillar analysis."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['pillar_analysis'])

@app.route('/api/admin/agents')
@admin_required
def api_agents():
    """API endpoint for agent leaderboard."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['agent_performance'])

@app.route('/api/admin/cities')
@admin_required
def api_cities():
    """API endpoint for city performance."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['city_performance'])


@app.route('/api/admin/risks')
@admin_required
def api_risks():
    """API endpoint for risk summary."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['risk_summary'])

@app.route('/api/admin/coaching')
@admin_required
def api_coaching():
    """API endpoint for coaching priorities."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report['coaching_priorities'])

@app.route('/api/admin/calls')
@admin_required
def api_admin_calls():
    """API endpoint for all evaluated calls."""
    calls = []
    for eval in all_evaluations:
        calls.append({
            'call_id': eval['metadata']['call_id'],
            'agent_name': eval['metadata']['agent_name'],
            'city': eval['metadata']['city'],
            'timestamp': eval['metadata']['timestamp'],
            'score': eval['overall']['score'],
            'grade': eval['overall']['grade'],
            'needs_review': eval['overall']['needs_supervisor_review'],
            'alerts': len(eval.get('supervisor_alerts', []))
        })
    return jsonify(calls)

@app.route('/api/admin/call/<call_id>')
@admin_required
def api_admin_call_detail(call_id):
    """API endpoint for detailed call evaluation."""
    for eval in all_evaluations:
        if eval['metadata']['call_id'] == call_id:
            return jsonify(eval)
    return jsonify({'error': 'Call not found'}), 404

@app.route('/api/admin/full-report')
@admin_required
def api_full_report():
    """API endpoint for full analytics report."""
    report = analytics_engine.generate_analytics_report()
    return jsonify(report)

# Legacy API routes for backward compatibility (admin dashboard)
@app.route('/api/overview')
@admin_required
def api_overview_legacy():
    return api_overview()

@app.route('/api/pillars')
@admin_required
def api_pillars_legacy():
    return api_pillars()

@app.route('/api/agents')
@admin_required
def api_agents_legacy():
    return api_agents()

@app.route('/api/cities')
@admin_required
def api_cities_legacy():
    return api_cities()


@app.route('/api/risks')
@admin_required
def api_risks_legacy():
    return api_risks()

@app.route('/api/coaching')
@admin_required
def api_coaching_legacy():
    return api_coaching()

@app.route('/api/calls')
@admin_required
def api_calls_legacy():
    return api_admin_calls()

@app.route('/api/call/<call_id>')
@admin_required
def api_call_detail_legacy(call_id):
    return api_admin_call_detail(call_id)

@app.route('/api/full-report')
@admin_required
def api_full_report_legacy():
    return api_full_report()

# =============================================================================
# CUSTOMER DASHBOARD ROUTES
# =============================================================================

@app.route('/customer')
@customer_required
def customer_dashboard():
    """Customer portal page."""
    return render_template('customer_dashboard/templates/customer.html')

@app.route('/customer/static/<path:filename>')
def customer_static(filename):
    """Serve customer static files."""
    return send_from_directory(os.path.join(BASE_DIR, 'customer_dashboard', 'static'), filename)


# Customer Profile API
@app.route('/api/customer/profile', methods=['GET', 'PUT'])
@customer_required
def api_profile():
    """Get or update user profile."""
    email = session.get('user_email')
    user = users_db.get(email)
    
    if request.method == 'GET':
        return jsonify(user)
    
    data = request.get_json()
    if 'name' in data:
        user['name'] = data['name']
        session['user_name'] = data['name']
    if 'phone' in data:
        user['phone'] = data['phone']
    if 'city' in data:
        user['city'] = data['city']
    
    return jsonify({"success": True, "user": user})

# Customer Chat API
@app.route('/api/customer/chat', methods=['POST'])
@customer_required
def api_chat():
    """Handle chatbot messages."""
    data = request.get_json()
    message = data.get('message', '').lower()
    user_id = session.get('user_id')
    
    if user_id not in chat_history_db:
        chat_history_db[user_id] = []
    
    response = generate_chat_response(message)
    
    chat_history_db[user_id].append({
        "user": data.get('message', ''),
        "bot": response,
        "time": datetime.now().strftime("%H:%M")
    })
    
    return jsonify({
        "response": response,
        "timestamp": datetime.now().strftime("%H:%M")
    })

def generate_chat_response(message):
    """Generate rule-based chatbot responses."""
    message = message.lower()
    
    if any(word in message for word in ['battery', 'locked', 'unlock', 'swap']):
        return "I understand you're having a battery issue. Can you please provide your battery ID (found on the battery label)? I'll check its status immediately."
    
    if any(word in message for word in ['bill', 'charge', 'refund', 'payment', 'money']):
        return "For billing inquiries, I'll need to verify your account. Your last transaction was ₹299 on Jan 15, 2024. Is this the charge you're asking about?"
    
    if any(word in message for word in ['subscription', 'plan', 'upgrade', 'cancel']):
        return "Your current plan is Pro (₹2,999/month, 60 swaps). Would you like to upgrade to Premium (unlimited swaps) or need help with something else?"
    
    if any(word in message for word in ['station', 'near', 'location', 'find']):
        return "The nearest Battery Smart station to your registered location is at MG Road (0.5 km away). It currently has 8 charged batteries available."
    
    if any(word in message for word in ['hi', 'hello', 'hey', 'good']):
        return "Hello! 👋 Welcome to Battery Smart support. How can I help you today?"
    
    if any(word in message for word in ['help', 'support', 'issue', 'problem']):
        return "I'm here to help! Please describe your issue or choose from:\n1️⃣ Battery problems\n2️⃣ Billing questions\n3️⃣ Subscription changes\n4️⃣ Find stations"
    
    if any(word in message for word in ['call', 'speak', 'agent', 'human']):
        return "I can help you schedule a call with our support team. Click on 'Schedule Call' tab to pick a convenient time slot."
    
    return "I'm here to help with Battery Smart services. Could you please provide more details about your query?"

# Customer Call Scheduling API
@app.route('/api/customer/schedule-call', methods=['GET', 'POST'])
@customer_required
def api_schedule_call():
    """Handle call scheduling."""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        return jsonify(scheduled_calls_db.get(user_id, []))
    
    data = request.get_json()
    call_id = f"SCH-{uuid.uuid4().hex[:8].upper()}"
    
    scheduled_call = {
        "id": call_id,
        "date": data.get('date'),
        "time": data.get('time'),
        "phone": data.get('phone'),
        "issue": data.get('issue', 'General inquiry'),
        "status": "scheduled",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if user_id not in scheduled_calls_db:
        scheduled_calls_db[user_id] = []
    scheduled_calls_db[user_id].append(scheduled_call)
    
    if user_id not in notifications_db:
        notifications_db[user_id] = []
    notifications_db[user_id].insert(0, {
        "id": f"NTF-{uuid.uuid4().hex[:8]}",
        "type": "success",
        "message": f"Call scheduled for {data.get('date')} at {data.get('time')}",
        "read": False,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify({"success": True, "call": scheduled_call})

@app.route('/api/customer/simulate-call/<call_id>', methods=['POST'])
@customer_required
def api_simulate_call(call_id):
    """Simulate a call."""
    user_id = session.get('user_id')
    
    transcript = """Agent: Thank you for calling Battery Smart. I'm your AI assistant. How may I help you today?

Customer: Hi, I scheduled this call about a battery issue.

Agent: I'd be happy to help! Can you please describe the issue you're facing?

Customer: My battery wouldn't unlock at the station yesterday.

Agent: I apologize for the inconvenience. Let me check your account... I can see there was a temporary issue. It's been resolved now.

Agent: As a goodwill gesture, I've added ₹50 credit to your wallet. Is there anything else I can help with?

Customer: No, that's all. Thanks!

Agent: You're welcome! Thank you for choosing Battery Smart. Have a great day!"""
    
    new_call = {
        "id": f"CALL-{uuid.uuid4().hex[:6].upper()}",
        "type": "call",
        "subject": "Scheduled call - Support inquiry",
        "status": "completed",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration": 180,
        "satisfaction_score": None,
        "transcript": transcript,
        "needs_feedback": True
    }
    
    if user_id not in call_logs_db:
        call_logs_db[user_id] = []
    call_logs_db[user_id].insert(0, new_call)
    
    return jsonify({
        "success": True,
        "call_id": new_call["id"],
        "transcript": transcript,
        "duration": 180
    })

# Customer Call Logs API
@app.route('/api/customer/call-logs')
@customer_required
def api_call_logs():
    """Get call logs for current user."""
    user_id = session.get('user_id')
    return jsonify(call_logs_db.get(user_id, []))

@app.route('/api/customer/call-logs/<call_id>')
@customer_required
def api_call_detail(call_id):
    """Get detailed call info."""
    user_id = session.get('user_id')
    logs = call_logs_db.get(user_id, [])
    
    for log in logs:
        if log['id'] == call_id:
            return jsonify(log)
    
    return jsonify({"error": "Call not found"}), 404

# Customer Feedback API
@app.route('/api/customer/feedback', methods=['POST'])
@customer_required
def api_feedback():
    """Submit feedback for a call."""
    data = request.get_json()
    user_id = session.get('user_id')
    call_id = data.get('call_id')
    
    logs = call_logs_db.get(user_id, [])
    for log in logs:
        if log['id'] == call_id:
            log['satisfaction_score'] = data.get('rating')
            log['feedback_tags'] = data.get('tags', [])
            log['feedback_comment'] = data.get('comment', '')
            log['needs_feedback'] = False
            break
    
    feedback_db.append({
        "user_id": user_id,
        "call_id": call_id,
        "rating": data.get('rating'),
        "tags": data.get('tags', []),
        "comment": data.get('comment', ''),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify({"success": True})

# Customer Tickets API
@app.route('/api/customer/tickets', methods=['GET', 'POST'])
@customer_required
def api_tickets():
    """Handle tickets/issues."""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        return jsonify(tickets_db.get(user_id, []))
    
    data = request.get_json()
    ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
    
    new_ticket = {
        "id": ticket_id,
        "subject": data.get('subject'),
        "category": data.get('category', 'general'),
        "status": "open",
        "priority": data.get('priority', 'medium'),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": data.get('description', ''),
        "history": [
            {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": "Ticket created"}
        ]
    }
    
    if user_id not in tickets_db:
        tickets_db[user_id] = []
    tickets_db[user_id].insert(0, new_ticket)
    
    return jsonify({"success": True, "ticket": new_ticket})

# Customer Notifications API
@app.route('/api/customer/notifications')
@customer_required
def api_notifications():
    """Get notifications for current user."""
    user_id = session.get('user_id')
    return jsonify(notifications_db.get(user_id, []))

@app.route('/api/customer/notifications/mark-read', methods=['POST'])
@customer_required
def api_mark_notifications_read():
    """Mark notifications as read."""
    user_id = session.get('user_id')
    data = request.get_json()
    notification_ids = data.get('ids', [])
    
    notifications = notifications_db.get(user_id, [])
    for notif in notifications:
        if notif['id'] in notification_ids or 'all' in notification_ids:
            notif['read'] = True
    
    return jsonify({"success": True})

@app.route('/api/customer/notifications/unread-count')
@customer_required
def api_unread_count():
    """Get unread notification count."""
    user_id = session.get('user_id')
    notifications = notifications_db.get(user_id, [])
    count = sum(1 for n in notifications if not n.get('read', True))
    return jsonify({"count": count})

# Legacy customer API routes (for backward compatibility)
@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def api_profile_legacy():
    """Get or update user profile (works for both admin and customer)."""
    email = session.get('user_email')
    user = users_db.get(email)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if request.method == 'GET':
        return jsonify(user)
    
    data = request.get_json()
    if 'name' in data:
        user['name'] = data['name']
        session['user_name'] = data['name']
    if 'phone' in data:
        user['phone'] = data['phone']
    if 'city' in data:
        user['city'] = data['city']
    
    return jsonify({"success": True, "user": user})


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat_legacy():
    if session.get('user_role') == 'customer':
        return api_chat()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/schedule-call', methods=['GET', 'POST'])
@login_required
def api_schedule_call_legacy():
    if session.get('user_role') == 'customer':
        return api_schedule_call()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/simulate-call/<call_id>', methods=['POST'])
@login_required
def api_simulate_call_legacy(call_id):
    if session.get('user_role') == 'customer':
        return api_simulate_call(call_id)
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/call-logs')
@login_required
def api_call_logs_legacy():
    if session.get('user_role') == 'customer':
        return api_call_logs()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/feedback', methods=['POST'])
@login_required
def api_feedback_legacy():
    if session.get('user_role') == 'customer':
        return api_feedback()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/tickets', methods=['GET', 'POST'])
@login_required
def api_tickets_legacy():
    if session.get('user_role') == 'customer':
        return api_tickets()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/notifications')
@login_required
def api_notifications_legacy():
    if session.get('user_role') == 'customer':
        return api_notifications()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def api_mark_read_legacy():
    if session.get('user_role') == 'customer':
        return api_mark_notifications_read()
    return jsonify({"error": "Access denied"}), 403

@app.route('/api/notifications/unread-count')
@login_required
def api_unread_count_legacy():
    if session.get('user_role') == 'customer':
        return api_unread_count()
    return jsonify({"error": "Access denied"}), 403

# =============================================================================
# STATIC FILE SERVING
# =============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Fallback static file serving."""
    # Try customer dashboard first
    customer_path = f'customer_dashboard/static/{filename}'
    if os.path.exists(customer_path):
        return app.send_static_file(customer_path)
    # Then admin dashboard
    admin_path = f'dashboard/static/{filename}'
    if os.path.exists(admin_path):
        return app.send_static_file(admin_path)
    return "File not found", 404

# =============================================================================
# ADMIN DASHBOARD API ENDPOINTS
# =============================================================================

@app.route('/api/evaluations')
@admin_required
def api_evaluations():
    """Get all voice call evaluations for admin dashboard."""
    try:
        # Return voice call evaluations in descending order (newest first)
        evaluations_summary = []
        
        for eval_data in voice_call_evaluations:
            evaluations_summary.append({
                'evaluation_id': eval_data.get('evaluation_id'),
                'call_id': eval_data['metadata']['call_id'],
                'agent_name': eval_data['metadata']['agent_name'],
                'agent_id': eval_data['metadata']['agent_id'],
                'city': eval_data['metadata']['city'],
                'timestamp': eval_data['metadata']['timestamp'],
                'duration': eval_data.get('session_data', {}).get('duration_seconds', 0),
                'overall_score': eval_data['overall']['score'],
                'grade': eval_data['overall']['grade'],
                'needs_review': eval_data['overall']['needs_supervisor_review'],
                'pillar_scores': {
                    'script_adherence': eval_data['pillar_scores']['script_adherence']['score'],
                    'resolution_correctness': eval_data['pillar_scores']['resolution_correctness']['score'],
                    'sentiment_handling': eval_data['pillar_scores']['sentiment_handling']['score'],
                    'communication_quality': eval_data['pillar_scores']['communication_quality']['score'],
                    'risk_compliance': eval_data['pillar_scores']['risk_compliance']['score']
                },
                'sentiment': eval_data['detailed_breakdown']['sentiment_handling'].get('customer_sentiment', 'neutral')
            })
        
        return jsonify({
            'success': True,
            'count': len(evaluations_summary),
            'evaluations': evaluations_summary
        })
    except Exception as e:
        print(f"Error in /api/evaluations: {e}")
        return jsonify({'success': False, 'error': str(e), 'evaluations': []}), 500


@app.route('/api/evaluations/<evaluation_id>')
@admin_required
def api_evaluation_detail(evaluation_id):
    """Get detailed evaluation for a specific call."""
    try:
        for evaluation in voice_call_evaluations:
            if evaluation.get('evaluation_id') == evaluation_id:
                return jsonify({
                    'success': True,
                    'evaluation': evaluation
                })
        
        return jsonify({
            'success': False,
            'error': 'Evaluation not found'
        }), 404
    except Exception as e:
        print(f"Error in /api/evaluations/<id>: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/complaints')
@admin_required
def api_complaints():
    """Get complaints extracted from low-scoring/problematic voice calls."""
    try:
        complaints = []
        complaint_id = 1
        
        for evaluation in voice_call_evaluations:
            # Extract complaints based on criteria:
            # 1. Score < 60 (poor performance)
            # 2. Needs supervisor review
            # 3. Negative sentiment
            
            overall = evaluation['overall']
            score = overall['score']
            needs_review = overall['needs_supervisor_review']
            sentiment_data = evaluation['detailed_breakdown']['sentiment_handling']
            sentiment = sentiment_data.get('customer_sentiment', 'neutral')
            
            # Determine if this is a complaint
            is_complaint = False
            severity = 'low'
            categories = []
            description_parts = []
            
            if score < 60:
                is_complaint = True
                severity = 'high' if score < 40 else 'medium'
                categories.append('Poor Performance')
                description_parts.append(f"Call scored {score}/100 ({overall['grade']})")
            
            if needs_review:
                is_complaint = True
                if severity == 'low':
                    severity = 'medium'
                categories.append('Needs Review')
                
                # Add supervisor alerts
                alerts = evaluation.get('supervisor_alerts', [])
                for alert in alerts:
                    categories.append(alert.get('category', 'Unknown Issue'))
                    description_parts.append(f"{alert['category']}: {alert.get('severity', 'medium')}")
            
            if sentiment == 'negative':
                is_complaint = True
                if severity == 'low':
                    severity = 'medium'
                categories.append('Negative Sentiment')
                description_parts.append("Customer displayed negative sentiment")
            
            if is_complaint:
                # Get areas for improvement
                improvements = evaluation['coaching_insights'].get('areas_for_improvement', [])
                if improvements:
                    description_parts.extend(improvements[:2])  # Top 2 issues
                
                complaints.append({
                    'id': f"COMP-{complaint_id:03d}",
                    'call_id': evaluation['metadata']['call_id'],
                    'evaluation_id': evaluation.get('evaluation_id'),
                    'agent_name': evaluation['metadata']['agent_name'],
                    'customer_name': 'Customer',  # Could extract from session data
                    'category': categories[0] if categories else 'General Issue',
                    'all_categories': categories,
                    'severity': severity,
                    'status': 'open',
                    'timestamp': evaluation['metadata']['timestamp'],
                    'description': '. '.join(description_parts) if description_parts else 'Call flagged for review',
                    'score': score,
                    'sentiment': sentiment
                })
                complaint_id += 1
        
        return jsonify({
            'success': True,
            'count': len(complaints),
            'complaints': complaints
        })
    except Exception as e:
        print(f"Error in /api/complaints: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'complaints': []}), 500

# =============================================================================
# VOICE TRANSCRIPT PROCESSING
# =============================================================================

def process_and_evaluate_transcript(session_data):
    """
    Process voice call transcript through QA evaluation system.
    
    Args:
        session_data: Voice session data with transcript, agent info, etc.
        
    Returns:
        Evaluation results or None if processing fails
    """
    try:
        # Extract formatted transcript
        formatted_transcript = session_data.get('formatted_transcript', '')
        
        print(f"Processing transcript of length: {len(formatted_transcript)}")
        
        if not formatted_transcript:
            print("Warning: No transcript to evaluate (empty string)")
            print(f"Session data keys: {session_data.keys()}")
            return None
        
        # Create metadata from session data
        metadata = CallMetadata(
            call_id=session_data.get('session_id', 'UNKNOWN'),
            agent_id="VOICE-001",  # Voice agent identifier
            agent_name=session_data.get('agent_name', 'Priya'),
            city="Unknown",  # Could extract from user profile
            timestamp=session_data.get('start_time', datetime.now().isoformat()),
            duration_seconds=session_data.get('duration_seconds', 0)
        )
        
        # Run evaluation
        print(f"→ Evaluating voice call: {metadata.call_id} (Duration: {metadata.duration_seconds}s)")
        evaluation = evaluator.evaluate_call(formatted_transcript, metadata)
        
        if not evaluation:
            print("❌ CallEvaluator returned None evaluation")
            return None
            
        # Add session metadata
        evaluation['session_data'] = {
            'session_id': session_data.get('session_id'),
            'start_time': session_data.get('start_time'),
            'end_time': session_data.get('end_time'),
            'duration_seconds': session_data.get('duration_seconds'),
        }
        
        # Add to in-memory list
        voice_call_evaluations.insert(0, evaluation)  # Newest first
        
        # Persist to file
        try:
            with open(evaluations_file, 'w') as f:
                json.dump(voice_call_evaluations, f, indent=2)
            print(f"✓ Saved evaluation: {evaluation['overall']['score']}/100 ({evaluation['overall']['grade']})")
        except Exception as e:
            print(f"Error saving evaluation file: {e}")
        
        # Add to analytics engine
        analytics_engine.add_evaluation(evaluation)
        
        return evaluation
        
    except Exception as e:
        print(f"✗ Error processing transcript evaluation: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_voice_transcript(session_data):
    """Save voice transcript to JSON file and process through QA evaluation."""
    session_id = session_data.get('session_id')
    if not session_id:
        return
    
    # Save transcript file
    transcripts_dir = os.path.join(os.path.dirname(__file__), 'voice_transcripts')
    os.makedirs(transcripts_dir, exist_ok=True)
    file_path = os.path.join(transcripts_dir, f"{session_id}.json")
    
    with open(file_path, 'w') as f:
        json.dump(session_data, f, indent=2)
    print(f"Saved voice transcript: {file_path}")
    
    # Process and evaluate transcript
    evaluation = process_and_evaluate_transcript(session_data)
    
    return evaluation

# =============================================================================
# VOICE AGENT WEBSOCKET HANDLERS
# =============================================================================

@socketio.on('connect')
def handle_voice_connect():
    """Handle new WebSocket connection."""
    print(f"Voice client connected: {request.sid}")
    emit('connected', {'message': 'Connected to Battery Smart Voice Agent'})


@socketio.on('disconnect')
def handle_voice_disconnect():
    """Handle WebSocket disconnection."""
    print(f"Voice client disconnected: {request.sid}")
    
    # End any active session
    if request.sid in voice_socket_sessions:
        session_id = voice_socket_sessions[request.sid].get('session_id')
        if session_id:
            try:
                session_data = voice_session_manager.end_session(session_id)
                print(f"Disconnecting session {session_id}, saving transcript...")
                save_voice_transcript(session_data)
            except Exception as e:
                print(f"Error saving transcript on disconnect: {e}")
                import traceback
                traceback.print_exc()
        del voice_socket_sessions[request.sid]


@socketio.on('start_call')
def handle_start_call(data):
    """Start a new voice call session."""
    print(f"Starting voice call for {request.sid}")
    
    try:
        # Create new session
        session_id, greeting = voice_session_manager.create_session()
        
        # Store session info
        voice_socket_sessions[request.sid] = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'name': data.get('name', 'Customer'),
            'phone': data.get('phone', '')
        }
        
        # Send greeting
        emit('call_started', {
            'session_id': session_id,
            'greeting': greeting
        })
        
        # Generate TTS for greeting if available
        if EDGE_TTS_AVAILABLE and TTSHandler:
            asyncio.run(send_voice_tts_audio(greeting))
        
    except Exception as e:
        print(f"Error starting call: {e}")
        emit('error', {'message': str(e)})


@socketio.on('user_message')
def handle_voice_user_message(data):
    """Process user message (from speech-to-text)."""
    message = data.get('text', '')
    if not message:
        return
    
    session_info = voice_socket_sessions.get(request.sid)
    if not session_info:
        emit('error', {'message': 'No active session'})
        return
    
    session_id = session_info.get('session_id')
    
    try:
        # Get agent response
        response = voice_session_manager.process_message(session_id, message)
        
        # Send response
        emit('agent_response', {
            'text': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Generate TTS if available
        if EDGE_TTS_AVAILABLE and TTSHandler:
            asyncio.run(send_voice_tts_audio(response))
        
    except Exception as e:
        print(f"Error processing voice message: {e}")
        emit('error', {'message': str(e)})


@socketio.on('end_call')
def handle_end_call(data):
    """End the current voice call."""
    session_info = voice_socket_sessions.get(request.sid)
    if not session_info:
        emit('error', {'message': 'No active session'})
        return
    
    session_id = session_info.get('session_id')
    
    try:
        # End session and get data
        session_data = voice_session_manager.end_session(session_id)
        
        # Save transcript
        save_voice_transcript(session_data)
        
        # Clean up socket session
        del voice_socket_sessions[request.sid]
        
        # Send confirmation
        emit('call_ended', {
            'session_id': session_id,
            'duration_seconds': session_data.get('duration_seconds'),
            'transcript': session_data.get('formatted_transcript')
        })
        
    except Exception as e:
        print(f"Error ending call: {e}")
        emit('error', {'message': str(e)})


# =============================================================================
# VOICE AGENT HELPER FUNCTIONS
# =============================================================================

async def send_voice_tts_audio(text: str):
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


def save_voice_transcript(session_data: dict):
    """Save transcript to file."""
    session_id = session_data.get('session_id')
    if not session_id:
        return
    
    file_path = os.path.join(voice_transcripts_dir, f"{session_id}.json")
    with open(file_path, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"Saved voice transcript: {file_path}")


# =============================================================================
# VOICE AGENT API ROUTES
# =============================================================================

# In-memory storage for voice call logs (persisted to file on shutdown)
voice_call_logs = []
voice_call_logs_file = os.path.join(BASE_DIR, 'voice_call_logs.json')

# Load existing voice call logs on startup
if os.path.exists(voice_call_logs_file):
    try:
        with open(voice_call_logs_file, 'r') as f:
            voice_call_logs = json.load(f)
    except:
        voice_call_logs = []


@app.route('/api/voice/status')
def voice_status():
    """Get voice agent status."""
    return jsonify({
        "status": "online",
        "gemini_available": bool(os.getenv('GEMINI_API_KEY')),
        "tts_available": EDGE_TTS_AVAILABLE,
        "active_sessions": len(voice_socket_sessions)
    })


@app.route('/api/voice-call-log', methods=['POST'])
@customer_required
def save_voice_call_log():
    """Save a voice call log with feedback."""
    data = request.json
    
    # Add user info
    data['user_email'] = session.get('email')
    
    # Add to logs
    voice_call_logs.insert(0, data)  # Add to beginning (newest first)
    
    # Persist to file
    try:
        with open(voice_call_logs_file, 'w') as f:
            json.dump(voice_call_logs, f, indent=2)
    except Exception as e:
        print(f"Error saving voice call logs: {e}")
    
    return jsonify({"success": True, "message": "Call log saved"})


@app.route('/api/voice-call-logs')
@customer_required
def get_voice_call_logs():
    """Get voice call logs for current user."""
    user_email = session.get('email')
    
    # Filter logs for current user
    user_logs = [log for log in voice_call_logs if log.get('user_email') == user_email]
    
    return jsonify({
        "success": True,
        "logs": user_logs
    })


@app.route('/api/voice-call-transcript/<call_id>')
@customer_required
def get_voice_call_transcript(call_id):
    """Get transcript for a specific voice call."""
    user_email = session.get('email')
    
    # Find the call log
    for log in voice_call_logs:
        if log.get('id') == call_id and log.get('user_email') == user_email:
            return jsonify({
                "success": True,
                "transcript": log.get('transcript', []),
                "duration": log.get('duration'),
                "rating": log.get('rating'),
                "date": log.get('date')
            })
    
    return jsonify({"success": False, "error": "Transcript not found"}), 404


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Battery Smart Unified Portal")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 60)
    print("\n  Login Credentials:")
    print("  ─────────────────────────────────────────")
    print("  ADMIN:    admin@batterysmart.com / admin123")
    print("  CUSTOMER: demo@batterysmart.com / demo123")
    print("=" * 60)
    print(f"\n  Voice Agent: {'Enabled' if (os.getenv('GROQ_API_KEY') or os.getenv('GEMINI_API_KEY')) else 'API Key Missing'}")
    print(f"  TTS Available: {EDGE_TTS_AVAILABLE}")
    print("=" * 60 + "\n")
    
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)


