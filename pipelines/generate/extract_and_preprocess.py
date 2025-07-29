import os
import json
import uuid
import copy

repos = ["cpp", "go", "java", "javascript", "python", "rust"]
aider_ai_repos_path = "./pipelines/spider/repos/data/{repo}/exercises/practice"
aider_ai_repos_output_path = "./pipelines/generate/dataset/all/{repo}.jsonl"

ployglot_benchmark_path = "./evaluation/LiveRepoReflection/tmp.benchmarks/polyglot-benchmark/{repo}/exercises/practice"
ployglot_benchmark_output_path = "./pipelines/generate/dataset/ployglot-benchmark/{repo}.jsonl"

path = aider_ai_repos_path
outpath = aider_ai_repos_output_path

if not os.path.exists(os.path.dirname(outpath)):
    os.makedirs(os.path.dirname(outpath))

def try_read_file(file_path, file_name):
    encodings = ['utf-8', 'latin-1', 'gbk', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                decoded_content = content.decode(encoding)
                return decoded_content
        except UnicodeDecodeError:
            continue
    
    print(f"Warning: All encoding attempts failed, cannot read file {file_name}")
    return None

is_ployglot_benchmark_count = {}
not_is_ployglot_benchmark_count = {}

keep_flag_count = {
    "keep": 0,
    "drop": 0
}

for repo in repos:
    repo_datas = []
    print(f"Processing {repo}...")
    repo_path = path.format(repo=repo)
    items = os.listdir(repo_path)
    folders = [item for item in items if os.path.isdir(os.path.join(repo_path, item))]

    polyglot_benchmark_repo_path = ployglot_benchmark_path.format(repo=repo)
    polyglot_benchmark_folders = os.listdir(polyglot_benchmark_repo_path)

    for folder in folders:
        folder_path = os.path.join(repo_path, folder)
        if folder in polyglot_benchmark_folders:
            is_ployglot_benchmark = True
            is_ployglot_benchmark_count[repo] = is_ployglot_benchmark_count.get(repo, 0) + 1
        else:
            is_ployglot_benchmark = False
            not_is_ployglot_benchmark_count[repo] = not_is_ployglot_benchmark_count.get(repo, 0) + 1
        repo_datas_item = {
            "id": "seed-" + str(uuid.uuid4()),
            "is_ployglot_benchmark": is_ployglot_benchmark,
            "repo": repo,
            "folder": folder,
            "config": {},   
            "contents": {}
        }
        config_path = os.path.join(folder_path, ".meta/config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                repo_datas_item["config"] = config["files"]
                for file_tag, file_list in repo_datas_item["config"].items():
                    new_file_list = []
                    for file_name in file_list:
                        new_file_list.append(folder + "/" + file_name)
                    repo_datas_item["config"][file_tag] = new_file_list
                repo_datas_item["config"]["instruction"] = [folder + "/" + ".docs/instructions.md"]
        else:
            continue
        for root, dirs, files in os.walk(folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if os.path.exists(file_path):
                    content = try_read_file(file_path, file_name)
                    if content is not None:
                        key = os.path.relpath(file_path, folder_path)
                        key = folder + "/" + key
                        need_replace_str = """#ifdef EXERCISM_TEST_SUITE
#include <catch2/catch.hpp>
#else
#include "test/catch.hpp"
#endif"""
                        target_str = '#include "catch.hpp"'
                        content = content.replace(need_replace_str, target_str)
                        repo_datas_item["contents"][key] = content
                    if key.endswith(".docs/instructions.md"):
                        content = content.replace("# Instructions\n\n", "")
                        repo_datas_item["contents"][key] = content
                    if key.endswith(".docs/instructions.append.md"):
                        content = content.replace("# Instructions append\n\n", "")
                        repo_datas_item["contents"][key] = content

        raw_repo_datas_item = copy.deepcopy(repo_datas_item)
        keep_flag = True
        append_str = ""
        need_pop_k = ""
        for k, v in repo_datas_item["contents"].items():
            if k.endswith(".docs/instructions.append.md"):
                append_str = v
                need_pop_k = k
        if need_pop_k != "":
            repo_datas_item["contents"].pop(need_pop_k)
        for k, v in repo_datas_item["contents"].items():
            if k.endswith(".docs/instructions.md"):
                repo_datas_item["contents"][k] = v + append_str
        if repo == "python":
            python_example_filename = repo_datas_item["config"]["example"][0]
            python_solution_filename = repo_datas_item["config"]["solution"][0]
            repo_datas_item["contents"][python_solution_filename] = repo_datas_item["contents"][python_example_filename]
            repo_datas_item["contents"].pop(python_example_filename)
            repo_datas_item["config"].pop("example")
        if repo == "go":
            go_example_filename = repo_datas_item["config"]["example"][0]
            go_solution_filename = repo_datas_item["config"]["solution"][0]
            repo_datas_item["contents"][go_solution_filename] = repo_datas_item["contents"][go_example_filename]
            repo_datas_item["contents"].pop(go_example_filename)
            repo_datas_item["config"].pop("example")
            if "invalidator" in repo_datas_item["config"]:
                repo_datas_item["config"]["solution"].extend(repo_datas_item["config"]["invalidator"])
                repo_datas_item["config"].pop("invalidator")
            else:
                if "go.mod" in repo_datas_item["contents"]:
                    repo_datas_item["config"]["solution"].append("go.mod")
            if "editor" in repo_datas_item["config"]:
                repo_datas_item["config"]["test"].extend(repo_datas_item["config"]["editor"])
                repo_datas_item["config"].pop("editor")
        if repo == "java":
            for solution_filename in repo_datas_item["config"]["solution"]:
                repo_datas_item["contents"].pop(solution_filename)
            repo_datas_item["config"]["solution"] = []
            for e_fname in repo_datas_item["config"]["example"]:
                e_fname_new = e_fname.replace(".meta/src/reference/java", "src/main/java")
                repo_datas_item["contents"][e_fname_new] = repo_datas_item["contents"][e_fname]
                repo_datas_item["contents"].pop(e_fname)
            repo_datas_item["config"]["solution"] = [e_fname.replace(".meta/src/reference/java", "src/main/java") for e_fname in repo_datas_item["config"]["example"]]
            repo_datas_item["config"].pop("example")    
            repo_datas_item["config"]["solution"].extend(repo_datas_item["config"]["invalidator"])
            repo_datas_item["config"].pop("invalidator")
            if "editor" in repo_datas_item["config"]:
                repo_datas_item["config"]["solution"].extend(repo_datas_item["config"]["editor"])
                repo_datas_item["config"].pop("editor")

        if repo == "rust":
            s_fname_rs = [f_name for f_name in repo_datas_item["config"]["solution"] if f_name.endswith(".rs")][0]
            e_fname_rs = [f_name for f_name in repo_datas_item["config"]["example"] if f_name.endswith(".rs")][0]
            repo_datas_item["contents"][s_fname_rs] = repo_datas_item["contents"][e_fname_rs]
            repo_datas_item["contents"].pop(e_fname_rs)
            repo_datas_item["config"].pop("example")
        if repo == "javascript":
            if "editor" in repo_datas_item["config"]:
                keep_flag = False
                continue
            e_fname_js = [f_name for f_name in repo_datas_item["config"]["example"] if f_name.endswith(".js")][0]
            s_fname_js = [f_name for f_name in repo_datas_item["config"]["solution"] if f_name.endswith(".js")][0]
            repo_datas_item["contents"][s_fname_js] = repo_datas_item["contents"][e_fname_js]
            repo_datas_item["contents"].pop(e_fname_js)
            repo_datas_item["config"].pop("example")
            for fname, fcontent in repo_datas_item["contents"].items():
                if fname.endswith("package.json"):
                    repo_datas_item["config"]["solution"].append(fname)
                if fname.endswith("babel.config.js"):
                    repo_datas_item["config"]["solution"].append(fname)
                if fname.endswith(".npmrc"):
                    repo_datas_item["config"]["solution"].append(fname)
                if fname.endswith("jest.config.js"):
                    repo_datas_item["config"]["solution"].append(fname)
        elif repo == "cpp":
            if len(repo_datas_item["config"]["example"]) != 2 or len(repo_datas_item["config"]["solution"]) != 2:
                keep_flag = False
                continue
            h_fname_e = [f_name for f_name in repo_datas_item["config"]["example"] if f_name.endswith(".h")][0]
            h_fname_s = [f_name for f_name in repo_datas_item["config"]["solution"] if f_name.endswith(".h")][0]
            cpp_fname_e = [f_name for f_name in repo_datas_item["config"]["example"] if f_name.endswith(".cpp")][0]
            cpp_fname_s = [f_name for f_name in repo_datas_item["config"]["solution"] if f_name.endswith(".cpp")][0]
            repo_datas_item["contents"][cpp_fname_s] = repo_datas_item["contents"][cpp_fname_e]
            repo_datas_item["contents"].pop(cpp_fname_e)
            repo_datas_item["contents"][h_fname_s] = repo_datas_item["contents"][h_fname_e]
            repo_datas_item["contents"].pop(h_fname_e)
            repo_datas_item["config"].pop("example")
            pop_fnames = []
            add_dic = {}
            for fname, fcontent in repo_datas_item["contents"].items():
                if fname.endswith("tests-main.cpp"):
                    pop_fnames.append(fname)
                    new_fname = fname.replace("test/tests-main.cpp", "tests-main.cpp")
                    add_dic[new_fname] = fcontent
                if fname.endswith("catch.hpp"):
                    pop_fnames.append(fname)
                    new_fname = fname.replace("test/catch.hpp", "catch.hpp")
                    add_dic[new_fname] = fcontent
            for fname in pop_fnames:
                repo_datas_item["contents"].pop(fname)
            for fname, fcontent in add_dic.items():
                repo_datas_item["contents"][fname] = fcontent
        if keep_flag:
            keep_flag_count["keep"] += 1
            repo_datas.append(repo_datas_item)
        
    with open(outpath.format(repo=repo), "w") as f:
        for i, repo_data in enumerate(repo_datas):
            f.write(json.dumps(repo_data) + "\n")        

print("is_ployglot_benchmark_count: ", is_ployglot_benchmark_count)
print("not_is_ployglot_benchmark_count: ", not_is_ployglot_benchmark_count)
print("is_ployglot_benchmark_count: ", sum(is_ployglot_benchmark_count.values()))
print("not_is_ployglot_benchmark_count: ", sum(not_is_ployglot_benchmark_count.values()))
keep_flag_count["drop"] = sum(not_is_ployglot_benchmark_count.values()) + sum(is_ployglot_benchmark_count.values()) - keep_flag_count["keep"]
print("keep_flag_count: ", keep_flag_count)

with open(outpath.format(repo="all"), "w") as f_all:
    for repo in repos:
        with open(outpath.format(repo=repo), "r") as f:
            for line in f:
                f_all.write(line)