from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import traceback
import uuid
import jsonlines
import datetime
import argparse
import tqdm
from openai import OpenAI
import copy


root_dir = Path(__file__).parent.parent.parent  # Go up two levels to get to the project root
root_dir_str = str(root_dir)
if root_dir_str not in sys.path:
    sys.path.append(root_dir_str)

from pipelines.utils.tools import parse_stacked_content
from pipelines.utils.setting import APPEND_FILES

UNIT_TEST_RESOURCES_PATH = root_dir / "pipelines" / "utils" / "unit_test_resources"
UNIT_TEST_TIMEOUT = 60 * 3
TEST_COMMANDS = {
    "python": ["pytest"],
    "rust": ["cargo", "test", "--", "--include-ignored"],
    "go": ["go", "test", "./..."],
    "javascript": ["./npm-test.sh"],
    "cpp": ["./cpp-test.sh"],
    "java": ["./gradlew", "test", "--no-daemon"],
}
env  = os.environ.copy()
UNIT_TEST_ENV = env


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



def read_jsonl_file(file_name, max_sentence=None, start_index=0, end_index=None):
    data = []
    with jsonlines.open(file_name, "r") as r:
        for i, obj in tqdm.tqdm(enumerate(r)):
            if i < start_index:
                continue
            if end_index is not None and i >= end_index:
                break
            if max_sentence is not None and i >= max_sentence + start_index:
                break
            data.append(obj)
    return data

def write_jsonl_file(objs, path, chunk_size = 1, format="w"):
    os.makedirs(os.path.dirname(path), exist_ok = True)
    with jsonlines.open(path, mode=format, flush=True) as writer:
        for i in tqdm.tqdm(range(0, len(objs), chunk_size)):
            for obj in objs[i: i + chunk_size]:
                writer.write(obj)
    print(f"Successfully saving to {path} : {len(objs)}")


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

def messages_update_data_map(data_map):
    check_data_map = copy.deepcopy(data_map)
    check_data_map["contents"] = {}
    check_data_map["config"] = {}
    source_messages = check_data_map["source_messages"]
    question_response = source_messages["question"][-1]["content"]
    project_name_response = source_messages["project_name"][-1]["content"]
    answer_response = source_messages["answer"][-1]["content"]
    unit_test_response = source_messages["unit_test"][-1]["content"]
    # config/contents
    project_name_pattern = r'```\n+([a-zA-Z_]+)\n+```'
    # first get the match object, avoid directly calling group(1) to cause an exception
    match = re.search(project_name_pattern, project_name_response)
    if match:
        # when successfully matched, extract the value
        project_name = match.group(1).strip()  # add strip() to handle unexpected spaces
        if not project_name:  # handle empty string case
            raise Exception("Cannot get project name")
    else:
        raise Exception("Cannot get project name")
    check_data_map["folder"] = project_name
    check_data_map["contents"][f"{check_data_map['folder']}/.docs/instructions.md"] = question_response
    tmp_data = parse_stacked_content(unit_test_response)
    keys = []
    for item in tmp_data:
        for filename, content in item.items():
            check_data_map["contents"][filename] = content
            keys.append(filename)
    check_data_map["config"]["test"] = keys
    tmp_data = parse_stacked_content(answer_response)
    keys = []
    for item in tmp_data:
        for filename, content in item.items():
            check_data_map["contents"][filename] = content
            keys.append(filename)
    check_data_map["config"]["solution"] = keys
    return check_data_map

def unit_test_command_preparation(tmp_path, check_data_map):
    language = check_data_map["language"]
    folder = check_data_map["folder"]
    unit_test_path = tmp_path / language / f"unit_test_{str(uuid.uuid4()).replace('-', '_')}"
    unit_test_cwd_path = unit_test_path / folder

    # append files
    append_file = APPEND_FILES.get(language, {})
    for filename, content in append_file.items():
        file_path = unit_test_cwd_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)

    # model generated file, can override the above
    for filename, content in check_data_map["contents"].items():
        if filename.startswith(folder):
            file_path = unit_test_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            wcontent = content
            with open(file_path, "w") as f:
                f.write(wcontent)
        else:
            file_path = unit_test_cwd_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            wcontent = content
            with open(file_path, "w") as f:
                f.write(wcontent)

    # permission adjustment, link creation, miscellaneous processing
    if language == "cpp":
        os.chmod(unit_test_cwd_path / "cpp-test.sh", 0o777)
        shutil.copy(UNIT_TEST_RESOURCES_PATH / "cpp" / "catch.hpp", unit_test_cwd_path / 'catch.hpp')

    elif language == "java":
        # Set executable permissions for gradlew
        os.chmod(unit_test_cwd_path / "gradlew", 0o777)
        
        # Remove @Disabled annotations from Java test files
        test_files = check_data_map["config"]["test"]
        for file_path in test_files:
            if file_path.endswith(".java"):
                test_file = unit_test_cwd_path / file_path
                if test_file.exists():
                    content = test_file.read_text()
                    content = re.sub(r"@Disabled\([^)]*\)\s*\n", "", content)
                    test_file.write_text(content)

        shutil.copy(UNIT_TEST_RESOURCES_PATH / "java" / "gradle-wrapper.jar", unit_test_cwd_path / 'gradle' / 'wrapper' / 'gradle-wrapper.jar')
        os.chmod(unit_test_cwd_path / "gradle" / "wrapper" / "gradle-wrapper.jar", 0o777)

    elif language == "javascript":
        # Set executable permissions for npm-test.sh
        os.chmod(unit_test_cwd_path / "npm-test.sh", 0o777)
        
    elif language == "rust":
        # modify .../Cargo.toml
        cargo_toml = unit_test_cwd_path / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text()
            # ensure edition = "2021"
            content = re.sub(r"edition = \"[0-9.]+\"", "edition = \"2021\"", content)
            cargo_toml.write_text(content)

    # if the test file is not in testcwd, paste in
    for file in check_data_map["config"]["test"]:
        file = unit_test_path / file
        file_name = file.name
        tgt_file = unit_test_cwd_path / file_name
        if not tgt_file.exists():
            file.rename(tgt_file)

    return unit_test_cwd_path

def run_unit_test(unit_test_cwd_path, language):
    command_list = TEST_COMMANDS[language]
    command_str = " ".join(command_list)

    result = subprocess.run(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=UNIT_TEST_TIMEOUT,
            cwd=unit_test_cwd_path,
            env=UNIT_TEST_ENV,
            encoding="utf-8",
            errors="replace",
    )
    success = result.returncode == 0
    res = result.stdout
    return success, result.returncode, res, command_str

def run_data_map(tmp_path, data_map):
    if not tmp_path.exists():
        tmp_path.mkdir(parents=True, exist_ok=True)
    check_data_map = messages_update_data_map(data_map)
    check_data_map_to_run = copy.deepcopy(check_data_map)
    language = check_data_map_to_run["language"]
    check_data_map_to_run["check_info"] = {}
    if len(check_data_map["config"]["solution"]) == 0:
        check_data_map_to_run["error"] = {
            "str": "Missing solution file",
            "traceback": None
        }
        raise Exception("Missing solution file", check_data_map_to_run)
    if len(check_data_map["config"]["test"]) == 0:
        check_data_map_to_run["error"] = {
            "str": "Missing test file",
            "traceback": None
        }
        raise Exception("Missing test file", check_data_map_to_run)
    
    try:
        unit_test_cwd_path = unit_test_command_preparation(tmp_path, check_data_map_to_run)
        check_data_map_to_run["check_info"]["unit_test_cwd_path"] = str(unit_test_cwd_path)
    except Exception as e:
        check_data_map_to_run["error"] = {
            "str": str(e),
            "traceback": traceback.format_exception(e)
        }
        raise Exception("Cannot create unit test env", check_data_map_to_run)
    
    try:
        success, returncode, res, command_str = run_unit_test(unit_test_cwd_path, language)
        check_data_map_to_run["check_info"]["success"] = success
        check_data_map_to_run["check_info"]["returncode"] = returncode
        check_data_map_to_run["check_info"]["res"] = res
        check_data_map_to_run["check_info"]["command"] = command_str
    except Exception as e:
        check_data_map_to_run["error"] = {
            "str": str(e),
            "traceback": traceback.format_exception(e)
        }
        raise Exception("Cannot run unit test", check_data_map_to_run)
    return check_data_map_to_run

def task_worker(task_args):
    obj = task_args.get("obj", {})
    tmp_path = task_args.get("tmp_path", Path("tmp"))
    result = copy.deepcopy(obj)
    result = run_data_map(tmp_path, result)
    return result

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", "-input_path", type=str, default="./check/dataset/answer_unit_test/xxxxx.jsonl")
    parser.add_argument("--tmp_path", "-tmp_path", type=str, default="./check/tmp_debug")
    parser.add_argument("--output_path", "-output_path", type=str, default="./check/dataset/run_unit_test/")
    parser.add_argument("--workers", "-workers", type=int, default=1)
    parser.add_argument("--start_index", "-start_index", type=int, default=0, help="Start index of the input file (inclusive).")
    parser.add_argument("--end_index", "-end_index", type=int, default=None, help="End index of the input file (exclusive).")
    parser.add_argument("--batch_size", "-batch_size", type=int, default=1, help="Batch size of the input file.")
    args = parser.parse_args()
    ensure_directory_exists(args.output_path, type="dir")
    ensure_directory_exists(args.tmp_path, type="dir")
    return args

def main():
    main_args = parse_args()
    objs = read_jsonl_file(
        main_args.input_path,
        start_index=main_args.start_index,
        end_index=main_args.end_index
    )

    task_queue = []
    for obj in objs:
        task_queue.append(
            {
                "obj": obj,
                "tmp_path": Path(main_args.tmp_path)
            }
        )
    random.shuffle(task_queue)
    task_bar = tqdm.tqdm(total=len(task_queue), desc=f"Job Running {main_args.workers} workers")
    batch_size = main_args.batch_size
    output_objs, error_objs = [], []
    with ProcessPoolExecutor(max_workers=main_args.workers) as executor:
        futures = [executor.submit(task_worker, task_args) for task_args in task_queue]
        for i, future in enumerate(as_completed(futures), 1):
            task_bar.update(1)
            e = future.exception()
            if e:
                error_objs.append(
                    {
                        # "obj": task_queue[i-1]["obj"],
                        "error": str(e) + "\n" + traceback.format_exc()
                    }
                )
            else:
                obj = future.result()
                output_objs.append(obj)
            if i % batch_size == 0 or i == len(futures):
                if output_objs:
                    write_jsonl_file(output_objs, os.path.join(main_args.output_path, os.path.basename(main_args.input_path)), format="a")
                    output_objs.clear()
                if error_objs:
                    write_jsonl_file(error_objs, os.path.join(main_args.output_path, os.path.basename(main_args.input_path).replace(".jsonl", "_error.jsonl")), format="a")
                    error_objs.clear()
    task_bar.close()

if __name__ == "__main__":
    main()

