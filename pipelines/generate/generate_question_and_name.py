from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import random
import sys
import jsonlines
import datetime
import argparse
import tqdm
from openai import OpenAI

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

def write_jsonl_file(objs, path, chunk_size = 1, format="w"):
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
        chat_args = {"model": "EMPTY", "messages": [{"role": "user", "content": "Hello, how are you?"}]}
    ):
    try:
        return _chat(client_args, chat_args)
    except Exception as e:
        return "Retry" + " " + str(e)

def ext2md_prefix(ext):
    if ext == "py":
        return "python"
    elif ext == "js":
        return "javascript"
    elif ext == "java":
        return "java"
    elif ext == "cpp":
        return "cpp"
    elif ext == "go":
        return "go"
    elif ext == "rust":
        return "rust"
    elif ext == "md":
        return "md"
    else:
        return ""

def split_sample_data_by_flag(one, flag):
    answer = ""
    if flag == "project_name":
        answer = "```\n" + one["folder"] + "\n```"
    elif flag == "instruction":
        for fname, fcontent in one["contents"].items():
            if fname.endswith(".docs/instructions.md"):
                answer = fcontent
                break
    elif flag == "solution":
        for fname, fcontent in one["contents"].items():
            if fname in one["config"]["solution"]:
                md_prefix = ext2md_prefix(fname.split(".")[-1])
                if md_prefix == "":
                    answer += f"{fname}\n```{md_prefix}\n{fcontent}\n```\n"
                else:
                    answer += f"{fname}\n```{md_prefix}\n{fcontent}\n```\n"
    elif flag == "test":
        for fname, fcontent in one["contents"].items():
            if fname in one["config"]["test"]:
                md_prefix = ext2md_prefix(fname.split(".")[-1])
                if md_prefix == "":
                    answer += f"{fname}\n```{md_prefix}\n{fcontent}\n```\n"
                else:
                    answer += f"{fname}\n```{md_prefix}\n{fcontent}\n```\n"
    return answer

def sample_data_2_sample_data_str(sample_data):
    if len(sample_data) == 0:
        return ""
    sample_data_str_template = "## Question Example {index_placeholder}:\n\n### Project Name\n\n{project_name_placeholder}\n\n### Question Description\n\n{question_description_placeholder}\n\n### Answer File With Dependencies\n\n{answer_placeholder}\n\n### Unit Test File\n\n{unit_test_placeholder}"
    sample_data_str = "Here are some question examples to give you inspiration:\n"
    for i, one in enumerate(sample_data):
        project_name = split_sample_data_by_flag(one, "project_name")
        question_description = split_sample_data_by_flag(one, "instruction")
        answer = split_sample_data_by_flag(one, "solution")
        unit_test = split_sample_data_by_flag(one, "test")
        sample_data_str += sample_data_str_template.format(index_placeholder=i+1, project_name_placeholder=project_name, question_description_placeholder=question_description, answer_placeholder=answer, unit_test_placeholder=unit_test)
    return sample_data_str

def task_worker(task_args):
    objs = task_args.get("objs", [])
    language = task_args.get("language", "")
    sample_seed_data = random.sample(objs, random.randint(1, 3))
    sample_format_data = random.sample([obj for obj in objs if obj["repo"] == language], 1)
    model = "gemini-2.0-flash"
    result = {
        "source_ids": {
            "seed": [one["id"] for one in sample_seed_data],
            "format": [one["id"] for one in sample_format_data]
        },
        "source_messages": {
            "question": [],
            "project_name": []
        },
        "source_models": {
            "question": model,
            "project_name": model
        },
        "language": language
    }

    system_prompt = "Act as a high-level programming competition question setter and take requests for generating a new code problem.\n\n1. Make sure your code problem concise but complete.\n2. Make sure your code problem difficult and challenging."
    question_instruction_prompt_template = """Please generate a challenging and sophisticated {language} coding problem. Consider incorporating these elements to increase complexity from question example inspiration:

- Advanced data structures (trees, graphs, heaps)
- Multiple edge cases and constraints
- Optimization requirements
- Real-world practical scenarios
- System design aspects
- Algorithmic efficiency requirements
- Multiple valid approaches with different trade-offs

Make sure the difficulty is as high as possible, similar to the leetcode Hard level.

Please **only** describe the question clearly but challenge the solver with interesting constraints and requirements. Do not include any project name, code signature, answer, unit test or any other things at this stage.

{sample_data_str}

Now, begin!"""

    project_name_instruction_prompt_template = """Now, present the name of this {language} problem with snake case and keep it short and concise by using 1-3 words, like "hello_world". Please generate the name in the following format:

```
project_name
```

Please **only** generate the name in the above format. Do not include any question description, code signature, answer, unit test or any other things at this stage. Now, begin!"""

    question_chat_messages = [
        {"role": "user", "content": system_prompt},
        {"role": "user", "content": question_instruction_prompt_template.format(sample_data_str=sample_data_2_sample_data_str(sample_seed_data), language=language)},
    ]
    question_response = chat(chat_args={"messages": question_chat_messages, "model": model, "temperature": 0.8})
    if question_response.startswith("Retry"):
        raise Exception("Question generation failed")
    question_chat_messages.append({"role": "assistant", "content": question_response})
    result["source_messages"]["question"] = question_chat_messages
    
    project_name_chat_messages = [
        {"role": "user", "content": system_prompt},
        {"role": "user", "content": question_instruction_prompt_template.format(sample_data_str=sample_data_2_sample_data_str(sample_format_data), language=language)},
        {"role": "assistant", "content": question_response},
        {"role": "user", "content": project_name_instruction_prompt_template.format(language=language)},
    ]
    project_name_response = chat(chat_args={"messages": project_name_chat_messages, "model": model, "temperature": 0.8})
    if project_name_response.startswith("Retry"):
        raise Exception("Project name generation failed")
    project_name_chat_messages.append({"role": "assistant", "content": project_name_response})
    result["source_messages"]["project_name"] = project_name_chat_messages
    return result

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", "-input_path", type=str, default="./pipelines/generate/dataset/all/xxxxx.jsonl")
    parser.add_argument("--output_path", "-output_path", type=str, default="./pipelines/generate/dataset/question_and_name/")
    parser.add_argument("--workers", "-workers", type=int, default=1)
    parser.add_argument("--target_python", "-target_python", type=int, default=1)
    parser.add_argument("--target_rust", "-target_rust", type=int, default=1)
    parser.add_argument("--target_java", "-target_java", type=int, default=1)
    parser.add_argument("--target_go", "-target_go", type=int, default=1)
    parser.add_argument("--target_javascript", "-target_javascript", type=int, default=1)
    parser.add_argument("--target_cpp", "-target_cpp", type=int, default=1)
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
    main_args.target = {
        "python": main_args.target_python,
        "rust": main_args.target_rust,
        "java": main_args.target_java,
        "go": main_args.target_go,
        "javascript": main_args.target_javascript,
        "cpp": main_args.target_cpp
    }
    for language, times in main_args.target.items():
        for i in range(times):
            task_queue.append(
                {
                    "language": language,
                    "objs": objs
                }
            )

    random.shuffle(task_queue)
    task_bar = tqdm.tqdm(total=len(task_queue), desc=f"Job Running {main_args.workers} workers")
    batch_size = 20  # 每100个结果写入一次
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
                    write_jsonl_file(output_objs, os.path.join(main_args.output_path, os.path.basename(main_args.input_path)), format="a")
                    output_objs.clear()
                if error_objs:
                    write_jsonl_file(error_objs, os.path.join(main_args.output_path, os.path.basename(main_args.input_path).replace(".jsonl", "_error.jsonl")), format="a")
                    error_objs.clear()
    task_bar.close()

if __name__ == "__main__":
    main()

