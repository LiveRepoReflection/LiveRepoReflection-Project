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

def read_jsonl_file(file_name, max_sentence=None):
    data = []
    with jsonlines.open(file_name, "r") as r:
        for i, obj in tqdm.tqdm(enumerate(r)):
            if max_sentence is not None and i >= max_sentence:
                return data
            data.append(obj)
    return data

def write_jsonl_file(objs, path, chunk_size = 1, format="w"):
    # format options: "w", "a"
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
    # print(f"Successfully saving to {filename}")


# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
root_dir_str = str(root_dir)
if root_dir_str not in sys.path:
    sys.path.append(root_dir_str)


def _chat(client_args, chat_args):
    client = OpenAI(
        **client_args
    )
    response = client.chat.completions.create(
        **chat_args
    )
    content = ""
    reasoning_content = ""
    if "stream" in chat_args and chat_args["stream"]:
        for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0 and hasattr(chunk.choices[0], "delta"):
                delta = chunk.choices[0].delta
                if hasattr(delta, "content"):
                    content += delta.content
                if hasattr(delta, "reasoning_content"):
                    reasoning_content += delta.reasoning_content
    else:
        if hasattr(response, "choices") and len(response.choices) > 0 and hasattr(response.choices[0], "message"):
            message = response.choices[0].message
            if hasattr(message, "content"):
                content = message.content
            if hasattr(message, "reasoning_content"):
                reasoning_content = message.reasoning_content
    if reasoning_content and reasoning_content.strip() != "":
        return_str = "<think>\n" + reasoning_content + "\n</think>\n" + content 
    else:
        return_str = content
    return return_str

def chat(
        client_args = {"base_url": os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/"), "api_key": os.environ.get("OPENAI_API_KEY"), "timeout": 600, "max_retries": 10}, 
        chat_args = {"model": "deepseek-r1-inner", "messages": [{"role": "user", "content": "Hello, how are you?"}]}
    ):
    try:
        return _chat(client_args, chat_args)
    except Exception as e:
        return "Retry" + str(e)

def task_worker(task_args):
    obj = task_args.get("obj", {})
    model = task_args.get("model", "deepseek-v3-inner")
    result = copy.deepcopy(obj)

    raw_language = result.get("language", "")
    source_messages = result.get("source_messages", {})
    raw_question_chat_messages = source_messages.get("question", [])
    raw_project_name_chat_messages = source_messages.get("project_name", [])
    if "source_models" not in result:
        result["source_models"] = {}
    else:
        result["source_models"]["answer"] = model
        result["source_models"]["unit_test"] = model
    if len(raw_question_chat_messages) > 0 and "Retry" in raw_question_chat_messages[-1]["content"].strip():
        raise Exception(raw_question_chat_messages[-1]["content"].strip().replace("Retry", ""))
    if len(raw_project_name_chat_messages) > 0 and "Retry" in raw_project_name_chat_messages[-1]["content"].strip():
        raise Exception(raw_project_name_chat_messages[-1]["content"].strip().replace("Retry", ""))
    
    end_suffix = ""
    if raw_language == "rust" or raw_language == "javascript":
        if raw_language == "rust":
            end_suffix = "Attention Our Rust Environment is `rustc 1.75.0 (82e1608df 2023-12-21) (built from a source tarball)`, only support rust edition <= 2021."
        else:
            end_suffix = "Attention Our JavaScript Environment is `Node.js v16.20.2`."

    format_reminder = """When Creating files, maintain a consistent folder structure as shown in the examples by providing the appropriate path/to/filename and adhere to the following format:

path/to/filename
```
// entire code or file content ...
```

- The first line should contain *only* the appropriate path/to/filename, without any additional markup, punctuation, comments, or other elements.
- The second line should start with three backticks (```)
- ... include the complete content of the file ...
- The last line should end with three closing backticks (```)

Please ensure that you *never* skip, omit, or abbreviate content using ellipsis (...) or by adding comments like "... rest of code...". Use only standard libraries in your code.
"""
    project_name = raw_project_name_chat_messages[-1]["content"].strip().replace("```\n", "").replace("\n```", "")

    unit_test_prompt_template = """Please supply a comprehensive {language} unit test for this question. DO NOT include any answer or any other things at this stage.

{format_reminder}

Attention to follow and implement the `{project_name}` project structure, each file should replace in `{project_name}` folder and have similar filepath to ensure the unit test can be run successfully.

Now, begin! {end_suffix}"""

    unit_test_chat_messages = copy.deepcopy(raw_project_name_chat_messages)
    unit_test_chat_messages.append({"role": "user", "content": unit_test_prompt_template.format(language=raw_language, format_reminder=format_reminder, project_name=project_name, end_suffix=end_suffix)})
    unit_test_response = chat(chat_args={"messages": unit_test_chat_messages, "model": model})
    if unit_test_response.strip() == "Retry":
        raise Exception("Unit test generation failed")
    unit_test_chat_messages.append({"role": "assistant", "content": unit_test_response})
    result["source_messages"]["unit_test"] = unit_test_chat_messages
    

    answer_prompt_template = """Please supply a comprehensive {language} answer and necessary dependencies for this question.

{format_reminder}

Attention to follow and implement the `{project_name}` project structure, each file should replace in `{project_name}` folder and have similar filepath to ensure the answer can be run successfully.

Now, begin! {end_suffix}"""

    answer_chat_messages = copy.deepcopy(unit_test_chat_messages)
    answer_chat_messages.append({"role": "user", "content": answer_prompt_template.format(language=raw_language, format_reminder=format_reminder, project_name=project_name, end_suffix=end_suffix)})
    answer_response = chat(chat_args={"messages": answer_chat_messages, "model": model})
    if answer_response.strip() == "Retry":
        raise Exception("Answer generation failed")
    answer_chat_messages.append({"role": "assistant", "content": answer_response})
    result["source_messages"]["answer"] = answer_chat_messages

    return result

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", "-input_path", type=str, default="./generate/dataset/question_and_name/all-cpp-example.jsonl")
    parser.add_argument("--output_path", "-output_path", type=str, default="./generate/dataset/debug/")
    parser.add_argument("--workers", "-workers", type=int, default=1)
    parser.add_argument("--model", "-model", type=str, default="deepseek-v3-inner")
    parser.add_argument("--batch_size", "-batch_size", type=int, default=1)
    args = parser.parse_args()
    ensure_directory_exists(args.output_path, type="dir")
    args.current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    args.output_path = os.path.join(args.output_path, args.current_time)
    ensure_directory_exists(args.output_path, type="dir")
    return args

def main():
    main_args = parse_args()
    objs = read_jsonl_file(main_args.input_path)

    task_queue = []
    for i in range(len(objs)):
        task_queue.append(
            {
                "obj": objs[i],
                "model": main_args.model
            }
        )

    random.shuffle(task_queue)
    task_bar = tqdm.tqdm(total=len(task_queue), desc=f"Job Running {main_args.workers} workers")
    output_objs, error_objs = [], []
    output_objs_path, error_objs_path = os.path.join(main_args.output_path, os.path.basename(main_args.input_path)), os.path.join(main_args.output_path, os.path.basename(main_args.input_path).replace(".jsonl", "_error.jsonl"))

    with ProcessPoolExecutor(max_workers=main_args.workers) as executor:
        futures = [executor.submit(task_worker, task_args) for task_args in task_queue]
        for i, future in enumerate(as_completed(futures), 1):
            task_bar.update(1)
            e = future.exception()
            if e:
                error_objs.append(str(e))
                task_queue.append(task_queue[i])
            else:
                obj = future.result()
                output_objs.append(obj)
            if i % main_args.batch_size == 0 or i == len(futures):
                if output_objs:
                    write_jsonl_file(output_objs, output_objs_path, format="a")
                    output_objs.clear()
                if error_objs:
                    write_jsonl_file(error_objs, error_objs_path, format="a")
                    error_objs.clear()
    task_bar.close()

    len_output_objs = 0
    try:
        with open(output_objs_path, "r") as f:
            for line in f:
                len_output_objs += 1
    except FileNotFoundError as e:
        len_output_objs = 0
    print(f"Success saved to {output_objs_path}, {len_output_objs} objs")
    len_error_objs = 0
    try:
        with open(error_objs_path, "r") as f:
            for line in f:
                len_error_objs += 1
    except FileNotFoundError as e:
        len_error_objs = 0
    
    print(f"Error saved to {error_objs_path}, {len_error_objs} objs")
    


if __name__ == "__main__":
    main()
