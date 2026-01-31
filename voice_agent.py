"""
Battery Smart Voice Agent
AI-powered voice assistant for customer support using Gemini LLM.
Follows Battery Smart SOPs for consistent, professional responses.
"""

import os
import json
from datetime import datetime
import uuid
from typing import Dict, List, Optional
import sys

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    BATTERY_SMART_SOPS,
    REQUIRED_SCRIPT_ELEMENTS,
    COMPLAINT_CATEGORIES,
    SENTIMENT_KEYWORDS
)

# Try to import Groq (preferred) or Gemini (fallback)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: groq not installed. Run: pip install groq")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class VoiceAgent:
    """
    Battery Smart Voice Agent powered by Groq/Llama LLM.
    Handles customer support conversations following company SOPs.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the voice agent.
        
        Args:
            api_key: Groq or Gemini API key. If not provided, reads from env vars.
        """
        # Try Groq first (faster and more reliable)
        self.groq_key = api_key or os.getenv('GROQ_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        self.client = None
        self.model_type = None
        self.chat_session = None
        self.session_id = None
        self.transcript = []
        self.start_time = None
        self.agent_name = "Priya"
        self.conversation_history = []
        
        if GROQ_AVAILABLE and self.groq_key:
            self._initialize_groq()
        elif GEMINI_AVAILABLE and self.gemini_key:
            self._initialize_gemini()
        else:
            print("⚠ No API available, using fallback responses only")
    
    def _initialize_groq(self):
        """Initialize Groq client with Llama model."""
        try:
            self.client = Groq(api_key=self.groq_key)
            self.model_type = 'groq'
            self.model_name = 'openai/gpt-oss-120b'  # Fast and accurate
            print(f"✓ Groq client initialized with model: {self.model_name}")
        except Exception as e:
            print(f"✗ Failed to initialize Groq: {e}")
            self.client = None
    
    def _initialize_gemini(self):
        """Initialize Gemini model with Battery Smart system prompt."""
        try:
            genai.configure(api_key=self.gemini_key)
            
            # Use Gemini 1.5 Flash Latest for best stability and speed
            model_name = 'gemini-1.5-flash-latest'
            
            # Configure generation parameters for consistent, helpful responses
            generation_config = {
                'temperature': 0.7,  # Balanced creativity and consistency
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 200,  # Keep responses concise for voice
            }
            
            print(f"Initializing Gemini model: {model_name}")
            self.model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=self._build_system_prompt(),
                generation_config=generation_config
            )
            self.model_type = 'gemini'
            print("✓ Gemini model initialized successfully")
        except Exception as e:
            print(f"✗ Failed to initialize Gemini: {e}")
            self.model = None
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt from Battery Smart SOPs."""
        
        system_prompt = f"""You are {self.agent_name}, Battery Smart's AI customer support agent.

## YOUR ROLE
You help customers with battery swap services, subscriptions, and technical issues. Be friendly, helpful, and concise.

## CORE SERVICES
**Battery Swapping:**
- 500+ stations across India
- 30-second swap time
- Works with Ola S1, TVS iQube, Bajaj Chetak, and more

**Subscription Plans:**
- Basic: ₹1,999/month (30 swaps)
- Pro: ₹2,999/month (60 swaps)
- Premium: ₹3,999/month (unlimited swaps)

**Battery Range:** 80-100 km per charge

## COMMON ISSUES & SOLUTIONS

**Battery Locked:**
"Try restarting your scooter. If it's still locked, visit any swap station - our team will unlock it immediately."

**Station Not Found:**
"Use the Battery Smart app to locate the nearest station. We have 500+ locations with real-time battery availability."

**Refund Requests:**
"Refunds are processed within 3-7 business days. Check status in the Battery Smart app under transactions."

**Charging Issues:**
"Swap your battery at any station for a fully charged one. This is included in your subscription."

**Subscription Questions:**
"I recommend the Pro plan at ₹2,999 for 60 swaps - it's our most popular choice. You can upgrade or downgrade anytime in the app."

## RESPONSE RULES
1. **Answer immediately** - Don't ask for verification unless changing account details
2. **Be brief** - 1-2 sentences max (this is voice)
3. **Be specific** - Give exact prices, times, and steps
4. **Be helpful** - Solve the problem directly
5. **Be natural** - Talk like a human, not a script

## EXAMPLES

Customer: "How much does it cost?"
You: "We have three plans! Basic is 1,999 rupees, Pro is 2,999, and Premium is 3,999 for unlimited swaps. Most customers love the Pro plan!"

Customer: "My battery won't charge"
You: "Just swap it for a new battery at any station - swapping takes only 30 seconds and it's included in your plan!"

Customer: "Where's the nearest station?"
You: "Open the Battery Smart app and tap 'Find Station' - it'll show all nearby locations with live battery availability. What area are you in?"

## IMPORTANT
- Answer questions directly without asking for phone numbers first
- Keep responses under 30 words when possible
- Sound natural and conversational
- If you don't know something, say "Let me check on that" and provide general help"""

        return system_prompt

    
    def start_session(self) -> str:
        """
        Start a new voice call session.
        
        Returns:
            Session ID
        """
        self.session_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()
        self.transcript = []
        self.conversation_history = []
        
        # Add system message to conversation history
        system_prompt = self._build_system_prompt()
        self.conversation_history.append({
            "role": "system",
            "content": system_prompt
        })
        
        if self.client and self.model_type == 'groq':
            print(f"✓ Groq chat session started: {self.session_id}")
        elif self.model and self.model_type == 'gemini':
            try:
                self.chat_session = self.model.start_chat(history=[])
                print(f"✓ Gemini chat session started: {self.session_id}")
            except Exception as e:
                print(f"✗ Failed to start Gemini session: {e}")
                self.chat_session = None
        else:
            print("⚠ No LLM available, using fallback responses")
        
        return self.session_id
    
    def get_greeting(self) -> str:
        """Get the agent's opening greeting."""
        greeting = f"Thank you for calling Battery Smart! My name is {self.agent_name}. How may I help you today?"
        self._add_to_transcript("agent", greeting)
        return greeting
    
    def process_message(self, user_message: str) -> str:
        """
        Process user message and generate response.
        
        Args:
            user_message: The customer's spoken text (from STT)
            
        Returns:
            Agent's response text (to be sent to TTS)
        """
        if not user_message.strip():
            return "I'm sorry, I didn't catch that. Could you please repeat?"
        
        # Add user message to transcript
        self._add_to_transcript("customer", user_message)
        
        # Generate response using Groq or Gemini
        if self.client and self.model_type == 'groq':
            try:
                # Add user message to history
                self.conversation_history.append({
                    "role": "user",
                    "content": user_message
                })
                
                print(f"→ User: {user_message}")
                
                # Get response from Groq
                chat_completion = self.client.chat.completions.create(
                    messages=self.conversation_history,
                    model=self.model_name,
                    temperature=0.7,
                    max_tokens=200,
                    top_p=0.9,
                )
                
                agent_response = chat_completion.choices[0].message.content.strip()
                print(f"← Groq: {agent_response}")
                
                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": agent_response
                })
                
            except Exception as e:
                print(f"✗ Groq error: {e}")
                agent_response = self._get_fallback_response(user_message)
                print(f"← Fallback: {agent_response}")
                
        elif self.chat_session and self.model_type == 'gemini':
            try:
                print(f"→ User: {user_message}")
                response = self.chat_session.send_message(user_message)
                agent_response = response.text.strip()
                print(f"← Gemini: {agent_response}")
            except Exception as e:
                print(f"✗ Gemini error: {e}")
                agent_response = self._get_fallback_response(user_message)
                print(f"← Fallback: {agent_response}")
        else:
            print(f"⚠ Using fallback (no LLM session)")
            agent_response = self._get_fallback_response(user_message)
        
        # Clean up response for voice
        agent_response = self._clean_for_voice(agent_response)
        
        # Add agent response to transcript
        self._add_to_transcript("agent", agent_response)
        
        return agent_response
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Get a fallback response when Gemini is unavailable."""
        message_lower = user_message.lower()
        
        # Check for common issues - provide helpful responses directly
        if any(kw in message_lower for kw in ['battery locked', 'locked', "can't unlock", 'unlock']):
            return "Try restarting your scooter first. If that doesn't work, visit any Battery Smart station and our staff can help unlock it."
        
        if any(kw in message_lower for kw in ['refund', 'money back', 'charged twice']):
            return "For refund requests, the amount will be credited back within 3 to 7 business days. You can also check the status in your Battery Smart app."
        
        if any(kw in message_lower for kw in ['nearest station', 'find station', 'station location', 'where is station', 'station near']):
            return "Use the Battery Smart app to find the nearest station - we have 500+ locations with real-time battery availability. What city are you in?"
        
        if any(kw in message_lower for kw in ['price', 'cost', 'plan', 'subscription', 'how much']):
            return "We have three plans! Basic at 1,999 rupees for 30 swaps, Pro at 2,999 for 60 swaps, and Premium at 3,999 for unlimited swaps."
        
        if any(kw in message_lower for kw in ['battery shortage', 'no battery', 'battery not available', 'shortage']):
            return "I understand the concern. Our stations work hard to maintain stock. Please check the Battery Smart app for real-time availability at nearby stations."
        
        if any(kw in message_lower for kw in ['charge', 'charging', 'not charging', 'won\'t charge']):
            return "Just swap your battery for a fully charged one at any station - swapping takes only 30 seconds and it's included in your plan!"
        
        if any(kw in message_lower for kw in ['bye', 'thank', 'that\'s all', 'nothing else', 'goodbye']):
            return "Thank you for calling Battery Smart! Have a wonderful day!"
        
        if any(kw in message_lower for kw in ['hello', 'hi', 'hey']):
            return "Hello! Welcome to Battery Smart. How can I help you today?"
        
        # Generic helpful response for anything else
        return "I'm here to help! You can ask me about battery swaps, finding stations, subscription plans, or technical issues. What would you like to know?"
    
    def _clean_for_voice(self, text: str) -> str:
        """Clean text for voice output - remove markdown, emojis, etc."""
        # Remove markdown
        text = text.replace('**', '').replace('*', '').replace('_', ' ')
        text = text.replace('#', '').replace('`', '')
        
        # Remove common emojis
        for char in '📞🔋⚡✅❌💡📍🚨':
            text = text.replace(char, '')
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _add_to_transcript(self, speaker: str, text: str):
        """Add an entry to the transcript."""
        self.transcript.append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
    
    def end_session(self) -> Dict:
        """
        End the voice call session.
        
        Returns:
            Session summary with transcript
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
        
        # Format transcript for QA evaluation
        formatted_transcript = self._format_transcript_for_qa()
        
        session_data = {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration),
            "transcript": self.transcript,
            "formatted_transcript": formatted_transcript
        }
        
        # Reset session
        self.chat_session = None
        self.session_id = None
        self.transcript = []
        self.start_time = None
        
        return session_data
    
    def _format_transcript_for_qa(self) -> str:
        """Format transcript in the same format as sample_transcripts.py for QA evaluation."""
        lines = []
        for entry in self.transcript:
            speaker = "Agent" if entry["speaker"] == "agent" else "Customer"
            lines.append(f"{speaker}: {entry['text']}")
        return "\n\n".join(lines)
    
    def get_transcript(self) -> List[Dict]:
        """Get the current transcript."""
        return self.transcript


class VoiceSessionManager:
    """Manages multiple voice agent sessions."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.sessions: Dict[str, VoiceAgent] = {}
        self.completed_sessions: List[Dict] = []
    
    def create_session(self) -> tuple:
        """
        Create a new voice session.
        
        Returns:
            Tuple of (session_id, greeting)
        """
        agent = VoiceAgent(api_key=self.api_key)
        session_id = agent.start_session()
        self.sessions[session_id] = agent
        greeting = agent.get_greeting()
        return session_id, greeting
    
    def process_message(self, session_id: str, message: str) -> str:
        """Process a message in an existing session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id].process_message(message)
    
    def end_session(self, session_id: str) -> Dict:
        """End a session and return its data."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = self.sessions[session_id].end_session()
        self.completed_sessions.append(session_data)
        del self.sessions[session_id]
        return session_data
    
    def get_session(self, session_id: str) -> Optional[VoiceAgent]:
        """Get a session by ID."""
        return self.sessions.get(session_id)


# Test the voice agent
if __name__ == "__main__":
    print("=" * 60)
    print("Battery Smart Voice Agent - Test Mode")
    print("=" * 60)
    
    agent = VoiceAgent()
    session_id = agent.start_session()
    
    print(f"\nSession started: {session_id}")
    print(f"\nAgent: {agent.get_greeting()}")
    
    # Simulate a conversation
    test_messages = [
        "Hi, my battery is locked and I can't swap it",
        "Yes, my phone number is 9876543210",
        "The battery ID is BS-2024-78456",
        "Great, thank you so much!",
        "No that's all, bye"
    ]
    
    for msg in test_messages:
        print(f"\nCustomer: {msg}")
        response = agent.process_message(msg)
        print(f"Agent: {response}")
    
    # End session
    session_data = agent.end_session()
    print("\n" + "=" * 60)
    print("Session Ended")
    print(f"Duration: {session_data['duration_seconds']} seconds")
    print("\nFormatted Transcript for QA:")
    print("-" * 40)
    print(session_data['formatted_transcript'])
