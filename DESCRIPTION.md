# Description

`nb-asr-normalize-abbreviations` normalizes Norwegian ASR JSONL text fields.

It expands high-confidence written abbreviations such as `f.eks.`, `dvs.`, and
`o.s.v.`, and canonicalizes scientific, medical, legal, and technical units only
when the unit follows a digit-based number or the `<NUM>` placeholder.

The numeric guard is intentional: `5 kilometer` becomes `5 km`, while
`fem kilometer` stays unchanged because the latter is more likely to represent
spoken-form text that should not be collapsed into symbols.
