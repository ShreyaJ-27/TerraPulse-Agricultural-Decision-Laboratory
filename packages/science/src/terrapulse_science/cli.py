"""Offline demonstration CLI; never uploads or pushes project source."""
import argparse,json,sys
from pathlib import Path
from .contracts import ScienceError,request_from_dict
from .fao56 import run_fao
from .compare import compare_runs,compare_aquacrop_runs
from .capability import CapabilityRegistry,registry
from .aquacrop_adapter import parse_aquacrop_fixture,run_published_wheat

def dump(data,path):
    text=json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+"\n"
    if path:Path(path).write_text(text,encoding="utf-8")
    else:print(text,end="")

def main(argv=None):
    p=argparse.ArgumentParser(description="TerraPulse Developer A offline science adapters")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("capabilities")
    fao=sub.add_parser("fao56")
    fao.add_argument("input",help="JSON FaoRequest fixture")
    fao.add_argument("--out")
    fao.add_argument("--reference-profiles",action="store_true",help="enable published numerical reference profiles")
    fao.add_argument("--metric",action="append",default=[])
    comp=sub.add_parser("compare")
    comp.add_argument("run_a");comp.add_argument("run_b");comp.add_argument("--out");comp.add_argument("--fork-date")
    aquacmp=sub.add_parser("aquacrop-compare")
    aquacmp.add_argument("run_a");aquacmp.add_argument("run_b")
    aquacmp.add_argument("--fork-date",required=True);aquacmp.add_argument("--out")
    aqua=sub.add_parser("aquacrop-fixture")
    aqua.add_argument("directory");aqua.add_argument("--label",default="baseline")
    aqua.add_argument("--plot-id",default="tunis-demo");aqua.add_argument("--branch-id",default="baseline")
    aqua.add_argument("--out")
    aqua.add_argument("--metric",action="append",default=[])
    real=sub.add_parser("aquacrop-run")
    real.add_argument("--planting",choices=["10/01","11/01"],default="10/01")
    real.add_argument("--out")
    real.add_argument("--branch-id",default="original")
    real.add_argument("--metric",action="append",default=[])
    args=p.parse_args(argv)
    try:
        if args.command=="capabilities":result=registry();out=None
        elif args.command=="fao56":
            result=run_fao(request_from_dict(json.loads(Path(args.input).read_text(encoding="utf-8"))),
                capabilities=CapabilityRegistry(include_reference_profiles=args.reference_profiles),
                requested_outputs=args.metric)
            out=args.out
        elif args.command=="compare":result=compare_runs(json.loads(Path(args.run_a).read_text(encoding="utf-8")),json.loads(Path(args.run_b).read_text(encoding="utf-8")),fork_date=args.fork_date);out=args.out
        elif args.command=="aquacrop-compare":
            result=compare_aquacrop_runs(json.loads(Path(args.run_a).read_text(encoding="utf-8")),json.loads(Path(args.run_b).read_text(encoding="utf-8")),fork_date=args.fork_date);out=args.out
        elif args.command=="aquacrop-fixture":
            result=parse_aquacrop_fixture(args.directory,label=args.label,
                    plot_id=args.plot_id,branch_id=args.branch_id,start_date="1979-10-01",
                    input_snapshot_id="published-Tunis-Wheat-SandyLoam",weather_realization_id="tunis_climate.txt",
                    requested_outputs=args.metric);out=args.out
        else:
            result=run_published_wheat(planting_mmdd=args.planting,branch_id=args.branch_id,
                requested_outputs=args.metric);out=args.out
        dump(result,out)
        return 0
    except (ScienceError,ValueError,FileNotFoundError) as exc:
        print(json.dumps({"status":"failed","code":getattr(exc,"code","INVALID_FILE"),
                          "error":str(exc)}),file=sys.stderr)
        return 2

if __name__=="__main__":sys.exit(main())
