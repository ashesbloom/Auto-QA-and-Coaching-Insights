"""
AWS Bedrock LLM Handler with Streaming Support

Provides low-latency LLM responses using AWS Bedrock's Converse API
with streaming for real-time voice applications.

Supports:
- Claude 3 Haiku (recommended for conversational AI)
- Claude 3.5 Sonnet (higher quality)
- Amazon Nova Micro/Lite (fastest, cost-effective)
"""

import os
import json
import logging
from typing import Generator, Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check for boto3
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. Run: pip install boto3")


@dataclass
class BedrockMessage:
    """A message in the conversation."""
    role: str  # 'user' or 'assistant'
    content: str


class BedrockLLM:
    """
    AWS Bedrock LLM client with streaming support for low-latency voice applications.
    
    Uses the Converse API for consistent interface across models and built-in
    conversation management.
    """
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = None,
        system_prompt: str = None,
        max_tokens: int = 512,  # Keep short for voice
        temperature: float = 0.7
    ):
        """
        Initialize Bedrock LLM client.
        
        Args:
            model_id: Bedrock model ID
            region: AWS region (defaults to AWS_REGION env var or us-east-1)
            system_prompt: System instructions for the model
            max_tokens: Maximum tokens in response (keep low for voice)
            temperature: Response creativity (0.0-1.0)
        """
        self.model_id = model_id
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.conversation_history: List[Dict] = []
        self.client = None
        
        if BOTO3_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Bedrock Runtime client."""
        try:
            # Configure for low latency
            config = Config(
                retries={'max_attempts': 2, 'mode': 'adaptive'},
                connect_timeout=5,
                read_timeout=30
            )
            
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
                config=config
            )
            logger.info(f"Bedrock client initialized with model: {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Bedrock is available and configured."""
        return self.client is not None
    
    def reset_conversation(self):
        """Clear conversation history for a new session."""
        self.conversation_history = []
    
    def send_message(self, user_message: str) -> str:
        """
        Send a message and get a complete response (non-streaming).
        
        Args:
            user_message: The user's message
            
        Returns:
            The assistant's response text
        """
        if not self.client:
            raise RuntimeError("Bedrock client not initialized")
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": [{"text": user_message}]
        })
        
        # Build request
        request_params = {
            "modelId": self.model_id,
            "messages": self.conversation_history,
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            }
        }
        
        # Add system prompt if configured
        if self.system_prompt:
            request_params["system"] = [{"text": self.system_prompt}]
        
        try:
            response = self.client.converse(**request_params)
            
            # Extract response text
            assistant_message = response['output']['message']
            response_text = assistant_message['content'][0]['text']
            
            # Add to conversation history
            self.conversation_history.append(assistant_message)
            
            return response_text
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Bedrock API error: {error_code} - {e}")
            raise
    
    def send_message_streaming(self, user_message: str) -> Generator[str, None, None]:
        """
        Send a message and stream the response token by token.
        
        This is the recommended method for voice applications as it allows
        TTS to start generating audio as soon as the first sentence is complete.
        
        Args:
            user_message: The user's message
            
        Yields:
            Response text chunks as they arrive
        """
        if not self.client:
            raise RuntimeError("Bedrock client not initialized")
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": [{"text": user_message}]
        })
        
        # Build request
        request_params = {
            "modelId": self.model_id,
            "messages": self.conversation_history,
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            }
        }
        
        # Add system prompt if configured
        if self.system_prompt:
            request_params["system"] = [{"text": self.system_prompt}]
        
        try:
            response = self.client.converse_stream(**request_params)
            
            full_response = ""
            
            for event in response['stream']:
                if 'contentBlockDelta' in event:
                    delta = event['contentBlockDelta']['delta']
                    if 'text' in delta:
                        chunk = delta['text']
                        full_response += chunk
                        yield chunk
                
                elif 'messageStop' in event:
                    # Stream complete
                    break
            
            # Add complete response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": [{"text": full_response}]
            })
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Bedrock streaming error: {error_code} - {e}")
            raise
    
    def stream_sentences(self, user_message: str) -> Generator[str, None, None]:
        """
        Stream response as complete sentences for optimal TTS processing.
        
        This buffers tokens until a sentence boundary is detected,
        then yields complete sentences for natural-sounding TTS.
        
        Args:
            user_message: The user's message
            
        Yields:
            Complete sentences as they become available
        """
        buffer = ""
        sentence_endings = {'.', '!', '?'}
        
        for chunk in self.send_message_streaming(user_message):
            buffer += chunk
            
            # Check for sentence boundaries
            while any(end in buffer for end in sentence_endings):
                # Find the earliest sentence ending
                earliest_pos = len(buffer)
                for end in sentence_endings:
                    pos = buffer.find(end)
                    if pos != -1 and pos < earliest_pos:
                        earliest_pos = pos
                
                if earliest_pos < len(buffer):
                    # Extract and yield the sentence
                    sentence = buffer[:earliest_pos + 1].strip()
                    if sentence:
                        yield sentence
                    buffer = buffer[earliest_pos + 1:].lstrip()
                else:
                    break
        
        # Yield any remaining text
        if buffer.strip():
            yield buffer.strip()


class BedrockVoiceAgent:
    """
    Voice agent powered by AWS Bedrock with streaming support.
    Drop-in replacement for the Gemini-based VoiceAgent.
    """
    
    def __init__(
        self,
        model_id: str = None,
        region: str = None,
        system_prompt: str = None
    ):
        """
        Initialize Bedrock voice agent.
        
        Args:
            model_id: Bedrock model ID (defaults to AWS_BEDROCK_MODEL env var)
            region: AWS region
            system_prompt: Custom system prompt (defaults to Battery Smart SOPs)
        """
        self.model_id = model_id or os.getenv(
            'AWS_BEDROCK_MODEL', 
            'anthropic.claude-3-haiku-20240307-v1:0'
        )
        self.region = region
        self.agent_name = "Priya"
        self.session_id = None
        self.transcript = []
        self.start_time = None
        
        # Build system prompt if not provided
        if system_prompt is None:
            system_prompt = self._build_system_prompt()
        
        self.llm = BedrockLLM(
            model_id=self.model_id,
            region=self.region,
            system_prompt=system_prompt,
            max_tokens=256,  # Keep responses concise for voice
            temperature=0.7
        )
    
    def _build_system_prompt(self) -> str:
        """Build the Battery Smart system prompt."""
        return f"""You are {self.agent_name}, a professional and friendly Battery Smart customer support voice agent.

## YOUR IDENTITY
- Name: {self.agent_name}
- Role: Battery Smart Customer Support Agent
- Company: Battery Smart - India's leading battery swap network for electric vehicles

## RESPONSE STYLE (CRITICAL FOR VOICE)
- Keep responses SHORT: 1-3 sentences maximum
- Be conversational and natural
- No bullet points, numbered lists, or formatting
- No emojis or special characters
- Speak as if talking on a phone call

## WHAT YOU CAN HELP WITH

**Battery Issues:**
- Battery locked: Restart scooter or visit swap station
- Not charging: Recommend battery swap
- Overheating: Stop use immediately, visit station

**Swap Stations:**
- 500+ stations across India
- Find nearest via Battery Smart app
- Swapping takes 30 seconds

**Subscription Plans:**
- Basic: Rs. 1,999/month for 30 swaps
- Pro: Rs. 2,999/month for 60 swaps
- Premium: Rs. 3,999/month for unlimited swaps

## EXAMPLE RESPONSES

Customer: "How much does it cost?"
You: "We have three plans - Basic at 1,999 rupees for 30 swaps, Pro at 2,999 for 60 swaps, and Premium at 3,999 for unlimited. Most customers prefer our Pro plan!"

Customer: "My battery is locked"
You: "Try restarting your scooter first. If that doesn't work, visit any Battery Smart station and our team will help unlock it right away."

## CLOSING
When customer is done: "Thank you for calling Battery Smart! Have a great day!"

Remember: This is a VOICE call - be brief, helpful, and natural!"""

    def is_available(self) -> bool:
        """Check if Bedrock is available."""
        return self.llm.is_available()
    
    def start_session(self) -> str:
        """Start a new voice session."""
        import uuid
        from datetime import datetime
        
        self.session_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()
        self.transcript = []
        self.llm.reset_conversation()
        
        return self.session_id
    
    def get_greeting(self) -> str:
        """Get the agent's opening greeting."""
        greeting = f"Thank you for calling Battery Smart! My name is {self.agent_name}. How may I help you today?"
        self._add_to_transcript("agent", greeting)
        return greeting
    
    def process_message(self, user_message: str) -> str:
        """
        Process user message and get complete response.
        
        Args:
            user_message: Customer's message
            
        Returns:
            Agent's response
        """
        if not user_message.strip():
            return "I'm sorry, I didn't catch that. Could you please repeat?"
        
        self._add_to_transcript("customer", user_message)
        
        try:
            response = self.llm.send_message(user_message)
            response = self._clean_for_voice(response)
        except Exception as e:
            logger.error(f"Bedrock error: {e}")
            response = self._get_fallback_response(user_message)
        
        self._add_to_transcript("agent", response)
        return response
    
    def process_message_streaming(self, user_message: str) -> Generator[str, None, None]:
        """
        Process user message with streaming response.
        
        Args:
            user_message: Customer's message
            
        Yields:
            Response sentences as they become available
        """
        if not user_message.strip():
            yield "I'm sorry, I didn't catch that. Could you please repeat?"
            return
        
        self._add_to_transcript("customer", user_message)
        
        try:
            full_response = ""
            for sentence in self.llm.stream_sentences(user_message):
                clean_sentence = self._clean_for_voice(sentence)
                full_response += clean_sentence + " "
                yield clean_sentence
            
            self._add_to_transcript("agent", full_response.strip())
            
        except Exception as e:
            logger.error(f"Bedrock streaming error: {e}")
            fallback = self._get_fallback_response(user_message)
            self._add_to_transcript("agent", fallback)
            yield fallback
    
    def _clean_for_voice(self, text: str) -> str:
        """Clean text for voice output."""
        # Remove markdown and formatting
        text = text.replace('**', '').replace('*', '').replace('_', ' ')
        text = text.replace('#', '').replace('`', '')
        
        # Remove emojis
        for char in '📞🔋⚡✅❌💡📍🚨':
            text = text.replace(char, '')
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Fallback responses when Bedrock is unavailable."""
        message_lower = user_message.lower()
        
        if any(kw in message_lower for kw in ['locked', "can't unlock"]):
            return "Try restarting your scooter first. If that doesn't work, visit any Battery Smart station for help."
        
        if any(kw in message_lower for kw in ['price', 'cost', 'plan']):
            return "We have Basic at 1,999 rupees, Pro at 2,999, and Premium at 3,999 for unlimited swaps."
        
        if any(kw in message_lower for kw in ['swap', 'station']):
            return "Find your nearest station in the Battery Smart app. We have over 500 locations across India."
        
        if any(kw in message_lower for kw in ['bye', 'thank', 'nothing']):
            return "Thank you for calling Battery Smart! Have a wonderful day!"
        
        return "I'd be happy to help with battery swaps, subscriptions, or finding stations. What would you like to know?"
    
    def _add_to_transcript(self, speaker: str, text: str):
        """Add entry to transcript."""
        from datetime import datetime
        self.transcript.append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
    
    def end_session(self) -> Dict:
        """End session and return data."""
        from datetime import datetime
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
        
        session_data = {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration),
            "transcript": self.transcript,
            "formatted_transcript": self._format_transcript()
        }
        
        self.llm.reset_conversation()
        self.session_id = None
        self.transcript = []
        self.start_time = None
        
        return session_data
    
    def _format_transcript(self) -> str:
        """Format transcript for QA evaluation."""
        lines = []
        for entry in self.transcript:
            speaker = "Agent" if entry["speaker"] == "agent" else "Customer"
            lines.append(f"{speaker}: {entry['text']}")
        return "\n\n".join(lines)
    
    def get_transcript(self) -> List[Dict]:
        """Get current transcript."""
        return self.transcript
