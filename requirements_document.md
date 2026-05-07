# Data Adjustment Requirements Document for Leadership Survey Study

## 1. Project Overview

This project involves adjusting survey data for a leadership study examining how autocratic versus empowering leadership styles affect subordinates' feelings of jealousy/envy, and how these feelings influence work behaviors and thriving.

### Research Question:
In the real workplace, do autocratic leaders and empowering leaders make subordinates have different feelings of envy toward their leaders? Do these feelings further influence subordinates' thriving, helping behaviors toward leaders, and negative behaviors toward leaders?

In more colloquial terms: Why do some leaders inspire subordinates to "want to become better," while others trigger "hostility, resentment, or even retaliation"? And how do these different psychological responses ultimately affect subordinate work performance?

## 2. Data Structure & Sample Requirements

### 2.1 Sample Size Timeline:
- T1: Collect data from 90 leaders' subordinates
- T2: Remaining 85 leaders' subordinates (5 lost from T1)
- T3: Final 79 leaders, collecting data from both leaders and subordinates (6 lost from T2)
- Final analysis: 79 matched leader-subordinate groups (confirmed as final target)

### 2.2 Data Structure Requirements:
- Each leader must have at least 3 subordinates in the final dataset
- Maintain matched leader-subordinate pairs throughout processing
- Track sample attrition across waves

## 3. Questionnaire Information

### 3.1 Survey Links:
- T1: https://v.wjx.cn/vm/OtkYkUN.aspx#
- T2: https://v.wjx.cn/vm/tlbXYed.aspx#
- T3: https://v.wjx.cn/vm/eBmn806.aspx# (follower-rated)
- T3: https://v.wjx.cn/vm/P86fphH.aspx# (leader-rated)

### 3.2 Attention Check Items:
1. T2 questionnaire: malicious envy item 6
2. T1 questionnaire: empowering leadership item 9
3. T3 (follower side): OCBS item 7
4. T3 (leader side): CWBS item 6 (in the first subordinate evaluation)

## 4. Statistical Model Requirements

### 4.1 Model Type:
- Two-level nested multilevel model (not cross-level)
- No aggregation required, use individual-level original scores directly
- Random-intercept multilevel path model on scale scores/composite scores in multilevel SEM/path framework

### 4.2 Models to Generate:
- **Model 1**: Main analysis model (controls included)
- **Model 2**: No-controls model (robustness check)
- **Model 3**: Robustness check replacing leader-rated OCBS/CWBS with follower-rated versions

### 4.3 Centering Rules:
Apply grand-mean centering to the following continuous variables when used in formal multilevel hypothesis-testing models:
- Autocratic leadership
- Empowering leadership
- Narcissism
- Power Distance
- Follower age
- Tenure with current leader
- Interaction frequency with leader
- T1 thriving (only when predicting T3 thriving)

All dummy variables should not be centered.

Variables for Descriptive statistics, correlations, reliability, ICC/rwg, CFA/MCFA should use non-centered variables.

### 4.4 Additional Statistical Requirements:
- Conduct Multilevel Confirmatory Factor Analysis (MCFA), not regular CFA (due to clustering)
- Report ICC values (null-model ICC) to confirm between-group variance and nesting
- Use Monte Carlo simulations with 20,000 replications for 95% confidence intervals of indirect and conditional indirect effects

## 5. Data Processing Requirements

### 5.1 Data Files Structure:
The final deliverables should include separate files:
1. T1 - Before cleaning / After cleaning
2. T2 - Before cleaning / After cleaning
3. T3 Leader - Before cleaning / After cleaning
4. T3 Follower - Before cleaning / After cleaning
5. Final merged analysis data (cleaned, matched, attention checks passed)

### 5.2 Missing Data Simulation:
#### T1:
- Add ~10 missing values in non-core, non-control variables (avoid core variables, mediators, outcomes, attention checks, IDs)
- Add ≤10 duplicate IDs for removal
- No missing data in core variables

#### T2:
- Zero missing values in core variables
- Add ≤5 duplicate IDs with identical responses for removal
- Add 3 ID mismatches to identify and exclude
- Add 3 missing values in non-core variables only

#### T3 Leader Side:
- Add ~3 missing values in non-core, non-control variables
- Add ≤1 duplicate ID for removal
- Add 1 ID mismatch to identify and exclude

### 5.3 Cleaning Steps:
1. Remove attention check failures
2. Remove duplicate IDs
3. Identify and exclude mismatched IDs
4. Retain only matched T1-T2-T3 samples
5. Ensure each leader has ≥3 subordinates in final dataset

## 6. Output Requirements

### 6.1 Deliverable Files:
- `Model1.xlsx`: Main analysis model results
- `Model2.xlsx`: No-controls model (robustness check)
- `Model3.xlsx`: Alternative outcome source model (robustness check)
- `measurement appendix.xlsx`: MCFA and CFA results
- `ICC空模型.xlsx`: Null model ICC results
- `YUYU样本量变化.xlsx`: Sample attrition table

### 6.2 Analysis Code Requirements:
- Complete code for running all models (preferably in R, but Mplus syntax if required)
- Code for MCFA with cluster adjustment
- Code for generating dummy variables
- Code for calculating composite parcels according to theory:
  - Empowering leadership: EMPP1 = mean(EMP1, EMP2, EMP3), EMPP2 = mean(EMP4, EMP5, EMP6), etc.
  - Thriving: THRP1 = mean(THR1, THR3, R_THR5), THRP2 = mean(THR2, THR4), etc.

## 7. Variable Requirements

### 7.1 New Variables:
- `LeaderEducation`: Range 2-5
- Proper dummy coding for categorical variables

### 7.2 Composite Generation:
Generate parcels according to theoretical dimensions, not randomly:
- Empowering leadership parcels based on theoretical subscales
- Thriving parcels based on theoretical dimensions
- Other constructs according to established factor structure

## 8. Constraints and Validation Checks

### 8.1 Data Quality Constraints:
- Every leader in final dataset must have minimum 3 subordinates
- All attention check items must be properly identified and processed
- Missing values must only appear in specified non-core variables
- Duplicate IDs must be correctly simulated and identifiable
- ID mismatches must be correctly included for exclusion

### 8.2 Statistical Validity:
- ICC values must be calculated to confirm clustering effects
- MCFA must be conducted instead of traditional CFA due to multilevel structure
- Centering must be applied according to specified rules
- Monte Carlo simulation must be used for confidence intervals

## 9. Special Considerations

### 9.1 Cluster ID Requirements:
- Raw leader IDs may be alphanumeric (e.g., A01L1, A02L1)
- Must create numeric CLID for Mplus compatibility
- CLID must be a 1:1 mapping from raw LeaderID
- CLID used in "CLUSTER IS CLID" statements

### 9.2 MCFA Implementation:
Due to nested data structure, traditional CFA is insufficient. MCFA (Multilevel CFA) is required to properly account for within-cluster and between-cluster variances.