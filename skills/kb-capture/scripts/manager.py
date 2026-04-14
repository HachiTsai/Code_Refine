import os
import sys
import argparse
from pathlib import Path

# 強制 UTF-8 輸出環境 (Win32 誠信防線)
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ==========================================
# 🏛️ Daily Log Manager CLI (v1.1)
# 職責：系統日誌收割門戶，引導 AGENT 進行「智慧提煉」並調用服務執行歸檔。
# ==========================================

# 確保可以導入 src 下的模組
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
sys.path.append(str(SCRIPT_DIR.parent))

try:
    from src.archiver import ArchiverService
except ImportError as e:
    # 暫時相容舊版，如果 ArchiverService 還沒建立
    print(f"⚠️ [CLI] ArchiverService not found, falling back to legacy mode: {e}", file=sys.stderr)
    ArchiverService = None

def check_synthesis_guidance(args):
    """[v1.1] 智慧引導：若非系統日誌且缺失 Metadata，輸出導引建議。"""
    if args.action == "capture" and args.type and args.type != "log":
        missing = []
        if not args.summary: missing.append("--summary")
        if not args.importance: missing.append("--importance")
        
        if missing:
            print("\n" + "="*60, file=sys.stderr)
            print("🛡️  [智慧提煉引導] 偵測到高品質資產收割意圖", file=sys.stderr)
            print("-"*60, file=sys.stderr)
            print(f"⚠️  警告：您正在收割 '{args.type}' 類型資產，但缺少參數: {', '.join(missing)}", file=sys.stderr)
            print(f"💡  建議：請先分析內容並產出摘要，隨後使用以下格式再次收割：", file=sys.stderr)
            print(f"    python {Path(__file__).name} --action capture --type {args.type} --topic \"{args.topic or '<topic>'}\" --summary \"<您的提煉>\" --importance \"<戰略評價>\"", file=sys.stderr)
            print("="*60 + "\n", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Daily Log Archiver & Knowledge Router")
    parser.add_argument("--action", choices=["capture", "audit"], default="capture")
    parser.add_argument("--type", help="Knowledge type (idea, knowhow, spec, etc.)")
    parser.add_argument("--topic", help="Topic for the captured note")
    parser.add_argument("--date", help="Custom date for filename (YYMMDD format)")
    parser.add_argument("--content", help="Direct content string to capture (bypasses AskGemini.md)", default=None)
    parser.add_argument("--summary", help="Automatic summary for YAML metadata", default=None)
    parser.add_argument("--importance", help="Automatic importance for YAML metadata", default=None)
    parser.add_argument("--positioning", help="Strategic positioning for YAML metadata", default=None)
    args = parser.parse_args()

    # 執行引導檢查
    check_synthesis_guidance(args)

    if ArchiverService:
        service = ArchiverService(project_root=PROJECT_ROOT)
        if args.action == "capture":
            service.run_capture(
                k_type=args.type, 
                topic=args.topic, 
                content=args.content, 
                custom_date=args.date,
                summary=args.summary,
                importance=args.importance,
                strategic_positioning=args.positioning
            )
    else:
        # Legacy fallback logic (calling existing archiver.py via subprocess)
        legacy_script = SCRIPT_DIR.parent / "src" / "archiver.py"
        cmd = [sys.executable, str(legacy_script)]
        if args.type: cmd.extend(["--type", args.type])
        if args.topic: cmd.extend(["--topic", args.topic])
        import subprocess
        subprocess.run(cmd)

if __name__ == "__main__":
    main()
