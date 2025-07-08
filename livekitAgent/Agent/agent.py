
from livekit.agents.llm import function_tool
from livekit.agents import Agent
from data_class.interview_data import get_next_question

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
