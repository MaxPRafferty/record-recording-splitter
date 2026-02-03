import re

def parse_raw_tracklist_data(raw_data):
    """
    Parses raw text data to extract a list of tracks with titles and durations
    using a more robust, line-by-line heuristic approach.
    """
    tracks = []
    time_pattern = re.compile(r'(\d{1,2}:\d{2})$')
    
    for line in raw_data.strip().split('\n'):
        line = line.strip()
        time_match = time_pattern.search(line)
        
        if not time_match:
            continue

        duration = time_match.group(1)
        title_part = line[:time_match.start()].strip()
        
        title_part = re.sub(r'^\d+\.\s*', '', title_part)
        title_part = title_part.rstrip(' -–')
        title_part = title_part.strip('"')
        
        if title_part:
            tracks.append({"title": title_part, "duration": duration})
            
    return tracks

if __name__ == '__main__':
    print("--- Testing Parser ---")
    sample_raw_data = """
    1. "The Day Begins" - 5:45
    2. "Dawn: Dawn Is a Feeling" - 3:50
    3. "The Morning: Another Morning" - 3:40
    4. "Lunch Break: Peak Hour" - 5:21
    5. "The Afternoon: Forever Afternoon (Tuesday?)" / "Time To Get Away" - 8:23
    6. "Evening: The Sunset" / "Twilight Time" - 6:40
    7. "The Night: Nights in White Satin" - 7:41
    """
    
    parsed_tracks = parse_raw_tracklist_data(sample_raw_data)
    
    if parsed_tracks:
        print("Parse successful. Found tracks:")
        for i, track in enumerate(parsed_tracks):
            print(f"  {i+1}. {track['title']} ({track['duration']})")
    else:
        print("Parse failed or no tracks found.")

