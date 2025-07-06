# sopel-waifu

A Sopel plugin that picks a waifu for you.

## Customizing the waifu list

`sopel-waifu` offers several options for customizing the available waifus. Any
settings described below that you wish to use should be placed in your Sopel
config file, for example:

```ini
[waifu]
json_path = /home/weeb/.sopel/my-waifus.json
json_mode = replace
```

### JSON schema

Waifu lists for `sopel-waifu` must be written in JSON, in this structure:

```json
{
    "Name of a Work": [
        "Character One",
        "Character Two",
        "Character Three"
    ],
    "Name of Another Work": [
        "Character Four",
        "Character One"
    ]
}
```

This dictionary structure is flattened into a single list when `sopel-waifu`
loads the waifu data at startup. For example, the above JSON translates into:

```python
[
    "Character One (Name of a Work)",
    "Character Two (Name of a Work)",
    "Character Three (Name of a Work)",
    "Character Four (Name of Another Work)",
    "Character One (Name of Another Work)",
]
```

Labeling characters in this way disambiguates between characters with the same
name from multiple sources, and allows all of them to coexist in the list if
deduplication is enabled (the default; see [below](#allowing-duplicate-waifus)
for how to allow duplicate entries).

An empty "Work" key can be used if you want to include generic characters, or
skip placing `(Franchise Name)` after the characters' names:

```json
{
    "": [
        "Generic Character",
        "Pop Culture Figure"
    ]
}
```

This becomes:

```python
[
    "Generic Character",
    "Pop Culture Figure",
]
```

Note that JSON **does not allow** trailing commas (unfortunately), so be
careful or the plugin will fail to load! It might be easiest to create the
data structure using Python's interactive console, and then export to JSON:

```pycon
>>> data = {}
>>> data["Name of a Work"] = ["Character One", "Character Two", "Character Three"]
>>> data["Name of Another Work"] = ["Character Four", "Character One"]
>>> with open('extra-waifus.json', 'w') as file:
...     json.dump(data, file, indent=4)
...
```

#### Pseudo-comments

Character entries that start with `//` will be skipped during loading. This is
provided as a way to include "comments" directly in your JSON list, since JSON
itself doesn't provide any comment syntax.

```json
{
    "Name of a Work": [
        "// primary source: https://wiki.gamecompa.ny/gamename",
        "Character One",
        "Character Two",
        "// Character Two-and-a-Half is just an alternate costume of Two",
        "Character Three"
    ]
}
```

This becomes:

```python
[
    "Character One (Name of a Work)",
    "Character Two (Name of a Work)",
    "Character Three (Name of a Work)",
]
```

### Extending the default list

By setting `json_mode` to `extend` (the default) and `json_path` to a properly
structured JSON file containing extra waifus, you can extend the default set
that ships with `sopel-waifu`.

### Replacing the default list

Setting `json_mode` to `replace` and `json_path` to a properly structured JSON
file will skip the list bundled with `sopel-waifu` and use only the contents
of _your_ file. You might want to do this if, for example, your bot focuses
heavily on non-anime content (the bundled list consists almost entirely of
anime-related characters).

### Allowing duplicate waifus

`sopel-waifu` filters duplicates from the list by default, based on their
_flattened_, or _expanded_, forms (see [JSON schema](#json-schema)), logging
any entries that appeared multiple times at the `INFO` log level.

If you want to allow duplicates, simply set `unique_waifus` to `no`.
