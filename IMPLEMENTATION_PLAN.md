# Comprehensive Data Adjustment Requirements & Implementation Plan

## Executive Summary

This document consolidates all requirements for the leadership survey data adjustment project. The study examines how autocratic versus empowering leadership styles affect subordinates' envy feelings and subsequent work behaviors/thriving.

## Project Requirements Summary

### 1. Data Structure Requirements
- **Sample progression**: T1 (90 leaders) → T2 (85 leaders) → T3 (79 leaders for analysis)
- **Minimum subordinates per leader**: At least 3 in final dataset
- **Waves**: 
  - T1: Followers evaluate leaders
  - T2: Followers evaluate leaders (follow-up)
  - T3: Both leaders and followers provide ratings

### 2. Attention Check Items
- T2: Malicious envy item 6
- T1: Empowering leadership item 9
- T3 (follower): OCBS item 7
- T3 (leader): CWBS item 6

### 3. Statistical Model Requirements
- **Primary approach**: Two-level nested multilevel models
- **No aggregation**: Use individual-level scores directly
- **Centering**: Grand-mean centering for specified variables in hypothesis-testing models
- **MCFA**: Multilevel Confirmatory Factor Analysis (not traditional CFA)

### 4. Variable Requirements
- New variable: LeaderEducation (range 2-5)
- Dummy coding for categorical variables
- Theoretical parcel creation (not random)

### 5. Deliverables
- **Model1.xlsx**: Main analysis with controls
- **Model2.xlsx**: No-controls robustness check
- **Model3.xlsx**: Alternative outcome source (follower-rated outcomes)
- **measurement appendix.xlsx**: MCFA and CFA results
- **ICC空模型.xlsx**: Null model ICC results
- **YUYU样本量变化.xlsx**: Sample attrition table
- Separate data files: T1/T2/T3 (leader/follower) cleaned/unprocessed
- Analysis code in R and Mplus

## Implementation Approach

### Phase 1: Data Preparation
1. Generate initial datasets following sample size requirements
2. Implement attention check items as specified
3. Add missing values strategically (non-core variables only)
4. Introduce duplicate IDs for cleaning validation
5. Add ID mismatches for exclusion validation

### Phase 2: Data Processing
1. Clean data according to attention check failures
2. Remove duplicate IDs
3. Exclude mismatched IDs
4. Match T1-T2-T3 datasets
5. Verify minimum 3 subordinates per leader requirement

### Phase 3: Variable Creation
1. Apply centering rules for specified variables
2. Create theoretical parcels (not random)
3. Generate dummy variables for categorical predictors
4. Create numeric CLID from LeaderID for Mplus compatibility

### Phase 4: Statistical Analysis
1. Run MCFA models (Five-factor, four-factor, etc.)
2. Calculate null model ICC values
3. Fit primary multilevel models (Model 1-3)
4. Generate bootstrap confidence intervals using Monte Carlo

## Constraint Validation Checklist

The `constraint_validator.py` script contains automated checks for:
- [ ] Sample size preservation across waves
- [ ] Minimum subordinate count per leader (≥3)
- [ ] Attention check item presence and processing
- [ ] Proper centering application
- [ ] New variable ranges (LeaderEducation: 2-5)
- [ ] Numeric cluster ID creation
- [ ] Theoretical parcel formation
- [ ] Dummy variable coding
- [ ] Overall data integrity

## Analysis Scripts Provided

1. **`analysis_code.R`**: Primary R analysis functions for:
   - ICC calculation for null models
   - Variable centering procedures
   - Theoretical parcel creation
   - Dummy variable generation
   - Model fitting framework
   - Monte Carlo simulation for confidence intervals

2. **`mcfa_mplus_syntax.inp`**: Complete Mplus syntax for:
   - Five-factor MCFA model
   - Four-factor MCFA model (envy combination)
   - Three-factor MCFA model (leadership combination)
   - Two-factor MCFA model
   - Null model for ICC calculation
   - Main multilevel model with bootstrap confidence intervals

3. **`constraint_validator.py`**: Automated validation of all project requirements

## Quality Assurance Process

Before final delivery, run the constraint validator on all generated datasets to ensure:
- All requirements from the requirements document are satisfied
- Data quality metrics meet specifications
- Statistical models can be successfully fitted
- Sample attrition follows expected pattern
- All deliverable files are properly formatted