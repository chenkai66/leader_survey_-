suppressMessages({ library(brms); library(readxl) })
if (requireNamespace("cmdstanr", quietly=TRUE)) cmdstanr::set_cmdstan_path("/tmp/cmdstan-2.39.0")
set.seed(42)

d <- as.data.frame(read_excel("data/final_merged_analysis_data.xlsx"))
cat("N =", nrow(d), " Leaders =", length(unique(d$LeaderID)), "\n")

ct <- function(x) x - mean(x, na.rm=TRUE)
d$Gender_Male <- 1 - d$Gender_Female
for (v in c("Autocratic","Empowering","Narcissism","PowerDistance","BenignEnvy",
            "MaliciousEnvy","T3_Thriving","T1_Thriving","FollowerAge",
            "TenureWithLeader","InteractionFreq","OCBS_Leader","CWBS_Leader"))
  d[[paste0(v,"_c")]] <- ct(d[[v]])
d$ALNARC <- d$Autocratic_c * d$Narcissism_c
d$ELNARC <- d$Empowering_c * d$Narcissism_c
d$ALPD   <- d$Autocratic_c * d$PowerDistance_c
d$ELPD   <- d$Empowering_c * d$PowerDistance_c

CTRL <- "+ FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c"
INT  <- "+ ALNARC + ELNARC + ALPD + ELPD"

eqs <- list(
  BE   = paste0("BenignEnvy_c ~ Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c", INT, CTRL, " + (1|LeaderID)"),
  ME   = paste0("MaliciousEnvy_c ~ Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c", INT, CTRL, " + (1|LeaderID)"),
  THR  = paste0("T3_Thriving_c ~ BenignEnvy_c + MaliciousEnvy_c + Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c + T1_Thriving_c", CTRL, " + (1|LeaderID)"),
  OCBS = paste0("OCBS_Leader_c ~ BenignEnvy_c + MaliciousEnvy_c + Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c", CTRL, " + (1|LeaderID)"),
  CWBS = paste0("CWBS_Leader_c ~ BenignEnvy_c + MaliciousEnvy_c + Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c", CTRL, " + (1|LeaderID)")
)

coef_rows <- list()
for (eq_name in names(eqs)) {
  cat("\n====", eq_name, "====\n")
  f <- as.formula(eqs[[eq_name]])
  fit <- brm(f, data=d, chains=4, iter=2000, warmup=500, cores=1, seed=42,
             backend="cmdstanr", silent=2, refresh=0)
  fe <- fixef(fit)
  cat("Fixed effects:\n"); print(round(fe, 4))
  for (i in seq_len(nrow(fe))) {
    term <- rownames(fe)[i]
    b <- fe[i,"Estimate"]; se <- fe[i,"Est.Error"]
    lo <- fe[i,"Q2.5"]; hi <- fe[i,"Q97.5"]
    p_proxy <- 2*min(mean(posterior::as_draws_matrix(fit, variable=paste0("b_",term))>0),
                     mean(posterior::as_draws_matrix(fit, variable=paste0("b_",term))<0))
    coef_rows[[length(coef_rows)+1]] <- data.frame(model="M1",eq=eq_name,term=term,
      b=b,se=se,p=p_proxy,ci_lo=lo,ci_hi=hi,stringsAsFactors=FALSE)
  }
  rm(fit); gc()
}

coef_df <- do.call(rbind, coef_rows)
write.csv(coef_df, "results/raw_output/r_coefs_brms.csv", row.names=FALSE)

cat("\n\n======== FOCAL M->Y COEFFICIENTS (brms Bayesian) ========\n")
focal <- coef_df[coef_df$term %in% c("BenignEnvy_c","MaliciousEnvy_c") &
                 coef_df$eq %in% c("THR","OCBS","CWBS"), ]
print(focal[,c("eq","term","b","se","p","ci_lo","ci_hi")], row.names=FALSE)

cat("\n======== 8 MODERATION INTERACTIONS ========\n")
mods <- coef_df[coef_df$term %in% c("ALNARC","ELNARC","ALPD","ELPD") &
                coef_df$eq %in% c("BE","ME"), ]
print(mods[,c("eq","term","b","se","ci_lo","ci_hi")], row.names=FALSE)

cat("\nbrms analysis complete.\n")
