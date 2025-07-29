import json
import math
import os
from anyio import Path
import tqdm
import jsonlines
import multiprocessing as mp
import traceback

def ensure_directory_exists(path, type="file"):
    """
    确保指定路径的目录存在，如果不存在则递归创建。
        使用parents=True参数，自动创建路径中所有缺失的父目录。
        使用exist_ok=True参数，如果目录已存在则不抛出异常。
    参数：
        path (str 或 Path): 要检查的目录路径，可以是字符串或Path对象。
    """
    # 如果是相对路径，则转换为绝对路径
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    path = Path(path)
    if type == "file":
        parent_dir = os.path.dirname(path)
        # filename = os.path.basename(path)
        os.makedirs(parent_dir, exist_ok=True)
    elif type == "dir":
        os.makedirs(path, exist_ok=True)
    else:
        raise ValueError(f"Invalid type: {type}")


def write_jsonl_file(objs, path, chunk_size = 1, format="w"):
    # format options: "w", "a"
    os.makedirs(os.path.dirname(path), exist_ok = True)
    with jsonlines.open(path, format, flush=True) as w:
        for i in tqdm.tqdm(range(0, len(objs), chunk_size)):
            w.write_all(objs[i: i + chunk_size])
    print(f"Successfully saving to {path}: {len(objs)}")

def read_jsonl_file(file_name, max_sentence=None):
    data = []
    with jsonlines.open(file_name, "r") as r:
        for i, obj in tqdm.tqdm(enumerate(r)):
            if max_sentence is not None and i >= max_sentence:
                return data
            data.append(obj)
    return data

def read_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def save_json(data, filename, indent = 4, format="w") -> None:
    ensure_directory_exists(os.path.dirname(filename), type="dir")
    if format == "w":
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    elif format == "a":
        with open(filename, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    # print(f"Successfully saving to {filename}")