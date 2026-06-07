#!/usr/bin/env Rscript
# ============================================================
# Study 3: Item-Level Multilevel CFA (TWOLEVEL)
# 自包含脚本 — 拿到任何装了 R + lavaan 的机器上直接跑
#
# 用法:
#   Rscript run_mcfa_twolevel.R [data.xlsx路径]
#
# 默认读同目录下 final_merged_analysis_data.xlsx
# 输出: mcfa_twolevel_results.csv + 屏幕打印
# 需要: R >= 4.1, lavaan, readxl, lme4
# 建议: >= 4GB RAM
# ============================================================

if (!require(lavaan, quietly=TRUE)) install.packages("lavaan", repos="https://cloud.r-project.org")
if (!require(readxl, quietly=TRUE)) install.packages("readxl", repos="https://cloud.r-project.org")
if (!require(lme4, quietly=TRUE)) install.packages("lme4", repos="https://cloud.r-project.org")
suppressMessages({ library(lavaan); library(readxl); library(lme4) })

args <- commandArgs(trailingOnly=TRUE)
DATA <- if (length(args) >= 1) args[1] else "final_merged_analysis_data.xlsx"
if (!file.exists(DATA)) {
  # 试几个常见路径
  for (p in c("data/final_merged_analysis_data.xlsx",
              "../data/final_merged_analysis_data.xlsx")) {
    if (file.exists(p)) { DATA <- p; break }
  }
}
if (!file.exists(DATA)) stop("找不到数据文件。用法: Rscript run_mcfa_twolevel.R <xlsx路径>")

d <- as.data.frame(read_excel(DATA))
cat("=",.rep=70,"\n")
cat("Study 3 Item-Level Multilevel CFA (TWOLEVEL)\n")
cat(sprintf("N = %d  Leaders = %d  File = %s\n", nrow(d), length(unique(d$LeaderID)), DATA))
cat("=",.rep=70,"\n\n")

# ---- ICC 诊断 ----
cat("--- Item ICC (between-level variance check) ---\n")
items <- c(paste0("AUT",1:6), paste0("EMP",1:12),
           paste0("BEN",1:5), paste0("MAL",1:5),
           "THR1","THR2","THR3","THR4","R_THR5",
           "THR6","THR7","THR8","THR9","R_THR10")
for (it in items) {
  if (!it %in% names(d)) next
  f <- lmer(as.formula(paste(it, "~ 1 + (1|LeaderID)")), data=d, REML=FALSE,
            control=lmerControl(check.conv.singular="ignore"))
  vc <- as.data.frame(VarCorr(f))
  vb <- vc$vcov[vc$grp=="LeaderID"]; vw <- attr(VarCorr(f),"sc")^2
  icc <- vb/(vb+vw)
  flag <- if (icc < 0.02) " ** LOW **" else if (icc > 0.30) " (high)" else ""
  cat(sprintf("  %-10s ICC=%.3f%s\n", it, icc, flag))
}

# ---- 5 competing models (all TWOLEVEL) ----
fit_model <- function(name, mod_str) {
  cat("\n====", name, "====\n")
  t0 <- Sys.time()
  fit <- tryCatch(
    cfa(mod_str, data=d, cluster="LeaderID", estimator="MLR"),
    error=function(e) { cat("  ERROR:", conditionMessage(e), "\n"); NULL },
    warning=function(w) {})
  elapsed <- as.numeric(difftime(Sys.time(), t0, units="secs"))
  cat(sprintf("  time: %.0f sec\n", elapsed))

  if (is.null(fit)) return(NULL)
  conv <- lavInspect(fit, "converged")
  cat("  converged:", conv, "\n")
  if (!conv) return(NULL)

  fm <- tryCatch(
    fitMeasures(fit, c("chisq.scaled","df.scaled","pvalue.scaled",
                       "cfi.scaled","tli.scaled","rmsea.scaled",
                       "srmr_within","srmr_between","aic")),
    error=function(e) { cat("  fit measures error:", conditionMessage(e), "\n"); NULL })
  if (is.null(fm)) return(NULL)

  cat(sprintf("  chisq=%.1f  df=%d  p=%.4f\n  CFI=%.3f  TLI=%.3f  RMSEA=%.3f\n  SRMR_within=%.3f  SRMR_between=%.3f  AIC=%.1f\n",
              fm[1],fm[2],fm[3],fm[4],fm[5],fm[6],fm[7],fm[8],fm[9]))

  # Check for negative variances
  neg <- lavInspect(fit, "post.check")
  if (!isTRUE(neg)) cat("  WARNING: post-check failed (possible negative variances)\n")

  data.frame(model=name, chisq=round(fm[1],1), df=as.integer(fm[2]),
             pvalue=round(fm[3],4),
             cfi=round(fm[4],3), tli=round(fm[5],3), rmsea=round(fm[6],3),
             srmr_w=round(fm[7],3), srmr_b=round(fm[8],3),
             aic=round(fm[9],1), row.names=NULL)
}

results <- list()

# Model 1: Five-Factor Hypothesized (all 5 factors at both levels)
results[[1]] <- fit_model("5-Factor Hypothesized", '
  level: 1
    AUTW =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
    EMPW =~ EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
    BENW =~ BEN1+BEN2+BEN3+BEN4+BEN5
    MALW =~ MAL1+MAL2+MAL3+MAL4+MAL5
    THRW =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
  level: 2
    AUTB =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
    EMPB =~ EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
    BENB =~ BEN1+BEN2+BEN3+BEN4+BEN5
    MALB =~ MAL1+MAL2+MAL3+MAL4+MAL5
    THRB =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
')

# Model 2: Four-Factor (BEN+MAL combined into ENVY)
results[[2]] <- fit_model("4-Factor (BEN+MAL)", '
  level: 1
    AUTW =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
    EMPW =~ EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
    ENVYW =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
    THRW =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
  level: 2
    AUTB =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
    EMPB =~ EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
    ENVYB =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
    THRB =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
')

# Model 3: Three-Factor (AUT+EMP combined, BEN+MAL combined)
results[[3]] <- fit_model("3-Factor", '
  level: 1
    LEADW =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
    ENVYW =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
    THRW =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
  level: 2
    LEADB =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
    ENVYB =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
    THRB =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
')

# Model 4: Two-Factor
results[[4]] <- fit_model("2-Factor", '
  level: 1
    PREDW =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
    OUTW =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
  level: 2
    PREDB =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
    OUTB =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
')

# Model 5: Single-Factor
results[[5]] <- fit_model("1-Factor", '
  level: 1
    GENW =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5+THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
  level: 2
    GENB =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5+THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10
')

# ---- 输出汇总 ----
cat("\n","=",rep("=",69),"\n")
cat("MCFA TWOLEVEL ITEM-LEVEL RESULTS (lavaan MLR)\n")
cat("=",rep("=",69),"\n\n")
all_res <- do.call(rbind, results[!sapply(results, is.null)])
if (nrow(all_res) > 0) {
  print(all_res, row.names=FALSE)
  outfile <- "mcfa_twolevel_results.csv"
  write.csv(all_res, outfile, row.names=FALSE)
  cat("\n结果已保存:", outfile, "\n")
  cat("\n预期: 5-Factor CFI 最高, 逐步递减到 1-Factor\n")
} else {
  cat("所有模型都未收敛。建议:\n")
  cat("  1. 确认内存 >= 4GB (free -m)\n")
  cat("  2. 用 Mplus 跑 code/mcfa_mplus_syntax.inp\n")
}
cat("\n完成。\n")
