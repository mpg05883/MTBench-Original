# Shared setup for the evaluation run_*.sh scripts. Source it from the task
# folder (evaluation/finance or evaluation/weather) after cd-ing there:
#   ALLOWED_MODES="timeseries_only text_only combined"   # optional
#   . ../setup_env.sh
#
# It activates the MTBench conda env (on the cluster or locally, e.g. Git Bash
# on Windows) and sets these variables from the environment:
#   API_NAME     model name (default gpt-5.1); Azure models need their
#                deployment env var in .env (see AZURE_DEPLOYMENT_ENV in
#                evaluation/api_call.py)
#   BATCH_FLAGS  e.g. "--batch --wait" for the Batch API (evaluation/batch.py)
#   MODE         prompt inputs (default combined), one of ALLOWED_MODES
#   LIMIT        evaluate only the first N samples (smoke test); also taken
#                from the script's first argument. Sets LIMIT_FLAGS and
#                LIMIT_SUFFIX ("_limitN", appended to save paths so a smoke
#                test never mixes with a full run).

# --- conda ---------------------------------------------------------------
if command -v module >/dev/null 2>&1; then
    module load miniconda
fi
if command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)"
else
    # Non-interactive bash (e.g. Git Bash on Windows) does not define `conda`;
    # load it from the install. Set CONDA_ROOT if conda lives elsewhere.
    for root in "${CONDA_ROOT:-}" "$HOME/anaconda3" "$HOME/miniconda3"; do
        if [ -n "$root" ] && [ -f "$root/etc/profile.d/conda.sh" ]; then
            . "$root/etc/profile.d/conda.sh"
            break
        fi
    done
fi
if ! command -v conda >/dev/null 2>&1; then
    echo "conda not found; set CONDA_ROOT to your conda install" >&2; exit 1
fi
conda activate MTBench || { echo "conda env 'MTBench' not found" >&2; exit 1; }
# On Windows, conda's openssl activate script for bash points SSL_CERT_FILE
# at <env>/ssl/cacert.pem, but the file is in <env>/Library/ssl/. A missing
# file makes every API call fail with "[Errno 2] No such file or directory".
if [ -n "${SSL_CERT_FILE:-}" ] && [ ! -f "$SSL_CERT_FILE" ]; then
    if [ -f "$CONDA_PREFIX/Library/ssl/cacert.pem" ]; then
        export SSL_CERT_FILE="$CONDA_PREFIX/Library/ssl/cacert.pem"
    else
        unset SSL_CERT_FILE
    fi
fi

# --- run options ---------------------------------------------------------
API_NAME="${API_NAME:-gpt-5.1}"
BATCH_FLAGS="${BATCH_FLAGS:-}"

ALLOWED_MODES="${ALLOWED_MODES:-timeseries_only text_only combined}"
MODE="${MODE:-combined}"
case " $ALLOWED_MODES " in
    *" $MODE "*) ;;
    *) echo "Invalid MODE: $MODE (choose from: $ALLOWED_MODES)" >&2; exit 1 ;;
esac

LIMIT="${1:-${LIMIT:-}}"
LIMIT_FLAGS=""
LIMIT_SUFFIX=""
if [ -n "$LIMIT" ]; then
    case "$LIMIT" in
        *[!0-9]*) echo "Invalid LIMIT: $LIMIT (must be a positive integer)" >&2; exit 1 ;;
    esac
    LIMIT_FLAGS="--limit=$LIMIT"
    LIMIT_SUFFIX="_limit${LIMIT}"
fi
