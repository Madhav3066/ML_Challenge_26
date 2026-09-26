import os
import sys
import time
import json
import random
import tracemalloc
import multiprocessing as mp
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import normalization as norm

def load_s1_sample(s1_file, sample_size=10000, seed=42):
    random.seed(seed)
    s1_records = []
    
    # Reservoir sampling for S1
    with open(s1_file, 'r', encoding='utf-8', errors='replace') as f:
        f.readline() # header
        for i, line in enumerate(f):
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) < 4:
                continue
            if i < sample_size:
                s1_records.append(parts[:4])
            else:
                j = random.randint(0, i)
                if j < sample_size:
                    s1_records[j] = parts[:4]
                    
    return {p[0].strip(): (p[1].strip(), p[2].strip(), p[3].strip()) for p in s1_records}

def load_ground_truth(gt_file, s1_ids):
    gt_map = defaultdict(set)
    total_pos = 0
    s2_pos = 0
    s3_pos = 0
    
    with open(gt_file, 'r', encoding='utf-8', errors='replace') as f:
        f.readline() # header
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) < 2 or not parts[1].strip():
                continue
            s1_id = parts[0].strip()
            if s1_id in s1_ids:
                mids = [m.strip() for m in parts[1].split(',') if m.strip()]
                for mid in mids:
                    gt_map[s1_id].add(mid)
                    total_pos += 1
                    if mid.startswith('S2-'):
                        s2_pos += 1
                    else:
                        s3_pos += 1
                        
    return gt_map, total_pos, s2_pos, s3_pos

def index_source_against_keys(file_path, active_keys, max_key_freq=150, src_label="Source"):
    print(f"      [{src_label}] Started indexing...", flush=True)
    key_counts = defaultdict(int)
    key_to_cands = defaultdict(list)
    
    t0 = time.time()
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline() # header
        for count, line in enumerate(f):
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) < 4:
                continue
            eid, name, addr, country = parts[0], parts[1], parts[2], parts[3]
            
            c_name = norm.clean_business_name(name)
            r_name = norm.get_root_name(c_name)
            c_addr = norm.clean_business_address(addr)
            keys_dict = norm.generate_blocking_keys(r_name, c_name, addr, c_addr, country)
            
            for pass_name, k in keys_dict.items():
                if k and k in active_keys:
                    key_counts[k] += 1
                    key_to_cands[k].append(eid)
                    
            if (count + 1) % 1000000 == 0:
                print(f"      [{src_label}] Processed {count+1:,} records in {round(time.time() - t0, 1)}s...", flush=True)
                
    # Frequency capping: prune keys with > max_key_freq
    print(f"      [{src_label}] Applying frequency capping (<= {max_key_freq})...", flush=True)
    capped_index = {}
    pruned = 0
    for k, cands in key_to_cands.items():
        if len(cands) <= max_key_freq:
            capped_index[k] = cands
        else:
            pruned += 1
    print(f"      [{src_label}] Retained {len(capped_index):,} active blocks ({pruned:,} high-frequency blocks pruned in {round(time.time() - t0, 1)}s).", flush=True)
    return capped_index

def main():
    tracemalloc.start()
    start_time = time.time()
    print("=" * 60, flush=True)
    print("STEP 3C: CANDIDATE GENERATION & RECALL EVALUATION (PARALLEL OFFLINE)", flush=True)
    print("=" * 60, flush=True)
    
    output_dir = "student_resource/outputs/step3_baseline/reports"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    s1_file = "student_resource/dataset/train/train_source1.tsv"
    s2_file = "student_resource/dataset/train/train_source2.tsv"
    s3_file = "student_resource/dataset/train/train_source3.tsv"
    gt_file = "student_resource/dataset/train/train_ground_truth.tsv"
    
    SAMPLE_SIZE = 10000
    print(f"[1/5] Sampling {SAMPLE_SIZE} S1 reference entities from Train Source 1...", flush=True)
    s1_records = load_s1_sample(s1_file, sample_size=SAMPLE_SIZE, seed=42)
    s1_ids = set(s1_records.keys())
    print(f"      Sampled {len(s1_records)} S1 entities.", flush=True)
    
    print("[2/5] Loading ground-truth matches for evaluation sample...", flush=True)
    gt_map, total_eval_positives, total_eval_s2_pos, total_eval_s3_pos = load_ground_truth(gt_file, s1_ids)
    print(f"      Evaluation ground-truth positives: {total_eval_positives:,} ({total_eval_s2_pos:,} S2, {total_eval_s3_pos:,} S3)", flush=True)
    
    print("[3/5] Precomputing blocking keys for S1 sample...", flush=True)
    # s1_id -> pass_id -> key
    s1_keys = {}
    active_keys = set()
    key_to_s1_matches = defaultdict(list)
    
    for s1_id, (s1_name, s1_addr, s1_c) in s1_records.items():
        c_name = norm.clean_business_name(s1_name)
        r_name = norm.get_root_name(c_name)
        c_addr = norm.clean_business_address(s1_addr)
        k_dict = norm.generate_blocking_keys(r_name, c_name, s1_addr, c_addr, s1_c)
        s1_keys[s1_id] = k_dict
        for pid, (pass_name, k) in enumerate(k_dict.items(), start=1):
            if k:
                active_keys.add(k)
                key_to_s1_matches[k].append((s1_id, pid))
                
    print(f"      Generated {len(active_keys):,} distinct blocking keys across sample S1 entities.", flush=True)
    
    print("[4/5] Indexing target sources (Source 2 and Source 3) in parallel against sample keys...", flush=True)
    with mp.Pool(2) as pool:
        async_s2 = pool.apply_async(index_source_against_keys, (s2_file, active_keys, 150, "Source 2"))
        async_s3 = pool.apply_async(index_source_against_keys, (s3_file, active_keys, 150, "Source 3"))
        s2_index = async_s2.get()
        s3_index = async_s3.get()
    
    # Generate candidates and rank
    print("\n[5/5] Generating candidates and computing recall across K in {10, 15, 20, 25}...", flush=True)
    # s1_id -> cand_id -> (passes_matched, min_pass_id)
    s1_candidates = defaultdict(lambda: defaultdict(lambda: [0, 999]))
    
    for k, s2_cands in s2_index.items():
        for s1_id, pid in key_to_s1_matches[k]:
            for cid in s2_cands:
                entry = s1_candidates[s1_id][cid]
                entry[0] += 1
                if pid < entry[1]:
                    entry[1] = pid
                    
    for k, s3_cands in s3_index.items():
        for s1_id, pid in key_to_s1_matches[k]:
            for cid in s3_cands:
                entry = s1_candidates[s1_id][cid]
                entry[0] += 1
                if pid < entry[1]:
                    entry[1] = pid
                    
    total_candidates_found = sum(len(cands) for cands in s1_candidates.values())
    avg_cands_per_s1 = round(total_candidates_found / SAMPLE_SIZE, 2)
    print(f"      Total candidates generated: {total_candidates_found:,} (Average: {avg_cands_per_s1} per S1 entity)", flush=True)
    
    # Rank candidates per S1 entity by (passes_matched DESC, min_pass_id ASC)
    ranked_candidates = {}
    for s1_id, cands in s1_candidates.items():
        sorted_cands = sorted(cands.items(), key=lambda x: (-x[1][0], x[1][1]))
        ranked_candidates[s1_id] = [cid for cid, _ in sorted_cands]
        
    k_values = [10, 15, 20, 25]
    recall_results = {}
    
    for k in k_values:
        recalled_total = 0
        recalled_s2 = 0
        recalled_s3 = 0
        
        for s1_id, gt_mids in gt_map.items():
            top_k = set(ranked_candidates.get(s1_id, [])[:k])
            for mid in gt_mids:
                if mid in top_k:
                    recalled_total += 1
                    if mid.startswith('S2-'):
                        recalled_s2 += 1
                    else:
                        recalled_s3 += 1
                        
        recall_pct = round(100.0 * recalled_total / total_eval_positives, 2) if total_eval_positives else 0
        recall_s2_pct = round(100.0 * recalled_s2 / total_eval_s2_pos, 2) if total_eval_s2_pos else 0
        recall_s3_pct = round(100.0 * recalled_s3 / total_eval_s3_pos, 2) if total_eval_s3_pos else 0
        
        recall_results[f"K={k}"] = {
            "k": k,
            "overall_recall_pct": recall_pct,
            "recalled_total": recalled_total,
            "total_positives": total_eval_positives,
            "s2_recall_pct": recall_s2_pct,
            "s3_recall_pct": recall_s3_pct
        }
        print(f"      >> K = {k:2d}: Overall Recall = {recall_pct:6.2f}% | S2 Recall = {recall_s2_pct:6.2f}% | S3 Recall = {recall_s3_pct:6.2f}%", flush=True)
        
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mem_mb = round(peak_mem / (1024 * 1024), 2)
    elapsed = round(time.time() - start_time, 2)
    print(f"\nExecution completed in {elapsed} seconds. Peak memory: {peak_mem_mb} MB.", flush=True)
    
    report_data = {
        "sample_size": SAMPLE_SIZE,
        "total_eval_positives": total_eval_positives,
        "total_candidates_found": total_candidates_found,
        "avg_candidates_per_s1": avg_cands_per_s1,
        "recall_by_k": recall_results,
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_mem_mb
    }
    
    report_files = [
        os.path.join(output_dir, "candidate_recall_report.json"),
        "reports/candidate_recall_report.json"
    ]
    for rf in report_files:
        with open(rf, "w") as fp:
            json.dump(report_data, fp, indent=2)
        print(f"Report saved to: {rf}", flush=True)

if __name__ == "__main__":
    main()
