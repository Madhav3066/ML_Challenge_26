import os
import sys
import csv
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))
import normalization as norm

def normalize_source_file(input_path: str, output_path: str, chunk_report: int = 500000):
    if not os.path.exists(input_path):
        print(f"Error: input file not found: {input_path}")
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Normalizing: {input_path} -> {output_path}")
    t0 = time.time()
    
    with open(input_path, 'r', encoding='utf-8', errors='replace') as infile, \
         open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')
        
        header = next(reader, None)
        out_header = [
            "entity_id",
            "raw_name",
            "clean_name",
            "root_name",
            "raw_address",
            "clean_address",
            "standard_region",
            "first_num_token",
            "country",
            "pass1_key",
            "pass2_key",
            "pass3_key",
            "pass4_key"
        ]
        writer.writerow(out_header)
        
        row_count = 0
        for row in reader:
            if not row:
                continue
            eid = row[0].strip()
            name = row[1].strip() if len(row) > 1 else ""
            addr = row[2].strip() if len(row) > 2 else ""
            raw_country = row[3].strip() if len(row) > 3 else ""
            
            # 1. Cleaned and root name
            c_name = norm.clean_business_name(name)
            r_name = norm.get_root_name(c_name)
            
            # 2. Cleaned address and tokens
            c_addr = norm.clean_business_address(addr)
            reg = norm.standardize_region(addr, raw_country)
            num_tok = norm.extract_first_num_token(c_addr)
            
            # 3. Normalized country
            c_country = norm.normalize_country(raw_country)
            
            # 4. Blocking keys
            keys = norm.generate_blocking_keys(r_name, c_name, addr, c_addr, c_country)
            
            writer.writerow([
                eid,
                name,
                c_name,
                r_name,
                addr,
                c_addr,
                reg,
                num_tok,
                c_country,
                keys.get("pass1", ""),
                keys.get("pass2", ""),
                keys.get("pass3", ""),
                keys.get("pass4", "")
            ])
            
            row_count += 1
            if row_count % chunk_report == 0:
                print(f"  Processed {row_count:,} records in {round(time.time() - t0, 1)}s...")
                
    elapsed = round(time.time() - t0, 2)
    print(f"Completed {input_path}: {row_count:,} records normalized in {elapsed}s.")

def main():
    parser = argparse.ArgumentParser(description="Normalize entity resolution TSV datasets.")
    parser.add_argument("--sources", nargs="+", default=["train_source1", "train_source2", "train_source3", "test_source1", "test_source2", "test_source3"],
                        help="List of sources to normalize")
    parser.add_argument("--dataset-dir", default="student_resource/dataset", help="Dataset directory")
    parser.add_argument("--output-dir", default="outputs/normalized", help="Output directory for normalized data")
    args = parser.parse_args()
    
    for src in args.sources:
        split = "train" if src.startswith("train") else "test"
        infile = os.path.join(args.dataset_dir, split, f"{src}.tsv")
        outfile = os.path.join(args.output_dir, f"{src}_normalized.tsv")
        normalize_source_file(infile, outfile)

if __name__ == "__main__":
    main()
