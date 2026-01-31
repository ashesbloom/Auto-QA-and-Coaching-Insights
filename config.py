"""
Auto-QA System Configuration
Comprehensive configuration for Battery Smart call evaluation.
Includes scoring weights, keywords, SOPs, and complaint categories.
"""

# =============================================================================
# SCORING WEIGHTS (Five-Pillar Framework)
# =============================================================================
PILLAR_WEIGHTS = {
    "script_adherence": 0.30,       # 30% - Greeting, identity verification, closure
    "resolution_correctness": 0.30,  # 30% - SOP alignment, policy compliance
    "sentiment_handling": 0.20,      # 20% - De-escalation, empathy signals
    "communication_quality": 0.10,   # 10% - Clarity, tone, professionalism
    "risk_compliance": 0.10          # 10% - Red flags, violation tracking
}

# =============================================================================
# BATTERY SMART COMPLAINT CATEGORIES
# =============================================================================
COMPLAINT_CATEGORIES = {
    "battery_issues": {
        "name": "Battery Issues",
        "keywords": [
            "battery locked", "can't unlock", "locked out", "battery is locked",
            "not charging", "won't charge", "charge problem", "low charge",
            "battery drain", "draining fast", "battery dead", "no power",
            "overheating", "battery hot", "heating up", "warm battery",
            "low capacity", "range reduced", "less range", "short range",
            "battery damaged", "swollen battery", "battery not working"
        ],
        "priority": "high"
    },
    "swap_station_issues": {
        "name": "Swap Station Issues",
        "keywords": [
            "swap failed", "couldn't swap", "station error", "swap not working",
            "station offline", "station down", "station closed",
            "no batteries available", "all slots empty", "no charged batteries",
            "slot jammed", "can't insert", "can't remove", "stuck battery",
            "card reader not working", "payment failed at station", "machine error",
            "wrong station", "station location wrong", "can't find station"
        ],
        "priority": "high"
    },
    "billing_issues": {
        "name": "Billing & Payment Issues",
        "keywords": [
            "wrong charge", "overcharged", "charged twice", "double billing",
            "refund", "money back", "incorrect amount", "extra charge",
            "subscription issue", "plan not applied", "wrong plan",
            "payment failed", "transaction failed", "couldn't pay",
            "invoice wrong", "receipt missing", "bill not received",
            "wallet balance", "promocode not applied", "discount missing"
        ],
        "priority": "medium"
    },
    "app_issues": {
        "name": "App & Technical Issues",
        "keywords": [
            "app not working", "app crash", "app frozen", "login issue",
            "can't login", "otp not received", "password reset",
            "location not updating", "gps issue", "wrong location shown",
            "notification not received", "push notification", 
            "app update issue", "old version", "compatibility",
            "profile update", "can't edit details", "account locked"
        ],
        "priority": "medium"
    },
    "subscription_issues": {
        "name": "Subscription & Plan Issues",
        "keywords": [
            "cancel subscription", "subscription cancellation", "end subscription",
            "change plan", "upgrade plan", "downgrade plan",
            "subscription not active", "plan expired", "renew subscription",
            "auto-renewal", "recurring charge", "subscription charge",
            "plan benefits", "what's included", "plan comparison"
        ],
        "priority": "medium"
    },
    "delivery_issues": {
        "name": "Home Delivery Issues",
        "keywords": [
            "delivery late", "not delivered", "wrong address",
            "delivery person", "rider issue", "battery delivery",
            "scheduled delivery", "reschedule delivery", "cancel delivery",
            "delivery tracking", "where is my battery", "delivery status"
        ],
        "priority": "medium"
    },
    "vehicle_compatibility": {
        "name": "Vehicle Compatibility Issues",
        "keywords": [
            "battery not fitting", "wrong battery type", "incompatible",
            "vehicle model", "which battery", "battery for my vehicle",
            "connector issue", "terminal problem", "doesn't connect",
            "voltage mismatch", "capacity mismatch"
        ],
        "priority": "low"
    },
    "service_quality": {
        "name": "Service Quality Complaints",
        "keywords": [
            "rude staff", "unprofessional", "bad service", "poor service",
            "long wait", "waiting too long", "slow service",
            "wrong information", "misinformed", "lied to me",
            "not helpful", "didn't help", "ignored my complaint",
            "previous complaint", "complaint not resolved", "follow up"
        ],
        "priority": "high"
    },
    "safety_concerns": {
        "name": "Safety & Emergency Issues",
        "keywords": [
            "fire", "smoke", "sparks", "burning smell", "explosion",
            "electric shock", "electrocuted", "shock hazard",
            "dangerous", "safety issue", "emergency", "accident",
            "injury", "hurt", "burn", "damaged vehicle"
        ],
        "priority": "critical"
    },
    "general_inquiry": {
        "name": "General Inquiries",
        "keywords": [
            "how to", "how does", "what is", "explain",
            "pricing", "cost", "rates", "charges",
            "nearest station", "station location", "find station",
            "working hours", "opening time", "closing time",
            "registration", "new user", "sign up", "create account"
        ],
        "priority": "low"
    }
}

# =============================================================================
# SCRIPT ADHERENCE CONFIGURATION
# =============================================================================
REQUIRED_SCRIPT_ELEMENTS = {
    "greeting": {
        "keywords": [
            "thank you for calling battery smart",
            "welcome to battery smart",
            "good morning", "good afternoon", "good evening",
            "how may i help you", "how can i assist you",
            "battery smart customer support", "namaste"
        ],
        "points": 25,
        "description": "Opening greeting"
    },
    "identity_verification": {
        "keywords": [
            "phone number", "mobile number", "registered number",
            "battery id", "customer id", "account number",
            "verify your", "confirm your", "can you provide",
            "registered email", "your name please"
        ],
        "points": 35,
        "description": "Customer verification"
    },
    "closing": {
        "keywords": [
            "anything else", "further assistance",
            "thank you for calling", "have a great day",
            "is there anything else", "happy to help",
            "thank you for choosing battery smart"
        ],
        "points": 25,
        "description": "Closing script"
    },
    "problem_acknowledgment": {
        "keywords": [
            "i understand", "i apologize", "sorry for the inconvenience",
            "let me help", "i can help you with that",
            "i will look into this", "let me check"
        ],
        "points": 15,
        "description": "Problem acknowledgment"
    }
}

# =============================================================================
# RESOLUTION CORRECTNESS - BATTERY SMART SOPs
# =============================================================================
BATTERY_SMART_SOPS = {
    "locked_battery": {
        "issue_keywords": ["battery locked", "can't unlock", "locked out", "battery is locked"],
        "required_steps": [
            "ask for battery id",
            "check system status",
            "provide unlock code or escalate"
        ],
        "correct_responses": [
            "unlock code", "reset the battery", "visit nearest station",
            "escalate to technical team", "remote unlock", "otp sent"
        ],
        "resolution_time": "immediate"
    },
    "refund_request": {
        "issue_keywords": ["refund", "money back", "charged wrongly", "wrong charge", "double billing", "overcharged"],
        "required_steps": [
            "verify transaction details",
            "check refund eligibility",
            "process or explain policy"
        ],
        "correct_responses": [
            "refund will be processed", "3-5 business days", "7 working days",
            "not eligible because", "refund policy states", "credited to your wallet",
            "bank account", "original payment method"
        ],
        "resolution_time": "3-7 days"
    },
    "swap_failure": {
        "issue_keywords": ["swap failed", "couldn't swap", "station error", "swap not working", "slot jammed"],
        "required_steps": [
            "get station id",
            "log the issue",
            "provide alternative"
        ],
        "correct_responses": [
            "try station", "alternative station", "reported to operations",
            "technical team will check", "nearest station at", "station id noted",
            "free swap credit"
        ],
        "resolution_time": "immediate"
    },
    "charging_issue": {
        "issue_keywords": ["not charging", "charge problem", "battery drain", "low charge", "draining fast"],
        "required_steps": [
            "check battery health",
            "verify usage patterns",
            "recommend solution"
        ],
        "correct_responses": [
            "swap for new battery", "battery health", "charging station",
            "normal usage", "replacement", "diagnostic", "health check"
        ],
        "resolution_time": "same day"
    },
    "overheating": {
        "issue_keywords": ["overheating", "battery hot", "heating up", "warm battery", "sparks", "smoke"],
        "required_steps": [
            "document the issue",
            "safety instructions",
            "escalate to safety team"
        ],
        "correct_responses": [
            "stop using immediately", "do not charge", "safety team",
            "escalating to safety", "replacement", "priority", "callback within"
        ],
        "resolution_time": "2 hours (priority)"
    },
    "subscription_change": {
        "issue_keywords": ["cancel subscription", "change plan", "upgrade", "downgrade", "plan expired"],
        "required_steps": [
            "verify current plan",
            "explain options",
            "process change"
        ],
        "correct_responses": [
            "current plan is", "upgrade to", "downgrade to", "plan benefits",
            "effective from", "prorated", "cancellation processed"
        ],
        "resolution_time": "immediate"
    },
    "app_login": {
        "issue_keywords": ["can't login", "login issue", "otp not received", "password reset", "account locked"],
        "required_steps": [
            "verify identity",
            "check account status",
            "reset or unlock"
        ],
        "correct_responses": [
            "sending otp", "password reset link", "account unlocked",
            "try again", "clear cache", "reinstall app", "update app"
        ],
        "resolution_time": "immediate"
    },
    "station_locator": {
        "issue_keywords": ["nearest station", "find station", "station location", "where is station"],
        "required_steps": [
            "get current location",
            "check nearby stations",
            "provide directions"
        ],
        "correct_responses": [
            "nearest station is", "km away", "directions", "open until",
            "available batteries", "app will show", "google maps"
        ],
        "resolution_time": "immediate"
    }
}

# =============================================================================
# SENTIMENT ANALYSIS KEYWORDS
# =============================================================================
SENTIMENT_KEYWORDS = {
    "positive": [
        "thank you", "thanks", "great", "excellent", "helpful",
        "appreciate", "wonderful", "perfect", "awesome", "good job",
        "satisfied", "happy", "pleased", "amazing", "fantastic",
        "resolved", "fixed", "working now", "problem solved"
    ],
    "negative": [
        "angry", "frustrated", "upset", "terrible", "worst",
        "unacceptable", "ridiculous", "pathetic", "useless", "waste",
        "disappointed", "annoyed", "horrible", "disgusted", "fed up",
        "sick of", "tired of", "enough", "last straw"
    ],
    "escalation_signals": [
        "manager", "supervisor", "escalate", "higher authority",
        "not acceptable", "speak to someone else", "complaint",
        "consumer forum", "social media", "twitter", "review"
    ],
    "empathy_phrases": [
        "i understand", "i apologize", "sorry to hear",
        "i can imagine", "that must be frustrating",
        "let me help you", "i'm here to help",
        "i completely understand", "thank you for your patience"
    ]
}

# =============================================================================
# COMMUNICATION QUALITY INDICATORS
# =============================================================================
COMMUNICATION_QUALITY = {
    "positive_indicators": [
        "certainly", "absolutely", "of course", "happy to help",
        "let me explain", "to clarify", "in simple terms",
        "great question", "good point", "definitely"
    ],
    "negative_indicators": [
        "i don't know", "not my job", "you should have",
        "as i said before", "i already told you", "that's not possible",
        "you're wrong", "calm down", "relax", "whatever"
    ],
    "jargon_to_avoid": [
        "sop", "backend", "api", "system error code",
        "escalation matrix", "ticket id", "crm", "lifecycle",
        "sla", "tat", "nps"
    ],
    "interruption_patterns": [
        "let me finish", "i was saying", "you interrupted",
        "please let me complete", "hold on", "wait"
    ]
}

# =============================================================================
# RISK & COMPLIANCE DETECTION
# =============================================================================
RISK_FLAGS = {
    "legal_threats": {
        "keywords": [
            "sue", "lawyer", "legal action", "court", "consumer forum",
            "legal notice", "police", "fir", "complaint against",
            "consumer rights", "ombudsman"
        ],
        "severity": "critical",
        "requires_supervisor": True
    },
    "safety_issues": {
        "keywords": [
            "exploded", "fire", "burn", "shock", "electrocuted",
            "smoke", "sparks", "overheating", "dangerous", "injury",
            "accident", "hurt"
        ],
        "severity": "critical",
        "requires_supervisor": True
    },
    "abuse_harassment": {
        "keywords": [
            "idiot", "stupid", "fool", "useless person",
            "threatening", "will find you", "curse words"
        ],
        "severity": "critical",
        "requires_supervisor": True
    },
    "churn_risk": {
        "keywords": [
            "cancel subscription", "switch to", "competitor",
            "never use again", "done with battery smart", "closing account",
            "ather", "ola", "bounce", "yulu"  # Competitor names
        ],
        "severity": "high",
        "requires_supervisor": False
    },
    "compliance_violation": {
        "keywords": [
            "give you discount", "special offer just for you",
            "don't tell anyone", "between us", "i'll waive the fee",
            "off the record", "personal favor"
        ],
        "severity": "high",
        "requires_supervisor": True
    },
    "media_threat": {
        "keywords": [
            "twitter", "facebook", "social media", "viral",
            "news", "media", "influencer", "youtube", "instagram"
        ],
        "severity": "medium",
        "requires_supervisor": False
    }
}

# =============================================================================
# SCORING THRESHOLDS
# =============================================================================
SCORE_THRESHOLDS = {
    "excellent": 90,
    "good": 75,
    "needs_improvement": 60,
    "poor": 40
}

SUPERVISOR_ALERT_THRESHOLD = 50  # Calls scoring below this trigger review

# =============================================================================
# ANALYTICS CONFIGURATION
# =============================================================================
ANALYTICS_CONFIG = {
    "time_periods": ["daily", "weekly", "monthly"],
    "trend_thresholds": {
        "improving": 5,    # Score increased by 5+ points
        "declining": -5    # Score decreased by 5+ points
    },
    "coaching_triggers": {
        "low_script_threshold": 60,     # Below this triggers script coaching
        "low_empathy_threshold": 50,    # Below this triggers empathy coaching
        "low_resolution_threshold": 60  # Below this triggers SOP training
    }
}
