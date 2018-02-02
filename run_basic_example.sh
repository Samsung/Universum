#!/usr/bin/env bash

export SOURCE_DIR=../examples
mkdir -p temp
cd temp

echo -e "\nRun using 'basic_config.py'\n"
rm -rf artifacts/

universum -vt none -lcp basic_config.py


echo -e "\nRun using 'if_env_set_config.py'\n"
rm -rf artifacts/

export IS_X64=false
export PLATFORM=B

universum -vt none -lcp if_env_set_config.py
