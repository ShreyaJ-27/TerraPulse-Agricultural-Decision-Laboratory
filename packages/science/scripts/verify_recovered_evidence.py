"""Validate preserved user-supplied archives and rerun their standard-library tests.

Offline-only. Original ZIP bytes remain untouched. Reports numerical acceptance,
not local crop calibration or a new installation of AquaCrop-OSPy.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import csv,hashlib,json,subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parents[1]
EVID=ROOT/'research_evidence'
CASES=[
    ('fao56_original_2026-11-03.zip','validate.py','results/acceptance_tests.csv',17, ['validate.py']),
    ('turmeric_seasonal_original_2026-11-04.zip','seasonal_test.py','results/acceptance_tests.csv',22,['seasonal_test.py','source_data.json']),
]

def main()->int:
    for archive,script,csvfile,expected,files in CASES:
        with zipfile.ZipFile(EVID/archive) as z:
            if z.testzip() is not None:raise RuntimeError('ZIP CRC failed: '+archive)
            manifest=json.loads(z.read('manifest.json'))
            for name,sha in manifest.items():
                actual=hashlib.sha256(z.read(name)).hexdigest()
                if actual!=sha:raise RuntimeError(f'archive member hash mismatch: {archive}/{name}')
            with TemporaryDirectory(prefix='terrapulse-dev-a-evidence-') as d:
                p=Path(d)
                for filename in files:
                    (p/filename).write_bytes(z.read(filename))
                run=subprocess.run([sys.executable,script,'--out','fresh'],cwd=d,
                    capture_output=True,text=True,timeout=180)
                if run.returncode:raise RuntimeError(f'{script} failed: '+run.stderr+'\n'+run.stdout[-3000:])
                orig=list(csv.DictReader(z.read(csvfile).decode('utf-8').splitlines()))
                fresh=list(csv.DictReader((p/'fresh'/'acceptance_tests.csv').open(newline='')))
                if len(orig)!=expected or len(fresh)!=expected:
                    raise RuntimeError(f'{script}: unexpected check count {len(fresh)}')
                if any(x['status']!='PASS' for x in orig+fresh):
                    raise RuntimeError(f'{script}: acceptance test failed')
                print(f'{script}: archived manifest {len(manifest)}/{len(manifest)} hashes PASS; fresh {len(fresh)}/{len(fresh)} acceptance PASS')
    with zipfile.ZipFile(EVID/'aquacrop_3_1_0_original_2026-11-03.zip') as z:
        if z.testzip() is not None:raise RuntimeError('AquaCrop archive CRC failed')
        files=[n for n in z.namelist() if n.endswith('.csv') and n.startswith(('baseline_','repeat_','planting_11_01_'))]
        expected=json.loads((ROOT/'tests'/'fixtures'/'aquacrop_3_1_0'/'sha256_manifest.json').read_text())
        if set(files)!=set(expected):raise RuntimeError('AquaCrop fixture set mismatch')
        for name in files:
            if hashlib.sha256(z.read(name)).hexdigest()!=expected[name]:
                raise RuntimeError(f'AquaCrop CSV hash mismatch: {name}')
        print(f'aquacrop 3.1.0 archive: ZIP CRC PASS; archived vs bundled {len(files)}/{len(files)} CSV SHA-256 PASS')
        print('AquaCrop executable runtime NOT invoked by this verification script.')
    return 0

if __name__=='__main__':sys.exit(main())
