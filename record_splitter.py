import argparse
import os
import subprocess
import json
from datetime import timedelta

import sys
# The silence detection is now handled by find_silences.py
# from detect_silence import detect_silence_intervals
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

def find_side_break(silence_intervals, side_a_duration_ms):
    """
    Finds the silence interval that is closest to the calculated end of Side A.
    """
    if not silence_intervals:
        return None
    
    # Find the silence that is closest to our expected split point
    closest_silence = min(silence_intervals, key=lambda s: abs(s[0] - side_a_duration_ms))
    return closest_silence

def duration_to_ms(duration_str):
    """Converts MM:SS string to milliseconds."""
    parts = duration_str.split(':')
    minutes = int(parts[0])
    seconds = int(parts[1])
    return (minutes * 60 + seconds) * 1000

def split_tracks_by_duration(tracks, start_offset=0):
    """
    Creates a list of tracks with start and end times based on their duration.
    """
    aligned_tracks = []
    last_split_point = start_offset

    for i, track in enumerate(tracks):
        start_ms = last_split_point
        end_ms = start_ms + track['duration_ms']
        aligned_tracks.append({
            "title": track['title'],
            "start_ms": start_ms,
            "end_ms": end_ms
        })
        last_split_point = end_ms
    return aligned_tracks


def sanitize_filename(name):
    """
    Removes or replaces characters that are problematic in filenames.
    This is a simple version; a more robust solution might be needed.
    """
    return name.lower().replace(" ", "_").replace("&", "and")

def get_silence_intervals_from_file(s_artist, s_album_title):
    """
    Loads silence intervals from the generated JSON file.
    """
    silence_file = os.path.join("output", s_artist, s_album_title, "silences.json")

    try:
        with open(silence_file, 'r') as f:
            silence_intervals = json.load(f)
        print(f"--- Silence data loaded from {silence_file} ---")
        return silence_intervals
    except FileNotFoundError:
        print(f"Error: Silence file '{silence_file}' not found. Aborting.", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{silence_file}'. Aborting.", file=sys.stderr)
        return None

def main(input_audio, output_dir, min_silence_len, silence_thresh):
    artist, album_title = parse_artist_album_from_filename(input_audio)
    if not artist or not album_title:
        return 0

    # Sanitize for use in paths
    s_artist = sanitize_filename(artist)
    s_album_title = sanitize_filename(album_title)

    # If output_dir is not specified, create it based on the album title
    if not output_dir:
        output_dir = os.path.join("output", s_artist, s_album_title)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    album_data_path = os.path.join(output_dir, "album_data.json")
    if not os.path.exists(album_data_path):
        print(f"Error: '{album_data_path}' not found. Please run fetch_album_data.py first.", file=sys.stderr)
        return 0

    with open(album_data_path, 'r') as f:
        ALBUM_DATA = json.load(f)
    
    print(f"Starting intelligent track splitting for {input_audio}...")
    
    if not album_title or album_title.lower() not in ALBUM_DATA:
        print(f"Album '{album_title}' not found in database. Aborting.")
        return 0
        
    album_info = ALBUM_DATA[album_title.lower()]
    for track in album_info['tracks']:
        track['duration_ms'] = duration_to_ms(track['duration'])

    # --- New Side-Break Logic ---

    # 1. Calculate the duration of each side
    side_a_track_count = album_info.get('side_a_tracks', len(album_info['tracks']) // 2)
    side_a_tracks = album_info['tracks'][:side_a_track_count]
    side_b_tracks = album_info['tracks'][side_a_track_count:]
    side_a_duration_ms = sum(t['duration_ms'] for t in side_a_tracks)
    side_b_duration_ms = sum(t['duration_ms'] for t in side_b_tracks)

    print(f"Calculated Side A length: {str(timedelta(milliseconds=side_a_duration_ms)).split('.')[0]}")
    print(f"Calculated Side B length: {str(timedelta(milliseconds=side_b_duration_ms)).split('.')[0]}")

    # 2. Iteratively find the best side break
    best_side_break = None
    silence_threshold_step = 5.0 # Increase threshold by 5dB
    max_retries = 10
    
    initial_silence_thresh = silence_thresh # Store initial value

    for i in range(max_retries):
        current_silence_thresh = initial_silence_thresh + (i * silence_threshold_step)
        print(f"\n--- Attempt {i+1}/{max_retries}: Detecting silences at {current_silence_thresh}dB ---")

        # Run silence detection
        silence_py_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'find_silences.py')
        subprocess.run([sys.executable, silence_py_path, input_audio,
                        "--min_silence_len", str(min_silence_len),
                        "--silence_thresh", str(current_silence_thresh)], check=True)
        
        silence_intervals = get_silence_intervals_from_file(s_artist, s_album_title)

        if not silence_intervals:
            print("--- No silences found at this threshold. ---")
            continue

        # Find the silence closest to the calculated end of Side A
        potential_break = find_side_break(silence_intervals, side_a_duration_ms)
        
        if potential_break:
            break_start = potential_break[0]
            break_end = potential_break[1]
            break_duration = break_end - break_start
            break_diff = abs(break_start - side_a_duration_ms)
            
            print(f"Closest silence: Start={str(timedelta(milliseconds=break_start)).split('.')[0]}, End={str(timedelta(milliseconds=break_end)).split('.')[0]}, Duration={break_duration / 1000:.2f}s")
            print(f"Difference from calculated Side A end: {break_diff / 1000:.2f}s")

            if break_diff <= 5000: # 5-second threshold
                print("--- Found a good side break! ---")
                best_side_break = potential_break
                break
    
    if not best_side_break:
        print("\n--- Warning: Could not find a suitable side break after multiple attempts. ---")
        print("--- The split tracks may not be accurate. Will try to split as one side. ---")
        all_aligned_tracks = split_tracks_by_duration(album_info['tracks'])
    else:
        # 3. Split tracks by duration for each side
        # Side A starts at 0 and ends at the start of the side break
        aligned_side_a = split_tracks_by_duration(side_a_tracks, start_offset=0)
        # Side B starts at the end of the side break
        aligned_side_b = split_tracks_by_duration(side_b_tracks, start_offset=best_side_break[1])
        all_aligned_tracks = aligned_side_a + aligned_side_b

    print("\nAligned Tracks:")
    for i, track in enumerate(all_aligned_tracks):
        start_td = str(timedelta(milliseconds=track['start_ms'])).split('.')[0]
        end_td = str(timedelta(milliseconds=track['end_ms'])).split('.')[0]
        print(f"  {i+1:02d}. {track['title']}: {start_td} - {end_td}")

    # 4. Split and rename files
    print("\nSplitting and renaming tracks...")
    for i, track in enumerate(all_aligned_tracks):
        # Sanitize filename
        safe_title = "".join([c for c in track['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        output_filename = os.path.join(output_dir, f"{i+1:02d} - {safe_title}.mp3")
        
        split_audio_segment(input_audio, track['start_ms'], track['end_ms'], output_filename)

    print("\nIntelligent track splitting complete.")
    return len(silence_intervals) if 'silence_intervals' in locals() and silence_intervals is not None else 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a record recording (MP3) into individual tracks.")
    parser.add_argument("input_audio", type=str, help="Path to the input MP3 file.")
    parser.add_argument("--output_dir", type=str, help="Directory to save the split track files (optional).")
    parser.add_argument("--min_silence_len", type=float, default=1.0,
                        help="Minimum length in seconds of a silence to be considered (default: 1.0s).")
    parser.add_argument("--silence_thresh", type=float, default=-40.0,
                        help="The dBFS value below which audio is considered silent (default: -40.0 dBFS).")
    
    args = parser.parse_args()
    
    main(args.input_audio, args.output_dir, args.min_silence_len, args.silence_thresh)
