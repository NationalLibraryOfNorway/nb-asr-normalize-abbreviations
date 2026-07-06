# Normalizer Notes

This directory documents the behavior expected from the JSONL normalizer.

## Abbreviations

Abbreviation expansion is meant for high-confidence Norwegian prose forms, such as:

- `f.eks.` -> `for eksempel`
- `dvs.` -> `det vil si`
- `o.s.v.` -> `og så videre`

Regex rules use conservative boundaries to avoid matching inside words, identifiers, or email-like text.

## Units

Unit normalization is guarded by `NUMBER_PATTERN`. The normalizer changes `5 kilometer` to `5 km` and `<NUM> milligram` to `<NUM> mg`, but leaves `fem kilometer` unchanged.

Compound rules should appear before shorter rules. For example, `millimol per liter` must be checked before `millimol`.
