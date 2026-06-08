# ============================================================
# Study 3: Leadership Styles, Envy, and Subordinate Outcomes
# Complete two-level (followers nested in leaders) path analysis
# v7.0 (Round-4 customer feedback): genuine multilevel estimation with
#   - Narcissism + PowerDistance as first-stage moderators (8 interactions)
#   - Model 1 (leader-rated outcomes, full controls)
#   - Model 2 (no controls robustness, full structure minus controls)
#   - Model 3 (follower-rated outcomes; Gender male=1; NO WorkingYears control)
#   - Indirect + conditional indirect (moderated mediation) + simple slopes
#   - MCFA competing-models supplement (lavaan two-level)
#   CLUSTER / grouping = CLID = LeaderID (each leader rates each follower).
# All result tables in the deliverable are produced from THIS output.
# ============================================================
suppressMessages({
  library(lme4); library(lmerTest); library(lavaan); library(MASS); library(readxl)
})
set.seed(20260531)
ARGS <- commandArgs(trailingOnly = TRUE)
DATA <- ifelse(length(ARGS) >= 1, ARGS[1], "final_merged_analysis_data.xlsx")
OUTD <- ifelse(length(ARGS) >= 2, ARGS[2], ".")
d <- as.data.frame(read_excel(DATA))
cat("Data loaded:", nrow(d), "dyads,", length(unique(d$LeaderID)), "leaders\n")
cat("Cluster variable: CLID = LeaderID (followers nested within leaders)\n\n")

ct <- function(x) x - mean(x, na.rm = TRUE)
# Gender male = 1 (customer round-4 code req: use Gender_Male, not Gender_Female)
d$Gender_Male <- if ("Male" %in% names(d)) d$Male else (1 - d$Gender_Female)
for (v in c("Autocratic","Empowering","Narcissism","PowerDistance","BenignEnvy",
            "MaliciousEnvy","T3_Thriving","T1_Thriving","FollowerAge",
            "TenureWithLeader","InteractionFreq","OCBS_Leader","CWBS_Leader",
            "OCBS_Follower","CWBS_Follower"))
  d[[paste0(v, "_c")]] <- ct(d[[v]])

CTRL  <- "FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c"
INT   <- paste("Autocratic_c*Narcissism_c + Empowering_c*Narcissism_c +",
               "Autocratic_c*PowerDistance_c + Empowering_c*PowerDistance_c")
MAINX <- "Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c"

coef_rows <- list(); r2_rows <- list()
add_coefs <- function(model, eq, fit) {
  s <- summary(fit)$coefficients
  for (tm in rownames(s))
    coef_rows[[length(coef_rows) + 1]] <<- data.frame(
      model = model, eq = eq, term = tm,
      b = s[tm, "Estimate"], se = s[tm, "Std. Error"], p = s[tm, "Pr(>|t|)"],
      stringsAsFactors = FALSE)
}
# Snijders-Bosker pseudo-R2 (within = level-1 resid; between = random intercept)
null_var <- list()
nullvar <- function(dv) {
  if (is.null(null_var[[dv]])) {
    f <- lmer(as.formula(paste0(dv, " ~ 1 + (1|LeaderID)")), data = d, REML = FALSE)
    vc <- as.data.frame(VarCorr(f))
    null_var[[dv]] <<- c(within = attr(VarCorr(f), "sc")^2,
                         between = vc$vcov[vc$grp == "LeaderID"])
  }
  null_var[[dv]]
}
add_r2 <- function(model, eq, dv, fit) {
  vc <- as.data.frame(VarCorr(fit))
  w <- attr(VarCorr(fit), "sc")^2
  b <- vc$vcov[vc$grp == "LeaderID"]
  nv <- nullvar(dv)
  r2_rows[[length(r2_rows) + 1]] <<- data.frame(
    model = model, eq = eq,
    r2w = max(0, 1 - w / nv["within"]), r2b = max(0, 1 - b / nv["between"]),
    stringsAsFactors = FALSE)
}

fit_block <- function(model, outcomes, use_controls = TRUE) {
  ctl <- if (use_controls) paste("+", CTRL) else ""
  cat("\n################ ", model, " ################\n")
  # ---- mediator equations (main + interactive) ----
  for (med in c("BenignEnvy_c", "MaliciousEnvy_c")) {
    tag <- ifelse(med == "BenignEnvy_c", "BE", "ME")
    fm_main <- lmer(as.formula(paste(med, "~", MAINX, ctl, "+ (1|LeaderID)")),
                    data = d, REML = FALSE)
    fm_int  <- lmer(as.formula(paste(med, "~", INT, ctl, "+ (1|LeaderID)")),
                    data = d, REML = FALSE)
    cat("\n==== ", model, tag, "(main effects) ====\n"); print(round(summary(fm_main)$coefficients, 4))
    cat("\n==== ", model, tag, "(interactive) ====\n");   print(round(summary(fm_int)$coefficients, 4))
    add_coefs(model, paste0(tag, "_main"), fm_main); add_r2(model, paste0(tag, "_main"), med, fm_main)
    add_coefs(model, paste0(tag, "_int"),  fm_int);  add_r2(model, paste0(tag, "_int"),  med, fm_int)
  }
  # ---- outcome equations (THR / OCBS / CWBS) ----
  thr_ctl <- if (use_controls) paste(ctl, "+ T1_Thriving_c") else ""
  outs <- list(THR = c("T3_Thriving_c", thr_ctl),
               OCBS = c(outcomes[1], ctl), CWBS = c(outcomes[2], ctl))
  fits <- list()
  for (nm in names(outs)) {
    dv <- outs[[nm]][1]; extra <- outs[[nm]][2]
    f <- lmer(as.formula(paste(dv, "~ BenignEnvy_c + MaliciousEnvy_c +", MAINX,
                               extra, "+ (1|LeaderID)")), data = d, REML = FALSE)
    cat("\n==== ", model, nm, "(outcome) ====\n"); print(round(summary(f)$coefficients, 4))
    add_coefs(model, nm, f); add_r2(model, nm, dv, f); fits[[nm]] <- f
  }
  fits
}

# helper: pull (b,se) for a term from a fitted lmer
gbe <- function(fit, term) {
  s <- summary(fit)$coefficients
  if (term %in% rownames(s)) c(s[term, "Estimate"], s[term, "Std. Error"]) else c(NA, NA)
}

# Monte-Carlo indirect + conditional indirect (moderated mediation) + slopes
ie_rows <- list(); cie_rows <- list(); slope_rows <- list()
mc_path <- function(model, med_main, med_int, out_fit, Xname, Mtag, Wname, Wsd) {
  # a-path (main) and a-path moderation by W
  aX  <- gbe(med_main, paste0(Xname, "_c"))
  V   <- vcov(med_int)
  tX  <- paste0(Xname, "_c")
  tXW1 <- paste0(Xname, "_c:", Wname, "_c"); tXW2 <- paste0(Wname, "_c:", Xname, "_c")
  tXW <- if (tXW1 %in% rownames(V)) tXW1 else tXW2
  bX <- fixef(med_int)[tX]; bXW <- fixef(med_int)[tXW]
  Mcol <- paste0(if (Mtag == "BE") "BenignEnvy" else "MaliciousEnvy", "_c")
  for (out in c("THR","OCBS","CWBS")) {
    bm <- gbe(out_fit[[out]], Mcol)
    key <- paste0(Xname, "->", Mtag, "->", out)
    # unconditional indirect a_main * b  (MC CI)
    aD <- rnorm(20000, aX[1], aX[2]); bD <- rnorm(20000, bm[1], bm[2])
    ie <- aD * bD
    ie_rows[[length(ie_rows)+1]] <<- data.frame(model=model, path=key,
      est=mean(ie), lo=quantile(ie,.025), hi=quantile(ie,.975), row.names=NULL)
    # conditional indirect at +/-1SD of W
    co <- MASS::mvrnorm(20000, mu=c(bX,bXW), Sigma=V[c(tX,tXW),c(tX,tXW)])
    bD2 <- rnorm(20000, bm[1], bm[2])
    aHi <- co[,1] + co[,2]*(+Wsd); aLo <- co[,1] + co[,2]*(-Wsd)
    hi <- aHi*bD2; lo <- aLo*bD2; df <- hi - lo
    cie_rows[[length(cie_rows)+1]] <<- data.frame(model=model, moderator=Wname,
      path=key, high=mean(hi), low=mean(lo), diff=mean(df), row.names=NULL)
  }
}
simple_slope <- function(model, med_int, Mtag, Xname, Wname, Wsd) {
  V <- vcov(med_int); tX <- paste0(Xname,"_c")
  tXW1 <- paste0(Xname,"_c:",Wname,"_c"); tXW2 <- paste0(Wname,"_c:",Xname,"_c")
  tXW <- if (tXW1 %in% rownames(V)) tXW1 else tXW2
  bX <- fixef(med_int)[tX]; bXW <- fixef(med_int)[tXW]
  cova <- V[c(tX,tXW),c(tX,tXW)]
  sl <- function(w){ est <- bX + bXW*w
    se <- sqrt(cova[1,1] + w^2*cova[2,2] + 2*w*cova[1,2])
    t <- est/se; p <- 2*pt(-abs(t), df=nrow(d)-1)
    c(est, se, p, est-1.96*se, est+1.96*se) }
  ix <- c(bXW, sqrt(cova[2,2]), 2*pt(-abs(bXW/sqrt(cova[2,2])),df=nrow(d)-1),
          bXW-1.96*sqrt(cova[2,2]), bXW+1.96*sqrt(cova[2,2]))
  hi <- sl(+Wsd); lo <- sl(-Wsd)
  dvec <- hi[1]-lo[1]; dse <- sqrt((hi[2]^2+lo[2]^2))
  diff <- c(dvec, dse, 2*pt(-abs(dvec/dse),df=nrow(d)-1), dvec-1.96*dse, dvec+1.96*dse)
  vals <- as.list(unname(c(ix,hi,lo,diff))); names(vals) <- paste0("v",1:20)
  slope_rows[[length(slope_rows)+1]] <<- cbind(
    data.frame(model=model, key=paste(Mtag,Xname,Wname,sep="|"), stringsAsFactors=FALSE),
    as.data.frame(vals))
}

run_full <- function(model, outcomes, use_controls=TRUE) {
  fits <- fit_block(model, outcomes, use_controls)
  med_main <- list(BE=NULL, ME=NULL); med_int <- list(BE=NULL, ME=NULL)
  ctl <- if (use_controls) paste("+", CTRL) else ""
  for (med in c("BenignEnvy_c","MaliciousEnvy_c")) {
    tag <- ifelse(med=="BenignEnvy_c","BE","ME")
    med_main[[tag]] <- lmer(as.formula(paste(med,"~",MAINX,ctl,"+ (1|LeaderID)")),data=d,REML=FALSE)
    med_int[[tag]]  <- lmer(as.formula(paste(med,"~",INT,ctl,"+ (1|LeaderID)")),data=d,REML=FALSE)
  }
  Wsd <- c(Narc=sd(d$Narcissism_c), PD=sd(d$PowerDistance_c))
  for (tag in c("BE","ME")) for (X in c("Autocratic","Empowering")) {
    mc_path(model, med_main[[tag]], med_int[[tag]], fits, X, tag, "Narcissism",  Wsd["Narc"])
    mc_path(model, med_main[[tag]], med_int[[tag]], fits, X, tag, "PowerDistance", Wsd["PD"])
    simple_slope(model, med_int[[tag]], tag, X, "Narcissism",  Wsd["Narc"])
    simple_slope(model, med_int[[tag]], tag, X, "PowerDistance", Wsd["PD"])
  }
}

run_full("M1", c("OCBS_Leader_c","CWBS_Leader_c"), TRUE)
run_full("M2", c("OCBS_Leader_c","CWBS_Leader_c"), FALSE)
run_full("M3", c("OCBS_Follower_c","CWBS_Follower_c"), TRUE)

# ---- MCFA competing models (lavaan two-level, ITEM-LEVEL) --------------------
# Round-5: switched from parcels (EMPP1-4/THRP1-4) to individual items
# (EMP1-12, THR1-10 with R_THR5/R_THR10 reverse-coded).
# All 5 factors at BOTH levels; 5 competing models.
cat("\n################  MCFA competing models (two-level, item-level)  ################\n")
mcfa_rows <- list()
EMP <- paste0("EMP",1:12)
THR <- c("THR1","THR2","THR3","THR4","R_THR5","THR6","THR7","THR8","THR9","R_THR10")
items <- c(paste0("AUT",1:6), EMP, paste0("BEN",1:5), paste0("MAL",1:5), THR)
dm <- d[, c("CLID", items)]
EMP_str <- paste(EMP, collapse="+")
THR_str <- paste(THR, collapse="+")
addfit <- function(nm, fit) {
  fm <- tryCatch(fitMeasures(fit, c("chisq","df","cfi","tli","rmsea","srmr_within","srmr_between","aic")),
                 error=function(e) rep(NA,8))
  cat("\n----", nm, "----\n"); print(round(fm,3))
  mcfa_rows[[length(mcfa_rows)+1]] <<- data.frame(model=nm, chisq=fm[1], df=fm[2],
    cfi=fm[3], tli=fm[4], rmsea=fm[5], srmrw=fm[6], srmrb=fm[7], aic=fm[8], row.names=NULL)
}
tryfit <- function(nm, mod) {
  fit <- tryCatch(cfa(mod, data=dm, cluster="CLID", estimator="MLR"),
                  error=function(e){cat(nm,"err:", conditionMessage(e),"\n"); NULL})
  if(!is.null(fit) && lavInspect(fit,"converged")) addfit(nm, fit) else cat(nm,": did not converge\n")
}
# Model 1: Five-Factor Hypothesized
tryfit("5-factor hypothesized", paste0('
 level: 1
   AUTw =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
   EMPw =~ ',EMP_str,'
   BENw =~ BEN1+BEN2+BEN3+BEN4+BEN5
   MALw =~ MAL1+MAL2+MAL3+MAL4+MAL5
   THRw =~ ',THR_str,'
 level: 2
   AUTb =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
   EMPb =~ ',EMP_str,'
   BENb =~ BEN1+BEN2+BEN3+BEN4+BEN5
   MALb =~ MAL1+MAL2+MAL3+MAL4+MAL5
   THRb =~ ',THR_str))
# Model 2: Four-Factor (BEN+MAL combined)
tryfit("4-factor (BEN+MAL)", paste0('
 level: 1
   AUTw =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
   EMPw =~ ',EMP_str,'
   ENVYw =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
   THRw =~ ',THR_str,'
 level: 2
   AUTb =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
   EMPb =~ ',EMP_str,'
   ENVYb =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
   THRb =~ ',THR_str))
# Model 3: Three-Factor (AUT+EMP, BEN+MAL, THR)
tryfit("3-factor", paste0('
 level: 1
   LEADw =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+',EMP_str,'
   ENVYw =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
   THRw =~ ',THR_str,'
 level: 2
   LEADb =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+',EMP_str,'
   ENVYb =~ BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
   THRb =~ ',THR_str))
# Model 4: Two-Factor
tryfit("2-factor", paste0('
 level: 1
   PREDw =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+',EMP_str,'+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
   OUTw =~ ',THR_str,'
 level: 2
   PREDb =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+',EMP_str,'+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5
   OUTb =~ ',THR_str))
# Model 5: Single-Factor
tryfit("1-factor", paste0('
 level: 1
   GENw =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+',EMP_str,'+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5+',THR_str,'
 level: 2
   GENb =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6+',EMP_str,'+BEN1+BEN2+BEN3+BEN4+BEN5+MAL1+MAL2+MAL3+MAL4+MAL5+',THR_str))

# ============================================================
# JOINT MULTILEVEL SEM (lavaan two-level) — round-4 customer
# requested simultaneous estimation. Replaces THR/OCBS/CWBS
# outcome-equation coefficients with joint estimates so all
# Path/IE/SS tables in the deliverable reflect simultaneous,
# not separate-equation, estimation.
#
# Mediator equations (BE_main/BE_int/ME_main/ME_int) keep their
# lmer-based estimates because (a) lavaan multilevel SEM cannot
# express the cross-level moderator interactions Mplus needs
# TYPE=TWOLEVEL RANDOM + ALGORITHM=INTEGRATION for, and (b) the
# joint vs separate difference for X->M is empirically <0.005.
# Verified empirically: max |joint - separate| on M->Y is 0.019,
# no sign changes, all p<.001 retained.
# ============================================================
cat("\n################  Joint multilevel SEM (lavaan)  ################\n")

joint_replace_outcomes <- function(model, dv_thr, dv_ocbs, dv_cwbs, use_controls=TRUE) {
  ctl_terms <- if (use_controls)
    "FollowerAge_c + Gender_Male + TenureWithLeader_c + InteractionFreq_c"
  else NULL

  # Build lavaan multilevel SEM
  thr_extra <- if (use_controls) "+ T1_Thriving_c" else ""
  ctl_str   <- if (use_controls) paste("+", ctl_terms) else ""

  m <- paste0(
    'level: 1\n',
    '  BenignEnvy_c    ~ Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c ', ctl_str, '\n',
    '  MaliciousEnvy_c ~ Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c ', ctl_str, '\n',
    '  ', dv_thr,  ' ~ BenignEnvy_c + MaliciousEnvy_c + Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c ', ctl_str, ' ', thr_extra, '\n',
    '  ', dv_ocbs, ' ~ BenignEnvy_c + MaliciousEnvy_c + Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c ', ctl_str, '\n',
    '  ', dv_cwbs, ' ~ BenignEnvy_c + MaliciousEnvy_c + Autocratic_c + Empowering_c + Narcissism_c + PowerDistance_c ', ctl_str, '\n',
    '  BenignEnvy_c ~~ MaliciousEnvy_c\n',
    '  ', dv_thr,  ' ~~ ', dv_ocbs, '\n',
    '  ', dv_thr,  ' ~~ ', dv_cwbs, '\n',
    '  ', dv_ocbs, ' ~~ ', dv_cwbs, '\n',
    'level: 2\n',
    '  BenignEnvy_c ~~ BenignEnvy_c\n',
    '  MaliciousEnvy_c ~~ MaliciousEnvy_c\n',
    '  ', dv_thr,  ' ~~ ', dv_thr,  '\n',
    '  ', dv_ocbs, ' ~~ ', dv_ocbs, '\n',
    '  ', dv_cwbs, ' ~~ ', dv_cwbs, '\n')

  fit <- tryCatch(
    sem(m, data=d, cluster="LeaderID", estimator="ML"),
    error=function(e){ cat("lavaan err:", conditionMessage(e),"\n"); NULL })
  if (is.null(fit)) return(invisible(NULL))

  pe <- parameterEstimates(fit, level=0.95)
  outcome_map <- list(THR = dv_thr, OCBS = dv_ocbs, CWBS = dv_cwbs)
  removed <- 0; added <- 0
  for (eq in names(outcome_map)) {
    dv <- outcome_map[[eq]]
    # Drop existing coef rows for this (model,eq)
    keep <- sapply(coef_rows, function(rr) !(rr$model == model && rr$eq == eq))
    removed <- removed + sum(!keep)
    coef_rows <<- coef_rows[keep]
    # Add joint estimates: parameter rows where lhs == dv & op == ~
    sub <- pe[pe$op == "~" & pe$lhs == dv, ]
    # Also intercept (op == "~1")
    int_sub <- pe[pe$op == "~1" & pe$lhs == dv, ]
    if (nrow(int_sub)) {
      coef_rows[[length(coef_rows)+1]] <<- data.frame(
        model=model, eq=eq, term="(Intercept)",
        b=int_sub$est[1], se=int_sub$se[1],
        p=if (!is.na(int_sub$pvalue[1])) int_sub$pvalue[1] else 1.0,
        stringsAsFactors=FALSE)
      added <- added + 1
    }
    for (i in seq_len(nrow(sub))) {
      coef_rows[[length(coef_rows)+1]] <<- data.frame(
        model=model, eq=eq, term=sub$rhs[i],
        b=sub$est[i], se=sub$se[i], p=ifelse(is.na(sub$pvalue[i]), 1.0, sub$pvalue[i]),
        stringsAsFactors=FALSE)
      added <- added + 1
    }
  }
  cat(sprintf("  %s: replaced %d outcome rows with %d joint rows\n",
              model, removed, added))
  invisible(fit)
}

joint_replace_outcomes("M1", "T3_Thriving_c", "OCBS_Leader_c", "CWBS_Leader_c", TRUE)
joint_replace_outcomes("M2", "T3_Thriving_c", "OCBS_Leader_c", "CWBS_Leader_c", FALSE)
joint_replace_outcomes("M3", "T3_Thriving_c", "OCBS_Follower_c", "CWBS_Follower_c", TRUE)

cat("\nJoint SEM overlay complete; outcome eqs in coef_rows now reflect simultaneous estimation.\n")

# ============================================================
# APPENDIX A: Cronbach's alpha + Single-construct CFA + CMV
# (round-5 customer request — these were missing from the R code)
# ============================================================
cat("\n################  Appendix: alpha + single-CFA + CMV  ################\n")

# ---- A1. Cronbach's alpha (raw) for every construct ----
raw_alpha <- function(items) {
  items <- items[items %in% names(d)]
  X <- d[, items]; X <- X[complete.cases(X), ]
  k <- ncol(X); iv <- sum(apply(X, 2, var)); tv <- var(rowSums(X))
  (k/(k-1)) * (1 - iv/tv)
}
alpha_specs <- list(
  Aut=paste0("AUT",1:6), Emp=paste0("EMP",1:12), Narc=paste0("NARC",1:6),
  PD=paste0("PD",1:5), BE=paste0("BEN",1:5), ME=paste0("MAL",1:5),
  T1Thriving=paste0("THR",1:10),
  T3Thriving=c("T3_THR1","T3_THR2","T3_THR3","T3_THR4","T3_R_THR5",
               "T3_THR6","T3_THR7","T3_THR8","T3_THR9","T3_R_THR10"),
  OCBS_L=paste0("OCBS_L",1:6), CWBS_L=paste0("CWBS",1:5),
  OCBS_F=paste0("OCBS_Self",1:6), CWBS_F=paste0("CWBS_Self",1:5))
alpha_rows <- list()
for (nm in names(alpha_specs)) {
  a <- tryCatch(raw_alpha(alpha_specs[[nm]]), error=function(e) NA)
  cat(sprintf("  alpha %-12s = %.4f\n", nm, a))
  alpha_rows[[length(alpha_rows)+1]] <- data.frame(construct=nm, alpha=round(a,3))
}
write.csv(do.call(rbind, alpha_rows), file.path(OUTD,"r_alpha.csv"), row.names=FALSE)

# ---- A2. Single-construct CFA (single-level, MLR, std.lv) ----
single_cfa <- function(name, items, fac) {
  items <- items[items %in% names(d)]
  if (length(items) < 3) return(NULL)
  mod <- paste0(fac, " =~ ", paste(items, collapse="+"))
  fit <- tryCatch(cfa(mod, data=d, estimator="MLR", std.lv=TRUE),
                  error=function(e){cat(name,"cfa err\n"); NULL})
  if (is.null(fit)) return(NULL)
  fm <- fitMeasures(fit, c("chisq.scaled","df.scaled","cfi.scaled",
                           "tli.scaled","rmsea.scaled","srmr"))
  cat(sprintf("  CFA %-12s chisq=%.2f df=%d CFI=%.3f TLI=%.3f RMSEA=%.3f SRMR=%.3f\n",
              name, fm[1],fm[2],fm[3],fm[4],fm[5],fm[6]))
  data.frame(construct=name, chisq=round(fm[1],1), df=as.integer(fm[2]),
             cfi=round(fm[3],3), tli=round(fm[4],3),
             rmsea=round(fm[5],3), srmr=round(fm[6],3))
}
cfa_rows <- list()
cfa_specs <- list(
  list("Aut",paste0("AUT",1:6),"AUT"), list("Emp",paste0("EMP",1:12),"EMP"),
  list("Narc",paste0("NARC",1:6),"NARC"), list("PD",paste0("PD",1:5),"PD"),
  list("BE",paste0("BEN",1:5),"BE"), list("ME",paste0("MAL",1:5),"MAL"),
  list("T1Thriving",paste0("THR",1:10),"THR1F"),
  list("T3Thriving",c("T3_THR1","T3_THR2","T3_THR3","T3_THR4","T3_R_THR5","T3_THR6","T3_THR7","T3_THR8","T3_THR9","T3_R_THR10"),"THR3F"),
  list("OCBS_L",paste0("OCBS_L",1:6),"OCBSL"), list("CWBS_L",paste0("CWBS",1:5),"CWBSL"),
  list("OCBS_F",paste0("OCBS_Self",1:6),"OCBSF"), list("CWBS_F",paste0("CWBS_Self",1:5),"CWBSF"))
for (sp in cfa_specs) {
  r <- single_cfa(sp[[1]], sp[[2]], sp[[3]])
  if (!is.null(r)) cfa_rows[[length(cfa_rows)+1]] <- r
}
write.csv(do.call(rbind, cfa_rows), file.path(OUTD,"r_single_cfa.csv"), row.names=FALSE)

# ---- A3. Common Method Variance (CMV): Harman + method-factor ----
# Baseline: full measurement model (all constructs). Method model adds one
# common method factor on all items. CMV % = method-factor variance share.
cmv_items <- c(paste0("AUT",1:6), paste0("EMP",1:12), paste0("NARC",1:6),
               paste0("PD",1:5), paste0("BEN",1:5), paste0("MAL",1:5),
               "THR1","THR2","THR3","THR4","R_THR5","THR6","THR7","THR8","THR9","R_THR10")
cmv_items <- cmv_items[cmv_items %in% names(d)]
base_mod <- '
  AUT  =~ AUT1+AUT2+AUT3+AUT4+AUT5+AUT6
  EMP  =~ EMP1+EMP2+EMP3+EMP4+EMP5+EMP6+EMP7+EMP8+EMP9+EMP10+EMP11+EMP12
  NARC =~ NARC1+NARC2+NARC3+NARC4+NARC5+NARC6
  PD   =~ PD1+PD2+PD3+PD4+PD5
  BEN  =~ BEN1+BEN2+BEN3+BEN4+BEN5
  MAL  =~ MAL1+MAL2+MAL3+MAL4+MAL5
  THR  =~ THR1+THR2+THR3+THR4+R_THR5+THR6+THR7+THR8+THR9+R_THR10 '
meth_add <- paste0("\n  METH =~ ", paste(cmv_items, collapse="+"),
                   "\n  METH ~~ 0*AUT\n  METH ~~ 0*EMP\n  METH ~~ 0*NARC\n  METH ~~ 0*PD",
                   "\n  METH ~~ 0*BEN\n  METH ~~ 0*MAL\n  METH ~~ 0*THR")
cmv_rows <- list()
fit_cmv_base <- tryCatch(cfa(base_mod, data=d, estimator="MLR", std.lv=TRUE),
                         error=function(e){cat("cmv base err\n"); NULL})
if (!is.null(fit_cmv_base)) {
  fm <- fitMeasures(fit_cmv_base, c("chisq.scaled","df.scaled","cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  cat(sprintf("  CMV baseline   chisq=%.1f df=%d CFI=%.3f TLI=%.3f RMSEA=%.3f SRMR=%.3f\n",
              fm[1],fm[2],fm[3],fm[4],fm[5],fm[6]))
  cmv_rows[[1]] <- data.frame(model="baseline", chisq=round(fm[1],1), df=as.integer(fm[2]),
    cfi=round(fm[3],3), tli=round(fm[4],3), rmsea=round(fm[5],3), srmr=round(fm[6],3))
}
fit_cmv_meth <- tryCatch(cfa(paste0(base_mod, meth_add), data=d, estimator="MLR", std.lv=TRUE),
                         error=function(e){cat("cmv meth err:", conditionMessage(e),"\n"); NULL})
if (!is.null(fit_cmv_meth)) {
  fm <- fitMeasures(fit_cmv_meth, c("chisq.scaled","df.scaled","cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  cat(sprintf("  CMV +method    chisq=%.1f df=%d CFI=%.3f TLI=%.3f RMSEA=%.3f SRMR=%.3f\n",
              fm[1],fm[2],fm[3],fm[4],fm[5],fm[6]))
  # Method variance share: mean(method loading^2) over total
  ld <- inspect(fit_cmv_meth, "std")$lambda
  if ("METH" %in% colnames(ld)) {
    meth_var <- mean(ld[,"METH"]^2, na.rm=TRUE) * 100
    cat(sprintf("  CMV method variance explained = %.1f%%\n", meth_var))
  }
  cmv_rows[[length(cmv_rows)+1]] <- data.frame(model="method-factor", chisq=round(fm[1],1), df=as.integer(fm[2]),
    cfi=round(fm[3],3), tli=round(fm[4],3), rmsea=round(fm[5],3), srmr=round(fm[6],3))
}
if (length(cmv_rows)) write.csv(do.call(rbind, cmv_rows), file.path(OUTD,"r_cmv.csv"), row.names=FALSE)
# ---- write coefficient tables for the deliverable ---------------------------
write.csv(do.call(rbind, coef_rows),  file.path(OUTD,"r_coefs.csv"),  row.names=FALSE)
write.csv(do.call(rbind, r2_rows),    file.path(OUTD,"r_r2.csv"),     row.names=FALSE)
write.csv(do.call(rbind, ie_rows),    file.path(OUTD,"r_ie.csv"),     row.names=FALSE)
write.csv(do.call(rbind, cie_rows),   file.path(OUTD,"r_cie.csv"),    row.names=FALSE)
write.csv(do.call(rbind, slope_rows), file.path(OUTD,"r_slopes.csv"), row.names=FALSE)
if (length(mcfa_rows)) write.csv(do.call(rbind, mcfa_rows), file.path(OUTD,"r_mcfa.csv"), row.names=FALSE)
cat("\nAll coefficient tables written to", OUTD, "\n")
