# Normalize Abbreviations Agent

Use this agent profile for maintenance or batch runs of the Norwegian ASR JSONL normalizer.

## Objective

Expand high-confidence Norwegian prose abbreviations and normalize numeric unit expressions in selected JSONL text fields.

## Inputs

- UTF-8 JSONL files containing one JSON object per line.
- One or more string field paths, for example `text` or `document.transcript`.

## Outputs

- JSONL with the same record structure and normalized selected fields.
- Summary counts for processed and changed records.

## Rules

- Normalize unit expressions only after digit-based numbers or `<NUM>`.
- Leave units after written numbers unchanged.
- Keep replacements conservative and covered by tests.
- Write output to a different file unless streaming to stdout.
