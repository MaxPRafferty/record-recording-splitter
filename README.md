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

### 2. Update `ALBUM_DATA` in `record_splitter.py`

The script uses a hardcoded `ALBUM_DATA` dictionary to fetch track information. You need to add an entry for your album in `record_splitter.py`.

Open `record_splitter.py` and locate the `ALBUM_DATA` dictionary. Add a new entry like this:

```python
ALBUM_DATA = {
    # Existing entries...
    "your album title in lowercase": {
        "artist": "your artist name in lowercase",
        "tracks": [
            {"title": "Track 1 Title", "duration": "MM:SS"},
            {"title": "Track 2 Title", "duration": "MM:SS"},
            # ... add all tracks
        ],
        "side_a_tracks": N # Optional: Number of tracks on Side A (defaults to half if not specified)
    },
    # Example:
    "days of future passed": {
        "artist": "moody blues",
        "tracks": [
            {"title": "The Day Begins", "duration": "5:45"},
            {"title": "Dawn: Dawn Is A Feeling", "duration": "3:50"},
            {"title": "The Morning: Another Morning", "duration": "3:40"},
            {"title": "Lunch Break: Peak Hour", "duration": "5:21"},
            {"title": "The Afternoon: Forever Afternoon (Tuesday?)", "duration": "8:25"},
            {"title": "Evening: The Sun Set: Twilight Time", "duration": "6:39"},
            {"title": "The Night: Nights In White Satin", "duration": "7:41"}
        ],
        "side_a_tracks": 4 
    }
}
```
*   **Keys (`"your album title in lowercase"`)**: Must exactly match the album part of your filename (e.g., `days of future passed` for `moody blues - days of future passed.mp3`), converted to lowercase.
*   **`artist`**: The artist's name (lowercase).
*   **`tracks`**: A list of dictionaries, each with:
    *   `"title"`: The exact title of the track.
    *   `"duration"`: The official duration of the track in "MM:SS" format.
*   **`side_a_tracks` (Optional)**: Specify the number of tracks on Side A of the record. If omitted, the script will assume the tracks are split roughly in half.

### 3. Run the script

Execute the `record_splitter.py` script from your terminal:

```bash
/path/to/your/python record_splitter.py "path/to/your/input.mp3" "path/to/your/output_directory" [--min_silence_len SECONDS] [--silence_thresh DBFS]
```

**Example:**
```bash
~/.pyenv/versions/3.14.2/bin/python record_splitter.py "moody blues - days of future passed.mp3" final_tracks
```

**Arguments:**

*   `input_audio`: Path to your input MP3 file.
*   `output_dir`: Path to the directory where the split track files will be saved.
*   `--min_silence_len` (Optional, default: 1.0): Minimum length in *seconds* of a silence to be considered by `ffmpeg`'s `silencedetect` filter. Adjust this if `ffmpeg` detects too many or too few silences.
*   `--silence_thresh` (Optional, default: -40.0): The dBFS value below which audio is considered silent by `ffmpeg`. Lower (more negative) values mean quieter sounds are still considered "audio."

## Output

The script will create a series of MP3 files in your specified `output_dir`, named with their track number and title (e.g., `01 - The Day Begins.mp3`).

## Considerations

*   **Silence Detection**: The accuracy of splitting heavily relies on `ffmpeg`'s `silencedetect` filter. You might need to experiment with `--min_silence_len` and `--silence_thresh` parameters for optimal results, especially with noisy recordings.
*   **Record Flip**: The script identifies the single longest silence as the point where the record was flipped (Side A / Side B). Ensure your recording has a distinct long pause for this to work effectively.
*   **Missing Silences**: If a side has no detectable silences between tracks, the script will fall back to splitting purely based on the cumulative durations provided in `ALBUM_DATA`. This is less precise but prevents failure.