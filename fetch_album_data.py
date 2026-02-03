import argparse
import json
import requests
import sys
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

def search_release(artist, album):
    """
    Searches for a release on MusicBrainz.
    """
    headers = {
        'User-Agent': 'RecordRecordingSplitter/1.0 ( gemini-cli@example.com )'
    }
    search_url = f"https://musicbrainz.org/ws/2/release/?query=artist:{artist} AND release:{album} AND primarytype:album&fmt=json"
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data['releases']:
            return data['releases']
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error searching for release: {e}", file=sys.stderr)
        return None

def get_release_details(release_id):
    """
    Gets detailed information for a specific release, including track listing.
    """
    headers = {
        'User-Agent': 'RecordRecordingSplitter/1.0 ( gemini-cli@example.com )'
    }
    # inc=recordings is crucial to get track details
    details_url = f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json"

    try:
        response = requests.get(details_url, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error getting release details: {e}", file=sys.stderr)
        return None

def format_duration(milliseconds):
    """Converts milliseconds to MM:SS format."""
    if not milliseconds:
        return "0:00"
    seconds = int(milliseconds) // 1000
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes}:{seconds:02}"

def main():
    parser = argparse.ArgumentParser(description="Fetch album data from MusicBrainz and create album_data.json in a new folder.")
    parser.add_argument("input_file", type=str, help="The input audio file (e.g., 'artist - album.mp3').")
    
    args = parser.parse_args()

    artist, album = parse_artist_album_from_filename(args.input_file)
    if not artist or not album:
        sys.exit(1)

    # Create a directory for the album
    output_dir = album.lower().replace(" ", "_")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Searching for '{album}' by '{artist}'...")
    release_list = search_release(artist, album)

    if not release_list:
        print("Could not find a matching release on MusicBrainz.", file=sys.stderr)
        sys.exit(1)

    # Find the first release that doesn't have "live" in the title
    release = None
    for r in release_list:
        if 'live' not in r['title'].lower():
            release = r
            break
    
    # If no non-live release is found, fall back to the first one
    if not release:
        release = release_list[0]

    print(f"Selected release: {release['title']} ({release['id']})")
    
    release_details = get_release_details(release['id'])
    
    if not release_details:
        print("Could not retrieve release details.", file=sys.stderr)
        sys.exit(1)

    # Assume the first media entry is what we want (e.g., CD 1, or Side A/B)
    # A more complex script might handle multi-disc albums.
    tracks_data = release_details['media'][0]['tracks']

    album_struct = {
        release['title'].lower(): {
            "artist": release['artist-credit'][0]['name'].lower(),
            "tracks": [],
            # A default assumption. The user might need to adjust this.
            "side_a_tracks": len(tracks_data) // 2
        }
    }

    print("\nProcessing tracks...")
    for i, track in enumerate(tracks_data):
        title = track['title']
        # 'length' is in milliseconds
        duration_ms = track.get('length') 
        duration_str = format_duration(duration_ms)
        
        album_struct[release['title'].lower()]['tracks'].append({
            "title": title,
            "duration": duration_str
        })
        print(f"  {i+1:02d}. {title} ({duration_str})")


    # Write to the output file
    output_path = os.path.join(output_dir, "album_data.json")
    try:
        with open(output_path, 'w') as f:
            json.dump(album_struct, f, indent=4)
        print(f"\nSuccessfully created '{output_path}'.")
        print("NOTE: The 'side_a_tracks' value is an estimate. Please verify and adjust it if necessary.")

    except IOError as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
