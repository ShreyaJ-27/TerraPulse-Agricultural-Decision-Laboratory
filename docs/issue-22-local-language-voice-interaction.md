# Issue #22: Local-Language Text and Voice Interaction — Architecture & Closeout

**Project:** TerraPulse
**Issue:** #22 — [P1] Add local-language text and voice interaction
**Authors:** Developer C (Data & Crop Lens) + Developer D (Frontend & UI/UX)
**Branch:** `dev-c`

---

## 1. Overview & Objectives

Issue #22 implements end-to-end local-language text and voice interaction for smallholder farmers across English, Kannada (`ಕನ್ನಡ`), and Hindi (`हिन्दी`). The system supports natural spoken and typed queries, detects device speech capabilities with graceful touch/text fallback, strictly refuses ungrounded commodity speculation or chemical diagnosis, and adheres to TerraPulse biophysical model boundaries (FAO-56 and AquaCrop).

---

## 2. Interaction API Contract

### Endpoint
`POST /api/v1/crops/interact`

### Request Payload (`CropInteractionRequest`)
```json
{
  "query": "ಅರಿಶಿನ ಬೆಳೆಗೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಇದೆಯೇ?",
  "language": "kn"
}
```
- `query` (*string, required*): The farmer's typed question or browser speech-to-text transcript.
- `language` (*string, required*): `"en" | "kn" | "hi"`. Defaults to `"en"`.

### Response Payload (`ApiResponse[CropInteractionResponse]`)
```json
{
  "data": {
    "intent": "crop_capability",
    "language": "kn",
    "resolutionStatus": "exact_match",
    "resolvedCrop": {
      "cropId": "00000000-0000-0000-0000-000000000003",
      "canonicalName": "Turmeric",
      "scientificName": "Curcuma longa",
      "family": "Zingiberaceae",
      "aliases": ["turmeric", "haldi", "ಅರಿಶಿನ", "हल्दी"],
      "selectedEngine": "FAO-56",
      "engineVersion": "1.0",
      "supportedOutputs": ["actualEvapotranspiration", "waterStress", "irrigation"]
    },
    "candidates": [],
    "responseText": "Turmeric ಬೆಳೆಗಾಗಿ FAO-56 (1.0) ಮಾದರಿಯು ಬೇರಿನ ವಲಯದ ನೀರಿನ ಕೊರತೆ ಮತ್ತು ಆವಿಯಾಗುವಿಕೆಯನ್ನು (ET) ಲೆಕ್ಕಹಾಕುತ್ತದೆ. ಆದರೆ ಈ ಬೆಳೆಗೆ ಮಾಪನಾಂಕ ನಿರ್ಣಯಿಸಿದ ಇಳುವರಿ (yield) ಮುನ್ಸೂಚನೆ ಬೆಂಬಲಿತವಾಗಿಲ್ಲ.",
    "speechText": "Turmeric ಬೆಳೆಗೆ FAO-56 ನೀರಿನ ಸಮತೋಲನ ಲಭ್ಯವಿದೆ, ಆದರೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಲಭ್ಯವಿಲ್ಲ.",
    "limitations": [
      "No calibrated dry-matter yield output for Turmeric under FAO-56."
    ],
    "escalationRequired": false,
    "sources": [
      "FAO-56 Irrigation and Drainage Paper 56",
      "TerraPulse C7 Model Registry"
    ]
  },
  "correlationId": "4f5e7143-5cb7-4509-90d5-39dca6d09e3a",
  "contractVersion": "1.0"
}
```

---

## 3. Supported Intents & Scientific Guardrails

| Intent | Trigger Queries (Examples) | Behavior & Evidence Grounding | Guardrail / Boundary |
|---|---|---|---|
| **`crop_resolution`** | `"ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ"`, `"मेरी फसल हल्दी है"`, `"I grow wheat"` | Resolves canonical crop via `CropLensResolver` with Indic script aliases; returns taxonomy, selected engine, and C7 capabilities. | Ambiguous categories (e.g. `millet`, `ಸಿರಿಧಾನ್ಯ`, `दाल`) return `ambiguous` status with candidates for confirmation. Never guesses. |
| **`crop_capability`** | `"Can you predict yield for turmeric?"`, `"ಅರಿಶಿನಕ್ಕೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಇದೆಯೇ?"`, `"क्या हल्दी की उपज का अनुमान मिलेगा?"` | Explains engine differences: AquaCrop supports calibrated dry-matter yield for Maize; FAO-56 models water balance and stress ($K_s$) for Turmeric, Wheat, and Millets without yield. | Refuses uncalibrated yield claims. |
| **`water_guidance`** | `"How much water does ragi need?"`, `"ರಾಗಿ ಬೆಳೆಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?"`, `"रागी के लिए कितना पानी चाहिए?"` | Retrieves sourced FAO-56 crop coefficients ($K_c$) from C7 registry (`kcIni: 0.35`, `kcMid: 1.1`, `kcEnd: 0.3`); explains that daily irrigation depends on plot weather ($ET_0$) and soil water depletion. | Does not fabricate dynamic irrigation depths without farm environmental snapshots. |
| **`escalation_plant_pathology`** | `"My crop has brown spots and rot"`, `"ಬೆಳೆಯಲ್ಲಿ ಕೀಟ ಮತ್ತು ರೋಗ ಬಾಧೆ ಹೆಚ್ಚಾಗಿದೆ"`, `"फसल में कीड़े लग गए हैं"` | Immediate policy refusal to diagnose plant diseases, pests, or chemical sprays. Structured referral to Krishi Vigyan Kendra (KVK) and state agricultural extension. | `escalationRequired = true`. |
| **`refusal_market_pricing`** | `"What is today's turmeric market price?"`, `"ಅರಿಶಿನ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಎಷ್ಟು?"`, `"मंडी में हल्दी का भाव क्या है?"` | Refuses price speculation. Informs user that TerraPulse is a biophysical soil-water laboratory, not a commodity trading tool; points to Agmarknet / APMC mandi. | `escalationRequired = false`. |
| **`unknown_or_unsupported`** | General unparsed queries | Provides localized explanation of TerraPulse capabilities. | No invented answers. |

---

## 4. Indic-Script Unicode Normalization & Ambiguity

1. **Combining Character (Matra & Virama) Preservation:**
   - Standard regex `\w` treats Unicode combining marks (`Mn` and `Mc`) as non-word characters. `_normalize` was updated to use Unicode NFC normalization and preserve categories `L*` (letters), `M*` (matras / viramas like `ಿ`, `ी`, `े`, `ू`, `ಾ`, `्`), `N*` (numbers), and whitespace.
2. **Safe Word Boundaries:**
   - Standard regex `\b` fails on Indic words ending in combining vowel signs. Tokenization (`text.split()`) and whitespace boundaries were implemented.
3. **Ambiguity Protection:**
   - Queries referencing crop groups (e.g., `"millet"`, `"millets"`, `"ಸಿರಿಧಾನ್ಯ"`, `"ತೃಣಧಾನ್ಯ"`, `"मिलेट"`, `"मोटा अनाज"`, `"gram"`, `"pulse"`, `"ಕಾಳು"`, `"ದಾಲ್"`, `"दाल"`) return `ResolutionStatus.AMBIGUOUS` with interactive candidate chips.

---

## 5. Frontend Voice Architecture & Fallback Boundaries

### Speech-to-Text (STT)
- Uses the W3C Web Speech API (`window.SpeechRecognition` / `window.webkitSpeechRecognition`).
- Language tags: `kn-IN` (Kannada), `hi-IN` (Hindi), `en-IN` (English).
- **Graceful Detection & Failure Handling:**
  - If microphone access is denied by the user, or if the browser does not support Web Speech: the UI displays an informative status banner and leaves the text/touch input completely usable.
  - Microphone access is **never required** to use TerraPulse.
  - Offline speech recognition is not claimed; it depends on device-installed language packs.

### Text-to-Speech (TTS)
- Uses `window.speechSynthesis`.
- Speaks the backend-generated `speechText` tailored for concise auditory consumption.
- If a native Kannada or Hindi voice is not installed on the operating system, the system warns gracefully without breaking UI state.
- Playback can be stopped at any time via the Stop Audio button.

---

## 6. Manual Demonstration Steps

1. **Kannada Crop Resolution Flow:**
   - Select `ಕನ್ನಡ` from the sidebar language selector.
   - Navigate to **Assisted** (`/assisted`) or click "ರೈತರ ಧ್ವನಿ ಮತ್ತು ಪಠ್ಯ ಸಮಾಲೋಚನೆ" on the home page.
   - Type or speak: `"ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ"`
   - Click "ಪ್ರಶ್ನಿಸಿ".
   - *Verification:* The system resolves Turmeric (`Curcuma longa`), identifies the FAO-56 engine, and displays the localized explanation.
2. **Hindi Crop Resolution Flow:**
   - Select `हिन्दी` from the language selector.
   - Type or speak: `"मेरी फसल हल्दी है"`
   - *Verification:* The system resolves Turmeric (`Curcuma longa`) with Hindi guidance.
3. **English Yield Limitation Flow:**
   - Select `English`.
   - Click prompt chip: `"I grow turmeric. Can you predict yield?"`
   - *Verification:* Response clearly states that FAO-56 does not model dry-matter yield, explaining the scientific boundary.
4. **Disease / Pest Guardrail Escalation Flow:**
   - Click prompt chip: `"ಬೆಳೆಯಲ್ಲಿ ಕೀಟ ಮತ್ತು ರೋಗ ಬಾಧೆ ಹೆಚ್ಚಾಗಿದೆ."` (Kannada) or `"My crop has brown spots."` (English).
   - *Verification:* Response displays red alert badge with explicit referral to local Krishi Vigyan Kendra (KVK).
5. **Market Pricing Refusal Flow:**
   - Query: `"What is today's turmeric market price?"`
   - *Verification:* System refuses commodity pricing and directs the farmer to Agmarknet / APMC.
6. **Ambiguity Clarification Flow:**
   - Query: `"millet"` or `"ಸಿರಿಧಾನ್ಯ"`
   - *Verification:* Returns interactive chips for Pearl Millet, Finger Millet, and Foxtail Millet for user confirmation.
7. **Audio Playback:**
   - Click "Listen to Answer" / "ಉತ್ತರವನ್ನು ಆಲಿಸಿ" / "उत्तर सुनें" to play `speechText`. Click "Stop Audio" to cancel.

---

## 7. Test Results
- **Full Backend Suite:** 188 tests passed (`.venv/bin/pytest tests/`).
- **Cross-Contract Science Suite:** 15 tests passed (`packages/science/tests/`).
- **Frontend Build & Typecheck:** 0 errors (`npm run build`).
- **Frontend Linter:** 0 errors (`npm run lint`).
- **Python Ruff Linter:** 0 errors (`ruff check`).
