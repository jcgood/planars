# Planars coordinator command aliases.
# Activate the project venv before running: source .venv/bin/activate
# For commands with flags not covered here, use: python -m coding <command> --help

.PHONY: help \
        generate-sheets import-sheets apply-pending validate-coding \
        update-sheets sync-params restructure-sheets generate-notebooks generate-reports \
        update-sheets-dry sync-params-dry restructure-dry \
        integrity-check check-codebook lookup-lang \
        test snapshots

help:
	@echo "Sheet lifecycle:"
	@echo "  generate-sheets       Create annotation sheets for new classes"
	@echo "  import-sheets         Download filled sheets → TSVs"
	@echo "  apply-pending         Review and apply pending destructive changes"
	@echo "  validate-coding       Re-validate sheets and update pink highlights"
	@echo ""
	@echo "Sheet maintenance (write to Google Sheets — dry run first):"
	@echo "  update-sheets         Add missing rows to sheets (--apply)"
	@echo "  sync-params           Sync criterion columns (--apply)"
	@echo "  restructure-sheets    Archive + regenerate after planar changes (--apply)"
	@echo "  generate-notebooks    Regenerate and upload Colab notebooks"
	@echo "  generate-reports      Generate and upload HTML reports to Drive"
	@echo ""
	@echo "Dry runs (show what would change, no writes):"
	@echo "  update-sheets-dry     Dry run for update-sheets"
	@echo "  sync-params-dry       Dry run for sync-params"
	@echo "  restructure-dry       Dry run for restructure-sheets"
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

apply-pending:
	python -m coding apply-pending

validate-coding:
	python -m coding validate-coding

# ---------------------------------------------------------------------------
# Sheet maintenance  (write changes — review dry runs first)
# Rename/split/merge/remove flags are not aliased; use full command directly.
# ---------------------------------------------------------------------------

update-sheets:
	python -m coding update-sheets --apply

sync-params:
	python -m coding sync-params --apply

# DESTRUCTIVE: archives existing sheets before regenerating.
# For rename/element-rename: python -m coding restructure-sheets --rename-map ...
restructure-sheets:
	python -m coding restructure-sheets --apply

generate-notebooks:
	python -m coding generate-notebooks

generate-reports:
	python -m coding generate-reports --apply

# Dry runs

update-sheets-dry:
	python -m coding update-sheets

sync-params-dry:
	python -m coding sync-params

restructure-dry:
	python -m coding restructure-sheets

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
