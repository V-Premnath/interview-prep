# main_whisper.py

import collections
import numpy as np
import pyaudio
import torch
import webrtcvad
from whisper import load_model, transcribe

# --- Configuration ---
MODEL_SIZE = "small.en"  # "base.en" for English-only, "base" for multilingual.
# Other sizes: "tiny.en", "small.en", "medium.en"
# GPU is highly recommended.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Audio parameters  
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper works best with 16kHz audio
FRAME_DURATION_MS = 30  # VAD supports 10, 20, or 30 ms frames
CHUNK_SIZE = int(RATE * FRAME_DURATION_MS / 1000)  # Chunks for VAD

# VAD and Transcription Logic
VAD_AGGRESSIVENESS = 0  # 0 (least aggressive) to 3 (most aggressive)
SILENCE_THRESHOLD_MS = 700  # How long a pause triggers transcription
SPEECH_PAD_MS = 200 # Add padding before/after speech to avoid cutting words off

class VADAudio:
    """A class to handle audio recording and Voice Activity Detection."""

    def __init__(self, aggressiveness=VAD_AGGRESSIVENESS, device=None):
        self.vad = webrtcvad.Vad(aggressiveness)
        self._p = pyaudio.PyAudio()
        self.stream = self._p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )

    def __iter__(self):
        return self

    def __next__(self):
        frame = self.stream.read(CHUNK_SIZE)
        is_speech = self.vad.is_speech(frame, RATE)
        return frame, is_speech

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self._p.terminate()

def main():
    """Continuously listens, detects speech, and transcribes it using Whisper."""
    print(f"Loading Whisper model '{MODEL_SIZE}' on device '{DEVICE}'...")
    model = load_model(MODEL_SIZE, device=DEVICE)
    print("Model loaded. Ready to listen.")

    vad_audio = VADAudio()
    
    # Ring buffer to hold a bit of audio before speech is detected
    padding_frames_count = SILENCE_THRESHOLD_MS // FRAME_DURATION_MS
    speech_frames_count = SPEECH_PAD_MS // FRAME_DURATION_MS

    ring_buffer = collections.deque(maxlen=padding_frames_count)
    triggered = False
    speech_buffer = []

    print("\nListening... (press Ctrl+C to exit)")
    try:
        for frame, is_speech in vad_audio:
            if not triggered:
                ring_buffer.append((frame, is_speech))
                # Check if enough consecutive frames are speech to trigger
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > 0.8 * ring_buffer.maxlen:
                    print("Speech detected...")
                    triggered = True
                    # Add preceding audio frames from buffer to catch start of utterance
                    speech_buffer.extend([f for f, _ in ring_buffer])
                    ring_buffer.clear()
            else:
                speech_buffer.append(frame)
                ring_buffer.append((frame, is_speech))
                # Check if there's enough silence to consider the utterance ended
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    print("Silence detected, transcribing...")
                    
                    # 1. Prepare audio data
                    audio_data_bytes = b"".join(speech_buffer)
                    audio_data_np = np.frombuffer(audio_data_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                    # 2. Transcribe
                    result = transcribe(model, audio_data_np, language="en", fp16=torch.cuda.is_available())
                    text = result['text'].strip()

                    print("Transcription:", text)
                    print("\nListening...")

                    # Reset for next utterance
                    triggered = False
                    speech_buffer.clear()
                    ring_buffer.clear()

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        vad_audio.close()


if __name__ == "__main__":
    main()