# DeChord - Real-Time Music Key and Chord Recognition Tool

Welcome to DeChord! This application is designed for musicians, music enthusiasts, and anyone interested in analyzing the harmonic content of audio files. DeChord uses advanced music analysis algorithms to recognize the musical key and chords in an audio file and displays this information in real-time through an intuitive graphical user interface.

## Images

![Screenshot (10)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/f2a399a5-7ba3-430a-bf9a-795f2abc88a8)
![Screenshot (9)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/fc6256c8-bf94-4542-b985-2dafbf2d3990)
![Screenshot (14)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/f1cd092b-f5c5-4f02-8a0a-077fc399564e)

## Features

### Key and Chord Recognition

- **Key Recognition:** Detects the musical key of an audio file using the `madmom` library.
- **Chord Recognition:** Identifies chords in the audio file with start and end times, also using the `madmom` library.
- **Real-Time Display:** Shows the current, previous, and next chords in real-time as the audio plays.

### Audio Playback

- **Play/Pause:** Controls to play and pause the audio.
- **Seek:** Allows seeking forward and backward in the audio track.
- **Volume Control:** Adjustable volume control through a slider.
- **Mute:** Mute and unmute the audio.

### User Interface

- **Drag and Drop:** Supports dragging and dropping audio files into the application window.
- **Theme Toggle:** Switch between dark and light themes.
- **Progress Slider:** Displays and controls the current position within the audio file.
- **Key Display:** Shows the detected musical key.
- **Export Chords:** Export recognized chords to a text file.
- **Keyboard Shortcuts:** Various keyboard shortcuts for quick access to functions.

### Additional Features

- **GitHub Redirect:** Opens the GitHub repository in a web browser.
- **Exception Handling:** Custom exception handler to manage and print exceptions.

## Technology Stack

### Libraries and Frameworks

- **Python:** The primary programming language used for development.
- **PyQt5:** For building the graphical user interface.
- **madmom:** A library for music signal processing, used for key and chord recognition.

## Windows Installation 

### Prerequisites

- Python 3.7 or higher
- Pip (Python package installer)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/chinmaykrishnroy/DeChord.git
   cd DeChord

2. Run the run.bat script for the first time:

   ```bash
   run.bat

3. Run the createWindowsShortcut.bat to generate a shortcut for the application:

   ```bash
   createWindowsShortcut.bat

4. <b> Use the shortcut file 'DeChord' to open the application from next time. </b>

## Linux/MacOS Installation 

### Prerequisites

- Python 3.7 or higher
- Pip (Python package installer)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/chinmaykrishnroy/DeChord.git
   cd DeChord

2. Build and run the run.sh script for the first time:

   ```bash
   chmod +x run.sh && ./run.sh

3. Run the createLinuxShortcut.sh to generate Desktop shortcut for the application:

   ```bash
   chmod +x createLinuxShortcut.sh && ./createLinuxShortcut.sh

4. <b> Use the Desktop Shortcut file 'DeChord' to open the application from the next time. </b>

## How to Use

### Loading an Audio File

- Click the **Open** button or use the **drag and drop** feature to load an audio file.
- Supported formats: `.wav`, `.mp3`, `.m4a`, `.aac`.

### Playback Controls

- **Play/Pause:** Use the play/pause button to start or pause the audio.
- **Seek:** Use the forward and backward buttons to seek 10 seconds ahead or back.
- **Mute:** Click the mute button to mute or unmute the audio.
- **Volume Control:** Adjust the volume using the slider.
- **Progress Slider:** Drag the slider to move to a different part of the audio file.

### Chord and Key Recognition

- The application will automatically start recognizing chords and the key when an audio file is loaded.
- The recognized chords will be displayed in real-time as the audio plays.
- The detected key will be displayed above the playback controls.

### Exporting Chords

- Click the **Save Chords** button to export the recognized chords to a text file.

### Toggling Theme

- Click the **Theme** button to switch between dark and light themes.

### Redirect to GitHub

- Click the **GitHub** button to open the project's GitHub repository in your web browser.

### Keyboard Shortcuts

- **Esc:** Close the application
- **-:** Minimize the application
- **T:** Toggle theme
- **P:** Play/Pause
- **Left Arrow:** Seek backward
- **Right Arrow:** Seek forward
- **M:** Mute/Unmute
- **O:** Open audio file
- **E:** Export chords
- **R:** Redirect to GitHub

## Code Structure

### Main Files and Directories

- **main.py:** The entry point of the application.
- **interface.py:** Contains the GUI layout and setup.
- **chords.py:** Functions and classes related to chord recognition.
- **key.py:** Functions and classes related to key recognition.
- **icons/:** Directory containing icon files.
- **export/:** Directory where exported chord files are saved.

### Key Classes

- **KeyRecognitionThread:** A thread for performing key recognition.
- **ChordRecognitionThread:** A thread for performing chord recognition.
- **Ui_MainWindow:** The class is for the application's user interface.
- **MainWindow:** The main window class for every other class's integration and features.

### Exception Handling

- A custom exception handler is set up to handle and print exceptions, making debugging easier.

## Customizing the Application

### Adding New Features

To add new features, you can extend the existing classes or add new ones. Ensure to update the GUI (`interface.py`) and connect the new functionalities appropriately.

### Modifying the Theme

To modify the themes, you can update the `dark_theme` and `light_theme` stylesheets in the `theme.py` file.

## Contributing

### Reporting Issues

If you find any bugs or issues, please report them in the [Issues](https://github.com/chinmaykrishnroy/dechord/issues) section of the GitHub repository.

### Pull Requests

I welcome contributions! Please fork the repository and create a pull request with your changes. Ensure your code follows the existing coding style and includes appropriate documentation and tests.

### Coding Standards

- Follow PEP 8 guidelines for Python code.
- Document your code using docstrings.
- Write meaningful commit messages.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

### Libraries and Tools

- **madmom:** For music signal processing algorithms.
- **PyQt5:** For the GUI framework.
- **Python:** The programming language used.

### Inspiration

This project is inspired by the need for a user-friendly tool for musicians to analyze and learn music through real-time key and chord recognition.

## Contact

For any questions or suggestions, feel free to open an issue on the GitHub repository or contact the maintainer directly.

---

Thank you for using DeChord! I hope it helps you in your musical journey.

## More Images

![Screenshot (14)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/92275a84-39f8-4926-9073-7db6b6a7de64)
![Screenshot (13)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/e70cf1ca-ff69-4c2d-8637-0caecbdeb4d5)
![Screenshot (11)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/50380852-ba6c-4ca6-a49c-4970c0cb37f2)
![Screenshot (10)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/a5174ab7-70ab-4821-84a8-868b89591d7c)
![Screenshot (9)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/3e167d19-e7a2-4e90-a519-bf59db37ce41)
![Screenshot (7)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/cba3a277-589c-4499-9c5f-31e7d722b0a0)
![Screenshot (6)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/318b373d-1896-4549-9d0a-7b9a290b9744)
![Screenshot (5)](https://github.com/chinmaykrishnroy/DeChord/assets/65699140/09d12110-2b0c-4de9-bf04-4eedbca234f5)
![image](https://github.com/user-attachments/assets/8c1966eb-27f2-4a5f-9cc4-b1ea8785847b)

## Web App (2026 Redesign)

The repository now includes a browser-based DeChord practice app (FastAPI backend + React frontend) with persistent local storage.

### Highlights

- Persistent song library (single-user localhost mode)
- Audio files stored as BLOB in local LibSQL database
- Saved analysis (key/tempo/chords) per song
- Upload modes:
  - `Analyze chords only`
  - `Analyze + split stems`
- Stage-based upload processing status with real progress values:
  - overall progress (`progress_pct`)
  - current stage progress (`stage_progress_pct`)
  - stage label/message (`queued`, `analyzing_chords`, `splitting_stems`, `persisting`)
- Playback speed control from `40%` to `200%`
- Timeline looping and chord sync
- Fretboard current + next chord highlighting
- Timestamp notes and chord notes with playback toasts
- Note markers on playback progress and chord timeline
- Stem-aware playback:
  - automatic fallback to single mixed track when no stems are available
  - stem mixer checkboxes (all stems enabled by default)
  - per-stem stream endpoints (`/api/songs/{song_id}/stems`, `/api/audio/{song_id}/stems/{stem_key}`)
- Bass artifact pipeline (EADG 4-string v2):
  - drums stem -> beat/downbeat bar grid
  - bass stem -> MIDI artifact generation
  - cleaned + quantized notes -> AlphaTex (`.alphatex`) tab generation with `\sync` points
  - status stages: `transcribing_bass_midi`, `generating_tabs`
  - artifact file endpoints:
    - `/api/songs/{song_id}/midi/file`
    - `/api/songs/{song_id}/tabs/file`
  - dedicated stems-to-tab endpoint:
    - `POST /api/tab/from-demucs-stems`

### Start Locally

Use tmux-managed targets from the root `Makefile`:

```bash
npm install -g portless
make install
make up
make status
```

Open:

- Frontend: [http://dechord.localhost:1355](http://dechord.localhost:1355)
- Backend API: [http://api.dechord.localhost:1355/api/health](http://api.dechord.localhost:1355/api/health)

### Stem Separation Configuration (Environment)

The backend stem splitter is configurable through environment variables and loads `backend/.env` at runtime, so Demucs model overrides apply even when the process was imported before env setup. Playback/download stems still use the raw separated files; tab/MIDI generation now builds a dedicated `bass_analysis.wav` artifact for transcription-focused preprocessing and diagnostics.

| Variable | Default | Description |
| --- | --- | --- |
| `DECHORD_DEMUCS_MODEL` | `htdemucs_ft` | Primary Demucs model name. |
| `DECHORD_DEMUCS_FALLBACK_MODEL` | `htdemucs` | Fallback Demucs model when the primary model is unavailable. |
| `DECHORD_STEM_ENGINE` | `demucs` | Stem engine: `demucs` or `fallback`. |
| `DECHORD_STEM_FALLBACK_ON_ERROR` | `0` | If `1`, fallback splitter runs when Demucs fails. |
| `DECHORD_STEM_DEVICE` | `auto` | Compute device: `auto`, `cpu`, `mps`, `cuda`. |
| `DECHORD_STEM_SEGMENT` | `7.8` | Segment length in seconds (`> 0`). |
| `DECHORD_STEM_OVERLAP` | `0.25` | Segment overlap (`0.0` to `< 1.0`). |
| `DECHORD_STEM_SHIFTS` | `0` | Number of random shifts (`>= 0`). |
| `DECHORD_STEM_INPUT_GAIN_DB` | `0.0` | Gain applied before separation. |
| `DECHORD_STEM_OUTPUT_GAIN_DB` | `0.0` | Gain applied before writing output stems. |
| `DECHORD_STEM_JOBS` | unset | Optional Demucs CPU jobs/thread workers (`>= 0`). |
| `DECHORD_STEM_ANALYSIS_ENABLE` | `1` | If `1`, build a separate analysis-only bass stem for tab/MIDI generation. |
| `DECHORD_STEM_ANALYSIS_HIGHPASS_HZ` | `35` | Analysis stem high-pass filter cutoff (`> 0`). |
| `DECHORD_STEM_ANALYSIS_LOWPASS_HZ` | `300` | Analysis stem low-pass filter cutoff (`> high-pass`). |
| `DECHORD_STEM_ANALYSIS_SAMPLE_RATE` | `22050` | Analysis stem sample rate for refinement and fallback transcription. |
| `DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS` | primary model | Comma-separated candidate model list for future analysis-stem experiments. |
| `DECHORD_STEM_ANALYSIS_ENSEMBLE` | `0` | If `1`, enable candidate-model selection scaffolding for analysis diagnostics. |

Example `backend/.env` for local tinkering:

```bash
DECHORD_DEMUCS_MODEL=htdemucs_ft
DECHORD_DEMUCS_FALLBACK_MODEL=htdemucs
DECHORD_STEM_DEVICE=auto
DECHORD_STEM_SEGMENT=7.8
DECHORD_STEM_OVERLAP=0.25
DECHORD_STEM_SHIFTS=0
DECHORD_STEM_INPUT_GAIN_DB=0.0
DECHORD_STEM_OUTPUT_GAIN_DB=0.0
DECHORD_STEM_ANALYSIS_ENABLE=1
DECHORD_STEM_ANALYSIS_HIGHPASS_HZ=35
DECHORD_STEM_ANALYSIS_LOWPASS_HZ=300
DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS=htdemucs_ft,htdemucs_6s
DECHORD_STEM_ANALYSIS_ENSEMBLE=0
```

Example Linux host CPU-focused config:

```bash
DECHORD_STEM_DEVICE=cpu
DECHORD_STEM_SEGMENT=7.8
DECHORD_STEM_OVERLAP=0.25
DECHORD_STEM_SHIFTS=0
DECHORD_STEM_JOBS=4
DECHORD_STEM_FALLBACK_ON_ERROR=0
```

### Upload Workflow (Web App)

1. Drag/drop or browse an audio file.
2. Choose mode in the upload card:
   - `Analyze chords only` for fastest processing.
   - `Analyze + split stems` to also generate stem tracks.
3. Watch staged progress while processing (overall + current stage).
4. If stems are generated, use the Stem Mixer panel to mute/unmute stems during playback.
5. If bass/drums stem extraction succeeds, the Tab Viewer panel loads generated AlphaTex tabs and syncs with player time.

### tmux Controls

```bash
make backend-up
make backend-attach
make backend-status
make backend-logs
make backend-down

make frontend-up
make frontend-attach
make frontend-status
make frontend-logs
make frontend-down

make up
make down
make status
make logs
make portless-routes
make portless-proxy-up
make portless-proxy-down
```

### Test Commands

```bash
cd backend && uv run pytest tests/ -v
cd frontend && bun run test
cd frontend && bun run build
```
