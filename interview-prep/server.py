import asyncio
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Import your LiveInterviewAgent class from the file
from openai_whisper import VADAudio, main as run_whisper       

app = FastAPI()

# Allow your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get():
    return {"status": "Interview bot WebSocket server is running."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for signaling and text exchange between frontend and agent.
    Frontend sends SDP offers / ICE candidates.
    Backend runs the LiveInterviewAgent session and streams responses back.
    """
    await websocket.accept()
    agent = VADAudio()

    try:
        # Kick off the agent session
        asyncio.create_task(agent.main())

        while True:
            # Receive data from the frontend (JSON messages: offer, candidate, etc.)
            data = await websocket.receive_text()
            print(f"Received from frontend: {data}")

            # Here you would parse SDP offers/candidates and forward them to aiortc or your RTC lib
            # For now we’ll just echo it back as a placeholder
            await websocket.send_text(f"Echo: {data}")

            # You can also push live transcriptions back as agent receives them:
            if agent.transcribed_response:
                await websocket.send_text(agent.transcribed_response)

    except WebSocketDisconnect:
        print("Frontend disconnected.")
    except Exception as e:
        traceback.print_exception(e)
        await websocket.close()
