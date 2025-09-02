// src/components/AudioStreamer.tsx
import './audiostreamer.css';
import React, { useState, useRef, useEffect } from 'react';

const AudioStreamer: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState('');
  
  // Use useRef for objects that should persist across renders without causing re-renders
  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // Use useEffect to manage the WebSocket connection lifecycle
  useEffect(() => {
    // This function will be called when the component is unmounted
    return () => {
      console.log("Cleaning up WebSocket and MediaRecorder.");
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []); // The empty dependency array [] means this effect runs only once on mount

  const handleToggleRecording = async () => {
    if (isRecording) {
      // --- STOP RECORDING ---
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
      setIsRecording(false);
    } else {
      // --- START RECORDING ---
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        socketRef.current = new WebSocket('ws://localhost:8000/ws');

        socketRef.current.onopen = () => {
          console.log("WebSocket connection established.");
          setIsRecording(true);
          
          mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm; codecs=opus' });
          
          mediaRecorderRef.current.addEventListener('dataavailable', (event) => {
            if (event.data.size > 0 && socketRef.current?.readyState === WebSocket.OPEN) {
              socketRef.current.send(event.data);
            }
          });

          mediaRecorderRef.current.onstop = () => {
            console.log("MediaRecorder closed.");
          };

          socketRef.current!.onmessage = (event) => {
            console.log('Received transcription:', event.data);
            setTranscription((prev) => prev + event.data + ' ');
          };
          
          mediaRecorderRef.current.start(200); // Send data chunks every 250ms
        };

        socketRef.current.onerror = (error) => {
          console.error('WebSocket Error:', error);
          setIsRecording(false); // Stop on error
        };

        socketRef.current.onclose = (event) => {
          console.log('WebSocket Connection Closed:', event.reason);
          setIsRecording(false); // Ensure state is updated
        };

      } catch (error) {
        console.error("Failed to start recording:", error);
      }
    }
  };

  return (
    <div className="audio-streamer">
  <h2>Real-Time Transcription</h2>

  <button
    onClick={handleToggleRecording}
    className={isRecording ? "recording" : ""}
  >
    {isRecording ? "Stop Recording" : "Start Recording"}
  </button>

  <div className="transcription">
    <h3>Transcription:</h3>
    <p>{transcription || "..."}</p>
  </div>
</div>
  );
};

export default AudioStreamer;