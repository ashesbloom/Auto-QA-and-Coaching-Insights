"""
Customer Dashboard Server for Battery Smart
Flask-based web portal for customer interactions.
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import json
from datetime import datetime
import os
import sys
import uuid

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 
            template_folder='customer_dashboard/templates', 
            static_folder='customer_dashboard/static')
app.secret_key = 'battery-smart-secret-key-2024'

# =============================================================================
# IN-MEMORY DATA STORES
# =============================================================================

# Users database (in-memory)
users_db = {
    "demo@batterysmart.com": {
        "id": "USR-001",
        "name": "Demo User",
        "email": "demo@batterysmart.com",
        "password": "demo123",
        "phone": "9876543210",
        "city": "Bangalore",
        "plan": "Pro",
        "created_at": "2024-01-01"
    }
}

# Call logs (in-memory)
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
        },
        {
            "id": "CALL-003",
            "type": "chat",
            "subject": "Station availability",
            "status": "resolved",
            "timestamp": "2024-01-13 09:15:00",
            "duration": 120,
            "satisfaction_score": 4,
            "transcript": "Customer: No batteries available at MG Road...\nAgent: Let me check alternatives..."
        }
    ]
}

# Tickets/Issues (in-memory)
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
    ]
}

# Notifications (in-memory)
notifications_db = {
    "USR-001": [
        {"id": "NTF-001", "type": "info", "message": "Welcome to Battery Smart!", "read": True, "time": "2024-01-01 10:00:00"},
        {"id": "NTF-002", "type": "success", "message": "Your subscription has been renewed", "read": True, "time": "2024-01-10 08:00:00"},
        {"id": "NTF-003", "type": "warning", "message": "Scheduled call reminder for tomorrow 10 AM", "read": False, "time": "2024-01-15 18:00:00"},
        {"id": "NTF-004", "type": "info", "message": "New station opened near your location", "read": False, "time": "2024-01-16 12:00:00"}
    ]
}

# Scheduled calls (in-memory)
scheduled_calls_db = {}

# Feedback (in-memory)
feedback_db = []

# Chat history (in-memory)
chat_history_db = {}

# =============================================================================
# AUTHENTICATION DECORATOR
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# PAGE ROUTES
# =============================================================================

@app.route('/')
def customer_home():
    """Redirect to login or dashboard."""
    if 'user_id' in session:
        return redirect(url_for('customer_dashboard'))
    return redirect(url_for('customer_login'))

@app.route('/login')
def customer_login():
    """Login page."""
    return render_template('customer.html', page='login')

@app.route('/signup')
def customer_signup():
    """Signup page."""
    return render_template('customer.html', page='signup')

@app.route('/dashboard')
@login_required
def customer_dashboard():
    """Main customer dashboard."""
    return render_template('customer.html', page='dashboard')

# =============================================================================
# AUTH API ENDPOINTS
# =============================================================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Handle login."""
    data = request.get_json()
    email = data.get('email', '').lower()
    password = data.get('password', '')
    
    if email in users_db and users_db[email]['password'] == password:
        user = users_db[email]
        session['user_id'] = user['id']
        session['user_email'] = email
        session['user_name'] = user['name']
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": email
            }
        })
    
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    """Handle signup."""
    data = request.get_json()
    email = data.get('email', '').lower()
    
    if email in users_db:
        return jsonify({"success": False, "error": "Email already exists"}), 400
    
    user_id = f"USR-{len(users_db) + 1:03d}"
    users_db[email] = {
        "id": user_id,
        "name": data.get('name', ''),
        "email": email,
        "password": data.get('password', ''),
        "phone": data.get('phone', ''),
        "city": data.get('city', 'Unknown'),
        "plan": "Basic",
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
    
    return jsonify({
        "success": True,
        "user": {"id": user_id, "name": data.get('name', ''), "email": email}
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
        "created_at": user.get('created_at')
    })

# =============================================================================
# PROFILE API
# =============================================================================

@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def api_profile():
    """Get or update user profile."""
    email = session.get('user_email')
    user = users_db.get(email)
    
    if request.method == 'GET':
        return jsonify(user)
    
    # PUT - Update profile
    data = request.get_json()
    if 'name' in data:
        user['name'] = data['name']
        session['user_name'] = data['name']
    if 'phone' in data:
        user['phone'] = data['phone']
    if 'city' in data:
        user['city'] = data['city']
    
    return jsonify({"success": True, "user": user})

# =============================================================================
# CHATBOT API
# =============================================================================

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Handle chatbot messages."""
    data = request.get_json()
    message = data.get('message', '').lower()
    user_id = session.get('user_id')
    
    # Initialize chat history for user
    if user_id not in chat_history_db:
        chat_history_db[user_id] = []
    
    # Simple rule-based responses
    response = generate_chat_response(message)
    
    # Store in history
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
    
    # Battery issues
    if any(word in message for word in ['battery', 'locked', 'unlock', 'swap']):
        return "I understand you're having a battery issue. Can you please provide your battery ID (found on the battery label)? I'll check its status immediately."
    
    # Billing
    if any(word in message for word in ['bill', 'charge', 'refund', 'payment', 'money']):
        return "For billing inquiries, I'll need to verify your account. Your last transaction was ₹299 on Jan 15, 2024. Is this the charge you're asking about?"
    
    # Subscription
    if any(word in message for word in ['subscription', 'plan', 'upgrade', 'cancel']):
        return "Your current plan is Pro (₹2,999/month, 60 swaps). Would you like to upgrade to Premium (unlimited swaps) or need help with something else?"
    
    # Station
    if any(word in message for word in ['station', 'near', 'location', 'find']):
        return "The nearest Battery Smart station to your registered location is at MG Road (0.5 km away). It currently has 8 charged batteries available. Would you like directions?"
    
    # Greeting
    if any(word in message for word in ['hi', 'hello', 'hey', 'good']):
        return "Hello! 👋 Welcome to Battery Smart support. How can I help you today? You can ask about:\n• Battery issues\n• Billing & refunds\n• Subscription plans\n• Station locations"
    
    # Help
    if any(word in message for word in ['help', 'support', 'issue', 'problem']):
        return "I'm here to help! Please describe your issue or choose from:\n1️⃣ Battery problems\n2️⃣ Billing questions\n3️⃣ Subscription changes\n4️⃣ Find stations\n5️⃣ Schedule a call"
    
    # Call request
    if any(word in message for word in ['call', 'speak', 'agent', 'human']):
        return "I can help you schedule a call with our support team. Would you like to schedule now? Click on 'Schedule Call' tab to pick a convenient time slot."
    
    # Default
    return "I'm here to help with Battery Smart services. Could you please provide more details about your query? Or would you prefer to schedule a call with our support team?"

# =============================================================================
# CALL SCHEDULING API
# =============================================================================

@app.route('/api/schedule-call', methods=['GET', 'POST'])
@login_required
def api_schedule_call():
    """Handle call scheduling."""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        # Return scheduled calls
        return jsonify(scheduled_calls_db.get(user_id, []))
    
    # POST - Schedule new call
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
    
    # Add notification
    notifications_db[user_id].insert(0, {
        "id": f"NTF-{uuid.uuid4().hex[:8]}",
        "type": "success",
        "message": f"Call scheduled for {data.get('date')} at {data.get('time')}",
        "read": False,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify({"success": True, "call": scheduled_call})

@app.route('/api/simulate-call/<call_id>', methods=['POST'])
@login_required
def api_simulate_call(call_id):
    """Simulate a call (dummy functionality)."""
    user_id = session.get('user_id')
    
    # Generate mock transcript
    transcript = """Agent: Thank you for calling Battery Smart. I'm Priya. How may I help you today?

Customer: Hi Priya, I scheduled this call about a battery issue.

Agent: I'd be happy to help! Can you please provide your registered phone number for verification?

Customer: Sure, it's 9876543210.

Agent: Thank you for verifying. I can see your account. What issue are you facing with the battery?

Customer: The battery at MG Road station wouldn't unlock yesterday.

Agent: I apologize for the inconvenience. Let me check the system... I can see there was a temporary network issue at that station. It's been resolved now. As a goodwill gesture, I'm adding ₹50 credit to your wallet.

Customer: That's great, thank you!

Agent: Is there anything else I can help you with today?

Customer: No, that's all. Thanks for the quick help!

Agent: You're welcome! Thank you for choosing Battery Smart. Have a great day!"""
    
    # Add to call logs
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

# =============================================================================
# CALL LOGS API
# =============================================================================

@app.route('/api/call-logs')
@login_required
def api_call_logs():
    """Get call logs for current user."""
    user_id = session.get('user_id')
    logs = call_logs_db.get(user_id, [])
    return jsonify(logs)

@app.route('/api/call-logs/<call_id>')
@login_required
def api_call_detail(call_id):
    """Get detailed call info."""
    user_id = session.get('user_id')
    logs = call_logs_db.get(user_id, [])
    
    for log in logs:
        if log['id'] == call_id:
            return jsonify(log)
    
    return jsonify({"error": "Call not found"}), 404

# =============================================================================
# FEEDBACK API
# =============================================================================

@app.route('/api/feedback', methods=['POST'])
@login_required
def api_feedback():
    """Submit feedback for a call."""
    data = request.get_json()
    user_id = session.get('user_id')
    call_id = data.get('call_id')
    
    # Update call log with feedback
    logs = call_logs_db.get(user_id, [])
    for log in logs:
        if log['id'] == call_id:
            log['satisfaction_score'] = data.get('rating')
            log['feedback_tags'] = data.get('tags', [])
            log['feedback_comment'] = data.get('comment', '')
            log['needs_feedback'] = False
            break
    
    # Store feedback
    feedback_db.append({
        "user_id": user_id,
        "call_id": call_id,
        "rating": data.get('rating'),
        "tags": data.get('tags', []),
        "comment": data.get('comment', ''),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify({"success": True})

# =============================================================================
# TICKETS/ISSUES API
# =============================================================================

@app.route('/api/tickets', methods=['GET', 'POST'])
@login_required
def api_tickets():
    """Handle tickets/issues."""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        return jsonify(tickets_db.get(user_id, []))
    
    # POST - Create new ticket
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

@app.route('/api/tickets/<ticket_id>')
@login_required
def api_ticket_detail(ticket_id):
    """Get ticket details."""
    user_id = session.get('user_id')
    tickets = tickets_db.get(user_id, [])
    
    for ticket in tickets:
        if ticket['id'] == ticket_id:
            return jsonify(ticket)
    
    return jsonify({"error": "Ticket not found"}), 404

# =============================================================================
# NOTIFICATIONS API
# =============================================================================

@app.route('/api/notifications')
@login_required
def api_notifications():
    """Get notifications for current user."""
    user_id = session.get('user_id')
    return jsonify(notifications_db.get(user_id, []))

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
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

@app.route('/api/notifications/unread-count')
@login_required
def api_unread_count():
    """Get unread notification count."""
    user_id = session.get('user_id')
    notifications = notifications_db.get(user_id, [])
    count = sum(1 for n in notifications if not n.get('read', True))
    return jsonify({"count": count})

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  Battery Smart Customer Portal")
    print("  Open http://localhost:5001 in your browser")
    print("  Demo login: demo@batterysmart.com / demo123")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5001)
