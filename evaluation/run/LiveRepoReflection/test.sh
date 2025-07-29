#!/bin/bash

#############################################################################################################################################
START_TIME=$(date +%s)
START_TIME_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
ROOT_DIR=`pwd`
echo "ROOT_DIR: ${ROOT_DIR}"

# Environment Setup, Inherited from Aider Polyglot Benchmark `Dockerfile`, Modified for LiveRepoReflection

## python 3.11
apt-get update && apt-get install -y \
    software-properties-common \
    cmake \
    libboost-all-dev \
    rsync \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    ca-certificates-java \
    openjdk-21-jdk \
    libtbb-dev \
    && rm -rf /var/lib/apt/lists/*

## Make python 3.11 default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
# Ensure pip consistency
if [ ! -L /usr/bin/pip ]; then
    ln -sf /usr/bin/pip3 /usr/bin/pip
fi

## Install Go with architecture detection
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    GOARCH="amd64";
elif [ "$ARCH" = "aarch64" ]; then
    GOARCH="arm64";
else
    false;
fi
curl -L "https://golang.org/dl/go1.21.5.linux-$GOARCH.tar.gz" -o go.tar.gz
tar -C /usr/local -xzf go.tar.gz
rm go.tar.gz
export PATH="/usr/local/go/bin:${PATH}"

## Install Rust
curl -fsSL https://sh.rustup.rs -o /tmp/rustup.sh
chmod +x /tmp/rustup.sh && /tmp/rustup.sh -y && rm /tmp/rustup.sh
export PATH="/root/.cargo/bin:${PATH}"

## Install Node.js and dependencies
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
rm -rf /var/lib/apt/lists/*
mkdir -p /npm-install
cd /npm-install && echo "Changed to /npm-install"
npm init -y
npm install \
    jest \
    @babel/core@7.25.2 \
    @exercism/babel-preset-javascript@0.2.1 \
    @exercism/eslint-config-javascript@0.6.0 \
    @types/jest@29.5.12 \
    @types/node@20.12.12 \
    babel-jest@29.6.4 \
    core-js@3.37.1 \
    eslint@8.49.0

#############################################################################################################################################
# File System Setup, Inherited from Aider Polyglot Benchmark `Dockerfile`, Modified for LiveRepoReflection
## script => LiveRepoReflection => LiveRepoReflection-execution/LiveRepoReflection-execution-${uuid} => /LiveRepoReflection-execution-${uuid}
cd ${ROOT_DIR} && echo "Changed to ROOT_DIR: ${ROOT_DIR}"
mkdir -p LiveRepoReflection-execution
DIR_UUID=LiveRepoReflection-$(date +%Y%m%d-%H%M%S)-$(cat /proc/sys/kernel/random/uuid)
LOCAL_SCRIPT_BASENAME=LiveRepoReflection-execution-${DIR_UUID}
LOCAL_SCRIPT_DIR=${ROOT_DIR}/LiveRepoReflection-execution/${LOCAL_SCRIPT_BASENAME}
# DOCKER_SCRIPT_DIR=/${LOCAL_SCRIPT_BASENAME}
## do not use uuid actual value
DOCKER_SCRIPT_DIR=/LiveRepoReflection-execution
# mkdir -p /tmp/empty_dir && rsync -ahP --delete-before /tmp/empty_dir/ ${LOCAL_SCRIPT_DIR}/ && rm -rf /tmp/empty_dir
rm -rf ${LOCAL_SCRIPT_DIR}
if [ ! -d "LiveRepoReflection" ]; then
    echo "Error: LiveRepoReflection directory not found in ${ROOT_DIR}"
    exit 1
fi
# rsync -ahP --delete-before LiveRepoReflection/ ${LOCAL_SCRIPT_DIR}/
cp -r LiveRepoReflection/ ${LOCAL_SCRIPT_DIR}/
if [ $? -ne 0 ]; then
    echo "Error: rsync failed to copy LiveRepoReflection directory"
    exit 1
fi
# Remove existing link if it exists
[ -L ${DOCKER_SCRIPT_DIR} ] && rm -f ${DOCKER_SCRIPT_DIR}
ln -sf ${LOCAL_SCRIPT_DIR} ${DOCKER_SCRIPT_DIR}
echo "Linking ${LOCAL_SCRIPT_DIR} (DIR_NAME: ${LOCAL_SCRIPT_BASENAME}) to ${DOCKER_SCRIPT_DIR} (DIR_NAME: ${DOCKER_SCRIPT_DIR})"
if [ ! -d ${DOCKER_SCRIPT_DIR} ]; then
    echo "Error: Failed to create symbolic link ${DOCKER_SCRIPT_DIR}"
    exit 1
fi

LOCAL_BENCHMARK_DIR=${LOCAL_SCRIPT_DIR}/tmp.benchmarks.LiveRepoReflection
# DOCKER_BENCHMARK_DIR=/${DOCKER_SCRIPT_DIR}/tmp.benchmarks.LiveRepoReflection
DOCKER_BENCHMARK_DIR=/benchmarks
mkdir -p ${LOCAL_BENCHMARK_DIR}
# Remove existing link if it exists
[ -L ${DOCKER_BENCHMARK_DIR} ] && rm -f ${DOCKER_BENCHMARK_DIR}
ln -sf ${LOCAL_BENCHMARK_DIR} ${DOCKER_BENCHMARK_DIR}
echo "Linking ${LOCAL_BENCHMARK_DIR} (DIR_NAME: ${LOCAL_BENCHMARK_DIR}) to ${DOCKER_BENCHMARK_DIR} (DIR_NAME: ${DOCKER_BENCHMARK_DIR})"

pip3 install --no-cache-dir --upgrade pip uv -i https://pypi.tuna.tsinghua.edu.cn/simple
echo "Checking DOCKER_SCRIPT_DIR before uv installation: ${DOCKER_SCRIPT_DIR}"
if [ ! -d ${DOCKER_SCRIPT_DIR} ]; then
    echo "Error: DOCKER_SCRIPT_DIR ${DOCKER_SCRIPT_DIR} does not exist, cannot install LiveRepoReflection package"
    exit 1
fi
if [ ! -f ${DOCKER_SCRIPT_DIR}/setup.py ] && [ ! -f ${DOCKER_SCRIPT_DIR}/pyproject.toml ]; then
    echo "Warning: No setup.py or pyproject.toml found in ${DOCKER_SCRIPT_DIR}, skipping package installation"
else
    uv pip install --system --no-cache-dir -e ${DOCKER_SCRIPT_DIR}[dev] -i https://pypi.tuna.tsinghua.edu.cn/simple
fi
git config --global --add safe.directory ${DOCKER_SCRIPT_DIR}

## Python Lib
# python -m pip install -U --upgrade-strategy only-if-needed aider-chat -i https://pypi.tuna.tsinghua.edu.cn/simple
uv pip install --system --no-cache-dir jsonlines tqdm lox pandas matplotlib imgcat typer pyyaml fastapi aiofiles openai uvicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "LOCAL_SCRIPT_BASENAME: ${LOCAL_SCRIPT_BASENAME}"
echo "LOCAL_SCRIPT_DIR: ${LOCAL_SCRIPT_DIR}"
echo "DOCKER_SCRIPT_DIR: ${DOCKER_SCRIPT_DIR}"
echo "LOCAL_BENCHMARK_DIR: ${LOCAL_BENCHMARK_DIR}"
echo "DOCKER_BENCHMARK_DIR: ${DOCKER_BENCHMARK_DIR}"

# Environment Variables Setup, Inherited from Aider Polyglot Benchmark `docker.sh`
export OPENAI_API_KEY=$OPENAI_API_KEY
export HISTFILE=${DOCKER_SCRIPT_DIR}/.bash_history
export PROMPT_COMMAND='history -a'
export HISTCONTROL=ignoredups
export HISTSIZE=10000
export HISTFILESIZE=20000
export AIDER_DOCKER=1
export AIDER_BENCHMARK_DIR=${DOCKER_BENCHMARK_DIR}


#############################################################################################################################################
# BENCHMARK WORK SETUP, Customized for LiveRepoReflection, Compatible with Aider Polyglot Benchmark

# OPENAI COMPATIBLE MODEL NAME 
MODEL_NAME=$1
MODEL_NAME=${MODEL_NAME:-"Qwen2.5-Coder-32B-Instruct"}
# EVALUATION OUTPUT DIR
OUTPUT_DIR=$2
OUTPUT_DIR=${OUTPUT_DIR:-"evaluation-LiveRepoReflection-output"}
OUTPUT_DIR_FOR_THIS_RUN=${OUTPUT_DIR}/${MODEL_NAME}_${DIR_UUID}
mkdir -p ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR_FOR_THIS_RUN}
# OPENAI API BASE URL
CUSTOM_OPENAI_API_BASE=$3
CUSTOM_OPENAI_API_BASE=${CUSTOM_OPENAI_API_BASE:-"http://127.0.0.1:8000/v1/"}
# OPENAI API KEY
CUSTOM_OPENAI_API_KEY=$4
CUSTOM_OPENAI_API_KEY=${CUSTOM_OPENAI_API_KEY:-"token-abc123"}
export OPENAI_API_KEY=${CUSTOM_OPENAI_API_KEY:-"token-abc123"}
# BENCHMARK MULTI-THREADS NUM
THREADS_NUM=$5
THREADS_NUM=${THREADS_NUM:-10}
# MODEL MAX TOKENS
MODEL_MAX_LEN=$6
MODEL_MAX_LEN=${MODEL_MAX_LEN:-8192}
# BENCHMARK PYTHON SCRIPT PATH
BENCHMARK_PYTHON_SCRIPT_PATH=$7
BENCHMARK_PYTHON_SCRIPT_PATH=${BENCHMARK_PYTHON_SCRIPT_PATH:-"benchmark/benchmark.py"}
# PROXY ON BENCHMARK AND LARGE LANGUAGE MODELS, OPTION: off, stream, non_stream
PROXY_MODE=$8
PROXY_MODE=${PROXY_MODE:-"off"}
# ENABLE PROXY HACK DATA FEATURE, OPTION: off (default), on
HACK_PROXY=$9
HACK_PROXY=${HACK_PROXY:-"off"}
# AIDER YAML EXTRA PARAMS
AIDER_PARAMS=${10}
AIDER_PARAMS=${AIDER_PARAMS:-'{"extra_params":{"max_tokens":8192}}'}

# litellm need service provider, so we use openai prefix default
API_MODEL_NAME=openai/${MODEL_NAME}

# if HACK_PROXY is on, use proxy to hack data, target is PROXY_URL, http://127.0.0.1:58080/forward/v1
if [ "$HACK_PROXY" = "on" ]; then
    export OPENAI_API_BASE=http://127.0.0.1:58080/forward/v1
# otherwise, use target URL
else
    export OPENAI_API_BASE=${CUSTOM_OPENAI_API_BASE}
fi

echo "OPENAI_API_BASE: ${OPENAI_API_BASE}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY}"
echo "MODEL_NAME: ${MODEL_NAME}, API_MODEL_NAME: ${API_MODEL_NAME}"
echo "OUTPUT_DIR: ${OUTPUT_DIR}"
echo "OUTPUT_DIR_FOR_THIS_RUN: ${OUTPUT_DIR_FOR_THIS_RUN}"
echo "THREADS_NUM: ${THREADS_NUM}"
echo "MODEL_MAX_LEN: ${MODEL_MAX_LEN}"
echo "BENCHMARK_PYTHON_SCRIPT_PATH: ${BENCHMARK_PYTHON_SCRIPT_PATH}"
echo "PROXY_MODE: ${PROXY_MODE}"
echo "HACK_PROXY: ${HACK_PROXY}"
echo "AIDER_PARAMS: ${AIDER_PARAMS}"


#############################################################################################################################################
# BENCHMARK RUN

## YAML GENERATION
echo "API_MODEL_NAME: ${API_MODEL_NAME}"
echo "AIDER_PARAMS: ${AIDER_PARAMS}"
echo "OUTPUT_DIR_FOR_THIS_RUN: ${OUTPUT_DIR_FOR_THIS_RUN} (yaml output dir)"

MODEL_SETTINGS_YML_PATH=$(python3 ${ROOT_DIR}/generate-yaml/generate-yaml.py \
    --model_name "${API_MODEL_NAME}" \
    --aider_params "${AIDER_PARAMS}" \
    --yaml_output_dir "${OUTPUT_DIR_FOR_THIS_RUN}")

echo "MODEL_SETTINGS_YML_PATH: ${MODEL_SETTINGS_YML_PATH}"

## LLM API PROXY
### proxy server on http://127.0.0.1:58080/forward/v1
PROXY_OUTPUT_DIR=${OUTPUT_DIR_FOR_THIS_RUN}/proxy
mkdir -p ${PROXY_OUTPUT_DIR}
EXPOSE_HOST=127.0.0.1
EXPOSE_PORT=58080
CUSTOM_OPENAI_API_BASE=${CUSTOM_OPENAI_API_BASE:-"http://127.0.0.1:8000/v1/"}

echo "Starting proxy server..."
echo "PROXY_OUTPUT_DIR: ${PROXY_OUTPUT_DIR}"
echo "EXPOSE_HOST: ${EXPOSE_HOST}"
echo "EXPOSE_PORT: ${EXPOSE_PORT}"
echo "CUSTOM_OPENAI_API_BASE: ${CUSTOM_OPENAI_API_BASE}"

python3 ${ROOT_DIR}/proxy/app.py \
    --output_path ${PROXY_OUTPUT_DIR} \
    --expose_host ${EXPOSE_HOST} \
    --expose_port ${EXPOSE_PORT} \
    --url ${CUSTOM_OPENAI_API_BASE} \
    --mode ${PROXY_MODE} --compatible \
    > ${PROXY_OUTPUT_DIR}/standard_io.log 2>&1 &

## BENCHMARK SCRIPT RUN
run_benchmark() {
    local EDIT_FORMAT=$1
    TASK_FOLDER=${OUTPUT_DIR_FOR_THIS_RUN}/results/${EDIT_FORMAT}
    mkdir -p ${TASK_FOLDER}

    echo "EDIT_FORMAT: ${EDIT_FORMAT}"
    echo "BENCHMARK_PYTHON_SCRIPT_PATH: ${BENCHMARK_PYTHON_SCRIPT_PATH}"
    echo "MODEL_NAME: ${MODEL_NAME} => (DIR_NAME: ${MODEL_NAME})"
    echo "API_MODEL_NAME: ${API_MODEL_NAME}"
    echo "THREADS_NUM: ${THREADS_NUM}"
    echo "MODEL_SETTINGS_YML_PATH: ${MODEL_SETTINGS_YML_PATH}"
    echo "Attempting to change to DOCKER_SCRIPT_DIR: ${DOCKER_SCRIPT_DIR}"
    if [ ! -d ${DOCKER_SCRIPT_DIR} ]; then
        echo "Error: DOCKER_SCRIPT_DIR ${DOCKER_SCRIPT_DIR} does not exist"
        return 1
    fi
    cd ${DOCKER_SCRIPT_DIR} && echo "Changed to DOCKER_SCRIPT_DIR: ${DOCKER_SCRIPT_DIR}" || {
        echo "Error: Failed to change to DOCKER_SCRIPT_DIR: ${DOCKER_SCRIPT_DIR}"
        return 1
    }
    python3 -u ${BENCHMARK_PYTHON_SCRIPT_PATH} ${MODEL_NAME} \
        --graphs \
        --new \
        --model ${API_MODEL_NAME} \
        --edit-format ${EDIT_FORMAT} \
        --threads ${THREADS_NUM} \
        --tries 2 \
        --read-model-settings ${MODEL_SETTINGS_YML_PATH} \
        --exercises-dir LiveRepoReflection > ${TASK_FOLDER}/log.log 2>&1

    echo "BENCHMARK PID: $!"

    # extract the required lines from log.log and use awk to extract the corresponding values
    pass_rate_1=$(tail -n 100 "${TASK_FOLDER}/log.log" | grep 'pass_rate_1' | awk '{print $2}' || echo "0")
    pass_rate_2=$(tail -n 100 "${TASK_FOLDER}/log.log" | grep 'pass_rate_2' | awk '{print $2}' || echo "0")
    percent_cases_well_formed=$(tail -n 100 "${TASK_FOLDER}/log.log" | grep 'percent_cases_well_formed' | awk '{print $2}' || echo "0")
    edit_format=$(tail -n 100 "${TASK_FOLDER}/log.log" | grep 'edit_format' | awk '{print $2}' || echo "")
    # Calculate fix_weight properly using awk for floating point calculations
    fix_weight=$(awk -v p1="$pass_rate_1" -v p2="$pass_rate_2" 'BEGIN {
        if (p2 + 0 == 0) {
            print "0";
        } else {
            result = (p2 - p1) / p2 * 100;
            printf "%.1f", result;
        }
    }')
    
    json_content=$(cat <<EOF
{
    "pass@1": $pass_rate_1,
    "pass@2": $pass_rate_2,
    "well_format": $percent_cases_well_formed,
    "fix_weight": $fix_weight
}
EOF
)
    echo "$json_content" > "${TASK_FOLDER}/results.json"
}

merge_results() {
    local results_json="${OUTPUT_DIR_FOR_THIS_RUN}/results.json"
    local whole_json="${OUTPUT_DIR_FOR_THIS_RUN}/results/whole/results.json"
    local diff_json="${OUTPUT_DIR_FOR_THIS_RUN}/results/diff/results.json"
    # check if the files exist
    if [[ ! -f "${whole_json}" || ! -f "${diff_json}" ]]; then
        echo "Error: One of the results.json files does not exist."
        exit 1
    fi
    # extract values from whole.json
    local whole_pass_rate_1=$(grep 'pass@1' "${whole_json}" | awk '{print $2}' | tr -d ',' || echo "0")
    local whole_pass_rate_2=$(grep 'pass@2' "${whole_json}" | awk '{print $2}' | tr -d ',' || echo "0")
    local whole_percent=$(grep 'well_format' "${whole_json}" | awk '{print $2}' | tr -d ',' || echo "0")
    local whole_fix_weight=$(grep 'fix_weight' "${whole_json}" | awk '{print $2}' | tr -d ',' || echo "0")

    # Ensure fix_weight values are valid numbers
    if [[ -z "$whole_fix_weight" || ! "$whole_fix_weight" =~ ^-?[0-9]+\.?[0-9]*$ ]]; then
        whole_fix_weight=0
    fi

    # extract values from diff.json
    local diff_pass_rate_1=$(grep 'pass@1' "${diff_json}" | awk '{print $2}' | tr -d ',' || echo "0")
    local diff_pass_rate_2=$(grep 'pass@2' "${diff_json}" | awk '{print $2}' | tr -d ',' || echo "0")
    local diff_percent=$(grep 'well_format' "${diff_json}" | awk '{print $2}' | tr -d ',' || echo "0")
    local diff_fix_weight=$(grep 'fix_weight' "${diff_json}" | awk '{print $2}' | tr -d ',' || echo "0")

    # Ensure fix_weight values are valid numbers
    if [[ -z "$diff_fix_weight" || ! "$diff_fix_weight" =~ ^-?[0-9]+\.?[0-9]*$ ]]; then
        diff_fix_weight=0
    fi

    # create merged JSON content
    cat <<EOF > "${results_json}"
{
    "test_name": "LiveRepoReflection",
    "test_history_dir": "${DOCKER_BENCHMARK_DIR}",
    "test_output_dir": "${OUTPUT_DIR_FOR_THIS_RUN}",
    "test_model_name": "${MODEL_NAME}",
    "test_start_time": "${START_TIME_HUMAN}",
    "test_end_time": "${END_TIME_HUMAN}",
    "test_total_time": "${TOTAL_TIME}",
    "results": {
        "whole": {
            "pass@1": ${whole_pass_rate_1},
            "pass@2": ${whole_pass_rate_2},
            "well_format": ${whole_percent},
            "fix_weight": ${whole_fix_weight}
        },
        "diff": {
            "pass@1": ${diff_pass_rate_1},
            "pass@2": ${diff_pass_rate_2},
            "well_format": ${diff_percent},
            "fix_weight": ${diff_fix_weight}
        }
    }
}
EOF

    echo "Results have been written to ${results_json}"
}

# parallel run two tasks driven by two edit format
echo "Parallel Benchmarking ${MODEL_NAME}... (whole/diff)"
run_benchmark whole &
WHOLE_PID=$!
run_benchmark diff &
DIFF_PID=$!

echo "Waiting for WHOLE_PID: $WHOLE_PID and DIFF_PID: $DIFF_PID to complete..."
wait $WHOLE_PID $DIFF_PID || true
echo "Background processes completed."


# remove the link but not the directory
rm -rf ${DOCKER_SCRIPT_DIR} ${DOCKER_BENCHMARK_DIR}

END_TIME=$(date +%s)
END_TIME_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
TOTAL_TIME=$((END_TIME - START_TIME))

echo "END_TIME: ${END_TIME_HUMAN} (${END_TIME})"
echo "START_TIME: ${START_TIME_HUMAN} (${START_TIME})"
echo "TOTAL_TIME: ${TOTAL_TIME} seconds"

merge_results

echo "Benchmarking ${MODEL_NAME} on LiveRepoReflection... Done"