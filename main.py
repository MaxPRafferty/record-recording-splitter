import argparse
import sys

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
    
    # --- Step 2: Split Audio ---
    print("--- Step 2: Splitting Audio ---")
    try:
        # The splitter's main function takes output_dir as None by default
        split_main(args.input_audio, None, args.min_silence_len, args.silence_thresh)
        print("--- Audio splitting complete. ---")
    except SystemExit as e:
        if e.code != 0:
            print("--- Step 2 Failed: Could not split audio. ---", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
