# ============================================================
# Study 3: Complete Two-Level Path Analysis using brms
# Bayesian multivariate multilevel model (simultaneous estimation)
#
# This script fits a SINGLE brms multivariate model with all 5
# endogenous variables jointly estimated, including:
#   - 8 first-stage interactions (AL/EL × Narc/PD → BE/ME)
#   - Full mediation structure (BE/ME → THR/OCBS/CWBS)
#   - Random intercepts per leader (cluster = LeaderID)
#   - Correlated residuals across all 5 equations
#
# Output: posterior summaries equivalent to Mplus TYPE=TWOLEVEL
# coefficients, indirect effects via posterior algebra.
#
# Requirements: R 4.1+, brms, cmdstanr (or rstan)
# ============================================================
suppressMessages({
  library(brms)
  library(readxl)
  library(posterior)
})

set.seed(20260606)
ARGS <- commandArgs(trailingOnly = TRUE)
DATA <- ifelse(length(ARGS) >= 1, ARGS[1], "data/final_merged_analysis_data.xlsx")
OUTD <- ifelse(length(ARGS) >= 2, ARGS[2], "results/raw_output")

d <- as.data.frame(read_excel(DATA))
cat("Data loaded:", nrow(d), "dyads,", length(unique(d$LeaderID)), "leaders\n")

# ---- Grand-mean center all predictors ----------------------------------------
ct <- function(x) x - mean(x, na.rm = TRUE)
d$Gender_Male <- if ("Male" %in% names(d)) d$Male else (1 - d$Gender_Female)
for (v in c("Autocratic", "Empowering", "Narcissism", "PowerDistance",
            "BenignEnvy", "MaliciousEnvy", "T3_Thriving", "T1_Thriving",
            "FollowerAge", "TenureWithLeader", "InteractionFreq",
            "OCBS_Leader", "CWBS_Leader", "OCBS_Follower", "CWBS_Follower"))
  d[[paste0(v, "_c")]] <- ct(d[[v]])

# ---- Create 4 interaction terms (matches customer's Mplus DEFINE block) ------
d$ALNARC <- d$Autocratic_c * d$Narcissism_c
d$ELNARC <- d$Empowering_c * d$Narcissism_c
d$ALPD   <- d$Autocratic_c * d$PowerDistance_c
d$ELPD   <- d$Empowering_c * d$PowerDistance_c

# ---- Control variables string ------------------------------------------------
CTRL <- "FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c"

# ============================================================
# MULTIVARIATE brms MODEL (5 equations, simultaneous)
# ============================================================
cat("\n================================================================\n")
cat("Fitting multivariate brms model (5 equations, simultaneous)\n")
cat("This may take 10-30 minutes (MCMC sampling with Stan backend)\n")
cat("================================================================\n\n")

# Define 5 response formulas
bf_be <- bf(
  BenignEnvy_c ~ Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c +
    ALNARC + ELNARC + ALPD + ELPD +
    FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c +
    (1 | p | LeaderID)
)

bf_me <- bf(
  MaliciousEnvy_c ~ Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c +
    ALNARC + ELNARC + ALPD + ELPD +
    FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c +
    (1 | p | LeaderID)
)

bf_thr <- bf(
  T3_Thriving_c ~ BenignEnvy_c + MaliciousEnvy_c +
    Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c +
    T1_Thriving_c +
    FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c +
    (1 | p | LeaderID)
)

bf_ocbs <- bf(
  OCBS_Leader_c ~ BenignEnvy_c + MaliciousEnvy_c +
    Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c +
    FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c +
    (1 | p | LeaderID)
)

bf_cwbs <- bf(
  CWBS_Leader_c ~ BenignEnvy_c + MaliciousEnvy_c +
    Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c +
    FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c +
    (1 | p | LeaderID)
)

# Fit multivariate model (all 5 simultaneously with correlated random effects)
fit <- brm(
  bf_be + bf_me + bf_thr + bf_ocbs + bf_cwbs + set_rescor(TRUE),
  data = d,
  chains = 4,
  iter = 4000,
  warmup = 1000,
  cores = 4,
  seed = 42,
  backend = "cmdstanr",
  silent = 0
)

cat("\n================================================================\n")
cat("Model fitted. Extracting results...\n")
cat("================================================================\n")

# ---- Extract fixed effects (population-level) --------------------------------
fe <- fixef(fit)
cat("\n--- Fixed effects summary ---\n")
print(round(fe, 4))

# ---- Format as coefficient table (matches r_coefs.csv format) ----------------
coef_rows <- list()
for (resp in c("BenignEnvyc", "MaliciousEnvyc", "T3Thrivingc", "OCBSLeaderc", "CWBSLeaderc")) {
  eq_label <- switch(resp,
    BenignEnvyc = "BE", MaliciousEnvyc = "ME",
    T3Thrivingc = "THR", OCBSLeaderc = "OCBS", CWBSLeaderc = "CWBS")
  rows_this <- fe[grepl(paste0("^", resp, "_"), rownames(fe)), , drop = FALSE]
  for (i in seq_len(nrow(rows_this))) {
    term <- sub(paste0("^", resp, "_"), "", rownames(rows_this)[i])
    b <- rows_this[i, "Estimate"]
    se <- rows_this[i, "Est.Error"]
    ci_lo <- rows_this[i, "Q2.5"]
    ci_hi <- rows_this[i, "Q97.5"]
    # Bayesian "p-value" proxy: proportion of posterior on other side of zero
    p_proxy <- 2 * min(
      mean(as_draws_matrix(fit, variable = paste0("b_", resp, "_", term)) > 0),
      mean(as_draws_matrix(fit, variable = paste0("b_", resp, "_", term)) < 0)
    )
    coef_rows[[length(coef_rows) + 1]] <- data.frame(
      model = "M1", eq = eq_label, term = term,
      b = b, se = se, p = p_proxy,
      ci_lo = ci_lo, ci_hi = ci_hi,
      stringsAsFactors = FALSE
    )
  }
}
coef_df <- do.call(rbind, coef_rows)

cat("\n--- Focal M->Y coefficients (brms posterior) ---\n")
focal <- coef_df[coef_df$term %in% c("BenignEnvyc", "MaliciousEnvyc") &
                 coef_df$eq %in% c("THR", "OCBS", "CWBS"), ]
print(focal[, c("eq", "term", "b", "se", "p", "ci_lo", "ci_hi")], row.names = FALSE)

cat("\n--- 8 moderation interactions (brms posterior) ---\n")
mod_terms <- c("ALNARC", "ELNARC", "ALPD", "ELPD")
mods <- coef_df[coef_df$term %in% mod_terms & coef_df$eq %in% c("BE", "ME"), ]
print(mods[, c("eq", "term", "b", "se", "p", "ci_lo", "ci_hi")], row.names = FALSE)

# ---- Indirect effects via posterior algebra ----------------------------------
cat("\n--- Indirect effects (posterior product a*b) ---\n")
draws <- as_draws_matrix(fit)
compute_ie <- function(a_var, b_var, label) {
  a <- draws[, a_var]
  b <- draws[, b_var]
  ie <- a * b
  est <- median(ie)
  ci <- quantile(ie, c(0.025, 0.975))
  sig <- ifelse(ci[1] * ci[2] > 0, "*", "ns")
  cat(sprintf("  %-40s est=%+.4f  95%%CI [%+.4f, %+.4f] %s\n",
              label, est, ci[1], ci[2], sig))
}

# AL/EL -> BE -> THR/OCBS/CWBS
for (x in c("Autocratic", "Empowering")) {
  xvar <- paste0("b_BenignEnvyc_", x, "c")
  for (y in list(c("T3Thrivingc", "THR"), c("OCBSLeaderc", "OCBS"), c("CWBSLeaderc", "CWBS"))) {
    bvar <- paste0("b_", y[1], "_BenignEnvyc")
    compute_ie(xvar, bvar, paste0(x, " -> BE -> ", y[2]))
  }
}
# AL/EL -> ME -> THR/OCBS/CWBS
for (x in c("Autocratic", "Empowering")) {
  xvar <- paste0("b_MaliciousEnvyc_", x, "c")
  for (y in list(c("T3Thrivingc", "THR"), c("OCBSLeaderc", "OCBS"), c("CWBSLeaderc", "CWBS"))) {
    bvar <- paste0("b_", y[1], "_MaliciousEnvyc")
    compute_ie(xvar, bvar, paste0(x, " -> ME -> ", y[2]))
  }
}

# ---- ICC from brms (variance components) -------------------------------------
cat("\n--- ICC (from random effects) ---\n")
vc <- VarCorr(fit)
for (resp in c("BenignEnvyc", "MaliciousEnvyc", "T3Thrivingc", "OCBSLeaderc", "CWBSLeaderc")) {
  sigma_b <- vc$LeaderID$sd[resp, "Estimate"]
  sigma_w <- vc$residual__$sd[resp, "Estimate"]  # brms stores these differently
  icc_val <- sigma_b^2 / (sigma_b^2 + sigma_w^2)
  cat(sprintf("  %-20s ICC = %.3f\n", resp, icc_val))
}

# ---- Save outputs ------------------------------------------------------------
write.csv(coef_df, file.path(OUTD, "r_coefs_brms.csv"), row.names = FALSE)
cat("\n\nbrms coefficient table saved to", file.path(OUTD, "r_coefs_brms.csv"), "\n")

# ---- Model diagnostics -------------------------------------------------------
cat("\n--- MCMC diagnostics ---\n")
cat("Rhat summary:\n")
rh <- rhat(fit)
cat(sprintf("  min=%.4f  max=%.4f  all<1.01: %s\n", min(rh), max(rh), all(rh < 1.01)))
cat("Effective sample size (bulk ESS):\n")
ne <- neff_ratio(fit)
cat(sprintf("  min ratio=%.2f  median=%.2f\n", min(ne, na.rm=TRUE), median(ne, na.rm=TRUE)))

cat("\n================================================================\n")
cat("brms analysis complete.\n")
cat("================================================================\n")
