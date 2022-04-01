.PHONY: quality
quality:
	jsonschema -i sopel_waifu/waifu.json sopel_waifu/waifu.json.schema
