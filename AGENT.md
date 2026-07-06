# Agent

## Role

Maintain and run the Norwegian ASR abbreviation/unit normalizer.

## Responsibilities

- Normalize selected JSONL string fields without changing unrelated fields.
- Expand only high-confidence Norwegian prose abbreviations.
- Normalize units only after digit-based numbers or `<NUM>`.
- Preserve JSONL record boundaries and write regular-file outputs atomically.
- Prefer adding tests before broadening abbreviation or unit coverage.

## Guardrails

- Do not normalize units after written numbers such as `en`, `fem`, or `tjue`.
- Do not overwrite output files unless `--overwrite` is explicitly supplied.
- Do not silently coerce non-string fields in strict mode.
- Keep replacement rules ordered from most specific to least specific.
