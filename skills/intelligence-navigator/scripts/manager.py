# ==========================================
# 🏗️ Intelligence Navigator: Unified Gateway (v4.1: Cross-Platform Hardened)
# 職責：旗艦級入口點。整合語義索引、智慧搜尋、Omni-Vision 診斷與行為模擬。
# 變更：強化 Win32 路徑標準化與鎖定防護。
# ==========================================

import sys
import json
import argparse
from pathlib import Path

# ==========================================
# 🏗️ 環境初始化 (Win32 Path Compatibility)
# ==========================================
curr_dir = Path(__file__).resolve().parent
src_dir = (curr_dir.parent / "src").resolve()
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

def main():
    parser = argparse.ArgumentParser(description="🧠 Intelligence Navigator: Unified Gateway")
    parser.add_argument("--client", default=None, help="指定客戶名稱")
    parser.add_argument("--site", default=None, help="指定場區名稱")
    
    subparsers = parser.add_subparsers(dest="action", help="可用功能組")

    # 1. Index 子指令
    idx_parser = subparsers.add_parser("index", help="重建或更新語義索引 (ChromaDB)")
    idx_parser.add_argument("--source", type=str, help="指定索引來源路徑")
    idx_parser.add_argument("--reset", action="store_true", help="清空向量庫後重新索引")
    idx_parser.add_argument("--force", action="store_true", help="忽略 mtime 強制更新")

    search_parser = subparsers.add_parser("search", help="執行語義搜尋")
    search_parser.add_argument("--query", required=True, help="搜尋字串")

    consult_parser = subparsers.add_parser("consult", help="執行 RAG 專家診斷")
    consult_parser.add_argument("--topic", required=True, help="診斷主題")

    sim_parser = subparsers.add_parser("simulate", help="執行控制行為模擬")
    sim_parser.add_argument("--loop", required=True, help="Loop ID")
    
    drift_parser = subparsers.add_parser("drift", help="執行跨設備邏輯偏移偵測")
    drift_parser.add_argument("--keyword", required=True, help="偵測關鍵字")

    args = parser.parse_args()

    if args.action == "index":
        try:
            from index_engine import IndexManager
            # 路徑標準化處理
            source_path = str(Path(args.source).resolve()) if args.source else None
            
            manager = IndexManager(client=args.client, site=args.site)
            if args.reset:
                col_name = f"dcs_kb_{manager.resolver.site.lower()}"
                print(f"🗑️ 正在清空向量庫 (Collection: {col_name})...")
                try:
                    manager.client_db.delete_collection(name=col_name)
                except Exception as e:
                    print(f"ℹ️ 提示：Collection 不存在，無需刪除 ({e})")
                
                manager.collection = manager.client_db.get_or_create_collection(
                    name=col_name, embedding_function=manager.ef
                )
            
            manager.run_indexing(source_path=source_path, force=args.force or args.reset)
            print("✨ 索引任務執行完畢。")
        except Exception as e:
            print(f"🛑 索引任務異常中斷: {e}")
            sys.exit(1)

    elif args.action == "search":
        from intelligence_hub import IntelligenceHub
        hub = IntelligenceHub(client=args.client, site=args.site)
        data = hub.get_full_data(args.query)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.action == "consult":
        from expert_consultant import ExpertRAGManager
        manager = ExpertRAGManager(client=args.client, site=args.site)
        results = manager.execute_consult(args.topic)
        report = manager.build_insight_report(args.topic, results)
        print(report)

    elif args.action == "simulate":
        # 引用 behavior_simulator 的現有邏輯
        try:
            from behavior_orchestrator import DCSOrchestrator
            from physical_engine import PhysicalEngine
            from behavior_simulator import format_report
            
            engine = PhysicalEngine(client=args.client, site=args.site)
            loop_id = args.loop
            ddc_params = engine.get_loop_parameters(loop_id)
            
            # 自動掛載關聯 SEQ/BLS (保留現有腳本邏輯)
            orchestrator = DCSOrchestrator(ddc_params, {}, bls_data={})
            print(f"🧪 啟動行為模擬: {loop_id}...")
            results = orchestrator.run_batch_simulation(steps_to_simulate=3600)
            print(format_report(loop_id, ddc_params, results))
        except ImportError as e:
            print(f"🛑 模擬引擎載入失敗: {e}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
