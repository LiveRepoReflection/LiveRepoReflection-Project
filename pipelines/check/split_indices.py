import argparse
import math
import json
import os
from pathlib import Path

def split_indices(total_lines, num_splits):
    return [
        (i * total_lines // num_splits, min((i+1)*total_lines // num_splits, total_lines))
        for i in range(num_splits)
    ]


def ensure_directory_exists(path, type="file"):
    """
    Ensure the directory exists, if it does not exist, create it recursively.
    Use parents=True parameter, automatically create all missing parent directories.
    Use exist_ok=True parameter, if the directory exists, do not throw an exception.
    Parameters:
        path (str or Path): The directory path to check, can be a string or Path object.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    path = Path(path)
    if type == "file":
        parent_dir = os.path.dirname(path)
        os.makedirs(parent_dir, exist_ok=True)
    elif type == "dir":
        os.makedirs(path, exist_ok=True)
    else:
        raise ValueError(f"Invalid type: {type}")

def save_json(data, filename, indent = 4, format="w") -> None:
    ensure_directory_exists(os.path.dirname(filename), type="dir")
    if format == "w":
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    elif format == "a":
        with open(filename, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    print(f"Successfully saving to {filename}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", required=True)
    parser.add_argument("--output_file", default="splits.json")
    parser.add_argument("--num_splits", type=int, default=-1)
    parser.add_argument("--average_lines", type=int, default=-1)
    args = parser.parse_args()
    with open(args.input_path) as f:
        total = sum(1 for _ in f)
    if args.average_lines == -1:
        args.average_lines = total // args.num_splits
    if args.num_splits == -1:
        args.num_splits = math.ceil(total / args.average_lines)

    if args.num_splits > total:
        print(f"Warning: The number of splits ({args.num_splits}) is greater than the number of data lines ({total}), automatically adjusted to the number of data lines")
        args.num_splits = total

    splits = split_indices(total, args.num_splits)

    print(f"Total lines: {total}")
    print(f"Average lines: {args.average_lines}")
    print(f"Number of splits: {args.num_splits}")

    result = {
        "splits": [
            {"split_id": i+1, "start": s, "end": e, "length": e-s}
            for i, (s,e) in enumerate(splits)
        ]
    }
    
    save_json(result, args.output_file) 

if __name__ == "__main__":
    main()