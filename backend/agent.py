from __future__ import annotations
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm
)
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai, noise_cancellation, silero
from dotenv import load_dotenv
from prompts import WELCOME_MESSAGE, INSTRUCTIONS, LOOKUP_VIN_MESSAGE
import os
from livekit.agents.stt import STT, SpeechEvent
from faster_whisper import WhisperModel
from livekit.agents.tts import TTS
from TTS.api import TTS as CoquiTTS
import tempfile

class CoquiTTSPlugin(TTS):
    def __init__(self, model_name="tts_models/en/ljspeech/tacotron2-DDC"):
        self.tts = CoquiTTS(model_name)

    async def synthesize(self, text: str) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
            self.tts.tts_to_file(text=text, file_path=tmpfile.name)
            tmpfile.seek(0)
            return tmpfile.read()

class FastWhisperSTT(STT):
    def __init__(self, model_size="medium", language="en"):
        self.model = WhisperModel(model_size, compute_type="int8")
        self.language = language

    async def transcribe(self, audio: bytes) -> SpeechEvent:
        segments, _ = self.model.transcribe(audio, language=self.language)
        text = " ".join([seg.text for seg in segments])
        return SpeechEvent(text=text)

load_dotenv()
print("GROQ_API_KEY:", os.getenv("GROQ_API_KEY"))
async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    # session = AgentSession(
    #     stt=groq.STT( 
    #         model="whisper-large-v3",
    #         language="en",
    #         api_key=os.getenv("GROQ_API_KEY")
    # ),
    #     llm=openai.LLM.with_ollama(model="llama3.2", base_url="http://localhost:11434/v1"),
    #     tts=cartesia.TTS(api_key=os.getenv("CARTESIA_API_KEY")),
    #     vad=silero.VAD.load(),
    #     # turn_detection=MultilingualModel(),
    # )
    session = AgentSession(
        stt=FastWhisperSTT(model_size="medium", language="en"),
        llm=openai.LLM.with_ollama(model="llama3", base_url="http://localhost:11434/v1"),
        tts=CoquiTTSPlugin(),
        vad=silero.VAD.load(),
    )
    await session.start(
        room=ctx.room,
        agent=Agent(instructions="You are a helpful voice AI assistant."),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))