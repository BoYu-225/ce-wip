#!/usr/bin/env bash
# Compile ce.tex, including its bibliography and cross-references.
# Usage: ./build.sh (also works when called from another directory)
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="$project_dir/build"
output_dir="$project_dir/output/pdf"
cd "$project_dir"

for tool in pdflatex bibtex; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Missing command: %s. Install TeX Live or MacTeX and add its bin directory to PATH.\n' "$tool" >&2
        exit 1
    fi
done

mkdir -p "$build_dir" "$output_dir"

run_step() {
    local step="$1"
    shift
    printf '%s\n' "$step"
    if "$@" >"$build_dir/$step.log" 2>&1; then
        return 0
    else
        local status=$?
        tail -n 60 "$build_dir/$step.log" >&2
        printf 'Build failed. Full log: %s/%s.log\n' "$build_dir" "$step" >&2
        exit "$status"
    fi
}

latex_args=(-interaction=nonstopmode -halt-on-error -file-line-error
            -no-shell-escape -output-directory="$build_dir" ce.tex)
run_step pdflatex-1 pdflatex "${latex_args[@]}"
# Keep auxiliary files in build/ while resolving project-local .bib/.bst files.
(
    cd "$build_dir"
    export BIBINPUTS="$project_dir:${BIBINPUTS:-}"
    export BSTINPUTS="$project_dir:${BSTINPUTS:-}"
    run_step bibtex bibtex ce
)
run_step pdflatex-2 pdflatex "${latex_args[@]}"
run_step pdflatex-3 pdflatex "${latex_args[@]}"

# Publish the PDF only after every compilation step has succeeded.
cp "$build_dir/ce.pdf" "$output_dir/ce.pdf"
printf '\nPDF: %s/ce.pdf\nLogs and auxiliary files: %s\n' "$output_dir" "$build_dir"
if grep -Eq 'Warning|Overfull|Underfull' "$build_dir/ce.log"; then
    printf 'LaTeX warnings remain; see %s/ce.log\n' "$build_dir"
fi
