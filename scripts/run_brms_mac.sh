#!/bin/bash
# ============================================================
# Study 3 brms 一键运行脚本 (Mac)
# 用法: bash run_brms_mac.sh
# 从零开始：装 R → 装 brms → 跑分析 → 输出结果
# ============================================================
set -e

echo "========================================================"
echo "Study 3 brms Bayesian Multilevel Path Model — Mac 一键脚本"
echo "========================================================"

# ---- 1. 检查 / 安装 R ----
if ! command -v Rscript &>/dev/null; then
    echo "[1/5] R 未安装，正在通过 Homebrew 安装..."
    if ! command -v brew &>/dev/null; then
        echo "  Homebrew 也没有，先装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Apple Silicon PATH
        [ -f /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    brew install r
    echo "  R 安装完成: $(Rscript --version 2>&1)"
else
    echo "[1/5] R 已安装: $(Rscript --version 2>&1 | head -1)"
fi

# ---- 2. 检查 / 安装 brms + cmdstanr + cmdstan ----
echo "[2/5] 检查 R 包..."
Rscript -e '
need_install <- c()
if (!requireNamespace("brms", quietly=TRUE)) need_install <- c(need_install, "brms")
if (!requireNamespace("cmdstanr", quietly=TRUE)) need_install <- c(need_install, "cmdstanr")
if (!requireNamespace("readxl", quietly=TRUE)) need_install <- c(need_install, "readxl")
if (!requireNamespace("posterior", quietly=TRUE)) need_install <- c(need_install, "posterior")

if (length(need_install) > 0) {
    cat("  安装 R 包:", paste(need_install, collapse=", "), "...\n")
    cran_pkgs <- setdiff(need_install, "cmdstanr")
    if (length(cran_pkgs)) install.packages(cran_pkgs, repos="https://cloud.r-project.org", quiet=TRUE)
    if ("cmdstanr" %in% need_install)
        install.packages("cmdstanr", repos=c("https://stan-dev.r-universe.dev","https://cloud.r-project.org"), quiet=TRUE)
}

# cmdstan binary
library(cmdstanr)
tryCatch({
    v <- cmdstan_version()
    cat("  cmdstan 已安装:", v, "\n")
}, error = function(e) {
    cat("  安装 cmdstan (编译 C++, 约 5 分钟)...\n")
    install_cmdstan(cores = parallel::detectCores(), quiet = TRUE)
    cat("  cmdstan 安装完成:", cmdstan_version(), "\n")
})

cat("  brms:", as.character(packageVersion("brms")), "\n")
cat("  cmdstanr:", as.character(packageVersion("cmdstanr")), "\n")
cat("  R 包就绪.\n")
'

# ---- 3. 定位项目目录 ----
REPO=""
if [ -f "code/analysis_brms.R" ] && [ -f "data/final_merged_analysis_data.xlsx" ]; then
    REPO="$(pwd)"
elif [ -f "../code/analysis_brms.R" ]; then
    REPO="$(cd .. && pwd)"
elif [ -d "$HOME/Desktop/Project/leader_survey_v2" ]; then
    REPO="$HOME/Desktop/Project/leader_survey_v2"
fi

if [ -z "$REPO" ] || [ ! -f "$REPO/code/analysis_brms.R" ]; then
    echo "[3/5] 找不到项目文件，尝试 clone..."
    git clone git@github.com:chenkai66/leader_survey_-.git ./leader_survey_v2 2>/dev/null || \
    git clone https://github.com/chenkai66/leader_survey_-.git ./leader_survey_v2
    REPO="./leader_survey_v2"
fi
echo "[3/5] 项目目录: $REPO"
mkdir -p "$REPO/results/raw_output"

# ---- 4. 跑 brms 分析 ----
echo "[4/5] 开始跑 brms 分析 (预计 15-25 分钟)..."
echo "      $(date '+%H:%M:%S') 开始"
cd "$REPO"
Rscript code/analysis_brms.R data/final_merged_analysis_data.xlsx results/raw_output 2>&1 | tee ./brms_output.log

echo "      $(date '+%H:%M:%S') 完成"

# ---- 5. 输出结果 ----
echo ""
echo "========================================================"
echo "[5/5] 结果"
echo "========================================================"
if [ -f results/raw_output/r_coefs_brms.csv ]; then
    echo "✓ 系数表: $REPO/results/raw_output/r_coefs_brms.csv"
    echo ""
    echo "--- 关键 M→Y 路径 (brms Bayesian 后验) ---"
    Rscript -e '
    d <- read.csv("results/raw_output/r_coefs_brms.csv")
    focal <- d[d$term %in% c("BenignEnvy_c","MaliciousEnvy_c") & d$eq %in% c("THR","OCBS","CWBS"),]
    focal$sig <- ifelse(focal$p < .001, "***", ifelse(focal$p < .01, "**", ifelse(focal$p < .05, "*", "ns")))
    for (i in seq_len(nrow(focal)))
        cat(sprintf("  %-6s <- %-18s  b=%+.4f  95%%CI [%+.3f, %+.3f]  %s\n",
            focal$eq[i], focal$term[i], focal$b[i], focal$ci_lo[i], focal$ci_hi[i], focal$sig[i]))
    '
    echo ""
    echo "--- 完整日志: ./brms_output.log ---"
    echo "--- 如果和 lavaan 结果一致（预期内），当前交付表不用改 ---"
    echo "--- 如果有方向不一致，把 r_coefs_brms.csv 发回来 ---"
else
    echo "✗ 分析失败，查看日志: ./brms_output.log"
    tail -20 ./brms_output.log
fi
