"""duplicate_detect.py

Detect duplicate keys in a JSON file, exiting non-zero if found.

Based on the detection routines from @htv2012's gist 🫡:
https://gist.github.com/htv2012/ad8c19ac43e128aa7ee1

Adopted these validation functions because they're very portable, requiring
only Python's stdlib.
"""
from __future__ import annotations

import collections
import json
import sys


# detection logic adapted from our savior @htv2012's gist
# just flattened into a single function
def validate_data(list_of_pairs):
    key_count = collections.Counter(k for k,v in list_of_pairs)
    if duplicate_keys := ', '.join(k for k,v in key_count.items() if v>1):
        raise ValueError('Duplicate key(s) found: {}'.format(duplicate_keys))

    return dict(list_of_pairs)


# our CLI logic
with open(sys.argv[1]) as f:
    try:
        json.load(f, object_pairs_hook=validate_data)
    except ValueError as exc:
        print("{err} ❌".format(err=exc))
        sys.exit(1)
    else:
        print("No duplicate keys detected! ✅")
        sys.exit(0)
