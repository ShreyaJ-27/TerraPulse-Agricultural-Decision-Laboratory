"""C7 capability registry: never derive model support from crop-name matches alone."""
from dataclasses import asdict
from copy import deepcopy
from .contracts import CropKc, fail, nonempty, stable_hash

REGISTRY_VERSION = "dev-a-0.2.0"
OUTPUT_VERSION = "dev-a-science-output-0.2.0"
ADAPTER_VERSION = "dev-a-adapters-0.2.0"
WEATHER_SHA256 = "5da8ee184e107ba1e37a842ec024987c042fb715463dcbcb5d591c3e2b701ccd"
AQUA_PROFILE = {"capabilityId":"dev-a:tunis-wheat-aquacrop-3.1.0",
    "parameterVersion":"Tunis-Wheat-example-3.1.0",
    "parameterSource":"AquaCrop-OSPy 3.1.0 bundled Wheat and SandyLoam defaults; published PyPI example",
    "reference":"https://pypi.org/project/aquacrop/3.1.0/",
    "engineCrop":"Wheat","soilType":"SandyLoam","runtimeVersion":"3.1.0",
    "weatherSha256":WEATHER_SHA256,"plantingDatesMmDd":["10/01","11/01"],
    "initialWaterContent":"FC","startDate":"1979-10-01","endDate":"1985-05-30",
    "validationStatus":"example-runtime-reproducibility; not field calibration"}
FAO_METRICS = {
    "actualEtMm":"mm/day", "potentialEtMm":"mm/day",
    "rootZoneDepletionMm":"mm", "waterStressKs":"fraction",
    "soilThetaM3M3":"m3/m3", "drainageMm":"mm/day", "fallowEtMm":"mm/day",
}
AQUA_METRICS = {
    "actualEtMm":"mm/day", "potentialEtMm":"mm/day", "rootWaterStorageMm":"mm",
    "canopyCoverFraction":"fraction", "rootDepthM":"m", "biomassTonnesPerHa":"tonnes/ha",
    "seasonalDryYieldTonnesPerHa":"tonnes/ha", "drainageMm":"mm/day",
    "fallowEtMm":"mm/day",
}


def require_outputs(requested, supported, engine):
    if not isinstance(requested, (tuple, list)):
        fail("INVALID_OUTPUT_REQUEST", "requested outputs must be a list or tuple")
    for metric in requested:
        if not isinstance(metric, str) or metric not in supported:
            fail("UNSUPPORTED_OUTPUT", f"{engine} cannot supply {metric}")


def require_aquacrop(crop, soil, runtime, parameter_version, requested_outputs=()):
    profile = AQUA_PROFILE
    if (crop, soil, runtime, parameter_version) != (
        profile["engineCrop"], profile["soilType"], profile["runtimeVersion"], profile["parameterVersion"]
    ):
        fail("AQUACROP_UNSUPPORTED", "only the registered Tunis wheat example is supported")
    require_outputs(requested_outputs, AQUA_METRICS, "AquaCrop")
    return deepcopy(profile)


def dry_bean_reference_profile() -> CropKc:
    """FAO-56 Example 28 numerical reference, specific to its example conditions."""
    return CropKc(scientific_name="Phaseolus vulgaris L.",
        parameter_version="FAO56-Example28-dry-bean-v1",
        parameter_source="FAO Irrigation and Drainage Paper 56, chapter 6, Example 28 and Figure 36",
        kc_initial=0.15, kc_mid=1.19, kc_end=0.35,
        stage_lengths_days=(25,25,30,20), mapping_status="provisional")

TURMERIC_A=(15,105,120,30)
TURMERIC_B=(60,90,90,30)
TURMERIC_C=(30,90,105,45)
MAPS={"A":TURMERIC_A,"B":TURMERIC_B,"C":TURMERIC_C}

def turmeric_profile(mapping:str="A") -> CropKc:
    if mapping not in MAPS:fail("UNSUPPORTED_MAPPING", "turmeric mappings: A/B/C provisional only")
    return CropKc(scientific_name="Curcuma longa L.",
        parameter_version=f"Pereira2024-Table7-Chitra2017-provisional-{mapping}",
        parameter_source="Pereira et al. 2024 Table 7; Chitra et al. 2017; FAO-56 Eq66",
        kc_initial=0.40,kc_mid=1.05,kc_end=0.90,
        stage_lengths_days=MAPS[mapping],mapping_status="provisional")

def _default_models() -> list:
    return [
        {"cropScientificName":"Curcuma longa L.","engine":"fao56",
         "status":"conditional-numerical","parameterMappings":["A","B","C"],
         "supportedOutputs":["actualEtMm","potentialEtMm","rootZoneDepletionMm","waterStressKs","soilThetaM3M3","drainageMm"],
         "unsupportedOutputs":["biomassTonnesPerHa","yieldTonnesPerHa","measured canopy cover","layer-wise water profile"],
         "limitations":["provisional stage calendar","fixed root zone","synthetic soil may be used in test fixtures","not field calibrated"]},
        {"cropScientificName":"Triticum aestivum L.","engine":"aquacrop","status":"published-example-runtime-and-fixture",
         "supportedOutputs":["actualEtMm","rootWaterStorageMm","canopyCoverFraction","rootDepthM","biomassTonnesPerHa","seasonalDryYieldTonnesPerHa"],
         "unsupportedOutputs":["FAO56 root-zone depletion from Wr"],
         "limitations":["AquaCrop-OSPy 3.1.0 Tunis SandyLoam published wheat example only","not local calibration","real runtime optional"]}
    ]


class CapabilityRegistry:
    """Scientific parameter registrations, never an identity/alias catalogue.

    Exact scientific-name matching is a boundary check, not name resolution.
    Caller-owned crop IDs are retained as opaque references. Additional FAO
    crops require explicit sourced parameter registration; no calibration is
    inferred from numeric validity. AquaCrop extensions require an adapter and
    evidence for their parameterization before they can be registered here.
    """
    def __init__(self, *, defaults=True, include_reference_profiles=False):
        self._profiles = {}
        self._models = _default_models() if defaults else []
        if defaults:
            for mapping in MAPS:
                self._add(turmeric_profile(mapping), f"dev-a:turmeric-fao56-{mapping}",
                          ["research_evidence/turmeric_seasonal_original_2026-11-04.zip",
                           "https://www.fao.org/4/X0490E/x0490e0e.htm"], None, [])
        if include_reference_profiles:
            self.register_fao_profile(dry_bean_reference_profile(),
                capability_id="dev-a:dry-bean-fao56-example28",
                references=["https://www.fao.org/4/x0490e/x0490e0b.htm"],
                validation_evidence=["FAO-56 Example 28 Kc checkpoints, reproduced in tests/test_v02.py"])

    def _add(self, profile, capability_id, references, external_crop_id, validation_evidence):
        if not isinstance(profile, CropKc):
            fail("MISSING_PARAMETERS", "a complete CropKc parameter set is required")
        profile.validate()
        nonempty(capability_id, "capability_id")
        if not isinstance(references, (list, tuple)) or not references:
            fail("MISSING_PROVENANCE", "scientific source references are required")
        for ref in references:
            nonempty(ref, "parameter reference")
        if external_crop_id is not None:
            nonempty(external_crop_id, "external_crop_id")
        if not isinstance(validation_evidence, (list, tuple)):
            fail("MISSING_PROVENANCE", "validation evidence must be a list")
        for item in validation_evidence:
            nonempty(item, "validation evidence")
        if profile.mapping_status == "calibrated" and not validation_evidence:
            fail("UNCERTIFIED_CALIBRATION", "calibrated profiles require explicit validation evidence")
        key = (profile.scientific_name, profile.parameter_version)
        if key in self._profiles or any(v["capabilityId"] == capability_id for v in self._profiles.values()):
            fail("DUPLICATE_CAPABILITY", "profile identity/version or capability ID already registered")
        record = {"capabilityId":capability_id, "externalCropId":external_crop_id,
                  "parameters":asdict(profile), "parameterHash":stable_hash(asdict(profile)),
                  "references":list(references), "validationEvidence":list(validation_evidence),
                  "validationStatus":"caller-declared-calibration" if profile.mapping_status == "calibrated" else "numerical-only-not-field-calibrated"}
        self._profiles[key] = record

    def register_fao_profile(self, profile, *, capability_id, references,
                             external_crop_id=None, validation_evidence=()):
        self._add(profile, capability_id, references, external_crop_id, validation_evidence)
        if not any(m["engine"] == "fao56" and m["cropScientificName"] == profile.scientific_name for m in self._models):
            self._models.append({"cropScientificName":profile.scientific_name, "engine":"fao56",
                                 "status":"conditional-numerical", "limitations":["caller-supplied parameter evidence; no inferred field validity"]})

    def require_fao(self, profile, *, requested_outputs=()):
        if not isinstance(profile, CropKc):
            fail("MISSING_PARAMETERS", "complete CropKc required")
        profile.validate()
        entry = self._profiles.get((profile.scientific_name, profile.parameter_version))
        if entry is None:
            fail("UNSUPPORTED_CROP_CAPABILITY", "no registered FAO parameter set for this exact crop/version")
        if stable_hash(asdict(profile)) != entry["parameterHash"]:
            fail("PARAMETER_MISMATCH", "parameters differ from the registered scientific profile")
        require_outputs(requested_outputs, FAO_METRICS, "FAO-56")
        return deepcopy(entry)

    def describe(self):
        models = deepcopy(self._models)
        for m in models:
            is_fao = m["engine"] == "fao56"
            m["engineVersion"] = "fao56-single-kc-1.0" if is_fao else "aquacrop-ospy-3.1.0"
            m["adapterVersion"] = ADAPTER_VERSION
            m["outputUnits"] = deepcopy(FAO_METRICS if is_fao else AQUA_METRICS)
            m["supportedOutputs"] = list(m["outputUnits"])
            m["unsupportedOutputs"] = (["biomassTonnesPerHa", "yieldTonnesPerHa", "canopyCoverFraction", "rootDepthM", "layerWiseWaterProfile"] if is_fao else
                                       ["rootZoneDepletionMm", "waterStressKs", "yieldTonnesPerHa", "groundwaterDepthM"])
            if is_fao:
                m["parameterSets"] = [deepcopy(p) for (name, _), p in self._profiles.items() if name == m["cropScientificName"]]
                m["requiredInputs"] = ["registered CropKc", "sourced Soil with fixed root depth and depletion fraction", "daily dated weather with provenance", "initial depletion", "effective irrigation in mm", "fallow Kc when needed"]
            else:
                m["parameterSets"] = [deepcopy(AQUA_PROFILE)]
                m["limitations"] = ["Only registered Tunis/Wheat/SandyLoam example is executable", "No local yield calibration", "Seasonal yield only; no daily yield", "No fertility/salinity/weed/perennial support claimed by this adapter", "Other AquaCrop crops require separate sourced registration, adapter and validation"]
                m["requiredInputs"] = ["exact aquacrop 3.1.0", "verified bundled weather hash", "supported planting date"]
        return {"registryVersion":REGISTRY_VERSION, "scientificOutputVersion":OUTPUT_VERSION,
                "identityOwner":"Developer C; no aliases or canonical crop IDs authored here",
                "unsupportedPolicy":"fail closed; identity/ecology may be supplied by Developer C, never simulated values",
                "models":models}


def registry() -> dict:
    result = CapabilityRegistry().describe()
    result["optInReferenceProfiles"] = CapabilityRegistry(defaults=False, include_reference_profiles=True).describe()["models"]
    return result
