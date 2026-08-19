# Spesifikasjon for Normalisering av Norsk ASR-Tekst

**Dokumentversjon:** 1.1.0  
**Status:** Offisiell spesifikasjon og implementasjonsveiledning  
**Målgruppe:** Utviklere, samarbeidspartnere og databehandlere innen Automatisk Talegjenkjenning (ASR)

---

## 1. Innledning og Formål

Dette dokumentet definerer den offisielle spesifikasjonen for normalisering av tekstfelt i norske ASR-datasett (JSONL). Formålet med normaliseringsprosessen er å:

1. Ekspandere høyfrekvente, entydige norske prosa-forkortelser til sin fullstendige skriftlige form (f.eks. `f.eks.` $\rightarrow$ `for eksempel`).
2. Kanonisere utskrevne eller ustandardiserte tekniske, medisinske, juridiske og vitenskapelige måleenheter til standard SI-symboler og enheter (f.eks. `5 kilometer` $\rightarrow$ `5 km`), **kun når de følger et sifferbasert tall eller en numerisk plassholder**.
3. Bevare uendret den talemåtenære formen dersom tall er skrevet med ord (f.eks. `fem kilometer` skal **ikke** endres).
4. Normalisere tallformatering til norsk standard (Språkrådets regler): Bruke mellomrom som tusenskille for 4-sifrede og større tall, og komma som desimalskilletegn (f.eks. `1000` $\rightarrow$ `1 000`, `25000` $\rightarrow$ `25 000`, `1.000.000` $\rightarrow$ `1 000 000`, `1234.56` $\rightarrow$ `1 234,56`).

Spesifikasjonen er utformet for å være **konservativ og deterministisk**, slik at utilsiktet endring av semantikk eller kontekst unngås.

---

## 2. Hovedregler og Konserveringsprinsipper

### 2.1 Hovedregel: Numerisk prefiks for måleenheter (Numerisk sperre)
Måleenheter og enhetsforkortelser skal **kun** konverteres dersom de umiddelbart etterfølger et tall i sifferform eller plassholderen `<NUM>`.

* **Regel:** Et tall defineres av mønsteret `NUMBER_PATTERN`:
  $$\text{NUMBER\_PATTERN} = \texttt{(?:<NUM>|[+-]?(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,]\d+)?(?:\s*[–-]\s*[+-]?(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,]\d+)?)?)}$$
  Dette dekker heltall (både uformaterte `1000` og mellomrom-grupperte `1 000`), desimaltall (med komma eller punktum), tallområder/intervall (f.eks. `5–10` eller `1 000–2 000`), samt plassholderen `<NUM>`.

* **Eksempler på gyldig konvertering:**
  * `5 kilometer` $\rightarrow$ `5 km`
  * `1000 kilometer` $\rightarrow$ `1 000 km`
  * `<NUM> milligram` $\rightarrow$ `<NUM> mg`
  * `100 cm3` $\rightarrow$ `100 cm³`
  * `0.5 til 1.5 millimol per liter` $\rightarrow$ `0,5 til 1,5 mmol/l`

* **Eksempler på sperret (uendret) tekst:**
  * `fem kilometer` $\rightarrow$ `fem kilometer` *(skrevet tallord skal bevares)*
  * `en kilometer` $\rightarrow$ `en kilometer`
  * `kilometer i timen` $\rightarrow$ `kilometer i timen` *(ingen tall i forkant)*

---

### 2.2 Ord- og tegn-grenser (Boundary Matching)
For å forhindre feilaktig erstatning midt i ord, sammensatte ord, e-postadresser eller variabelfelt, må alle regelerstatninger bruke strenge grensebetingelser.

* **Prosa-forkortelser:** Skal benytte negativ lookbehind og lookahead for bokstaver og `@`-tegnet:
  $$\texttt{(?<![\w@])<mønster>(?![\w@])}$$
* **Måleenheter:** Skal benytte negativ lookbehind for ord/vinkelparentes og negativ lookahead for ord/skråstrek:
  $$\texttt{(?<![\w>])<NUMBER\_PATTERN>\s+<enhetsmønster>(?![\w/])}$$

---

### 2.3 Norsk Tallformatering (Tusenskille og desimalskilletegn)
På norsk brukes enkelt mellomrom som tusenskille og komma som desimalskilletegn. Normaliseringen utfører følgende tilpasninger:

1. **Tusenskille for 4-sifrede og større tall:**
   * Firesifrede heltall og større tall grupperes med mellomrom fra høyre i puljer på 3 siffer.
   * `1000` $\rightarrow$ `1 000`
   * `25000` $\rightarrow$ `25 000`
   * `1000000` $\rightarrow$ `1 000 000`
   * `12345678` $\rightarrow$ `12 345 678`
2. **Feilaktige punktum-tusenskiller:**
   * Punktum brukt uanbefalt som tusenskille erstattes med mellomrom når det etterfølges av nøyaktig 3 siffer.
   * `1.000` $\rightarrow$ `1 000`
   * `1.000.000` $\rightarrow$ `1 000 000`
3. **Desimalskilletegn:**
   * Komma `,` er standard desimalskilletegn på norsk.
   * Punktum brukt som desimalskilletegn etter et tall konverteres til komma.
   * `0.5` $\rightarrow$ `0,5`
   * `1234.56` $\rightarrow$ `1 234,56`
   * `1000,5` $\rightarrow$ `1 000,5`
4. **Unntak og skåneregler (Edge cases):**
   * **Datoer:** Fullstendige datoer som `17.05.1814`, `20.08.2026`, `2026-08-19` og `17/05/1814` bevares uendret.
   * **Ordenstall:** Punktum etter tall etterfulgt av mellomrom og bokstav/ord (f.eks. `17. mai`, `1. plass`, `paragraf 1.`) representerer ordenstall og skal bevares.
   * **Plassholdere:** Spesialtegn som `<NUM>` berøres ikke.
   * **Versjonsnumre og IP-adresser:** Tekst som `v1.0.0` og `192.168.1.1` skal ikke endres.
5. **Kjøringsvalg:** Tallnormalisering er **aktivert som standard**. Den kan deaktiveres ved å sende inn kommandolinjeflagget `--ignore_number_normalisations` (eller aliaset `--no_normalize_numbers`).

---

### 2.4 Prioriteringsrekkefølge (Mest spesifikk til minst spesifikk)
Ved matching av tekst må regler evalueres i en bestemt rekkefølge for å unngå at kortere mønstre "stjeler" prefikser fra lengre og mer spesifikke mønstre.

1. **Unicode-normalisering:** Erstatt ustandardiserte mellomrom (`\u00a0`, `\u202f` $\rightarrow$ ` `) og gresk mu (`μ` $\rightarrow$ `µ`).
2. **Norsk tallformatering:** Formatering av tusenskiller og desimalskilletegn (`_normalize_number_format`).
3. **Prosa-forkortelser:** Ekspander vanlige forkortelser (`GENERAL_ABBREVIATIONS`).
4. **Paragraf- og spesialregler:** Håndter `paragraf` / `paragrafene`.
5. **Ustandardiserte enhets-aliaser:** Rett opp ASCII-varianter og ustandardiserte tegn (`UNIT_ALIASES`, f.eks. `kwh` $\rightarrow$ `kWh`, `cm3` $\rightarrow$ `cm³`).
6. **Utskrevne enhets-uttrykk:** Konverter sammensatte og lange enheter før enkle enheter (`UNIT_EXPRESSIONS`, f.eks. `millimol per liter` før `millimol`, `kubikkkilometer` før `kubikkmeter`).
7. **Mellomrom ved symboler:** Sikre korrekt mellomrom før `%`, `‰`, `°C` og `°F`.
8. **Whitespace-normalisering:** Reduser multiple vanlige mellomrom/tabulatorer til enkelt mellomrom per linje, samtidig som linjeskift bevares.

---

## 3. Fullstendige Regel-Tabeller

### 3.1 Prosa-forkortelser (`GENERAL_ABBREVIATIONS`)
Følgende tabell inneholder samtlige 43 godkjente norsk prosa-forkortelser. Matching er uavhengig av tegnstørrelse (case-insensitive) og tillater valgfritt punktum og mellomrom mellom bokstavene.

| Nr. | Forkortelsesmønster (Regex) | Måltekst (Ekspandert) | Eksempel |
| :--- | :--- | :--- | :--- |
| 1 | `f\.?\s*o\.?\s*m\.?` | `fra og med` | `f.o.m.` $\rightarrow$ `fra og med` |
| 2 | `t\.?\s*o\.?\s*m\.?` | `til og med` | `t.o.m.` $\rightarrow$ `til og med` |
| 3 | `o\.?\s*s\.?\s*v\.?` | `og så videre` | `o.s.v.` $\rightarrow$ `og så videre` |
| 4 | `o\.?\s*s\.?\s*b\.?` | `og så bortetter` | `o.s.b.` $\rightarrow$ `og så bortetter` |
| 5 | `f\.?\s*eks\.?` | `for eksempel` | `f.eks.` $\rightarrow$ `for eksempel` |
| 6 | `bl\.?\s*a\.?` | `blant annet` | `bl.a.` $\rightarrow$ `blant annet` |
| 7 | `m\.?\s*a\.?` | `med annet` | `m.a.` $\rightarrow$ `med annet` |
| 8 | `m\.?\s*m\.?` | `med mer` | `m.m.` $\rightarrow$ `med mer` |
| 9 | `o\.?\s*l\.?` | `og lignende` | `o.l.` $\rightarrow$ `og lignende` |
| 10 | `e\.?\s*l\.?` | `eller lignende` | `e.l.` $\rightarrow$ `eller lignende` |
| 11 | `d\.?\s*v\.?\s*s\.?` | `det vil si` | `dvs.` $\rightarrow$ `det vil si` |
| 12 | `m\.?\s*a\.?\s*o\.?` | `med andre ord` | `m.a.o.` $\rightarrow$ `med andre ord` |
| 13 | `p\.?\s*g\.?\s*a\.?` | `på grunn av` | `p.g.a.` $\rightarrow$ `på grunn av` |
| 14 | `i\.?\s*h\.?\s*t\.?` | `i henhold til` | `i.h.t.` $\rightarrow$ `i henhold til` |
| 15 | `i\.?\s*f\.?\s*m\.?` | `i forbindelse med` | `ifm.` $\rightarrow$ `i forbindelse med` |
| 16 | `i\.?\s*f\.?\s*t\.?` | `i forhold til` | `ift.` $\rightarrow$ `i forhold til` |
| 17 | `v\.?\s*h\.?\s*a\.?` | `ved hjelp av` | `vha.` $\rightarrow$ `ved hjelp av` |
| 18 | `m\.?\s*h\.?\s*t\.?` | `med hensyn til` | `mht.` $\rightarrow$ `med hensyn til` |
| 19 | `m\.?\s*t\.?\s*p\.?` | `med tanke på` | `mtp.` $\rightarrow$ `med tanke på` |
| 20 | `p\.?\s*t\.?` | `for tiden` | `p.t.` $\rightarrow$ `for tiden` |
| 21 | `f\.?\s*t\.?` | `for tiden` | `f.t.` $\rightarrow$ `for tiden` |
| 22 | `d\.?\s*d\.?` | `dags dato` | `d.d.` $\rightarrow$ `dags dato` |
| 23 | `s\.?\s*d\.?` | `se denne` | `s.d.` $\rightarrow$ `se denne` |
| 24 | `h\.?\s*h\.?\s*v\.?` | `henholdsvis` | `hhv.` $\rightarrow$ `henholdsvis` |
| 25 | `vedr\.?` | `vedrørende` | `vedr.` $\rightarrow$ `vedrørende` |
| 26 | `ang\.?` | `angående` | `ang.` $\rightarrow$ `angående` |
| 27 | `inkl\.?` | `inkludert` | `inkl.` $\rightarrow$ `inkludert` |
| 28 | `ekskl\.?` | `ekskludert` | `ekskl.` $\rightarrow$ `ekskludert` |
| 29 | `maks\.?` | `maksimalt` | `maks.` $\rightarrow$ `maksimalt` |
| 30 | `min\.?` | `minimum` | `min.` $\rightarrow$ `minimum` |
| 31 | `ca\.?` / `cirka\.?` | `cirka` | `ca.` $\rightarrow$ `cirka` |
| 32 | `evt\.?` / `ev\.?` | `eventuelt` | `evt.` $\rightarrow$ `eventuelt` |
| 33 | `jf\.?` / `jfr\.?` | `jamfør` | `jfr.` $\rightarrow$ `jamfør` |
| 34 | `fig\.?` | `figur` | `fig.` $\rightarrow$ `figur` |
| 35 | `tab\.?` | `tabell` | `tab.` $\rightarrow$ `tabell` |
| 36 | `kap\.?` | `kapittel` | `kap.` $\rightarrow$ `kapittel` |
| 37 | `pkt\.?` | `punkt` | `pkt.` $\rightarrow$ `punkt` |
| 38 | `spm\.?` | `spørsmål` | `spm.` $\rightarrow$ `spørsmål` |
| 39 | `mill\.?` | `millioner` | `mill.` $\rightarrow$ `millioner` |
| 40 | `mrd\.?` | `milliarder` | `mrd.` $\rightarrow$ `milliarder` |

---

### 3.2 Ustandardiserte enhets-aliaser (`UNIT_ALIASES`)
Følgende regler normerer ustandardiserte enhetsforkortelser, eksponenter eller skrivemåter etter tall/`<NUM>`:

| Nr. | Kilde-mønster | Kanonisk enhet | Eksempel |
| :--- | :--- | :--- | :--- |
| 1 | `km\s*/\s*(?:h\|time)`, `km\s+per\s+(?:h\|time)` | `km/t` | `80 km/h` $\rightarrow$ `80 km/t` |
| 2 | `k\s*w\s*h`, `kwh`, `kwt` | `kWh` | `100 kwh` $\rightarrow$ `100 kWh` |
| 3 | `mwh`, `mwt` | `MWh` | `50 mwh` $\rightarrow$ `50 MWh` |
| 4 | `gwh`, `gwt` | `GWh` | `10 gwh` $\rightarrow$ `10 GWh` |
| 5 | `twh`, `twt` | `TWh` | `2 twh` $\rightarrow$ `2 TWh` |
| 6 | `μmol\s*/\s*l`, `umol\s*/\s*l` | `µmol/l` | `5 umol/l` $\rightarrow$ `5 µmol/l` |
| 7 | `μg\s*/\s*l`, `ug\s*/\s*l` | `µg/l` | `10 ug/l` $\rightarrow$ `10 µg/l` |
| 8 | `μg\s*/\s*ml`, `ug\s*/\s*ml` | `µg/ml` | `5 ug/ml` $\rightarrow$ `5 µg/ml` |
| 9 | `μg\s*/\s*kg`, `ug\s*/\s*kg` | `µg/kg` | `2 ug/kg` $\rightarrow$ `2 µg/kg` |
| 10 | `m\s*(?:\^?2\|²)` | `m²` | `50 m2` $\rightarrow$ `50 m²` |
| 11 | `cm\s*(?:\^?2\|²)` | `cm²` | `100 cm2` $\rightarrow$ `100 cm²` |
| 12 | `mm\s*(?:\^?2\|²)` | `mm²` | `10 mm2` $\rightarrow$ `10 mm²` |
| 13 | `km\s*(?:\^?2\|²)` | `km²` | `5 km2` $\rightarrow$ `5 km²` |
| 14 | `m\s*(?:\^?3\|³)` | `m³` | `10 m3` $\rightarrow$ `10 m³` |
| 15 | `cm\s*(?:\^?3\|³)` | `cm³` | `100 cm3` $\rightarrow$ `100 cm³` |
| 16 | `mm\s*(?:\^?3\|³)` | `mm³` | `50 mm3` $\rightarrow$ `50 mm³` |
| 17 | `km\s*(?:\^?3\|³)` | `km³` | `100 km3` $\rightarrow$ `100 km³` |
| 18 | `μl`, `ul` | `µl` | `5 ul` $\rightarrow$ `5 µl` |
| 19 | `μg`, `ug` | `µg` | `10 ug` $\rightarrow$ `10 µg` |
| 20 | `μmol`, `umol` | `µmol` | `2 umol` $\rightarrow$ `2 µmol` |
| 21 | `μkat`, `ukat` | `µkat` | `1 ukat` $\rightarrow$ `1 µkat` |

---

### 3.3 Utskrevne enhets-uttrykk (`UNIT_EXPRESSIONS`)
Alle utskrevne måleenheter som følger etter et tall eller `<NUM>` konverteres til sine tilhørende SI- eller standardiserte enhetssymboler. 

#### A. Medisin, Kjemi og Konsentrasjon
* `milli-internasjonale enheter per liter` / `milli internasjonale enheter per liter` $\rightarrow$ `mIU/l`
* `internasjonale enheter per liter` $\rightarrow$ `IU/l`
* `milliekvivalenter per liter` $\rightarrow$ `mEq/l`
* `millimol per liter` $\rightarrow$ `mmol/l`
* `mikromol per liter` $\rightarrow$ `µmol/l`
* `nanomol per liter` $\rightarrow$ `nmol/l`
* `mol per liter` $\rightarrow$ `mol/l`
* `nanogram per milliliter` $\rightarrow$ `ng/ml`
* `mikrogram per milliliter` $\rightarrow$ `µg/ml`
* `milligram per milliliter` $\rightarrow$ `mg/ml`
* `gram per milliliter` $\rightarrow$ `g/ml`
* `nanogram per liter` $\rightarrow$ `ng/l`
* `mikrogram per liter` $\rightarrow$ `µg/l`
* `milligram per liter` $\rightarrow$ `mg/l`
* `gram per liter` $\rightarrow$ `g/l`
* `nanogram per kilogram` $\rightarrow$ `ng/kg`
* `mikrogram per kilogram` $\rightarrow$ `µg/kg`
* `milligram per kilogram` $\rightarrow$ `mg/kg`
* `gram per kilogram` $\rightarrow$ `g/kg`
* `mikroliter per kilogram` $\rightarrow$ `µl/kg`
* `milliliter per kilogram` $\rightarrow$ `ml/kg`
* `liter per kilogram` $\rightarrow$ `l/kg`
* `milli-internasjonale enheter` / `milli internasjonale enheter` $\rightarrow$ `mIU`
* `internasjonale enheter` $\rightarrow$ `IU`
* `milliekvivalenter` $\rightarrow$ `mEq`
* `mikrokatal` $\rightarrow$ `µkat` \| `nanokatal` $\rightarrow$ `nkat` \| `katal` $\rightarrow$ `kat`
* `millimol` $\rightarrow$ `mmol` \| `mikromol` $\rightarrow$ `µmol` \| `nanomol` $\rightarrow$ `nmol` \| `mol` $\rightarrow$ `mol`

#### B. Hastighet, Akselerasjon, Temperatur og Fysikk
* `kilometer i timen` / `kilometer per timen` / `kilometer per time` $\rightarrow$ `km/t`
* `meter per sekund i andre` / `meter per sekund kvadrert` / `meter per sekund per sekund` $\rightarrow$ `m/s²`
* `meter per sekund` $\rightarrow$ `m/s`
* `watt per kvadratmeter` $\rightarrow$ `W/m²`
* `kilogram per kvadratmeter` $\rightarrow$ `kg/m²`
* `grader celsius` / `celsiusgrader` $\rightarrow$ `°C`
* `grader fahrenheit` / `fahrenheitgrader` $\rightarrow$ `°F`

#### C. Energi, Effekt og Elektrisitet
* `terawatt-timer` / `terawatttimer` $\rightarrow$ `TWh`
* `gigawatt-timer` / `gigawatttimer` $\rightarrow$ `GWh`
* `megawatt-timer` / `megawatttimer` $\rightarrow$ `MWh`
* `kilowatt-timer` / `kilowatttimer` $\rightarrow$ `kWh`
* `watt-timer` / `watttimer` $\rightarrow$ `Wh`
* `terawatt` $\rightarrow$ `TW` \| `gigawatt` $\rightarrow$ `GW` \| `megawatt` $\rightarrow$ `MW` \| `kilowatt` $\rightarrow$ `kW` \| `milliwatt` $\rightarrow$ `mW` \| `watt` $\rightarrow$ `W`
* `gigahertz` $\rightarrow$ `GHz` \| `megahertz` $\rightarrow$ `MHz` \| `kilohertz` $\rightarrow$ `kHz` \| `hertz` $\rightarrow$ `Hz`
* `megavolt` $\rightarrow$ `MV` \| `kilovolt` $\rightarrow$ `kV` \| `millivolt` $\rightarrow$ `mV` \| `mikrovolt` $\rightarrow$ `µV` \| `volt` $\rightarrow$ `V`
* `kiloampere` $\rightarrow$ `kA` \| `milliampere` $\rightarrow$ `mA` \| `mikroampere` $\rightarrow$ `µA` \| `ampere` $\rightarrow$ `A`

#### D. Data, Nettverk og Lagring
* `terabit per sekund` $\rightarrow$ `Tbit/s` \| `gigabit per sekund` $\rightarrow$ `Gbit/s` \| `megabit per sekund` $\rightarrow$ `Mbit/s` \| `kilobit per sekund` $\rightarrow$ `kbit/s`
* `terabyte per sekund` $\rightarrow$ `TB/s` \| `gigabyte per sekund` $\rightarrow$ `GB/s` \| `megabyte per sekund` $\rightarrow$ `MB/s` \| `kilobyte per sekund` $\rightarrow$ `kB/s`
* `terabyte` $\rightarrow$ `TB` \| `gigabyte` $\rightarrow$ `GB` \| `megabyte` $\rightarrow$ `MB` \| `kilobyte` $\rightarrow$ `kB` \| `byte` $\rightarrow$ `B`
* `terabit` $\rightarrow$ `Tbit` \| `gigabit` $\rightarrow$ `Gbit` \| `megabit` $\rightarrow$ `Mbit` \| `kilobit` $\rightarrow$ `kbit` \| `bit` $\rightarrow$ `bit`

#### E. Geometri, Areal og Volum
* `kvadratkilometer` $\rightarrow$ `km²` \| `kvadratmeter` $\rightarrow$ `m²` \| `kvadratcentimeter` $\rightarrow$ `cm²` \| `kvadratmillimeter` $\rightarrow$ `mm²`
* `kubikk-kilometer` / `kubikkkilometer` $\rightarrow$ `km³` \| `kubikkmeter` $\rightarrow$ `m³` \| `kubikkcentimeter` $\rightarrow$ `cm³` \| `kubikkmillimeter` $\rightarrow$ `mm³`

#### F. Tid, Lengde, Masse og Symboler
* `mikrosekunder` $\rightarrow$ `µs` \| `millisekunder` $\rightarrow$ `ms` \| `sekunder` $\rightarrow$ `s` \| `minutter` $\rightarrow$ `min` \| `timer` $\rightarrow$ `h`
* `kilometer` $\rightarrow$ `km` \| `meter` $\rightarrow$ `m` \| `centimeter` $\rightarrow$ `cm` \| `millimeter` $\rightarrow$ `mm` \| `mikrometer` $\rightarrow$ `µm` \| `nanometer` $\rightarrow$ `nm`
* `liter` $\rightarrow$ `l` \| `desiliter` $\rightarrow$ `dl` \| `centiliter` $\rightarrow$ `cl` \| `milliliter` $\rightarrow$ `ml` \| `mikroliter` $\rightarrow$ `µl`
* `tonn` $\rightarrow$ `t` \| `kilogram` $\rightarrow$ `kg` \| `gram` $\rightarrow$ `g` \| `milligram` $\rightarrow$ `mg` \| `mikrogram` $\rightarrow$ `µg` \| `nanogram` $\rightarrow$ `ng`
* `prosent` $\rightarrow$ `%` \| `promille` $\rightarrow$ `‰`

---

### 3.4 Lovverk, Paragraftegn og Tegnformatering
Spesielle regler gjelder for lovhenvisninger og formatering av symbolavstand:

| Regel | Kilde-mønster | Kanonisk resultat | Eksempel |
| :--- | :--- | :--- | :--- |
| **Flertall paragraf** | `paragrafene <NUM_1> og <NUM_2>` | `§§ <NUM_1> og <NUM_2>` | `paragrafene 5 og 6` $\rightarrow$ `§§ 5 og 6` |
| **Entall paragraf** | `paragraf <NUM>` | `§ <NUM>` | `paragraf 12` $\rightarrow$ `§ 12` |
| **Symbol-avstand** | `<NUM>\s*(%\|‰\|°C\|°F)` | `<NUM> <SYMBOL>` | `50%` $\rightarrow$ `50 %`, `37°C` $\rightarrow$ `37 °C` |

---

## 4. Teknisk Implementasjonsveiledning for Databehandlere

For å garantere identisk oppførsel på tvers av ulike programmeringsspråk (f.eks. Python, Rust, C++, Java, Go), skal følgende tekniske retningslinjer følges:

### 4.1 Datastruktur for JSONL-behandling
* **Punktum-notasjon (Dotted Paths):** Feltangivelser skal støtte nøstede objekter (f.eks. `document.transcript.text`).
* **Ikke-strenger:** Ikke-strengfelter (tall, booleanske verdier, objekter) eller manglende felt skal hoppes over uten feil, med mindre `--strict_fields` (strengetilstand) er aktivert.

### 4.2 Atomisk Filsikkerhet (Atomic File Writes)
Ved skriving til filer på disk skal prosessen:
1. Opprette og skrive til en midlertidig fil i samme katalog (f.eks. `.output.jsonl.tmp`).
2. Kjøre en eksplisitt fildisk-synkronisering (`fsync` / `flush`).
3. Atomisk erstatte/flytte den midlertidige filen til målfilen (`rename` / `replace`). Dette forhindrer korrupte delvise filer ved avbrudd.

### 4.3 Kjøring fra Kommandolinje (CLI)
Standard referanseimplementasjon kjøres via skriptet `scripts/clean_asr_jsonl.py`:

```bash
python3 scripts/clean_asr_jsonl.py \
  --input_file inndata.jsonl \
  --output_file utdata.jsonl \
  --fields text document.transcript \
  --overwrite
```

Dersom du ønsker å deaktivere norsk tallformatering:
```bash
python3 scripts/clean_asr_jsonl.py \
  --input_file inndata.jsonl \
  --output_file utdata.jsonl \
  --ignore_number_normalisations
```

### 4.4 Verifikasjonstestsett
Implementasjonen skal bestå verifikasjonstester tilsvarende følgende testtilfeller:

```python
# Test 1: Norsk tallformatering (Tusenskille og desimalkomma)
"1000"                       -> "1 000"
"25000"                      -> "25 000"
"1000000"                    -> "1 000 000"
"1.000.000"                  -> "1 000 000"
"0.5"                        -> "0,5"
"1234.56"                    -> "1 234,56"
"1000.5"                     -> "1 000,5"

# Test 2: Skåneregler for datoer, ordenstall og koder (SKAL IKKE ENDRES)
"17.05.1814"                 -> "17.05.1814"
"20.08.2026"                 -> "20.08.2026"
"2026-08-19"                 -> "2026-08-19"
"17. mai"                    -> "17. mai"
"1. plass"                   -> "1. plass"
"<NUM>"                      -> "<NUM>"
"192.168.1.1"                -> "192.168.1.1"
"v1.0.0"                     -> "v1.0.0"

# Test 3: Prosa-forkortelser
"Det var f.eks. relevant, o.s.v." -> "Det var for eksempel relevant, og så videre"

# Test 4: Måleenheter med tall
"1000 kilometer"             -> "1 000 km"
"<NUM> milligram"            -> "<NUM> mg"
"5 millimol per liter"       -> "5 mmol/l"
"100 cm3"                    -> "100 cm³"
"10 kubikkkilometer"         -> "10 km³"
```

---
**Dokument-eier:** Nasjonalbiblioteket ASR Prosjekt  
**Lisens:** MIT License
