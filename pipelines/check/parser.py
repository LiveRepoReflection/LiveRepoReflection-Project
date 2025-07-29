from collections import Counter
import logging
import random
import re
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
root_dir_str = str(root_dir)
if root_dir_str not in sys.path:
    sys.path.append(root_dir_str)
import copy
import tqdm
import os
import json
import jsonlines
import argparse
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback

def ensure_directory_exists(path, type="file"):
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
    print(f"Successfully saving to {path} : {len(objs)}")

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
    print(f"Successfully saving to {filename}")



def parse_python(output):
    # pytest summary example:
    # ============================= test session starts ==============================
    # collected 3 items

    # test_module.py ..F                                      [100%]

    # ========================= FAILURES ========================
    # ________________________ test_failure ______________________
    # ...
    # ==================== short test summary info =====================
    # FAILED test_module.py::test_failure - AssertionError

    # For simplicity, check for "failed" or "errors"
    total, passed, failed, errors = 0, 0, 0, 0
    # Match lines like "X passed", "Y failed", "Z errors"
    pass_match = re.search(r'(\d+) passed', output, re.IGNORECASE)
    fail_match = re.search(r'(\d+) failed', output, re.IGNORECASE)
    error_match = re.search(r'(\d+) error', output, re.IGNORECASE)
    if pass_match:
        passed = int(pass_match.group(1))
    if fail_match:
        failed = int(fail_match.group(1))
    if error_match:
        errors = int(error_match.group(1))
    total = passed + failed + errors
    return total, passed, failed, errors


def parse_rust(output):
    # Cargo test summary example:
    # test tests::test_success ... ok
    # test tests::test_failure ... FAILED
    total = passed = failed = 0
    for line in output.splitlines():
        if re.match(r'test .* ... ok', line):
            passed += 1
        elif re.match(r'test .* ... FAILED', line):
            failed += 1
    total = passed + failed
    return total, passed, failed, 0


def parse_go(output):
    # Go test summary example:
    # ok      example  0.123s

    # For failed tests:
    # --- FAIL: TestFunction (0.00s)
    #     function_test.go:10: Expected X, got Y

    total = passed = failed = 0
    if "FAIL" in output:
        failed = 1
        total = 1
        passed = 0
    elif "ok" in output:
        passed = 1
        total = 1
    else:
        total = 0
        passed = 0
        failed = 0
    return total, passed, failed, 0

def parse_javascript(output):
    # Assuming npm test outputs something like:
    # PASS  ./module.test.js
    # FAIL  ./anotherModule.test.js
    total = passed = failed = 0
    for line in output.splitlines():
        if line.startswith("PASS"):
            passed += 1
        elif line.startswith("FAIL"):
            failed += 1
    total = passed + failed
    return total, passed, failed, 0

def parse_cpp(output):
    # Assuming tests are run and output shows number passed/failed
    all_passed_match = re.search(r'All tests passed\s*\((\d+) assertions? in (\d+) test cases?\)', output, re.IGNORECASE)
    if all_passed_match:
        passed_assertions = int(all_passed_match.group(1))
        passed_tests = int(all_passed_match.group(2))
        return passed_tests, passed_assertions, 0, 0
    some_failed_match = re.search(r'Some tests failed\s*\((\d+) failed(?:, (\d+) passed)?\)', output, re.IGNORECASE)
    if some_failed_match:        
        failed_tests = int(some_failed_match.group(1))
        passed_tests = int(some_failed_match.group(2))
        return passed_tests + failed_tests, passed_tests, failed_tests, 0
    return 0, 0, 0, 0

def parse_java(output):
    # Gradle test summary example:
    # BUILD SUCCESSFUL in 3s
    # 5 tests completed, 0 failed
    # total = passed = failed = 0
    # summary_match = re.search(r'(\d+) tests? completed, (\d+) failed', output)
    # if summary_match:
    #     passed = int(summary_match.group(1)) - int(summary_match.group(2))
    #     failed = int(summary_match.group(2))
    #     total = passed + failed
    # else:
        # return 0, 0, 0, 0
    pass_count = output.count(" PASSED")
    if pass_count > 0:
        return pass_count, pass_count, 0, 0
    else:
        return 0, 0, 0, 0
    
parsers = {
    "python": parse_python,
    "rust": parse_rust,
    "go": parse_go,
    "javascript": parse_javascript,
    "cpp": parse_cpp,
    "java": parse_java
}

def is_passed(data_item):
    """
    Check if the unit test is completely passed.
    
    Conditions:
    1. check_info["success"] is True
    2. At least one test is run
    3. All tests are passed
        TEST_COMMANDS = {
            "python": ["pytest"],
            "rust": ["cargo", "test", "--", "--include-ignored"],
            "go": ["go", "test", "./..."],
            "javascript": ["./npm-test.sh"],
            "cpp": ["./cpp-test.sh"],
            "java": ["./gradlew", "test", "--offline", "--gradle-user-home", GRADLE_USER_HOME]
        }
    
    Parameters:
        data_item = {
            "check_info": {
                "unit_test_cwd_path": str,
                "success": bool,
                "returncode": int,
                "res": str,
                "command": str
            },
            "error": {
                "message": str,
                "traceback": str
            },
            "language": str, can be ["python", "rust", "go", "javascript", "cpp", "java"]
            ...
        }
    Return:
        bool: If the unit test is completely passed, return True; otherwise return False and error
    """
    language = data_item.get("language", "")
    check_info = data_item.get("check_info", {})
    if check_info == {}:
        raise Exception(f"Error: {data_item.get('error', {}).get('message', 'unknown')}")
    success = check_info.get("success", False)
    if not success:
        raise Exception(f"{language} Test command failed with return code {check_info.get('returncode', 'unknown')}. {check_info.get('res', '')}.")
    parser = parsers.get(language)
    if not parser:
        raise Exception(f"No parser available for language: {language}")
    test_output = check_info.get("res", "")
    total, passed, failed, errors = parser(test_output)
    failed = failed + errors
    if total == 0:
        raise Exception(f"{language} No tests were run.")
    return total, passed, failed
    
def task_worker(task_args):
    obj = task_args.get("obj", {})
    total, passed, failed = is_passed(obj)
    obj["total"] = total
    obj["passed"] = passed
    obj["failed"] = failed
    return obj


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", nargs='+', type=str, default=["./check/dataset/run_unit_test/xxxxx.jsonl"])
    parser.add_argument("--output_path", type=str, default="./check/dataset/parsed")
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    ensure_directory_exists(args.output_path, type="dir")
    args.current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    print(args.current_time)
    ensure_directory_exists(args.output_path, type="dir")
    return args

def main():
    import subprocess
    subprocess.run(["rm", "-rf", "./check/dataset/parsed"])
    main_args = parse_args()
    all_objs = []
    for input_path in main_args.input_path:
        objs = read_jsonl_file(input_path)
        all_objs.extend(objs)
    
    print(f"Total objects: {len(all_objs)}")
    task_queue = []
    for obj in all_objs:
        task_queue.append(
            {
                "obj": obj
            }
        )
    task_bar = tqdm.tqdm(total=len(task_queue), desc=f"Job Running {main_args.workers} workers")
    batch_size = len(task_queue) + 1
    output_objs, error_objs = [], []
    with ProcessPoolExecutor(max_workers=main_args.workers) as executor:
        futures = [executor.submit(task_worker, task_args) for task_args in task_queue]
        for i, future in enumerate(as_completed(futures), 1):
            task_bar.update(1)
            e = future.exception()
            if e:
                error_objs.append(str(e))
            else:
                obj = future.result()
                output_objs.append(obj)
            if i % batch_size == 0 or i == len(futures):
                if output_objs:
                    write_jsonl_file(output_objs, os.path.join(main_args.output_path, "parsed.jsonl"), format="w")
                    output_objs.clear()
                if error_objs:
                    write_jsonl_file(error_objs, os.path.join(main_args.output_path, "parsed_error.jsonl"), format="w")
                    error_objs.clear()
    task_bar.close()
    stats = {}
    len_output_objs = 0
    try:
        with open(os.path.join(main_args.output_path, "parsed.jsonl"), "r") as f:
            for line in f:
                len_output_objs += 1
                obj = json.loads(line)
                stats[obj["language"]] = stats.get(obj["language"], 0) + 1
    except FileNotFoundError as e:
        len_output_objs = 0
    print(f"Success saved to {os.path.join(main_args.output_path, 'parsed.jsonl')} , {len_output_objs} objs")
    len_error_objs = 0
    try:
        with open(os.path.join(main_args.output_path, "parsed_error.jsonl"), "r") as f:
            for line in f:
                len_error_objs += 1
    except FileNotFoundError as e:
        len_error_objs = 0
    print(f"Error saved to {os.path.join(main_args.output_path, 'parsed_error.jsonl')} , {len_error_objs} objs")

    save_json(stats, os.path.join(main_args.output_path, "parsed_stats.json"), format="w")


if __name__ == "__main__":
    main()

