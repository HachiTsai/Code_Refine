import argparse
import sys
import subprocess
from pathlib import Path

# ==========================================
# 🏗️ Core Logic: Unit Refinery Orchestrator (v1.6: Full Integrity)
# ==========================================
# 職責：全單元解析調度。達成「物理還原 -> 語義注入 -> 知識掛載」的全鏈路誠信。
# 變更紀錄:
#   v1.6: 整合 Phase 3 知識強化管線 (knowledge_enhancer.py)。
#   v1.5: 整合 Phase 2 語義注入管線 (semantic_injector.py)。
# ==========================================

def run_script(script_path, client, site, unit, extra_args=None):
    # ==========================================
    # ⚙️ Script Execution Protocol (v1.7: Unified Argument)
    # ==========================================
    cmd = [
        sys.executable, str(script_path),
        '--client', client,
        '--site', site,
        '--unit', unit
    ]
    
    if extra_args:
        cmd.extend(extra_args)

    import os
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    print(f'▶️ Executing {script_path.name} for {unit}...')
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding='utf-8')
    print(result.stdout)
    if result.returncode != 0:
        print(f'❌ Error in {script_path.name}: {result.stderr}')

def main():
    # ==========================================
    # 📡 CLI Entry & Scoping
    # ==========================================
    parser = argparse.ArgumentParser(description='Unit Refinery Orchestrator v1.6')
    parser.add_argument('--unit', required=True, help='Unit ID (e.g., MLC01)')
    parser.add_argument('--site', default='Johor', help='Site Location')
    parser.add_argument('--client', default='RCMT', help='Client Name')
    args = parser.parse_args()

    engine_root = Path(__file__).resolve().parents[1]
    kb_root = engine_root.parents[1] / "20_Knowledge_Base"
    
    # --- 🏗️ Phase 1: Extraction (GID) ---
    parsers = [
        'tag_parser.py', 'seq_tm_parser.py', 'ddc_parser.py', 
        'seq_parser.py', 'bls_parser.py', 'vmd_parser.py', 'alm_parser.py'
    ]
    
    print(f"\n--- [Phase 1: Extraction] GID generation for {args.unit} ---")
    for p in parsers:
        run_script(engine_root / 'src' / 'parsers' / p, args.client, args.site, args.unit)

    # --- 🏗️ Phase 2: Enrichment (CORE SEED) ---
    print(f"\n--- [Phase 2: Enrichment] Semantic Injection (Smart Seeds) for {args.unit} ---")
    run_script(engine_root / 'src' / 'semantic_injector.py', args.client, args.site, args.unit)

    # --- 🏗️ Phase 3: Knowledge Feedforward (CORE ENHANCE) ---
    print(f"\n--- [Phase 3: Knowledge Feedforward] Syncing existing KB to Core for {args.unit} ---")
    # 呼叫 enhancer 掃描 KB 目錄並反哺至剛產出的 core.json
    enhancer_path = engine_root / 'scripts' / 'knowledge_enhancer.py'
    if enhancer_path.exists():
        run_script(enhancer_path, args.client, args.site, args.unit, extra_args=['--batch', str(kb_root)])
    else:
        print(f"⚠️ Warning: Knowledge Enhancer not found at {enhancer_path}")

    # --- 🔄 Post-Processing ---
    print("\n🔄 [Linkage] Triggering DCS Index Rebuild...")
    from index_builder import run_indexing
    run_indexing(client=args.client, site=args.site, unit=args.unit)

if __name__ == '__main__':
    main()
