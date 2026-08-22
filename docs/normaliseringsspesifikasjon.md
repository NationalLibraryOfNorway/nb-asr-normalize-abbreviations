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

### 2.2 Ord-, Tegn- og Kapitaliserings-grenser (Boundary Matching og Kollisjonssikring)
For å forhindre feilaktig erstatning midt i ord, sammensatte ord, e-postadresser, egennavn eller ubeslektede versalforkortelser, benyttes følgende regler:

* **Variant-matching og Versalsikring (ALL-CAPS protection):**
  * Alle forkortelser i versaler (ALL-CAPS), både med og uten punktum (f.eks. `OL.`, `OL`, `PT.`, `PT`, `PGA.`, `PGA`, `DVS.`, `DVS`, `CA.`, `CA`, `FT.`, `FT`), bevares uendret for å forhindre kollisjon med organisasjonsnavn, forkortelser og faguttrykk.
  * Tittelkasserte og lavere varianter (`pga`, `Pga`, `o.s.v.`, `osv`) ekspanderes trygt.
* **Mellomrom + Stor bokstav ved setningsavslutning:**
  * Hvis en forkortelse (f.eks. `osv.`) står i en kontekst etterfulgt av mellomrom og stor bokstav (f.eks. `osv. Katten...`), bevares forkortelsen uendret for å unngå usikre setningsgrenseerstatninger.
* **Bindestrek- og sammensatte ord (Compound Word Protection):**
  * Grense-matching benytter `(?<![\w@-])` og `(?![\w@-])` for å hindre at forkortelser matcher inne i sammensatte fagord med bindestrek (f.eks. `osb-plater`, `e-post`, `it-ansvarlig`).
* **Ord- og enhets-skåning:**
  * Ordene `tom` (f.eks. "en tom flaske" / "Tom") skånes (krever punktum som `t.o.m.` / `t.o.m` for `til og med`).
  * Egennavnet `Maks` uten punktum skånes (krever punktum som `maks.` eller tallkontekst som `maks 10` for `maksimalt`).
  * Eiendomspronomenet `min` (f.eks. "magen min. Det...") og skrivemåten `min.` er helt utelatt fra ekspansjon for å unngå tvetydighet og falske positiver.
  * Verbet `bla` ("å bla i boka") og enheten `mm` ("10 mm") skånes fra ekspansjon.
* **Dynamisk Entall/Flertall for tallstørrelser:**
  * Forkortelser som `mrd.` og `mill.` ekspanderes dynamisk til entall (`1 milliard kr`, `1 million kr`) hvis det foregående tallet er `1`, `1,0` eller et entalls tallord (`en`, `et`, `ei`), og til flertall (`5 milliarder kr`, `5 millioner kr`) ved større tall.
* **Regeluttrykk:**
  * **Prosa-forkortelser:** $\texttt{(?<![\w@-])<mønster>(?![\w@-])}$
  * **Måleenheter:** $\texttt{(?<![\w>])<NUMBER\_PATTERN>\s+<enhetsmønster>(?![\w/])}$

---

### 2.3 Norsk Tallformatering (Tusenskille for 5-sifrede og større tall)
For å unngå feilaktig endring av 4-sifrede årstall (som `1492`, `1976`, `2024`), århundrer (`1200-tallet`), klokkeslett/sportstider (`3.56`, `7.30`), versjonsnumre (`2.0`), og feilformaterte sekvenser (`29.2015`), utføres tallformatering **kun på heltall med 5 eller flere siffer**:

1. **Tusenskille for 5-sifrede og større tall:**
   * Heltall med 5 eller flere siffer grupperes med mellomrom fra høyre i puljer på 3 siffer (`10000` $\rightarrow$ `10 000`, `25000` $\rightarrow$ `25 000`, `1000000` $\rightarrow$ `1 000 000`).
2. **Beskyttelse av 4-sifrede tall og punktumnumre:**
   * Alle 1-, 2-, 3- og 4-sifrede tall (f.eks. `1492`, `1600`, `1200-tallet`, `2020`), samt desimal- og tidspunktsikre punktumuttrykk (`3.56`, `2.0`, `7.30`, `29.2015`), bevares 100 % uendret for å garantere null falske positiver.
3. **Datoer (Kanonisering til DD.MM.YYYY):**
   * Ulike datoskrivemåter som ISO-format (`YYYY-MM-DD`), skråstrek (`DD/MM/YYYY`), bindestrek (`DD-MM-YYYY`) og ufullstendig nullpolstrede datoer (`D.M.YYYY` / `D/M/YYYY`) normeres til det offisielle norske datoformatet `DD.MM.YYYY`.
4. **Kjøringsvalg:** Tall- og datonormalisering er **aktivert som standard**. Den kan deaktiveres ved å sende inn kommandolinjeflagget `--ignore_number_normalisations` (eller aliaset `--no_normalize_numbers`).

---

### 2.4 Prioriteringsrekkefølge (Mest spesifikk til minst spesifikk)
Ved matching av tekst må regler evalueres i en bestemt rekkefølge for å unngå at kortere mønstre "stjeler" prefikser fra lengre og mer spesifikke mønstre.

1. **Unicode-normalisering:** Erstatt ustandardiserte mellomrom (`\u00a0`, `\u202f` $\rightarrow$ ` `) og gresk mu (`μ` $\rightarrow$ `µ`).
2. **Dato-kanonisering:** Konverter ustandardiserte datoformater til `DD.MM.YYYY` (`_normalize_date_format`).
3. **Norsk tallformatering:** Formatering av tusenskiller og desimalskilletegn (`_normalize_number_format`).
4. **Prosa-forkortelser:** Ekspander vanlige forkortelser (`GENERAL_ABBREVIATIONS`).
5. **Paragraf- og spesialregler:** Håndter `paragraf` / `paragrafene`.
6. **Ustandardiserte enhets-aliaser:** Rett opp ASCII-varianter og ustandardiserte tegn (`UNIT_ALIASES`, f.eks. `kwh` $\rightarrow$ `kWh`, `cm3` $\rightarrow$ `cm³`).
7. **Utskrevne enhets-uttrykk:** Konverter sammensatte og lange enheter før enkle enheter (`UNIT_EXPRESSIONS`, f.eks. `millimol per liter` før `millimol`, `kubikkkilometer` før `kubikkmeter`).
8. **Mellomrom ved symboler:** Sikre korrekt mellomrom før `%`, `‰`, `°C` og `°F`.
9. **Whitespace-normalisering:** Reduser multiple vanlige mellomrom/tabulatorer til enkelt mellomrom per linje, samtidig som linjeskift bevares.

---

### 2.5 Utfordringer og Teoretiske Begrensninger ved bruk av Regulære Uttrykk (Regex vs. NLP)

Å benytte regulære uttrykk (reg.exp.) for tekstnormalisering i ASR-datasett gir ekstremt høy prosesseringshastighet, null avhengigheter og 100 % deterministisk oppførsel. Likevel innebærer bruk av ren regelbasert mønstermatching visse iboende utfordringer og teoretiske begrensninger som har formet arkitekturen i denne normalisereren:

1. **Mangel på dyp syntaktisk og semantisk kontekstforståelse:**
   * Regulære uttrykk opererer på tegnnivå og har ikke tilgang til morfosyntaktisk analyse (Part-of-Speech tagging) eller leksikalske parsningstrær.
   * En streng som `min.` kan rent teoretisk representere adjektivet/pronomenet *min* ved et setningspunktum, forkortelsen for måleenheten *minutter*, eller forkortelsen for *minimum*. Regex kan ikke analysere setningens dype grammatiske tre.

2. **Det grunnleggende prinsippet: Presisjon fremfor Gjenfinning (Precision vs. Recall):**
   * I dette prosjektet er det fastslått som et ubetinget krav at **null falske positiver ("Do No Harm")** har høyere prioritet enn å fange opp 100 % av alle mulige ustandardiserte skrivemåter.
   * En uoppdaget forkortelse i kildematerialet (f.eks. at en ekstremt sjelden lokal forkortelse står uendret) har minimal skadevirkning, mens en feilaktig erstatning (som f.eks. å endre `PGA Tour` til `På grunn av Tour` eller `en tom boks` til `en til og med boks`) ødelegger den semantiske meningen i datasettet.

3. **Kollisjonshåndtering av homografer og versalkoder:**
   * Mange korte bokstavkombinasjoner uten punktum kolliderer med enten vanlige norske ord (`tom`, `bla`, `min`, `el`, `tab`), SI-måleenheter (`mm`), eller internasjonale versalforkortelser og egennavn (`PGA` for PGA Tour, `OL` for Olympiske leker, `PT` for Personal Trainer, `CA` for California).
   * Løsningen i regulære uttrykk krever eksplisitte versalsperrer (ALL-CAPS protection) og strenge krav til enten punktum eller tilhørende numerisk kontekst (`min. 10 kg`).

4. **Hvorfor generelle kontekstforbud (f.eks. "neste bokstav må ikke være stor") feiler:**
   * Det kan ved første øyekast virke fristende å innføre generelle heuristikker som at *"en forkortelse må ikke etterfølges av stor bokstav"*.
   * Dette vil imidlertid krasje umiddelbart i to svært vanlige tilfeller:
     1. *Forkortelser foran egennavn:* `f.eks. Norge`, `dvs. Equinor`, `bl.a. Ola`.
     2. *Forkortelser i setningsavslutninger:* `...osv. Neste setning...`
   * Regulære uttrykk må derfor bygges opp med presise lookaheads/lookbehinds fremfor globale antagelser.

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
| 7 | `m\.?\s*m\.?` | `med mer` | `m.m.` $\rightarrow$ `med mer` |
| 8 | `o\.?\s*l\.?` | `og lignende` | `o.l.` $\rightarrow$ `og lignende` |
| 9 | `e\.?\s*l\.?` | `eller lignende` | `e.l.` $\rightarrow$ `eller lignende` |
| 10 | `d\.?\s*v\.?\s*s\.?` | `det vil si` | `dvs.` $\rightarrow$ `det vil si` |
| 11 | `m\.?\s*a\.?\s*o\.?` | `med andre ord` | `m.a.o.` $\rightarrow$ `med andre ord` |
| 12 | `p\.?\s*g\.?\s*a\.?` | `på grunn av` | `p.g.a.` $\rightarrow$ `på grunn av` |
| 13 | `i\.?\s*h\.?\s*t\.?` | `i henhold til` | `i.h.t.` $\rightarrow$ `i henhold til` |
| 14 | `i\.?\s*f\.?\s*m\.?` | `i forbindelse med` | `ifm.` $\rightarrow$ `i forbindelse med` |
| 15 | `i\.?\s*f\.?\s*t\.?` | `i forhold til` | `ift.` $\rightarrow$ `i forhold til` |
| 16 | `v\.?\s*h\.?\s*a\.?` | `ved hjelp av` | `vha.` $\rightarrow$ `ved hjelp av` |
| 17 | `m\.?\s*h\.?\s*t\.?` | `med hensyn til` | `mht.` $\rightarrow$ `med hensyn til` |
| 18 | `m\.?\s*t\.?\s*p\.?` | `med tanke på` | `mtp.` $\rightarrow$ `med tanke på` |
| 19 | `p\.?\s*t\.?` | `for tiden` | `p.t.` $\rightarrow$ `for tiden` |
| 20 | `f\.?\s*t\.?` | `for tiden` | `f.t.` $\rightarrow$ `for tiden` |
| 21 | `d\.?\s*d\.?` | `dags dato` | `d.d.` $\rightarrow$ `dags dato` |
| 22 | `s\.?\s*d\.?` | `se denne` | `s.d.` $\rightarrow$ `se denne` |
| 23 | `h\.?\s*h\.?\s*v\.?` | `henholdsvis` | `hhv.` $\rightarrow$ `henholdsvis` |
| 24 | `vedr\.?` | `vedrørende` | `vedr.` $\rightarrow$ `vedrørende` |
| 25 | `ang\.?` | `angående` | `ang.` $\rightarrow$ `angående` |
| 26 | `inkl\.?` | `inkludert` | `inkl.` $\rightarrow$ `inkludert` |
| 27 | `ekskl\.?` | `ekskludert` | `ekskl.` $\rightarrow$ `ekskludert` |
| 28 | `maks\.?` | `maksimalt` | `maks.` $\rightarrow$ `maksimalt` |
| 29 | `ca\.?` / `cirka\.?` | `cirka` | `ca.` $\rightarrow$ `cirka` |
| 30 | `evt\.?` / `ev\.?` | `eventuelt` | `evt.` $\rightarrow$ `eventuelt` |
| 31 | `jf\.?` / `jfr\.?` | `jamfør` | `jfr.` $\rightarrow$ `jamfør` |
| 32 | `fig\.?` | `figur` | `fig.` $\rightarrow$ `figur` |
| 33 | `tab\.?` | `tabell` | `tab.` $\rightarrow$ `tabell` |
| 34 | `kap\.?` | `kapittel` | `kap.` $\rightarrow$ `kapittel` |
| 35 | `pkt\.?` | `punkt` | `pkt.` $\rightarrow$ `punkt` |
| 36 | `spm\.?` | `spørsmål` | `spm.` $\rightarrow$ `spørsmål` |
| 37 | `mill\.?` | `millioner` | `mill.` $\rightarrow$ `millioner` |
| 38 | `mrd\.?` | `milliarder` | `mrd.` $\rightarrow$ `milliarder` |

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
Spesielle regler gjelder for lovhenvisninger, temperaturer og formatering av symbolavstand:

| Regel | Kilde-mønster | Kanonisk resultat | Eksempel |
| :--- | :--- | :--- | :--- |
| **Flertall paragraf** | `paragrafene <NUM_1> og <NUM_2>` | `§§ <NUM_1> og <NUM_2>` | `paragrafene 5 og 6` $\rightarrow$ `§§ 5 og 6` |
| **Entall paragraf** | `paragraf <NUM>` | `§ <NUM>` | `paragraf 12` $\rightarrow$ `§ 12` |
| **Temperatur & prosent (Mellomrom tvinges)** | `<NUM>\s*(%\|‰\|°C\|°F)` | `<NUM> <SYMBOL>` | `50%` $\rightarrow$ `50 %`, `37°C` $\rightarrow$ `37 °C` |
| **Vinkel- & GPS-grader (Mellomrom fjernes)** | `<NUM>\s+°(?![CFcf])` | `<NUM>°` | `60 °` $\rightarrow$ `60°`, `60 °N` $\rightarrow$ `60°N`, `45 °` $\rightarrow$ `45°` |

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

# Test 5: Grader og tegnformatering (Temperatur vs GPS/Vinkler)
"37°C"                        -> "37 °C"
"60 °"                        -> "60°"
"60 °N"                       -> "60°N"
"45 ° vinkel"                 -> "45° vinkel"
```

---
**Dokument-eier:** Nasjonalbiblioteket ASR Prosjekt  
**Lisens:** MIT License

