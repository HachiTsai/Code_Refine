# ==========================================
# 🏗️ 智慧導航索引引擎 (v5.3: Dynamic Path & Empty-Chunk Guard)
# 職責：ChromaDB 語義索引維護、增量更新、語義感應切割與元數據深度萃取。
# 新增：COMMON 模式（僅索引 Manual）、場區隔離過濾修正、空 Chunk 防護。
# ==========================================

"""
🧠 Intelligence Navigator: Index Engine
============================================================
美學：遵循 Aesthetic Hardening v3.0 規範。
核心：實施語義感應切割 (Semantic-Aware Chunking) 與元數據治理。
"""

import os
import sys
import glob
import time
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, cast, Union, Tuple
from dotenv import load_dotenv

try:
    import chromadb
    from chromadb.utils import embedding_functions
    from google import genai
except ImportError:
    print("\n[⚠️ 環境錯誤] 請執行： pip install chromadb google-genai python-dotenv", file=sys.stderr)
    sys.exit(1)

# 導入統一路徑解析器
try:
    from .utils import NavigatorPathResolver, NavigatorStandardizer
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from utils import NavigatorPathResolver, NavigatorStandardizer

# 載入環境變數
_temp_resolver = NavigatorPathResolver()
_root = _temp_resolver.project_root
load_dotenv(_root / "credentials" / ".env")
load_dotenv(_root / ".env")
load_dotenv()

# 版本資訊
__version__ = "v5.3 (Dynamic Path & Empty-Chunk Guard)"

# ==========================================
# 🏗️ Embedding 函數定義 (Custom Google SDK)
# 職責：封裝 Gemini Embedding 2 Preview 接口與 Batch 處理。
# ==========================================
class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """自定義 Gemini Embedding 實作 (支援分段 Batch 處理)"""
    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-2-preview"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        # Gemini Embedding API 安全限制：截斷超長文檔 (~2048 tokens ≈ 8000 chars)
        MAX_CHARS = 8000
        safe_input = [doc[:MAX_CHARS] if doc else " " for doc in input]
        
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(safe_input), batch_size):
            batch = safe_input[i : i + batch_size]
            result = self.client.models.embed_content(
                model=self.model_name,
                contents=batch,
                config={"task_type": "RETRIEVAL_DOCUMENT"}
            )
            all_embeddings.extend([e.values for e in result.embeddings])
            
        return all_embeddings

# ==========================================
# 🏗️ 核心索引管理器: IndexManager
# 職責：負責 ChromaDB 索引生命週期管理與報告產出。
# ==========================================
class IndexManager:
    """負責 ChromaDB 索引生命週期管理 (具備語義全貌感應能力)"""
    def __init__(self, client: Optional[str] = None, site: Optional[str] = None):
        self.resolver = NavigatorPathResolver(client=client, site=site)
        self.resolver.verify_context_exists()
        
        api_key = os.getenv("Google_Generative_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.ef = None
        if api_key:
            print(f"💡 偵測到 Google API Key，啟用 Gemini Embedding (v2-preview)")
            try:
                self.ef = GeminiEmbeddingFunction(api_key=api_key)
            except Exception as e:
                print(f"⚠️ Gemini 初始化失敗: {e}，將回退至本地模型")
                self.ef = None
        
        # 測試環境支持 + 聯邦路徑選擇
        if os.getenv("CHROMA_DB_PATH_OVERRIDE"):
            self.db_path = Path(os.getenv("CHROMA_DB_PATH_OVERRIDE"))
        elif self.resolver.site.upper() == "COMMON":
            self.db_path = self.resolver.get_global_db_path()
        else:
            self.db_path = self.resolver.get_db_path()
        print(f"📦 ChromaDB 實體路徑: {self.db_path}")
        
        self.client_db = chromadb.PersistentClient(path=str(self.db_path))
        
        col_name = f"dcs_kb_{self.resolver.site.lower()}"
        try:
            # 優先嘗試獲取現有 Collection (不帶 EF 以避免衝突報錯)
            self.collection = self.client_db.get_collection(name=col_name)
            # 成功獲取後，如果 EF 不同，Chromadb 在 upsert 時會處理，但我們在此處重新連結 EF
            self.collection._embedding_function = self.ef
        except Exception:
            # 失敗時才建立
            self.collection = self.client_db.get_or_create_collection(
                name=col_name,
                embedding_function=self.ef
            )

    # ==========================================
    # 🏗️ 索引管線邏輯 (Pipeline)
    # ==========================================
    def run_indexing(self, source_path: Optional[str] = None, force: bool = False) -> None:
        """執行增量索引管線 (v5.1: 加入語義全貌注入)"""
        print(f"\n🧠 啟動語義索引管線 (v{__version__})...")
        print(f"📍 目標場區: {self.resolver.client}/{self.resolver.site}")
        
        core_search_path = self.resolver.core_base
        
        files_to_index = []
        if source_path:
            p = Path(source_path).resolve()
            if p.is_file(): files_to_index.append(p)
            else: files_to_index.extend(list(p.rglob("*.md")) + list(p.rglob("*_core.json")))
        else:
            # 聯邦路徑分流：COMMON 只掃 Manual，Site 只掃場區筆記 + core.json
            if self.resolver.site.upper() == "COMMON":
                scan_root = self.resolver.manual_base
                files_to_index.extend(list(scan_root.rglob("*.md")))
                print(f"📚 [COMMON 模式] 掃描範圍: {scan_root}")
            else:
                scan_root = self.resolver.site_base
                files_to_index.extend(list(scan_root.rglob("*.md")))
                files_to_index.extend(list(core_search_path.rglob("*_core.json")))
                print(f"🏭 [Site 模式] 掃描範圍: {scan_root}")

        print(f"🔍 掃描完成。待處理資產總數: {len(files_to_index)}")
        
        stats = {"indexed": [], "skipped": [], "failed": []}
        
        for f in files_to_index:
            # Win32 Hardening: 確保 file_id_base 永遠使用正斜線
            file_id_base = str(f.relative_to(self.resolver.project_root)).replace("\\", "/")
            mtime = os.path.getmtime(f)
            
            # 場區隔離檢查 (僅 Site 模式需要，COMMON 模式已在掃描階段限縮範圍)
            if self.resolver.site.upper() != "COMMON":
                site_key = f"/{self.resolver.site}/".lower()
                if site_key not in file_id_base.lower():
                    stats["skipped"].append({"path": file_id_base, "reason": "場區隔離"})
                    continue

            # 增量檢查
            existing = self.collection.get(ids=[f"{file_id_base}#chunk_0"])
            if not force and existing and existing.get('ids') and existing.get('metadatas'):
                meta_list = existing['metadatas']
                if meta_list and meta_list[0].get('mtime') == mtime:
                    stats["skipped"].append({"path": file_id_base, "reason": "mtime 未變"})
                    if len(stats["skipped"]) % 100 == 0:
                        print(f"   [Verified] {len(stats['skipped'])} assets matched (Incremental skip)...")
                    continue
            
            print(f"   🚀 [Indexing] {file_id_base} (New or Modified)")
            try:
                contents, base_metadata = self._parse_file(f)
                # 空值防護：過濾空白 Chunk 避免 Embedding 維度不一致
                contents = [c for c in contents if c and c.strip()]
                if not contents:
                    stats["failed"].append({"path": file_id_base, "reason": "內容解析為空"})
                    continue

                try:
                    self.collection.delete(where={"path": file_id_base})
                except Exception: pass

                ids = []; docs = []; metas = []
                for i, chunk_content in enumerate(contents):
                    chunk_id = f"{file_id_base}#chunk_{i}"
                    chunk_meta = base_metadata.copy()
                    chunk_meta.update({
                        "mtime": mtime,
                        "path": file_id_base,
                        "chunk_index": i,
                        "total_chunks": len(contents)
                    })
                    ids.append(chunk_id); docs.append(chunk_content); metas.append(chunk_meta)
                
                # 批次 upsert，失敗時降級為逐筆處理
                try:
                    self.collection.upsert(ids=ids, documents=docs, metadatas=metas)
                except Exception as batch_err:
                    if "Inconsistent" in str(batch_err):
                        print(f"   ⚠️ [Fallback] 批次失敗，改為逐筆處理: {file_id_base}")
                        for j in range(len(ids)):
                            try:
                                self.collection.upsert(ids=[ids[j]], documents=[docs[j]], metadatas=[metas[j]])
                            except Exception:
                                pass  # 個別 chunk 失敗不影響整體
                    else:
                        raise batch_err
                stats["indexed"].append({"path": file_id_base, "chunks": len(contents)})
                
                if len(stats["indexed"]) % 50 == 0:
                    print(f"   -> 已處理 {len(stats['indexed'])} 份資產...")
            except Exception as e:
                stats["failed"].append({"path": file_id_base, "reason": str(e)})

        self._generate_insight_report(stats)
        print(f"✅ 索引同步完成！")

    # ==========================================
    # 🏗️ 語義解析與切塊 (Parsing & Chunking)
    # ==========================================
    def _parse_file(self, file_path: Path) -> Tuple[List[str], Dict[str, Any]]:
        try:
            if file_path.suffix == ".md":
                content, meta, global_ctx = self._parse_md(file_path)
                chunks = self._chunk_text(content)
                if global_ctx:
                    chunks = [f"{global_ctx}\n---\n{c}" for c in chunks]
                return chunks, meta
            elif file_path.suffix == ".json":
                content, meta = self._parse_json(file_path)
                return [content], meta
        except Exception as e: print(f"⚠️ 解析失敗 {file_path.name}: {e}")
        return [], {}

    def _parse_md(self, file_path: Path) -> Tuple[str, Dict[str, Any], str]:
        """[v5.1] 強化版 Markdown 解析器：萃取 YAML 與 Facts"""
        content = file_path.read_text(encoding='utf-8')
        metadata = {"type": "markdown", "loop_id": "", "unit": "", "site": self.resolver.site, "service_name": ""}
        
        # 萃取 YAML
        yaml_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if yaml_match:
            for line in yaml_match.group(1).split('\n'):
                if ':' in line:
                    p = line.split(':', 1)
                    k, v = p[0].strip().lower(), p[1].strip().strip('"').strip("'")
                    if k in metadata: metadata[k] = v

        # 萃取 DCS Facts
        global_context = ""
        facts_match = re.search(r'%% DCS_FACTS_START %%.*?Summary::\s*(.*?)\n.*?Importance::\s*(.*?)\n%% DCS_FACTS_END %%', content, re.DOTALL)
        if facts_match:
            s, i = facts_match.groups()
            global_context = f"[Summary] {s.strip()} [Importance] {i.strip()}"
            metadata["summary_snippet"] = s.strip()[:100]

        # 自動對位實體路徑
        if metadata["loop_id"] and metadata["unit"]:
            site = metadata.get("site") or self.resolver.site
            metadata["core_pointer"] = f"_assets/30_Digital_Twin/core/{site}/{metadata['unit']}/{metadata['loop_id']}.json"

        clean_content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        if not metadata["loop_id"]:
            m = re.search(r'loop_id:\s*(\S+)', content)
            if m: metadata["loop_id"] = m.group(1)

        return clean_content, metadata, global_context

    def _parse_json(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """[v5.1] Core JSON 解析：萃取邏輯片段與元數據"""
        data = json.loads(file_path.read_text(encoding='utf-8'))
        meta = data.get("metadata", {})
        loop_id = meta.get("id", file_path.stem.replace("_core", ""))
        logic_fragments = []
        for ltype in ["shift", "always", "correction"]:
            for item in data.get(ltype, []):
                expr = item.get("expression_semantic", item.get("expression", ""))
                out = item.get("output_semantic", item.get("output", ""))
                if expr: logic_fragments.append(f"[{ltype.upper()}] {out} = {expr}")
        
        flattened_text = f"Loop: {loop_id}\nService: {meta.get('SERVICE', '')}\nSummary: {meta.get('summary', '')}\nImportance: {meta.get('importance', '')}\nLogic:\n" + "\n".join(logic_fragments)
        return flattened_text, {"type": "core_json", "loop_id": loop_id, "unit": meta.get("unit", ""), "service_name": meta.get('SERVICE', '')}

    def _chunk_text(self, text: str, chunk_size: int = 1500) -> List[str]:
        """[v5.1] 代理方法：執行語義感應切割"""
        return self._semantic_chunker(text, max_chunk_size=chunk_size)

    def _semantic_chunker(self, text: str, max_chunk_size: int = 1500) -> List[str]:
        """[v5.1] 語義感知切割器：保護標題與表格"""
        if len(text) <= max_chunk_size: return [text.strip()]
        sections = re.split(r'(\n##\s+)', text)
        final_chunks = []; current_chunk = ""
        for section in sections:
            if len(current_chunk) + len(section) > (max_chunk_size + 500):
                if current_chunk: final_chunks.append(current_chunk.strip()); current_chunk = ""
                if len(section) > max_chunk_size: final_chunks.extend(self._table_aware_sub_chunk(section, max_chunk_size))
                else: current_chunk = section
            else:
                current_chunk += section
        if current_chunk: final_chunks.append(current_chunk.strip())
        return [c for c in final_chunks if c]

    def _table_aware_sub_chunk(self, text: str, limit: int) -> List[str]:
        """表格感知子切割：優先在表格邊界切斷"""
        table_matches = list(re.finditer(r'(\n\|.*\n\|.*\n(?:\|.*\n)*)', text, re.DOTALL))
        if not table_matches: return self._sub_chunk_logic(text, limit)
        chunks = []; last_idx = 0
        for m in table_matches:
            start, end = m.span()
            if start > last_idx: chunks.extend(self._sub_chunk_logic(text[last_idx:start], limit))
            chunks.append(text[start:end].strip())
            last_idx = end
        if last_idx < len(text): chunks.extend(self._sub_chunk_logic(text[last_idx:], limit))
        return chunks

    def _sub_chunk_logic(self, text: str, limit: int) -> List[str]:
        """降級物理切割邏輯"""
        chunks = []; start = 0
        while start < len(text):
            end = start + limit
            if end >= len(text): chunks.append(text[start:]); break
            boundary = text.rfind("\n\n", start, end)
            if boundary != -1 and boundary > start + (limit // 3): end = boundary + 2
            else:
                boundary = text.rfind("\n", start, end)
                if boundary != -1 and boundary > start + (limit // 2): end = boundary + 1
            chunks.append(text[start:end]); start = end
        return chunks

    # ==========================================
    # 🏗️ 查詢與報告 (Search & Reports)
    # ==========================================
    def quick_search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            return self._format_results(results)
        except Exception: return []

    def _format_results(self, raw: Any) -> List[Dict[str, Any]]:
        formatted = []
        if not raw or not raw['ids'] or not raw['ids'][0]: return []
        for i in range(len(raw['ids'][0])):
            formatted.append({
                "id": raw['ids'][0][i],
                "content": raw['documents'][0][i],
                "metadata": raw['metadatas'][0][i],
                "distance": raw['distances'][0][i]
            })
        return formatted

    def _generate_insight_report(self, stats: Dict[str, List[Dict[str, Any]]]) -> None:
        """產出索引成果洞察報告 (Markdown)"""
        report_path = self.resolver.project_root / "00_Inbox" / "Index_Insight_Report.md"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# 🧠 Index Insight Report ({now_str})",
            f"\n## 📊 數據統計",
            f"- **新增/更新資產**: {len(stats['indexed'])}",
            f"- **跳過資產**: {len(stats['skipped'])}",
            f"- **解析失敗**: {len(stats['failed'])}",
            f"\n---",
            f"\n## 🚀 已處理資產 (Processed)",
            "| 資產路徑 | 切塊數 (Chunks) |",
            "| :--- | :---: |"
        ]
        for item in stats["indexed"][:100]:
            lines.append(f"| {item['path']} | {item['chunks']} |")
        
        if stats["failed"]:
            lines.extend([
                f"\n## 🛑 失敗資產 (Failed)",
                "| 資產路徑 | 錯誤訊息 |",
                "| :--- | :--- |"
            ])
            for item in stats["failed"]:
                lines.append(f"| {item['path']} | {item['reason']} |")
        
        report_path.write_text("\n".join(lines), encoding="utf-8")

# ==========================================
# 🏗️ CLI 入口點
# ==========================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Intelligence Navigator: Index Engine")
    parser.add_argument("--index", action="store_true", help="執行索引動作")
    parser.add_argument("--source", type=str, help="指定索引來源路徑")
    parser.add_argument("--force", action="store_true", help="強制重新索引 (忽略 mtime)")
    parser.add_argument("--reset", action="store_true", help="重置向量庫")
    parser.add_argument("--client", default=None)
    parser.add_argument("--site", default=None)
    
    args = parser.parse_args()
    
    if args.index:
        manager = IndexManager(client=args.client, site=args.site)
        if args.reset:
            col_name = f"dcs_kb_{manager.resolver.site.lower()}"
            print(f"🗑️ 正在清空向量庫 (Collection: {col_name})...")
            manager.chroma_client.delete_collection(name=col_name)
            # 重新獲取 collection
            manager.collection = manager.chroma_client.get_or_create_collection(name=col_name, embedding_function=manager.ef)
            
        manager.run_indexing(source_path=args.source, force=args.force or args.reset)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
