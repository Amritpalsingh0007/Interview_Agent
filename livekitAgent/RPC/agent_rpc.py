
from livekit.agents import AgentSession
from data_class.interview_data import InterviewData
from Agent.agent import BaseAgent
from config.config import INTERVIEW_INSTRUCTIONS
from data_class.interview_data import get_next_question, InterviewPrompt
import asyncio
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_rpc.py")




#--------------------------------RPC Methods---------------------------------
async def confirm_answer(payload, session: AgentSession):
    try:
        interview_data: InterviewData = session.userdata
        logger.info("🔵 Starting confirm_answer process...")
        logger.info(f"here is the resume data {interview_data.resume_data}")
        # Step 1: Save the current STT refining agent
        if not (payload.payload == "first_request"):
            # Save the answer from the previous question
            if interview_data.qna_history:
                interview_data.qna_history.append({"question":interview_data.interview_history.items[-1]["content"],"answer":payload.payload})
                logger.info("💾 Saved previous answer to QnA history")
            
            interview_data.interview_history.add_message(role="user", content=payload.payload)
        
        
        # Step 2: Store reference to current STT refining agent
        stt_refining_agent = session.current_agent
        logger.info("📝 Stored reference to STT refining agent")
       
        # Step 3: Create and switch to BaseAgent
        base_agent = BaseAgent(
                instructions=INTERVIEW_INSTRUCTIONS.format(resume_data=interview_data.resume_data),
                chat_context=interview_data.interview_history
            )
       
        logger.info("🔄 Switching to BaseAgent...")
        session.update_agent(base_agent)

        # Step 4: Wait for agent switch to complete
        await asyncio.sleep(0.1)  # Minimal wait for agent switch
       
        # Step 5: Get the question directly using the tool function
        logger.info("🎯 Getting next question using tool...")
        next_question = get_next_question(interview_data)
       
        # Step 6: Generate reply with the specific question
        logger.info(f"🎯 BaseAgent asking question: {next_question}")
        if next_question == InterviewPrompt.INTERVIEW_END:
            await session.generate_reply(
                instructions="The interview is complete. Provide a summary of the candidate's performance and final scores."
            )
        elif next_question == InterviewPrompt.ASK_FOLLOW_UP:
            await session.generate_reply(
                instructions="Ask a follow-up question based on the candidate's previous answer to get more details or clarification."
            )
        elif next_question == InterviewPrompt.ASK_RESUME_QUESTION:
            await session.generate_reply(
                instructions="""Based on the candidate's resume, ask a relevant and specific question about their experience, skills, education, or projects.
Vary the focus each time to cover different aspects of the resume and avoid repetition."""
            )
        else:
            # Extract question text if it's a dict
            logger.info(f"asking a predefine question: {next_question}")
            question_text = next_question.get("question", next_question) if isinstance(next_question, dict) else next_question
            await session.generate_reply(
                instructions=f"Do not use any context and only ask this exact question to the candidate : {question_text}"
            )
        
        
       
        # Step 8: Wait for reply completion
        await asyncio.sleep(0.5)  # Reduced wait time
        interview_data.interview_history = session.current_agent.chat_ctx.copy()
       
        # if next_question == "Interview End":
        interview_history_json = []
        for item in session.current_agent.chat_ctx.items:
            interview_history_json.append({item.role : item.content})
        with open("interview_history.json","w") as fp:
            json.dump(interview_history_json, fp, ensure_ascii=False, indent=2)
        with open("interview_qna.json", "w") as fp:
                json.dump(interview_data.qna_history, fp, ensure_ascii=False, indent= 2)
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
 
    #skipping to the next predefine question question
    interview_data.number_of_follow_ups = 99
    # Mark current question as skipped
    if interview_data.qna_history:
        interview_data.qna_history.append({"question":interview_data.interview_history.items[-1]["content"],"answer":"[Question Skipped]"})
    interview_data.interview_history.add_message("user", "[Question Skipped]")
   
    # Use similar switching logic as confirm_answer
    stt_refining_agent = session.current_agent

    base_agent = None
    if not interview_data.interview_history:
        base_agent = BaseAgent(
            instructions=INTERVIEW_INSTRUCTIONS.format(resume_data=interview_data.resume_data),
            chat_context=interview_data.interview_history
        )
    else:
        base_agent = BaseAgent(chat_context=interview_data.interview_history)
    session.update_agent(base_agent)
    await asyncio.sleep(0.1)
   
    # Get the question directly
    next_question = get_next_question(interview_data)
   
    # Generate appropriate response
    if next_question == InterviewPrompt.INTERVIEW_END:
        await session.generate_reply(
            instructions="The interview is complete. Provide a summary of the candidate's performance and final scores."
        )
    elif next_question == InterviewPrompt.ASK_FOLLOW_UP:
        await session.generate_reply(
            instructions="Ask a follow-up question based on the candidate's previous answer to get more details or clarification."
        )
    elif next_question == InterviewPrompt.ASK_RESUME_QUESTION:
        await session.generate_reply(
                instructions="""Based on the candidate's resume, ask a relevant and specific question about their experience, skills, education, or projects.
Vary the focus each time to cover different aspects of the resume and avoid repetition."""
            ) 
    else:
        question_text = next_question.get("question", next_question) if isinstance(next_question, dict) else next_question
        await session.generate_reply(
            instructions=f"Ask this exact question to the candidate: {question_text}"
        )
   
    await asyncio.sleep(0.5)
    
    # if next_question == "Interview End":
    with open("interview_qna.json", "w") as fp:
            json.dump(interview_data.qna_history, fp, ensure_ascii=False, indent= 2)
    interview_data.interview_history = session.current_agent.chat_ctx.copy()
    session.current_agent.chat_ctx.empty()
    session.update_agent(stt_refining_agent)
   
    return f"Skipped question with payload: {payload.payload}"
 
async def re_answer(payload, session):
    logger.info("🔄 Re-answering question...")
    # For re-answer, we just stay on the STT refining agent
    # and let the user provide a new answer
    return "Please provide your answer again"
 
#------------------------------------------------------------------------------