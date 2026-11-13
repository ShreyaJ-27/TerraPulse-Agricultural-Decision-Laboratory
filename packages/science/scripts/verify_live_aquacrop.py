"""Execute the installed engine and compare its adapter output with pinned CSVs."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from terrapulse_science import compare_aquacrop_runs, parse_aquacrop_fixture, run_published_wheat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fixtures = ROOT / "tests/fixtures/aquacrop_3_1_0"
    report = {"python":sys.version,"pythonExecutable":sys.executable,
              "runtime":{name:version(name) for name in ("aquacrop","numpy","pandas")},"runs":{}}
    runs = {}
    for planting, label in (("10/01","baseline"),("11/01","planting_11_01")):
        live = run_published_wheat(planting_mmdd=planting, branch_id=label)
        archived = parse_aquacrop_fixture(fixtures, label=label, start_date=live["startDate"],
            branch_id=label, plot_id=live["plotId"], input_snapshot_id=live["inputSnapshotId"],
            weather_realization_id=live["weatherRealizationId"])
        fields = ("tableHashes","states","harvests","waterBalance","summary","weatherHash")
        checks = {field:live[field] == archived[field] for field in fields}
        if not all(checks.values()) or live["evidenceKind"] != "executed-aquacrop":
            raise RuntimeError(f"Golden reference mismatch at {planting}: {checks}")
        report["runs"][planting] = {"evidenceKind":live["evidenceKind"],
            "referenceKind":archived["evidenceKind"],"runId":live["runId"],
            "weatherHash":live["weatherHash"],"tableHashes":live["tableHashes"],
            "harvests":live["harvests"],"waterBalance":live["waterBalance"],
            "exactChecks":checks}
        print(f"{planting}: PASS {sum(checks.values())}/{len(checks)} exact golden checks")
        runs[planting] = live
    comparison = compare_aquacrop_runs(runs["10/01"],runs["11/01"],fork_date="1979-09-30")
    if comparison["status"] != "comparable" or len(comparison["seasonalDryYield"]) != 6:
        raise RuntimeError("Live planting-date comparison failed")
    report["comparison"] = {key:comparison[key] for key in
                            ("status","seasonalDryYield","meanDryYieldA","meanDryYieldB")}
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("Live planting-date comparison: PASS (six paired seasons)")


if __name__ == "__main__":
    main()
