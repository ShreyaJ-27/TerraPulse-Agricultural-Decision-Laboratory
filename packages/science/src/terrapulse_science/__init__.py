"""TerraPulse Developer A science boundary. No network/service imports at import time."""
from .contracts import (ScienceError, FaoRequest, Soil, CropKc, WeatherDay, request_from_dict)
from .fao56 import fao_day, kc_at_day, run_fao
from .compare import compare_runs, compare_aquacrop_runs
from .capability import CapabilityRegistry, dry_bean_reference_profile, turmeric_profile, registry
from .c1_c8 import from_c1_with_root_depth, irrigation_from_c8
from .aquacrop_adapter import parse_aquacrop_fixture, parse_aquacrop_outputs, run_published_wheat
__all__ = ["ScienceError","FaoRequest","Soil","CropKc","WeatherDay","request_from_dict",
           "fao_day","kc_at_day","run_fao","compare_runs","compare_aquacrop_runs","turmeric_profile","registry",
           "CapabilityRegistry","dry_bean_reference_profile",
           "from_c1_with_root_depth","irrigation_from_c8",
           "parse_aquacrop_fixture","parse_aquacrop_outputs","run_published_wheat"]
