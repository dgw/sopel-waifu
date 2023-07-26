.PHONY: quality
quality:
	check-jsonschema --schemafile sopel_waifu/waifu.json.schema sopel_waifu/waifu.json
