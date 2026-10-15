"""Each cleaning rule of ADR 0003, with its edge cases. Pure functions: no database needed."""

import pytest

from app.etl.parsers import (
    InvalidValue,
    Money,
    parse_count,
    parse_id,
    parse_list,
    parse_money,
    parse_optional_text,
    parse_rating,
    parse_required_text,
    parse_score,
    parse_whole,
    parse_year,
    repair_mojibake,
)
from app.text import fold, like_escape


class TestYear:
    def test_plain_year(self) -> None:
        assert parse_year("2019", 2026) == (2019, None)

    def test_year_inside_text_is_extracted_with_a_correction(self) -> None:
        assert parse_year("TV Movie 2019", 2026) == (2019, "year_from_text")

    @pytest.mark.parametrize(
        ("text", "reason"),
        [
            ("1999 2001", "more than one year"),
            ("abc", "no year"),
            ("", "no year"),
            ("1850", "year out of range"),
            ("2031", "year out of range"),
            ("12019", "no year"),  # part of a longer number, not a year
        ],
    )
    def test_rejected(self, text: str, reason: str) -> None:
        with pytest.raises(InvalidValue, match=reason):
            parse_year(text, 2030)


class TestWholeNumbers:
    @pytest.mark.parametrize(("text", "expected"), [("57", (57, None)), ("57.0", (57, "whole_from_decimal"))])
    def test_integers_and_integers_written_as_decimals(self, text: str, expected: tuple[int, str | None]) -> None:
        assert parse_whole(text) == expected

    def test_empty_is_no_data(self) -> None:
        assert parse_whole("") == (None, None)

    @pytest.mark.parametrize("text", ["57.5", "1e3", "-3", "nan"])
    def test_anything_else_is_invalid(self, text: str) -> None:
        with pytest.raises(InvalidValue):
            parse_whole(text)


class TestRequiredNumbers:
    def test_count(self) -> None:
        assert parse_count("2278845", "votes") == 2278845

    @pytest.mark.parametrize("text", ["", "12.5", "-1", "1,000"])
    def test_malformed_count(self, text: str) -> None:
        with pytest.raises(InvalidValue, match="malformed votes"):
            parse_count(text, "votes")

    def test_count_out_of_the_column_range(self) -> None:
        with pytest.raises(InvalidValue, match="duration out of range"):
            parse_count("0", "duration", minimum=1)
        with pytest.raises(InvalidValue, match="duration out of range"):
            parse_count("40000", "duration", maximum=32767)

    def test_numbers_too_long_for_int_are_invalid_values(self) -> None:
        """int() refuses more than 4,300 digits with a plain ValueError, which stopped the whole load."""
        huge = "9" * 5000
        with pytest.raises(InvalidValue, match="votes out of range"):
            parse_count(huge, "votes")
        with pytest.raises(InvalidValue, match="number out of range"):
            parse_whole(huge + ".0")
        with pytest.raises(InvalidValue, match="amount too large"):
            parse_money(f"$ {huge}")

    def test_leading_zeros_do_not_count_as_digits(self) -> None:
        assert parse_count("0" * 5000 + "42", "votes") == 42

    @pytest.mark.parametrize(("text", "expected"), [("80.0", (80, "whole_from_decimal")), ("0", (0, None))])
    def test_score(self, text: str, expected: tuple[int, str | None]) -> None:
        assert parse_score(text) == expected

    def test_score_over_100(self) -> None:
        with pytest.raises(InvalidValue, match="metascore out of range"):
            parse_score("101")

    @pytest.mark.parametrize(("text", "expected"), [("9.3", 9.3), ("1.0", 1.0), ("10", 10.0)])
    def test_rating(self, text: str, expected: float) -> None:
        assert parse_rating(text) == expected

    @pytest.mark.parametrize("text", ["0.5", "10.5", "9.35", "", "abc"])
    def test_rating_out_of_range_or_malformed(self, text: str) -> None:
        with pytest.raises(InvalidValue, match="rating out of range"):
            parse_rating(text)


class TestMoney:
    def test_dollar_sign_is_usd(self) -> None:
        assert parse_money("$ 25000000") == (Money(25000000, "USD"), "dollar_sign_to_usd")

    def test_other_currencies_are_kept_without_conversion(self) -> None:
        assert parse_money("EUR 5000") == (Money(5000, "EUR"), None)

    def test_amounts_beyond_int32_fit(self) -> None:
        assert parse_money("IRR 350000000000") == (Money(350000000000, "IRR"), None)

    def test_zero_means_no_data(self) -> None:
        assert parse_money("$ 0") == (None, "zero_amount_to_null")
        assert parse_money("GBP 0") == (None, "zero_amount_to_null")

    def test_empty_is_no_data(self) -> None:
        assert parse_money("") == (None, None)

    @pytest.mark.parametrize("text", ["25000000", "$25000000", "usd 5", "EUR 5.5", "EURO 5"])
    def test_malformed(self, text: str) -> None:
        with pytest.raises(InvalidValue, match="malformed amount"):
            parse_money(text)


class TestLists:
    def test_split_and_trim(self) -> None:
        assert parse_list("Crime, Drama") == (["Crime", "Drama"], [])

    def test_names_with_a_comma_stay_whole(self) -> None:
        assert parse_list("English, Latin, Swedish, Norse, Old, Danish, Arabic") == (
            ["English", "Latin", "Swedish", "Norse, Old", "Danish", "Arabic"],
            ["comma_name_kept"],
        )
        assert parse_list("English, Greek, Ancient (to 1453)")[0] == ["English", "Greek, Ancient (to 1453)"]

    def test_repeated_items_are_dropped_keeping_the_order(self) -> None:
        # Goodfellas: Pileggi is credited for the book and for the screenplay.
        assert parse_list("Nicholas Pileggi, Nicholas Pileggi") == (["Nicholas Pileggi"], ["duplicate_items_removed"])

    def test_none_is_kept_as_a_language(self) -> None:
        # "None" means no dialogue (rule 7): it is data, not a null.
        assert parse_list("None") == (["None"], [])
        assert parse_list("English, None") == (["English", "None"], [])

    def test_empty_is_no_data(self) -> None:
        assert parse_list("") == (None, [])
        assert parse_list(" , ") == (None, [])


class TestMojibake:
    def test_reversible_text_is_repaired(self) -> None:
        assert repair_mojibake("finds his fiancÃ© with another man") == (
            "finds his fiancé with another man",
            "mojibake_repaired",
        )

    def test_latin1_case(self) -> None:
        # "Á" in UTF-8 has a byte (0x81) that Windows-1252 doesn't define, so it needs Latin-1.
        assert repair_mojibake("Ã\x81lvaro finds the body") == ("Álvaro finds the body", "mojibake_repaired")

    def test_irreversible_text_is_kept(self) -> None:
        text = "love music Ã¢ÂEURÂ\x9d just not"
        assert repair_mojibake(text) == (text, "mojibake_kept")

    def test_healthy_text_is_not_touched(self) -> None:
        for text in ("Amélie", "São Paulo", "Ãlvaro is a name", "plain text"):
            assert repair_mojibake(text) == (text, None)


class TestText:
    def test_required_text_is_trimmed(self) -> None:
        assert parse_required_text("  Up ", "title") == "Up"

    def test_empty_required_text_is_invalid(self) -> None:
        with pytest.raises(InvalidValue, match="empty title"):
            parse_required_text("   ", "title")

    def test_nul_characters_are_removed(self) -> None:
        # PostgreSQL can't store them; one would make the whole COPY fail.
        assert parse_optional_text("Before\x00after") == "Beforeafter"
        assert parse_list("English,\x00None")[0] == ["English", "None"]

    def test_empty_optional_text_is_no_data(self) -> None:
        assert parse_optional_text("  ") is None


class TestIds:
    @pytest.mark.parametrize("text", ["tt0111161", "tt10000000"])
    def test_valid(self, text: str) -> None:
        assert parse_id(text) == text

    @pytest.mark.parametrize("text", ["tt123", "0111161", "tt01111611x", "TT0111161", ""])
    def test_invalid(self, text: str) -> None:
        with pytest.raises(InvalidValue):
            parse_id(text)


class TestFolding:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Le fabuleux destin d'Amélie Poulain", "le fabuleux destin d'amelie poulain"),
            ("Æon Flux", "aeon flux"),
            ("Død snø", "dod sno"),
            ("Relatos  salvajes ", "relatos salvajes"),
            ("STRASSE", "strasse"),
        ],
    )
    def test_fold(self, text: str, expected: str) -> None:
        assert fold(text) == expected

    def test_like_wildcards_are_escaped(self) -> None:
        assert like_escape("100% E_mail \\") == "100\\% E\\_mail \\\\"
