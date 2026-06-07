#!/bin/bash
# End-to-end pipeline. Run from project root.
set -e
cd "$(dirname "$0")"
python code/data_generator.py
python code/inject_signal.py
python code/fill_templates.py
python code/fill_master_templates.py
python code/constraint_validator.py
python code/audit.py
