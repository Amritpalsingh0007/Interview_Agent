import asyncio
from typing import Optional
from livekit.agents import JobContext, WorkerOptions, cli, ChatContext
from livekit.agents.llm import function_tool, ChatItem, ChatContent
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import google, silero
import json
from dataclasses import dataclass, field
import random
from dotenv import load_dotenv
from functools import partial
from test2 import CustomSTT, CustomTTS
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test2")
load_dotenv()

#----------------------------Helper methods--------------------------------
def question_bank_loader():
    with open('questions.json', 'r') as file:
        return json.load(file)

def select_questions(question_bank, num_easy=2, num_medium=2, num_hard=1):
    # Filter questions by difficulty
    easy_qs = [q for q in question_bank if q['difficulty'] == 'basic']
    medium_qs = [q for q in question_bank if q['difficulty'] == 'intermediate']
    hard_qs = [q for q in question_bank if q['difficulty'] == 'advanced']

    # Randomly select questions without repetition
    selected = []
    selected.extend(random.sample(easy_qs, min(num_easy, len(easy_qs))))
    selected.extend(random.sample(medium_qs, min(num_medium, len(medium_qs))))
    selected.extend(random.sample(hard_qs, min(num_hard, len(hard_qs))))

    return selected

# Standalone function to handle question logic
def get_next_question(interview_data):
    """Get the next question based on current interview state"""
    logger.info(f"get_next_question called. current_question: {interview_data.current_question}")

    if interview_data.current_question == 0:
        interview_data.current_question += 1
        return interview_data.pre_define_questions[0]
    
    if interview_data.current_question == len(interview_data.pre_define_questions):
        return "Interview End"
    
    if interview_data.number_of_follow_ups < 1:
        interview_data.number_of_follow_ups += 1
        return "Ask a Follow Up"

    interview_data.current_question += 1
    interview_data.number_of_follow_ups = 0        
    return interview_data.pre_define_questions[interview_data.current_question - 1]

#---------------------------Agent Instructions--------------------------

interview_instructions = """
Your role is to conduct an interview using a predefined set of questions.
When a question is provided in the prompt, return it exactly as given. Do not generate new questions unless explicitly instructed to do so.
If the prompt asks you to generate a follow-up question, create one that is directly related to the candidate's previous responses and the overall context of the interview.
Always follow the instructions provided in the prompt carefully.
Output format: Return only the question string. Do not include any symbols, commentary, or additional text.
""" 

#----------------------------DATA Class----------------------------------
@dataclass
class InterviewData:
    current_question: int = 0
    number_of_follow_ups: int = 0
    pre_define_questions: list[dict[str, str]] = field(default_factory=lambda: select_questions(question_bank_loader()))
    refining_agent: Optional[Agent] = None
    base_agent: Optional[Agent] = None
    qna_history: list[dict[str, str]] = field(default_factory=list)
    interview_history: ChatContext = field(default_factory=lambda: ChatContext.from_dict({"items":[{"type":"message","role":"system", "content":[interview_instructions]}]}))

#-----------------------------BASE Agent-------------------------------------
class BaseAgent(Agent):
    def __init__(self, instructions, chat_context=None):
        instructions="""You are a Voice-to-Voice AI Agent. 
                Be concise and to the point.\n\n""" + instructions
        if chat_context:
            super().__init__(
                instructions=instructions,
                chat_ctx = chat_context
            )
        else:
            super().__init__(
                instructions=instructions
            )

    # Remove automatic on_enter to prevent unwanted responses
    # We'll manually trigger the reply generation when needed
    
    @function_tool
    async def get_question(self):
        """Tool function that uses the session's userdata"""
        interview_data = self.session.userdata
        return get_next_question(interview_data)

class STTRefiningAgent(Agent):
    def __init__(self, instructions):
        super().__init__(
            instructions="""You are a Voice-to-Voice AI Agent. 
            Be concise and to the point.\n\n""" + instructions
        )

#--------------------------------RPC Methods---------------------------------
async def confirm_answer(payload, session: AgentSession):
    try:
        interview_data: InterviewData = session.userdata
        logger.info("🔵 Starting confirm_answer process...")
        
        # Step 1: Save the current STT refining agent
        if not (payload.payload == "first_request"):
            # Save the answer from the previous question
            if interview_data.qna_history:
                interview_data.qna_history[-1]["answer"] = payload.payload
                logger.info("💾 Saved previous answer to QnA history")

        # Step 2: Store reference to current STT refining agent
        stt_refining_agent = session.current_agent
        logger.info("📝 Stored reference to STT refining agent")
        
        # Step 3: Create and switch to BaseAgent
        if not interview_data.base_agent:
            interview_data.base_agent = BaseAgent(
                instructions=interview_instructions, 
                chat_context=interview_data.interview_history
            )
            logger.info("🆕 Created new BaseAgent instance")
        
        logger.info("🔄 Switching to BaseAgent...")
        session.update_agent(interview_data.base_agent)
        
        # Step 4: Wait for agent switch to complete
        await asyncio.sleep(0.1)  # Minimal wait for agent switch
        
        # Step 5: Get the question directly using the tool function
        logger.info("🎯 Getting next question using tool...")
        next_question = get_next_question(interview_data)
        
        # Step 6: Add question to QnA history if it's a new question
        if next_question not in ["Ask a Follow Up", "Interview End"]:
            interview_data.qna_history.append({
                "question": next_question.get("question", next_question) if isinstance(next_question, dict) else next_question,
                "answer": ""
            })
        
        # Step 7: Generate reply with the specific question
        logger.info(f"🎯 BaseAgent asking question: {next_question}")
        if next_question == "Interview End":
            await session.generate_reply(
                instructions="The interview is complete. Provide a summary of the candidate's performance and final scores."
            )
        elif next_question == "Ask a Follow Up":
            await session.generate_reply(
                instructions="Ask a follow-up question based on the candidate's previous answer to get more details or clarification."
            )
        else:
            # Extract question text if it's a dict
            question_text = next_question.get("question", next_question) if isinstance(next_question, dict) else next_question
            await session.generate_reply(
                instructions=f"Ask this exact question to the candidate: {question_text}"
            )
        
        # Step 8: Wait for reply completion
        await asyncio.sleep(0.5)  # Reduced wait time
        interview_data.interview_history = session.current_agent.chat_ctx
        # Step 7: Switch back to STT refining agent
        logger.info("🔄 Switching back to STT refining agent...")
        session.update_agent(stt_refining_agent)
        
        logger.info("✅ Successfully completed agent switching cycle")
        
    except Exception as e:
        logger.error(f"❌ Error in confirm_answer: {e}")
        # Ensure we're back on the refining agent even if there's an error
        if 'stt_refining_agent' in locals():
            session.update_agent(stt_refining_agent)

async def skip_question(payload, session):
    interview_data: InterviewData = session.userdata
    logger.info("⏭️ Skipping question...")
    
    # Mark current question as skipped
    if interview_data.qna_history:
        interview_data.qna_history[-1]["answer"] = "[Question Skipped]"
    
    # Use similar switching logic as confirm_answer
    stt_refining_agent = session.current_agent
    
    if not interview_data.base_agent:
        interview_data.base_agent = BaseAgent(
            instructions=interview_instructions,
            chat_context=interview_data.interview_history
        )
    
    session.update_agent(interview_data.base_agent)
    await asyncio.sleep(0.1)
    
    # Get the question directly
    next_question = get_next_question(interview_data)
    
    # Add to QnA history if it's a new question
    if next_question not in ["Ask a Follow Up", "Interview End"]:
        interview_data.qna_history.append({
            "question": next_question.get("question", next_question) if isinstance(next_question, dict) else next_question,
            "answer": "[Question Skipped]"
        })
    
    # Generate appropriate response
    if next_question == "Interview End":
        await session.generate_reply(
            instructions="The interview is complete. Provide a summary of the candidate's performance and final scores."
        )
    elif next_question == "Ask a Follow Up":
        await session.generate_reply(
            instructions="Ask a follow-up question based on the candidate's previous answer to get more details or clarification."
        )
    else:
        question_text = next_question.get("question", next_question) if isinstance(next_question, dict) else next_question
        await session.generate_reply(
            instructions=f"Ask this exact question to the candidate: {question_text}"
        )
    
    await asyncio.sleep(0.5)
    
    session.update_agent(stt_refining_agent)
    
    return f"Skipped question with payload: {payload.payload}"

async def re_answer(payload, session):
    logger.info("🔄 Re-answering question...")
    # For re-answer, we just stay on the STT refining agent
    # and let the user provide a new answer
    return "Please provide your answer again"

#------------------------------------------------------------------------------

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info("🚀 Starting interview session...")
    
    interview_data = InterviewData()

    session = AgentSession[InterviewData](
        userdata=interview_data,
        stt=CustomSTT("medium"),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=CustomTTS(),
        vad=silero.VAD.load()
    )

    stt_refining_instructions = """
    Your role is to refine the speech input (e.g., STT output) exactly as if the user is speaking.
    - Clean the input by removing repetitions, filler words, and speech disfluencies (e.g., "uh," "like," stutters), while keeping the original intent and tone.
    - Do not add new information, explanations, or rephrase into formal language.
    - Maintain the structure and flow of natural spoken language.
    Output format: A refined version of the user's input in the first person, as if the user just spoke it fluently.
    """

    # Store the STT refining agent in interview_data for easy access
    interview_data.refining_agent = STTRefiningAgent(instructions=stt_refining_instructions)

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

    #-------------------sending agent-ready message to participants-------------
    await asyncio.sleep(1)  # optional buffer
    await ctx.room.local_participant.publish_data(
        b"agent-ready",
    )

InterviewData()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
