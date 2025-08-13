"""
## Documentation
This script is a refactored version of the Google Gemini LiveAPI Quickstart.
Original: https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.py

It has been modified to act as a controllable "agent" for a larger application,
removing the human-input loop and replacing it with methods that can be called
by an orchestrating script.

## Setup
pip install google-genai opencv-python pyaudio pillow mss python-dotenv exceptiongroup
"""

import os
import asyncio
import base64
import io
import traceback

import cv2
from exceptiongroup import ExceptionGroup
import pyaudio
import PIL.Image
import mss

import argparse

from google import genai
from google.genai import types

# --- Initial Setup and Constants (from original script) ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-1.5-pro-preview-0514"
DEFAULT_MODE = "camera"

# It's recommended to use python-dotenv to load this from a .env file
# Create a .env file with: GEMINI_API_KEY="your_api_key"
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(
    # The original script used a different API version; this is more standard now.
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)


CONFIG = types.LiveConnectConfig(
    response_modalities=[
        "AUDIO",
        "TEXT" # Also get text response for processing
    ],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=25600,
        sliding_window=types.SlidingWindow(target_tokens=12800),
    ),
)

pya = pyaudio.PyAudio()


# --- Main Agent Class ---
class LiveInterviewAgent:
    """
    A controllable agent for conducting a live, multimodal interview.
    """
    def __init__(self, video_mode=DEFAULT_MODE):
        self.video_mode = video_mode
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None

        # NEW: Event to control when the agent is listening for a user response.
        self.is_listening = asyncio.Event()
        # NEW: Buffer to store the complete transcribed text of an answer.
        self.transcribed_response = ""

    # --- Original Helper Functions (Unchanged) ---
    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret: return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None: break
            await asyncio.sleep(1.0)
            await self.out_queue.put(frame)
        cap.release()

    def _get_screen(self):
        sct = mss.mss()
        monitor = sct.monitors[0]
        i = sct.grab(monitor)
        image_bytes = mss.tools.to_png(i.rgb, i.size)
        img = PIL.Image.open(io.BytesIO(image_bytes))
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

    async def get_screen(self):
        while True:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None: break
            await asyncio.sleep(1.0)
            await self.out_queue.put(frame)

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open, format=FORMAT, channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE, output=True)
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    # --- Refactored & New Methods ---

    async def send_realtime(self):
        """Continuously sends audio/video from the out_queue."""
        while True:
            msg = await self.out_queue.get()
            # The session is guaranteed to exist inside the 'run' context
            await self.session.send(input=msg)

    async def listen_audio(self):
        """Records audio from mic, controlled by the is_listening event."""
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open, format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
            input=True, input_device_index=mic_info["index"], frames_per_buffer=CHUNK_SIZE)
        
        kwargs = {"exception_on_overflow": False} if __debug__ else {}

        while True:
            # Block here until listen_for_answer() sets the event
            await self.is_listening.wait()
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_and_process_responses(self):
        """Processes incoming data, populates queues, and manages state."""
        while True:
            turn = await self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                if text := response.text:
                    self.transcribed_response += text
                    print(f"User Said (live): {text.strip()}", end="\r")
            
            # This logic runs after a "turn" is complete (e.g., user stops talking).
            if self.transcribed_response:
                print(f"\nFinal Transcript: {self.transcribed_response.strip()}")
                # Signal that listening is complete.
                self.is_listening.clear()

    # NEW: Orchestrator-callable method to ask a question.
    async def ask_question(self, text: str):
        """Sends a text question to be spoken aloud by the AI."""
        if self.session:
            print(f"\nAI Asks: {text}")
            await self.session.send(input=text, end_of_turn=False)

    # NEW: Orchestrator-callable method to listen for an answer.
    async def listen_for_answer(self) -> str:
        """Listens for and returns the final transcribed text of a user's answer."""
        self.transcribed_response = ""
        self.is_listening.set()  # Start the listen_audio loop

        # Wait here until receive_and_process_responses clears the event
        while self.is_listening.is_set():
            await asyncio.sleep(0.1)
        
        return self.transcribed_response.strip()

    # MODIFIED: Main execution loop, demonstrating programmatic control.
    async def run_interview_session(self):
        """Main loop managed by the orchestrator."""
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=10)

                # Start all the background I/O tasks
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_and_process_responses())
                tg.create_task(self.play_audio())
                if self.video_mode in ["camera", "screen"]:
                    tg.create_task(self.get_frames() if self.video_mode == "camera" else self.get_screen())

                # --- This is where your Orchestrator takes control ---
                print("✅ Interview session started. Waiting for orchestrator...")

                # 1. Ask the first question
                await self.ask_question("Hello, thank you for joining. To start, could you please tell me about yourself?")

                # 2. Listen for the user's answer
                answer1 = await self.listen_for_answer()
                print(f"📋 Orchestrator received answer 1: {answer1}")

                # 3. Your other agents would now process this answer...
                # ...and generate the next question.
                next_question = "That's insightful. Can you describe a challenging project you've worked on and how you handled it?"

                # 4. Ask the next question
                await self.ask_question(next_question)

                # 5. Listen for the next answer
                answer2 = await self.listen_for_answer()
                print(f"📋 Orchestrator received answer 2: {answer2}")
                
                await self.ask_question("Thank you. That concludes our interview.")
                await asyncio.sleep(5) # Give time for the final audio to play

        except asyncio.CancelledError:
            print("Session cancelled by user.")
        except ExceptionGroup as eg:
            print(f"An error occurred: {eg}")
            traceback.print_exception(eg)
        finally:
            if self.audio_stream:
                self.audio_stream.close()
            pya.terminate()
            print("Session closed cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default=DEFAULT_MODE,
        help="Pixels to stream from", choices=["camera", "screen", "none"])
    args = parser.parse_args()
    
    agent = LiveInterviewAgent(video_mode=args.mode)
    try:
        asyncio.run(agent.run_interview_session())
    except KeyboardInterrupt:
        print("\nExiting application.")