import os
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Any

from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

_sync_client: Optional[OpenAI] = None
_async_client: Optional[AsyncOpenAI] = None


def _get_async_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    global _async_client
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. AI features are disabled until this is configured."
        )
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=key)
    return _async_client


def _get_sync_client(api_key: Optional[str] = None) -> OpenAI:
    global _sync_client
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. AI features are disabled until this is configured."
        )
    if _sync_client is None:
        _sync_client = OpenAI(api_key=key)
    return _sync_client


# ---------------------------------------------------------------------------
# Message / content types
# ---------------------------------------------------------------------------

@dataclass
class ImageContent:
    """Mirrors emergentintegrations.llm.chat.ImageContent"""
    image_base64: str


@dataclass
class UserMessage:
    """
    Mirrors emergentintegrations.llm.chat.UserMessage.
    Original call sites use either `text=` or `content=` as the keyword for
    the message body - both are accepted here for compatibility.
    file_contents holds a list of ImageContent for vision calls.
    """
    text: Optional[str] = None
    content: Optional[str] = None
    file_contents: List[ImageContent] = field(default_factory=list)

    @property
    def body(self) -> str:
        return self.text if self.text is not None else (self.content or "")


@dataclass
class _ChatResponse:
    """Returned by send_async() - mirrors the object emergentintegrations returned,
    which exposes a `.text` attribute (confirmed via response.text usage in server.py)."""
    text: str


def _build_openai_messages(system_message: Optional[str], user_message: UserMessage) -> list:
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})

    if user_message.file_contents:
        content_parts = [{"type": "text", "text": user_message.body}]
        for img in user_message.file_contents:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img.image_base64}"},
            })
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": user_message.body})

    return messages


class LlmChat:
    """
    Mirrors emergentintegrations.llm.chat.LlmChat.

    Original usage patterns supported:
        LlmChat(api_key=..., session_id=...)
        LlmChat(api_key=..., session_id=..., system_message="...")
        LlmChat(api_key=..., model="gpt-4o-mini")
        LlmChat(...).with_model("openai", "gpt-4o-mini")
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.model = model or self.DEFAULT_MODEL
        self._history: List[dict] = []

    def with_model(self, provider: str, model: str) -> "LlmChat":
        """Original signature: .with_model('openai', 'gpt-4o-mini'). Provider is
        accepted for interface compatibility but we only support OpenAI here."""
        self.model = model
        return self

    def add_message(self, message: UserMessage) -> None:
        """Used by the WhatsApp bot's llm.add_message(...) + llm.chat pattern."""
        self._history.append({"role": "user", "content": message.body})

    async def send_async(self, message: UserMessage) -> _ChatResponse:
        """Returns an object with `.text` - matches original send_async contract."""
        client = _get_async_client(self.api_key)
        messages = _build_openai_messages(self.system_message, message)
        completion = await client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        text = completion.choices[0].message.content or ""
        return _ChatResponse(text=text)

    async def send_message(self, message: UserMessage) -> str:
        """Returns a plain string - matches original send_message contract."""
        response = await self.send_async(message)
        return response.text

    def chat(self, message: Optional[str] = None) -> str:
        """
        Sync fallback used in one call site via asyncio.to_thread(llm.chat).
        Uses internal history built via add_message().
        """
        client = _get_sync_client(self.api_key)
        messages = []
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})
        messages.extend(self._history)
        if message:
            messages.append({"role": "user", "content": message})
        completion = client.chat.completions.create(model=self.model, messages=messages)
        return completion.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Speech-to-text / text-to-speech
# ---------------------------------------------------------------------------

class OpenAISpeechToText:
    """Mirrors emergentintegrations.llm.openai.OpenAISpeechToText (Whisper)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def transcribe(self, audio_file, language: Optional[str] = None) -> _ChatResponse:
        """
        audio_file: a file-like object (e.g. BytesIO with .name set), matching
        the original usage: stt = OpenAISpeechToText(...); await stt.transcribe(audio_file)
        Returns object with `.text` per original contract (response.text seen at
        server.py line ~18217-18218).
        """
        client = _get_async_client(self.api_key)
        kwargs = {"model": "whisper-1", "file": audio_file}
        if language:
            kwargs["language"] = language
        transcript = await client.audio.transcriptions.create(**kwargs)
        return _ChatResponse(text=transcript.text)


class OpenAITextToSpeech:
    """Mirrors emergentintegrations.llm.openai.OpenAITextToSpeech."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def generate_speech(self, text: str, model: str = "tts-1", voice: str = "alloy") -> bytes:
        """Returns raw audio bytes - matches original generate_speech contract."""
        client = _get_async_client(self.api_key)
        response = await client.audio.speech.create(model=model, voice=voice, input=text)
        return response.read()

    async def generate_speech_base64(self, text: str, model: str = "tts-1", voice: str = "alloy") -> str:
        """Returns base64-encoded audio - matches original generate_speech_base64 contract."""
        audio_bytes = await self.generate_speech(text=text, model=model, voice=voice)
        return base64.b64encode(audio_bytes).decode("utf-8")