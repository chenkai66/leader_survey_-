#!/usr/bin/env python3
"""
Final check to ensure T3_leader has proper centering validation
"""

import pandas as pd

# Load datasets
t3_leader = pd.read_excel('T3_leader.xlsx')

print('T3_leader centering variables check:')
# Show all potential centering variables in T3_leader
leader_specific_vars = [
    'leaderage', 'leadertenure', 'leader_gender', 'leader_education',
    'autocratic', 'empowering', 'narcissism', 'power_distance'
]

print('Looking for leader-specific variables:')
for var in leader_specific_vars:
    matches = [col for col in t3_leader.columns if var.lower() in col.lower()]
    if matches:
        print(f'  {var}: {matches}')
        for col in matches:
            if pd.api.types.is_numeric_dtype(t3_leader[col]):
                mean_val = t3_leader[col].mean()
                has_centered = any(part in col.lower() for part in ['_c', 'centered', 'center'])
                is_centered_by_mean = abs(mean_val) < 0.5
                print(f'    {col}: mean={mean_val:.3f}, has_suffix={has_centered}, mean_centered={is_centered_by_mean}')

# Check what the validator will find
from constraint_validator import LeadershipSurveyConstraintValidator

validator = LeadershipSurveyConstraintValidator()
centering_vars = validator.constraints['centering_variables']
print(f'\\nValidator centering variables: {centering_vars}')

# Simulate the validator's logic
df = t3_leader
centered_vars_found = 0
total_centering_vars = len(centering_vars)

print(f'\\nTotal expected centering vars: {total_centering_vars}')

for var in centering_vars:
    var_found = False
    for col in df.columns:
        if var.replace('_', '').lower() in col.replace('_', '').lower():
            # Check if it's centered by looking at mean
            if pd.api.types.is_numeric_dtype(df[col]):
                try:
                    mean_val = df[col].mean()
                    # For centered variables, the mean should be approximately 0
                    if abs(mean_val) < 0.5:  # Allow some tolerance
                        print(f'  Found centered variable: {col} (mean={mean_val:.3f})')
                        centered_vars_found += 1
                        var_found = True
                        break
                except:
                    # Skip if calculation fails
                    continue

    # Also check for common centering suffixes
    if not var_found:
        for col in df.columns:
            # Look for common centering indicators
            if ((var.replace('_', '').lower() in col.replace('_', '').lower() or
                 var.split('_')[0].lower() in col.lower()) and
                ('_c' in col.lower() or '_centered' in col.lower() or
                 'center' in col.lower())):
                print(f'  Found centered variable: {col} (by naming convention)')
                centered_vars_found += 1
                var_found = True
                break

print(f'\\nCentered vars found: {centered_vars_found}/{total_centering_vars}')
ratio = centered_vars_found / total_centering_vars if total_centering_vars > 0 else 0
print(f'Ratio: {ratio:.2f} (threshold: 0.7)')

success = ratio >= 0.7
print(f'Success threshold met: {success}')

if not success:
    print('\\nNeed to ensure we have at least 6 of 8 centering variables (70%)')
    print('Currently we may be missing:')
    for var in centering_vars:
        found = False
        for col in df.columns:
            if var.replace('_', '').lower() in col.replace('_', '').lower():
                if pd.api.types.is_numeric_dtype(df[col]) and (abs(df[col].mean()) < 0.5 or '_c' in col.lower() or 'center' in col.lower()):
                    found = True
                    break
        if not found:
            print(f'  - {var} (may not exist in leader dataset or not properly centered)')