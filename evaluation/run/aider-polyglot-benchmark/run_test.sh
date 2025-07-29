#!/bin/bash

#############################################################################################################################################
# BENCHMARK WORK SETUP, Customized for LiveRepoReflection, Compatible with Aider Polyglot Benchmark
# "aider-polyglot-benchmark"


# EVALUATION OUTPUT DIR
OUTPUT_DIR="LiveRepoReflection/evaluation/evaluation-output/aider-polyglot-benchmark"
# OPENAI API BASE URL
CUSTOM_OPENAI_API_BASE="http://127.0.0.1:8000/v1/"
# OPENAI COMPATIBLE MODEL NAME 
MODEL_NAME="Deepseek-V3"
# OPENAI API KEY
CUSTOM_OPENAI_API_KEY="sk-abc123"
# BENCHMARK MULTI-THREADS NUM
THREADS_NUM=20
# MODEL MAX TOKENS
MODEL_MAX_LEN=8192
# BENCHMARK PYTHON SCRIPT PATH
BENCHMARK_PYTHON_SCRIPT_PATH="benchmark/benchmark.py"
# PROXY ON BENCHMARK AND LARGE LANGUAGE MODELS, OPTION: off (default), stream, non_stream
PROXY_MODE="off"
# ENABLE PROXY HACK DATA FEATURE, OPTION: off (default), on
HACK_PROXY="on"
# AIDER YAML EXTRA PARAMS
AIDER_PARAMS='{"extra_params":{"max_tokens":8192}}'

RUN_TEST_DIR="LiveRepoReflection/evaluation/"
TEST_SCRIPT_DIR="run/aider-polyglot-benchmark/test.sh"

echo "RUN_TEST_DIR: ${RUN_TEST_DIR}"
echo "TEST_SCRIPT_DIR: ${TEST_SCRIPT_DIR}"
echo "MODEL_NAME: ${MODEL_NAME}"
echo "OUTPUT_DIR: ${OUTPUT_DIR}"
echo "CUSTOM_OPENAI_API_BASE: ${CUSTOM_OPENAI_API_BASE}"
echo "CUSTOM_OPENAI_API_KEY: ${CUSTOM_OPENAI_API_KEY}"
echo "THREADS_NUM: ${THREADS_NUM}"
echo "MODEL_MAX_LEN: ${MODEL_MAX_LEN}"
echo "BENCHMARK_PYTHON_SCRIPT_PATH: ${BENCHMARK_PYTHON_SCRIPT_PATH}"
echo "PROXY_MODE: ${PROXY_MODE}"
echo "HACK_PROXY: ${HACK_PROXY}"
echo "AIDER_PARAMS: ${AIDER_PARAMS}"

cd ${RUN_TEST_DIR}
bash ${TEST_SCRIPT_DIR} ${MODEL_NAME} ${OUTPUT_DIR} ${CUSTOM_OPENAI_API_BASE} ${CUSTOM_OPENAI_API_KEY} ${THREADS_NUM} ${MODEL_MAX_LEN} ${BENCHMARK_PYTHON_SCRIPT_PATH} ${PROXY_MODE} ${HACK_PROXY} ${AIDER_PARAMS}

