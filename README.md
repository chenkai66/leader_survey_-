# Leadership Survey Data - Study 3

Simulated 3-wave longitudinal survey data for a leadership study examining how autocratic vs. empowering leadership styles affect subordinate envy and downstream outcomes.

## File Manifest

### Data Files
- `T1_raw.xlsx` / `T1_cleaned.xlsx` - Wave 1 (90 leaders, followers rate leadership + thriving)
- `T2_raw.xlsx` / `T2_cleaned.xlsx` - Wave 2 (85 leaders, followers rate envy)
- `T3_leader_raw.xlsx` / `T3_leader_cleaned.xlsx` - Wave 3 leader-rated (79 leaders rate OCBS/CWBS)
- `T3_follower_raw.xlsx` / `T3_follower_cleaned.xlsx` - Wave 3 follower-rated (T3 thriving + self-rated outcomes)
- `final_merged_analysis_data.xlsx` - Final merged dataset (438 rows, 79 leaders)

### Model Output Files
- `Model1.xlsx` - Main analysis (with controls)
- `Model2.xlsx` - No-controls robustness check
- `Model3.xlsx` - Follower-rated outcome source robustness check
- `measurement appendix.xlsx` - MCFA model comparison table
- `ICC空模型.xlsx` - Null-model ICC results
- `YUYU样本量变化.xlsx` - Sample attrition across waves

### Code
- `data_generator.py` - Generates all simulated data
- `constraint_validator.py` - Validates all requirements are met
- `fill_templates.py` - Fills model output templates with results
- `analysis_code.R` - R analysis code (multilevel path models, ICC, Monte Carlo CI)
- `mcfa_mplus_syntax.inp` - Mplus syntax for MCFA (five/four/three/two factor models)

### Reference Documents
- `complete_project_record.md` - Full client conversation record
- `comprehensive_requirements_document.md` - Detailed requirements specification

### Source Materials (read-only)
- `原始客户提供文件/` - Original measurement plan and research info
- `第一轮结果后客户反馈/` - Updated templates from client
- `第一轮交付结果/` - First round results (reference only)

## Usage

```bash
# Generate all data
python data_generator.py

# Validate constraints
python constraint_validator.py

# Fill model output templates
python fill_templates.py
```

## Study Design

- 3-wave longitudinal: T1 (90 leaders) -> T2 (85 leaders) -> T3 (79 leaders)
- Leader-subordinate nested structure (min 3 subordinates per leader)
- Two-level random-intercept multilevel path model
- MCFA for measurement validation (Mplus required)
- Grand-mean centering for continuous predictors in hypothesis-testing models
