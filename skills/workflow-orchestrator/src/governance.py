import os
import sys
import json
import hashlib
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Tuple

# ==========================================
# 🏗️ Governance Core (v1.2: Environment-Aware & Tool-Hardened)
# 職責：處理系統 Manifest、環境感知偵測、誠信審計與文檔同步。
# ==========================================

class OrchestratorContract:
    """[v3.2] 邏輯契約：驗證系統誠信對齊、環境感知與工具路徑鎖定。"""
    
    @staticmethod
    def detect_environment() -> Dict[str, str]:
        """偵測當前執行環境 (myenv-windows vs myenv-mac)。"""
        conda_env = os.environ.get("CONDA_DEFAULT_ENV", "unknown")
        os_platform = sys.platform
        
        env_info = {
            "platform": os_platform,
            "conda_env": conda_env,
            "harden_mode": "STANDARD"
        }
        
        if os_platform == "win32" or conda_env == "myenv-windows":
            env_info["harden_mode"] = "WIN32_TOOL_FIRST"
        elif conda_env == "myenv-mac":
            env_info["harden_mode"] = "DARWIN_OPTIMIZED"
            
        return env_info

    @staticmethod
    def get_tool_protocol(env_info: Dict[str, str]) -> Dict[str, str]:
        """根據環境返回對應的工具使用協定。"""
        if env_info["harden_mode"] == "WIN32_TOOL_FIRST":
            return {
                "read": "GEMINI_READ_FILE (UTF-8 Mandatory)",
                "search": "GEMINI_GREP_SEARCH (Regex)",
                "modify": "GEMINI_REPLACE / WRITE_FILE",
                "shell": "PowerShell / CMD"
            }
        return {
            "read": "Standard Posix / Gemini Tools",
            "search": "Grep / Gemini Search",
            "modify": "Sed / Gemini Replace",
            "shell": "Zsh / Bash"
        }
    
    @staticmethod
    def calculate_hash(file_path: Path) -> str:
        """計算檔案的 SHA-256 雜湊 (8位短雜湊)。"""
        if not file_path.exists(): return "file_missing"
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()[:8]
        except Exception as e:
            return f"error:{str(e)}"

    @staticmethod
    def validate_paths(paths: Dict[str, Path]) -> bool:
        """驗證關鍵路徑是否存在。"""
        critical = ["PROJECT_ROOT", "SKILLS_DIR", "MANIFEST_FILE"]
        for key in critical:
            if not paths[key].exists():
                print(f"   ❌ [Contract] Error: Critical path missing: {key} -> {paths[key]}")
                return False
        return True

    @staticmethod
    def diagnose_metadata(metadata: Dict[str, Any]) -> List[str]:
        """診斷技能元數據是否具備實質意義。"""
        issues = []
        if metadata.get("description") == "No description":
            issues.append("MISSING_DESCRIPTION")
        if metadata.get("version") == "unknown":
            issues.append("MISSING_VERSION")
        if metadata.get("status") == "ZOMBIE":
            issues.append("ZOMBIE_DIR_DETECTED")
        return issues

# ==========================================
# 🗺️ Path Configuration (SSoT)
# ==========================================
SRC_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SRC_DIR.parent
PROJECT_ROOT = SKILL_ROOT.parents[2]
SKILLS_DIR = PROJECT_ROOT / ".gemini" / "skills"
MANIFEST_FILE = PROJECT_ROOT / "conductor" / "system_manifest.json"
CACHE_FILE = SKILL_ROOT / "assets" / "skills_cache.json"

# Documentation Targets
CONDUCTOR_INDEX = PROJECT_ROOT / "conductor" / "index.md"
TECH_STACK_MD = PROJECT_ROOT / "conductor" / "tech-stack.md"
README_MD = PROJECT_ROOT / "README.md"
GEMINI_MD = PROJECT_ROOT / "GEMINI.md"

PATHS = {
    "PROJECT_ROOT": PROJECT_ROOT,
    "SKILLS_DIR": SKILLS_DIR,
    "MANIFEST_FILE": MANIFEST_FILE
}

# ==========================================
# 🧠 Manifest & Logic Core
# ==========================================

def load_system_manifest() -> Dict[str, Any]:
    if not MANIFEST_FILE.exists(): return {"system_version": "8.2"}
    try:
        return json.loads(MANIFEST_FILE.read_text(encoding='utf-8'))
    except: return {"system_version": "8.2"}

def save_system_manifest(manifest: Dict[str, Any]) -> None:
    manifest["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

def update_manifest_hashes() -> None:
    """[v3.1] Audit all skill components and document integrity."""
    manifest = load_system_manifest()
    skills = manifest.get("skills", {})
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"🔍 [Integrity] Auditing skill components & documents...")
    changes_detected = False
    
    for skill_name, sdata in skills.items():
        skill_path = SKILLS_DIR / skill_name
        if not skill_path.exists(): continue
            
        # 1. Component Audit (v1.2: Support List-to-Dict Auto-Conversion)
        components = sdata.get("components", {})
        code_changed = False
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 實作自動格式升級 (Legacy List -> Dict with Hash)
        if isinstance(components, list):
            print(f"   🔄 [Integrity] Upgrading '{skill_name}' from Legacy List to Hash Dict...")
            new_components = {}
            for comp_rel_path in components:
                full_path = skill_path / comp_rel_path
                new_components[comp_rel_path] = {
                    "hash": OrchestratorContract.calculate_hash(full_path),
                    "last_audit": today_str
                }
            sdata["components"] = new_components
            components = new_components
            changes_detected = True
            code_changed = True

        # 標準雜湊更新與誠信校驗
        if isinstance(components, dict):
            for comp_rel_path, cdata in components.items():
                full_path = skill_path / comp_rel_path
                current_hash = OrchestratorContract.calculate_hash(full_path)
                if current_hash != cdata.get("hash"):
                    cdata["hash"] = current_hash
                    cdata["last_audit"] = today_str
                    changes_detected = True
                    code_changed = True
        
        # 2. Document Audit (SKILL.md)
        doc_file = skill_path / "SKILL.md"
        doc_hash = OrchestratorContract.calculate_hash(doc_file)
        old_doc_hash = sdata.get("doc_hash")
        
        # Mode B Logic: Detect Skew
        if code_changed and doc_hash == old_doc_hash:
            sdata["doc_status"] = "OUTDATED"
            changes_detected = True
        elif doc_hash != old_doc_hash:
            sdata["doc_hash"] = doc_hash
            sdata["doc_status"] = "OK"
            changes_detected = True
        
        if not sdata.get("doc_status"): sdata["doc_status"] = "OK"

    if changes_detected:
        save_system_manifest(manifest)
        print(f"✅ [Integrity] system_manifest.json updated.")
    else:
        print(f"🆗 [Integrity] All consistent.")

# ==========================================
# 📡 SSoT Sync Logic
# ==========================================

def get_skill_metadata(skill_dir: Path) -> Dict[str, Any]:
    skill_file = skill_dir / "SKILL.md"
    src_dir = skill_dir / "src"
    scripts_dir = skill_dir / "scripts"
    
    # 物理偵測：若無核心資產，判定為 ZOMBIE
    has_core_assets = skill_file.exists() or src_dir.exists() or scripts_dir.exists()
    
    metadata = {
        "name": skill_dir.name, 
        "description": "No description", 
        "version": "unknown", 
        "active": False, 
        "last_modified": "unknown", 
        "category": "🛠️ 工具",
        "status": "OK" if has_core_assets else "ZOMBIE"
    }
    
    if skill_file.exists():
        mtime = os.path.getmtime(skill_file)
        metadata["last_modified"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        content = skill_file.read_text(encoding='utf-8')
        v_match = re.search(r'version:\s*["\']?\s*(v?[\d\.]+[​\w\.\-]*)\s*["\']?', content)

        if v_match: metadata["version"] = v_match.group(1).lower()
        d_match = re.search(r'description:\s*["\\]?(.+?)["\\]?\s*$', content, re.M)
        if d_match: metadata["description"] = d_match.group(1).strip()
        
        name = skill_dir.name.lower()
        if any(x in name for x in ["orchestrator", "guardian", "sentinel"]): metadata["category"] = "🏛️ 系統"
        elif any(x in name for x in ["engine", "core"]): metadata["category"] = "🧪 核心"
        elif any(x in name for x in ["workflow", "pipeline", "navigator"]): metadata["category"] = "🚀 流程"
        metadata["active"] = True
    elif has_core_assets:
        # 有代碼但無 SKILL.md 的情況，標記為 Active 但可能 metadata 缺失
        metadata["active"] = True
        
    return metadata

def generate_markdown_table(skills: Dict[str, Any], target_type: str = "display") -> str:
    """Generate Markdown tables for docs."""
    if target_type == "governance":
        table = "| 技能名稱 | 目前版本 | 最後維護日 | 同步狀態 | 核心分類 | 治理連結 |\n"
        table += "| :--- | :---: | :---: | :---: | :---: | :--- |\n"
        for name, meta in sorted(skills.items()):
            sync_status = "🟢 已同步" if meta["active"] else "🔴 異常"
            governance_link = f"[[{name}/SKILL.md|查看詳情]]"
            table += f"| `{name}` | `{meta['version']}` | {meta['last_modified']} | {sync_status} | {meta['category']} | {governance_link} |\n"
    else:
        table = "| 技能名稱 | 版本 | 最後維護 | 職責說明 | 類別 |\n"
        table += "| :--- | :---: | :---: | :--- | :---: |\n"
        for name, meta in sorted(skills.items()):
            table += f"| `{name}` | `{meta['version']}` | {meta['last_modified']} | {meta['description']} | {meta['category']} |\n"
    return table

def update_skills_cache() -> None:
    """[v5.1] 更新技能元數據快取，並執行品質診斷 (Quality Gate)。"""
    print(f"🔄 [Registry] Updating skills metadata cache & Quality Audit...")
    manifest = load_system_manifest()
    skills_manifest = manifest.get("skills", {})
    
    cache_data = {}
    changes_detected = False
    
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith(('.', '_')):
            metadata = get_skill_metadata(item)
            issues = OrchestratorContract.diagnose_metadata(metadata)
            metadata["issues"] = issues
            cache_data[item.name] = metadata
            
            # 同步回 Manifest 的描述性欄位
            if item.name in skills_manifest:
                sdata = skills_manifest[item.name]
                # 強制更新 Issues 狀態
                if sdata.get("metadata_issues") != issues:
                    sdata["metadata_issues"] = issues
                    changes_detected = True
                
                if sdata.get("version") != metadata["version"] or sdata.get("description") != metadata["description"]:
                    sdata["version"] = metadata["version"]
                    sdata["description"] = metadata["description"]
                    changes_detected = True
            else:
                # 若 Manifest 遺漏此技能，自動補上基礎結構
                skills_manifest[item.name] = {
                    "version": metadata["version"],
                    "description": metadata["description"],
                    "components": {},
                    "doc_status": "UNKNOWN",
                    "metadata_issues": issues
                }
                changes_detected = True

    # 寫入快取檔案
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    if changes_detected:
        manifest["skills"] = skills_manifest
        save_system_manifest(manifest)
        print(f"✅ [Registry] Metadata synced to system_manifest.json.")
    
    print(f"🆗 [Registry] Cache updated: {len(cache_data)} skills registered.")

def sync_all_docs() -> None:
    update_manifest_hashes()
    manifest = load_system_manifest()
    sys_ver = manifest.get("system_version", "8.2")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Refresh cache for tables
    cache_data = {}
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith(('.', '_')):
            cache_data[item.name] = get_skill_metadata(item)
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding='utf-8')

    anchor_start = "<!-- SKILL_MATRIX_START -->"
    anchor_end = "<!-- SKILL_MATRIX_END -->"
    targets = [(CONDUCTOR_INDEX, "display"), (TECH_STACK_MD, "display"), (README_MD, "display"), (GEMINI_MD, "display")]
    
    print(f"📡 [Orchestrator] Global Sync v{sys_ver}...")
    for target_path, target_type in targets:
        if not target_path.exists(): continue
        content = target_path.read_text(encoding="utf-8")
        if anchor_start in content and anchor_end in content:
            table_content = generate_markdown_table(cache_data, target_type=target_type)
            content = re.sub(f"{re.escape(anchor_start)}.*?{re.escape(anchor_end)}", 
                             f"{anchor_start}\n\n{table_content}\n{anchor_end}", content, flags=re.DOTALL)
        content = re.sub(r'System Version:\s*[\d\.]+', f'System Version: {sys_ver}', content)
        content = re.sub(r'Conductor System v\s*[\d\.]+', f'Conductor System v{sys_ver}', content)
        content = re.sub(r'\*Last Updated:.*?\*', f'*Last Updated: {today_str} | Conductor System v{sys_ver}*', content)
        target_path.write_text(content, encoding="utf-8")
