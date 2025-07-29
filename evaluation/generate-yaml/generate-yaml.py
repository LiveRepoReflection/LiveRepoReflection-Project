import json
from pathlib import Path
import uuid
import yaml
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, required=True)
    parser.add_argument("--aider_params", type=str, required=True)
    parser.add_argument("--yaml_output_dir", type=str, required=True)
    args = parser.parse_args()

    # 调整数据结构为列表格式
    write_yaml_args = [
        {
            "name": args.model_name,
        }
    ]

    # 下面的优先级更高，但保留已设置的extra_params
    if args.aider_params:
        # print(f"args.aider_params: {args.aider_params}")
        try:
            # 尝试解析JSON字符串
            aider_params = json.loads(args.aider_params) or {}
        except json.JSONDecodeError as e:
            try:
                # 尝试解析YAML字符串
                aider_params = json.loads("'" + args.aider_params + "'") or {}
            except json.JSONDecodeError as e:
                # print(f"Error parsing aider_params: {e}")
                # print(f"Using empty dict instead")
                aider_params = {}
        
        # 特殊处理extra_params，进行合并而不是替换
        if "extra_params" in aider_params and "extra_params" in write_yaml_args[0]:
            # 保存原始的extra_params
            original_extra_params = write_yaml_args[0]["extra_params"].copy()
            # 更新其他参数
            write_yaml_args[0].update(aider_params)
            # 合并extra_params
            write_yaml_args[0]["extra_params"].update(original_extra_params)
        else:
            # 如果没有冲突，直接更新
            write_yaml_args[0].update(aider_params)


    yaml_output_dir = Path(args.yaml_output_dir)
    yaml_output_dir.mkdir(parents=True, exist_ok=True)
    yaml_file_name = f"{uuid.uuid4()}.aider.model.settings.yml"
    yaml_file_path = yaml_output_dir / yaml_file_name
    
    # 配置 YAML dumper
    yaml.Dumper.ignore_aliases = lambda *args : True
    
    with open(yaml_file_path, "w") as f:
        yaml.dump(write_yaml_args, f, default_flow_style=False, sort_keys=False)

    print(yaml_file_path, end='')

"""
# 配合aider yaml食用，下面的测试脚本，完全不能用😊，用就炸
cd generate-yaml
python generate-yaml.py \
    --model_name "gpt-4" \
    --aider_params '{"extra_params":{"thinking":{"type":"enabled","budget_tokens":16384}}}' \
    --yaml_output_dir "./yaml_output"

cd generate-yaml
python generate-yaml.py \
    --model_name "gpt-4" \
    --aider_params '{"temperature": 0.7, "top_p": 0.9, "extra_params": {"thinking": {"type": "enabled", "budget_tokens": 16384}, "num_ctx": 0, "max_input_tokens": 0, "max_output_tokens": 0}}' \
    --yaml_output_dir "./yaml_output"
"""