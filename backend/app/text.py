"""Text folding shared by the load and the search: both sides have to compare the same way."""

import re
import unicodedata

# Latin letters that NFKD doesn't decompose, mapped the way Postgres unaccent does (see the data profile).
_EXTRA_LETTERS = str.maketrans({"ø": "o", "æ": "ae", "œ": "oe", "ð": "d", "þ": "th", "ł": "l", "đ": "d"})
_SPACES = re.compile(r"\s+")


def fold(text: str) -> str:
    """Lowercase, without accents and with single spaces: "Æon  Flux" -> "aeon flux"."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACES.sub(" ", without_marks.casefold().translate(_EXTRA_LETTERS)).strip()


def like_escape(text: str) -> str:
    """Make %, _ and the escape character itself literal in a LIKE pattern (the escape is a backslash)."""
    return re.sub(r"([\\%_])", r"\\\1", text)
