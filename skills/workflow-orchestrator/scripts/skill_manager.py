import os
import sys
import argparse
from pathlib import Path

# ==========================================
# 🏛️ Workflow Orchestrator CLI (v5.0)
# 職責：系統治理入口，調用 src/governance 執行核心邏輯。
# ==========================================

# 確保可以導入 src 下的模組
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
sys.path.append(str(SCRIPT_DIR.parent))

try:
    from src.governance import (
        sync_all_docs, 
        update_manifest_hashes, 
        update_skills_cache,
        load_system_manifest, 
        OrchestratorContract,
        PATHS,
        GEMINI_MD,
        TECH_STACK_MD,
        PROJECT_ROOT
    )
    import subprocess
    import platform
    import json
except ImportError as e:
    print(f"❌ [CLI] Import Error: {e}")
    sys.exit(1)

__version__ = "v5.0 (Modular Entry)"

# ==========================================
# 🔍 Legacy Audit Bridge (v7.0)
# ==========================================

def get_git_history(count: int = 5) -> str:
    try:
        cmd = ["git", "log", f"-n {count}", "--stat", "--pretty=format:---%ncommit: %h%ndate: %ad%nsubject: %s%nbody: %b", "--date=short"]
        return subprocess.check_output(cmd, encoding='utf-8', stderr=subprocess.DEVNULL).strip()
    except: return "No git history available."

def get_archived_track_context(days: int = 3) -> str:
    archive_dir = PROJECT_ROOT / "conductor" / "archive"
    if not archive_dir.exists(): return "No archive directory found."
    tracks = []
    try:
        all_archives = sorted([d for d in archive_dir.iterdir() if d.is_dir()], key=os.path.getmtime, reverse=True)[:days]
        for arch in all_archives:
            plan_file = arch / "plan.md"
            if plan_file.exists():
                lines = plan_file.read_text(encoding='utf-8').split('\n')[:10]
                tracks.append(f"📁 Track: {arch.name}\n" + "\n".join(lines) + f"\n{'-'*20}")
        return "\n".join(tracks) if tracks else "No archived plans found."
    except: return "Error reading archives."

def check_doc_integrity_alerts(manifest: dict):
    """[Mode B] Check for outdated SKILL.md and issue alerts."""
    alerts = []
    for sname, sdata in manifest.get("skills", {}).items():
        if sdata.get("doc_status") == "OUTDATED":
            alerts.append(f"   🚨 [Doc Integrity] {sname}/SKILL.md is outdated! (Code changed but doc hash remains same)")
        
        # 新增：元數據品質警報
        issues = sdata.get("metadata_issues", [])
        if issues:
            alerts.append(f"   ⚠️ [Metadata Skew] {sname} has incomplete metadata: {', '.join(issues)}")
    return alerts

# ==========================================
# 🛠️ Main Entry
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Workflow Orchestrator {__version__}")
    parser.add_argument("--sync-all", action="store_true", help="Sync all skills metadata and broadcast to global docs.")
    parser.add_argument("--update-cache", action="store_true", help="Update skills metadata cache and manifest descriptions.")
    parser.add_argument("--on-work-audit", action="store_true", help="Perform comprehensive on-work audit (Integrity + Git + Archive).")
    parser.add_argument("--off-work-audit", action="store_true", help="Perform off-work audit and sync.")
    parser.add_argument("--audit", action="store_true", help="Audit all component hashes and document integrity.")
    args = parser.parse_args()

    if not OrchestratorContract.validate_paths(PATHS):
        sys.exit(1)

    manifest = load_system_manifest()
    sys_ver = manifest.get("system_version", "8.2")

    if args.on_work_audit:
        update_skills_cache() # 新增：先執行元數據與殭屍偵測
        sync_all_docs() # 內部包含 update_manifest_hashes
        manifest = load_system_manifest() # 重新讀取含警報狀態的 manifest
        
        print("\n" + "="*80 + f"\n📋 Project Intelligence Brief (v{sys_ver})\n" + "="*80)
        print(f"OS: {sys.platform} | Architecture: Pipeline v{sys_ver}")
        
        # Mode B Alert Injection
        alerts = check_doc_integrity_alerts(manifest)
        if alerts:
            print("\n" + "!"*80 + "\n⚠️ CRITICAL GOVERNANCE ALERTS\n" + "!"*80)
            for a in alerts: print(a)
            
            # 針對殭屍技能提供物理建議
            zombies = [sname for sname, sdata in manifest.get("skills", {}).items() if "ZOMBIE_DIR_DETECTED" in sdata.get("metadata_issues", [])]
            if zombies:
                print("\n💡 ACTION REQUIRED:")
                for z in zombies:
                    print(f"   - Skill '{z}' is a ZOMBIE (no code/docs). Please `rm -rf .gemini/skills/{z}` or initialize it.")
            print("!"*80)

        print("\n" + "="*80 + "\n📜 Execution Provenance (Git History)\n" + "="*80)
        print(get_git_history(5))
        
        print("\n" + "="*80 + "\n📁 Recent Task Context (Archives)\n" + "="*80)
        print(get_archived_track_context(3))
        
        print(f"\n🌅 上班審計 v8.5 已完成。")
        sys.exit(0)

    if args.off_work_audit:
        sync_all_docs()
        print(f"\n🕒 下班收尾已完成。")
        sys.exit(0)

    if args.sync_all:
        sync_all_docs()
    elif args.update_cache:
        update_skills_cache()
    elif args.audit:
        update_manifest_hashes()
