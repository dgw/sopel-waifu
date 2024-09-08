.PHONY: quality
quality:
	python3 duplicate_detect.py sopel_waifu/waifu.json
	check-jsonschema --schemafile sopel_waifu/waifu.json.schema sopel_waifu/waifu.json
