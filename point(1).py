import asyncio
from typing import Optional
from livekit.agents import JobContext, WorkerOptions, cli, ChatContext
from livekit.agents.llm import function_tool, ChatItem, ChatContent
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import google, silero, groq, cartesia
import json
from dataclasses import dataclass, field
import random
from dotenv import load_dotenv
from functools import partial
from pymongo import MongoClient
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test2")
load_dotenv()

def get_latest_resume():
    try:
        logger.info("Attempting to connect to MongoDB...")
        client = MongoClient('mongodb://localhost:27017/')
        db = client['interview_db']
        collection = db['resumes']
        logger.info("Connected to MongoDB successfully")
        
        all_docs = list(collection.find())
        logger.info(f"Total documents found: {len(all_docs)}")
        for doc in all_docs:
            logger.info(f"Document: {doc}")
        
        latest_resume = collection.find().sort([('id', -1)]).limit(1)
        resume_data = list(latest_resume)
        logger.info(f"Found {len(resume_data)} resume records")
        
        if resume_data:
            resume_content = resume_data[0].get('resume', '')
            logger.info(f"Resume content length: {len(resume_content)}")
            logger.info(f"Resume preview: {resume_content[:200]}...")
            return resume_content
        else:
            logger.warning("No resume data found in database")
            return ''
    except Exception as e:
        logger.error(f"Error fetching resume: {e}")
        return ''

def question_bank_loader():
    with open('questions.json', 'r') as file:
        return json.load(file)

def select_questions(question_bank, num_easy=2, num_medium=2, num_hard=1):
    easy_qs = [q for q in question_bank if q['difficulty'] == 'basic']
    medium_qs = [q for q in question_bank if q['difficulty'] == 'intermediate']
    hard_qs = [q for q in question_bank if q['difficulty'] == 'advanced']

    selected = []
    selected.extend(random.sample(easy_qs, min(num_easy, len(easy_qs))))
    selected.extend(random.sample(medium_qs, min(num_medium, len(medium_qs))))
    selected.extend(random.sample(hard_qs, min(num_hard, len(hard_qs))))

    return selected

def get_next_question(interview_data):
    logger.info(f"get_next_question called. current_question: {interview_data.current_question}")

    if interview_data.current_question == 0:
        interview_data.current_question += 1
        return "Ask Resume Based Question 1"
    elif interview_data.current_question == 1:
        interview_data.current_question += 1
        return "Ask Resume Based Question 2"
    elif interview_data.current_question == 2:
        interview_data.current_question += 1
        return "Ask Resume Based Question 3"
    elif interview_data.current_question == 3:
        interview_data.current_question += 1
        return interview_data.pre_define_questions[0]
    
    if interview_data.current_question - 3 >= len(interview_data.pre_define_questions):
        return "Interview End"
    
    if interview_data.number_of_follow_ups < 1:
        interview_data.number_of_follow_ups += 1
        return "Ask a Follow Up"

    interview_data.current_question += 1
    interview_data.number_of_follow_ups = 0        
    return interview_data.pre_define_questions[interview_data.current_question - 4]

resume_data = get_latest_resume()
logger.info(f"Resume data loaded: {len(resume_data)} characters")
logger.info(f"Resume data preview: {resume_data[:100]}...")

interview_instructions = f"""
Your role is to conduct an interview using a predefined set of questions.
When a question is provided in the prompt, return it exactly as given. Do not generate new questions unless explicitly instructed to do so.
If the prompt asks you to generate a follow-up question, create one that is directly related to the candidate's previous responses and the overall context of the interview.
Always follow the instructions provided in the prompt carefully.

CANDIDATE RESUME INFORMATION:
{resume_data}

Use the above resume information to ask relevant questions and provide context during the interview. Consider the candidate's experience, skills, and background when asking questions.

Output format: Return only the question string. Do not include any symbols, commentary, or additional text.
""" 

@dataclass
class InterviewData:
    current_question: int = 0
    number_of_follow_ups: int = 0
    pre_define_questions: list[dict[str, str]] = field(default_factory=lambda: select_questions(question_bank_loader()))
    refining_agent: Optional[Agent] = None
    base_agent: Optional[Agent] = None
    qna_history: list[dict[str, str]] = field(default_factory=list)
    interview_history: ChatContext = field(default_factory=lambda: ChatContext.from_dict({"items":[{"type":"message","role":"system", "content":[interview_instructions]}]}))

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
    
    @function_tool
    async def get_question(self):
        interview_data = self.session.userdata
        return get_next_question(interview_data)

class STTRefiningAgent(Agent):
    def __init__(self, instructions):
        super().__init__(
            instructions="""You are a Voice-to-Voice AI Agent. 
            Be concise and to the point.\n\n""" + instructions
        )

async def confirm_answer(payload, session: AgentSession):
    try:
        interview_data: InterviewData = session.userdata
        logger.info("🔵 Starting confirm_answer process...")
        
        if not (payload.payload == "first_request"):
            if interview_data.qna_history:
                interview_data.qna_history[-1]["answer"] = payload.payload
                logger.info("💾 Saved previous answer to QnA history")

        stt_refining_agent = session.current_agent
        logger.info("📝 Stored reference to STT refining agent")
        
        if not interview_data.base_agent:
            interview_data.base_agent = BaseAgent(
                instructions=interview_instructions, 
                chat_context=interview_data.interview_history
            )
            logger.info("🆕 Created new BaseAgent instance")
        
        logger.info("🔄 Switching to BaseAgent...")
        session.update_agent(interview_data.base_agent)
        
        await asyncio.sleep(0.5)
        
        logger.info("🎯 Getting next question using tool...")
        next_question = get_next_question(interview_data)
        
        if next_question not in ["Ask a Follow Up", "Ask Resume Based Question 1", "Ask Resume Based Question 2", "Ask Resume Based Question 3", "Interview End"]:
            interview_data.qna_history.append({
                "question": next_question.get("question", next_question) if isinstance(next_question, dict) else next_question,
                "answer": ""
            })
        
        logger.info(f"🎯 BaseAgent asking question: {next_question}")
        if next_question == "Interview End":
            await session.generate_reply(
                instructions="The interview is complete. Provide a summary of the candidate's performance and final scores."
            )
        elif next_question == "Ask a Follow Up":
            await session.generate_reply(
                instructions="Ask a follow-up question based on the candidate's previous answer to get more details or clarification."
            )
        elif next_question == "Ask Resume Based Question 1":
            await session.generate_reply(
                instructions="Based on the candidate's resume, ask about their current role and responsibilities. Start with 'In your resume, you mentioned that you are currently working as...' and ask about their specific responsibilities and achievements in that role."
            )
        elif next_question == "Ask Resume Based Question 2":
            await session.generate_reply(
                instructions="Based on the candidate's resume, ask about their technical skills and experience. Start with 'I see in your resume that you have experience with...' and ask them to elaborate on their proficiency with specific technologies mentioned in their resume."
            )
        elif next_question == "Ask Resume Based Question 3":
            await session.generate_reply(
                instructions="Based on the candidate's resume, ask about their educational background or certifications. Start with 'Your resume shows that you have...' and ask about how their education or certifications have prepared them for this role."
            )
        else:
            question_text = next_question.get("question", next_question) if isinstance(next_question, dict) else next_question
            await session.generate_reply(
                instructions=f"Ask this exact question to the candidate: {question_text}"
            )
        
        await asyncio.sleep(1.5)
        interview_data.interview_history = session.current_agent.chat_ctx
        logger.info("🔄 Switching back to STT refining agent...")
        session.update_agent(stt_refining_agent)
        
        logger.info("✅ Successfully completed agent switching cycle")
        
    except Exception as e:
        logger.error(f"❌ Error in confirm_answer: {e}")
        if 'stt_refining_agent' in locals():
            session.update_agent(stt_refining_agent)

async def skip_question(payload, session):
    interview_data: InterviewData = session.userdata
    logger.info("⏭️ Skipping question...")
    
    if interview_data.qna_history:
        interview_data.qna_history[-1]["answer"] = "[Question Skipped]"
    
    stt_refining_agent = session.current_agent
    
    if not interview_data.base_agent:
        interview_data.base_agent = BaseAgent(
            instructions=interview_instructions,
            chat_context=interview_data.interview_history
        )
    
    session.update_agent(interview_data.base_agent)
    await asyncio.sleep(0.5)
    
    next_question = get_next_question(interview_data)
    
    if next_question not in ["Ask a Follow Up", "Ask Resume Based Question 1", "Ask Resume Based Question 2", "Ask Resume Based Question 3", "Interview End"]:
        interview_data.qna_history.append({
            "question": next_question.get("question", next_question) if isinstance(next_question, dict) else next_question,
            "answer": "[Question Skipped]"
        })
    
    if next_question == "Interview End":
        await session.generate_reply(
            instructions="The interview is complete. Provide a summary of the candidate's performance and final scores."
        )
    elif next_question == "Ask a Follow Up":
        await session.generate_reply(
            instructions="Ask a follow-up question based on the candidate's previous answer to get more details or clarification."
        )
    elif next_question == "Ask Resume Based Question 1":
        await session.generate_reply(
            instructions="Based on the candidate's resume, ask about their current role and responsibilities. Start with 'In your resume, you mentioned that you are currently working as...' and ask about their specific responsibilities and achievements in that role."
        )
    elif next_question == "Ask Resume Based Question 2":
        await session.generate_reply(
            instructions="Based on the candidate's resume, ask about their technical skills and experience. Start with 'I see in your resume that you have experience with...' and ask them to elaborate on their proficiency with specific technologies mentioned in their resume."
        )
    elif next_question == "Ask Resume Based Question 3":
        await session.generate_reply(
            instructions="Based on the candidate's resume, ask about their educational background or certifications. Start with 'Your resume shows that you have...' and ask about how their education or certifications have prepared them for this role."
        )
    else:
        question_text = next_question.get("question", next_question) if isinstance(next_question, dict) else next_question
        await session.generate_reply(
            instructions=f"Ask this exact question to the candidate: {question_text}"
        )
    
    await asyncio.sleep(1.5)
    
    session.update_agent(stt_refining_agent)
    
    return f"Skipped question with payload: {payload.payload}"

async def re_answer(payload, session):
    logger.info("🔄 Re-answering question...")
    return "Please provide your answer again"

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info("🚀 Starting interview session...")
    
    interview_data = InterviewData()

    session = AgentSession[InterviewData](
        userdata=interview_data,
        stt=groq.STT(model="whisper-large-v3-turbo",language="en"),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=cartesia.TTS(),
        vad=silero.VAD.load()
    )

    stt_refining_instructions = """
    Your role is to refine the speech input (e.g., STT output) exactly as if the user is speaking.
    - Clean the input by removing repetitions, filler words, and speech disfluencies (e.g., "uh," "like," stutters), while keeping the original intent and tone.
    - Do not add new information, explanations, or rephrase into formal language.
    - Maintain the structure and flow of natural spoken language.
    Output format: A refined version of the user's input in the first person, as if the user just spoke it fluently.
    """

    interview_data.refining_agent = STTRefiningAgent(instructions=stt_refining_instructions)

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

    await session.start(
        agent=interview_data.refining_agent,
        room=ctx.room
    )

    await asyncio.sleep(1)
    await ctx.room.local_participant.publish_data(
        b"agent-ready",
    )

InterviewData()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))