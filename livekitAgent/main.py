import asyncio
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession
from livekit.plugins import google, silero, groq, cartesia
from dotenv import load_dotenv
from functools import partial
from data_class.interview_data import InterviewData
from Agent.agent import STTRefiningAgent
from config.config import STT_REFINING_INSTRUCTIONS
from RPC.agent_rpc import confirm_answer, skip_question, re_answer
from test2 import CustomTTS
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_entrypoint")
load_dotenv()


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info("🚀 Starting interview session...")
    
    interview_data = InterviewData()

    session = AgentSession[InterviewData](
        userdata=interview_data,
        # stt=CustomSTT("medium"),
        stt = groq.STT(model="whisper-large-v3-turbo",language="en"),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=CustomTTS(),
        # tts=cartesia.TTS(),
        vad=silero.VAD.load()
    )

    
    
    # Store the STT refining agent in interview_data for easy access
    interview_data.refining_agent = STTRefiningAgent(instructions=STT_REFINING_INSTRUCTIONS)

    #----------------------Registering the RPC methods-------------------------
    lp = ctx.room.local_participant
    lp.register_rpc_method(
        "confirm_answer",
        partial(confirm_answer, session=session)
    )
    lp.register_rpc_method(
        "re_answer",
        partial(re_answer, session=session)
    )
    lp.register_rpc_method(
        "skip_question",
        partial(skip_question, session=session)
    )

    #---------Starting Agent session-------------
    await session.start(
        agent=interview_data.refining_agent,
        room=ctx.room
    )

    logger.info(f"Resume : {interview_data.resume_data}")
    #-------------------sending agent-ready message to participants-------------
    await asyncio.sleep(1)  # optional buffer
    await ctx.room.local_participant.publish_data(
        b"agent-ready",
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
