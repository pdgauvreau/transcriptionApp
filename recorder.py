import sounddevice as sd
import soundcard as sc
import numpy as np
import soundfile as sf
import assemblyai as aai
import os
import time
from datetime import datetime
from config import ASSEMBLYAI_API_KEY
import warnings
import threading
import queue

# Suppress the data discontinuity warnings
warnings.filterwarnings("ignore", category=UserWarning)

class AudioRecorder:
    def __init__(self, assemblyai_api_key):
        self.assemblyai_api_key = assemblyai_api_key
        self.recording = False
        self.audio_data = []
        self.sample_rate = 44100
        self.audio_queue = queue.Queue()
        
        # Initialize AssemblyAI
        aai.settings.api_key = self.assemblyai_api_key
        
        # Get device information
        try:
            # Get the default input device info
            input_info = sd.query_devices(kind='input')
            self.input_device_index = input_info['index']
            self.input_channels = input_info['max_input_channels']
            
            print(f"Using input device: {input_info['name']} ({self.input_channels} channels)")
            
        except Exception as e:
            print(f"Error getting device information: {str(e)}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        if self.recording:
            self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        self.audio_data = []
        print("Recording started... Press Enter to stop.")
        
        try:
            # Start the audio recording stream
            stream = sd.InputStream(
                callback=self.audio_callback,
                channels=self.input_channels,
                samplerate=self.sample_rate,
                device=self.input_device_index
            )
            
            # Start recording
            stream.start()
            
            # Wait for Enter key in a separate thread
            def wait_for_enter():
                input()
                self.recording = False
            
            # Start the Enter key listener thread
            enter_thread = threading.Thread(target=wait_for_enter)
            enter_thread.daemon = True
            enter_thread.start()
            
            # Collect audio data until recording is stopped
            while self.recording:
                try:
                    # Get audio data from queue with timeout
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    self.audio_data.append(audio_chunk)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Warning during audio recording: {str(e)}")
                    continue
            
            # Stop recording
            stream.stop()
            stream.close()
            print("Recording stopped.")
            
        except Exception as e:
            print(f"Error during recording: {str(e)}")
            self.recording = False
            raise

    def save_recording(self):
        if not self.audio_data:
            print("No recording data available.")
            return None

        try:
            # Concatenate all recorded data
            audio_data = np.concatenate(self.audio_data, axis=0)
            
            # Convert to stereo if needed
            if audio_data.shape[1] == 1:
                audio_data = np.repeat(audio_data, 2, axis=1)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
            
            # Save the recording
            sf.write(filename, audio_data, self.sample_rate)
            print(f"Recording saved as {filename}")
            return filename
            
        except Exception as e:
            print(f"Error saving recording: {str(e)}")
            return None

    def transcribe_audio(self, audio_file):
        if not os.path.exists(audio_file):
            print(f"Audio file {audio_file} not found.")
            return None

        try:
            # Create a transcript from the audio file
            transcript = aai.Transcriber().transcribe(audio_file)
            return transcript.text
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            return None

def main():
    # Get AssemblyAI API key from config file
    if not ASSEMBLYAI_API_KEY or ASSEMBLYAI_API_KEY == "your-api-key-here":
        print("Please set your AssemblyAI API key in config.py")
        return

    try:
        recorder = AudioRecorder(ASSEMBLYAI_API_KEY)
        
        while True:
            print("\n=== Audio Recorder Menu ===")
            print("1. Start Recording")
            print("2. Exit")
            
            choice = input("Enter your choice (1-2): ")
            
            if choice == "1":
                try:
                    recorder.start_recording()
                    audio_file = recorder.save_recording()
                    
                    if audio_file:
                        print("\nTranscribing audio...")
                        transcript = recorder.transcribe_audio(audio_file)
                        
                        if transcript:
                            print("\nTranscription:")
                            print(transcript)
                            
                            # Save transcript to file
                            transcript_file = audio_file.replace(".wav", "_transcript.txt")
                            with open(transcript_file, "w", encoding="utf-8") as f:
                                f.write(transcript)
                            print(f"\nTranscript saved to {transcript_file}")
                except Exception as e:
                    print(f"Error during recording session: {str(e)}")
            
            elif choice == "2":
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")
                
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        return

if __name__ == "__main__":
    main() 