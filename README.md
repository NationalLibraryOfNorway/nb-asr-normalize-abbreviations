# nb-asr-normalize-abbreviations

Library and CLI for normalizing Norwegian ASR text in JSONL files.

The normalizer applies two conservative layers:

- expands common Norwegian prose abbreviations, for example `o.s.v.` to `og så videre`
- normalizes scientific, medical, legal, and technical units only after digit-based numbers or `<NUM>`

Examples:

```text
5 kilometer              -> 5 km
<NUM> milligram          -> <NUM> mg
5 millimol per liter     -> 5 mmol/l
<NUM> kilometer i timen  -> <NUM> km/t
fem kilometer            -> fem kilometer
en kilometer             -> en kilometer
```

## Install

```bash
python3 -m pip install -e ".[test]"
```

## CLI

```bash
python3 scripts/clean_asr_jsonl.py \
  --input_file input.jsonl \
  --output_file output.jsonl \
  --fields text
```

Multiple fields and dotted nested paths are supported:

```bash
python3 scripts/clean_asr_jsonl.py \
  --input_file input.jsonl \
  --output_file output.jsonl \
  --fields text document.transcript \
  --overwrite
```

Use `-` for stdin or stdout:

```bash
printf '{"text":"Det var 5 kilometer, o.s.v."}\n' |
  python3 scripts/clean_asr_jsonl.py --input_file - --output_file - --no_progress
```

## Python API

```python
from clean_asr_jsonl import TextNormalizer, process_jsonl

normalizer = TextNormalizer()
cleaned = normalizer.normalize("Det var 5 kilometer, o.s.v.")

records_read, records_changed = process_jsonl(
    "input.jsonl",
    "output.jsonl",
    fields=("text",),
)
```

## Behavior

The unit rules are guarded by a numeric prefix. This means `5 kilometer` becomes
`5 km`, but `fem kilometer` is left as-is. This avoids turning spoken-form ASR
text into symbolic written units unless the text already contains numeric form.

By default, missing fields and non-string fields are skipped. Pass
`--strict_fields` to fail on missing or non-string requested fields.

Regular-file outputs are written through a temporary file and moved into place
only after successful processing.

## Tests

```bash
python3 -m pytest
```
