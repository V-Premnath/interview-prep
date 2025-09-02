# server2.py

import asyncio
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from audio_processor import AudioProcessor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get():
    return {"status": "WebSocket server is running."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("INFO:     Connection accepted.")

    processor = None  # Initialize processor to None

    try:
        # Define the callback function first
        async def on_transcription(text: str):
            print("websocket state:",websocket.client_state.value)
            if websocket.client_state.value == 1:
                print(f"Sending Transcription: {text}")
                await websocket.send_text(text)

        # NOW, create the single processor instance for this connection
        processor = AudioProcessor(on_transcription_complete=on_transcription)
        
        while True:
            audio_chunk = await websocket.receive_bytes()
            await processor.process_audio_chunk(audio_chunk)

    except WebSocketDisconnect:
        print(f"Client disconnected: {websocket.client}")
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        # Cleanup processor if it was created
        if processor:
            await processor.cleanup()