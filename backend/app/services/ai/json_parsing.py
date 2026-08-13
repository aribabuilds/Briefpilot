"""Shared lenient JSON-value extraction for LLM responses.

Even with response_mime_type="application/json" (structured-output mode), a
provider does not reliably return ONLY the JSON value -- confirmed live
against gemini-3.5-flash across two separate real calls: one appended an
explanatory sentence AFTER an otherwise perfect JSON object, another wrapped
it with prose BEFORE it (both still returned HTTP 200). Plain `json.loads`
rejects both outright, silently degrading a genuinely correct extraction to
entirely null -- the null-not-guess fallback firing for the wrong reason, on
a response that was not actually malformed.

This finds the first `{` or `[` in the (code-fence-stripped) text and lets
`json.JSONDecoder.raw_decode` parse one JSON value from there, deliberately
ignoring whatever precedes or follows it. What still counts as genuinely
malformed -- no JSON-looking character anywhere, or a broken/truncated JSON
body -- still returns None, exactly as before.
"""

import re
from json import JSONDecodeError, JSONDecoder
from typing import cast

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

_decoder = JSONDecoder()


def extract_json_value(raw_text: str) -> object | None:
    cleaned = _CODE_FENCE_RE.sub("", raw_text).strip()
    start = _first_json_start(cleaned)
    if start is None:
        return None
    try:
        value, _end_index = _decoder.raw_decode(cleaned, start)
    except JSONDecodeError:
        return None
    return cast(object, value)


def _first_json_start(text: str) -> int | None:
    for index, char in enumerate(text):
        if char in "{[":
            return index
    return None
