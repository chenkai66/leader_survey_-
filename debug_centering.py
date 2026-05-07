#!/usr/bin/env python3
"""
Debug the centering validation issue in T3_leader
"""

import pandas as pd
import numpy as np

# Load T3_leader dataset
t3_leader = pd.read_excel('T3_leader.xlsx')

print('T3_leader dataset info:')
print(f'Shape: {t3_leader.shape}')
print(f'Columns: {t3_leader.columns.tolist()}')

# Look for centering variables as defined in the validator
centering_vars = [
    'autocratic_leadership',
    'empowering_leadership',
    'narcissism',
    'power_distance',
    'follower_age',
    'tenure_with_current_leader',
    'interaction_frequency_with_leader',
    'T1_thriving'  # only when predicting T3 thriving
]

print('\\nLooking for centering variables:')
found_vars = []
for var in centering_vars:
    print(f'\\nSearching for: {var}')
    # Find columns that match this variable name
    matches = []
    for col in t3_leader.columns:
        if var.replace('_', '').lower() in col.replace('_', '').lower():
            matches.append(col)

    if matches:
        print(f'  Found matching columns: {matches}')
        for col in matches:
            if pd.api.types.is_numeric_dtype(t3_leader[col]):
                mean_val = t3_leader[col].mean()
                print(f'    {col}: mean = {mean_val:.3f}')
                # Check if it's centered
                if abs(mean_val) < 0.5:
                    print(f'      -> Identified as centered (mean < 0.5)')
                    found_vars.append(col)
                else:
                    print(f'      -> Not centered (mean >= 0.5)')
    else:
        print(f'  No matching columns found for {var}')

print(f'\\nFound {len(found_vars)} centered variables: {found_vars}')

# Also check for common centering indicators regardless of the original variable names
print('\\nChecking for variables with common centering indicators:')
centered_by_name = []
for col in t3_leader.columns:
    if ('_c' in col.lower() or '_centered' in col.lower() or 'center' in col.lower()) and pd.api.types.is_numeric_dtype(t3_leader[col]):
        mean_val = t3_leader[col].mean()
        centered_by_name.append((col, mean_val))
        print(f'  {col}: mean = {mean_val:.3f} (identified by name)')

print(f'\\nFound {len(centered_by_name)} variables by naming convention')