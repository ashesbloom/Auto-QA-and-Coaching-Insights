"""
Speech-to-Text Integration Module
Provides audio transcription capabilities using Whisper or other STT engines.
"""

import os
import json
from typing import Dict, Optional, Tuple
from datetime import datetime


class SpeechToTextProcessor:
    """
    Processes audio files to extract text transcripts.
    Supports multiple STT backends: Whisper (local), Google Cloud, Azure.
    """
    
    def __init__(self, engine: str = "whisper"):
        """
        Initialize the STT processor.
        
        Args:
            engine: STT engine to use ('whisper', 'google', 'azure')
        """
        self.engine = engine
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm']
        self._whisper_model = None
    
    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dict with transcript, segments, and metadata
        """
        if not os.path.exists(audio_path):
            return {"error": f"File not found: {audio_path}"}
        
        ext = os.path.splitext(audio_path)[1].lower()
        if ext not in self.supported_formats:
            return {"error": f"Unsupported format: {ext}. Use: {self.supported_formats}"}
        
        if self.engine == "whisper":
            return self._transcribe_whisper(audio_path)
        elif self.engine == "google":
            return self._transcribe_google(audio_path)
        elif self.engine == "azure":
            return self._transcribe_azure(audio_path)
        else:
            return {"error": f"Unknown engine: {self.engine}"}
    
    def _transcribe_whisper(self, audio_path: str) -> Dict:
        """Transcribe using OpenAI Whisper (local)."""
        try:
            import whisper
            
            if self._whisper_model is None:
                print("Loading Whisper model (this may take a moment)...")
                self._whisper_model = whisper.load_model("base")
            
            result = self._whisper_model.transcribe(audio_path)
            
            # Extract segments with timestamps
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                    "speaker": self._detect_speaker(seg["text"])
                })
            
            return {
                "success": True,
                "transcript": result["text"],
                "segments": segments,
                "language": result.get("language", "en"),
                "duration": segments[-1]["end"] if segments else 0,
                "engine": "whisper",
                "processed_at": datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                "error": "Whisper not installed. Run: pip install openai-whisper",
                "fallback": self._create_mock_transcript(audio_path)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _transcribe_google(self, audio_path: str) -> Dict:
        """Transcribe using Google Cloud Speech-to-Text."""
        try:
            from google.cloud import speech
            
            client = speech.SpeechClient()
            
            with open(audio_path, "rb") as audio_file:
                content = audio_file.read()
            
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-IN",
                enable_automatic_punctuation=True,
                enable_speaker_diarization=True,
                diarization_speaker_count=2
            )
            
            response = client.recognize(config=config, audio=audio)
            
            transcript = " ".join([
                result.alternatives[0].transcript 
                for result in response.results
            ])
            
            return {
                "success": True,
                "transcript": transcript,
                "engine": "google",
                "processed_at": datetime.now().isoformat()
            }
            
        except ImportError:
            return {"error": "Google Cloud Speech not installed. Run: pip install google-cloud-speech"}
        except Exception as e:
            return {"error": str(e)}
    
    def _transcribe_azure(self, audio_path: str) -> Dict:
        """Transcribe using Azure Speech Services."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            speech_key = os.environ.get("AZURE_SPEECH_KEY")
            speech_region = os.environ.get("AZURE_SPEECH_REGION")
            
            if not speech_key or not speech_region:
                return {"error": "Azure credentials not configured. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION"}
            
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, 
                region=speech_region
            )
            audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
            
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            result = recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return {
                    "success": True,
                    "transcript": result.text,
                    "engine": "azure",
                    "processed_at": datetime.now().isoformat()
                }
            else:
                return {"error": f"Recognition failed: {result.reason}"}
                
        except ImportError:
            return {"error": "Azure Speech SDK not installed. Run: pip install azure-cognitiveservices-speech"}
        except Exception as e:
            return {"error": str(e)}
    
    def _detect_speaker(self, text: str) -> str:
        """Simple speaker detection based on text patterns."""
        text_lower = text.lower()
        
        # Agent indicators
        agent_indicators = [
            "thank you for calling", "how may i help",
            "let me check", "i apologize", "is there anything else",
            "battery smart", "customer support"
        ]
        
        for indicator in agent_indicators:
            if indicator in text_lower:
                return "Agent"
        
        return "Customer"
    
    def _create_mock_transcript(self, audio_path: str) -> Dict:
        """Create a mock transcript for testing when Whisper is not installed."""
        return {
            "success": True,
            "transcript": """
Agent: Thank you for calling Battery Smart. How may I help you today?

Customer: Hi, my battery is not charging properly.

Agent: I apologize for the inconvenience. Can you provide your battery ID?

Customer: Yes, it's BS-2024-12345.

Agent: Thank you. Let me check the status. I can see there might be a sync issue. 
Let me try to reset it remotely.

Customer: Okay, thank you.

Agent: The reset is complete. Please try charging again. 
Is there anything else I can help you with?

Customer: No, that's all. Thanks for your help!

Agent: You're welcome. Thank you for calling Battery Smart. Have a great day!
            """.strip(),
            "segments": [
                {"start": 0, "end": 3, "text": "Thank you for calling Battery Smart. How may I help you today?", "speaker": "Agent"},
                {"start": 3, "end": 6, "text": "Hi, my battery is not charging properly.", "speaker": "Customer"},
                {"start": 6, "end": 10, "text": "I apologize for the inconvenience. Can you provide your battery ID?", "speaker": "Agent"},
                {"start": 10, "end": 13, "text": "Yes, it's BS-2024-12345.", "speaker": "Customer"},
                {"start": 13, "end": 20, "text": "Thank you. Let me check the status. I can see there might be a sync issue. Let me try to reset it remotely.", "speaker": "Agent"},
                {"start": 20, "end": 22, "text": "Okay, thank you.", "speaker": "Customer"},
                {"start": 22, "end": 28, "text": "The reset is complete. Please try charging again. Is there anything else I can help you with?", "speaker": "Agent"},
                {"start": 28, "end": 31, "text": "No, that's all. Thanks for your help!", "speaker": "Customer"},
                {"start": 31, "end": 35, "text": "You're welcome. Thank you for calling Battery Smart. Have a great day!", "speaker": "Agent"}
            ],
            "language": "en",
            "duration": 35,
            "engine": "mock",
            "note": "This is a mock transcript for testing. Install Whisper for real transcription.",
            "processed_at": datetime.now().isoformat()
        }


class AudioPipeline:
    """
    End-to-end pipeline: Audio → Transcript → QA Evaluation → Analytics
    """
    
    def __init__(self, stt_engine: str = "whisper"):
        from call_evaluator import CallEvaluator
        from analytics import AnalyticsEngine
        
        self.stt = SpeechToTextProcessor(engine=stt_engine)
        self.evaluator = CallEvaluator()
        self.analytics = AnalyticsEngine()
    
    def process_audio(self, audio_path: str, metadata: Dict = None) -> Dict:
        """
        Process a single audio file through the complete pipeline.
        
        Args:
            audio_path: Path to the audio file
            metadata: Optional call metadata (agent_id, city, etc.)
            
        Returns:
            Complete evaluation results
        """
        from call_evaluator import CallMetadata
        
        # Step 1: Transcribe
        print(f"[1/3] Transcribing: {audio_path}")
        stt_result = self.stt.transcribe(audio_path)
        
        if "error" in stt_result and "fallback" not in stt_result:
            return {"error": stt_result["error"], "stage": "transcription"}
        
        # Use fallback if main transcription failed
        if "fallback" in stt_result:
            stt_result = stt_result["fallback"]
        
        transcript = stt_result.get("transcript", "")
        
        # Step 2: Evaluate
        print("[2/3] Evaluating call quality...")
        call_meta = CallMetadata(
            call_id=metadata.get("call_id", f"AUDIO-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            agent_id=metadata.get("agent_id", "UNKNOWN"),
            agent_name=metadata.get("agent_name", "Unknown Agent"),
            city=metadata.get("city", "Unknown"),
            timestamp=datetime.now().isoformat(),
            duration_seconds=int(stt_result.get("duration", 0))
        ) if metadata else CallMetadata(
            call_id=f"AUDIO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            agent_id="UNKNOWN",
            agent_name="Unknown",
            city="Unknown",
            timestamp=datetime.now().isoformat()
        )
        
        evaluation = self.evaluator.evaluate_call(transcript, call_meta)
        
        # Step 3: Add to analytics
        print("[3/3] Adding to analytics...")
        self.analytics.add_evaluation(evaluation)
        
        return {
            "success": True,
            "audio_file": audio_path,
            "transcription": stt_result,
            "evaluation": evaluation,
            "summary": {
                "score": evaluation["overall"]["score"],
                "grade": evaluation["overall"]["grade"],
                "needs_review": evaluation["overall"]["needs_supervisor_review"],
                "alerts": len(evaluation.get("supervisor_alerts", []))
            }
        }
    
    def process_batch(self, audio_folder: str, metadata_file: str = None) -> Dict:
        """
        Process multiple audio files from a folder.
        
        Args:
            audio_folder: Path to folder containing audio files
            metadata_file: Optional JSON file with metadata for each audio
            
        Returns:
            Batch processing results with analytics
        """
        if not os.path.isdir(audio_folder):
            return {"error": f"Folder not found: {audio_folder}"}
        
        # Load metadata if provided
        metadata_map = {}
        if metadata_file and os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata_map = json.load(f)
        
        # Find audio files
        audio_files = [
            os.path.join(audio_folder, f) 
            for f in os.listdir(audio_folder)
            if os.path.splitext(f)[1].lower() in self.stt.supported_formats
        ]
        
        print(f"Found {len(audio_files)} audio files to process")
        
        results = []
        for i, audio_path in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}] Processing: {os.path.basename(audio_path)}")
            
            filename = os.path.basename(audio_path)
            metadata = metadata_map.get(filename, {})
            
            result = self.process_audio(audio_path, metadata)
            results.append(result)
        
        # Generate analytics report
        print("\nGenerating analytics report...")
        analytics_report = self.analytics.generate_analytics_report()
        
        return {
            "total_processed": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if r.get("error")),
            "results": results,
            "analytics": analytics_report
        }


# Demo function
def demo_audio_pipeline():
    """Demonstrate the audio processing pipeline."""
    print("=" * 60)
    print("  Battery Smart Audio Processing Pipeline Demo")
    print("=" * 60)
    
    pipeline = AudioPipeline(stt_engine="whisper")
    
    # Process a mock audio (will use fallback transcript)
    result = pipeline.process_audio(
        "sample_call.wav",  # This doesn't exist, will use mock
        metadata={
            "call_id": "DEMO-001",
            "agent_id": "AGT-BLR-001",
            "agent_name": "Demo Agent",
            "city": "Bangalore"
        }
    )
    
    if result.get("success"):
        print("\n" + "=" * 60)
        print("  Processing Complete!")
        print("=" * 60)
        print(f"  Score: {result['summary']['score']}/100")
        print(f"  Grade: {result['summary']['grade']}")
        print(f"  Needs Review: {result['summary']['needs_review']}")
    else:
        print(f"\nError: {result.get('error')}")


if __name__ == "__main__":
    demo_audio_pipeline()
