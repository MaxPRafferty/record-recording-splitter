import argparse
import os
import subprocess
import json
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

def find_side_break(silence_intervals):
    """
    Finds the longest silence interval, assumed to be the side break.
    """
    if not silence_intervals:
        return None
    
    longest_silence = max(silence_intervals, key=lambda i: i[1] - i[0])
    return longest_silence

def duration_to_ms(duration_str):
    """Converts MM:SS string to milliseconds."""
    parts = duration_str.split(':')
    minutes = int(parts[0])
    seconds = int(parts[1])
    return (minutes * 60 + seconds) * 1000

def align_tracks_to_silences(tracks, silences, start_offset=0):
    """
    Aligns a list of tracks with a list of silences to find precise split points.
    Returns a list of tuples: (track_title, start_ms, end_ms)
    """
    aligned_tracks = []
    cumulative_duration = 0
    last_split_point = start_offset

    # If there are no silences to align to, fall back to using cumulative durations
    if not silences:
        print("Warning: No silences found for this side. Falling back to cumulative duration splitting.")
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

    # --- Original 'best-fit' logic ---
    for i, track in enumerate(tracks):
        cumulative_duration += track['duration_ms']
        
        # Find the silence that is closest to our expected split point
        # This is the 'best-fit' part of the algorithm
        closest_silence = min(silences, key=lambda s: abs(s[0] - (start_offset + cumulative_duration)))
        
        # The end of the track is the beginning of the closest silence
        split_point = closest_silence[0]
        
        aligned_tracks.append({
            "title": track['title'],
            "start_ms": last_split_point,
            "end_ms": split_point
        })
        
        # The next track starts at the end of this silence
        last_split_point = closest_silence[1]

    return aligned_tracks


def main(input_audio, output_dir, min_silence_len, silence_thresh):
    artist, album_title = parse_artist_album_from_filename(input_audio)
    if not artist or not album_title:
        return

    # If output_dir is not specified, create it based on the album title
    if not output_dir:
        output_dir = album_title.lower().replace(" ", "_")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    album_data_path = os.path.join(output_dir, "album_data.json")
    if not os.path.exists(album_data_path):
        print(f"Error: '{album_data_path}' not found. Please run fetch_album_data.py first.", file=sys.stderr)
        return

    with open(album_data_path, 'r') as f:
        ALBUM_DATA = json.load(f)
    
    print(f"Starting intelligent track splitting for {input_audio}...")
    
    if not album_title or album_title.lower() not in ALBUM_DATA:
        print(f"Album '{album_title}' not found in database. Aborting.")
        return
        
    album_info = ALBUM_DATA[album_title.lower()]
    for track in album_info['tracks']:
        track['duration_ms'] = duration_to_ms(track['duration'])

    # 1. Detect all silences and the main side break
    silence_intervals = detect_silence_intervals(input_audio, min_silence_len, silence_thresh)
    side_break = find_side_break(silence_intervals)
    
    if not side_break:
        print("Could not identify a side break. Cannot perform intelligent splitting. Aborting.")
        return

    # 2. Separate tracks and silences into Side A and Side B
    side_a_track_count = album_info.get('side_a_tracks', len(album_info['tracks']) // 2)
    side_a_tracks = album_info['tracks'][:side_a_track_count]
    side_b_tracks = album_info['tracks'][side_a_track_count:]

    side_a_silences = [s for s in silence_intervals if s[1] < side_break[0]]
    side_b_silences = [s for s in silence_intervals if s[0] > side_break[1]]
    
    # 3. Align tracks for each side
    aligned_side_a = align_tracks_to_silences(side_a_tracks, side_a_silences, start_offset=0)
    aligned_side_b = align_tracks_to_silences(side_b_tracks, side_b_silences, start_offset=side_break[1])

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
