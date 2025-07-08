
from dataclasses import dataclass, field
from typing import Optional
from livekit.agents import Agent, ChatContext
from config.config import INTERVIEW_INSTRUCTIONS
import random
import json
import logging
from enum import Enum
from redisLogic.redis_client import getCandidateData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Interview_data.py")
#----------------------------Helper methods--------------------------------
def get_latest_resume():
    try:
        logger.info("Attempting to retrieve resume")
        logger.info(f"resume : {getCandidateData('686b60d2a6601148142a968b')}")
        return getCandidateData("686b60d2a6601148142a968b")
        
    except Exception as e:
        logger.error(f"Error fetching resume: {e}")
        return ''

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
    
    if interview_data.current_question == len(interview_data.pre_define_questions) * 2:
        return InterviewPrompt.INTERVIEW_END
    
    if interview_data.number_of_follow_ups < 1:
        interview_data.number_of_follow_ups += 1
        return InterviewPrompt.ASK_FOLLOW_UP
    
    if interview_data.current_question % 2 == 1:
        interview_data.current_question += 1
        interview_data.number_of_follow_ups = 0
        return InterviewPrompt.ASK_RESUME_QUESTION

    interview_data.current_question += 1
    interview_data.number_of_follow_ups = 0        
    return interview_data.pre_define_questions[interview_data.current_question // 2]

class InterviewPrompt(Enum):
    ASK_RESUME_QUESTION = "Ask Resume Based Question"
    ASK_FOLLOW_UP = "Ask a Follow Up"
    INTERVIEW_END = "Interview End"

@dataclass
class InterviewData:
    current_question: int = 0
    number_of_follow_ups: int = 99 # setting this a high value as we need to ask predefine question first. refer: get_next_question
    pre_define_questions: list[dict[str, str]] = field(default_factory=lambda: select_questions(question_bank_loader()))
    refining_agent: Optional[Agent] = None
    qna_history: list[dict[str, str]] = field(default_factory=list)
    interview_history: ChatContext = field(default_factory=lambda: ChatContext.from_dict({"items":[{"type":"message","role":"system", "content":[INTERVIEW_INSTRUCTIONS]}]}))
    resume_data: str = field(default_factory=get_latest_resume)

