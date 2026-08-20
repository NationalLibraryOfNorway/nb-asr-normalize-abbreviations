#!/usr/bin/env python3
"""
Clean and normalize Norwegian ASR text in JSONL files.

The script applies two normalization layers:

1. Expand common Norwegian prose abbreviations:
       "o.s.v."  -> "og så videre"
       "f.eks."  -> "for eksempel"
       "dvs."    -> "det vil si"

2. Normalize scientific and medical units only when they follow:
       - a number written with digits, or
       - the placeholder <NUM>
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Sequence, TextIO

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - exercised only in minimal environments
    def tqdm(iterable, **_: object):  # type: ignore[no-redef]
        return iterable


LOGGER = logging.getLogger("clean_asr_jsonl")

NUMBER_PATTERN = (
    r"(?:"
    r"<NUM>"
    r"|"
    r"[+-]?(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,]\d+)?"
    r"(?:\s*[–-]\s*[+-]?(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,]\d+)?)?"
    r")"
)


@dataclass(frozen=True)
class ReplacementRule:
    """A compiled regex replacement rule."""

    pattern: re.Pattern[str]
    replacement: str


def compile_rule(pattern: str, replacement: str, *, ignore_case: bool = True) -> ReplacementRule:
    """Compile one replacement rule."""
    flags = re.IGNORECASE if ignore_case else 0
    return ReplacementRule(pattern=re.compile(pattern, flags), replacement=replacement)


def literal_abbreviation_pattern(abbreviation: str) -> str:
    """Build a conservative regex for a literal abbreviation."""
    return rf"(?<![\w@]){re.escape(abbreviation)}(?![\w@])"


GENERAL_ABBREVIATIONS: Sequence[tuple[str, str, tuple[str, ...]]] = (
    (r"(?<![\w@])(?:f\.?\s*o\.?\s*m\.?|fom\.?)(?![\w@])", "fra og med", ()),
    (r"(?<![\w@])(?:t\.\s*o\.\s*m\.?|t\.o\.m\.?|t\.o\.m)(?![\w@])", "til og med", ()),
    (r"(?<![\w@])(?:o\.?\s*s\.?\s*v\.?|osv\.?)(?![\w@])", "og så videre", ()),
    (r"(?<![\w@])(?:o\.?\s*s\.?\s*b\.?|osb\.?)(?![\w@])", "og så bortetter", ()),
    (r"(?<![\w@])(?:f\.?\s*eks\.?|feks\.?)(?![\w@])", "for eksempel", ()),
    (r"(?<![\w@])(?:bl\.\s*a\.?|bl\.a\.?)(?![\w@])", "blant annet", ()),
    (r"(?<![\w@])(?:m\.\s*m\.?|m\.m\.?)(?![\w@])", "med mer", ()),
    (r"(?<![\w@])(?:o\.\s*l\.?|o\.l\.?|ol\.)(?![\w@])", "og lignende", ("OL",)),
    (r"(?<![\w@])(?:e\.\s*l\.?|e\.l\.?)(?![\w@])", "eller lignende", ()),
    (r"(?<![\w@])(?:d\.?\s*v\.?\s*s\.?|dvs\.?)(?![\w@])", "det vil si", ("DVS",)),
    (r"(?<![\w@])(?:m\.?\s*a\.?\s*o\.?|mao\.?)(?![\w@])", "med andre ord", ()),
    (r"(?<![\w@])(?:p\.?\s*g\.?\s*a\.?|pga\.?)(?![\w@])", "på grunn av", ("PGA",)),
    (r"(?<![\w@])(?:i\.?\s*h\.?\s*t\.?|iht\.?)(?![\w@])", "i henhold til", ()),
    (r"(?<![\w@])(?:i\.?\s*f\.?\s*m\.?|ifm\.?)(?![\w@])", "i forbindelse med", ()),
    (r"(?<![\w@])(?:i\.?\s*f\.?\s*t\.?|ift\.?)(?![\w@])", "i forhold til", ()),
    (r"(?<![\w@])(?:v\.?\s*h\.?\s*a\.?|vha\.?)(?![\w@])", "ved hjelp av", ()),
    (r"(?<![\w@])(?:m\.?\s*h\.?\s*t\.?|mht\.?)(?![\w@])", "med hensyn til", ()),
    (r"(?<![\w@])(?:m\.?\s*t\.?\s*p\.?|mtp\.?)(?![\w@])", "med tanke på", ()),
    (r"(?<![\w@])(?:p\.\s*t\.?|p\.t\.?|pt\.)(?![\w@])", "for tiden", ("PT",)),
    (r"(?<![\w@])(?:f\.\s*t\.?|f\.t\.?|ft\.)(?![\w@])", "for tiden", ("FT",)),
    (r"(?<![\w@])(?:d\.\s*d\.?|d\.d\.?|dd\.)(?![\w@])", "dags dato", ()),
    (r"(?<![\w@])(?:s\.\s*d\.?|s\.d\.?|sd\.)(?![\w@])", "se denne", ()),
    (r"(?<![\w@])(?:h\.?\s*h\.?\s*v\.?|hhv\.?)(?![\w@])", "henholdsvis", ()),
    (r"(?<![\w@])vedr\.?(?![\w@])", "vedrørende", ()),
    (r"(?<![\w@])ang\.?(?![\w@])", "angående", ()),
    (r"(?<![\w@])inkl\.?(?![\w@])", "inkludert", ()),
    (r"(?<![\w@])ekskl\.?(?![\w@])", "ekskludert", ()),
    (r"(?<![\w@])maks\.?(?![\w@])", "maksimalt", ()),
    (r"(?<![\w@])min\.(?=\s+[\w\d]|[/–-])", "minimum", ()),
    (r"(?<![\w@])(?:ca\.?)(?![\w@])", "cirka", ("CA",)),
    (r"(?<![\w@])(?:evt\.?|ev\.?)(?![\w@])", "eventuelt", ()),
    (r"(?<![\w@])(?:jf\.?|jfr\.?)(?![\w@])", "jamfør", ()),
    (r"(?<![\w@])fig\.?(?![\w@])", "figur", ()),
    (r"(?<![\w@])tab\.(?![\w@])", "tabell", ()),
    (r"(?<![\w@])kap\.?(?![\w@])", "kapittel", ()),
    (r"(?<![\w@])pkt\.?(?![\w@])", "punkt", ()),
    (r"(?<![\w@])spm\.?(?![\w@])", "spørsmål", ()),
    (r"(?<![\w@])mill\.?(?![\w@])", "millioner", ()),
    (r"(?<![\w@])mrd\.?(?![\w@])", "milliarder", ()),
)

UNIT_EXPRESSIONS: Sequence[tuple[str, str]] = (
    (r"milli[\s-]*internasjonale?\s+enheter?\s+per\s+liter", "mIU/l"),
    (r"internasjonale?\s+enheter?\s+per\s+liter", "IU/l"),
    (r"milliekvivalenter?\s+per\s+liter", "mEq/l"),
    (r"millimol\s+per\s+liter", "mmol/l"),
    (r"mikromol\s+per\s+liter", "µmol/l"),
    (r"nanomol\s+per\s+liter", "nmol/l"),
    (r"mol\s+per\s+liter", "mol/l"),
    (r"nanogram\s+per\s+milliliter", "ng/ml"),
    (r"mikrogram\s+per\s+milliliter", "µg/ml"),
    (r"milligram\s+per\s+milliliter", "mg/ml"),
    (r"gram\s+per\s+milliliter", "g/ml"),
    (r"nanogram\s+per\s+liter", "ng/l"),
    (r"mikrogram\s+per\s+liter", "µg/l"),
    (r"milligram\s+per\s+liter", "mg/l"),
    (r"gram\s+per\s+liter", "g/l"),
    (r"nanogram\s+per\s+kilogram", "ng/kg"),
    (r"mikrogram\s+per\s+kilogram", "µg/kg"),
    (r"milligram\s+per\s+kilogram", "mg/kg"),
    (r"gram\s+per\s+kilogram", "g/kg"),
    (r"mikroliter\s+per\s+kilogram", "µl/kg"),
    (r"milliliter\s+per\s+kilogram", "ml/kg"),
    (r"liter\s+per\s+kilogram", "l/kg"),
    (r"kilometer\s+(?:i|per)\s+timen?", "km/t"),
    (r"kilometer\s+per\s+time", "km/t"),
    (r"meter\s+per\s+sekund\s+(?:i\s+andre|kvadrert)", "m/s²"),
    (r"meter\s+per\s+sekund\s+per\s+sekund", "m/s²"),
    (r"meter\s+per\s+sekund", "m/s"),
    (r"watt\s+per\s+kvadratmeter", "W/m²"),
    (r"kilogram\s+per\s+kvadratmeter", "kg/m²"),
    (r"grader?\s+celsius", "°C"),
    (r"celsiusgrader?", "°C"),
    (r"grader?\s+fahrenheit", "°F"),
    (r"fahrenheitgrader?", "°F"),
    (r"terawatt[\s-]*timer?", "TWh"),
    (r"gigawatt[\s-]*timer?", "GWh"),
    (r"megawatt[\s-]*timer?", "MWh"),
    (r"kilowatt[\s-]*timer?", "kWh"),
    (r"watt[\s-]*timer?", "Wh"),
    (r"terabit\s+per\s+sekund", "Tbit/s"),
    (r"gigabit\s+per\s+sekund", "Gbit/s"),
    (r"megabit\s+per\s+sekund", "Mbit/s"),
    (r"kilobit\s+per\s+sekund", "kbit/s"),
    (r"terabyte\s+per\s+sekund", "TB/s"),
    (r"gigabyte\s+per\s+sekund", "GB/s"),
    (r"megabyte\s+per\s+sekund", "MB/s"),
    (r"kilobyte\s+per\s+sekund", "kB/s"),
    (r"kvadratmillimeter", "mm²"),
    (r"kvadratcentimeter", "cm²"),
    (r"kvadratkilometer", "km²"),
    (r"kvadratmeter", "m²"),
    (r"kubikkmillimeter", "mm³"),
    (r"kubikkcentimeter", "cm³"),
    (r"kubikk-?kilometer", "km³"),
    (r"kubikkmeter", "m³"),
    (r"milli[\s-]*internasjonale?\s+enheter?", "mIU"),
    (r"internasjonale?\s+enheter?", "IU"),
    (r"milliekvivalenter?", "mEq"),
    (r"mikrokatal", "µkat"),
    (r"nanokatal", "nkat"),
    (r"katal", "kat"),
    (r"millimol", "mmol"),
    (r"mikromol", "µmol"),
    (r"nanomol", "nmol"),
    (r"mol", "mol"),
    (r"mikrosekunder?", "µs"),
    (r"millisekunder?", "ms"),
    (r"sekunder?", "s"),
    (r"minutter?", "min"),
    (r"timer?", "h"),
    (r"nanomet(?:er|re)", "nm"),
    (r"mikromet(?:er|re)", "µm"),
    (r"millimet(?:er|re)", "mm"),
    (r"centimet(?:er|re)", "cm"),
    (r"kilomet(?:er|re)", "km"),
    (r"met(?:er|re)", "m"),
    (r"mikrolit(?:er|re)", "µl"),
    (r"millilit(?:er|re)", "ml"),
    (r"centilit(?:er|re)", "cl"),
    (r"desilit(?:er|re)", "dl"),
    (r"lit(?:er|re)", "l"),
    (r"nanogram", "ng"),
    (r"mikrogram", "µg"),
    (r"milligram", "mg"),
    (r"kilogram", "kg"),
    (r"gram", "g"),
    (r"tonn", "t"),
    (r"gigahertz", "GHz"),
    (r"megahertz", "MHz"),
    (r"kilohertz", "kHz"),
    (r"hertz", "Hz"),
    (r"mikrovolt", "µV"),
    (r"millivolt", "mV"),
    (r"kilovolt", "kV"),
    (r"megavolt", "MV"),
    (r"volt", "V"),
    (r"mikroampere", "µA"),
    (r"milliampere", "mA"),
    (r"kiloampere", "kA"),
    (r"ampere", "A"),
    (r"milliwatt", "mW"),
    (r"kilowatt", "kW"),
    (r"megawatt", "MW"),
    (r"gigawatt", "GW"),
    (r"terawatt", "TW"),
    (r"watt", "W"),
    (r"terabyte", "TB"),
    (r"gigabyte", "GB"),
    (r"megabyte", "MB"),
    (r"kilobyte", "kB"),
    (r"byte", "B"),
    (r"terabit", "Tbit"),
    (r"gigabit", "Gbit"),
    (r"megabit", "Mbit"),
    (r"kilobit", "kbit"),
    (r"bit", "bit"),
    (r"prosent", "%"),
    (r"promille", "‰"),
)

UNIT_ALIASES: Sequence[tuple[str, str]] = (
    (r"km\s*/\s*(?:h|time)", "km/t"),
    (r"km\s+per\s+(?:h|time)", "km/t"),
    (r"k\s*w\s*h", "kWh"),
    (r"kwh", "kWh"),
    (r"kwt", "kWh"),
    (r"mwh", "MWh"),
    (r"mwt", "MWh"),
    (r"gwh", "GWh"),
    (r"gwt", "GWh"),
    (r"twh", "TWh"),
    (r"twt", "TWh"),
    (r"μmol\s*/\s*l", "µmol/l"),
    (r"umol\s*/\s*l", "µmol/l"),
    (r"μg\s*/\s*l", "µg/l"),
    (r"ug\s*/\s*l", "µg/l"),
    (r"μg\s*/\s*ml", "µg/ml"),
    (r"ug\s*/\s*ml", "µg/ml"),
    (r"μg\s*/\s*kg", "µg/kg"),
    (r"ug\s*/\s*kg", "µg/kg"),
    (r"m\s*(?:\^?2|²)", "m²"),
    (r"cm\s*(?:\^?2|²)", "cm²"),
    (r"mm\s*(?:\^?2|²)", "mm²"),
    (r"km\s*(?:\^?2|²)", "km²"),
    (r"m\s*(?:\^?3|³)", "m³"),
    (r"cm\s*(?:\^?3|³)", "cm³"),
    (r"mm\s*(?:\^?3|³)", "mm³"),
    (r"km\s*(?:\^?3|³)", "km³"),
    (r"μl", "µl"),
    (r"ul", "µl"),
    (r"μg", "µg"),
    (r"ug", "µg"),
    (r"μmol", "µmol"),
    (r"umol", "µmol"),
    (r"μkat", "µkat"),
    (r"ukat", "µkat"),
)


class TextNormalizer:
    """Reusable Norwegian ASR text normalizer."""

    def __init__(
        self,
        *,
        expand_abbreviations: bool = True,
        normalize_units: bool = True,
        normalize_whitespace: bool = True,
        normalize_numbers: bool = True,
        normalize_dates: bool = True,
    ) -> None:
        self.expand_abbreviations = expand_abbreviations
        self.normalize_units = normalize_units
        self.normalize_whitespace = normalize_whitespace
        self.normalize_numbers = normalize_numbers
        self.normalize_dates = normalize_dates
        self._abbreviation_rules = tuple(
            (
                re.compile(pattern, re.IGNORECASE),
                self._create_abbrev_sub(replacement, preserve_caps),
            )
            for pattern, replacement, preserve_caps in GENERAL_ABBREVIATIONS
        )
        self._unit_rules = tuple(
            self._compile_number_unit_rule(pattern, replacement)
            for pattern, replacement in UNIT_EXPRESSIONS
        )
        self._unit_alias_rules = tuple(
            self._compile_number_unit_rule(pattern, replacement)
            for pattern, replacement in UNIT_ALIASES
        )
        self._paragraph_plural_rule = compile_rule(
            rf"(?<!\w)paragrafene\s+(?P<first>{NUMBER_PATTERN})\s+og\s+"
            rf"(?P<second>{NUMBER_PATTERN})(?!\w)",
            r"§§ \g<first> og \g<second>",
        )
        self._paragraph_rule = compile_rule(
            rf"(?<!\w)paragraf\s+(?P<number>{NUMBER_PATTERN})(?!\w)",
            r"§ \g<number>",
        )
        self._number_symbol_spacing_rule = re.compile(
            rf"(?P<number>{NUMBER_PATTERN})\s*(?P<symbol>%|‰|°C|°F)",
            re.IGNORECASE,
        )
        self._degree_angle_spacing_rule = re.compile(
            rf"(?P<number>{NUMBER_PATTERN})\s+°(?![CFcf])"
        )

    @staticmethod
    def _compile_number_unit_rule(unit_pattern: str, canonical_unit: str) -> ReplacementRule:
        pattern = rf"(?<![\w>])(?P<number>{NUMBER_PATTERN})\s+(?:{unit_pattern})(?![\w/])"
        return compile_rule(pattern, rf"\g<number> {canonical_unit}")

    @staticmethod
    def _create_abbrev_sub(
        replacement: str, preserve_caps: tuple[str, ...]
    ) -> Callable[[re.Match[str]], str]:
        def sub_func(match: re.Match[str]) -> str:
            val = match.group(0)
            if val in preserve_caps:
                return val
            res = replacement
            if val[0].isupper():
                return res[0].upper() + res[1:]
            return res

        return sub_func

    _DATE_PATTERNS = (
        # YYYY-MM-DD
        re.compile(r"(?<![\w-])(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?![\w-])"),
        # DD-MM-YYYY
        re.compile(r"(?<![\w-])(?P<day>\d{1,2})-(?P<month>\d{1,2})-(?P<year>\d{4})(?![\w-])"),
        # DD/MM/YYYY
        re.compile(r"(?<![\w/])(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})(?![\w/])"),
        # DD.MM.YYYY or D.M.YYYY
        re.compile(r"(?<![\w.])(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})(?![\w.])"),
    )

    @classmethod
    def _replace_date_match(cls, match: re.Match[str]) -> str:
        day = int(match.group("day"))
        month = int(match.group("month"))
        year = match.group("year")
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{day:02d}.{month:02d}.{year}"
        return match.group(0)

    def _normalize_date_format(self, text: str) -> str:
        result = text
        for pattern in self._DATE_PATTERNS:
            result = pattern.sub(self._replace_date_match, result)
        return result

    _COMBINED_NUMBER_PATTERN = re.compile(
        r"(?P<skip>"
        r"<NUM>"
        r"|\b\d{1,2}[./]\d{1,2}[./]\d{4}\b"
        r"|\b\d{4}-\d{2}-\d{2}\b"
        r"|(?<![\w<])\d+(?:\.\d+){2,}\b"
        r")"
        r"|"
        r"(?<![\w<.])"
        r"(?P<sign>[+-])?"
        r"(?P<integer>"
        r"\d{1,3}(?:\.\d{3})+"
        r"|"
        r"\d{1,3}(?:[ \u00a0]\d{3})+"
        r"|"
        r"\d+"
        r")"
        r"(?P<decimal>[.,]\d+)?"
        r"(?![a-zA-Z>])"
    )

    _PERIOD_THOUSAND_PATTERN = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+$")

    @staticmethod
    def _format_digits(digits: str) -> str:
        if len(digits) < 4:
            return digits
        n = len(digits)
        first_len = n % 3 or 3
        chunks = [digits[:first_len]]
        for i in range(first_len, n, 3):
            chunks.append(digits[i : i + 3])
        return " ".join(chunks)

    @classmethod
    def _replace_number_match(cls, match: re.Match[str]) -> str:
        skip_val = match.group("skip")
        if skip_val:
            if cls._PERIOD_THOUSAND_PATTERN.match(skip_val):
                digits = skip_val.replace(".", "")
                sign = ""
                if digits.startswith(("+", "-")):
                    sign, digits = digits[0], digits[1:]
                return sign + cls._format_digits(digits)
            return skip_val

        sign = match.group("sign") or ""
        raw_int = match.group("integer")
        raw_dec = match.group("decimal")

        clean_digits = raw_int.replace(".", "").replace(" ", "").replace("\u00a0", "")
        formatted_int = cls._format_digits(clean_digits)

        formatted_dec = ("," + raw_dec[1:]) if raw_dec else ""
        return f"{sign}{formatted_int}{formatted_dec}"

    def _normalize_number_format(self, text: str) -> str:
        return self._COMBINED_NUMBER_PATTERN.sub(self._replace_number_match, text)

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """Normalize selected Unicode variants without changing content broadly."""
        return text.replace("\u00a0", " ").replace("\u202f", " ").replace("μ", "µ")

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        """Normalize horizontal whitespace conservatively while preserving newlines."""
        lines = text.splitlines(keepends=True)
        normalized_lines: list[str] = []
        for line in lines:
            if line.endswith("\r\n"):
                body, ending = line[:-2], "\r\n"
            elif line.endswith("\n") or line.endswith("\r"):
                body, ending = line[:-1], line[-1]
            else:
                body, ending = line, ""
            body = re.sub(r"[ \t]+", " ", body).strip()
            normalized_lines.append(body + ending)
        return "".join(normalized_lines)

    def normalize(self, text: str) -> str:
        """Normalize one text string."""
        if not isinstance(text, str):
            raise TypeError(f"Expected str, received {type(text).__name__}")

        result = self._normalize_unicode(text)
        if self.normalize_dates:
            result = self._normalize_date_format(result)
        if self.normalize_numbers:
            result = self._normalize_number_format(result)

        if self.expand_abbreviations:
            for pattern, sub_func in self._abbreviation_rules:
                result = pattern.sub(sub_func, result)

        if self.normalize_units:
            result = self._paragraph_plural_rule.pattern.sub(
                self._paragraph_plural_rule.replacement,
                result,
            )
            result = self._paragraph_rule.pattern.sub(self._paragraph_rule.replacement, result)
            for rule in self._unit_alias_rules:
                result = rule.pattern.sub(rule.replacement, result)
            for rule in self._unit_rules:
                result = rule.pattern.sub(rule.replacement, result)
            result = self._number_symbol_spacing_rule.sub(r"\g<number> \g<symbol>", result)
            result = self._degree_angle_spacing_rule.sub(r"\g<number>°", result)

        if self.normalize_whitespace:
            result = self._normalize_spaces(result)
        return result


def parse_field_path(field_name: str) -> tuple[str, ...]:
    """Parse a dotted JSON field path."""
    parts = tuple(part for part in field_name.split(".") if part)
    if not parts:
        raise ValueError(f"Invalid empty field path: {field_name!r}")
    return parts


def get_nested_value(record: Mapping[str, Any], path: Sequence[str]) -> tuple[bool, Any]:
    """Retrieve a nested mapping value."""
    current: Any = record
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return False, None
        current = current[key]
    return True, current


def set_nested_value(record: MutableMapping[str, Any], path: Sequence[str], value: Any) -> None:
    """Set an existing or new nested mapping value."""
    current: MutableMapping[str, Any] = record
    for key in path[:-1]:
        child = current.get(key)
        if child is None:
            child = {}
            current[key] = child
        if not isinstance(child, MutableMapping):
            dotted_path = ".".join(path)
            raise TypeError(f"Cannot set {dotted_path!r}: {key!r} is not an object")
        current = child
    current[path[-1]] = value


def normalize_record(
    record: MutableMapping[str, Any],
    *,
    field_paths: Sequence[Sequence[str]],
    normalizer: TextNormalizer,
    strict_fields: bool = False,
) -> MutableMapping[str, Any]:
    """Normalize selected fields in one JSON object."""
    for path in field_paths:
        exists, value = get_nested_value(record, path)
        dotted_path = ".".join(path)
        if not exists:
            if strict_fields:
                raise KeyError(f"Missing requested field: {dotted_path}")
            continue
        if value is None:
            continue
        if not isinstance(value, str):
            if strict_fields:
                raise TypeError(
                    f"Field {dotted_path!r} must be a string or null, "
                    f"received {type(value).__name__}"
                )
            LOGGER.debug("Skipping non-string field %s of type %s", dotted_path, type(value).__name__)
            continue
        set_nested_value(record, path, normalizer.normalize(value))
    return record


def count_lines(path: Path, encoding: str) -> int:
    """Count lines for an accurate tqdm progress bar."""
    with path.open("r", encoding=encoding, errors="strict") as handle:
        return sum(1 for _ in handle)


def open_input(path: str, encoding: str) -> tuple[TextIO, bool]:
    """Open an input path or return stdin."""
    if path == "-":
        return sys.stdin, False
    return Path(path).open("r", encoding=encoding), True


def iter_jsonl(handle: TextIO, *, source_name: str) -> Iterator[tuple[int, MutableMapping[str, Any]]]:
    """Yield parsed JSON objects from a JSONL stream."""
    for line_number, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source_name}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(record, MutableMapping):
            raise TypeError(
                f"{source_name}:{line_number}: expected a JSON object, "
                f"received {type(record).__name__}"
            )
        yield line_number, record


def process_stream(
    input_handle: TextIO,
    output_handle: TextIO,
    *,
    source_name: str,
    field_paths: Sequence[Sequence[str]],
    normalizer: TextNormalizer,
    total: int | None = None,
    show_progress: bool = True,
    strict_fields: bool = False,
    ensure_ascii: bool = False,
) -> tuple[int, int]:
    """Process JSONL data from one stream to another."""
    records_read = 0
    records_changed = 0
    iterator: Iterable[tuple[int, MutableMapping[str, Any]]] = iter_jsonl(
        input_handle,
        source_name=source_name,
    )
    if show_progress:
        iterator = tqdm(iterator, total=total, unit="lines", desc="Normalizing", dynamic_ncols=True)

    for line_number, record in iterator:
        records_read += 1
        before = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            normalize_record(
                record,
                field_paths=field_paths,
                normalizer=normalizer,
                strict_fields=strict_fields,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise type(exc)(f"{source_name}:{line_number}: {exc}") from exc

        after = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if before != after:
            records_changed += 1
        json.dump(record, output_handle, ensure_ascii=ensure_ascii, separators=(",", ":"))
        output_handle.write("\n")

    return records_read, records_changed


def process_jsonl(
    input_file: str | Path,
    output_file: str | Path,
    *,
    fields: Sequence[str] = ("text",),
    encoding: str = "utf-8",
    expand_abbreviations: bool = True,
    normalize_units: bool = True,
    normalize_whitespace: bool = True,
    normalize_numbers: bool = True,
    normalize_dates: bool = True,
    strict_fields: bool = False,
    ensure_ascii: bool = False,
    show_progress: bool = True,
    overwrite: bool = False,
) -> tuple[int, int]:
    """Normalize selected fields in a JSONL file."""
    input_path = str(input_file)
    output_path = str(output_file)

    if input_path != "-" and output_path != "-":
        input_resolved = Path(input_path).expanduser().resolve()
        output_resolved = Path(output_path).expanduser().resolve()
        if input_resolved == output_resolved:
            raise ValueError("Input and output files must be different")
        if output_resolved.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {output_resolved}. Use --overwrite to replace it."
            )
        output_resolved.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_resolved = None

    field_paths = tuple(parse_field_path(field) for field in fields)
    normalizer = TextNormalizer(
        expand_abbreviations=expand_abbreviations,
        normalize_units=normalize_units,
        normalize_whitespace=normalize_whitespace,
        normalize_numbers=normalize_numbers,
        normalize_dates=normalize_dates,
    )

    total: int | None = None
    if input_path != "-" and show_progress:
        total = count_lines(Path(input_path), encoding)

    input_handle, close_input = open_input(input_path, encoding)
    temporary_path: Path | None = None
    output_handle: TextIO | None = None

    try:
        if output_path == "-":
            output_handle = sys.stdout
        else:
            assert output_resolved is not None
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{output_resolved.name}.",
                suffix=".tmp",
                dir=output_resolved.parent,
                text=True,
            )
            os.close(file_descriptor)
            temporary_path = Path(temporary_name)
            output_handle = temporary_path.open("w", encoding=encoding)

        records_read, records_changed = process_stream(
            input_handle,
            output_handle,
            source_name=input_path,
            field_paths=field_paths,
            normalizer=normalizer,
            total=total,
            show_progress=show_progress,
            strict_fields=strict_fields,
            ensure_ascii=ensure_ascii,
        )

        if output_handle is not sys.stdout:
            output_handle.flush()
            os.fsync(output_handle.fileno())
            output_handle.close()
            output_handle = None

        if temporary_path is not None:
            assert output_resolved is not None
            os.replace(temporary_path, output_resolved)
            temporary_path = None

        return records_read, records_changed
    finally:
        if close_input:
            input_handle.close()
        if output_handle is not None and output_handle is not sys.stdout:
            output_handle.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Expand common Norwegian abbreviations and normalize scientific "
            "units after digits or <NUM> in selected JSONL fields."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input_file", required=True, help='Input JSONL file, or "-" for stdin.')
    parser.add_argument("--output_file", required=True, help='Output JSONL file, or "-" for stdout.')
    parser.add_argument(
        "--fields",
        nargs="+",
        default=["text"],
        help="Text fields to normalize. Dotted paths such as 'document.text' are supported.",
    )
    parser.add_argument("--encoding", default="utf-8", help="Input and output text encoding.")
    parser.add_argument(
        "--no_expand_abbreviations",
        action="store_true",
        help="Do not expand common Norwegian prose abbreviations.",
    )
    parser.add_argument(
        "--no_normalize_units",
        action="store_true",
        help="Do not normalize scientific and medical units.",
    )
    parser.add_argument(
        "--no_normalize_whitespace",
        action="store_true",
        help="Do not normalize horizontal whitespace.",
    )
    parser.add_argument(
        "--ignore_number_normalisations",
        "--no_normalize_numbers",
        action="store_true",
        help="Do not normalize number formatting (thousand space separator and decimal comma).",
    )
    parser.add_argument(
        "--strict_fields",
        action="store_true",
        help="Fail when a requested field is missing or is not a string.",
    )
    parser.add_argument("--ensure_ascii", action="store_true", help="Escape non-ASCII characters.")
    parser.add_argument("--no_progress", action="store_true", help="Disable the tqdm progress bar.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    return parser


def configure_logging(debug: bool) -> None:
    """Configure command-line logging."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    configure_logging(args.debug)
    try:
        records_read, records_changed = process_jsonl(
            input_file=args.input_file,
            output_file=args.output_file,
            fields=args.fields,
            encoding=args.encoding,
            expand_abbreviations=not args.no_expand_abbreviations,
            normalize_units=not args.no_normalize_units,
            normalize_whitespace=not args.no_normalize_whitespace,
            normalize_numbers=not args.ignore_number_normalisations,
            normalize_dates=not args.ignore_number_normalisations,
            strict_fields=args.strict_fields,
            ensure_ascii=args.ensure_ascii,
            show_progress=not args.no_progress,
            overwrite=args.overwrite,
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info(
        "Finished: %d records processed, %d records changed",
        records_read,
        records_changed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
