# Farmer advisory data handoff

Developer D can call `GET /api/v1/advisory/regions/{region_id}/crops/{crop_id}`
and read the `data` property. The route reads local data and needs no database
connection or external API. Use a confirmed canonical crop UUID from the plot
or from the existing crop catalogue and resolver.

| Demo region | Crop | Canonical UUID | Window |
| --- | --- | --- | --- |
| `IN-PB`, Punjab, India | Maize | `00000000-0000-0000-0000-000000000010` | Late May through the end of June |
| `IN-PB`, Punjab, India | Wheat | `00000000-0000-0000-0000-000000000020` | First half of November |

```http
GET /api/v1/advisory/regions/IN-PB/crops/00000000-0000-0000-0000-000000000020
```

TypeScript types are exported from `@terrapulse/contracts`. The response is
`AdvisoryCropResponse`. The advisory cards use `data.regionalContext` and
`data.capabilities`, and link to `source.url` with `source.edition` and each
item's `sourceSection`. The route's OpenAPI schema describes the response.

- Select `IN-PB` for a known Punjab location or for the explicit Punjab demo.
  The service uses the supplied region code. A farm timezone alone gives
  insufficient geographic evidence.
- A known crop without a sourced profile returns its identity and a null
  `regionalContext`. Use `status` to distinguish an unsupported region from a
  crop without coverage. An unknown crop UUID returns HTTP 404. Malformed
  region codes and UUIDs return HTTP 422.
- Keep `AdvisoryPlantingDate` on the plot. Map a date to `farmer_confirmed`
  only after explicit farmer confirmation. Use `farmer_estimated` for a
  farmer-entered estimate and `unconfirmed` with a null date when unavailable.
  A legacy date with unknown provenance requires confirmation before being
  presented as confirmed. The sourced `typical_regional_window` is
  year-independent display text. Never copy it into the plot date.
- Show milestones as definitions. They carry no date, offset or inferred
  field status. The advisory flags for numerical irrigation, harvest-date
  prediction, yield and simulation are false. Existing C7 and science
  validation govern any separate scientific run.

## Deterministic demo

Load [advisory-punjab.json](../packages/contracts/fixtures/advisory-punjab.json)
as `AdvisoryDemoFixture`. Match profiles by both `regionId` and `crop.cropId`.
The offline profiles mirror the API and carry the same sourced text. Use the
weather fixture only in explicit demo mode. Its event ID, time range, and
`synthetic_fixture` source are fixed. Label it as example weather. In live
mode, show weather as unavailable when the provider has no suitable data.

`AdvisoryWeatherEvent` is an input type for the advisory UI. It includes the
event ID, region, optional farm ID, event type, title, start and end timestamps
with offsets, and a source. Use `forecast` or `observation` only for actual
provider data, with the provider and issue timestamp. The demo timezone is
`Asia/Kolkata`. The shape carries no agronomic thresholds, measurements,
recommendation or external delivery status. The existing weather service and
C1 data path remain the sources for scientific runs.

## Sources and scope

Both guides were checked on 13 November 2026. The PAU download links can be
updated by the publisher. The edition, publication month and chapter reference
in each profile identify the reviewed material.

- Maize covers direct-sown kharif maize. The main sowing window and the
  earlier option for fields prone to standing water come from **Maize,
  Agronomic Practices**, printed pp. 30–31. The chapter identifies silking
  and grain filling. The undated glossary definitions draw on Purdue
  Extension, checked on 13 November 2026. [PAU Kharif 2026,
  March 2026](https://pau.edu/content/ccil/pf/pp_kharif.pdf) · [Purdue Extension,
  Grain Fill Stages in Corn](https://agry.purdue.edu/ext/corn/news/timeless/GrainFill.html)
- Wheat covers direct-sown rabi wheat. The first half of November is the
  general optimum in the reviewed edition, with variety-specific exceptions.
  The sowing and emergence entries refer to **Wheat, Time of Sowing and
  Sowing Method and Spacing**, printed pp. 4–6. Use this edition as a typical
  regional reference and confirm current-season and variety-specific guidance
  locally. [PAU Rabi 2025–26, August 2025](https://pau.edu/content/ccil/pf/pp_rabi.pdf)
