# audio_processor.py

import asyncio
import collections
import numpy as np
import torch
import webrtcvad
import subprocess
from whisper import load_model, transcribe

# --- Configuration ---
MODEL_SIZE = "small.en"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
RATE = 16000
FRAME_DURATION_MS = 30
BYTES_PER_FRAME = int(RATE * (FRAME_DURATION_MS / 1000) * 2)
VAD_AGGRESSIVENESS = 3
SILENCE_THRESHOLD_MS = 1000
SPEECH_PAD_MS = 200
MAX_SPEECH_SECONDS = 60
MAX_SPEECH_FRAMES = int(MAX_SPEECH_SECONDS * 1000 / FRAME_DURATION_MS)

class AudioProcessor:
    def __init__(self, on_transcription_complete):
        self.on_transcription_complete = on_transcription_complete
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        
        print("Loading Whisper model...")
        self.model = load_model(MODEL_SIZE, device=DEVICE)
        print("Model loaded.")

        self.ring_buffer = collections.deque(maxlen=SILENCE_THRESHOLD_MS // FRAME_DURATION_MS)
        self.triggered = False
        self.speech_buffer = bytearray()
        self.ffmpeg_process = None
        
        # NEW: An asyncio.Queue to communicate between the reader task and the processor
        self.decoded_queue = asyncio.Queue()
        
        # Start the FFmpeg process and the reader task immediately
        self._start_ffmpeg_and_reader()

    def _start_ffmpeg_and_reader(self):
        command = [
            "ffmpeg", "-i", "pipe:0", "-f", "s16le",
            "-ar", str(RATE), "-ac", "1", "pipe:1"
        ]
        self.ffmpeg_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("FFmpeg process started.")
        # NEW: Start the background task that reads from FFmpeg's output
        asyncio.create_task(self._read_ffmpeg_output())

    async def _read_ffmpeg_output(self):
        """A background task that continuously reads decoded PCM data from FFmpeg."""
        while True:
            try:
                # Run the blocking read in a thread to not block the event loop
                decoded_chunk = await asyncio.to_thread(self.ffmpeg_process.stdout.read, BYTES_PER_FRAME)
                if not decoded_chunk:
                    print("FFmpeg stdout closed.")
                    break
                await self.decoded_queue.put(decoded_chunk)
            except Exception as e:
                print(f"Error reading from FFmpeg: {e}")
                break

    async def process_audio_chunk(self, audio_chunk: bytes):
        """This function now only WRITES to FFmpeg and processes data from the queue."""
        if self.ffmpeg_process.stdin.closed:
            return
        
        # Write the incoming compressed audio to FFmpeg's stdin
        await asyncio.to_thread(self.ffmpeg_process.stdin.write, audio_chunk)
        
        # Process all frames currently in the queue from the reader task
        while not self.decoded_queue.empty():
            frame = await self.decoded_queue.get()
            
            is_speech = self.vad.is_speech(frame, RATE)
            print('S' if is_speech else '_', end='', flush=True)

            if not self.triggered:
                self.ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in self.ring_buffer if speech])
                if num_voiced > 0.9 * self.ring_buffer.maxlen:
                    print("\nSpeech detected...")
                    self.triggered = True
                    padding_ms = SPEECH_PAD_MS // FRAME_DURATION_MS
                    for f, s in list(self.ring_buffer)[-padding_ms:]:
                        self.speech_buffer.extend(f)
                    self.ring_buffer.clear()
            else:
                self.speech_buffer.extend(frame)
                self.ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in self.ring_buffer if not speech])
                if num_unvoiced > 0.8 * self.ring_buffer.maxlen:
                    print("\nSilence detected, transcribing...")
                    await self._transcribe_and_reset()
                elif len(self.speech_buffer) / BYTES_PER_FRAME > MAX_SPEECH_FRAMES:
                    print("\nMax speech length reached, transcribing...")
                    await self._transcribe_and_reset()

    async def _transcribe_and_reset(self):
        # This function remains the same
        if not self.speech_buffer: return
        padding_frames = SPEECH_PAD_MS // FRAME_DURATION_MS
        end_silence_frames = len(self.ring_buffer) - padding_frames
        if end_silence_frames > 0:
            bytes_to_trim = end_silence_frames * BYTES_PER_FRAME
            self.speech_buffer = self.speech_buffer[:-bytes_to_trim]
        if not self.speech_buffer:
            self.triggered = False; self.ring_buffer.clear(); return
        audio_data_np = np.frombuffer(self.speech_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        result = transcribe(self.model, audio_data_np, language="en", fp16=torch.cuda.is_available())
        text = result['text'].strip()
        if text:
            print("Transcription , about to be sent to frontend:", text)
            await self.on_transcription_complete(text)
        self.triggered = False; self.speech_buffer.clear(); self.ring_buffer.clear()
        print("\nListening...")

    async def cleanup(self):
        print("Processor cleaning up.")
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            await asyncio.to_thread(self.ffmpeg_process.terminate)
            print("FFmpeg process terminated.")