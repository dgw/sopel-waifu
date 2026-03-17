.DEFAULT_GOAL := lint
.PHONY: dev install install-dev json5-lint-deps lint duplicates schema-check sort sort-check whitespace whitespace-deps

WAIFU_JSON := sopel_waifu/waifu.json5
WAIFU_SCHEMA := $(WAIFU_JSON).schema

dev: json5-lint-deps whitespace-deps install-dev

install:
	pip install -U .

install-dev:
	pip install -U -e .

lint: whitespace duplicates schema-check sort-check

json5-lint-deps:
	pip3 install -U check-jsonschema json5

duplicates:
	@echo "🎯 Running duplicate_detect script"
	python3 scripts/duplicate_detect.py $(WAIFU_JSON)
	@echo ""

schema-check:
	@echo "🎯 Running check-jsonschema"
	check-jsonschema --schemafile $(WAIFU_SCHEMA) $(WAIFU_JSON)
	@echo ""

sort:
	@echo "🎯 Sorting top-level keys in $(WAIFU_JSON)"
	python3 scripts/sort_json5.py $(WAIFU_JSON)
	@echo ""

sort-check:
	@echo "🎯 Running sort_check script"
	python3 scripts/sort_check.py $(WAIFU_JSON)
	@echo ""

whitespace:
	@echo "🎯 Running whitespace-format"
	whitespace-format --check-only --add-new-line-marker-at-end-of-file \
	--new-line-marker auto --normalize-new-line-markers \
	--replace-tabs-with-spaces 4 --remove-trailing-empty-lines \
	--remove-trailing-whitespace $(WAIFU_JSON)
	@echo ""

whitespace-deps:
	pip3 install -U whitespace-format
