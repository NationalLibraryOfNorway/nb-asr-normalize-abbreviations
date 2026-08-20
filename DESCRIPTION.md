# Description

`nb-asr-normalize-abbreviations` normalizes Norwegian ASR JSONL text fields.

It expands high-confidence written abbreviations such as `f.eks.`, `dvs.`, and `osv.`, canonicalizes scientific, medical, legal, and technical units only when following digits or `<NUM>`, and normalizes Norwegian number formats (thousand space separators and decimal commas) and dates (`DD.MM.YYYY`).

## Design Principles & Regex Challenges

The normalizer prioritizes **Precision over Recall** ("Do No Harm"):

- **Zero False Positives**: It is far better to leave an ambiguous abbreviation unexpanded than to make an incorrect replacement that corrupts text semantics (e.g., expanding `PGA Tour` to `På grunn av Tour` or `en tom flaske` to `en til og med flaske`).
- **Homograph & Acronym Collision Protection**: Regex rules explicitly guard against collisions with Norwegian words (`tom`, `bla`, `min`, `mm`, `el`) and uppercase acronyms (`PGA`, `OL`, `PT`, `CA`, `DVS`).
- **Numeric Guard**: Unit canonicalization strictly requires digit prefixes (`5 kilometer` $\rightarrow$ `5 km`), while spoken-form word numbers (`fem kilometer`) remain unchanged.
- **Regex Context Boundaries**: Pure regular expressions lack full NLP part-of-speech context. To prevent errors without sacrificing performance, the engine uses targeted lookaheads/lookbehinds, case-sensitivity rules, and fixed-width pattern matching rather than global context-free assumptions.
