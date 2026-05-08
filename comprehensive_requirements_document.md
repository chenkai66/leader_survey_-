# Comprehensive Data Adjustment Requirements Document for Leadership Survey Study

## 1. Project Overview

### 1.1 Research Objective
This project involves adjusting survey data for a leadership study examining how autocratic versus empowering leadership styles affect subordinates' feelings of jealousy/envy, and how these feelings influence work behaviors and thriving.

### 1.2 Research Questions
- In the real workplace, do autocratic leaders and empowering leaders make subordinates have different feelings of envy toward their leaders? 
- Do these feelings further influence subordinates' thriving, helping behaviors toward leaders, and negative behaviors toward leaders?

In more colloquial terms: Why do some leaders inspire subordinates to "want to become better," while others trigger "hostility, resentment, or even retaliation"? And how do these different psychological responses ultimately affect subordinate work performance?

### 1.3 Survey Links and Wave Information
- **T1**: https://v.wjx.cn/vm/OtkYkUN.aspx# - Followers evaluate leaders (90 leaders initially)
- **T2**: https://v.wjx.cn/vm/tlbXYed.aspx# - Followers evaluate leaders (85 leaders remaining)  
- **T3**: https://v.wjx.cn/vm/eBmn806.aspx# - Follower-rated outcomes
- **T3**: https://v.wjx.cn/vm/P86fphH.aspx# - Leader-rated outcomes

## 2. Sample Size and Attrition Requirements

### 2.1 Sample Size Timeline
- **T1**: Collect data from 90 leaders' subordinates
- **T2**: Remaining 85 leaders' subordinates (5 lost from T1)  
- **T3**: Final 79 leaders, collecting data from both leaders and subordinates (6 lost from T2)
- **Final analysis**: 79 matched leader-subordinate groups (confirmed as final target)

### 2.2 Data Structure Requirements
- Each leader must have at least 3 subordinates in the final dataset
- Maintain matched leader-subordinate pairs throughout processing
- Track sample attrition across waves
- Preserve data from intermediate stages (attention check failures, ID mismatches, etc.)

## 3. Attention Check Requirements

### 3.1 Attention Check Items Locations
1. **T2 questionnaire**: malicious envy item 6
2. **T1 questionnaire**: empowering leadership item 9  
3. **T3 (follower side)**: OCBS item 7
4. **T3 (leader side)**: CWBS item 6 (in the first subordinate evaluation)

### 3.2 Processing Requirements
- Identify attention check failures during cleaning
- Remove participants who fail attention checks from final dataset
- Track attention check failure rates for attrition table

## 4. Statistical Model Requirements

### 4.1 Primary Model Approach
- **Model Type**: Two-level nested multilevel model (not cross-level)
- **Aggregation**: No aggregation required, use individual-level original scores directly
- **Framework**: Random-intercept multilevel path model on scale scores/composite scores in multilevel SEM/path framework

### 4.2 Required Models
- **Model 1**: Main analysis model (with controls)
- **Model 2**: No-controls model (robustness check)
- **Model 3**: Robustness check replacing leader-rated OCBS/CWBS with follower-rated versions

### 4.3 Centering Rules
Apply **grand-mean centering** to the following continuous variables when used in formal multilevel hypothesis-testing models:
- Autocratic leadership
- Empowering leadership
- Narcissism
- Power Distance
- Follower age
- Tenure with current leader
- Interaction frequency with leader
- T1 thriving (only when predicting T3 thriving)

**Important**: All dummy variables should NOT be centered.

Variables for descriptive statistics, correlations, reliability, ICC/rwg, CFA/MCFA should use non-centered variables.

### 4.4 Advanced Statistical Requirements
- Conduct Multilevel Confirmatory Factor Analysis (MCFA), not regular CFA (due to clustering)
- Report ICC values (null-model ICC) to confirm between-group variance and nesting
- Use Monte Carlo simulations with 20,000 replications for 95% confidence intervals of indirect and conditional indirect effects
- Implement bootstrap confidence intervals for indirect effects

## 5. Data Processing and Quality Requirements

### 5.1 Missing Data Simulation Requirements
#### T1 Processing:
- Add ~10 missing values in non-core, non-control variables (avoid core variables, mediators, outcomes, attention checks, IDs)
- Add ≤10 duplicate IDs for removal
- No missing data in core variables

#### T2 Processing:
- Zero missing values (client requirement: "T2 设置为零缺失值")
- Add ≤5 duplicate IDs with identical responses for removal
- Add 3 ID mismatches to identify and exclude

#### T3 Leader Side:
- Add ~3 missing values in non-core, non-control variables
- Add ≤1 duplicate ID for removal
- Add 1 ID mismatch to identify and exclude

### 5.2 Data Cleaning Requirements
1. Remove attention check failures
2. Remove duplicate IDs (keeping first occurrence)
3. Identify and exclude mismatched IDs
4. Retain only matched T1-T2-T3 samples
5. Ensure each leader has ≥3 subordinates in final dataset
6. Preserve intermediate datasets for transparency

## 6. Variable Creation Requirements

### 6.1 New Variables to Create
- **LeaderEducation**: Range 2-5
- Proper dummy coding for categorical variables
- Composite parcels based on theoretical dimensions (not random assignment)

### 6.2 Theoretical Parcel Creation Rules
#### Empowering Leadership Parcels:
- EMPP1 = mean(EMP1, EMP2, EMP3)
- EMPP2 = mean(EMP4, EMP5, EMP6)  
- EMPP3 = mean(EMP7, EMP8, EMP9)
- EMPP4 = mean(EMP10, EMP11, EMP12)

#### Thriving Parcels:
- THRP1 = mean(THR1, THR3, R_THR5)
- THRP2 = mean(THR2, THR4)
- THRP3 = mean(THR6, THR8, R_THR10)
- THRP4 = mean(THR7, THR9)

#### Other Constructs:
Create parcels according to established factor structure and theoretical subscales.

### 6.3 Cluster ID Requirements
- Raw leader IDs may be alphanumeric (e.g., A01L1, A02L1)
- Must create numeric CLID for Mplus compatibility
- CLID must be a 1:1 mapping from raw LeaderID
- CLID used in "CLUSTER IS CLID" statements in Mplus syntax

## 7. Output Requirements

### 7.1 Deliverable Files Structure
The final deliverables should include separate files:

#### Primary Model Outputs:
- `Model1.xlsx`: Main analysis model results (with controls)
- `Model2.xlsx`: No-controls model results (robustness check)
- `Model3.xlsx`: Alternative outcome source model results (robustness check)

#### Measurement and Validation Outputs:
- `measurement appendix.xlsx`: MCFA and CFA results for different factor models
- `ICC空模型.xlsx`: Null model ICC results for various outcomes

#### Data Files (Raw and Cleaned):
- `T1_raw.xlsx`: T1 data before cleaning
- `T1_cleaned.xlsx`: T1 data after cleaning
- `T2_raw.xlsx`: T2 data before cleaning
- `T2_cleaned.xlsx`: T2 data after cleaning
- `T3_leader_raw.xlsx`: T3 leader data before cleaning
- `T3_leader_cleaned.xlsx`: T3 leader data after cleaning
- `T3_follower_raw.xlsx`: T3 follower data before cleaning
- `T3_follower_cleaned.xlsx`: T3 follower data after cleaning
- `final_merged_analysis_data.xlsx`: Final cleaned, matched dataset ready for analysis

#### Documentation Files:
- `YUYU样本量变化.xlsx`: Sample attrition table with counts and percentages across waves

### 7.2 Analysis Code Requirements
- Complete code for running all models (R preferred, Mplus syntax where required)
- Code for MCFA with cluster adjustment
- Code for generating dummy variables
- Code for calculating theoretical composite parcels
- Code for validating all constraints are met
- Code for Monte Carlo simulations

## 8. MCFA Model Specifications (for Mplus)

### 8.1 Five-Factor Model
```
TITLE: Study 3 MCFA - Hypothesized Five-Factor Model;
VARIABLE:
  NAMES ARE CLID AUT1-AUT6 EMPP1-EMPP4 BEN1-BEN5 MAL1-MAL5 THRP1-THRP4;
  CLUSTER IS CLID;
  MISSING ARE ALL (-999);

ANALYSIS:
  TYPE = TWOLEVEL;
  ESTIMATOR = MLR;
  ITERATIONS = 10000;
  H1ITERATIONS = 10000;

MODEL:
  %WITHIN%
    AUTW BY AUT1-AUT6;
    EMPW BY EMPP1-EMPP4;
    BENW BY BEN1-BEN5;
    MALW BY MAL1-MAL5;
    THRW BY THRP1-THRP4;

  %BETWEEN%
    AUTB BY AUT1-AUT6;
    EMPB BY EMPP1-EMPP4;
    BENB BY BEN1-BEN5;
    MALB BY MAL1-MAL5;
    THRB BY THRP1-THRP4;
```

### 8.2 Four-Factor Model (Benign and Malicious Envy Combined)
Similar structure but combining benign and malicious envy into one factor.

### 8.3 Other Factor Models
Three-factor and two-factor models as alternatives for model comparison.

## 9. Quality Control and Validation Requirements

### 9.1 Constraint Validation Checklist
The data must satisfy:
- [ ] Every leader in final dataset has minimum 3 subordinates
- [ ] All attention check items properly identified and processed
- [ ] Missing values only appear in specified non-core variables
- [ ] Duplicate IDs correctly simulated and removable
- [ ] ID mismatches correctly included for exclusion
- [ ] LeaderEducation variable within range [2, 5]
- [ ] Numeric CLID created for Mplus compatibility
- [ ] Proper centering applied according to rules
- [ ] Theoretical parcels created (not random)
- [ ] All model requirements met

### 9.2 Statistical Validation
- ICC values calculated to confirm clustering effects
- MCFA conducted instead of traditional CFA due to multilevel structure
- Monte Carlo simulation used for confidence intervals
- Model comparison performed across factor models

## 10. Additional Customer Notes and Clarifications

### 10.1 Model 3 Specifics
Model 3 should be kept clean - it's only an alternative outcome source robustness model: replacing leader-rated OCBS/CWBS with follower-rated OCBS/CWBS. Other model structure and controls should remain consistent with Model 1.

### 10.2 CFA vs MCFA
Traditional CFA is insufficient due to nested data structure. MCFA (Multilevel CFA) is required to properly account for within-cluster and between-cluster variances. This is due to the requirement that "same leader's different subordinates have different ratings for these variables" causing within-cluster variation that R's Lavaan cannot handle properly.

### 10.3 Sample Attrition Tracking
- Customer has pre-filled initial contacted sample size in the YUYU样本量变化.xlsx table
- Need to fill in the cleaning stages: cleaning, attention check failures, ID matching failures, final matched sample
- This is for calculating response rates and retention rates in section F

### 10.4 Measurement Appendix Requirements
The ordinary CFA in the measurement appendix also requires cluster adjustment to account for nested data.

## 11. Expected Final Validation Process

Before delivery, run complete validation to ensure:
- All requirements from this document are satisfied
- Data quality metrics meet specifications
- Statistical models can be successfully fitted
- Sample attrition follows expected pattern
- All deliverable files are properly formatted
- Constraint validator passes all checks