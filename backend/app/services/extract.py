"""Pulls prose out of a streaming JSON response.

The LLM streams raw JSON. The UI only wants the value of each "text" field, so
this walks the stream character by character and emits just that prose.

Decoding must match json.loads() exactly: whatever the reader watches being
typed live has to equal the text that ends up in the finished book. Anything
this gets wrong appears as garbage in the live preview that then silently
"corrects" itself once the page is saved.
"""
from typing import Callable


class TextExtractor:
    # JSON's two-character escapes.
    _ESC = {
        'n': '\n', 't': '\t', 'r': '\r',
        'b': '\b', 'f': '\f',
        '"': '"', '\\': '\\', '/': '/',
    }

    def __init__(self, notify: Callable[[str], None]):
        self._notify = notify
        self._buf = ""
        self._in_value = False
        self._esc = False
        self._uni: str | None = None    # collecting the 4 hex digits after \u
        self._high: int | None = None   # pending high surrogate

    def _emit_code(self, code: int) -> None:
        r"""Emit one \uXXXX escape, joining surrogate pairs (e.g. emoji)."""
        if 0xD800 <= code <= 0xDBFF:        # high surrogate: wait for its partner
            self._high = code
            return
        if self._high is not None:
            high, self._high = self._high, None
            if 0xDC00 <= code <= 0xDFFF:    # valid pair -> one character
                self._notify(chr(0x10000 + ((high - 0xD800) << 10) + (code - 0xDC00)))
                return
            # orphaned high surrogate: drop it rather than emit a lone surrogate
        self._notify(chr(code))

    def feed(self, raw: str) -> None:
        for ch in raw:
            if self._in_value:
                if self._uni is not None:
                    self._uni += ch
                    if len(self._uni) == 4:
                        try:
                            self._emit_code(int(self._uni, 16))
                        except ValueError:
                            pass            # malformed escape: skip it
                        self._uni = None
                elif self._esc:
                    self._esc = False
                    if ch == 'u':
                        self._uni = ""
                    else:
                        self._notify(self._ESC.get(ch, ch))
                elif ch == '\\':
                    self._esc = True
                elif ch == '"':
                    self._in_value = False
                    self._buf = ""
                    self._high = None
                else:
                    self._notify(ch)
            else:
                self._buf += ch
                if self._buf.endswith('"'):
                    tail = self._buf[-20:].replace(' ', '')
                    if tail.endswith('"text":"'):
                        self._in_value = True
                        self._buf = ""
                if len(self._buf) > 60:
                    self._buf = self._buf[-60:]
