# ============================================================
# Study 3: Leadership Styles, Envy, and Subordinate Outcomes
# Complete Analysis Code
# ============================================================

# --- Load Libraries ---
library(lme4)       # Multilevel modeling
library(lmerTest)   # p-values for lmer
library(lavaan)     # CFA (single-level)
library(readxl)     # Read Excel files
library(dplyr)      # Data manipulation
library(psych)      # Descriptive stats, reliability
library(performance) # ICC computation
library(boot)       # Bootstrapping

# --- Read Data ---
final_data <- read_excel("final_merged_analysis_data.xlsx")

cat("Data loaded:", nrow(final_data), "rows,",
    length(unique(final_data$LeaderID)), "leaders\n")

# ============================================================
# 1. DESCRIPTIVE STATISTICS AND CORRELATIONS
# ============================================================

# Key variables for descriptives (non-centered)
desc_vars <- c("Autocratic", "Empowering", "BenignEnvy", "MaliciousEnvy",
               "T1_Thriving", "T3_Thriving", "OCBS_Leader", "CWBS_Leader",
               "Narcissism", "PowerDistance", "FollowerAge", "TenureWithLeader",
               "InteractionFreq")

# Filter to existing columns
desc_vars_exist <- desc_vars[desc_vars %in% names(final_data)]

# Descriptive statistics
cat("\n=== Descriptive Statistics ===\n")
describe(final_data[, desc_vars_exist])

# Correlation matrix
cat("\n=== Correlations ===\n")
cor_matrix <- cor(final_data[, desc_vars_exist], use = "pairwise.complete.obs")
round(cor_matrix, 3)

# Reliability (Cronbach's alpha) for multi-item scales
cat("\n=== Reliability (Cronbach's Alpha) ===\n")

# Autocratic Leadership
aut_items <- paste0("AUT", 1:6)
if (all(aut_items %in% names(final_data))) {
  cat("Autocratic:", psych::alpha(final_data[, aut_items])$total$raw_alpha, "\n")
}

# Benign Envy
ben_items <- paste0("BEN", 1:5)
if (all(ben_items %in% names(final_data))) {
  cat("Benign Envy:", psych::alpha(final_data[, ben_items])$total$raw_alpha, "\n")
}

# Malicious Envy
mal_items <- paste0("MAL", 1:5)
if (all(mal_items %in% names(final_data))) {
  cat("Malicious Envy:", psych::alpha(final_data[, mal_items])$total$raw_alpha, "\n")
}

# ============================================================
# 2. ICC COMPUTATION (NULL MODELS)
# ============================================================

cat("\n=== ICC from Null Models ===\n")

icc_vars <- c("Autocratic", "Empowering", "BenignEnvy", "MaliciousEnvy",
              "T1_Thriving", "T3_Thriving", "OCBS_Leader", "CWBS_Leader",
              "Narcissism", "PowerDistance")

for (v in icc_vars) {
  if (v %in% names(final_data)) {
    formula_str <- paste0(v, " ~ 1 + (1|LeaderID)")
    null_model <- lmer(as.formula(formula_str), data = final_data, REML = TRUE)
    vc <- as.data.frame(VarCorr(null_model))
    between_var <- vc$vcov[1]
    within_var <- vc$vcov[2]
    icc_val <- between_var / (between_var + within_var)
    cat(sprintf("  %s: ICC(1) = %.3f\n", v, icc_val))
  }
}

# ============================================================
# 3. MODEL 1: Main Model (with controls)
# ============================================================

cat("\n=== Model 1: Main Analysis (Two-Level Path Model) ===\n")

# Step 1: Autocratic/Empowering -> Benign Envy
model1_ben <- lmer(BenignEnvy ~ Autocratic_C + Empowering_C +
                     FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                     Gender_Female + Narcissism_C + PowerDistance_C +
                     (1|LeaderID),
                   data = final_data, REML = FALSE)
summary(model1_ben)

# Step 2: Autocratic/Empowering -> Malicious Envy
model1_mal <- lmer(MaliciousEnvy ~ Autocratic_C + Empowering_C +
                     FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                     Gender_Female + Narcissism_C + PowerDistance_C +
                     (1|LeaderID),
                   data = final_data, REML = FALSE)
summary(model1_mal)

# Step 3: Envy -> T3 Thriving (controlling T1 thriving)
if ("T1_Thriving_C" %in% names(final_data) & "T3_Thriving" %in% names(final_data)) {
  model1_thr <- lmer(T3_Thriving ~ BenignEnvy + MaliciousEnvy +
                       T1_Thriving_C + FollowerAge_C + TenureWithLeader_C +
                       InteractionFreq_C + Gender_Female +
                       (1|LeaderID),
                     data = final_data, REML = FALSE)
  summary(model1_thr)
}

# Step 4: Envy -> OCBS (Leader-rated)
model1_ocbs <- lmer(OCBS_Leader ~ BenignEnvy + MaliciousEnvy +
                      FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                      Gender_Female +
                      (1|LeaderID),
                    data = final_data, REML = FALSE)
summary(model1_ocbs)

# Step 5: Envy -> CWBS (Leader-rated)
model1_cwbs <- lmer(CWBS_Leader ~ BenignEnvy + MaliciousEnvy +
                      FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                      Gender_Female +
                      (1|LeaderID),
                    data = final_data, REML = FALSE)
summary(model1_cwbs)

# Step 6: Moderation by Power Distance (Narcissism is treated as a mediator/predictor, NOT a moderator)
model1_mod_pd <- lmer(BenignEnvy ~ Empowering_C * PowerDistance_C +
                        Autocratic_C + FollowerAge_C + TenureWithLeader_C +
                        InteractionFreq_C + Gender_Female + Narcissism_C +
                        (1|LeaderID),
                      data = final_data, REML = FALSE)
summary(model1_mod_pd)

# ============================================================
# 4. MODEL 2: No Controls
# ============================================================

cat("\n=== Model 2: No Controls (Robustness) ===\n")

model2_ben <- lmer(BenignEnvy ~ Autocratic_C + Empowering_C + (1|LeaderID),
                   data = final_data, REML = FALSE)
model2_mal <- lmer(MaliciousEnvy ~ Autocratic_C + Empowering_C + (1|LeaderID),
                   data = final_data, REML = FALSE)
summary(model2_ben)
summary(model2_mal)

# ============================================================
# 5. MODEL 3: Alternative Outcome Source (Follower-rated OCBS/CWBS)
# ============================================================

cat("\n=== Model 3: Follower-Rated Outcomes (Robustness) ===\n")

if ("OCBS_Follower" %in% names(final_data)) {
  model3_ocbs <- lmer(OCBS_Follower ~ BenignEnvy + MaliciousEnvy +
                        FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                        Gender_Female +
                        (1|LeaderID),
                      data = final_data, REML = FALSE)
  summary(model3_ocbs)
}

if ("CWBS_Follower" %in% names(final_data)) {
  model3_cwbs <- lmer(CWBS_Follower ~ BenignEnvy + MaliciousEnvy +
                        FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                        Gender_Female +
                        (1|LeaderID),
                      data = final_data, REML = FALSE)
  summary(model3_cwbs)
}

# ============================================================
# 6. MONTE CARLO CI FOR INDIRECT EFFECTS (20,000 reps)
# ============================================================

cat("\n=== Monte Carlo Confidence Intervals (Indirect Effects) ===\n")

# Function to compute Monte Carlo CI for indirect effect
monte_carlo_ci <- function(a, se_a, b, se_b, reps = 20000, ci = 0.95) {
  # Draw from sampling distributions
  a_sim <- rnorm(reps, mean = a, sd = se_a)
  b_sim <- rnorm(reps, mean = b, sd = se_b)
  # Compute product (indirect effect)
  ab_sim <- a_sim * b_sim
  # Get CI
  lower <- (1 - ci) / 2
  upper <- 1 - lower
  ci_bounds <- quantile(ab_sim, probs = c(lower, upper))
  point_est <- a * b
  return(list(estimate = point_est, lower = ci_bounds[1], upper = ci_bounds[2]))
}

# Example: Autocratic -> Malicious Envy -> CWBS
a_path <- fixef(model1_mal)["Autocratic_C"]
se_a <- summary(model1_mal)$coefficients["Autocratic_C", "Std. Error"]
b_path <- fixef(model1_cwbs)["MaliciousEnvy"]
se_b <- summary(model1_cwbs)$coefficients["MaliciousEnvy", "Std. Error"]

mc_result <- monte_carlo_ci(a_path, se_a, b_path, se_b, reps = 20000)
cat(sprintf("  Autocratic -> Mal Envy -> CWBS: %.3f [%.3f, %.3f]\n",
            mc_result$estimate, mc_result$lower, mc_result$upper))

# Example: Empowering -> Benign Envy -> Thriving
a_path2 <- fixef(model1_ben)["Empowering_C"]
se_a2 <- summary(model1_ben)$coefficients["Empowering_C", "Std. Error"]
b_path2 <- fixef(model1_thr)["BenignEnvy"]
se_b2 <- summary(model1_thr)$coefficients["BenignEnvy", "Std. Error"]

mc_result2 <- monte_carlo_ci(a_path2, se_a2, b_path2, se_b2, reps = 20000)
cat(sprintf("  Empowering -> Ben Envy -> Thriving: %.3f [%.3f, %.3f]\n",
            mc_result2$estimate, mc_result2$lower, mc_result2$upper))

cat("\nNote: MCFA must be conducted in Mplus (see mcfa_mplus_syntax.inp)\n")
cat("R's lavaan does not properly support multilevel CFA for this data structure.\n")

# ============================================================
# 7. SAVE RESULTS
# ============================================================

cat("\n=== Analysis Complete ===\n")
cat("Key output files expected from Mplus: MCFA fit indices\n")
cat("All R-based results printed above.\n")
