# TerraPulse Developer A science v0.2

This standalone Python package contains the Developer A capability registry,
FAO-56 root-zone model, pinned AquaCrop-OSPy 3.1.0 adapter, and scientific branch
comparisons. It owns neither shared C1–C8 contracts nor application orchestration.

## Reproducible verification

Use Python 3.12 or newer. From `packages/science` in PowerShell:

### Local source-only verification

This mode uses first-party synthetic FAO examples and runs all available source,
contract, orchestration, crop-binding, and application-integration tests. If the
licensed research evidence is absent, only the AquaCrop evidence-dependent tests
are explicitly skipped; missing evidence is never replaced with synthetic
AquaCrop data. The shipped-example regression test also generates its synthetic
inputs if they are absent.

```powershell
python examples/make_fixtures.py
$env:TERRAPULSE_TEST_REPOSITORY_CONTRACTS = '1'
python -m unittest discover -s tests -v
```

The skipped test names and restoration instructions appear in the unittest
output. To run the application tests from the repository root:

```powershell
python -m pytest tests/
```

The three generated `fao_*.json` inputs use an explicit synthetic calendar and
soil assumption; they are not real weather, field evidence, or forecasts.

### Full evidence verification

Obtain the corrected ZIP directly from the Developer A maintainer through the
team's authorized channel. Its expected SHA-256 is
`a8a01afb5f9193a710562019d2eb774871fb8a5d68b34366bd86eac4584346d1`.
Restore and verify the release and each extracted file against
[`EVIDENCE_SHA256.txt`](EVIDENCE_SHA256.txt), then run the same suite:

```powershell
python scripts/restore_evidence.py 'C:\path\to\TerraPulse_Developer_A_Science_v0.2_corrected.zip'
python scripts/verify_recovered_evidence.py
$env:TERRAPULSE_TEST_REPOSITORY_CONTRACTS = '1'
python -m unittest discover -s tests -v
```

In this mode, the AquaCrop fixture, repository projection, and research archive
integrity tests run against the restored hash-verified files rather than being
skipped. A hash mismatch is a test or restoration failure, not a skip.

For the standalone examples and optional live AquaCrop-OSPy check:

```powershell
$env:PYTHONPATH = 'src'
python -m terrapulse_science.cli capabilities
python -m terrapulse_science.cli fao56 examples/fao_baseline.json --out baseline.json
python -m terrapulse_science.cli fao56 examples/fao_delayed.json --out delayed.json
python -m terrapulse_science.cli compare baseline.json delayed.json --fork-date 2025-05-01 --out comparison.json
# With the separately installed pinned AquaCrop dependency:
python scripts/verify_live_aquacrop.py --out live-golden.json
```

## Scientific and licensing boundaries

The repository boundary is in `terrapulse_science.repository_contracts`.
Use `fao_input_from_c1_v1` for authoritative C1 JSON and
`c3_states_from_run` to project executed FAO-56 or AquaCrop states into C3.
For a catalogue-driven farm run, wire the server's Crop Lens resolver and
canonical lookup into `CropBindingService` and call its `run_fao` entry point.
For repository orchestration, use `ScientificRunService.execute` with the
authoritative C1/C3 models. It returns validated C3 states and full run evidence,
or an error code and stage. See the handoff for wiring and persistence.
See the handoff for the exact dated schedule required alongside C8.
To run the cross-contract and crop-binding tests with the repository API environment:

```powershell
$env:TERRAPULSE_TEST_REPOSITORY_CONTRACTS = '1'
python -m unittest discover -s tests -v
```

FAO-56 uses a fixed homogeneous root zone and provisional turmeric stage maps.
The optional dry-bean reference reproduces FAO-56 Example 28. The pathway does
not predict yield or biomass. The AquaCrop example uses the bundled Tunis
weather and Wheat/SandyLoam parameters with October and November planting.
The profile balance covers executed days with field-capacity resets.
Skipped intervals have unknown storage change. Runtime reproducibility and
numerical conservation do not establish field calibration or local yield accuracy.

The repository's Apache-2.0 license covers this contribution's first-party
source, tests and documentation. The research ZIPs, AquaCrop CSVs, third-party
weather data and package binaries are not redistributed here. The upstream
3.1.0 release has inconsistent licensing metadata in the locally archived
evidence. The dependency remains optional and pinned for independent installation.

- [FAO-56 Chapter 6 and Example 28](https://www.fao.org/4/x0490e/x0490e0b.htm)
- [FAO-56 Chapter 8 water balance](https://www.fao.org/4/x0490e/x0490e0e.htm)
- [AquaCrop-OSPy 3.1.0 release](https://pypi.org/project/aquacrop/3.1.0/)
- [Integration handoff](docs/INTEGRATION_HANDOFF.md)
