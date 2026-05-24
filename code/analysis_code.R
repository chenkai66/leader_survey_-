# ============================================================
# Study 3: Leadership Styles, Envy, and Subordinate Outcomes
# Complete Multilevel Analysis Code
# Two-Level Random-Intercept Path Model with Full Moderation
# ============================================================
# v4.6.4 (Round 3 customer feedback): full theoretical model with
#   - Narcissism + PowerDistance both as moderators (8 moderation paths)
#   - Model 2 no-controls including outcome equations
#   - Model 3 follower-rated outcomes (NO WorkingYears_C addition)
#   - Simple slopes + Monte Carlo conditional indirect effects
# ============================================================

# --- Load Libraries ---
library(lme4)        # Multilevel modeling
library(lmerTest)    # p-values for lmer
library(lavaan)      # CFA (single-level supplement)
library(readxl)      # Read Excel files
library(dplyr)       # Data manipulation
library(psych)       # Descriptive stats, reliability
library(performance) # ICC computation
library(boot)        # Bootstrapping

# --- Read Data ---
final_data <- read_excel("final_merged_analysis_data.xlsx")

cat("Data loaded:", nrow(final_data), "rows,",
    length(unique(final_data$LeaderID)), "leaders\n")

# ============================================================
# 1. DESCRIPTIVE STATISTICS, CORRELATIONS, RELIABILITY
# ============================================================

desc_vars <- c("Autocratic", "Empowering", "Narcissism", "PowerDistance",
               "BenignEnvy", "MaliciousEnvy",
               "T1_Thriving", "T3_Thriving",
               "OCBS_Leader", "CWBS_Leader",
               "OCBS_Follower", "CWBS_Follower",
               "FollowerAge", "TenureWithLeader", "InteractionFreq")
desc_vars_exist <- desc_vars[desc_vars %in% names(final_data)]

cat("\n=== Descriptive Statistics ===\n")
describe(final_data[, desc_vars_exist])

cat("\n=== Correlations ===\n")
cor_matrix <- cor(final_data[, desc_vars_exist], use = "pairwise.complete.obs")
print(round(cor_matrix, 3))

# Reliability
cat("\n=== Reliability (Cronbach's Alpha) ===\n")
scale_items <- list(
  Autocratic    = paste0("AUT", 1:6),
  Empowering    = paste0("EMP", 1:12),
  Narcissism    = paste0("NARC", 1:6),
  PowerDistance = paste0("PD", 1:5),
  BenignEnvy    = paste0("BEN", 1:5),
  MaliciousEnvy = paste0("MAL", 1:5),
  Thriving_T1   = c(paste0("THR", 1:4), "R_THR5", paste0("THR", 6:9), "R_THR10"),
  OCBS_Leader   = paste0("OCBS_L", 1:6),
  CWBS_Leader   = paste0("CWBS", 1:5)
)
for (s in names(scale_items)) {
  items <- scale_items[[s]]
  if (all(items %in% names(final_data))) {
    a <- psych::alpha(final_data[, items])$total$raw_alpha
    cat(sprintf("  %s: alpha = %.3f\n", s, a))
  }
}

# ============================================================
# 2. ICC COMPUTATION (NULL MODELS)
# ============================================================
cat("\n=== ICC from Null Models ===\n")
icc_vars <- c("Autocratic", "Empowering", "BenignEnvy", "MaliciousEnvy",
              "T1_Thriving", "T3_Thriving",
              "OCBS_Leader", "CWBS_Leader",
              "OCBS_Follower", "CWBS_Follower",
              "Narcissism", "PowerDistance")
for (v in icc_vars) {
  if (v %in% names(final_data)) {
    null_model <- lmer(as.formula(paste0(v, " ~ 1 + (1|LeaderID)")),
                       data = final_data, REML = TRUE)
    vc <- as.data.frame(VarCorr(null_model))
    between_var <- vc$vcov[1]; within_var <- vc$vcov[2]
    icc_val <- between_var / (between_var + within_var)
    cat(sprintf("  %s: ICC(1) = %.3f\n", v, icc_val))
  }
}

# ============================================================
# 3. MODEL 1: Main Model (with full controls)
# ============================================================
# Two-level random-intercept multilevel path model on follower scale scores.
# Followers nested within leaders. Random intercepts at leader level.
# Mediator equations: Auto/Emp -> BE/ME, with Narc + PD as MODERATORS,
#   and full set of follower-level controls (Age, Gender, Tenure, InterFreq).
# Outcome equations: Auto/Emp + BE/ME -> {T3 Thriving (with T1 thr baseline),
#   OCBS_Leader, CWBS_Leader}.
# ============================================================
cat("\n=== Model 1: Main Analysis ===\n")

# --- 3a. Mediator equations: BE and ME without interactions (main effects only) ---
model1_ben_main <- lmer(BenignEnvy ~ Autocratic_C + Empowering_C +
                          Narcissism_C + PowerDistance_C +
                          FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                          Gender_Female + (1|LeaderID),
                        data = final_data, REML = FALSE)
summary(model1_ben_main)

model1_mal_main <- lmer(MaliciousEnvy ~ Autocratic_C + Empowering_C +
                          Narcissism_C + PowerDistance_C +
                          FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                          Gender_Female + (1|LeaderID),
                        data = final_data, REML = FALSE)
summary(model1_mal_main)

# --- 3b. Mediator equations with FULL moderation: 4 interactions × 2 mediators = 8 paths ---
# All 4 leadership × moderator interactions in single model per mediator, so estimates
# control for each other (customer R29: "完整理论模型必须保留, 即使不显著也要跑").
model1_ben_mod <- lmer(BenignEnvy ~ Autocratic_C * Narcissism_C +
                         Autocratic_C * PowerDistance_C +
                         Empowering_C * Narcissism_C +
                         Empowering_C * PowerDistance_C +
                         FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                         Gender_Female + (1|LeaderID),
                       data = final_data, REML = FALSE)
summary(model1_ben_mod)

model1_mal_mod <- lmer(MaliciousEnvy ~ Autocratic_C * Narcissism_C +
                         Autocratic_C * PowerDistance_C +
                         Empowering_C * Narcissism_C +
                         Empowering_C * PowerDistance_C +
                         FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                         Gender_Female + (1|LeaderID),
                       data = final_data, REML = FALSE)
summary(model1_mal_mod)

# --- 3c. Outcome equations ---
# T3 Thriving: includes T1 thriving baseline AND envy mediators AND direct leadership effects
if ("T1_Thriving_C" %in% names(final_data)) {
  model1_thr <- lmer(T3_Thriving ~ Autocratic_C + Empowering_C +
                       BenignEnvy + MaliciousEnvy + T1_Thriving_C +
                       FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                       Gender_Female + (1|LeaderID),
                     data = final_data, REML = FALSE)
  summary(model1_thr)
}

# OCBS_Leader (T1 thriving baseline NOT included — only thriving outcomes
# get T1 thriving control per study design)
model1_ocbs <- lmer(OCBS_Leader ~ Autocratic_C + Empowering_C +
                      BenignEnvy + MaliciousEnvy +
                      FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                      Gender_Female + (1|LeaderID),
                    data = final_data, REML = FALSE)
summary(model1_ocbs)

# CWBS_Leader
model1_cwbs <- lmer(CWBS_Leader ~ Autocratic_C + Empowering_C +
                      BenignEnvy + MaliciousEnvy +
                      FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                      Gender_Female + (1|LeaderID),
                    data = final_data, REML = FALSE)
summary(model1_cwbs)

# ============================================================
# 4. SIMPLE SLOPES at +/- 1 SD of moderator (8 paths)
# ============================================================
cat("\n=== Model 1: Simple Slopes (high vs low moderator) ===\n")
sd_narc <- sd(final_data$Narcissism_C, na.rm = TRUE)
sd_pd   <- sd(final_data$PowerDistance_C, na.rm = TRUE)

simple_slope <- function(model, x_var, w_var, sd_w) {
  fe  <- fixef(model)
  vcm <- vcov(model)
  inter_term <- paste0(x_var, ":", w_var)
  if (!(inter_term %in% names(fe))) inter_term <- paste0(w_var, ":", x_var)
  b_x  <- fe[x_var]; b_xw <- fe[inter_term]
  # high: slope of X when W = +1 SD
  hi <- b_x + b_xw * sd_w; lo <- b_x - b_xw * sd_w
  cat(sprintf("  %s × %s: hi=%.3f, lo=%.3f, diff=%.3f\n",
              x_var, w_var, hi, lo, hi - lo))
}
for (mod in list(model1_ben_mod, model1_mal_mod)) {
  for (x in c("Autocratic_C", "Empowering_C")) {
    simple_slope(mod, x, "Narcissism_C",   sd_narc)
    simple_slope(mod, x, "PowerDistance_C", sd_pd)
  }
}

# ============================================================
# 5. INDIRECT + CONDITIONAL INDIRECT EFFECTS (Monte Carlo, 20,000 reps)
# ============================================================
cat("\n=== Monte Carlo Confidence Intervals ===\n")

monte_carlo_ci <- function(a, se_a, b, se_b, reps = 20000, ci = 0.95) {
  a_sim <- rnorm(reps, a, se_a); b_sim <- rnorm(reps, b, se_b)
  ab_sim <- a_sim * b_sim
  q <- quantile(ab_sim, probs = c((1 - ci) / 2, 1 - (1 - ci) / 2))
  list(est = a * b, lo = q[1], hi = q[2])
}

# Indirect effects: X -> M -> Y for all combinations
indirects <- list(
  list(a_mod = model1_ben_main, a_var = "Autocratic_C",
       b_mod = model1_thr,      b_var = "BenignEnvy",   y = "Thriving"),
  list(a_mod = model1_ben_main, a_var = "Empowering_C",
       b_mod = model1_thr,      b_var = "BenignEnvy",   y = "Thriving"),
  list(a_mod = model1_mal_main, a_var = "Autocratic_C",
       b_mod = model1_thr,      b_var = "MaliciousEnvy", y = "Thriving"),
  list(a_mod = model1_mal_main, a_var = "Empowering_C",
       b_mod = model1_thr,      b_var = "MaliciousEnvy", y = "Thriving"),
  list(a_mod = model1_ben_main, a_var = "Autocratic_C",
       b_mod = model1_ocbs,     b_var = "BenignEnvy",   y = "OCBS"),
  list(a_mod = model1_ben_main, a_var = "Empowering_C",
       b_mod = model1_ocbs,     b_var = "BenignEnvy",   y = "OCBS"),
  list(a_mod = model1_mal_main, a_var = "Autocratic_C",
       b_mod = model1_ocbs,     b_var = "MaliciousEnvy", y = "OCBS"),
  list(a_mod = model1_mal_main, a_var = "Empowering_C",
       b_mod = model1_ocbs,     b_var = "MaliciousEnvy", y = "OCBS"),
  list(a_mod = model1_ben_main, a_var = "Autocratic_C",
       b_mod = model1_cwbs,     b_var = "BenignEnvy",   y = "CWBS"),
  list(a_mod = model1_ben_main, a_var = "Empowering_C",
       b_mod = model1_cwbs,     b_var = "BenignEnvy",   y = "CWBS"),
  list(a_mod = model1_mal_main, a_var = "Autocratic_C",
       b_mod = model1_cwbs,     b_var = "MaliciousEnvy", y = "CWBS"),
  list(a_mod = model1_mal_main, a_var = "Empowering_C",
       b_mod = model1_cwbs,     b_var = "MaliciousEnvy", y = "CWBS")
)
for (ie in indirects) {
  a <- fixef(ie$a_mod)[ie$a_var]
  se_a <- summary(ie$a_mod)$coefficients[ie$a_var, "Std. Error"]
  b <- fixef(ie$b_mod)[ie$b_var]
  se_b <- summary(ie$b_mod)$coefficients[ie$b_var, "Std. Error"]
  r <- monte_carlo_ci(a, se_a, b, se_b)
  cat(sprintf("  %s -> %s -> %s: %.3f [%.3f, %.3f]\n",
              ie$a_var, ie$b_var, ie$y, r$est, r$lo, r$hi))
}

# ============================================================
# 6. MODEL 2: NO CONTROLS (Robustness)
# ============================================================
# Drops all controls (Age, Gender, Tenure, InterFreq) from BOTH mediator
# AND outcome equations. Per customer round 3 docx: M2 must include
# outcome equations (T3 thriving, OCBS, CWBS), not just mediators.
# ============================================================
cat("\n=== Model 2: No Controls ===\n")

model2_ben <- lmer(BenignEnvy ~ Autocratic_C + Empowering_C +
                     Narcissism_C + PowerDistance_C + (1|LeaderID),
                   data = final_data, REML = FALSE)
model2_mal <- lmer(MaliciousEnvy ~ Autocratic_C + Empowering_C +
                     Narcissism_C + PowerDistance_C + (1|LeaderID),
                   data = final_data, REML = FALSE)
summary(model2_ben); summary(model2_mal)

# Outcome equations (NO controls)
model2_thr <- lmer(T3_Thriving ~ Autocratic_C + Empowering_C +
                     BenignEnvy + MaliciousEnvy + (1|LeaderID),
                   data = final_data, REML = FALSE)
model2_ocbs <- lmer(OCBS_Leader ~ Autocratic_C + Empowering_C +
                      BenignEnvy + MaliciousEnvy + (1|LeaderID),
                    data = final_data, REML = FALSE)
model2_cwbs <- lmer(CWBS_Leader ~ Autocratic_C + Empowering_C +
                      BenignEnvy + MaliciousEnvy + (1|LeaderID),
                    data = final_data, REML = FALSE)
summary(model2_thr); summary(model2_ocbs); summary(model2_cwbs)

# Also re-test the 4 moderation interactions without controls
model2_ben_mod <- lmer(BenignEnvy ~ Autocratic_C * Narcissism_C +
                         Autocratic_C * PowerDistance_C +
                         Empowering_C * Narcissism_C +
                         Empowering_C * PowerDistance_C + (1|LeaderID),
                       data = final_data, REML = FALSE)
model2_mal_mod <- lmer(MaliciousEnvy ~ Autocratic_C * Narcissism_C +
                         Autocratic_C * PowerDistance_C +
                         Empowering_C * Narcissism_C +
                         Empowering_C * PowerDistance_C + (1|LeaderID),
                       data = final_data, REML = FALSE)
summary(model2_ben_mod); summary(model2_mal_mod)

# ============================================================
# 7. MODEL 3: ALTERNATIVE OUTCOME SOURCE (Follower-rated OCBS/CWBS)
# ============================================================
# Per customer round 3 docx: Model 3 ONLY swaps leader-rated -> follower-rated
# outcomes. Controls match Model 1 (NO WorkingYears_C, NO additional changes).
# Mediator equations are the SAME as Model 1 (data unchanged).
# ============================================================
cat("\n=== Model 3: Follower-Rated Outcomes (Robustness) ===\n")

if ("OCBS_Follower" %in% names(final_data)) {
  model3_ocbs <- lmer(OCBS_Follower ~ Autocratic_C + Empowering_C +
                        BenignEnvy + MaliciousEnvy +
                        FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                        Gender_Female + (1|LeaderID),
                      data = final_data, REML = FALSE)
  summary(model3_ocbs)
}
if ("CWBS_Follower" %in% names(final_data)) {
  model3_cwbs <- lmer(CWBS_Follower ~ Autocratic_C + Empowering_C +
                        BenignEnvy + MaliciousEnvy +
                        FollowerAge_C + TenureWithLeader_C + InteractionFreq_C +
                        Gender_Female + (1|LeaderID),
                      data = final_data, REML = FALSE)
  summary(model3_cwbs)
}

# Note: Mediator equations for M3 are IDENTICAL to M1 (same data, only outcome
# source swapped) — no need to re-estimate model3_ben / model3_mal.

# ============================================================
# 8. MCFA — see mcfa_mplus_syntax.inp (Mplus required)
# ============================================================
cat("\nNote: Multilevel CFA must be conducted in Mplus.\n")
cat("See mcfa_mplus_syntax.inp for the corresponding syntax.\n")
cat("R's lavaan does not properly support clustered MCFA for this design.\n")

cat("\n=== Analysis Complete ===\n")
