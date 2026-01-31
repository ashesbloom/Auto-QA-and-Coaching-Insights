"""
Battery Smart Voice Agent
AI-powered voice assistant for customer support using Gemini LLM or AWS Bedrock.
Follows Battery Smart SOPs for consistent, professional responses.

Supports:
- AWS Bedrock (Claude 3 Haiku/Nova) with streaming for low latency
- Google Gemini as fallback for local development
"""

import os
import json
from datetime import datetime
import uuid
from typing import Dict, List, Optional, Generator
import sys
import asyncio

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    BATTERY_SMART_SOPS,
    REQUIRED_SCRIPT_ELEMENTS,
    COMPLAINT_CATEGORIES,
    SENTIMENT_KEYWORDS
)

# Check for AWS Bedrock availability
try:
    from aws_services.config import get_aws_config
    aws_config = get_aws_config()
    USE_BEDROCK = aws_config.is_bedrock_available()
    if USE_BEDROCK:
        from aws_services.bedrock_llm import BedrockLLM
        print("✅ AWS Bedrock LLM available")
except ImportError:
    USE_BEDROCK = False

# Try to import Groq (fast, preferred after Bedrock)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: groq not installed. Run: pip install groq")

# Try to import Gemini as fallback
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Run: pip install google-generativeai")


class VoiceAgent:
    """
    Battery Smart Voice Agent powered by AWS Bedrock, Groq, or Gemini LLM.
    Handles customer support conversations following company SOPs.
    
    Priority:
    1. AWS Bedrock (if USE_AWS=true and USE_AWS_BEDROCK=true)
    2. Groq/Llama (fastest, if GROQ_API_KEY is set)
    3. Google Gemini (fallback)
    4. Rule-based fallback responses
    """
    
    def __init__(self, api_key: str = None, use_bedrock: bool = None):
        """
        Initialize the voice agent.
        
        Args:
            api_key: Gemini API key. If not provided, reads from GEMINI_API_KEY env var.
            use_bedrock: Force Bedrock usage. If None, auto-detects based on USE_AWS env var.
        """
        self.gemini_key = api_key or os.getenv('GEMINI_API_KEY')
        self.groq_key = os.getenv('GROQ_API_KEY')
        self.model = None
        self.chat_session = None
        self.bedrock_agent = None
        self.groq_client = None
        self.session_id = None
        self.transcript = []
        self.conversation_history = []  # For Groq conversation tracking
        self.start_time = None
        self.agent_name = "Priya"
        self.use_streaming = False
        self.model_type = None  # Track which LLM is active
        
        # Determine which LLM to use (priority: Bedrock > Groq > Gemini)
        if use_bedrock is None:
            use_bedrock = USE_BEDROCK if USE_BEDROCK else False
        
        # Priority 1: AWS Bedrock
        if use_bedrock and USE_BEDROCK:
            self._initialize_bedrock()
        
        # Priority 2: Groq (if Bedrock failed or not enabled)
        if self.model_type is None and GROQ_AVAILABLE and self.groq_key:
            self._initialize_groq()
        
        # Priority 3: Gemini (fallback)
        if self.model_type is None and GEMINI_AVAILABLE and self.gemini_key:
            self._initialize_gemini()
    
    def _initialize_bedrock(self):
        """Initialize AWS Bedrock with streaming support."""
        try:
            self.bedrock_agent = BedrockVoiceAgent(
                system_prompt=self._build_system_prompt()
            )
            if self.bedrock_agent.is_available():
                self.use_streaming = True
                self.model_type = "bedrock"
                print("Voice Agent: Using AWS Bedrock with streaming")
            else:
                print("Voice Agent: Bedrock not available")
                self.bedrock_agent = None
        except Exception as e:
            print(f"Bedrock initialization failed: {e}")
            self.bedrock_agent = None
    
    def _initialize_groq(self):
        """Initialize Groq client with Llama model (fast inference)."""
        try:
            self.groq_client = Groq(api_key=self.groq_key)
            self.model_type = "groq"
            print("Voice Agent: Using Groq/Llama (fast mode)")
        except Exception as e:
            print(f"Groq initialization failed: {e}")
            self.groq_client = None
    
    def _initialize_gemini(self):
        """Initialize Gemini model with Battery Smart system prompt."""
        genai.configure(api_key=self.gemini_key)
        
        # Use Gemini 1.5 Flash for faster responses
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=self._build_system_prompt()
        )
        self.model_type = "gemini"
        print("Voice Agent: Using Google Gemini")
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt from Battery Smart SOPs."""
        
        # Build SOP resolution section
        sop_section = []
        for issue_type, sop in BATTERY_SMART_SOPS.items():
            keywords = ', '.join(sop.get('issue_keywords', [])[:3])
            responses = ', '.join(sop.get('correct_responses', [])[:3])
            sop_section.append(f"- **{issue_type.replace('_', ' ').title()}**: When customer mentions [{keywords}], respond with appropriate info about [{responses}]")
        
        system_prompt = f"""You are {self.agent_name}, a professional and friendly Battery Smart customer support voice agent. You handle calls from customers with empathy and efficiency.

## YOUR IDENTITY
- Name: {self.agent_name}
- Role: Battery Smart Customer Support Agent
- Company: Battery Smart - India's leading battery swap network for electric vehicles

## IMPORTANT: THIS IS A DEMO MODE
- Do NOT repeatedly ask for phone numbers or account verification
- Help customers directly with their questions
- Provide helpful information without requiring login
- If they want account-specific help, you can mention they'd need to verify, but don't block the conversation

## WHAT YOU CAN HELP WITH (Answer directly!)

**Battery Issues:**
- Battery locked? Advise them to try restarting or visit nearest swap station
- Not charging? Recommend swapping for a new battery
- Overheating? Tell them to stop using immediately and visit a station

**Swap Stations:**
- We have 500+ stations across India
- Nearest station can be found in the Battery Smart app
- Swapping takes about 30 seconds

**Subscription Plans:**
- Basic: Rs. 1,999/month for 30 swaps
- Pro: Rs. 2,999/month for 60 swaps  
- Premium: Rs. 3,999/month for unlimited swaps

**General Info:**
- We support Ola S1, TVS iQube, Bajaj Chetak, and more
- Battery range: 80-100 km per charge
- 24/7 customer support available

## RESPONSE GUIDELINES

1. **Answer the question directly** - Don't ask for verification first!
2. **Be conversational**: This is a VOICE call. Keep responses natural and brief (2-3 sentences max).
3. **Show empathy**: Use phrases like "I understand", "Let me help you with that".
4. **Be helpful**: Always provide useful information.
5. **Stay professional**: Remain calm and courteous.

## EXAMPLE CONVERSATIONS

Customer: "How much does your service cost?"
You: "We have three plans! Basic at 1,999 rupees for 30 swaps, Pro at 2,999 for 60 swaps, and Premium at 3,999 for unlimited swaps. Most customers love our Pro plan!"

Customer: "My battery is locked"
You: "I can help with that! Try restarting your scooter first. If that doesn't work, visit any Battery Smart station and our staff can help unlock it. Would you like me to help you find the nearest station?"

Customer: "Where is the nearest station?"
You: "You can find the nearest station using our Battery Smart app - it shows all 500+ locations with real-time battery availability. What area are you in? I can give you some general directions."

## CLOSING
- Ask: "Is there anything else I can help you with?"
- Thank them: "Thank you for calling Battery Smart! Have a great day!"

Remember: Help them first, verify only if absolutely needed for account changes!"""

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
        self.conversation_history = []  # Reset for Groq
        
        # Initialize session based on model type
        if self.bedrock_agent:
            self.bedrock_agent.start_session()
        elif self.groq_client:
            # Add system prompt to conversation history for Groq
            self.conversation_history.append({
                "role": "system",
                "content": self._build_system_prompt()
            })
        elif self.model:
            self.chat_session = self.model.start_chat(history=[])
        
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
        
        # Generate response using available LLM (priority: Bedrock > Groq > Gemini)
        agent_response = None
        
        # Try Bedrock first
        if self.bedrock_agent:
            try:
                agent_response = self.bedrock_agent.llm.send_message(user_message)
            except Exception as e:
                print(f"Bedrock error: {e}")
        
        # Try Groq (fast Llama inference)
        if agent_response is None and self.groq_client:
            try:
                # Add user message to history
                self.conversation_history.append({
                    "role": "user",
                    "content": user_message
                })
                
                # Call Groq API
                chat_completion = self.groq_client.chat.completions.create(
                    messages=self.conversation_history,
                    model="llama-3.3-70b-versatile",  # Fast and capable
                    temperature=0.7,
                    max_tokens=300
                )
                
                agent_response = chat_completion.choices[0].message.content.strip()
                
                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": agent_response
                })
            except Exception as e:
                print(f"Groq error: {e}")
        
        # Try Gemini as fallback
        if agent_response is None and self.chat_session:
            try:
                response = self.chat_session.send_message(user_message)
                agent_response = response.text.strip()
            except Exception as e:
                print(f"Gemini error: {e}")
        
        # Use fallback if no LLM available
        if agent_response is None:
            agent_response = self._get_fallback_response(user_message)
        
        # Clean up response for voice
        agent_response = self._clean_for_voice(agent_response)
        
        # Add agent response to transcript
        self._add_to_transcript("agent", agent_response)
        
        return agent_response
    
    def process_message_streaming(self, user_message: str) -> Generator[str, None, None]:
        """
        Process user message with streaming response (for low latency).
        
        Only works with Bedrock. Falls back to non-streaming for Gemini.
        
        Args:
            user_message: The customer's spoken text
            
        Yields:
            Response sentences as they become available
        """
        if not user_message.strip():
            yield "I'm sorry, I didn't catch that. Could you please repeat?"
            return
        
        self._add_to_transcript("customer", user_message)
        
        # Use streaming with Bedrock
        if self.bedrock_agent and self.use_streaming:
            try:
                full_response = ""
                for sentence in self.bedrock_agent.llm.stream_sentences(user_message):
                    clean_sentence = self._clean_for_voice(sentence)
                    full_response += clean_sentence + " "
                    yield clean_sentence
                
                self._add_to_transcript("agent", full_response.strip())
                return
                
            except Exception as e:
                print(f"Bedrock streaming error: {e}")
        
        # Non-streaming fallback
        response = self.process_message(user_message)
        yield response
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Get a fallback response when Gemini is unavailable."""
        message_lower = user_message.lower()
        
        # Check for common issues - provide helpful responses directly
        if any(kw in message_lower for kw in ['battery locked', 'locked', "can't unlock"]):
            return "I can help with that! Try restarting your scooter first. If that doesn't work, visit any Battery Smart station and our staff can help unlock it."
        
        if any(kw in message_lower for kw in ['refund', 'money back', 'charged twice']):
            return "For refund requests, the amount will be credited back within 3 to 7 business days. You can also check the status in your Battery Smart app."
        
        if any(kw in message_lower for kw in ['swap', 'station', 'no batteries']):
            return "We have over 500 swap stations across India! You can find the nearest one using the Battery Smart app. Swapping takes just 30 seconds."
        
        if any(kw in message_lower for kw in ['price', 'cost', 'plan', 'subscription']):
            return "We have three plans! Basic at 1,999 rupees for 30 swaps, Pro at 2,999 for 60 swaps, and Premium at 3,999 for unlimited swaps."
        
        if any(kw in message_lower for kw in ['bye', 'thank', 'that\'s all', 'nothing else']):
            return "Thank you for calling Battery Smart! Have a wonderful day. Goodbye!"
        
        if any(kw in message_lower for kw in ['hello', 'hi', 'hey']):
            return "Hello! Welcome to Battery Smart. How can I help you today?"
        
        return "I'd be happy to help! We offer battery swap services for electric scooters with over 500 stations across India. What would you like to know?"
    
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
            "formatted_transcript": formatted_transcript,
            "llm_provider": self.model_type or "fallback"
        }
        
        # Reset session
        self.chat_session = None
        self.conversation_history = []  # Reset Groq history
        if self.bedrock_agent:
            self.bedrock_agent.llm.reset_conversation()
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
    """Manages multiple voice agent sessions with AWS support."""
    
    def __init__(self, api_key: str = None, use_bedrock: bool = None):
        """
        Initialize session manager.
        
        Args:
            api_key: Gemini API key (for fallback)
            use_bedrock: Force Bedrock usage. If None, auto-detects.
        """
        self.api_key = api_key
        self.use_bedrock = use_bedrock
        self.sessions: Dict[str, VoiceAgent] = {}
        self.completed_sessions: List[Dict] = []
    
    def create_session(self) -> tuple:
        """
        Create a new voice session.
        
        Returns:
            Tuple of (session_id, greeting)
        """
        agent = VoiceAgent(api_key=self.api_key, use_bedrock=self.use_bedrock)
        session_id = agent.start_session()
        self.sessions[session_id] = agent
        greeting = agent.get_greeting()
        return session_id, greeting
    
    def process_message(self, session_id: str, message: str) -> str:
        """Process a message in an existing session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id].process_message(message)
    
    def process_message_streaming(self, session_id: str, message: str) -> Generator[str, None, None]:
        """Process a message with streaming response."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id].process_message_streaming(message)
    
    def is_streaming_enabled(self, session_id: str) -> bool:
        """Check if streaming is enabled for a session."""
        if session_id not in self.sessions:
            return False
        return self.sessions[session_id].use_streaming
    
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
