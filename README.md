# Interview_Agent
This is a simple Interview_Agent that uses livekit to leverage the realtime expreince
This is the first working prototype of interview

## How to run the app?
To run the app you need to run frontend, backend and livekit agent.
but first we need to install the dependencies in your python enviroment
using below command (make sure you are in Interview_Agent directory):
```
pip install -r requirements.txt
```

### Running the frontend
Go to the frontend folder and run the project.
Here are the commands:
```
cd frontend
npm i
npm run dev
```
### Running the backend
Go to the frontend folder and run the project.
Here are the commands:
```
cd backend
uvicorn server:app --host 0.0.0.0 --port 5001 --reload
```

### Running the livekit Agent
This is need one more step  before we run livekit agent.
In the main.py in livekitAgent folder you need to Add your LLM, TTS and STT provider. In the given code i am using my own customTTS and customSTT for TTS and STT task and for LLM I am using google's gemini 2.0 flash. 
replace the below code with your own in the main.py:
```
session = AgentSession[InterviewData](
        userdata=interview_data,
        stt=CustomSTT("medium"),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=CustomTTS(),
        vad=silero.VAD.load()
    )
```
Still confuse here is an example:
let say I want to use cartesia TTS, groq STT and openai LLM
```
session = AgentSession[InterviewData](
        userdata=interview_data,
        stt=groq.STT(model="whisper-large-v3-turbo",language="en"),
        llm=openai.LLM(model="gpt-4o-mini")
        tts=cartesia.TTS(),
        vad=silero.VAD.load()
    )
```

Now to run the code run following command:
```
cd livekitAgent
python main.py dev
```

Now you can go to http://localhost:5173/ in your browser and use this agent.
