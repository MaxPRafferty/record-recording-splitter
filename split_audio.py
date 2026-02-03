import subprocess
import os
import argparse

def split_audio_segment(input_path, start_ms, end_ms, output_path):
    """
    Splits an audio file into a segment using ffmpeg.

    Args:
        input_path (str): Path to the input audio file.
        start_ms (int): Start time of the segment in milliseconds.
        end_ms (int): End time of the segment in milliseconds.
        output_path (str): Path for the output segment file.

    Returns:
        bool: True if splitting was successful, False otherwise.
    """
    start_sec = start_ms / 1000.0
    end_sec = end_ms / 1000.0
    duration_sec = end_sec - start_sec

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    command = [
        "ffmpeg",
        "-i", input_path,
        "-ss", str(start_sec),
        "-to", str(end_sec),
        "-c", "copy",
        output_path
    ]

    print(f"Splitting audio from {start_sec:.2f}s to {end_sec:.2f}s to {output_path}")
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')

    if process.returncode != 0:
        print(f"ffmpeg split command failed for {output_path} with error:\n{process.stderr}")
        return False
    else:
        print(f"Successfully split audio to {output_path}")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split an audio file into segments using ffmpeg.")
    parser.add_argument("input_file", type=str, help="Path to the input audio file (e.g., MP3).")
    parser.add_argument("output_dir", type=str, help="Directory to save the split audio files.")
    parser.add_argument("--segments", type=str, nargs='+', required=True,
                        help="List of segments as 'start_ms,end_ms,filename'. "
                             "Example: '0,60000,track1.mp3' '60000,120000,track2.mp3'")

    args = parser.parse_args()

    for segment_str in args.segments:
        parts = segment_str.split(',')
        if len(parts) == 3:
            start_ms = int(parts[0])
            end_ms = int(parts[1])
            filename = parts[2]
            output_path = os.path.join(args.output_dir, filename)
            split_audio_segment(args.input_file, start_ms, end_ms, output_path)
        else:
            print(f"Invalid segment format: {segment_str}. Expected 'start_ms,end_ms,filename'")
