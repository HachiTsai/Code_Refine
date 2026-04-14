import os
import sys
import json
import uuid
import pandas as pd
import subprocess
from pathlib import Path

# ==============================================================================
# 🛡️ [v2.1] Excalidraw Toolkit & Type Shield
# ==============================================================================
__version__ = "v2.1 (Toolkit Hardening)"





# --- Helper Functions for Excalidraw Elements ---

def generate_id():
    return str(uuid.uuid4()).replace('-', '')[:16]

def create_excalidraw_element(type, x, y, width, height, **kwargs):
    base = {
        "id": generate_id(),
        "type": type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#000000",
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "strokeSharpness": "sharp",
        "seed": 123456,
        "version": 1,
        "versionNonce": 0,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }
    base.update(kwargs)
    return base

def write_excalidraw_md(output_path, excalidraw_data):
    """Writes the Excalidraw JSON into the Obsidian Markdown format."""
    
    # Extract text for searchability
    elements = excalidraw_data.get("elements", [])
    text_elements_content = ""
    for el in elements:
        if el.get("type") == "text" and "text" in el:
            text_elements_content += f"{el['text']} ^\n"

    # Construct Markdown content
    md_content = f"""
---
excalidraw-plugin: parsed
tags: [excalidraw]
---
# Text Elements
{text_elements_content}
# Drawing
```json
{json.dumps(excalidraw_data, indent=2, ensure_ascii=False)}
```
"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Successfully created: {output_path}")
    except Exception as e:
        print(f"Error writing file: {e}")

# --- Logic: CSV to Excalidraw ---

def process_csv(csv_path):
    print(f"Detected CSV input: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Normalize column names for flexibility
    df.columns = [c.strip() for c in df.columns]

    # Determine coordinate columns
    has_xy_cols = 'X' in df.columns and 'Y' in df.columns
    has_combined_coord = 'X,Y' in df.columns

    # Determine label column
    label_col = None
    if 'Label' in df.columns:
        label_col = 'Label'
    elif 'SLC NO.' in df.columns:
        label_col = 'SLC NO.'
    
    if not (has_xy_cols or has_combined_coord):
        print("Error: Coordinates not found. Need 'X' and 'Y' columns OR 'X,Y' column.")
        return
    
    if not label_col:
        print("Error: Label column not found. Need 'Label' or 'SLC NO.' column.")
        return

    elements = []
    print(f"Found {len(df)} rows. Generating elements...")

    for index, row in df.iterrows():
        try:
            x = 0
            y = 0
            
            # Extract coordinates
            if has_xy_cols:
                x = float(row['X'])
                y = float(row['Y'])
            elif has_combined_coord:
                coord_str = str(row['X,Y'])
                if ',' in coord_str:
                    x_str, y_str = coord_str.split(',')
                    x = float(x_str.strip())
                    y = float(y_str.strip())
                else:
                    continue # Skip invalid format

            label_text = str(row[label_col])
            
            group_id = generate_id()
            
            # Dot
            dot_size = 10
            dot = create_excalidraw_element(
                type="ellipse",
                x=x - (dot_size/2),
                y=y - (dot_size/2),
                width=dot_size,
                height=dot_size,
                backgroundColor="#3c65bc",
                strokeColor="transparent",
                fillStyle="solid",
                groupIds=[group_id]
            )
            
            # Label
            text_width = len(label_text) * 8 
            text = create_excalidraw_element(
                type="text",
                x=x + 8,
                y=y - 10,
                width=text_width,
                height=20,
                text=label_text,
                fontSize=16,
                fontFamily=1,
                textAlign="left",
                verticalAlign="top",
                groupIds=[group_id]
            )
            
            elements.append(dot)
            elements.append(text)
        except ValueError:
            continue
    
    # ... rest of function ...
    excalidraw_data = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
        "files": {}
    }

    # Output filename: .csv -> .excalidraw.md
    base_name = os.path.splitext(csv_path)[0]
    output_path = f"{base_name}.excalidraw.md"
    write_excalidraw_md(output_path, excalidraw_data)


# --- Logic: Legacy JSON to New MD ---

def process_legacy_json(json_path):
    print(f"Detected Legacy Excalidraw input: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # Output filename: .excalidraw -> .excalidraw.md
    output_path = json_path + ".md"
    
    write_excalidraw_md(output_path, data)

# --- Main Dispatcher ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_to_excalidraw.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    _, ext = os.path.splitext(input_file)
    ext = ext.lower()

    if ext == ".csv":
        process_csv(input_file)
    elif ext == ".excalidraw" or ext == ".json":
        process_legacy_json(input_file)
    else:
        print(f"Unsupported file extension: {ext}. Please use .csv or .excalidraw")
