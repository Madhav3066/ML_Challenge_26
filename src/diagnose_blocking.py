import os
import sys
import csv
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import normalization as norm

def load_ground_truth_sample(gt_path, target_s2=5000, target_s3=5000):
    s2_pairs = []
    s3_pairs = []
    s1_needed = set()
    s2_needed = set()
    s3_needed = set()

    with open(gt_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader, None)
        for row in reader:
            if len(row) < 2 or not row[1].strip():
                continue
            s1_id = row[0].strip()
            matched_ids = [m.strip() for m in row[1].split(',') if m.strip()]
            for mid in matched_ids:
                if mid.startswith('S2-') and len(s2_pairs) < target_s2:
                    s2_pairs.append((s1_id, mid, 'S2'))
                    s1_needed.add(s1_id)
                    s2_needed.add(mid)
                elif mid.startswith('S3-') and len(s3_pairs) < target_s3:
                    s3_pairs.append((s1_id, mid, 'S3'))
                    s1_needed.add(s1_id)
                    s3_needed.add(mid)
            if len(s2_pairs) >= target_s2 and len(s3_pairs) >= target_s3:
                break

    all_pairs = s2_pairs + s3_pairs
    return all_pairs, s1_needed, s2_needed, s3_needed

def load_entities_for_ids(file_path, target_ids):
    records = {}
    if not os.path.exists(file_path):
        print(f"Warning: file not found: {file_path}")
        return records
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            eid = row[0].strip()
            if eid in target_ids:
                name = row[1] if len(row) > 1 else ""
                addr = row[2] if len(row) > 2 else ""
                country = row[3] if len(row) > 3 else ""
                records[eid] = (name, addr, country)
                if len(records) == len(target_ids):
                    break
    return records

def main():
    print("Sampling 10,000 ground truth pairs (5,000 S2 and 5,000 S3)...")
    gt_file = "student_resource/dataset/train/train_ground_truth.tsv"
    s1_file = "student_resource/dataset/train/train_source1.tsv"
    s2_file = "student_resource/dataset/train/train_source2.tsv"
    s3_file = "student_resource/dataset/train/train_source3.tsv"

    pairs, s1_ids, s2_ids, s3_ids = load_ground_truth_sample(gt_file, 5000, 5000)
    print(f"Retrieved {len(pairs)} pairs for evaluation.")
    print(f"Loading entity records from Source 1 ({len(s1_ids)}), Source 2 ({len(s2_ids)}), Source 3 ({len(s3_ids)})...")

    s1_dict = load_entities_for_ids(s1_file, s1_ids)
    s2_dict = load_entities_for_ids(s2_file, s2_ids)
    s3_dict = load_entities_for_ids(s3_file, s3_ids)

    stats = {
        'S2': {'total': 0, 'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'any': 0, 'missed': 0},
        'S3': {'total': 0, 'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'any': 0, 'missed': 0}
    }

    missed_samples = {'S2': [], 'S3': []}

    for s1_id, m_id, src in pairs:
        s1_data = s1_dict.get(s1_id, ("", "", ""))
        s1_name, s1_addr, s1_c = s1_data

        m_data = s2_dict.get(m_id) if src == 'S2' else s3_dict.get(m_id)
        m_data = m_data or ("", "", "")
        m_name, m_addr, m_c = m_data

        # Keys for S1
        c1_name = norm.clean_business_name(s1_name)
        r1_name = norm.get_root_name(c1_name)
        c1_addr = norm.clean_business_address(s1_addr)
        k1_dict = norm.generate_blocking_keys(r1_name, c1_name, s1_addr, c1_addr, s1_c)

        # Keys for Match
        cm_name = norm.clean_business_name(m_name)
        rm_name = norm.get_root_name(cm_name)
        cm_addr = norm.clean_business_address(m_addr)
        km_dict = norm.generate_blocking_keys(rm_name, cm_name, m_addr, cm_addr, m_c)

        m_p1 = bool(k1_dict['pass1'] and k1_dict['pass1'] == km_dict['pass1'])
        m_p2 = bool(k1_dict['pass2'] and k1_dict['pass2'] == km_dict['pass2'])
        m_p3 = bool(k1_dict['pass3'] and k1_dict['pass3'] == km_dict['pass3'])
        m_p4 = bool(k1_dict['pass4'] and k1_dict['pass4'] == km_dict['pass4'])

        m_any = m_p1 or m_p2 or m_p3 or m_p4

        stats[src]['total'] += 1
        if m_p1: stats[src]['p1'] += 1
        if m_p2: stats[src]['p2'] += 1
        if m_p3: stats[src]['p3'] += 1
        if m_p4: stats[src]['p4'] += 1
        if m_any:
            stats[src]['any'] += 1
        else:
            stats[src]['missed'] += 1
            if len(missed_samples[src]) < 10:
                missed_samples[src].append({
                    's1_name': s1_name,
                    'm_name': m_name,
                    's1_addr': s1_addr,
                    'm_addr': m_addr,
                    's1_c': s1_c,
                    'k1_s1': k1_dict,
                    'k1_m': km_dict
                })

    for src in ['S2', 'S3']:
        tot = stats[src]['total']
        if tot == 0:
            continue
        print(f"\n=== STATS FOR {src} (Total: {tot}) ===")
        print(f"  Pass 1 (exact root name)       : {stats[src]['p1']:5d} ({stats[src]['p1']/tot*100:6.2f}%)")
        print(f"  Pass 2 (2 tokens + num addr)   : {stats[src]['p2']:5d} ({stats[src]['p2']/tot*100:6.2f}%)")
        print(f"  Pass 3 (6 chars + 3 region)    : {stats[src]['p3']:5d} ({stats[src]['p3']/tot*100:6.2f}%)")
        print(f"  Pass 4 (num addr + 3 char name): {stats[src]['p4']:5d} ({stats[src]['p4']/tot*100:6.2f}%)")
        print(f"  Union of all 4 passes          : {stats[src]['any']:5d} ({stats[src]['any']/tot*100:6.2f}%)")
        print(f"  Missed by all 4 passes         : {stats[src]['missed']:5d} ({stats[src]['missed']/tot*100:6.2f}%)")

    report_paths = [
        "student_resource/outputs/step3_baseline/reports/blocking_pass_breakdown.json",
        "reports/blocking_pass_breakdown.json"
    ]
    for rpath in report_paths:
        os.makedirs(os.path.dirname(rpath), exist_ok=True)
        with open(rpath, "w", encoding="utf-8") as fp:
            json.dump({
                "stats": stats,
                "missed_samples": missed_samples
            }, fp, indent=2, ensure_ascii=False)
        print(f"Detailed diagnostics saved to {rpath}")

if __name__ == "__main__":
    main()


