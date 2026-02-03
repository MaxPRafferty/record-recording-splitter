# Record Recording Splitter

This project provides a Python script to intelligently split a single MP3 file (typically a recording of a vinyl record) into individual track files. It leverages online album tracklist data to accurately determine track boundaries and names the output files accordingly.

## Features

*   **Intelligent Track Splitting**: Uses a "best-fit" algorithm to align detected silence intervals with known track durations from an online tracklist.
*   **Side Break Detection**: Identifies the longest silence as a potential record side flip, crucial for accurate splitting.
*   **Track Naming**: Automatically names output files with track numbers and titles (e.g., "01 - Track Title.mp3").
*   **Robustness**: Falls back to cumulative duration splitting if no inter-track silences are detected on a record side.

## Requirements

*   **Python 3.x**
*   **ffmpeg** and **ffprobe**: These command-line tools are essential for audio processing (silence detection and splitting).
    *   Ensure `ffmpeg` and `ffprobe` are installed and accessible in your system's PATH. You can often install them via your system's package manager (e.g., `sudo apt-get install ffmpeg` on Debian/Ubuntu, `brew install ffmpeg` on macOS).
*   **pydub**: A Python library that interacts with `ffmpeg`/`ffprobe` for audio manipulation.
    *   Install it using pip: `pip install pydub` (or `python3 -m pip install pydub` if you have multiple Python versions).

## Setup

1.  **Install Python dependencies**:
    ```bash
    pip install pydub
    ```
    (You might need to use `python3 -m pip install pydub` or refer to your `pyenv` or `conda` setup if you have specific Python environments.)

2.  **Ensure ffmpeg/ffprobe are installed**:
    Verify their installation by running:
    ```bash
    ffmpeg -version
    ffprobe -version
    ```

## Usage

### 1. Prepare your input MP3 file

Name your input MP3 file in the format `Artist - Album.mp3`.
For example: `moody blues - days of future passed.mp3`

### 2. Fetch Album Data

First, you need to fetch the album's tracklist and other metadata from MusicBrainz. This script will create a dedicated folder for the album, named `./output/<artist_slug>/<album_slug>/`, and place an `album_data.json` file inside it.

```bash
python3 fetch_album_data.py "path/to/your/input.mp3"
```

**Example:**
```bash
python3 fetch_album_data.py "moody blues - days of future passed.mp3"
```

This will create `output/moody_blues/days_of_future_passed/album_data.json`.
**NOTE**: The `side_a_tracks` value in the generated `album_data.json` is an estimate. Please verify and adjust it if necessary by editing the JSON file directly.

### 3. Run the Splitter Script

Once you have the `album_data.json` file in the correct album-specific directory, you can run the splitter script. It will automatically find the `album_data.json` in the `./output/<artist_slug>/<album_slug>/` directory (derived from your input filename) and save the split tracks into that same directory.

```bash
python3 record_splitter.py "path/to/your/input.mp3" [--min_silence_len SECONDS] [--silence_thresh DBFS]
```

**Example:**
```bash
python3 record_splitter.py "moody blues - days of future passed.mp3"
```

**Arguments:**

*   `input_audio`: Path to your input MP3 file.
*   `--output_dir` (Optional): If provided, overrides the default output directory structure (`./output/<artist_slug>/<album_slug>/`).
*   `--min_silence_len` (Optional, default: 1.0): Minimum length in *seconds* of a silence to be considered by `ffmpeg`'s `silencedetect` filter. Adjust this if `ffmpeg` detects too many or too few silences.
*   `--silence_thresh` (Optional, default: -40.0): The dBFS value below which audio is considered silent by `ffmpeg`. Lower (more negative) values mean quieter sounds are still considered "audio."

## Output

The script will create a series of MP3 files in the `./output/<artist_slug>/<album_slug>/` directory, named with their track number and title (e.g., `01 - The Day Begins.mp3`).

## Considerations

*   **Silence Detection**: The accuracy of splitting heavily relies on `ffmpeg`'s `silencedetect` filter. You might need to experiment with `--min_silence_len` and `--silence_thresh` parameters for optimal results, especially with noisy recordings.
*   **Record Flip**: The script identifies the single longest silence as the point where the record was flipped (Side A / Side B). Ensure your recording has a distinct long pause for this to work effectively.
*   **Missing Silences**: If a side has no detectable silences between tracks, the script will fall back to splitting purely based on the cumulative durations provided in `ALBUM_DATA`. This is less precise but prevents failure.