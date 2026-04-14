import re
import sys
import json
import argparse
import subprocess
from pathlib import Path

# ==========================================
# 🚀 Note Manager: Orchestrator (v17.6: Conditional Sync Optimization)
# ==========================================
# 職責：DCS 知識筆記總機，整合「物理還原」與「知識燃料供應」
# 語義：優化自動化煉金管線，實作條件式同步以消除 QA 雜訊 (v17.6)
# ==========================================

__version__ = "v17.6 (Conditional Sync Optimization)"

# 加入 src 目錄到路徑
sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from core_resolver import CoreResolver, _run_self_diagnostic as resolver_check # type: ignore
    from knowledge_injector import KnowledgeInjector, _run_self_diagnostic as injector_check # type: ignore
    from seq_engine import SeqMarkdownBuilder, _run_self_diagnostic as seq_check # type: ignore
    from ddc_engine import DdcMarkdownBuilder, _run_self_diagnostic as ddc_check # type: ignore
    from bls_engine import BlsMarkdownBuilder, _run_self_diagnostic as bls_check # type: ignore
except ImportError:
    from src.core_resolver import CoreResolver, _run_self_diagnostic as resolver_check # type: ignore
    from src.knowledge_injector import KnowledgeInjector, _run_self_diagnostic as injector_check # type: ignore
    from src.seq_engine import SeqMarkdownBuilder, _run_self_diagnostic as seq_check # type: ignore
    from src.ddc_engine import DdcMarkdownBuilder, _run_self_diagnostic as ddc_check # type: ignore
    from src.bls_engine import BlsMarkdownBuilder, _run_self_diagnostic as bls_check # type: ignore

class NoteManager:
    def __init__(self, client="RCMT", site="Johor", unit_id=None):
        self.resolver = CoreResolver(client=client, site=site, unit_id=unit_id)
        self.injector = KnowledgeInjector(self.resolver)
        self.seq_engine = SeqMarkdownBuilder(self.resolver)
        self.ddc_engine = DdcMarkdownBuilder(self.resolver)
        self.bls_engine = BlsMarkdownBuilder(self.resolver)

    def run_self_check(self):
        """Execute logic contract self-diagnostics for all components"""
        print(f"\n[Note Manager {__version__}] Starting Global Self-Diagnostic...")
        
        # Execute checks imported at top level
        resolver_check()
        ddc_check()
        seq_check()
        bls_check()
        injector_check()
        
        print(f"\n✨ [Global Check] All logical contracts verified successfully.\n")

    def run_action(self, args):
        if args.self_check:
            self.run_self_check()
            return

        active_unit = args.unit if args.unit else "MLC01"

        if args.action == "create-skeleton":
            # ==========================================
            # Smart Dispatcher: Choice the best engine
            # ==========================================
            if not args.loop: return
            loop_id = args.loop.upper()
            
            if loop_id.startswith("LP"):
                print(f"[Orchestrator] LP detected. Dispatching DDC Engine for {loop_id}...")
                self.ddc_engine.generate(loop_id)
            elif any(loop_id.startswith(p) for p in ["US", "MPN"]):
                print(f"[Orchestrator] SEQ detected. Dispatching SEQ Engine for {loop_id}...")
                self.seq_engine.generate(loop_id)
            elif loop_id.startswith("BL"):
                print(f"[Orchestrator] BL detected. Dispatching BLS Engine for {loop_id}...")
                self.bls_engine.generate(loop_id)
            else:
                # Generic Fallback: Create basic note via Core Data
                print(f"[Orchestrator] Generic tag detected. Creating basic skeleton for {loop_id}...")
                info = self.resolver.resolve_core_data(loop_id)
                kb_path = self.resolver.get_kb_file_path(loop_id, info['tag'])
                kb_path.parent.mkdir(parents=True, exist_ok=True)
                # Simple skeleton if no engine matches
                content = f"---\nloop_id: {loop_id}\ntype: {info['tag']}\nstatus: draft\n---\n\n# {loop_id}\n\n[AGENT] Basic data record."
                kb_path.write_text(content, encoding='utf-8')
            

        elif args.action == "auto-refine":
            if not args.loop: return
            loop_id = args.loop.upper()
            print(f"[Orchestrator] Starting AUTO-REFINE pipeline for {loop_id}...")
            
            # 1. Physical Restoration (Skeleton)
            if loop_id.startswith("LP"):
                print(f"   -> Dispatching DDC Engine...")
                self.ddc_engine.generate(loop_id)
            elif any(loop_id.startswith(p) for p in ["US", "MPN"]):
                print(f"   -> Dispatching SEQ Engine...")
                self.seq_engine.generate(loop_id)
            elif loop_id.startswith("BL"):
                print(f"   -> Dispatching BLS Engine...")
                if self.bls_engine.generate(loop_id):
                    # 優化 (v17.6)：偵測內容，若包含 [AGENT 補充] 則跳過初次同步
                    kb_file = self.resolver.get_kb_file_path(loop_id, "BLS")
                    if kb_file.exists() and "[AGENT 補充]" in kb_file.read_text(encoding='utf-8'):
                        print(f"   ℹ️ [Status] Skeleton created. Ready for Intelligence Injection (Sync skipped).")
                    else:
                        print(f"   -> [Auto Sync] Attempting sync_back_from_md for {loop_id}...")
                        if self.injector.sync_back_from_md(loop_id):
                            print(f"   ✅ [Auto Sync] sync_back 完成。")
            
            # 2. Agent Handshake & Intelligence Fueling (v16.7)
            info = self.resolver.resolve_core_data(loop_id)
            kb_path = self.resolver.get_kb_file_path(loop_id, info['tag'])
            rel_kb_path = kb_path.relative_to(self.resolver.base_dir)

            print(f"\n================================================================================")
            print(f"🚀 [AGENT_INTENT_REFINERY_TASK] (Phase: Analyze & Inject)")
            print(f"================================================================================")
            print(f"🔹 Target Loop  : {loop_id}")
            print(f"🔹 File Path    : {rel_kb_path}")
            print(f"🔹 Service Name : {info['summary']}")
            print(f"\n[DCS Context Fuel]:")
            fuel = {
                "previous_insight": info.get("previous_expert_insight", ""),
                "global_references": info.get("global_references", {}),
                "intelligence_report": info.get("intelligence_report", ""),
                "logic_spec": "spec-analyze-ddc.md" if loop_id.startswith("LP") else "spec-analyze-seq.md"
            }
            print(json.dumps(fuel, ensure_ascii=False, indent=2))
            
            print(f"\n[Action Directive]:")
            print(f"   1. READ physical data & OPEN {rel_kb_path}.")
            print(f"   2. INJECT high-quality engineering intent to [AGENT 補充] placeholders.")
            print(f"   3. FINISH by calling: python {sys.argv[0]} --action sync-back --loop {loop_id}")
            print(f"================================================================================\n")
            

        elif args.action == "sync-back":
            if not args.loop: return
            success = self.injector.sync_back_from_md(args.loop)
            if not success:
                print(f"🛑 [Abort] Sync failed for {args.loop}. Pipeline terminated.")
                sys.exit(1)

        elif args.action == "generate-large-seq":
            if not args.loop: return
            loop_id = args.loop.upper()
            print(f"🚀 [Orchestrator] Dispatching Engine for {loop_id}...")
            if self.seq_engine.generate(loop_id):
                info = self.resolver.resolve_core_data(loop_id)
                print(f"\n⛽ [Intelligence Fuel] Context for AGENT Injection:")
                fuel = {"loop_id": loop_id, "service_name": info["summary"], "raw_signals": list(info["signals"]), "governing_spec": "spec-analyze-seq.md"}
                print(json.dumps(fuel, ensure_ascii=False, indent=2))
                kb_path = self.resolver.get_kb_file_path(loop_id, info['tag'])
                print(f"\n👉 [MANDATORY NEXT STEP] Direct Edit: {kb_path.relative_to(self.resolver.base_dir)}")
    
        elif args.action == "generate-large-ddc":
            if not args.loop: return
            loop_id = args.loop.upper()
            print(f"[Orchestrator] Dispatching DDC Engine for {loop_id}...")
            
            if self.ddc_engine.generate(loop_id):
                # --- Intelligence Fuel Logic (Librarian Logic: v17) ---
                info = self.resolver.resolve_core_data(loop_id)
                
                print(f"\n[DDC Intelligence Fuel] Context for AGENT Analysis:")
                fuel = {
                    "loop_id": loop_id,
                    "service_name": info["summary"],
                    "previous_expert_insight": info.get("previous_expert_insight", ""),
                    "global_references": info.get("global_references", {}),
                    "mandatory_tasks": [
                        "1. Deep Search: Perform vector search for scan cycles and system-level limits.",
                        "2. BNO Decoding: Write engineering Intelligent Intent for each Fxx in the inventory table.",
                        "3. Chapter Completion: Write phased logic chain and linkage according to spec."
                    ],
                    "governing_spec": "spec-analyze-ddc.md"
                }
                print(json.dumps(fuel, ensure_ascii=False, indent=2))
                
                kb_path = self.resolver.get_kb_file_path(loop_id, info['tag'])
                print(f"\n[MANDATORY NEXT STEP] To complete the asset, AGENT must:")
                print(f"   1. PERFORM deep vector search for historical context.")
                print(f"   2. SURGICALLY EDIT: {kb_path.relative_to(self.resolver.base_dir)}")
                
    
        elif args.action == "sync-batch":
            # ==========================================
            # 🚜 Batch Knowledge Harvester (v16.2)
            # ==========================================
            unit_id = args.unit if args.unit else args.site
            if not unit_id:
                print("❌ [Batch] Please specify --unit or --site for batch sync.")
                return

            print(f"🚀 [Orchestrator] Starting Batch Back-Sync for {unit_id} (Pattern: {args.pattern if args.pattern else 'ALL'})...")
            
            # 定義搜尋根路徑
            kb_base = self.resolver.base_dir / "20_Knowledge_Base/1_Hitachi_EX-N01A/1_RCMT/Johor" / unit_id
            if not kb_base.exists():
                print(f"❌ [Batch] KB directory not found: {kb_base}")
                return

            md_files = list(kb_base.rglob("*.md"))
            
            success_count = 0
            fail_count = 0
            processed_files = []

            for md_path in md_files:
                # 1. 提取 ID
                match = re.match(r'^([A-Z]+\d+[A-Z]*S\d+)', md_path.name)
                if not match: continue
                loop_id = match.group(1)

                # 2. 模式過濾 (Pattern Filter)
                if args.pattern and args.pattern.upper() not in loop_id.upper():
                    continue
                
                processed_files.append(loop_id)
            
            print(f"   -> Filtered {len(processed_files)} assets for processing.")

            for loop_id in processed_files:
                print(f"\n🔄 [Processing] {loop_id}...")
                if self.injector.sync_back_from_md(loop_id):
                    success_count += 1
                else:
                    fail_count += 1
            
            print(f"\n✅ [Batch Complete] Summary for {unit_id}:")
            print(f"   🔹 Success: {success_count}")
            print(f"   🔹 Failed/Blocked: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Note Manager Orchestrator {__version__}")
    parser.add_argument("--action", choices=["create-skeleton", "update-summary", "pull-summary", "auto-refine", "generate-large-seq", "generate-large-ddc", "sync-back", "sync-batch"])
    parser.add_argument("--self-check", action="store_true", help="Run logical contract self-check")
    parser.add_argument("--client", default="RCMT", help="Client Name")
    parser.add_argument("--site", default="Johor", help="Site Location")
    parser.add_argument("--unit", help="Unit ID (e.g. MLC01)")
    parser.add_argument("--loop", help="Loop ID")
    parser.add_argument("--pattern", help="Loop ID pattern for batch sync (e.g. US, LP00)")
    parser.add_argument("--summary", help="Expert summary")
    parser.add_argument("--importance", help="Importance")
    parser.add_argument("--process", help="Process tags")
    parser.add_argument("--interlock", help="Interlock refs")
    parser.add_argument("--signals", help="Signal list")

    args = parser.parse_args()
    manager = NoteManager(
        client=args.client, 
        site=args.site, 
        unit_id=args.unit
    )
    manager.run_action(args)
