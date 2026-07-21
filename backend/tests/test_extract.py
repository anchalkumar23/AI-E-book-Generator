import json

from app.services.extract import TextExtractor


def collect(chunks: list[str]) -> str:
    out: list[str] = []
    ex = TextExtractor(out.append)
    for c in chunks:
        ex.feed(c)
    return "".join(out)


def test_emits_only_text_field_prose():
    raw = '{"pages":[{"heading":"H","text":"Hello world","page_number":1}]}'
    assert collect([raw]) == "Hello world"


def test_ignores_other_string_fields():
    raw = '{"pages":[{"heading":"Ignore me","text":"Keep me"}]}'
    assert collect([raw]) == "Keep me"


def test_decodes_escape_sequences():
    raw = '{"text":"Line one\\nLine two"}'
    assert collect([raw]) == "Line one\nLine two"


def test_escaped_quote_does_not_end_the_value():
    raw = '{"text":"She said \\"hi\\" loudly"}'
    assert collect([raw]) == 'She said "hi" loudly'


def test_works_when_split_across_token_boundaries():
    """Tokens arrive in arbitrary chunks — the marker can be split in half."""
    assert collect(['{"te', 'xt":"Hel', 'lo"}']) == "Hello"


def test_handles_multiple_text_fields():
    raw = '{"pages":[{"text":"One"},{"text":"Two"}]}'
    assert collect([raw]) == "OneTwo"


# ── \uXXXX escapes ────────────────────────────────────────────────────────────
# Models emit these for smart quotes, accents and dashes. The live preview must
# match what json.loads() puts in the finished book, or the reader sees
# "itu2019s" typed out and then silently corrected to "it's".
#
# NOTE: chr(92) is used to build a REAL backslash. Writing '\\u00ef' in a test
# would be decoded by Python's own literal parser, so the extractor would never
# see an escape and the test would pass while proving nothing.

B = chr(92)


def test_decodes_unicode_escapes():
    raw = '{"text":"na' + B + 'u00efve it' + B + 'u2019s"}'
    assert collect([raw]) == json.loads(raw)["text"] == "naïve it’s"


def test_unicode_escape_split_across_token_boundaries():
    assert collect(['{"text":"a' + B + 'u20', '19b"}']) == "a’b"


def test_decodes_surrogate_pair():
    """Emoji arrive as two escapes that must be combined into one character."""
    raw = '{"text":"hi ' + B + 'ud83d' + B + 'ude00"}'
    assert collect([raw]) == json.loads(raw)["text"] == "hi 😀"


def test_decodes_control_escapes_like_json():
    raw = '{"text":"a' + B + 'tb' + B + '/c"}'
    assert collect([raw]) == json.loads(raw)["text"] == "a\tb/c"
