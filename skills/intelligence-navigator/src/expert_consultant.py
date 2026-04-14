# ==========================================
# 🏗️ Omni-Vision 專家諮詢引擎 (v5.1: Federated Query Edition)
# 職責：整合戰略綜述、訊號 X 光與風險預判，達成 DCS 全貌診斷。
# 新增：聯邦查詢（自動合併 COMMON 全域手冊庫 + Site 場區庫）。
# ==========================================

"""
🧠 Intelligence Navigator: Expert Consultant (v5.0)
============================================================
美學：遵循 Aesthetic Hardening v3.0 規範。
核心：實施三位一體語義聚合 (Strategic/Relational/Audit)。
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dotenv import load_dotenv

# 導入統一路徑解析器與自定義 Embedding 函數
try:
    from .utils import NavigatorPathResolver, NavigatorStandardizer
    from .index_engine import GeminiEmbeddingFunction
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from utils import NavigatorPathResolver, NavigatorStandardizer
    from index_engine import GeminiEmbeddingFunction

# 版本資訊
__version__ = "v5.1 (Federated Query Edition)"

# ==========================================
# 🏗️ 核心邏輯: ExpertRAGManager
# ==========================================
class ExpertRAGManager:
    """負責全知檢索與專家診斷 (Orchestrator 模式)"""
    def __init__(self, client: Optional[str] = None, site: Optional[str] = None):
        self.resolver = NavigatorPathResolver(client=client, site=site)
        self.collection = None
        load_dotenv(self.resolver.project_root / "credentials" / ".env")
        self.api_key = os.getenv("Google_Generative_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        try:
            self.resolver.verify_db_exists()
            import chromadb
            db_path = Path(os.getenv("CHROMA_DB_PATH_OVERRIDE")) if os.getenv("CHROMA_DB_PATH_OVERRIDE") else self.resolver.get_db_path(create=False)
            self.chroma_client = chromadb.PersistentClient(path=str(db_path))
            self.ef = GeminiEmbeddingFunction(api_key=self.api_key) if self.api_key else None
            
            col_name = f"dcs_kb_{self.resolver.site.lower()}"
            try:
                # 優先嘗試獲取現有 Collection (不帶 EF 以避免衝突報錯)
                self.collection = self.chroma_client.get_collection(name=col_name)
                # 連結 EF
                self.collection._embedding_function = self.ef
            except Exception:
                # 失敗時才建立
                self.collection = self.chroma_client.get_or_create_collection(
                    name=col_name,
                    embedding_function=self.ef
                )
        except Exception as e: 
            self.init_error = str(e)
            print(f"⚠️ ExpertRAGManager 初始化異常: {e}", file=sys.stderr)

        # 聯邦架構：全域手冊庫連線 (COMMON DB)
        self.global_collection = None
        try:
            global_db_path = self.resolver.get_global_db_path(create=False)
            if global_db_path.exists() and (global_db_path / "chroma.sqlite3").exists():
                import chromadb
                global_chroma = chromadb.PersistentClient(path=str(global_db_path))
                try:
                    self.global_collection = global_chroma.get_collection(name="dcs_kb_common")
                    self.global_collection._embedding_function = self.ef
                    print(f"📚 全域手冊庫已連線 (COMMON DB)")
                except Exception:
                    pass  # COMMON DB 尚未建立
        except Exception:
            pass  # 全域庫不可用不影響場區查詢

    # ==========================================
    # 🏗️ 第一副眼鏡：訊號 X 光 (Relational)
    # ==========================================
    def _parse_intent(self, query: str) -> Dict[str, Any]:
        """解析 Query 意圖"""
        intent = {"loop_id": None, "unit": None, "signals": []}
        q_up = query.upper()
        all_tags = re.findall(r'\b([A-Z0-9\-_]{2,15})\b', q_up)
        for tag in all_tags:
            if re.match(r'^(?:LP|SEQ|BL|US|TIC|LIC)_?\d{2,4}', tag): intent["loop_id"] = tag
            elif re.match(r'^(?:MLC\d{2}|R-?\d{3,4}|UNIT\d{2})$', tag): intent["unit"] = tag
            elif re.match(r'^[A-Z]{2,3}\d{4}[A-Z]?$', tag): intent["signals"].append(tag)
        return intent

    def _recursive_signal_trace(self, primary_bundle: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """執行遞迴訊號追蹤，挖掘跨模組關聯"""
        discovered_signals = set()
        trace_results = []
        
        # 1. 從初次結果中提取物理標籤
        for item in primary_bundle:
            content = item.get("content", "")
            # 偵測 [SHIFT] 或 [ALWAYS] 區塊中的標籤
            tags = re.findall(r'\b([A-Z]{2}\d{4}[A-Z]?)\b', content)
            discovered_signals.update(tags)
        
        # 2. 限制追蹤數量以防過載
        target_signals = list(discovered_signals)[:3]
        if not target_signals: return []
        
        print(f"📡 [X-Ray] 偵測到關鍵訊號 {target_signals}，發起跨模組反向追蹤...")
        
        for sig in target_signals:
            # 執行精確過濾或語義搜尋該標籤
            res = self.collection.query(
                query_texts=[f"訊號 {sig} 的用途與聯動"],
                n_results=2
            )
            # 轉換為標準格式並標註為 [RELATIONAL]
            ids = res.get('ids')[0] if res.get('ids') else []
            metas = res.get('metadatas')[0] if res.get('metadatas') else []
            docs = res.get('documents')[0] if res.get('documents') else []
            for i in range(len(ids)):
                trace_results.append({
                    "id": ids[i],
                    "path": metas[i].get("path", "N/A"),
                    "content": f"[Relational Trace: {sig}]\n" + docs[i],
                    "metadata": metas[i],
                    "type": "relational"
                })
        return trace_results

    # ==========================================
    # 🏗️ 第二副眼鏡：風險預判 (Audit)
    # ==========================================
    def _audit_logic_integrity(self, semantic_content: str, physical_logic: str) -> Dict[str, Any]:
        """比對語義意圖與物理邏輯的對位度"""
        audit = {"risk_level": "LOW", "notes": []}
        
        # 範例規則：檢查聯鎖 (Interlock) 對位
        if "Interlock" in semantic_content.upper() and "[ALWAYS]" not in physical_logic:
            audit["risk_level"] = "MEDIUM"
            audit["notes"].append("筆記描述包含聯鎖，但物理 Core 中未發現 ALWAYS 邏輯。")
            
        return audit

    # ==========================================
    # 🏗️ 核心協調器 (The Orchestrator)
    # ==========================================
    def _bridge_to_physical_core(self, metadata: Dict[str, Any]) -> str:
        """物理數據穿透"""
        pointer = metadata.get("core_pointer")
        if not pointer: return ""
        full_path = self.resolver.project_root / pointer
        if not full_path.exists(): return ""
        try:
            data = json.loads(full_path.read_text(encoding="utf-8"))
            logic = []
            for ltype in ["shift", "always"]:
                for item in data.get(ltype, []):
                    expr = item.get("expression_semantic", item.get("expression", ""))
                    out = item.get("output_semantic", item.get("output", ""))
                    if expr: logic.append(f"[{ltype.upper()}] {out} = {expr}")
            return "\n[Physical Core Logic]\n" + "\n".join(logic[:8])
        except Exception: return ""

    def _run_sandbox_simulation(self, loop_id: str) -> Dict[str, Any]:
        """(Neuro-Symbolic) 執行背景沙盒模擬，提取動態推演事實"""
        try:
            from physical_engine import PhysicalEngine
            from behavior_orchestrator import DCSOrchestrator
            from behavior_simulator import format_report

            engine = PhysicalEngine(client=self.resolver.client, site=self.resolver.site)
            ddc_params = engine.get_loop_parameters(loop_id)
            if not ddc_params:
                return {}

            orchestrator = DCSOrchestrator(ddc_params, {}, bls_data={})
            print(f"🧪 [Neuro-Symbolic] 觸發背景時域推演: {loop_id} (3600 ticks)...")
            results = orchestrator.run_batch_simulation(steps_to_simulate=3600)
            
            sim_report = format_report(loop_id, ddc_params, results)
            return {
                "id": f"SIM_{loop_id}",
                "path": "Virtual_Sandbox",
                "content": f"[時域推演結果 (0~3600 Ticks)]\n{sim_report}",
                "type": "simulation"
            }
        except Exception as e:
            import sys
            print(f"⚠️ 背景模擬失敗: {e}", file=sys.stderr)
            return {}

    def execute_consult(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """執行 Omni-Vision 智慧檢索"""
        if not self.collection: return [{"id": "ERR", "path": "N/A", "content": "Offline", "type": "error"}]
        try:
            intent = self._parse_intent(query)
            all_ids = set(); primary_bundle = []
            
            # 1. 核心召回 (DDC/SEQ/BLS)
            if intent["loop_id"]:
                base = intent["loop_id"]
                candidates = [base, f"{base}S01", f"{base}S02", f"{base}S03", f"{base}S04"]
                res_p = self.collection.query(query_texts=[query], n_results=5, where={"loop_id": {"$in": candidates}})
                
                ids = res_p.get('ids')[0] if res_p.get('ids') else []
                docs = res_p.get('documents')[0] if res_p.get('documents') else []
                metas = res_p.get('metadatas')[0] if res_p.get('metadatas') else []
                for i in range(len(ids)):
                    if ids[i] in all_ids: continue
                    all_ids.add(ids[i])
                    m = metas[i]; c = docs[i]
                    phys = self._bridge_to_physical_core(m)
                    audit = self._audit_logic_integrity(c, phys)
                    primary_bundle.append({
                        "id": ids[i], "path": m.get("path", "N/A"), "content": c + phys, 
                        "metadata": m, "audit": audit, "type": "strategic"
                    })
            
            # 2. 補充語義召回 (通用搜尋)
            if len(primary_bundle) < 3:
                res_s = self.collection.query(query_texts=[query], n_results=5)
                ids = res_s.get('ids')[0] if res_s.get('ids') else []
                docs = res_s.get('documents')[0] if res_s.get('documents') else []
                metas = res_s.get('metadatas')[0] if res_s.get('metadatas') else []
                for i in range(len(ids)):
                    if ids[i] in all_ids: continue
                    all_ids.add(ids[i])
                    m = metas[i]; c = docs[i]
                    primary_bundle.append({
                        "id": ids[i], "path": m.get("path", "N/A"), "content": c, 
                        "metadata": m, "type": "semantic"
                    })

            # 3. 聯邦查詢：全域手冊庫 (COMMON DB)
            if self.global_collection:
                try:
                    res_g = self.global_collection.query(query_texts=[query], n_results=3)
                    g_ids = res_g.get('ids')[0] if res_g.get('ids') else []
                    g_docs = res_g.get('documents')[0] if res_g.get('documents') else []
                    g_metas = res_g.get('metadatas')[0] if res_g.get('metadatas') else []
                    for i in range(len(g_ids)):
                        if g_ids[i] in all_ids: continue
                        all_ids.add(g_ids[i])
                        primary_bundle.append({
                            "id": g_ids[i], "path": g_metas[i].get("path", "N/A"),
                            "content": f"[技術背書: Global Manual]\n" + g_docs[i],
                            "metadata": g_metas[i], "type": "global_manual"
                        })
                except Exception as e:
                    print(f"⚠️ 全域手冊庫查詢失敗: {e}", file=sys.stderr)

            # 4. 啟動 X-Ray 訊號追蹤 (Relational)
            trace_bundle = self._recursive_signal_trace(primary_bundle, query)
            
            # 5. [Neuro-Symbolic] 觸發背景時域推演
            if intent["loop_id"]:
                sim_res = self._run_sandbox_simulation(intent["loop_id"])
                if sim_res:
                    primary_bundle.append(sim_res)
            
            # 6. 合併結果
            final_bundle = primary_bundle + trace_bundle
            return final_bundle[:12]
        except Exception as e: 
            return [{"id": "ERR", "path": "ERROR", "content": str(e), "type": "error"}]

    # ==========================================
    # 🏗️ 第三副眼鏡：戰略綜述 (Synthesizer)
    # ==========================================
    def build_insight_report(self, query: str, bundle: List[Dict[str, Any]]) -> str:
        """產出 Omni-Vision 專家診斷報告"""
        if not bundle or "error" in bundle[0] or bundle[0].get("id") == "ERR":
            err_msg = bundle[0].get("content", "Unknown Error") if bundle else "No Data"
            return f"🛑 診斷中止：{err_msg}"
            
        if self.api_key:
            return self._build_gemini_synthesis(query, bundle)
        return self._build_template_report(query, bundle)

    def _build_gemini_synthesis(self, query: str, bundle: List[Dict[str, Any]]) -> str:
        """利用 Gemini 2.0 執行三位一體語義聚合"""
        from google import genai
        client = genai.Client(api_key=self.api_key)
        
        # 組裝燃料
        fuel = []
        for item in bundle:
            fuel.append(f"Source: {item['path']}\nType: {item.get('type')}\nContent: {item['content']}\nAudit: {item.get('audit')}\n---")
        
        prompt = f"""您是一位資深的 DCS 逆向工程師。請針對使用者的查詢與提供的多來源數據（包含語義筆記、物理邏輯、全域手冊與訊號追蹤結果），產出一份具備「戰略全貌感應」的診斷報告。

查詢主題：{query}

燃料數據：
{chr(10).join(fuel)}

要求：
1. [戰略定位]：總結此迴路或單元在場區中的核心角色。
2. [技術背書]：引用全域手冊 (Global Manual) 的定義，解釋「為什麼這麼設計」。
3. [物理一致性]：比對筆記意圖與代碼邏輯，指出是否有風險或漂移。
4. [動態實證]：若燃料中包含來源為 Virtual_Sandbox (`type: simulation`) 的時域推演結果，必須**強制**解讀該報表的起伏變化（如開關何時跳脫、斷線防護是否生效），用客觀實驗數據佐證你的推論！
5. [跨模組關聯]：根據訊號追蹤結果，說明此資產如何影響其他模組（SEQ/BLS）。
6. [診斷結論]：綜合靜態與動態觀察給出最終建議。
"""
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro", 
                contents=prompt
            )
            return f"\n# 🧠 Omni-Vision 專家診斷報告\n\n{response.text}"
        except Exception as e:
            return f"⚠️ Gemini 綜述失敗: {e}\n" + self._build_template_report(query, bundle)

    def _build_template_report(self, query: str, bundle: List[Dict[str, Any]]) -> str:
        """回退模式：範本報告"""
        report = f"\n# 🧠 Expert Insight (Fallback Mode): {query}\n"
        for item in bundle:
            m = item['metadata']
            report += f"### {m.get('loop_id', 'N/A')} [{item.get('type', 'Unknown')}]\n"
            report += f"- **路徑**: `{item['path']}`\n"
            report += f"{item['content'][:300]}...\n---\n"
        return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--site", default="Johor")
    args = parser.parse_args()
    manager = ExpertRAGManager(site=args.site)
    res = manager.execute_consult(args.query)
    print(manager.build_insight_report(args.query, res))
