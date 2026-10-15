"""Pure functions that turn CSV text into clean values, following the rules of ADR 0003.

None of them touches the database, so each rule is tested on its own. A function returns the clean value
(None when the CSV has no data) and, when it had to correct something, the code of that correction, which the
load counts. When the text can't be read, it raises InvalidValue with the reason recorded for the row.
"""

import re
from typing import NamedTuple

YEAR_MIN = 1880

# Language names that contain the list separator (ISO 639-2 style), checked against the whole CSV.
COMMA_NAMES = frozenset({"Greek, Ancient (to 1453)", "Norse, Old"})

_ID = re.compile(r"tt[0-9]{7,8}")
_YEAR = re.compile(r"(?<![0-9])[0-9]{4}(?![0-9])")
_COUNT = re.compile(r"[0-9]+")
_WHOLE = re.compile(r"([0-9]+)(\.0+)?")
_RATING = re.compile(r"[0-9]{1,2}(\.[0-9])?")
_MONEY = re.compile(r"(\$|[A-Z]{3}) ([0-9]+)")
_MOJIBAKE = re.compile(r"Ã[\x80-\xbf]|Â[\x80-\xbf]|â€")
_BIGINT_MAX = 2**63 - 1
INT_MAX = 2**31 - 1
SMALLINT_MAX = 2**15 - 1
# No column holds more digits than a bigint. Over 4,300, int() raises a plain ValueError instead of rejecting the row.
_MAX_DIGITS = len(str(_BIGINT_MAX))


class InvalidValue(ValueError):
    """The text doesn't have the expected format. The message is the reason recorded for the row."""


class Money(NamedTuple):
    amount: int
    currency: str


def parse_id(text: str) -> str:
    if not _ID.fullmatch(text):
        raise InvalidValue("malformed imdb_title_id")
    return text


def _to_int(digits: str, reason: str) -> int:
    """The integer of a string of ASCII digits; one too long for any column is an InvalidValue with that reason."""
    significant = digits.lstrip("0") or "0"
    if len(significant) > _MAX_DIGITS:
        raise InvalidValue(reason)
    return int(significant)


# Characters that change how a text is shown without being part of it: C0 and C1 controls, the bidirectional
# overrides and isolates (U+202E can show "txt.exe" as "exe.txt"), the zero-width space, the line and paragraph
# separators and a BOM in the middle of a text. ZWJ and ZWNJ (U+200C, U+200D) stay: emoji and several scripts
# need them. The CSV has none of these once its mojibake is repaired.
_INVISIBLE = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u200b\u2028\u2029\u202a-\u202e\u2066-\u2069\ufeff]")


def strip_invisible(text: str) -> str:
    """The text without invisible or control characters; a tab becomes a space."""
    return _INVISIBLE.sub("", text.replace("\t", " "))


def _clean(text: str) -> str:
    # PostgreSQL can't store the NUL character in a text column: one would make the whole COPY fail.
    return text.replace("\x00", "").strip()


def parse_required_text(text: str, column: str) -> str:
    value = _clean(text)
    if not value:
        raise InvalidValue(f"empty {column}")
    return value


def parse_optional_text(text: str) -> str | None:
    return _clean(text) or None


def parse_year(text: str, max_year: int) -> tuple[int, str | None]:
    """Rule 1: a year written with text ("TV Movie 2019") is read if it has exactly one valid year in it."""
    value = text.strip()
    years = [int(token) for token in _YEAR.findall(value)]
    if not years:
        raise InvalidValue("no year")
    if len(years) > 1:
        raise InvalidValue("more than one year")
    year = years[0]
    if not YEAR_MIN <= year <= max_year:
        raise InvalidValue("year out of range")
    return year, (None if value == str(year) else "year_from_text")


def parse_count(text: str, column: str, minimum: int = 0, maximum: int = INT_MAX) -> int:
    """A required integer within the range of its column: votes, duration."""
    value_text = text.strip()
    if not _COUNT.fullmatch(value_text):
        raise InvalidValue(f"malformed {column}")
    value = _to_int(value_text, f"{column} out of range")
    if not minimum <= value <= maximum:
        raise InvalidValue(f"{column} out of range")
    return value


def parse_whole(text: str) -> tuple[int | None, str | None]:
    """Rule 2: "57.0" is the integer 57, as pandas writes integers of a column with gaps; "57.5" is invalid."""
    value = text.strip()
    if not value:
        return None, None
    match = _WHOLE.fullmatch(value)
    if not match:
        raise InvalidValue("not a whole number")
    number = _to_int(match.group(1), "number out of range")
    if number > INT_MAX:
        raise InvalidValue("number out of range")
    return number, ("whole_from_decimal" if match.group(2) else None)


def parse_score(text: str) -> tuple[int | None, str | None]:
    """Metascore: a whole number from 0 to 100, possibly written as a decimal."""
    value, correction = parse_whole(text)
    if value is not None and value > 100:
        raise InvalidValue("metascore out of range")
    return value, correction


def parse_rating(text: str) -> float:
    if not _RATING.fullmatch(text.strip()) or not 1 <= float(text) <= 10:
        raise InvalidValue("rating out of range")
    return float(text)


def parse_money(text: str) -> tuple[Money | None, str | None]:
    """Rules 3 and 4: amount and currency without conversion; "$" is USD and an amount of 0 means no data."""
    value = text.strip()
    if not value:
        return None, None
    match = _MONEY.fullmatch(value)
    if not match:
        raise InvalidValue("malformed amount")
    symbol, amount = match.group(1), _to_int(match.group(2), "amount too large")
    if amount == 0:
        return None, "zero_amount_to_null"
    if amount > _BIGINT_MAX:
        raise InvalidValue("amount too large")
    if symbol == "$":
        return Money(amount, "USD"), "dollar_sign_to_usd"
    return Money(amount, symbol), None


def parse_list(text: str) -> tuple[list[str] | None, list[str]]:
    """Rules 5 and 6: split by comma keeping names like "Norse, Old" whole, and drop repeated items."""
    items: list[str] = []
    corrections: list[str] = []
    for part in (_clean(part) for part in text.split(",")):
        if not part:
            continue
        if items and f"{items[-1]}, {part}" in COMMA_NAMES:
            items[-1] = f"{items[-1]}, {part}"
            corrections.append("comma_name_kept")
        else:
            items.append(part)
    unique = list(dict.fromkeys(items))
    if len(unique) < len(items):
        corrections.append("duplicate_items_removed")
    return (unique or None), corrections


def repair_mojibake(text: str) -> tuple[str, str | None]:
    """Rule 9: undo UTF-8 read as Windows-1252 or Latin-1, only when the reversal comes out clean."""
    if not _MOJIBAKE.search(text):
        return text, None
    for codec in ("cp1252", "latin-1"):
        try:
            fixed = text.encode(codec).decode("utf-8")
        except UnicodeError:
            continue
        if not _MOJIBAKE.search(fixed):
            return fixed, "mojibake_repaired"
    return text, "mojibake_kept"
