import argparse
import sys
import json
import os
from record_splitter import parse_artist_album_from_filename, sanitize_filename

try:
    # Import the main functions from the other scripts
    from fetch_album_data import main as fetch_main
    from record_splitter import main as split_main
except ImportError as e:
    print(f"Error: Could not import necessary functions. Make sure all scripts are in the same directory.", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Fetch album data and split a record recording in one command.")
    parser.add_argument("input_audio", type=str, help="Path to the input MP3 file (e.g., 'artist - album.mp3').")
    parser.add_argument("--min_silence_len", type=float, default=1.0,
                        help="Minimum length in seconds of a silence to be considered (default: 1.0s).")
    parser.add_argument("--silence_thresh", type=float, default=-40.0,
                        help="The dBFS value below which audio is considered silent (default: -40.0 dBFS).")
    
    args = parser.parse_args()

    # --- Step 1: Fetch Album Data ---
    print("--- Step 1: Fetching Album Data ---")
    try:
        fetch_main(args.input_audio)
        print("--- Album data fetched successfully. ---\n")
    except SystemExit as e:
        if e.code != 0:
            print("--- Step 1 Failed: Could not fetch album data. Aborting. ---", file=sys.stderr)
            sys.exit(1)

    # --- Step 2: Split Audio with Retry Logic ---
    print("--- Step 2: Splitting Audio ---")

    artist, album_title = parse_artist_album_from_filename(args.input_audio)
    s_artist = sanitize_filename(artist)
    s_album_title = sanitize_filename(album_title)
    album_data_path = os.path.join("output", s_artist, s_album_title, "album_data.json")

    try:
        with open(album_data_path, 'r') as f:
            album_data = json.load(f)
        num_tracks = len(album_data[album_title.lower()]['tracks'])
    except (FileNotFoundError, KeyError):
        print(f"Error: Could not read album data from {album_data_path}. Aborting.", file=sys.stderr)
        sys.exit(1)

    max_retries = 10
    for i in range(max_retries):
        current_silence_thresh = args.silence_thresh + (i * 5)
        print(f"\n--- Attempt {i+1}/{max_retries}: Splitting with silence threshold at {current_silence_thresh}dB ---")
        
        num_silences = split_main(args.input_audio, None, args.min_silence_len, current_silence_thresh)

        if num_tracks -1 <= num_silences <= num_tracks + 2:
            print(f"\n--- Found a suitable number of silences ({num_silences}). Splitting complete. ---")
            break
    else:
        print(f"\n--- Warning: Could not find a suitable number of silences after {max_retries} attempts. ---")
        print("--- The split tracks may not be accurate. ---")

if __name__ == "__main__":
    main()
