# Leadership Survey Data Adjustment Project

Data processing and adjustment project for a 3-wave longitudinal leadership study examining how autocratic vs empowering leadership affects subordinate envy, thriving, and work behaviors.

## Project Structure

### Data Files
- `T1_raw.xlsx` / `T1_cleaned.xlsx` - T1 follower survey data (90 leaders)
- `T2_raw.xlsx` / `T2_cleaned.xlsx` - T2 follower survey data (85 leaders)
- `T3_leader_raw.xlsx` / `T3_leader_cleaned.xlsx` - T3 leader-rated data (79 leaders)
- `T3_follower_raw.xlsx` / `T3_follower_cleaned.xlsx` - T3 follower-rated data (79 leaders)
- `final_merged_analysis_data.xlsx` - Final cleaned, matched dataset for analysis

### Model Output Files
- `Model1.xlsx` - Main analysis model (with controls)
- `Model2.xlsx` - No-controls model (robustness check)
- `Model3.xlsx` - Alternative outcome source model (robustness check)
- `measurement appendix.xlsx` - MCFA/CFA measurement results
- `ICC空模型.xlsx` - Null model ICC results
- `YUYU样本量变化.xlsx` - Sample attrition table

### Analysis Code
- `analysis_code.R` - R analysis functions (ICC, centering, parcels, models)
- `mcfa_mplus_syntax.inp` - Mplus syntax for MCFA and multilevel models

### Validation Scripts
- `constraint_validator.py` - Core constraint validation class
- `comprehensive_constraint_validator.py` - Extended validator (identical to core)
- `updated_validator.py` - Context-aware centering validator

### Reference Directories
- `原始客户提供文件/` - Original client-provided templates and documents
- `第一轮交付结果/` - First round delivery results
- `第一轮结果后客户反馈/` - Client feedback after first round (updated templates)

## Requirements
See `comprehensive_requirements_document.md` for full specification.
