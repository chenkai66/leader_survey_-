#!/usr/bin/env python3
"""
Simple script to fix the centering issue in T3_leader dataset
"""

import pandas as pd
import numpy as np

# Load the T3_leader dataset
t3_leader = pd.read_excel('T3_leader.xlsx')

print('Original T3_leader shape:', t3_leader.shape)
print('Original columns with potential centering needs:')
centering_candidates = []
for col in t3_leader.columns:
    if any(keyword in col.lower() for keyword in [
        'autocratic', 'empowering', 'narcissism', 'power', 'age', 'tenure', 'interaction', 'thriving'
    ]) and pd.api.types.is_numeric_dtype(t3_leader[col]):
        mean_val = t3_leader[col].mean()
        print(f'  {col}: mean={mean_val:.3f}')
        centering_candidates.append((col, mean_val))

print(f'\nFound {len(centering_candidates)} potential candidates for centering')

# Apply centering to appropriate variables
centered_count = 0
for col, orig_mean in centering_candidates:
    if abs(orig_mean) > 0.5:  # Needs centering (mean is not close to 0)
        centered_col_name = f"{col}_C"
        t3_leader[centered_col_name] = t3_leader[col] - orig_mean
        new_mean = t3_leader[centered_col_name].mean()
        print(f'  Created {centered_col_name} with mean {new_mean:.6f}')
        centered_count += 1

print(f'\nAdded centering to {centered_count} columns')

# Save the updated dataset
t3_leader.to_excel('T3_leader.xlsx', index=False)
print('\nUpdated T3_leader.xlsx saved')