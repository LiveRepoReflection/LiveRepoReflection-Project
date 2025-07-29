#!/usr/bin/env python3
import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

class UnifiedCollector:
    def __init__(self, args):
        self.args = args
        self.setup_defaults()
    
    def setup_defaults(self):
        if not self.args.docker_script_dir:
            self.args.docker_script_dir = Path("/LiveRepoReflection-execution")
        if not self.args.benchmark_script:
            self.args.benchmark_script = "benchmark/benchmark_LiveRepoReflection.py"
        if not self.args.model_name:
            self.args.model_name = "Deepseek-V3"
        if not self.args.api_model_name:
            self.args.api_model_name = "openai/Deepseek-V3"
        if not self.args.model_settings_yml:
            self.args.model_settings_yml = "/dev/null"
        if not self.args.max_missing:
            self.args.max_missing = 50
        if not self.args.edit_format:
            self.args.edit_format = ['whole', 'diff']
    
    
    def find_test_case_dirs(self, edit_format: str, this_edit_format_benchmark_run_dir: Path) -> List[Path]:
        test_dirs = []
        for test_case_dir in this_edit_format_benchmark_run_dir.glob("*/exercises/practice/*/*"):
            if test_case_dir.is_dir():
                test_dirs.append(test_case_dir)
        
        return sorted(test_dirs)

    def check_test_case_status(self, test_case_dir: Path) -> Dict:
        results_file = test_case_dir / ".aider.results.json"
        
        status = {
            "test_case": test_case_dir.name,
            "lang": test_case_dir.parts[-4],
            "results_exists": results_file.exists(),
            "results_valid": False,
            "results_complete": False,
            "results_data": None,
            "error": None
        }
        
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                
                status["results_valid"] = True
                status["results_data"] = data
                
                if "tests_outcomes" in data and data["tests_outcomes"]:
                    status["results_complete"] = True
                    
            except json.JSONDecodeError as e:
                status["error"] = f"Invalid JSON: {e}"
            except Exception as e:
                status["error"] = f"Read file error: {e}"
        
        return status

    def summarize_results(self, this_edit_format_benchmark_run_dir: Path) -> Dict:
        all_results = []
        
        if self.args.stats_languages:
            languages = [lang.strip().lower() for lang in self.args.stats_languages.split(",")]
            glob_patterns = [f"{lang}/exercises/practice/*/*/.aider.results.json" for lang in languages]
        else:
            glob_patterns = ["*/exercises/practice/*/*/.aider.results.json"]
        
        for pattern in glob_patterns:
            for fname in this_edit_format_benchmark_run_dir.glob(pattern):
                try:
                    results = json.loads(fname.read_text())
                    all_results.append(results)
                except json.JSONDecodeError:
                    print(f"JSON decode error: {fname}")
                    continue
        
        total_tests = len(list(this_edit_format_benchmark_run_dir.glob("*/exercises/practice/*/*")))
        
        try:
            tries = max(len(results.get("tests_outcomes", [])) for results in all_results if results)
        except ValueError:
            tries = 0
        
        if tries == 0:
            return {
                "total_tests": total_tests,
                "completed_tests": 0,
                "pass_rates": {},
                "error": "No valid results found"
            }
        
        passed_tests = [0] * tries
        completed_tests = 0
        total_cost = 0
        total_duration = 0
        num_malformed_responses = 0
        num_with_malformed_responses = 0
        variants = defaultdict(set)
        
        for results in all_results:
            if not results:
                continue
                
            completed_tests += 1
            tests_outcomes = results.get("tests_outcomes", [])
            
            for i, outcome in enumerate(tests_outcomes):
                if outcome:
                    for j in range(i, tries):
                        passed_tests[j] += 1
                    break
            
            total_cost += results.get("cost", 0)
            total_duration += results.get("duration", 0)
            
            malformed = results.get("num_malformed_responses", 0)
            num_malformed_responses += malformed
            if malformed > 0:
                num_with_malformed_responses += 1
            
            for key in ["model", "edit_format", "commit_hash"]:
                val = results.get(key)
                if val:
                    variants[key].add(val)
        
        pass_rates = {}
        for i in range(tries):
            if completed_tests > 0:
                pass_rates[f"pass_rate_{i+1}"] = round(100 * passed_tests[i] / completed_tests, 1)
            else:
                pass_rates[f"pass_rate_{i+1}"] = 0.0
        
        if completed_tests > 0:
            percent_well_formed = round(100 * (1.0 - num_with_malformed_responses / completed_tests), 1)
        else:
            percent_well_formed = 0.0
        
        return {
            "total_tests": total_tests,
            "completed_tests": completed_tests,
            "pass_rates": pass_rates,
            "percent_cases_well_formed": percent_well_formed,
            "total_cost": total_cost,
            "total_duration": total_duration,
            "num_malformed_responses": num_malformed_responses,
            "num_with_malformed_responses": num_with_malformed_responses,
            "variants": {k: list(v) for k, v in variants.items()}
        }

    def run_single_test_case(self, test_case_path: str, edit_format: str, this_edit_format_benchmark_run_dir: Path) -> bool:
        cmd = [
            'python3', '-u', this_edit_format_benchmark_run_dir, 
            '--model', self.args.api_model_name,
            '--edit-format', edit_format,
            '--tries', '2',
            '--read-model-settings', self.args.model_settings_yml,
            '--keywords', test_case_path.split('/')[-1],
            '--num-tests', '1',
            '--threads', '1',
            '--exercises-dir', 'LiveRepoReflection',
            self.args.model_name
        ]
        
        print(f"Run single test case: {test_case_path}")
        print(f"命令：{' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.args.docker_script_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            if result.returncode == 0:
                print(f"✓ Test case {test_case_path} completed successfully")
                return True
            else:
                print(f"✗ Test case {test_case_path} failed")
                print(f"Standard output: {result.stdout[-500:]}")
                print(f"Standard error: {result.stderr[-500:]}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ Test case {test_case_path} timed out")
            return False
        except Exception as e:
            print(f"✗ Error running test case {test_case_path}: {e}")
            return False

    def process_format(self, edit_format: str, this_edit_format_benchmark_run_dir: Path):
        print(f"\n=== Process {edit_format} format ===")
        
        test_case_dirs = self.find_test_case_dirs(edit_format, this_edit_format_benchmark_run_dir)
        
        if not test_case_dirs:
            print("No test case directories found")
            return
        
        print(f"Found {len(test_case_dirs)} test case directories")
        
        missing_tests = []
        invalid_tests = []
        completed_tests = []
        
        for test_dir in test_case_dirs:
            status = self.check_test_case_status(test_dir)
            
            if not status["results_exists"] or self.args.force_rerun:
                missing_tests.append((test_dir, status))
            elif not status["results_valid"]:
                invalid_tests.append((test_dir, status))
            elif status["results_complete"]:
                completed_tests.append((test_dir, status))
            else:
                missing_tests.append((test_dir, status))
        
        print(f"Status summary:")
        print(f"  Completed tests: {len(completed_tests)}")
        print(f"  Missing results: {len(missing_tests)}")
        print(f"  Invalid results: {len(invalid_tests)}")
        
        if self.args.mode == "collect" and not self.args.check_only and missing_tests:
            print(f"Running missing tests (edit format: {edit_format}, max {self.args.max_missing} tests)...")
            
            tests_to_run = missing_tests[:self.args.max_missing]
            success_count = 0
            
            for test_dir, _ in tests_to_run:
                rel_path = test_dir.relative_to(this_edit_format_benchmark_run_dir)
                
                if self.run_single_test_case(str(rel_path), edit_format, this_edit_format_benchmark_run_dir):
                    success_count += 1
            
            print(f"Completed {success_count}/{len(tests_to_run)} test cases")
        
        summary = self.summarize_results(this_edit_format_benchmark_run_dir)
        
        print(f"{edit_format} format results summary:")
        print(f"  Total tests: {summary['total_tests']}")
        print(f"  Completed tests: {summary['completed_tests']}")
        for key, value in summary['pass_rates'].items():
            print(f"  {key}: {value}%")
        print(f"  Well-formed cases: {summary['percent_cases_well_formed']}%")
        
        pass_rate_1 = summary['pass_rates'].get('pass_rate_1', 0)
        pass_rate_2 = summary['pass_rates'].get('pass_rate_2', 0)
        fix_weight = 0 if pass_rate_2 == 0 else round((pass_rate_2 - pass_rate_1) / pass_rate_2 * 100, 1)
        print(f"  Fix weight: {fix_weight}%")
        
        if self.args.mode == "collect" and self.args.output_file:
            results_output = {
                "pass@1": pass_rate_1,
                "pass@2": pass_rate_2,
                "well_format": summary['percent_cases_well_formed'],
                "fix_weight": fix_weight,
                "total_tests": summary['total_tests'],
                "completed_tests": summary['completed_tests'],
                "edit_format": edit_format,
                "model": self.args.model_name
            }
            
            if len(self.args.edit_format) > 1:
                output_path = self.args.output_file.parent / f"{self.args.output_file.stem}_{edit_format}{self.args.output_file.suffix}"
            else:
                output_path = self.args.output_file
            
            with open(output_path, 'w') as f:
                json.dump(results_output, f, indent=2)
            print(f"Results saved to: {output_path}")
    
    def run(self):
        self.args.benchmark_dir = self.args.benchmark_dir / "tmp.benchmarks.LiveRepoReflection"
        for edit_format in self.args.edit_format:

            this_edit_format_benchmark_run_dir = None
            for subdir in sorted(self.args.benchmark_dir.iterdir()):
                if not subdir.is_dir() or not subdir.name.startswith("20"):
                    continue
                candidate = None
                for f in subdir.glob("*/exercises/practice/*/*/.aider.results.json"):
                    candidate = f
                    break
                if candidate is not None:
                    try:
                        with open(candidate, "r") as jf:
                            data = json.load(jf)
                        if data.get("edit_format") == edit_format:
                            this_edit_format_benchmark_run_dir = subdir
                            break
                    except Exception as e:
                        print(f"Warning: Failed to read {candidate}: {e}")
                        continue
            if this_edit_format_benchmark_run_dir is None:
                raise RuntimeError(f"Failed to find edit_format={edit_format} benchmark run directory in {self.args.benchmark_dir}")

            self.process_format(edit_format, this_edit_format_benchmark_run_dir)

def main():
    parser = argparse.ArgumentParser(
        description='LiveRepoReflection benchmark result collector',
    )
    
    parser.add_argument('--mode', choices=['check', 'collect'], required=True,
                        help='Operation mode: check (only check status), collect (collect results and optionally run missing tests)')
    parser.add_argument('--benchmark-dir', type=Path, required=True,
                        help='Benchmark directory containing test cases, should be the parent directory of LiveRepoReflection-execution/LiveRepoReflection-execution-UUID/')
    parser.add_argument('--docker-script-dir', type=Path, default=Path("/LiveRepoReflection-execution"),
                        help='Docker script directory (default: /LiveRepoReflection-execution), actually the LiveRepoReflection-execution/LiveRepoReflection-execution-UUID directory')
    parser.add_argument('--benchmark-script', default="benchmark/benchmark_LiveRepoReflection.py",
                        help='Benchmark script path (default: benchmark/benchmark_LiveRepoReflection.py)')
    parser.add_argument('--model-name', default="Deepseek-V3",
                        help='Model name (default: Deepseek-V3)')
    parser.add_argument('--api-model-name', default="openai/Deepseek-V3",
                        help='API model name (default: openai/Deepseek-V3)')
    parser.add_argument('--model-settings-yml', default="/dev/null",
                        help='Model settings YAML file (default: /dev/null)')
    parser.add_argument('--edit-format', choices=['whole', 'diff'], nargs='+', default=['whole', 'diff'],
                        help='Edit format to process (default: both whole and diff)')
    parser.add_argument('--stats-languages', 
                        help='Only include specific languages (comma separated)')
    
    parser.add_argument('--output-file', type=Path,
                        help='Result output file (collect mode)')
    parser.add_argument('--check-only', action='store_true',
                        help='Only check status, do not run missing tests')
    parser.add_argument('--force-rerun', action='store_true',
                        help='Force rerun all tests')
    parser.add_argument('--max-missing', type=int, default=50,
                        help='Maximum number of missing tests to run (default: 50)')
    
    args = parser.parse_args()
    
    collector = UnifiedCollector(args)
    collector.run()

if __name__ == "__main__":
    main()