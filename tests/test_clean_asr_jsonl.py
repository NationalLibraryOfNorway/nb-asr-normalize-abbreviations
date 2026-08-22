from __future__ import annotations

import io
import json

import pytest

from clean_asr_jsonl import TextNormalizer, normalize_record, parse_field_path, process_stream


def test_expands_common_abbreviations() -> None:
    normalizer = TextNormalizer()

    assert normalizer.normalize("Det var f.eks. relevant, o.s.v.") == (
        "Det var for eksempel relevant, og så videre."
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("5 kilometer", "5 km"),
        ("<NUM> milligram", "<NUM> mg"),
        ("5 millimol per liter", "5 mmol/l"),
        ("<NUM> kilometer i timen", "<NUM> km/t"),
        ("5 ug/ml", "5 µg/ml"),
        ("37 grader celsius", "37 °C"),
        ("100 cm3", "100 cm³"),
        ("100 cm2", "100 cm²"),
        ("100 km3", "100 km³"),
        ("10 kubikkkilometer", "10 km³"),
        ("60 °", "60°"),
        ("60 °N", "60°N"),
        ("45 ° vinkel", "45° vinkel"),
    ],
)
def test_normalizes_units_after_digit_or_num_placeholder(source: str, expected: str) -> None:
    assert TextNormalizer().normalize(source) == expected


@pytest.mark.parametrize("source", ["fem kilometer", "en kilometer"])
def test_does_not_normalize_units_after_written_numbers(source: str) -> None:
    assert TextNormalizer().normalize(source) == source


def test_normalizes_nested_jsonl_fields() -> None:
    input_handle = io.StringIO(
        json.dumps({"id": 1, "document": {"text": "Det var 5 kilometer, dvs. langt."}})
        + "\n"
    )
    output_handle = io.StringIO()

    records_read, records_changed = process_stream(
        input_handle,
        output_handle,
        source_name="<test>",
        field_paths=[parse_field_path("document.text")],
        normalizer=TextNormalizer(),
        show_progress=False,
    )

    assert (records_read, records_changed) == (1, 1)
    assert json.loads(output_handle.getvalue()) == {
        "id": 1,
        "document": {"text": "Det var 5 km, det vil si langt."},
    }


def test_strict_fields_rejects_non_string() -> None:
    with pytest.raises(TypeError, match="must be a string or null"):
        normalize_record(
            {"text": 5},
            field_paths=[("text",)],
            normalizer=TextNormalizer(),
            strict_fields=True,
        )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1000", "1 000"),
        ("25000", "25 000"),
        ("1000000", "1 000 000"),
        ("12.345,67", "12 345,67"),
        ("1.000.000", "1 000 000"),
        ("0.5", "0,5"),
        ("1234.56", "1 234,56"),
        ("1000.5", "1 000,5"),
        ("-1000.5", "-1 000,5"),
        ("17.05.1814", "17.05.1814"),
        ("17/05/1814", "17.05.1814"),
        ("2026-08-19", "19.08.2026"),
        ("19-08-2026", "19.08.2026"),
        ("10.5.1814", "10.05.1814"),
        ("1/5/1814", "01.05.1814"),
        ("17. mai", "17. mai"),
        ("Det var 1000.", "Det var 1 000."),
        ("<NUM>", "<NUM>"),
        ("192.168.1.1", "192.168.1.1"),
        ("v1.0.0", "v1.0.0"),
    ],
)
def test_normalizes_norwegian_number_formats(source: str, expected: str) -> None:
    assert TextNormalizer().normalize(source) == expected


def test_ignore_number_normalisations() -> None:
    normalizer = TextNormalizer(normalize_numbers=False)
    assert normalizer.normalize("Det var 1000 og 1234.56 kroner.") == (
        "Det var 1000 og 1234.56 kroner."
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Det var osv i teksten", "Det var og så videre i teksten"),
        ("Det var o.s.v. i teksten", "Det var og så videre i teksten"),
        ("Det var feks fint", "Det var for eksempel fint"),
        ("Pga regn ble det avlyst.", "På grunn av regn ble det avlyst."),
        ("Han vant PGA-touren i helgen.", "Han vant PGA-touren i helgen."),
        ("Spilte på PGA Tour.", "Spilte på PGA Tour."),
        ("Det var et OL på Lillehammer.", "Det var et OL på Lillehammer."),
        ("En tom flaske.", "En tom flaske."),
        ("Han valgte å bla i boka.", "Han valgte å bla i boka."),
        ("Bilen var 10 mm lang.", "Bilen var 10 mm lang."),
        ("Dette er bilen min.", "Dette er bilen min."),
        ("Trente med PT i dag.", "Trente med PT i dag."),
        ("Trente med PT. i dag.", "Trente med PT. i dag."),
        ("Reiste til CA i USA.", "Reiste til CA i USA."),
        ("Trykk tab for å fortsette.", "Trykk tab for å fortsette."),
        ("magen min. Det var fint.", "magen min. Det var fint."),
        ("OL. var gøy.", "OL. var gøy."),
        ("Kjøpte osb-plater.", "Kjøpte osb-plater."),
        ("Maks var her.", "Maks var her."),
        ("Aaret var 1976.", "Aaret var 1976."),
        ("Perioden var 2016-2020.", "Perioden var 2016-2020."),
        ("Møtet var 22.55.", "Møtet var 22.55."),
        ("Møtet var kl. 08.30.", "Møtet var kl. 08.30."),
        ("Det koster 1 mrd. kr.", "Det koster 1 milliard kr."),
        ("Det koster 5 mrd. kr.", "Det koster 5 milliarder kr."),
    ],
)
def test_abbreviation_variants_and_collision_protections(source: str, expected: str) -> None:
    assert TextNormalizer().normalize(source) == expected


