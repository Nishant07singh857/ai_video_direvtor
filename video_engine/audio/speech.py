from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum as PyEnum


class SpeechRecognitionStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass
class TranscriptResult:
    """Result of speech recognition."""
    segments: List[Dict[str, Any]]
    language: Optional[str] = None
    duration: Optional[float] = None
    status: SpeechRecognitionStatus = SpeechRecognitionStatus.PENDING
    error_message: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None


class SpeechAnalyzer(ABC):
    """Abstract base class for speech recognition.
    
    Defines the interface for speech-to-text analysis.
    Different implementations can use different backends
    (Whisper local, Whisper API, Azure Speech, Google Speech, etc.)
    """
    
    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> TranscriptResult:
        """Transcribe audio file to text with timestamps.
        
        Args:
            audio_path: Path to audio file (or video with audio)
            language: Optional language hint (ISO 639-1 code)
            **kwargs: Additional backend-specific options
            
        Returns:
            TranscriptResult with segments containing timestamps and text
        """
        ...
    
    @property
    @abstractmethod
    def analyzer_name(self) -> str:
        """Human-readable name of the analyzer."""
        ...
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the analyzer is available (model loaded, API key set, etc.)."""
        ...
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """List of supported language codes (ISO 639-1)."""
        ...
    
    @property
    @abstractmethod
    def supports_timestamps(self) -> bool:
        """Whether the analyzer provides word/segment-level timestamps."""
        ...


@dataclass
class WhisperConfig:
    """Configuration for Whisper-based speech recognition."""
    model_size: str = "base"  # tiny, base, small, medium, large
    device: str = "cpu"  # cpu, cuda
    compute_type: str = "float32"  # float32, float16, int8
    language: Optional[str] = None
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.6


class WhisperSpeechAnalyzer:
    """Whisper-based speech analyzer.
    
    Uses the open-source Whisper model for local transcription.
    Supports multiple model sizes and compute configurations.
    
    Status: Available if whisper package is installed.
    """
    
    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.config = WhisperConfig(**config)
        self._model = None
        self._analyzer_name = f"Whisper ({self.config.model_size})"
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            return False
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    @property
    def supported_languages(self) -> List[str]:
        # Whisper supports 99+ languages
        return [
            "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
            "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
            "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
            "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
            "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
            "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
            "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
            "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
            "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
            "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"
        ]
    
    @property
    def supports_timestamps(self) -> bool:
        return True
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> "TranscriptResult":
        """Transcribe audio using Whisper."""
        if not self._available:
            return TranscriptResult(
                segments=[],
                status=SpeechRecognitionStatus.UNAVAILABLE,
                error_message="Whisper not installed. Install with: pip install openai-whisper",
            )
        
        try:
            import whisper
        except ImportError:
            return TranscriptResult(
                segments=[],
                status=SpeechRecognitionStatus.UNAVAILABLE,
                error_message="Whisper not installed. Install with: pip install openai-whisper",
            )
        
        # Load model if not already loaded
        if self._model is None:
            try:
                self._model = whisper.load_model(
                    self.config.model_size,
                    device=self.config.device,
                    download_root=None,
                )
            except Exception as e:
                return TranscriptResult(
                    segments=[],
                    status=SpeechRecognitionStatus.FAILED,
                    error_message=f"Failed to load Whisper model: {e}",
                )
        
        try:
            # Prepare options
            options = {
                "language": language or self.config.language,
                "beam_size": kwargs.get("beam_size", self.config.beam_size),
                "best_of": kwargs.get("best_of", self.config.best_of),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "compression_ratio_threshold": kwargs.get(
                    "compression_ratio_threshold", 
                    self.config.compression_ratio_threshold
                ),
                "log_prob_threshold": kwargs.get(
                    "log_prob_threshold", 
                    self.config.log_prob_threshold
                ),
                "no_speech_threshold": kwargs.get(
                    "no_speech_threshold", 
                    self.config.no_speech_threshold
                ),
                "word_timestamps": True,
            }
            
            # Run transcription in thread pool to avoid blocking
            import asyncio
            import functools
            
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                functools.partial(self._model.transcribe, audio_path, **options)
            )
            
            # Parse Whisper result into segments
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": segment.get("avg_logprob", 0.0),
                    "speaker_id": None,
                    "words": segment.get("words", []),
                })
            
            return TranscriptResult(
                segments=segments,
                language=result.get("language"),
                duration=result.get("duration"),
                status=SpeechRecognitionStatus.COMPLETED,
                model_name=f"whisper-{self.config.model_size}",
                model_version=whisper.__version__,
            )
            
        except Exception as e:
            return TranscriptResult(
                segments=[],
                status=SpeechRecognitionStatus.FAILED,
                error_message=f"Transcription failed: {e}",
            )


class WhisperAPISpeechAnalyzer:
    """OpenAI Whisper API speech analyzer.
    
    Uses the OpenAI Whisper API for transcription.
    Requires OPENAI_API_KEY environment variable.
    
    Status: Available if OPENAI_API_KEY is set.
    """
    
    def __init__(self):
        self._analyzer_name = "Whisper API (OpenAI)"
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        import os
        return bool(os.getenv("OPENAI_API_KEY"))
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    @property
    def supported_languages(self) -> List[str]:
        # OpenAI Whisper API supports similar languages
        return [
            "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
            "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
            # ... (same as Whisper local)
        ]
    
    @property
    def supports_timestamps(self) -> bool:
        return True
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> "TranscriptResult":
        if not self._available:
            return TranscriptResult(
                segments=[],
                status=SpeechRecognitionStatus.UNAVAILABLE,
                error_message="OPENAI_API_KEY not set. Set environment variable to use Whisper API.",
            )
        
        try:
            import openai
            client = openai.AsyncOpenAI()
            
            with open(audio_path, "rb") as audio_file:
                response = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"],
                )
            
            segments = []
            for segment in response.segments:
                segments.append({
                    "start_time": segment.start,
                    "end_time": segment.end,
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, "avg_logprob", 0.0),
                    "speaker_id": None,
                    "words": getattr(segment, "words", []),
                })
            
            return TranscriptResult(
                segments=segments,
                language=response.language,
                duration=response.duration,
                status=SpeechRecognitionStatus.COMPLETED,
                model_name="whisper-1 (API)",
                model_version="1.0",
            )
            
        except Exception as e:
            return TranscriptResult(
                segments=[],
                status=SpeechRecognitionStatus.FAILED,
                error_message=f"API transcription failed: {e}",
            )


class UnavailableSpeechAnalyzer:
    """Fallback analyzer when no speech recognition is available."""
    
    def __init__(self, reason: str = "No speech analyzer available"):
        self._analyzer_name = "UnavailableSpeechAnalyzer"
        self._reason = reason
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def is_available(self) -> bool:
        return False
    
    @property
    def supported_languages(self) -> List[str]:
        return []
    
    @property
    def supports_timestamps(self) -> bool:
        return False
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> "TranscriptResult":
        return TranscriptResult(
            segments=[],
            status=SpeechRecognitionStatus.UNAVAILABLE,
            error_message=self._reason,
        )


# Factory function
_speech_analyzer: Optional[SpeechAnalyzer] = None


def get_speech_analyzer() -> SpeechAnalyzer | UnavailableSpeechAnalyzer:
    global _speech_analyzer
    if _speech_analyzer is None:
        try:
            analyzer = WhisperSpeechAnalyzer()
            _speech_analyzer = analyzer if analyzer.is_available else UnavailableSpeechAnalyzer(
                "Whisper is not installed; transcription was skipped"
            )
        except Exception as exc:
            _speech_analyzer = UnavailableSpeechAnalyzer(str(exc))
    return _speech_analyzer


# Export for compatibility
SpeechAnalyzerProtocol = SpeechAnalyzer
