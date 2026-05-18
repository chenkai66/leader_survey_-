#!/bin/bash
# End-to-end pipeline. Run from project root.
set -e
cd "$(dirname "$0")"
python3.8 code/data_generator.py
python3.8 code/inject_signal.py
python3.8 code/fill_templates.py
python3.8 code/fill_master_templates.py
python3.8 code/constraint_validator.py
python3.8 code/audit.py
