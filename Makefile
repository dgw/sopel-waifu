.DEFAULT_GOAL := lint
.PHONY: dev install install-dev lint duplicates schema-check schema-check-deps whitespace whitespace-deps

dev: schema-check-deps whitespace-deps install-dev

install:
	pip install -U .

install-dev:
	pip install -U -e .

lint: whitespace duplicates schema-check

duplicates:
	@echo "🎯 Running duplicate_detect script"
	@python3 scripts/duplicate_detect.py sopel_waifu/waifu.json5
	@echo ""

schema-check:
	@echo "🎯 Running check-jsonschema"
	@check-jsonschema --schemafile sopel_waifu/waifu.json5.schema sopel_waifu/waifu.json5
	@echo ""

schema-check-deps:
	pip3 install -U check-jsonschema

whitespace:
	@echo "🎯 Running whitespace-format"
	@whitespace-format --check-only --add-new-line-marker-at-end-of-file \
	--new-line-marker auto --normalize-new-line-markers \
	--replace-tabs-with-spaces 4 --remove-trailing-empty-lines \
	--remove-trailing-whitespace sopel_waifu/waifu.json5
	@echo ""

whitespace-deps:
	pip3 install -U whitespace-format
