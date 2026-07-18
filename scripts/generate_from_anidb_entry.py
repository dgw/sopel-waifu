#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
import os
from pathlib import Path
import re
import sys
import time

import json5
from lxml import etree
import pyperclip
import requests


HTTP_API_URL = os.getenv("ANIDB_HTTP_API_URL") or "http://api.anidb.net:9001/httpapi"
HTTP_API_CLIENT = "sopelwaifuhelper"
HTTP_API_CLIENT_VERSION = "2"
HTTP_API_CLIENT_PROTOVER = "1"
USER_AGENT = "sopel-waifu-helper/1.0 (+https://github.com/dgw/sopel-waifu)"


class AnimeEntry:
    """
    A simple representation of an AniDB anime entry.
    """
    def __init__(self, aid: int, xml: etree._Element) -> None:
        self._aid = aid
        self._xml = xml

    @classmethod
    def from_xml(cls, xml: etree._Element) -> AnimeEntry:
        aid = int(xml.xpath("/anime")[0].attrib.get("id"))
        return cls(aid=aid, xml=xml)

    @property
    def aid(self) -> int:
        return self._aid

    @property
    def xml(self) -> etree._Element:
        return self._xml

    @property
    def title(self) -> str:
        return (
            self.titles.get("x-jat") or
            self.titles.get("en") or
            self.titles.get("ja")
        )

    @property
    def titles(self) -> dict[str, str]:
        possibilities = self.xml.xpath("titles/title")
        result = {}
        for title in possibilities:
            # lxml implementation detail: the "xml" namespace is stored
            # internally as the full namespace URI, and there is no apparent
            # shortcut to this
            title_lang = title.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
            title_type = title.attrib.get("type")
            if title_type in ("main", "official"):
                result[title_lang] = title.text
        return result

    @property
    def start_date(self) -> str | None:
        startdate = self.xml.xpath("startdate")[0].text
        if startdate:
            if startdate in ("0000-00-00", "1970-01-01", "unknown"):
                # I've only seen "1970-01-01" in the wild, but the others are
                # more sensible values that I wish the API would use instead.
                return None
            elif '?' in startdate:
                # This might not actually happen? Needs more test data.
                return startdate.replace('?', '9')
            return startdate
        return None

    @property
    def relations(self) -> list[int]:
        return [
            int(rel.attrib.get("id"))
            for rel in self.xml.xpath("relatedanime/anime")
            if rel.attrib.get("id")
        ]

    def _normalize_character_type(self, char_type: str) -> str:
        char_type = char_type.lower()
        match char_type:
            case "appears in":
                return "appears"
            case "secondary cast in":
                return "secondary"
            case "main character in":
                return "main"
            case "cameo appearance in":
                return "cameo"
        raise RuntimeError(f"Unknown character type: {char_type}")

    def _character_type_sort_key(self, char_type: str) -> int:
        match char_type:
            case "main":
                return 0
            case "secondary":
                return 1
            case "appears":
                return 2
            case "cameo":
                return 3
        raise RuntimeError(f"Unknown character type: {char_type}")

    @property
    def characters(self) -> list[dict[str, str]]:
        # TODO: Anime XML doesn't include character tags (needed for filtering
        # based on things like "child" age range) nor "guise of" relationships
        # needed to deduplicate disguises or alter egos (e.g. Sailor Moon /
        # Tsukino Usagi). Most of this was also missing from the AI-generated
        # prototype I started with, despite mentioning it to the model twice, so
        # it must be fairly non-trivial. (ChatGPT [I think] *tried* to get
        # "guise of" detection working, but it was by HTML-scraping the
        # individual character pages. After I told it to use ONLY the API.)
        result = {}
        for char in self.xml.xpath("characters/character"):
            char_id = char.attrib.get("id")
            char_name = char.find("name").text
            char_gender = char.find("gender").text
            if all([char_id, char_name, char_gender]):
                result[char_id] = {
                    "cid": char_id,
                    "name": char_name,
                    "type": self._normalize_character_type(
                        char.attrib.get("type"),
                    ),
                    "gender": char_gender,
                }
        sorted_result = sorted(
            result.values(),
            key=lambda r: (self._character_type_sort_key(r["type"]), r["name"])
        )
        return sorted_result

    @property
    def waifus(self) -> list[dict[str, str]]:
        """Get a list of waifu-eligible characters from this anime entry.

        Excludes "male" characters but returns all others, as AniDB somewhat
        regularly stores less popular (read: "appears in") female characters
        without a gender value.

        Characters are deduplicated by name, relying on the sorting from the
        class's own `characters` property to ensure that higher-tier instances
        of a character are kept over lower ones (e.g. "main" over "secondary",
        and both over "appears").

        "cameo" type characters are skipped; they're usually from a different
        franchise and don't belong in the waifu list for THIS show.
        """
        # TODO: Track and return "seen" character IDs as well, which would make
        # it easier for callers to omit "guise of" entries that were already
        # skipped in an earlier entry.
        # Example: c151072 "Kikoyu" is in both a18204 (skipped, same-entry name
        # match) and a19580 (script returns this one; though this SPECIFIC case
        # could be deduplicated by name only, tracking IDs would be more robust)
        seen_names = set()
        result = []
        for char in self.characters:
            if (
                char["name"] in seen_names
                or char["type"] == "cameo"
            ):
                continue
            if char["gender"] == "female":
                result.append(char)
                seen_names.add(char["name"])
        return result


class AniDBClient:
    """
    A simple AniDB client that can fetch anime entries and cache them to disk.
    """

    def __init__(self, cooldown: float = 2.0, cache_dir: Path | None = None) -> None:
        self.cooldown = cooldown
        self.cache_dir = cache_dir
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": USER_AGENT,
        })
        self.last_request = 0.0

    @property
    def request_params(self) -> dict[str, str]:
        return {
            "client": HTTP_API_CLIENT,
            "clientver": HTTP_API_CLIENT_VERSION,
            "protover": HTTP_API_CLIENT_PROTOVER,
        }

    def fetch_anime_xml(
        self,
        aid: int,
        force_fetch: bool = False,
    ) -> etree._Element:
        """
        Fetch an anime entry from AniDB by its ID.

        `force_fetch` parameter allows bypassing the cached XML and fetching a
        fresh copy from the API.
        """
        max_cache_age_seconds = 24 * 60 * 60  # 1 day
        if self.cache_dir:
            cache_file = self.cache_dir / f"{aid}.xml"
            if cache_file.exists() and not force_fetch:
                cache_age = time.time() - cache_file.stat().st_mtime
                if cache_age > max_cache_age_seconds:
                    print(
                        "Cached entry is too old ({:,} seconds); fetching fresh copy: {}".format(
                            int(cache_age),
                            cache_file,
                        ),
                        file=sys.stderr
                    )
                    cache_file = None
                else:
                    print(
                        "Using cached entry: {}".format(cache_file),
                        file=sys.stderr
                    )
                    with open(cache_file, "rb") as f:
                        return etree.fromstring(f.read())

        if self.cache_dir:
            cache_file = self.cache_dir / f"{aid}.xml"
            if cache_file.exists() and not force_fetch:
                print(
                    "Using cached entry: {}".format(cache_file),
                    file=sys.stderr
                )
                with open(cache_file, "rb") as f:
                    return etree.fromstring(f.read())

        params = self.request_params.copy()
        params.update({
            "request": "anime",
            "aid": aid,
        })
        if self.cooldown > 0:
            elapsed = time.time() - self.last_request
            if elapsed < self.cooldown:
                time.sleep(self.cooldown - elapsed)
        self.last_request = time.time()
        response = self._session.get(
            HTTP_API_URL,
            params=params,
        )
        response.raise_for_status()
        xml_content = response.content

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "wb") as f:
                f.write(xml_content)

        return etree.fromstring(xml_content)

    def fetch_anime(self, aid: int, force_fetch: bool = False) -> AnimeEntry:
        """Parse an anime entry from AniDB into an AnimeEntry, by ID.

        `force_fetch` parameter allows bypassing the cached XML and fetching a
        fresh copy from the API; it's passed to `fetch_anime_xml()`.
        """
        xml_root = self.fetch_anime_xml(aid, force_fetch=force_fetch)
        return AnimeEntry.from_xml(xml_root)


def _parse_aid(value: str) -> int:
    """
    Parse the AniDB anime ID from an input URL, or return a numeric ID as-is.
    """
    if value.isdigit():
        return int(value)
    m = re.search(r"(?:/anime/)(\d+)", value)
    if m:
        return int(m.group(1))
    raise ValueError(f"Cannot parse AniDB anime ID from: {value}")


def expand_relation_group(
    client: AniDBClient,
    starting_aid: int,
    force_fetch: bool = False,
) -> list[AnimeEntry]:
    """Get all related anime entries for a given starting entry

    This function fetches all relations of the starting anime entry and returns
    a list of AnimeEntry objects sorted by their start dates.
    """
    seen: set[int] = set()
    queue: deque[int] = deque([starting_aid])
    result: list[AnimeEntry] = []

    while queue:
        current_aid = queue.popleft()
        if current_aid in seen:
            continue
        seen.add(current_aid)

        print(
            "Fetching AniDB entry: {0:>8}{1}".format(
                current_aid,
                " (forced)" if force_fetch else ""
            ),
            file=sys.stderr
        )
        entry = client.fetch_anime(current_aid, force_fetch=force_fetch)
        for related_aid in entry.relations:
            if related_aid not in seen:
                queue.append(related_aid)
        result.append(entry)

    # unaired entries should sort to the very end, hence "9999-99-99" fallback
    return sorted(result, key=lambda e: e.start_date or "9999-99-99")


def build_output_mapping(
    entries: list[AnimeEntry],
) -> dict[str, list[str]]:
    """Build a mapping of anime titles to their waifu character names.

    This function takes a list of AnimeEntry objects and constructs a dictionary
    where each key is the anime title and the value is a list of waifu character
    names associated with that anime.

    Waifus are included only in the earliest (by start date) entry where they
    appear, and are alphabetical within groups by cast type (main, secondary,
    appears). Cameo appearances are excluded.
    """
    mapping: dict[str, list[str]] = {}
    seen: set[int] = set()

    for entry in entries:
        title = entry.title

        for waifu in entry.waifus:
            if waifu["cid"] not in seen:
                if title not in mapping:
                    mapping[title] = []
                mapping[title].append(waifu["name"])
                seen.add(waifu["cid"])

    return mapping


def main() -> int:
    # This one is mostly copied from an AI-generated prototype; I don't like
    # writing argparsers. I did clean up unused portions, reformat the code, and
    # add a few things... but the skeleton is very much from """AI""".
    ap = argparse.ArgumentParser(
        description="Build waifu list snippet from an AniDB anime entry."
    )
    ap.add_argument(
        "starting_entry",
        nargs="?",  # prompted later if empty (None)
        help="AniDB anime ID (e.g. 1234) or full AniDB anime URL."
    )
    ap.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds).")
    ap.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(__file__).resolve().parent / ".anidb_cache",
        help="Disk cache directory for AniDB API/scrape responses.",
    )
    ap.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cached AniDB XML and fetch fresh copies from the API.",
    )
    args = ap.parse_args()

    if args.starting_entry is None:
        args.starting_entry = input("Entry ID or URL: ").strip()
        if not args.starting_entry:
            print("No entry provided; exiting.", file=sys.stderr)
            return 1

    client = AniDBClient(cooldown=args.delay, cache_dir=args.cache_dir)
    entries = expand_relation_group(
        client,
        _parse_aid(args.starting_entry),
        force_fetch=args.no_cache
    )
    mapping = build_output_mapping(entries)

    rendered = json5.dumps(
        mapping, ensure_ascii=False, indent=4, quote_keys=True,
    )
    # [2:-3] removes the outer braces
    rendered = rendered[2:-3] + ",\n"
    sys.stderr.write("\nGenerated snippet:\n\n")
    sys.stdout.write(rendered)
    pyperclip.copy(rendered)
    sys.stderr.write("\n📋 Copied the above snippet to the clipboard.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
