import os
import re
import argparse
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import fnmatch
from typing import List, Optional, Dict, Union, Set, Tuple, Any

# ==============================================================================
# 🛡️ [v2.1] Type Shield & Logic Contract
# ==============================================================================
try:
    import yaml  # type: ignore
    yaml_lib = yaml
except ImportError:
    yaml_lib = None

try:
    import chardet  # type: ignore
    chardet_lib = chardet
except ImportError:
    chardet_lib = None

__version__ = "v2.2 (NotebookLM Optimized - Auto-Splitter)"

class PackerContract:
    """[v2.2] 邏輯契約：驗證打包任務的輸入完整性與輸出合規性。"""
    
    @staticmethod
    def validate_inputs(files: List[Path]) -> bool:
        """驗證輸入檔案是否存在且非空。"""
        if not files:
            print("   ❌ [Contract] Error: No input files found.")
            return False
        for f in files:
            if not f.exists():
                print(f"   ❌ [Contract] Error: File not found: {f}")
                return False
        return True

    @staticmethod
    def validate_output(output_path: Path, expected_min_size: int = 100) -> bool:
        """驗證輸出檔案是否成功建立且具備基本內容。"""
        if not output_path.exists():
            print(f"   ❌ [Contract] Error: Output file failed to create: {output_path}")
            return False
        if output_path.stat().st_size < expected_min_size:
            print(f"   ⚠️ [Contract] Warning: Output file is unusually small ({output_path.stat().st_size} bytes).")
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

def read_file_with_encoding(file_path: Path) -> Tuple[str, str]:
    """Read file with auto-detected encoding."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read(), "utf-8"
    except UnicodeDecodeError:
        pass

    if chardet_lib is not None:
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()
                detected = chardet_lib.detect(raw_data)["encoding"]
                if detected:
                    with open(file_path, "r", encoding=detected, errors="replace") as f:
                        return f.read(), detected
        except:
            pass

    return file_path.read_text(encoding='latin1', errors='replace'), "latin1"

def filter_zero_content(content: str) -> str:
    """Filter lines containing only zeros or invalid data."""
    lines = content.splitlines()
    filtered: List[str] = []
    zero_count = 0
    pattern = re.compile(r"^[0.,\s]+$")

    for line in lines:
        if not line.strip() or pattern.match(line.strip()):
            zero_count += 1
        else:
            if zero_count > 0:
                filtered.append(f"\n... [ 已省略 {zero_count} 行全零/無效數據 ] ...\n")
                zero_count = 0
            filtered.append(line)
    
    if zero_count > 0:
        filtered.append(f"\n... [ 已省略 {zero_count} 行全零/無效數據 ] ...\n")
    return "\n".join(filtered)

# ==============================================================================
# 📦 Core Packing Logic
# ==============================================================================

def process_and_save(files: List[Path], output_path: Path, args: argparse.Namespace) -> None:
    """[v2.2] Core logic with Character Counting and Auto-Splitting for NotebookLM."""
    # Step 1: Logic Contract Check (Input)
    if not PackerContract.validate_inputs(files):
        return

    max_chars = getattr(args, 'max_chars', 450000)
    parts: List[List[str]] = [[]]
    current_part_chars = 0
    total_chars = 0
    
    def add_header(p_idx: int) -> int:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        h = [
            "=" * 80,
            f"📦 DCS 檔案整合報告 ({__version__}) - PART {p_idx+1}",
            f"生成時間: {timestamp} | 檔案總數: {len(files)} | 字符限制: {max_chars}",
            "=" * 80 + "\n"
        ]
        header_text = "\n".join(h)
        parts[p_idx].append(header_text)
        return len(header_text)

    # Initialize first part
    current_part_chars = add_header(0)

    for idx, f_path in enumerate(files, 1):
        if f_path.stat().st_size == 0: continue
        
        content, encoding = read_file_with_encoding(f_path)
        if args.filter_zeros:
            content = filter_zero_content(content)
            
        if not content.strip() or ("[ 已省略" in content and len(content.strip().split("\n")) <= 2):
            continue

        file_header = [
            "#" * 80,
            f"### FILE {idx:02d}: {f_path.name} [{encoding}]",
            f"### Path: {f_path.absolute()}",
            "#" * 80 + "\n"
        ]
        header_str = "\n".join(file_header) + "\n"
        content_str = content + "\n"
        entry_str = header_str + content_str
        entry_len = len(entry_str)

        # Check for split
        if current_part_chars + entry_len > max_chars and len(parts[-1]) > 1:
            # Create new part
            parts.append([])
            current_part_chars = add_header(len(parts) - 1)
        
        parts[-1].append(entry_str)
        current_part_chars += entry_len
        total_chars += entry_len

    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save all parts
    for i, p_lines in enumerate(parts):
        suffix = f"_part{i+1}" if len(parts) > 1 else ""
        final_path = output_path.with_stem(f"{output_path.stem}{suffix}")
        final_content = "\n".join(p_lines)
        final_path.write_text(final_content, encoding="utf-8")
        
        # Step 2: Logic Contract Check (Output)
        if PackerContract.validate_output(final_path):
            print(f"✅ [Packer] Part {i+1} saved ({len(final_content)} chars): {final_path}")

    print(f"📊 [Summary] Total Assets: {len(files)} | Total Characters: {total_chars} | Parts: {len(parts)}")

def collect_files(
    input_paths: List[str], 
    recursive: bool = False, 
    include: Optional[List[str]] = None, 
    exclude: Optional[List[str]] = None, 
    whitelist_dir: Optional[str] = None
) -> List[Path]:
    """Collect relevant files based on filters."""
    all_files: List[Path] = []
    exts = [".md", ".txt", ".csv", ".json"]
    
    # Pre-load whitelist if provided
    whitelist_ids: Set[str] = set()
    if whitelist_dir:
        w_path = Path(whitelist_dir)
        if w_path.exists():
            for f in w_path.glob("**/*"):
                if f.is_file():
                    whitelist_ids.add(f.stem.lower().replace("_refined", "").replace("_core", ""))

    for p_str in input_paths:
        p = Path(p_str)
        if p.is_file():
            all_files.append(p)
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for f in p.glob(pattern):
                if f.suffix.lower() not in exts: continue
                if include and not any(fnmatch.fnmatch(f.name, pat) for pat in include): continue
                if exclude and any(fnmatch.fnmatch(f.name, pat) for pat in exclude): continue
                
                if whitelist_ids:
                    f_stem = f.stem.lower()
                    critical = ["ddcinst.txt", "tagref.txt", "vmd_vsrname.txt", "gmsdef.txt"]
                    if f.name.lower() not in critical and not any(wid in f_stem or f_stem in wid for wid in whitelist_ids):
                        continue
                all_files.append(f)
    
    return sorted(list(set(all_files)))

# ==============================================================================
# 🚀 Execution Modes
# ==============================================================================

def run_dcs_mode(args: argparse.Namespace) -> None:
    """Mode B: Automatic DCS Structure Packing."""
    project_root = Path(os.getcwd())
    output_dir = project_root / "00_Inbox" / "80_packed_report"
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Paths mapping
    paths = {
        "RAW": project_root / f"_assets/00_Raw/{args.client}/{args.site}/{args.plant}",
        "GID": project_root / f"_assets/05_GID/{args.client}/{args.site}/{args.plant}",
        "TWIN_CORE": project_root / f"_assets/30_Digital_Twin/core/{args.client}/{args.site}/{args.plant}",
        "TWIN_INDEX": project_root / f"_assets/30_Digital_Twin/index/{args.client}/{args.site}/{args.plant}"
    }

    print(f"🚀 [DCS Mode] Scanning assets for {args.plant}...")

    # Pack RAW (with GID whitelist)
    if paths["RAW"].exists() and paths["GID"].exists():
        files = collect_files([str(paths["RAW"])], recursive=True, whitelist_dir=str(paths["GID"]))
        if files:
            out = output_dir / f"packed_{args.plant}_RAW_{date_str}.txt"
            process_and_save(files, out, args)

    # Pack GID
    if paths["GID"].exists():
        files = collect_files([str(paths["GID"])], recursive=True)
        if files:
            out = output_dir / f"packed_{args.plant}_GID_{date_str}.txt"
            process_and_save(files, out, args)

    # Pack TWIN (Core + Index)
    twin_srcs = [str(paths["TWIN_CORE"]), str(paths["TWIN_INDEX"])]
    files = collect_files([s for s in twin_srcs if Path(s).exists()], recursive=True)
    if files:
        out = output_dir / f"packed_{args.plant}_TWIN_{date_str}.txt"
        process_and_save(files, out, args)

def run_generic_mode(args: argparse.Namespace) -> None:
    """Mode A: Generic Path-based Packing."""
    files = collect_files(args.input_paths, args.recursive, args.include, args.exclude, args.whitelist_dir)
    if not files:
        print("⚠️ 未找到符合條件的檔案。")
        return

    if args.output:
        out_path = Path(args.output)
    else:
        # Smart Naming Logic
        output_dir = Path("00_Inbox/80_packed_report")
        date_str = datetime.now().strftime("%Y%m%d")
        if len(args.input_paths) > 1:
            prefix = "GLOBAL_TAGS" if all("TAG" in p.upper() for p in args.input_paths) else "MULTI_SOURCES"
            out_path = output_dir / f"0_packed_{prefix}_{date_str}.txt"
        else:
            in_p = Path(args.input_paths[0])
            name = in_p.name.replace(" ", "_")
            out_path = output_dir / f"packed_{name}_{date_str}.txt"

    process_and_save(files, out_path, args)

# ==============================================================================
# 🏁 Main Entry
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=f"DCS Asset Packer {__version__}")
    
    # Common Flags
    parser.add_argument("--filter-zeros", action="store_true", help="過濾全零無效行")
    parser.add_argument("--handshake", action="store_true", help="執行技能快取同步")
    parser.add_argument("--max-chars", type=int, default=1500000, help="[v2.2] 單一檔案最大字數限制 (預設 1,500,000)")
    
    # Generic Mode Args
    parser.add_argument("input_paths", nargs="*", help="[通用模式] 輸入路徑")
    parser.add_argument("-o", "--output", help="[通用模式] 輸出路徑")
    parser.add_argument("-r", "--recursive", action="store_true", help="遞歸搜尋")
    parser.add_argument("-i", "--include", nargs="*", help="包含模式")
    parser.add_argument("-e", "--exclude", nargs="*", help="排除模式")
    parser.add_argument("--whitelist-dir", help="白名單參考目錄")

    # DCS Mode Args
    parser.add_argument("--site", help="[DCS 模式] 站點名稱 (如 Johor)")
    parser.add_argument("--plant", help="[DCS 模式] 單元名稱 (如 MLC02)")
    parser.add_argument("--client", default="RCMT", help="[DCS 模式] 客戶名稱")

    args = parser.parse_args()

    if args.site and args.plant:
        run_dcs_mode(args)
    elif args.input_paths:
        run_generic_mode(args)
    else:
        parser.print_help()
        sys.exit(1)

    if args.handshake:
        handshake()

if __name__ == "__main__":
    main()
