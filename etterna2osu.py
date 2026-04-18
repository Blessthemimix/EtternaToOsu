import zipfile
import os
import tempfile
import re

# CONFIGURE PATHS HERE BEFORE RUNNING 
SOURCE_ZIP = 'ZIP_ARCHIVE'  
OUTPUT_FOLDER = 'PATH_TO_OUTPUT_FOLDER'
YOUR_OSU_USERNAME = 'mitix' # <-- REPLACE WITH YOUR OSU! USERNAME


def parse_any_sm_content(content):
    data = {
        'title': 'Unknown', 'artist': 'Unknown', 'audio': '', 'bg': '',
        'timing_point': '', 'hit_objects': []
    }
    
    # 1. Metadata extraction
    data['title'] = (re.findall(r'#TITLE:(.*?);', content, re.I) or ['Unknown'])[0].strip()
    data['artist'] = (re.findall(r'#ARTIST:(.*?);', content, re.I) or ['Unknown'])[0].strip()
    data['audio'] = (re.findall(r'#MUSIC:(.*?);', content, re.I) or [''])[0].strip()
    data['bg'] = (re.findall(r'#BACKGROUND:(.*?);', content, re.I) or [''])[0].strip()

    # 2. Timing points extraction (BPM and Offset)
    bpm_match = re.search(r'#BPMS:.*?=(\d+\.?\d*).*?;', content, re.I | re.S)
    bpm = float(bpm_match.group(1)) if bpm_match else 120.0
    offset_match = re.search(r'#OFFSET:(-?\d+\.?\d*);', content, re.I)
    offset_sec = float(offset_match.group(1)) if offset_match else 0.0
    
    start_time_ms = -offset_sec * 1000 
    beat_duration_ms = 60000.0 / bpm
    data['timing_point'] = f"{int(start_time_ms)},{beat_duration_ms},4,1,0,100,1,0"

    # Split the file into difficulty blocks
    blocks = re.split(r'#NOTES:|#NOTEDATA:', content, flags=re.I)
    all_difficulties = []

    for block in blocks[1:]:
        # Attempt to determine the difficulty level (Meter)
        meter = 0
        meter_match = re.search(r'#METER:(\d+)', block, re.I)
        if meter_match:
            meter = int(meter_match.group(1))
        else:
            # Fallback for older .sm files (usually the 4th element in the header)
            parts_header = block.split(':')
            if len(parts_header) >= 6:
                try:
                    meter = float(parts_header[3].strip())
                except ValueError:
                    pass

        # Isolate the actual note data
        parts = block.split(':')
        notes_data = parts[-1].split(';')[0].strip()
        
        if ',' not in notes_data: continue 
        
        measures = notes_data.split(',')
        current_time_ms = start_time_ms
        measure_duration_ms = beat_duration_ms * 4
        
        temp_hits = []
        # Tracker for Long Notes (Holds) across 4 columns
        active_holds = {0: None, 1: None, 2: None, 3: None}
        
        for measure in measures:
            lines = [l.strip() for l in measure.split('\n') if l.strip() and not l.startswith('//')]
            if not lines: continue
            
            line_time = measure_duration_ms / len(lines)
            for line in lines:
                for col, char in enumerate(line[:4]):
                    x = 64 + (col * 128)
                    
                    if char == '1': # Regular note (Rice)
                        temp_hits.append(f"{int(x)},192,{int(current_time_ms)},1,1,0:0:0:0:")
                    
                    elif char in '24': # 2 - Hold start, 4 - Roll start (treated as hold)
                        active_holds[col] = current_time_ms
                        
                    elif char == '3': # 3 - Hold end
                        start_time = active_holds[col]
                        if start_time is not None:
                            # osu! LN format: Type = 128, 6th parameter contains EndTime
                            end_time = int(current_time_ms)
                            temp_hits.append(f"{int(x)},192,{int(start_time)},128,1,{end_time}:0:0:0:0:")
                            active_holds[col] = None # Reset tracker
                            
                current_time_ms += line_time
        
        # If the difficulty contains notes, save it as a candidate
        if temp_hits:
            all_difficulties.append({
                'meter': meter,
                'note_count': len(temp_hits),
                'hits': temp_hits
            })

    # Select the most difficult chart (sort by Meter, then by total note count)
    if all_difficulties:
        best_diff = max(all_difficulties, key=lambda d: (d['meter'], d['note_count']))
        data['hit_objects'] = best_diff['hits']

    return data

def convert_etterna_to_osu(zip_path, out_dir):
    if not os.path.exists(zip_path):
        print(f"❌ Error: File '{zip_path}' not found!")
        return
    if not os.path.exists(out_dir): os.makedirs(out_dir)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📦 Extracting archive: {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        count = 0
        for root, dirs, files in os.walk(temp_dir):
            chart_files = [f for f in files if f.endswith('.sm') or f.endswith('.ssc')]
            if chart_files:
                try:
                    # Prioritize .ssc files as they are more accurate for Etterna
                    chart_files.sort(key=lambda x: x.endswith('.ssc'), reverse=True)
                    chart_path = os.path.join(root, chart_files[0])
                    
                    with open(chart_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        data = parse_any_sm_content(content)
                    
                    if not data['hit_objects']:
                        print(f"⚠️ Warning: No valid notes found in {chart_path}, skipping.")
                        continue

                    # Construct the .osu file content
                    osu_content = (
                        f"osu file format v14\n\n"
                        f"[General]\n"
                        f"AudioFilename: {data['audio']}\n"
                        f"AudioLeadIn: 0\n"
                        f"PreviewTime: 45000\n"
                        f"SampleSet: Normal\n"
                        f"Mode: 3\n\n"
                        f"[Metadata]\n"
                        f"Title:{data['title']}\n"
                        f"Artist:{data['artist']}\n"
                        f"Creator:{YOUR_OSU_USERNAME}\n"
                        f"Version:Top Diff\n\n"
                        f"[Difficulty]\n"
                        f"CircleSize:4\n\n"
                        f"[Events]\n"
                        f"0,0,\"{data['bg']}\",0,0\n\n"
                        f"[TimingPoints]\n"
                        f"{data['timing_point']}\n\n"
                        f"[HitObjects]\n"
                    ) + "\n".join(data['hit_objects'])
                    
                    safe_name = "".join([c for c in f"{data['artist']} - {data['title']}" if c.isalnum() or c in " - "]).strip()
                    osu_file_path = os.path.join(root, f"{safe_name}.osu")
                    
                    with open(osu_file_path, 'w', encoding='utf-8') as f:
                        f.write(osu_content)
                    
                    # Package back into a standard osu! format (.osz)
                    osz_path = os.path.join(out_dir, f"{safe_name}.osz")
                    with zipfile.ZipFile(osz_path, 'w') as osz:
                        for f in os.listdir(root):
                            if not (f.endswith('.sm') or f.endswith('.ssc')):
                                osz.write(os.path.join(root, f), f)
                    
                    print(f"✅ Success: {safe_name} ({len(data['hit_objects'])} objects, Top Diff)")
                    count += 1
                except Exception as e:
                    print(f"❌ Error processing {root}: {e}")

    print(f"\n🚀 Summary: Successfully converted {count} charts.")

if __name__ == "__main__":
    convert_etterna_to_osu(SOURCE_ZIP, OUTPUT_FOLDER)