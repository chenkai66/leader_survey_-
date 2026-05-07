# R Script for Leadership Survey Data Analysis
# Implements the statistical requirements specified in the project

# Load required libraries
library(lme4)
library(semTools)
library(lavaan)
library(dplyr)
library(tidyr)

# Function to calculate ICC for null models
calculate_null_model_icc <- function(data, dv, group_var) {
  # Fit null model (intercept only with random effects)
  null_model <- lmer(as.formula(paste(dv, "~ 1 + (1|", group_var, ")")), data = data)

  # Extract variance components
  var_components <- as.data.frame(VarCorr(null_model))
  between_var <- var_components$vcov[var_components$grp == group_var]
  residual_var <- var_components$vcov[var_components$grp == "Residual"]

  # Calculate ICC
  icc <- between_var / (between_var + residual_var)

  return(list(
    icc = icc,
    between_variance = between_var,
    within_variance = residual_var,
    model = null_model
  ))
}

# Function to perform centering as specified
perform_centering <- function(data, variables_to_center, type = "grand_mean") {
  centered_data <- data

  for (var in variables_to_center) {
    if (var %in% colnames(data)) {
      if (type == "grand_mean") {
        centered_data[[var]] <- data[[var]] - mean(data[[var]], na.rm = TRUE)
      } else if (type == "group_mean") {
        # Group mean centering would require grouping variable specification
        stop("Group mean centering requires specification of grouping variable")
      }
    }
  }

  return(centered_data)
}

# Function to create composite parcels according to theory
create_theoretical_parcels <- function(data) {
  # Example for Empowering Leadership parcels
  # EMPP1 = mean(EMP1, EMP2, EMP3)
  # EMPP2 = mean(EMP4, EMP5, EMP6)
  # EMPP3 = mean(EMP7, EMP8, EMP9)
  # EMPP4 = mean(EMP10, EMP11, EMP12)

  if(all(c("EMP1", "EMP2", "EMP3") %in% colnames(data))) {
    data$EMPP1 <- rowMeans(data[, c("EMP1", "EMP2", "EMP3")], na.rm = TRUE)
  }

  if(all(c("EMP4", "EMP5", "EMP6") %in% colnames(data))) {
    data$EMPP2 <- rowMeans(data[, c("EMP4", "EMP5", "EMP6")], na.rm = TRUE)
  }

  if(all(c("EMP7", "EMP8", "EMP9") %in% colnames(data))) {
    data$EMPP3 <- rowMeans(data[, c("EMP7", "EMP8", "EMP9")], na.rm = TRUE)
  }

  if(all(c("EMP10", "EMP11", "EMP12") %in% colnames(data))) {
    data$EMPP4 <- rowMeans(data[, c("EMP10", "EMP11", "EMP12")], na.rm = TRUE)
  }

  # Example for Thriving parcels
  # THRP1 = mean(THR1, THR3, R_THR5)
  # THRP2 = mean(THR2, THR4)
  # THRP3 = mean(THR6, THR8, R_THR10)
  # THRP4 = mean(THR7, THR9)

  if(all(c("THR1", "THR3", "R_THR5") %in% colnames(data))) {
    data$THRP1 <- rowMeans(data[, c("THR1", "THR3", "R_THR5")], na.rm = TRUE)
  }

  if(all(c("THR2", "THR4") %in% colnames(data))) {
    data$THRP2 <- rowMeans(data[, c("THR2", "THR4")], na.rm = TRUE)
  }

  if(all(c("THR6", "THR8", "R_THR10") %in% colnames(data))) {
    data$THRP3 <- rowMeans(data[, c("THR6", "THR8", "R_THR10")], na.rm = TRUE)
  }

  if(all(c("THR7", "THR9") %in% colnames(data))) {
    data$THRP4 <- rowMeans(data[, c("THR7", "THR9")], na.rm = TRUE)
  }

  return(data)
}

# Function to create dummy variables
create_dummy_variables <- function(data, categorical_vars) {
  for (var in categorical_vars) {
    if (var %in% colnames(data)) {
      # Assuming the variable has levels that need to be converted to dummies
      # This is a simplified approach - actual implementation may vary based on variable nature
      levels <- unique(data[[var]])
      levels <- levels[!is.na(levels)]

      # Create dummy variables for all levels except the first (baseline)
      for (i in 2:length(levels)) {
        dummy_name <- paste(var, "_", levels[i], sep="")
        data[[dummy_name]] <- ifelse(data[[var]] == levels[i], 1, 0)
      }
    }
  }
  return(data)
}

# Function for Multilevel CFA (MCFA) - using a simplified approach
# Note: Full MCFA requires special packages like lavaan with multilevel capabilities
run_mcfa <- function(data, model_syntax, cluster_var) {
  # Convert to long format if needed for multilevel analysis
  # This is a simplified example - full MCFA in R has limitations
  # compared to Mplus for complex multilevel models

  # lavaan multilevel model syntax
  fit <- sem(model_syntax,
             data = data,
             cluster = cluster_var,
             se = "robust",
             estimator = "MLR")

  return(fit)
}

# Model 1: Main analysis with controls
fit_model1 <- function(data) {
  # This is a placeholder - actual model specification would depend on variables
  model1_syntax <- '
    # Within-level factors
    Autocratic_W =~ aut1_w + aut2_w + aut3_w
    Empowering_W =~ emp1_w + emp2_w + emp3_w
    Envy_W =~ ben1_w + ben2_w + mal1_w + mal2_w
    Thriving_W =~ thr1_w + thr2_w + thr3_w

    # Between-level factors
    Autocratic_B =~ aut1_b + aut2_b + aut3_b
    Empowering_B =~ emp1_b + emp2_b + emp3_b
    Envy_B =~ ben1_b + ben2_b + mal1_b + mal2_b
    Thriving_B =~ thr1_b + thr2_b + thr3_b

    # Path relationships
    Envy_W ~ Autocratic_W + Empowering_W
    Thriving_W ~ Envy_W + Autocratic_W + Empowering_W

    Envy_B ~ Autocratic_B + Empowering_B
    Thriving_B ~ Envy_B + Autocratic_B + Empowering_B
  '

  # This assumes you have prepared the data appropriately for multilevel analysis
  # Actual implementation would need to address the clustering structure
  return(model1_syntax)
}

# Model 2: No-controls version
fit_model2 <- function(data) {
  # Similar to Model 1 but without control variables
  model2_syntax <- '
    # Same as Model 1 but excluding control paths
    # This would be adjusted based on the specific model requirements
  '

  return(model2_syntax)
}

# Model 3: Robustness check with follower-rated outcomes
fit_model3 <- function(data) {
  # Replace leader-rated OCBS/CWBS with follower-rated versions
  model3_syntax <- '
    # Modified model using follower-rated outcomes
    # Specific adjustments would depend on variable availability
  '

  return(model3_syntax)
}

# Function to run Monte Carlo simulation for confidence intervals
monte_carlo_ci <- function(model_fit, n_replications = 20000) {
  # This would implement Monte Carlo simulation for indirect effects
  # The actual implementation would depend on the specific model structure

  # For demonstration:
  cat("Running Monte Carlo simulation with", n_replications, "replications\n")
  # In practice, this would involve generating bootstrap samples,
  # fitting models to each sample, and calculating confidence intervals
  # for indirect effects

  # Placeholder return
  return(list(
    lower_ci = NA,
    upper_ci = NA,
    replications = n_replications
  ))
}

# Function to generate sample attrition table
generate_attrition_table <- function(original_n, cleaned_datasets, attention_check_failures,
                                   id_matching_failures, final_n) {
  attrition_df <- data.frame(
    Stage = c("Initial Contacted", "After Cleaning", "Attention Check Failures Removed",
              "ID Matching Failures Removed", "Final Analytic Sample"),
    Count = c(original_n, cleaned_datasets, cleaned_datasets - attention_check_failures,
              cleaned_datasets - attention_check_failures - id_matching_failures, final_n),
    Percentage = c(100,
                   round((cleaned_datasets/original_n)*100, 2),
                   round(((cleaned_datasets - attention_check_failures)/original_n)*100, 2),
                   round(((cleaned_datasets - attention_check_failures - id_matching_failures)/original_n)*100, 2),
                   round((final_n/original_n)*100, 2))
  )

  return(attrition_df)
}

# Main execution function
main_analysis_pipeline <- function() {
  cat("Starting leadership survey data analysis pipeline...\n")

  # Load data files
  # Note: File paths would need to be updated based on actual file locations
  # t1_data <- read.csv("T1_cleaned.csv")
  # t2_data <- read.csv("T2_cleaned.csv")
  # t3_leader_data <- read.csv("T3_leader_cleaned.csv")
  # t3_follower_data <- read.csv("T3_follower_cleaned.csv")
  # final_data <- read.csv("final_merged_analysis_data.csv")

  # Example of how to calculate ICC for null models
  # icc_results <- calculate_null_model_icc(final_data, "thriving_score", "leader_id")
  # cat("Null model ICC:", icc_results$icc, "\n")

  # Perform centering for specified variables
  # variables_to_center <- c("autocratic_leadership", "empowering_leadership",
  #                         "narcissism", "power_distance", "follower_age",
  #                         "tenure_with_leader", "interaction_freq", "T1_thriving")
  # centered_data <- perform_centering(final_data, variables_to_center)

  # Create theoretical parcels
  # data_with_parcels <- create_theoretical_parcels(centered_data)

  # Create dummy variables for categorical predictors
  # categorical_vars <- c("gender", "education_level", "position_type")  # Example
  # final_data_for_analysis <- create_dummy_variables(data_with_parcels, categorical_vars)

  # Fit models
  # model1 <- fit_model1(final_data_for_analysis)
  # model2 <- fit_model2(final_data_for_analysis)
  # model3 <- fit_model3(final_data_for_analysis)

  # Calculate Monte Carlo confidence intervals for indirect effects
  # mc_results <- monte_carlo_ci(model1, n_replications = 20000)

  # Generate sample attrition table
  # attrition_table <- generate_attrition_table(original_n = 1000, cleaned_datasets = 850,
  #                                          attention_check_failures = 20,
  #                                          id_matching_failures = 15, final_n = 790)
  # print(attrition_table)

  cat("Analysis pipeline completed.\n")
}

# Uncomment to run the main pipeline
# main_analysis_pipeline()

# Helper function to check if data meets requirements
validate_data_requirements <- function(data_list) {
  requirements_met <- list(
    has_t1 = !is.null(data_list$t1),
    has_t2 = !is.null(data_list$t2),
    has_t3_leader = !is.null(data_list$t3_leader),
    has_t3_follower = !is.null(data_list$t3_follower),
    has_final_merged = !is.null(data_list$final_merged),
    leader_education_range = if(!is.null(data_list$final_merged) && "LeaderEducation" %in% names(data_list$final_merged)) {
      edu_range_ok <- min(data_list$final_merged$LeaderEducation, na.rm = TRUE) >= 2 &&
                     max(data_list$final_merged$LeaderEducation, na.rm = TRUE) <= 5
    } else FALSE,
    each_leader_has_min_subordinates = if(!is.null(data_list$final_merged) &&
                                         "leader_id" %in% names(data_list$final_merged)) {
      min_subs <- min(table(data_list$final_merged$leader_id))
      min_subs >= 3
    } else FALSE
  )

  return(requirements_met)
}