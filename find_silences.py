import subprocess
import re
import argparse
import json
import os

def parse_artist_album_from_filename(filepath):
    """
    Parses artist and album from a filename like 'artist - album.mp3'.
    """
    try:
        filename = os.path.basename(filepath)
        name_without_ext = os.path.splitext(filename)[0]
        parts = name_without_ext.split(' - ')
        if len(parts) == 2:
            artist = parts[0].strip()
            album = parts[1].strip()
            return artist, album
        else:
            print(f"Warning: Could not parse artist and album from filename: {filename}")
            return None, None
    except Exception as e:
        print(f"Error parsing filename: {e}")
        return None, None

def detect_silence_intervals(audio_path, min_silence_len=1.0, silence_thresh=-40.0):
    """
    Detects silence intervals in an audio file using ffmpeg's silencedetect filter.

    Args:
        audio_path (str): Path to the input audio file (e.g., MP3).
        min_silence_len (float): Minimum length in seconds of a silence to be considered.
        silence_thresh (float): The dBFS value below which audio is considered silent.

    Returns:
        list: A list of (start_ms, end_ms) tuples representing silence intervals.
    """
    command = [
        "ffmpeg",
        "-i", audio_path,
        "-af", f"silencedetect=noise={silence_thresh}dB:d={min_silence_len}",
        "-f", "null",
        "-"
    ]

    print(f"Running ffmpeg for silence detection: {' '.join(command)}")
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if process.returncode != 0:
        print(f"ffmpeg command failed with error:\n{process.stderr}")
        return []

    silence_intervals = []
    # Regex to find silence start and end
    # [silencedetect @ 0x...] lavfi.c:204] silence_start: 1.23
    # [silencedetect @ 0x...] lavfi.c:204] silence_end: 4.56 | silence_duration: 3.33
    
    silence_start_pattern = re.compile(r"silence_start: (\d+\.?\d*)")
    silence_end_pattern = re.compile(r"silence_end: (\d+\.?\d*)")

    starts = []
    ends = []

    for line in process.stderr.splitlines():
        start_match = silence_start_pattern.search(line)
        end_match = silence_end_pattern.search(line)
        
        if start_match:
            starts.append(float(start_match.group(1)))
        elif end_match:
            ends.append(float(end_match.group(1)))
            
    # Combine starts and ends into intervals
    # If a track starts with silence, or ends with silence, we might get an unmatched start/end.
    # For splitting tracks, we're mostly interested in silence *between* tracks.
    # So we'll pair them up, assuming start precedes end.
    
    i, j = 0, 0
    while i < len(starts) and j < len(ends):
        if starts[i] < ends[j]:
            silence_intervals.append((int(starts[i] * 1000), int(ends[j] * 1000)))
            i += 1
            j += 1
        else: # Unmatched end, perhaps silence from start of file was detected
            j += 1
            
    return silence_intervals

def sanitize_filename(name):
    """
    Removes or replaces characters that are problematic in filenames.
    This is a simple version; a more robust solution might be needed.
    """
    return name.lower().replace(" ", "_").replace("&", "and")

def main():
    parser = argparse.ArgumentParser(description="Detect silence intervals in an audio file and save them to a JSON file.")
    parser.add_argument("audio_file", type=str, help="Path to the input audio file (e.g., 'artist - album.mp3').")
    parser.add_argument("--min_silence_len", type=float, default=1.0,
                        help="Minimum length in seconds of a silence to be considered (default: 1.0s).")
    parser.add_argument("--silence_thresh", type=float, default=-40.0,
                        help="The dBFS value below which audio is considered silent (default: -40.0 dBFS).")

    args = parser.parse_args()

    artist, album = parse_artist_album_from_filename(args.audio_file)

    if not artist or not album:
        print("Could not parse artist and album from filename. Exiting.")
        exit(1)

    intervals = detect_silence_intervals(args.audio_file, args.min_silence_len, args.silence_thresh)

    s_artist = sanitize_filename(artist)
    s_album = sanitize_filename(album)
    output_dir = os.path.join("output", s_artist, s_album)
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "silences.json")

    with open(output_path, 'w') as f:
        json.dump(intervals, f, indent=4)

    print(f"\nDetected silence intervals and saved them to {output_path}")

if __name__ == "__main__":
    main()
