#!/bin/bash
cd "$(dirname "$0")" || exit 1
export PATH="$PWD/venv/bin:$PATH"
python immich-s3-sync.py
