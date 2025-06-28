# import os
# from livekit import api
# from flask import Flask, request
# from dotenv import load_dotenv
# from flask_cors import CORS
# from livekit.api import LiveKitAPI, ListRoomsRequest
# import uuid

# load_dotenv()

# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}})

# async def generate_room_name():
#     name = "room-" + str(uuid.uuid4())[:8]
#     rooms = await get_rooms()
#     while name in rooms:
#         name = "room-" + str(uuid.uuid4())[:8]
#     return name

# async def get_rooms():
#     api = LiveKitAPI()
#     rooms = await api.room.list_rooms(ListRoomsRequest())
#     await api.aclose()
#     return [room.name for room in rooms.rooms]

# @app.route("/getToken")
# async def get_token():
#     name = request.args.get("name", "my name")
#     room = request.args.get("room", None)
    
#     if not room:
#         room = await generate_room_name()
        
#     token = api.AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET")) \
#         .with_identity(name)\
#         .with_name(name)\
#         .with_grants(api.VideoGrants(
#             room_join=True,
#             room=room
#         ))
    
#     return token.to_jwt()

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5001, debug=True)


# main.py
import os
import uuid
from dotenv import load_dotenv

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from livekit.api import LiveKitAPI, ListRoomsRequest, AccessToken, VideoGrants

load_dotenv()

app = FastAPI()

# Allow any origin (you can scope this down in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

async def get_rooms() -> list[str]:
    """
    Fetch the list of existing room names from LiveKit.
    """
    api = LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    resp = await api.room.list_rooms(ListRoomsRequest())
    await api.aclose()
    return [room.name for room in resp.rooms]

async def generate_room_name() -> str:
    """
    Generate a unique room name not already in use.
    """
    existing = set(await get_rooms())
    while True:
        candidate = f"room-{uuid.uuid4().hex[:8]}"
        if candidate not in existing:
            return candidate

@app.get("/getToken", response_class=PlainTextResponse)
async def get_token(
    name: str = Query("my name", description="User identity"),
    room: str | None = Query(None, description="Room name to join"),
):
    """
    Returns a JWT access token for the given user and room.
    If no room is provided, allocates a new unique room name.
    """
    # 1) Pick or create the room
    if not room:
        try:
            room = await generate_room_name()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Room lookup failed: {e}")

    # 2) Build the token grants
    try:
        token = (
            AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET"))
            .with_identity(name)
            .with_name(name)
            .with_grants(
                VideoGrants(room_join=True, room=room)
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {e}")

    # 3) Return the raw JWT
    return token.to_jwt()

