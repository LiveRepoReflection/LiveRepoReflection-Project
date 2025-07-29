import glob
import jsonlines
import json
import os
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor

def process_file(f):
    results = []
    error_count = 0
    
    try:
        with open(f, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    obj = json.loads(line)
                    results.append(obj)
                except json.JSONDecodeError as e:
                    error_count += 1
                    print(f"Warning: Invalid JSON in {f} at line {line_num}: {e}")
                    print(f"  Problematic line: {line[:100]}...")
                    continue
                except Exception as e:
                    error_count += 1
                    print(f"Warning: Unexpected error in {f} at line {line_num}: {e}")
                    continue
    
    except Exception as e:
        print(f"Error: Cannot read file {f}: {e}")
        return []
    
    if error_count > 0:
        print(f"File {f}: processed {len(results)} valid lines, skipped {error_count} invalid lines")
    
    return results

def merge_results(output_base, time_stample_flag=False, filename="all.jsonl"):
    if time_stample_flag:
        all_files = sorted(glob.glob(f"{output_base}/tmp.unit_test/split_*/*/{filename}"))
    else:
        all_files = sorted(glob.glob(f"{output_base}/tmp.unit_test/split_*/{filename}"))
    
    if not all_files:
        print(f"Warning: No {filename} files found in {output_base}")
        return
    
    print(f"Found {len(all_files)} files to merge")
    line_count = 0
    successful_files = 0

    try:
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(process_file, all_files))
    except Exception as e:
        print(f"Error during parallel processing: {e}")
        return

    merged_file = f"{output_base}/merged_{filename}"
    try:
        with jsonlines.open(merged_file, "w") as writer:
            for i, objs in enumerate(results):
                if objs:
                    successful_files += 1
                    for obj in objs:
                        try:
                            writer.write(obj)
                            line_count += 1
                        except Exception as e:
                            print(f"Warning: Failed to write object from file {all_files[i]}: {e}")
                            continue
                else:
                    print(f"Warning: No valid data from file {all_files[i]}")
    except Exception as e:
        print(f"Error creating merged file {merged_file}: {e}")
        return

    print(f"Merged {successful_files}/{len(all_files)} files into {merged_file}, with {line_count} lines")

def find_latest_batch_dir(base_path):
    pattern = os.path.join(base_path, "20*-*")
    batch_dirs = sorted(glob.glob(pattern), reverse=True)
    if batch_dirs:
        return batch_dirs[0]
    return None

def main():
    parser = argparse.ArgumentParser(description="Merge distributed unit test results")
    parser.add_argument("--batch_dir", type=str, 
                        help="Batch directory path, if not specified, automatically find the latest")
    parser.add_argument("--base_path", type=str, 
                        default="pipelines/check/dataset/run_unit_test",
                        help="Base path")
    parser.add_argument("--files", type=str, nargs="+", 
                        default=["all.jsonl", "all_error.jsonl"],
                        help="List of files to merge")
    
    args = parser.parse_args()
    
    if args.batch_dir:
        batch_path = args.batch_dir
    else:
        batch_path = find_latest_batch_dir(args.base_path)
        if not batch_path:
            print(f"Error: No batch directories found in {args.base_path}")
            sys.exit(1)
    
    if not os.path.exists(batch_path):
        print(f"Error: Batch directory {batch_path} does not exist")
        sys.exit(1)
    
    print(f"Merging results from: {batch_path}")
    
    for filename in args.files:
        print(f"Merging {filename}...")
        merge_results(batch_path, time_stample_flag=False, filename=filename)

if __name__ == "__main__":
    main()

