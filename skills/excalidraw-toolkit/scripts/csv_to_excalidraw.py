import os
import sys
import json
import uuid
import pandas as pd
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union

# ==============================================================================
# 🛡️ [v2.1] Excalidraw Toolkit & Type Shield
# ==============================================================================
__version__ = "v2.1 (Toolkit Hardening)"

class ExcalidrawContract:
    """[v2.0] 邏輯契約：驗證 CSV 轉換與 JSON 匯出的合規性。"""
    
    @staticmethod
    def validate_csv_columns(df: pd.DataFrame) -> bool:
        """驗證 CSV 是否包含必要的座標與標籤欄位。"""
        cols = [c.strip().upper() for c in df.columns]
        has_coord = ('X' in cols and 'Y' in cols) or ('X,Y' in cols)
        has_label = ('LABEL' in cols) or ('SLC NO.' in cols)
        
        if not has_coord:
            print("   ❌ [Contract] Error: Missing coordinates (X, Y or X,Y).")
            return False
        if not has_label:
            print("   ❌ [Contract] Error: Missing label (Label or SLC NO.).")
            return False
        return True

    @staticmethod
    def validate_element_count(elements: List[Dict[str, Any]], expected_rows: int) -> bool:
        """驗證生成的元素數量是否與 CSV 行數一致 (Dot + Label = 2x rows)。"""
        if len(elements) < expected_rows:
            print(f"   ⚠️ [Contract] Warning: Generated elements ({len(elements)}) less than expected ({expected_rows * 2}).")
            return False
        return True

# ==============================================================================
# 🛠️ Utility Functions
# ==============================================================================

def handshake() -> None:
    """Report status to workflow-orchestrator."""
    try:
        root = Path(__file__).resolve().parents[4]
        manager_path = root / ".gemini" / "skills" / "workflow-orchestrator" / "scripts" / "skill_manager.py"
        if manager_path.exists():
            subprocess.run([sys.executable, str(manager_path), "--update-cache"], check=False, capture_output=True)
            print("   ✅ [Handshake] Skill cache updated.")
    except Exception as e:
        print(f"   ⚠️ [Handshake] Failed: {e}")

def generate_id() -> str:
    return str(uuid.uuid4()).replace('-', '')[:16]

def create_excalidraw_element(type: str, x: float, y: float, width: float, height: float, **kwargs: Any) -> Dict[str, Any]:
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

def write_excalidraw_md(output_path: str, excalidraw_data: Dict[str, Any]) -> None: 
    """Writes the Excalidraw JSON into the Obsidian Markdown format."""
    elements = excalidraw_data.get("elements", [])
    text_elements_content = ""
    for el in elements:
        if el.get("type") == "text" and "text" in el:
            text_elements_content += f"{el['text']} ^\n"

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
        print(f"✅ [Exporter] Successfully created: {output_path}")
    except Exception as e:
        print(f"❌ [Exporter] Error writing file: {e}")

# ==============================================================================
# 🎨 Logic: CSV to Excalidraw
# ==============================================================================

def process_csv(csv_path: str) -> None:
    print(f"🚀 [CSV Mode] Processing: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ [CSV Mode] Error reading CSV: {e}")
        return

    # Step 1: Logic Contract Check (Columns)
    if not ExcalidrawContract.validate_csv_columns(df):
        return

    df.columns = [c.strip() for c in df.columns]
    has_xy_cols = 'X' in df.columns and 'Y' in df.columns
    has_combined_coord = 'X,Y' in df.columns

    label_col = 'Label' if 'Label' in df.columns else 'SLC NO.'
    elements: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        try:
            x, y = 0.0, 0.0
            if has_xy_cols:
                x, y = float(row['X']), float(row['Y'])
            elif has_combined_coord:
                coord_str = str(row['X,Y'])
                if ',' in coord_str:
                    x_str, y_str = coord_str.split(',')
                    x, y = float(x_str.strip()), float(y_str.strip())
                else: continue

            label_text = str(row[label_col])
            group_id = generate_id()
            
            # Dot
            elements.append(create_excalidraw_element(
                type="ellipse", x=x-5, y=y-5, width=10, height=10,
                backgroundColor="#3c65bc", strokeColor="transparent", fillStyle="solid", groupIds=[group_id]
            ))
            
            # Label
            elements.append(create_excalidraw_element(
                type="text", x=x+8, y=y-10, width=len(label_text)*8, height=20,
                text=label_text, fontSize=16, fontFamily=1, textAlign="left", verticalAlign="top", groupIds=[group_id]
            ))
        except (ValueError, KeyError):
            continue
    
    # Step 2: Logic Contract Check (Elements)
    ExcalidrawContract.validate_element_count(elements, len(df))

    excalidraw_data = {
        "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
        "elements": elements, "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20}, "files": {}
    }

    base_name = os.path.splitext(csv_path)[0]
    write_excalidraw_md(f"{base_name}.excalidraw.md", excalidraw_data)

def process_legacy_json(json_path: str) -> None:
    print(f"🚀 [Legacy Mode] Processing: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        write_excalidraw_md(json_path + ".md", data)
    except Exception as e:
        print(f"❌ [Legacy Mode] Error: {e}")

# ==============================================================================
# 🏁 Main Entry
# ==============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"🎨 Excalidraw Toolkit {__version__}")
        print("Usage: python csv_to_excalidraw.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"❌ Error: File '{input_file}' not found.")
        sys.exit(1)

    _, ext = os.path.splitext(input_file)
    ext = ext.lower()

    if ext == ".csv":
        process_csv(input_file)
    elif ext in [".excalidraw", ".json"]:
        process_legacy_json(input_file)
    else:
        print(f"❌ Unsupported extension: {ext}")
