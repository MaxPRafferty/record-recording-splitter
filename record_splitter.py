import argparse
import os
import subprocess
from datetime import timedelta

# Assuming detect_silence.py and split_audio.py are in the same directory
from detect_silence import detect_silence_intervals
from split_audio import split_audio_segment

def get_audio_duration(audio_path):
    """
    Gets the duration of an audio file in milliseconds using ffmpeg.
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        duration_seconds = float(result.stdout.strip())
        return int(duration_seconds * 1000)
    except Exception as e:
        print(f"Error getting audio duration for {audio_path}: {e}")
        return None

def main(input_audio, output_dir, min_silence_len, silence_thresh):
    print(f"Starting track splitting for {input_audio}...")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Detect silence intervals
    silence_intervals = detect_silence_intervals(input_audio, min_silence_len, silence_thresh)
    
    if not silence_intervals:
        print("No silence intervals detected. Splitting into one single track.")
        total_duration = get_audio_duration(input_audio)
        if total_duration is None:
            print("Could not determine audio duration. Aborting.")
            return

        output_filename = os.path.join(output_dir, f"track_01.mp3")
        split_audio_segment(input_audio, 0, total_duration, output_filename)
        return

    total_duration = get_audio_duration(input_audio)
    if total_duration is None:
        print("Could not determine audio duration. Aborting.")
        return

    # 2. Determine track boundaries based on silence intervals
    track_boundaries = [] # List of (start_ms, end_ms) for each track
    current_start = 0

    for i, (silence_start, silence_end) in enumerate(silence_intervals):
        # A track ends just before silence starts
        if silence_start > current_start: # Ensure there's actual audio before silence
            track_boundaries.append((current_start, silence_start))
        
        # The next track starts after silence ends
        current_start = silence_end
    
    # Add the last track (from the end of the last silence to the end of the audio)
    if current_start < total_duration:
        track_boundaries.append((current_start, total_duration))
    
    if not track_boundaries:
        print("No track boundaries determined. Aborting.")
        return

    print(f"\nDetermined {len(track_boundaries)} tracks:")
    for i, (start, end) in enumerate(track_boundaries):
        start_td = str(timedelta(milliseconds=start)).split('.')[0]
        end_td = str(timedelta(milliseconds=end)).split('.')[0]
        print(f"  Track {i+1:02d}: {start_td} - {end_td} ({end - start}ms)")

    # 3. Split the audio into individual tracks
    print("\nSplitting audio into tracks...")
    for i, (start, end) in enumerate(track_boundaries):
        output_filename = os.path.join(output_dir, f"track_{i+1:02d}.mp3")
        split_audio_segment(input_audio, start, end, output_filename)

    print("\nTrack splitting complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a record recording (MP3) into individual tracks.")
    parser.add_argument("input_audio", type=str, help="Path to the input MP3 file.")
    parser.add_argument("output_dir", type=str, help="Directory to save the split track files.")
    parser.add_argument("--min_silence_len", type=float, default=1.0,
                        help="Minimum length in seconds of a silence to be considered (default: 1.0s).")
    parser.add_argument("--silence_thresh", type=float, default=-40.0,
                        help="The dBFS value below which audio is considered silent (default: -40.0 dBFS).")
    
    args = parser.parse_args()
    
    main(args.input_audio, args.output_dir, args.min_silence_len, args.silence_thresh)
