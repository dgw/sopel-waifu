# Contributing to `sopel-waifu`

As prerequisites you will need `pip` >= 25.1, and GNU `make` (or compatible).

Start by cloning the repository (make a fork first if you plan to submit a pull
request), and `make install-dev` in a fresh venv.

## Adding new waifus

Edit `sopel_waifu/waifu.json5`, following the style you see in the existing
entries. Character order is generally matched to AniDB's display sort, i.e.
alphabetical within each of the "Main character", "Secondary cast", and "Appears
in" groups. ("Cameo appearance" is not included, except in very specific
circumstances; if in doubt, ask in the relevant issue, or open your pull request
as a draft and ask there.)

Use `// json5 comments` to add context, or disable entries who should be
mentioned for completeness but not included in the final list (e.g. Tsukino
Usagi's alter ego "Sailor Moon"; add such things as a nickname within the
character's main entry instead, like `"Tsukino \"Sailor Moon\" Usagi"`).

Also use `// json5 comments` to denote the `Next:` and `Previous:` entries if
alphabetical sorting of the titles places them out of order, and especially if
they are separated (e.g. a movie in between seasons, which usually winds up
under "G" for "Gekijouban").

Running `make` by itself will lint your current copy of `waifu.json5`, though
not everything can be checked automatically. If the linter flags a sort order
issue it can probably be fixed automatically by `make sort`.

### Quick and dirty new entries

Run `make entry` and enter an anime ID from AniDB when prompted. A script will
fetch what information it can from AniDB's API for *that relation group* (all
prequels, sequels, OVAs, etc. that AniDB knows about) and copy a snippet to the
clipboard for you.

**IMPORTANT: Do not submit this snippet without checking it first against the
cast list yourself.** The generator script cannot account for any of the below
conditions, nor other edge cases the author hasn't yet documented:

- "child" characters
- characters whose "name" is just a title or generic description, e.g. "Shoujo"
  ("girl"), "Kyoushi" ("instructor")
- characters with no gender set (only "male" is excluded; all others are
  included for manual review)
- characters without their own character page; these are usually background
  characters in the "Appears" section

When you omit a character due to one of these cases, it's preferred to comment
out their name rather than deleting it, and indicate which reason was applied.
For example:

```json5
        // "Pitz",  // pet squirrel, and gender unclear; skip
```

Please also put any additions the script didn't pick up after a comment, e.g.:

```json5
    "Uchuu no Stellvia": [
        /* ... top of list omitted for brevity ... */
        "Renge Ren",
        "Kazamatsuri Natasha",
        // Incomplete character entries that belong per educated guesses
        // These don't appear in the XML since they don't have full entries w/CIDs
        "Akiko Mills",
        "Kusanagi Youko",
    ],
```
