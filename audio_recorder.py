import sounddevice as sd
import numpy as np
import wave
import assemblyai as aai
import time
import os
from datetime import datetime

class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.sample_rate = 44100
        self.channels = 2
        self.assembly_client = None
        
    def setup_assemblyai(self, api_key):
        """Initialize AssemblyAI client with API key"""
        aai.settings.api_key = api_key
        self.assembly_client = aai.Client()
        
    def callback(self, indata, outdata, frames, time, status):
        """Callback function for audio recording"""
        if status:
            print(f"Status: {status}")
        if self.recording:
            self.audio_data.append(indata.copy())
            
    def start_recording(self):
        """Start recording audio"""
        self.recording = True
        self.audio_data = []
        print("Recording started...")
        
    def stop_recording(self):
        """Stop recording audio"""
        self.recording = False
        print("Recording stopped.")
        
    def save_audio(self, filename):
        """Save recorded audio to WAV file"""
        if not self.audio_data:
            print("No audio data to save")
            return
            
        audio_data = np.concatenate(self.audio_data, axis=0)
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
            
    def transcribe_audio(self, filename):
        """Transcribe audio using AssemblyAI"""
        if not self.assembly_client:
            print("AssemblyAI client not initialized. Please set up API key first.")
            return
            
        try:
            # Upload the audio file
            audio = self.assembly_client.audio.upload(filename)
            
            # Create a transcription with speaker labels
            transcript = self.assembly_client.transcribe(
                audio,
                speaker_labels=True,
                speaker_count=2  # Adjust based on number of speakers
            )
            
            # Print the transcription with speaker labels
            print("\nTranscription Results:")
            print("-" * 50)
            for utterance in transcript.utterances:
                print(f"Speaker {utterance.speaker}: {utterance.text}")
                
        except Exception as e:
            print(f"Error during transcription: {str(e)}")

def main():
    # Initialize recorder
    recorder = AudioRecorder()
    
    # Get AssemblyAI API key
    api_key = input("Please enter your AssemblyAI API key: ")
    recorder.setup_assemblyai(api_key)
    
    # Start audio stream
    with sd.Stream(callback=recorder.callback,
                  channels=recorder.channels,
                  samplerate=recorder.sample_rate,
                  blocksize=1024):
        
        print("Press Enter to start recording...")
        input()
        
        # Start recording
        recorder.start_recording()
        
        # Record for at least 20 seconds
        time.sleep(20)
        
        # Save the 20-second recording
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_20sec = f"recording_20sec_{timestamp}.wav"
        recorder.save_audio(filename_20sec)
        print(f"Saved 20-second recording to {filename_20sec}")
        
        # Transcribe the 20-second recording
        print("\nTranscribing 20-second recording...")
        recorder.transcribe_audio(filename_20sec)
        
        # Continue recording until user stops
        print("\nRecording continues. Press Enter to stop...")
        input()
        
        # Stop recording
        recorder.stop_recording()
        
        # Save the complete recording
        filename_complete = f"recording_complete_{timestamp}.wav"
        recorder.save_audio(filename_complete)
        print(f"Saved complete recording to {filename_complete}")
        
        # Transcribe the complete recording
        print("\nTranscribing complete recording...")
        recorder.transcribe_audio(filename_complete)
        
        # Clean up files
        os.remove(filename_20sec)
        os.remove(filename_complete)
        print("\nTemporary audio files cleaned up.")

if __name__ == "__main__":
    main() 