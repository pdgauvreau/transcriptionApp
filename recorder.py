import sounddevice as sd
import numpy as np
import soundfile as sf
import assemblyai as aai
import os
import queue
import threading
from datetime import datetime
from config import ASSEMBLYAI_API_KEY
import platform
import keyboard  # Cross-platform keyboard input
import time

class AudioRecorder:
    def __init__(self, assemblyai_api_key):
        self.assemblyai_api_key = assemblyai_api_key
        self.recording = False
        self.paused = False  # New pause state
        self.audio_data = []
        self.sample_rate = 48000
        self.audio_queue = queue.Queue()
        self.speaker_names = {}
        self.system = platform.system()
        
        # Initialize AssemblyAI
        aai.settings.api_key = self.assemblyai_api_key
        
        try:
            print("\nDetecting audio devices...")
            devices = sd.query_devices()
            
            # Print available devices
            print("\nAvailable audio devices:")
            for i, device in enumerate(devices):
                print(f"{i}: {device['name']} (Input channels: {device.get('max_input_channels', 0)})")
            
            # Find microphone (not Stereo Mix)
            self.mic_id = None
            for i, device in enumerate(devices):
                if device.get('max_input_channels', 0) > 0:
                    name = device['name'].lower()
                    if 'stereo mix' not in name and 'what u hear' not in name:
                        self.mic_id = i
                        print(f"\nFound microphone: {device['name']}")
                        break
            
            if self.mic_id is None:
                raise Exception("No microphone found")
            
            # Find Stereo Mix
            self.system_id = None
            for i, device in enumerate(devices):
                if device.get('max_input_channels', 0) > 0:
                    name = device['name'].lower()
                    if 'stereo mix' in name or 'what u hear' in name:
                        self.system_id = i
                        print(f"Found Stereo Mix: {device['name']}")
                        break
            
            if self.system_id is None:
                print("\nWarning: Stereo Mix not found. Please enable it in Windows sound settings:")
                print("1. Right-click the speaker icon in taskbar")
                print("2. Open Sound settings")
                print("3. Click 'Sound Control Panel'")
                print("4. In Recording tab, right-click and enable 'Show Disabled Devices'")
                print("5. Right-click 'Stereo Mix' and select 'Enable'")
                print("Note: You can still record from your microphone only")
            
            # Get device info for channels
            mic_info = sd.query_devices(self.mic_id)
            self.mic_channels = mic_info['max_input_channels']
            print(f"\nMicrophone channels: {self.mic_channels}")
            
            if self.system_id is not None:
                sys_info = sd.query_devices(self.system_id)
                self.sys_channels = sys_info['max_input_channels']
                print(f"System audio channels: {self.sys_channels}")
            else:
                self.sys_channels = 0
            
            # Test device access
            print("\nTesting device access...")
            with sd.InputStream(device=self.mic_id, channels=1, samplerate=self.sample_rate):
                pass
            if self.system_id is not None:
                with sd.InputStream(device=self.system_id, channels=1, samplerate=self.sample_rate):
                    pass
            print("Device access test successful")
            
        except Exception as e:
            print(f"\nError during audio device initialization: {str(e)}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        self.audio_queue.put(indata.copy())

    def record(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = f"recording_{timestamp}.wav"
        
        try:
            # Get device info to check channels
            mic_info = sd.query_devices(self.mic_id)
            sys_info = sd.query_devices(self.system_id)
            
            # OS-specific handling of device info
            if self.system == 'Windows':
                # Windows typically returns a dictionary
                mic_channels = mic_info.get('max_input_channels', 1)
                sys_channels = sys_info.get('max_input_channels', 1)
            elif self.system == 'Linux':
                # Linux might return a tuple or dictionary depending on the audio backend
                if isinstance(mic_info, dict):
                    mic_channels = mic_info.get('max_input_channels', 1)
                else:
                    mic_channels = 1
                if isinstance(sys_info, dict):
                    sys_channels = sys_info.get('max_input_channels', 1)
                else:
                    sys_channels = 1
            elif self.system == 'Darwin':  # macOS
                # macOS typically returns a dictionary
                mic_channels = mic_info.get('max_input_channels', 1)
                sys_channels = sys_info.get('max_input_channels', 1)
            else:
                # Fallback for unknown OS
                mic_channels = 1
                sys_channels = 1
            
            print(f"Operating System: {self.system}")
            print(f"Microphone channels: {mic_channels}")
            print(f"System audio channels: {sys_channels}")
            
            with sf.SoundFile(self.filepath, mode='x', 
                            samplerate=self.sample_rate,
                            channels=2,
                            subtype='PCM_24') as file:  # Using 24-bit audio instead of 16-bit
                
                def mic_callback(indata, frames, time, status):
                    if status:
                        print(f"Mic status: {status}")
                    data = indata.copy()
                    if data.shape[1] == 1:
                        data = np.repeat(data, 2, axis=1)
                    self.audio_queue.put(('mic', data))
                
                def system_callback(indata, frames, time, status):
                    if status:
                        print(f"System status: {status}")
                    data = indata.copy()
                    if data.shape[1] == 1:
                        data = np.repeat(data, 2, axis=1)
                    self.audio_queue.put(('system', data))
                
                # Create two input streams with optimized settings
                blocksize = 2048
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    device=self.mic_id,
                    channels=mic_channels,
                    callback=mic_callback,
                    blocksize=blocksize,
                    dtype=np.float32  # Use 32-bit float for better quality
                ), sd.InputStream(
                    samplerate=self.sample_rate,
                    device=self.system_id,
                    channels=sys_channels,
                    callback=system_callback,
                    blocksize=blocksize,
                    dtype=np.float32
                ):
                    print("Recording started... Press 'p' to pause, 'r' to resume, or 's' to stop.")
                    print("Recording from both microphone and system audio...")
                    
                    # Set up keyboard hooks
                    keyboard.on_press_key('p', lambda _: self.pause_recording() if not self.paused else None)
                    keyboard.on_press_key('r', lambda _: self.resume_recording() if self.paused else None)
                    keyboard.on_press_key('s', lambda _: setattr(self, 'recording', False))
                    
                    mic_buffer = []
                    system_buffer = []
                    
                    # Variables for silence detection
                    silence_threshold = 0.001  # Adjust this value based on your needs
                    silence_start_time = None
                    silence_duration = 0
                    last_check_time = time.time()
                    
                    # Variables for time-based check
                    recording_start_time = time.time()
                    hour_prompt_shown = False
                    
                    while self.recording:
                        try:
                            # Skip processing if paused
                            if self.paused:
                                time.sleep(0.1)  # Reduce CPU usage while paused
                                continue
                            
                            source, audio_data = self.audio_queue.get(timeout=0.1)
                            
                            if source == 'mic':
                                mic_buffer.append(audio_data)
                            else:
                                system_buffer.append(audio_data)
                                
                            # Process buffers when we have enough data
                            if mic_buffer and system_buffer:
                                # Get the minimum length between the two buffers
                                mic_data = np.concatenate(mic_buffer)
                                sys_data = np.concatenate(system_buffer)
                                min_len = min(len(mic_data), len(sys_data))
                                
                                # Trim both to the same length
                                mic_data = mic_data[:min_len]
                                sys_data = sys_data[:min_len]
                                
                                # Apply gentle noise reduction to mic input
                                mic_data = self.reduce_noise(mic_data)
                                
                                # Mix audio with improved balance
                                mixed_audio = self.mix_audio(mic_data, sys_data)
                                
                                # Calculate and show levels
                                mic_level = np.sqrt(np.mean(mic_data**2))
                                sys_level = np.sqrt(np.mean(sys_data**2))
                                print(f"\rMic level: {mic_level:.6f}, System level: {sys_level:.6f}", end='', flush=True)
                                
                                # Check for silence
                                current_time = time.time()
                                if mic_level < silence_threshold and sys_level < silence_threshold:
                                    if silence_start_time is None:
                                        silence_start_time = current_time
                                    silence_duration = current_time - silence_start_time
                                else:
                                    silence_start_time = None
                                    silence_duration = 0
                                
                                # Check if we should prompt to stop due to silence
                                if silence_duration >= 120:  # 2 minutes of silence
                                    print("\n\nNo sound detected for 2 minutes. Would you like to stop recording? (y/n)")
                                    response = input().lower()
                                    if response == 'y':
                                        self.recording = False
                                        break
                                    else:
                                        silence_start_time = None  # Reset silence timer
                                        silence_duration = 0
                                
                                # Check if we should prompt to stop due to time
                                recording_duration = current_time - recording_start_time
                                if recording_duration >= 3600 and not hour_prompt_shown:  # 1 hour
                                    print("\n\nRecording has been going on for an hour. Would you like to continue? (y/n)")
                                    response = input().lower()
                                    if response == 'n':
                                        self.recording = False
                                        break
                                    else:
                                        hour_prompt_shown = True  # Only show once per hour
                                
                                file.write(mixed_audio)
                                
                                # Clear buffers
                                mic_buffer = []
                                system_buffer = []
                                
                        except queue.Empty:
                            continue
                        except Exception as e:
                            print(f"\nError writing audio data: {e}")
                            continue
                    
                    # Clean up keyboard hooks
                    keyboard.unhook_all()
                            
            print("\nRecording finished.")
            
        except Exception as e:
            print(f"Error during recording: {str(e)}")
            return None
            
        return self.filepath

    def reduce_noise(self, audio_data):
        """Simple noise reduction"""
        # Apply a noise gate
        noise_threshold = 0.005
        audio_data[abs(audio_data) < noise_threshold] = 0
        return audio_data

    def mix_audio(self, mic_data, sys_data):
        """Improved audio mixing with dynamic leveling"""
        # Calculate RMS levels
        mic_rms = np.sqrt(np.mean(mic_data**2))
        sys_rms = np.sqrt(np.mean(sys_data**2))
        
        # Adjust mixing ratio based on levels
        if mic_rms > 0.01:  # If there's significant mic input
            mic_gain = 0.7
            sys_gain = 0.3
        else:  # If mic is quiet, boost system audio
            mic_gain = 0.4
            sys_gain = 0.6
        
        # Mix with soft limiting
        mixed = mic_gain * mic_data + sys_gain * sys_data
        
        # Apply soft limiting to prevent clipping
        threshold = 0.95
        mixed = np.where(
            abs(mixed) > threshold,
            threshold * np.sign(mixed) + (abs(mixed) - threshold) * 0.1,
            mixed
        )
        
        return mixed

    def start_recording(self):
        self.recording = True
        
        # Start recording in a separate thread
        record_thread = threading.Thread(target=self.record)
        record_thread.start()
        
        # Wait for recording to complete
        record_thread.join()
        
        # Generate transcript if we have a valid audio file
        if hasattr(self, 'filepath') and self.filepath:
            print("\nTranscribing audio...")
            transcript = self.transcribe_audio(self.filepath)
            
            if transcript:
                # Save and display the formatted transcript
                self.save_transcript(transcript, self.filepath)
        
        return self.filepath

    def transcribe_audio(self, audio_file):
        if not os.path.exists(audio_file):
            print(f"Audio file {audio_file} not found.")
            return None

        try:
            # Step 1: Create a 2-minute preview clip
            print("\nCreating preview clip...")
            preview_file = audio_file.replace(".wav", "_preview.wav")
            
            # Read the first 2 minutes of the audio file
            with sf.SoundFile(audio_file, 'r') as f:
                preview_data = f.read(int(120 * self.sample_rate))  # 2 minutes = 120 seconds
            
            # Save the preview clip
            with sf.SoundFile(preview_file, 'w', 
                            samplerate=self.sample_rate,
                            channels=2,
                            subtype='PCM_24') as f:
                f.write(preview_data)
            
            # Step 2: Transcribe the preview clip
            print("\nTranscribing preview clip...")
            config = aai.TranscriptionConfig(
                speaker_labels=True,
                language_code="en"
            )
            
            preview_transcript = aai.Transcriber().transcribe(preview_file, config=config)
            
            # Step 3: Get speaker names from preview
            print("\n=== Preview Transcript (First 2 minutes) ===\n")
            
            # Find the longest continuous speech for each speaker
            speaker_segments = {}
            current_speaker = None
            current_start = None
            current_text = []
            
            for utterance in preview_transcript.utterances:
                if current_speaker is None:
                    current_speaker = utterance.speaker
                    current_start = utterance.start
                    current_text = [utterance.text]
                elif utterance.speaker == current_speaker:
                    current_text.append(utterance.text)
                else:
                    # Store the previous segment
                    duration = utterance.start - current_start
                    if current_speaker not in speaker_segments or duration > speaker_segments[current_speaker]['duration']:
                        speaker_segments[current_speaker] = {
                            'start': current_start,
                            'duration': duration,
                            'text': ' '.join(current_text)
                        }
                    
                    # Start new segment
                    current_speaker = utterance.speaker
                    current_start = utterance.start
                    current_text = [utterance.text]
            
            # Don't forget the last segment
            if current_speaker is not None:
                duration = preview_transcript.utterances[-1].end - current_start
                if current_speaker not in speaker_segments or duration > speaker_segments[current_speaker]['duration']:
                    speaker_segments[current_speaker] = {
                        'start': current_start,
                        'duration': duration,
                        'text': ' '.join(current_text)
                    }
            
            # Format and display the longest segments
            def format_time(start_ms):
                seconds = int(start_ms / 1000)
                minutes = seconds // 60
                seconds = seconds % 60
                return f"[{minutes:02d}:{seconds:02d}]"
            
            print("\nLongest continuous speech segments from each speaker:")
            for speaker, segment in speaker_segments.items():
                timestamp = format_time(segment['start'])
                print(f"\n{timestamp} {speaker}:")
                print(f"    {segment['text']}\n")
            
            # Get names for each speaker
            print("\nBased on the preview above, please provide names for each speaker:")
            self.speaker_names = {}
            
            for speaker in sorted(speaker_segments.keys()):
                while True:
                    name = input(f"Enter name for {speaker}: ").strip()
                    if name:
                        self.speaker_names[speaker] = name
                        break
                    print("Please enter a valid name.")
            
            # Show the mapping
            print("\nSpeaker mapping:")
            for speaker, name in self.speaker_names.items():
                print(f"{speaker} → {name}")
            
            print("\nThese names will be used for the full transcription.")
            
            # Step 4: Transcribe the full audio with the same speaker mapping
            print("\nTranscribing full audio...")
            full_transcript = aai.Transcriber().transcribe(audio_file, config=config)
            
            # Step 5: Format the full transcript with the names from preview
            formatted_transcript = self.format_transcript(full_transcript)
            
            # Clean up the preview file
            os.remove(preview_file)
            
            return formatted_transcript
            
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            return None

    def format_transcript(self, transcript):
        """Format the transcript like a script with real names and timestamps"""
        formatted_lines = []
        current_speaker = None
        current_text = []
        
        def format_time(start_ms):
            seconds = int(start_ms / 1000)
            minutes = seconds // 60
            seconds = seconds % 60
            return f"[{minutes:02d}:{seconds:02d}]"
        
        # Process each utterance with real names
        for utterance in transcript.utterances:
            # Use provided name if available, otherwise use original speaker label
            speaker = self.speaker_names.get(utterance.speaker, utterance.speaker)
            timestamp = format_time(utterance.start)
            
            # If speaker changes, print the accumulated text
            if current_speaker and speaker != current_speaker:
                time_marker = format_time(transcript.utterances[0].start)
                formatted_lines.append(f"\n{time_marker} {current_speaker}:")
                formatted_lines.append("    " + " ".join(current_text))
                current_text = []
            
            # Add current text to buffer
            current_text.append(utterance.text)
            current_speaker = speaker
        
        # Don't forget to print the last speaker's text
        if current_text:
            time_marker = format_time(transcript.utterances[-1].start)
            formatted_lines.append(f"\n{time_marker} {current_speaker}:")
            formatted_lines.append("    " + " ".join(current_text))
        
        # Join all lines and add header
        final_transcript = "=== Complete Transcript with Speaker Identification ===\n"
        final_transcript += "\nSpeaker mapping:"
        for speaker, name in self.speaker_names.items():
            final_transcript += f"\n{speaker} → {name}"
        final_transcript += "\n\n" + "="*50 + "\n"
        final_transcript += "\n".join(formatted_lines)
        
        return final_transcript

    def save_transcript(self, transcript, filepath):
        """Save the transcript to a file with proper formatting"""
        transcript_file = filepath.replace(".wav", "_transcript.txt")
        
        try:
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript)
            
            print(f"\nTranscript saved to {transcript_file}")
            
            # Only show the full transcript, not the preview
            print("\n" + "="*50)
            print("FULL TRANSCRIPT:")
            print("="*50)
            print(transcript)
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"Error saving transcript: {str(e)}")

    def pause_recording(self):
        """Pause the current recording"""
        if self.recording and not self.paused:
            self.paused = True
            print("\nRecording paused. Press 'r' to resume or 's' to stop.")
            return True
        return False

    def resume_recording(self):
        """Resume a paused recording"""
        if self.recording and self.paused:
            self.paused = False
            print("\nRecording resumed.")
            return True
        return False

def main():
    print("\nStarting program...")
    
    # Get AssemblyAI API key from config file
    if not ASSEMBLYAI_API_KEY or ASSEMBLYAI_API_KEY == "your-api-key-here":
        print("Please set your AssemblyAI API key in config.py")
        return

    try:
        print("About to initialize AudioRecorder...")
        # Test device listing before creating AudioRecorder
        print("\nTesting audio device listing:")
        devices = sd.query_devices()
        print(f"Found {len(devices)} audio devices")
        
        # Now create the recorder
        recorder = AudioRecorder(ASSEMBLYAI_API_KEY)
        print("AudioRecorder initialized successfully")
        
        while True:
            print("\n=== Audio Recorder Menu ===")
            print("1. Start New Recording")
            print("2. Exit")
            
            choice = input("Enter your choice (1-2): ")
            
            if choice == "1":
                try:
                    print("\nPress Enter to start recording...")
                    input()
                    
                    audio_file = recorder.start_recording()
                    
                    if audio_file:
                        print("\nTranscribing audio...")
                        transcript = recorder.transcribe_audio(audio_file)
                        
                        if transcript:
                            # Save and display the formatted transcript
                            recorder.save_transcript(transcript, audio_file)
                            
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