
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
from platform import release
import random
import sys
import jsonlines
import datetime
import argparse
import tqdm
from openai import OpenAI
import copy
import uuid


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

def read_jsonl_file(file_name, max_sentence=None):
    data = []
    with jsonlines.open(file_name, "r") as r:
        for i, obj in tqdm.tqdm(enumerate(r)):
            if max_sentence is not None and i >= max_sentence:
                return data
            data.append(obj)
    return data

def write_jsonl_file(objs, path, chunk_size = 1, format="w"):
    os.makedirs(os.path.dirname(path), exist_ok = True)
    with jsonlines.open(path, format, flush=True) as w:
        for i in tqdm.tqdm(range(0, len(objs), chunk_size)):
            w.write_all(objs[i: i + chunk_size])
    print(f"Successfully saving to {path}: {len(objs)}")

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


root_dir = Path(__file__).parent.parent
root_dir_str = str(root_dir)
if root_dir_str not in sys.path:
    sys.path.append(root_dir_str)



file_path = "pipelines/check/dataset/xxx.jsonl"

all_train_data = read_jsonl_file(file_path, max_sentence=None)

language_maps = {}
for i, obj in enumerate(all_train_data):
    if "language" not in obj:
        print(f"Missing language key in object: {obj}")
        language = "unknown"
    else:
        language = obj["language"]
    if language not in language_maps:
        language_maps[language] = []
    language_maps[language].append(obj)
print(f"Total languages: {len(language_maps)}")

language_counts = {lang: len(data) for lang, data in language_maps.items()}
print(f"Language counts: {language_counts}")




