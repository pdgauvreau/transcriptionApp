# Audio Recorder with AssemblyAI Transcription

This Python program allows you to record audio from your microphone and system output, then transcribe it using AssemblyAI's speech-to-text API.

## Prerequisites

- Python 3.7 or higher
- AssemblyAI API key (get one at https://www.assemblyai.com/)
- Working microphone and speakers

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Setup

1. Sign up for an AssemblyAI account at https://www.assemblyai.com/
2. Get your API key from the AssemblyAI dashboard
3. Set your API key as an environment variable:
   - Windows (PowerShell):
     ```powershell
     $env:ASSEMBLYAI_API_KEY="your-api-key-here"
     ```
   - Windows (Command Prompt):
     ```cmd
     set ASSEMBLYAI_API_KEY=your-api-key-here
     ```
   - Linux/Mac:
     ```bash
     export ASSEMBLYAI_API_KEY=your-api-key-here
     ```

## Usage

1. Run the program:
```bash
python recorder.py
```

2. Use the menu to:
   - Start recording (press Enter to stop)
   - Exit the program

3. The program will:
   - Record your audio
   - Save it as a WAV file
   - Send it to AssemblyAI for transcription
   - Display the transcription
   - Save the transcription to a text file

## Output Files

- Audio recordings are saved as WAV files with timestamps (e.g., `recording_20240315_143022.wav`)
- Transcriptions are saved as text files with the same timestamp (e.g., `recording_20240315_143022_transcript.txt`)

## Notes

- Make sure your microphone is properly connected and selected as the default input device
- The recording quality depends on your microphone and system settings
- AssemblyAI transcription may take a few moments depending on the length of your recording 