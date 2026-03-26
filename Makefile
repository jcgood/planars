# Planars coordinator command aliases.
# Activate the project venv before running: source .venv/bin/activate
# For commands with flags not covered here, use: python -m coding <command> --help
#
# Commands that write to Google Sheets or Drive default to dry run.
# Use the -apply variant to execute: e.g. make update-sheets-apply

.PHONY: help \
        generate-sheets import-sheets apply-pending validate-coding \
        update-sheets update-sheets-apply \
        sync-params sync-params-apply \
        restructure-sheets restructure-sheets-apply \
        generate-notebooks generate-notebooks-apply \
        generate-reports generate-reports-apply \
        integrity-check check-codebook lookup-lang \
        test snapshots

help:
	@echo "Sheet lifecycle:"
	@echo "  generate-sheets             Create annotation sheets for new classes"
	@echo "  import-sheets               Dry run: show what would be imported"
	@echo "  import-sheets-apply         Download filled sheets → TSVs"
	@echo "  apply-pending               Review and apply pending destructive changes"
	@echo "  validate-coding             Re-validate sheets and update pink highlights"
	@echo ""
	@echo "Sheet maintenance (bare target = dry run; -apply variant writes):"
	@echo "  update-sheets               Dry run: show missing rows"
	@echo "  update-sheets-apply         Add missing rows to sheets"
	@echo "  sync-params                 Dry run: show criterion column changes"
	@echo "  sync-params-apply           Sync criterion columns"
	@echo "  restructure-sheets          Dry run: show restructure plan"
	@echo "  restructure-sheets-apply    DESTRUCTIVE: archive + regenerate sheets"
	@echo "  generate-notebooks          Dry run: show what would be generated"
	@echo "  generate-notebooks-apply    Regenerate and upload Colab notebooks"
	@echo "  generate-reports            Dry run: show languages to be reported"
	@echo "  generate-reports-apply      Generate and upload PDF reports to Drive"
	@echo ""
	@echo "Health checks:"
	@echo "  integrity-check       Full project health report"
	@echo "  check-codebook        Criterion/module/diagnostics consistency"
	@echo "  lookup-lang LANG=...  Fetch Glottolog metadata (e.g. make lookup-lang LANG=arao1248)"
	@echo ""
	@echo "Testing:"
	@echo "  test                  Run all tests"
	@echo "  snapshots             Regenerate snapshot baselines"

# ---------------------------------------------------------------------------
# Sheet lifecycle
# ---------------------------------------------------------------------------

generate-sheets:
	python -m coding generate-sheets

import-sheets:
	python -m coding import-sheets

import-sheets-apply:
	python -m coding import-sheets --apply

apply-pending:
	python -m coding apply-pending

validate-coding:
	python -m coding validate-coding

# ---------------------------------------------------------------------------
# Sheet maintenance — dry run by default; -apply variant writes
# Rename/split/merge/remove flags are not aliased; use full command directly.
# ---------------------------------------------------------------------------

update-sheets:
	python -m coding update-sheets

update-sheets-apply:
	python -m coding update-sheets --apply

sync-params:
	python -m coding sync-params

sync-params-apply:
	python -m coding sync-params --apply

# DESTRUCTIVE: archives existing sheets before regenerating.
# For rename/element-rename: python -m coding restructure-sheets --rename-map ...
restructure-sheets:
	python -m coding restructure-sheets

restructure-sheets-apply:
	python -m coding restructure-sheets --apply

generate-notebooks:
	python -m coding generate-notebooks

generate-notebooks-apply:
	python -m coding generate-notebooks --apply

generate-reports:
	python -m coding generate-reports

generate-reports-apply:
	python -m coding generate-reports --apply

# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

integrity-check:
	python -m coding integrity-check

check-codebook:
	python -m coding check-codebook

# Usage: make lookup-lang LANG=arao1248
lookup-lang:
	python -m coding lookup-lang $(LANG)

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test:
	pytest

snapshots:
	python generate_snapshots.py
