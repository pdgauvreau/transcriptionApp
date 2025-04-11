# HelloI Transcription App

A real-time audio recording and transcription application that can identify different speakers in a conversation. This application uses AssemblyAI's API for accurate speech-to-text transcription with speaker diarization.

## Features

- Real-time audio recording
- High-quality audio capture (44.1kHz, 16-bit, stereo)
- Automatic transcription using AssemblyAI
- Speaker diarization (identification of different speakers)
- Saves both intermediate (20-second) and complete recordings
- Automatic cleanup of temporary audio files

## Requirements

- Python 3.6 or higher
- AssemblyAI API key (sign up at [AssemblyAI](https://www.assemblyai.com/))
- Required Python packages:
  ```
  sounddevice
  numpy
  wave
  assemblyai
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pdgauvreau/HelloI-Transcription-App.git
   cd HelloI-Transcription-App
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python audio_recorder.py
   ```

2. When prompted, enter your AssemblyAI API key.

3. The application will:
   - Start recording when you press Enter
   - Automatically save and transcribe the first 20 seconds
   - Continue recording until you press Enter again
   - Save and transcribe the complete recording
   - Clean up temporary audio files

## How It Works

The application uses the following components:

- `sounddevice`: Captures real-time audio input
- `numpy`: Processes audio data
- `wave`: Saves audio in WAV format
- `assemblyai`: Handles transcription and speaker diarization

The transcription process includes:
1. Audio recording in high quality
2. Automatic file saving
3. Upload to AssemblyAI
4. Transcription with speaker identification
5. Display of results with speaker labels

## Output

The transcription output will show:
- Timestamp of the recording
- Speaker identification (e.g., "Speaker 1:", "Speaker 2:")
- Transcribed text for each speaker

## Notes

- The application is configured for 2 speakers by default
- Temporary audio files are automatically deleted after transcription
- Make sure your microphone is properly configured before starting

## License

[MIT License](LICENSE)

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements. 