# TerraPulse Developer A science v0.2

This standalone Python package contains the Developer A capability registry,
FAO-56 root-zone model, pinned AquaCrop-OSPy 3.1.0 adapter, and scientific branch
comparisons. It owns neither shared C1–C8 contracts nor application orchestration.

## Reproduce locally

Use Python 3.12 or newer for the offline package. The live example was verified
with Python 3.12.14 and AquaCrop-OSPy 3.1.0. From `packages/science` in PowerShell:

```powershell
python examples/make_fixtures.py
python scripts/restore_evidence.py 'C:\path\to\TerraPulse_Developer_A_Science_v0.2_corrected.zip'
python -m unittest discover -s tests -v
python scripts/verify_recovered_evidence.py
$env:PYTHONPATH = 'src'
python -m terrapulse_science.cli capabilities
python -m terrapulse_science.cli fao56 examples/fao_baseline.json --out baseline.json
python -m terrapulse_science.cli fao56 examples/fao_delayed.json --out delayed.json
python -m terrapulse_science.cli compare baseline.json delayed.json --fork-date 2025-05-01 --out comparison.json
# With the separately installed pinned AquaCrop dependency:
python scripts/verify_live_aquacrop.py --out live-golden.json
```

Obtain the corrected ZIP directly from the Developer A maintainer through the
team's authorized channel. Its SHA-256 is
`a8a01afb5f9193a710562019d2eb774871fb8a5d68b34366bd86eac4584346d1`.
Restoration verifies the release and each evidence member against
[`EVIDENCE_SHA256.txt`](EVIDENCE_SHA256.txt). The full suite requires these
files. The examples generator produces first-party synthetic FAO inputs.

## Scientific and licensing boundaries

The repository boundary is in `terrapulse_science.repository_contracts`.
Use `fao_input_from_c1_v1` for authoritative C1 JSON and
`c3_states_from_run` to project executed FAO-56 or AquaCrop states into C3.
See the handoff for the exact dated schedule required alongside C8.
To run the seven cross-contract tests with the repository API environment:

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
