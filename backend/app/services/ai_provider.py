from abc import ABC, abstractmethod
from typing import Dict, Any


class AIProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generates text from a given prompt."""
        ...

    @abstractmethod
    async def analyze_vision(
        self, image_url_or_path: str, prompt: str, **kwargs
    ) -> str:
        """Analyzes an image and returns a text result based on the prompt."""
        ...

    @abstractmethod
    async def process_audio(self, audio_url_or_path: str, **kwargs) -> Dict[str, Any]:
        """Processes audio (e.g., transcription) and returns structured data."""
        ...


class MockAIProvider(AIProvider):
    async def generate_text(self, prompt: str, **kwargs) -> str:
        return f"Mock response for prompt: {prompt[:20]}..."

    async def analyze_vision(
        self, image_url_or_path: str, prompt: str, **kwargs
    ) -> str:
        return "Mock vision analysis result."

    async def process_audio(self, audio_url_or_path: str, **kwargs) -> Dict[str, Any]:
        return {
            "transcript": "Mock audio transcript.",
            "confidence": 0.99,
        }
