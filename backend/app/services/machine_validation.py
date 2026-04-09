"""
Strict Machine Capability Validation Engine v2.0 for OEMLinker.

Physics-based HARD GATES - not scoring penalties.
A 3000mm shaft on a 2000mm lathe = EXCLUDED, not penalized.

Multi-Operation Decomposition:
  "Shaft with keyway and ground finish" -> turning + milling (keyway) + grinding

Vendor Categories:
  1. confirmed_capable  - Right machines + dimensions verified for ALL operations
  2. likely_capable      - Right machine types, missing dimension specs (cannot verify)
  3. partial_match       - Can handle SOME operations but not all
  4. excluded_too_small  - Right machine type, fails dimension gate
  5. excluded_wrong_type - No compatible machine for any operation
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

CLEARANCE_FACTOR = 1.10  # 10% safety margin on all dimensions

# =====================================================================
# 1. OPERATION -> REQUIRED MACHINE TYPES (hard compatibility)
# =====================================================================
# Each operation maps to machine types that CAN physically perform it.
# If a vendor has NONE of these, that operation is a hard fail.

OPERATION_MACHINE_MAP = {
    # -- Rotational operations --
    "turning": [
        "cnc lathe", "cnc turning", "turret lathe", "capstan lathe", "engine lathe",
        "gap bed lathe", "heavy duty lathe", "swiss lathe", "cnc turn-mill",
        "turn-mill center", "turn-mill", "vtl", "vertical turret lathe", "cnc vtl",
    ],
    "facing": [
        "cnc lathe", "cnc turning", "turret lathe", "engine lathe", "facing lathe",
        "cnc turn-mill", "turn-mill center", "vtl", "vertical turret lathe", "cnc vtl",
    ],
    "boring": [
        "boring machine", "floor boring", "cnc boring", "horizontal boring",
        "vmc", "cnc vmc", "hmc", "cnc hmc",
        "cnc lathe", "cnc turning", "vtl", "vertical turret lathe",
    ],
    "threading_external": [
        "cnc lathe", "cnc turning", "turret lathe", "engine lathe",
        "thread rolling machine", "cnc turn-mill", "turn-mill center",
    ],
    "threading_internal": [
        "cnc lathe", "cnc turning", "vmc", "cnc vmc", "hmc", "cnc hmc",
        "tapping machine", "drill press", "cnc turn-mill",
    ],
    # -- Prismatic / 3-axis operations --
    "milling": [
        "vmc", "cnc vmc", "hmc", "cnc hmc", "milling machine", "universal milling",
        "vertical milling", "horizontal milling", "bed mill", "knee mill",
        "5-axis vmc", "5-axis hmc", "5-axis mill-turn", "5-axis gantry",
        "cnc turn-mill", "turn-mill center", "double column vmc", "high speed vmc",
    ],
    "keyway": [
        "vmc", "cnc vmc", "hmc", "cnc hmc", "milling machine", "broaching machine",
        "shaping machine", "slotting machine", "5-axis vmc",
    ],
    "drilling": [
        "cnc lathe", "cnc turning", "cnc turn-mill", "turn-mill center",
        "drill press", "radial drill", "deep hole drill",
        "vmc", "cnc vmc", "hmc", "cnc hmc", "5-axis vmc",
    ],
    "5axis": [
        "5-axis vmc", "5-axis hmc", "5-axis mill-turn", "5-axis gantry",
    ],
    # -- Grinding --
    "surface_grinding": ["surface grinder", "cnc surface grinder"],
    "cylindrical_grinding": [
        "cylindrical grinder", "cnc cylindrical grinder", "universal grinder",
        "centerless grinder",
    ],
    "grinding": [
        "surface grinder", "cnc surface grinder", "cylindrical grinder",
        "cnc cylindrical grinder", "universal grinder", "centerless grinder",
        "tool & cutter grinder",
    ],
    # -- Specialty --
    "broaching": ["broaching machine", "vertical broaching", "horizontal broaching"],
    "bending": [
        "press brake", "cnc press brake", "hydraulic press",
        "roll bending machine", "bending machine",
    ],
    "laser_cutting": ["laser cutting machine", "fiber laser", "co2 laser", "laser cutter"],
    "edm_wire": ["wire edm", "wire cut edm", "cnc wire edm"],
    "edm_sink": ["sink edm", "die sink edm", "cnc sink edm", "sinker edm"],
    "welding": [
        "mig welder", "tig welder", "arc welder", "spot welder",
        "welding machine", "mig/mag", "tig", "arc", "robotic welder",
        "stud welder", "resistance welder", "orbital welder",
        "welding positioner", "welding rotator", "submerged arc welder",
    ],
    "riveting": [
        "riveting machine", "rivet gun", "hydraulic riveter", "pneumatic riveter",
        "orbital riveter", "riveting press", "pop rivet gun",
    ],
    "surface_treatment": [
        "pickling tank", "passivation tank", "phosphating tank",
        "electroplating machine", "anodizing tank", "paint booth",
        "powder coating booth", "shot blasting machine", "sand blasting machine",
        "tumbling machine", "vibratory finishing",
    ],
    "grinding_deburr": [
        "angle grinder", "bench grinder", "pedestal grinder",
        "deburring machine", "belt grinder", "surface grinder", "cnc surface grinder",
        "portable grinder", "die grinder",
    ],
    "shearing": [
        "shearing machine", "hydraulic shear", "cnc shear",
        "guillotine shear", "plate shear", "mechanical shear",
    ],
    "punching": [
        "punch press", "cnc punch", "turret punch", "hydraulic punch",
        "ironworker", "punching machine",
    ],
    "sheet_metal": [
        "press brake", "cnc press brake", "hydraulic press", "shearing machine",
        "punch press", "cnc punch", "laser cutting machine", "fiber laser",
        "co2 laser", "plasma cutting", "roll forming",
    ],
    "heat_treatment": [
        "heat treatment furnace", "furnace", "induction heater",
        "quenching tank", "tempering furnace",
    ],
    "gear_cutting": [
        "gear hobbing", "gear shaping", "gear grinder", "gear machine",
        "hobbing machine", "gear shaper",
    ],
    "sawing": [
        "band saw", "bandsaw", "hacksaw", "power saw", "circular saw",
        "cold saw", "metal saw", "saw machine", "cutting saw",
        "horizontal band saw", "vertical band saw",
    ],
}


# =====================================================================
# 2. DIMENSION RULES PER OPERATION
# =====================================================================
# For each operation, which machine dimension fields to check against
# which job dimension fields. These are HARD GATES.

def _get_dimension_rules(operation: str) -> list:
    """
    Returns list of dimension check rules for an operation.
    Each rule: {
        "machine_fields": [list of machine fields to try, first non-zero wins],
        "job_field": "job requirement field name",
        "job_fallback": "optional fallback field",
        "label": "human-readable label for fail message",
    }
    """
    rules = {
        "turning": [
            {
                "machine_fields": ["max_diameter", "max_swing", "swing_over_bed"],
                "job_field": "diameter",
                "job_fallback": "outer_diameter",
                "label": "swing/diameter",
            },
            {
                "machine_fields": ["max_length", "distance_between_centers"],
                "job_field": "length",
                "label": "bed length",
            },
        ],
        "facing": [
            {
                "machine_fields": ["max_diameter", "max_swing", "swing_over_bed"],
                "job_field": "diameter",
                "job_fallback": "outer_diameter",
                "label": "swing/diameter",
            },
            {
                "machine_fields": ["max_length", "distance_between_centers"],
                "job_field": "length",
                "label": "bed length (part must fit)",
            },
        ],
        "boring": [
            {
                "machine_fields": ["bore_diameter", "max_diameter"],
                "job_field": "inner_diameter",
                "job_fallback": "diameter",
                "label": "bore diameter",
            },
        ],
        "milling": [
            {
                "machine_fields": ["max_x", "table_size_x", "x_travel"],
                "job_field": "length",
                "label": "X-travel",
            },
            {
                "machine_fields": ["max_y", "table_size_y", "y_travel"],
                "job_field": "width",
                "label": "Y-travel",
            },
            {
                "machine_fields": ["max_z", "z_travel"],
                "job_field": "height",
                "label": "Z-travel",
            },
        ],
        "keyway": [
            {
                "machine_fields": ["max_x", "table_size_x"],
                "job_field": "length",
                "label": "X-travel",
            },
            {
                "machine_fields": ["max_y", "table_size_y"],
                "job_field": "width",
                "label": "Y-travel",
            },
        ],
        "5axis": [
            {
                "machine_fields": ["max_x", "table_size_x"],
                "job_field": "length",
                "label": "X-travel",
            },
            {
                "machine_fields": ["max_y", "table_size_y"],
                "job_field": "width",
                "label": "Y-travel",
            },
            {
                "machine_fields": ["max_z"],
                "job_field": "height",
                "label": "Z-travel",
            },
        ],
        "drilling": [
            {
                "machine_fields": ["max_diameter", "bore_diameter"],
                "job_field": "hole_diameter",
                "job_fallback": "diameter",
                "label": "drill capacity",
            },
        ],
        "surface_grinding": [
            {
                "machine_fields": ["max_x", "max_length"],
                "job_field": "length",
                "label": "grinding length",
            },
            {
                "machine_fields": ["max_y", "max_diameter"],
                "job_field": "width",
                "label": "grinding width",
            },
        ],
        "cylindrical_grinding": [
            {
                "machine_fields": ["max_length", "max_x"],
                "job_field": "length",
                "label": "grinding length",
            },
            {
                "machine_fields": ["max_diameter", "max_y"],
                "job_field": "diameter",
                "label": "grinding diameter",
            },
        ],
        "grinding": [
            {
                "machine_fields": ["max_x", "max_length", "max_diameter"],
                "job_field": "length",
                "job_fallback": "diameter",
                "label": "grinding capacity",
            },
        ],
        "bending": [
            {
                "machine_fields": ["max_x", "max_length"],
                "job_field": "length",
                "label": "bending length",
            },
        ],
        "laser_cutting": [
            {
                "machine_fields": ["max_x"],
                "job_field": "length",
                "label": "bed X",
            },
            {
                "machine_fields": ["max_y"],
                "job_field": "width",
                "label": "bed Y",
            },
            {
                "machine_fields": ["max_thickness"],
                "job_field": "thickness",
                "label": "cutting thickness",
            },
        ],
        "sheet_metal": [
            {
                "machine_fields": ["max_x", "max_length"],
                "job_field": "length",
                "label": "working length",
            },
        ],
        "gear_cutting": [
            {
                "machine_fields": ["max_diameter"],
                "job_field": "diameter",
                "label": "max gear diameter",
            },
        ],
        "sawing": [
            {
                "machine_fields": ["max_diameter", "max_x", "cutting_capacity"],
                "job_field": "diameter",
                "job_fallback": "width",
                "label": "cutting capacity",
            },
        ],
    }
    return rules.get(operation, [])


# =====================================================================
# 3. TOLERANCE MAPPING
# =====================================================================
def _tolerance_to_it_grade(tolerance_mm: float) -> int:
    if tolerance_mm <= 0.001:
        return 3
    if tolerance_mm <= 0.005:
        return 5
    if tolerance_mm <= 0.02:
        return 6
    if tolerance_mm <= 0.05:
        return 7
    if tolerance_mm <= 0.1:
        return 8
    if tolerance_mm <= 0.2:
        return 9
    if tolerance_mm <= 0.5:
        return 11
    return 12


def _machine_achievable_it(machine: dict) -> int:
    """Estimate the IT grade a machine can achieve from its specs or type."""
    mt = (machine.get("machine_type") or "").lower()
    tol = machine.get("tolerance") or machine.get("tolerance_capability")
    if tol:
        try:
            return _tolerance_to_it_grade(float(tol))
        except (ValueError, TypeError):
            pass
    if "grind" in mt:
        return 5
    if "edm" in mt:
        return 5
    if "cnc" in mt or "vmc" in mt or "hmc" in mt or "5-axis" in mt or "5 axis" in mt:
        return 6
    if any(k in mt for k in ["conventional", "engine lathe", "turret lathe", "manual"]):
        return 9
    return 8


# =====================================================================
# 4. MACHINE TYPE CLASSIFIER
# =====================================================================
def _classify_machine_type(machine_type_lower: str) -> str:
    """Classify a machine type string into a broad category for quick lookup."""
    if any(k in machine_type_lower for k in ["lathe", "turn", "capstan"]):
        if "vtl" in machine_type_lower or "vertical turret" in machine_type_lower:
            return "vtl"
        return "turning"
    if "5-axis" in machine_type_lower or "5 axis" in machine_type_lower:
        return "5axis"
    if any(k in machine_type_lower for k in ["vmc", "vertical machining"]):
        return "vmc"
    if any(k in machine_type_lower for k in ["hmc", "horizontal machining"]):
        return "hmc"
    if any(k in machine_type_lower for k in ["mill", "milling"]):
        return "milling"
    if any(k in machine_type_lower for k in ["boring", "floor boring"]):
        return "boring"
    if any(k in machine_type_lower for k in ["drill", "radial drill"]):
        return "drilling"
    if "surface grind" in machine_type_lower:
        return "surface_grinder"
    if "cylindrical grind" in machine_type_lower or "centerless" in machine_type_lower:
        return "cylindrical_grinder"
    if "grind" in machine_type_lower:
        return "grinder"
    if any(k in machine_type_lower for k in ["press brake", "press", "bend", "shear"]):
        return "press_brake"
    if any(k in machine_type_lower for k in ["laser", "fiber laser", "co2 laser"]):
        return "laser"
    if any(k in machine_type_lower for k in ["wire edm", "wire cut"]):
        return "wire_edm"
    if any(k in machine_type_lower for k in ["sink edm", "die sink", "sinker"]):
        return "sink_edm"
    if "edm" in machine_type_lower:
        return "edm"
    if any(k in machine_type_lower for k in ["weld", "mig", "tig", "arc"]):
        return "welding"
    if any(k in machine_type_lower for k in ["gear", "hob"]):
        return "gear"
    if any(k in machine_type_lower for k in ["heat treat", "furnace"]):
        return "heat_treatment"
    if any(k in machine_type_lower for k in ["broach"]):
        return "broaching"
    if any(k in machine_type_lower for k in ["shap", "slot"]):
        return "shaping"
    if any(k in machine_type_lower for k in ["saw", "band saw", "bandsaw", "hacksaw", "cold saw"]):
        return "sawing"
    if any(k in machine_type_lower for k in ["rivet", "riveting"]):
        return "riveting"
    if any(k in machine_type_lower for k in ["pickle", "passivat", "anodiz", "electroplat", "paint", "powder coat", "shot blast", "sand blast", "tumbl"]):
        return "surface_treatment"
    if any(k in machine_type_lower for k in ["shear", "guillotine"]):
        return "shearing"
    if any(k in machine_type_lower for k in ["punch press", "turret punch", "cnc punch", "ironworker"]):
        return "punching"
    return "other"


# =====================================================================
# 5. CHECK: Can this machine type perform this operation?
# =====================================================================
def _machine_can_do_operation(machine_type_lower: str, operation: str) -> bool:
    """Hard gate: is this machine type physically capable of this operation?"""
    allowed_types = OPERATION_MACHINE_MAP.get(operation)
    if not allowed_types:
        return True  # Unknown operation -> allow all (soft pass)
    for allowed in allowed_types:
        if allowed in machine_type_lower or machine_type_lower in allowed:
            return True
    return False


# =====================================================================
# 6. CHECK: Do machine dimensions pass the hard gate for this operation?
# =====================================================================
def _check_dimension_gate(machine: dict, job: dict, operation: str) -> dict:
    """
    Hard dimension gate. Returns:
      {
        "passed": True/False/None (None = cannot verify, missing specs),
        "fail_reasons": [],
        "unverified_reasons": [],
        "specs_checked": {}
      }
    """
    rules = _get_dimension_rules(operation)
    if not rules:
        return {"passed": True, "fail_reasons": [], "unverified_reasons": [], "specs_checked": {}}

    fail_reasons = []
    unverified_reasons = []
    specs_checked = {}
    has_any_unverifiable = False

    for rule in rules:
        # Get job requirement value
        job_val = job.get(rule["job_field"], 0) or 0
        if not job_val and rule.get("job_fallback"):
            job_val = job.get(rule["job_fallback"], 0) or 0

        if not job_val or float(job_val) <= 0:
            continue  # No requirement for this dimension -> skip

        job_val = float(job_val)
        required = job_val * CLEARANCE_FACTOR

        # Get machine spec value (try multiple fields)
        machine_val = 0
        spec_field_used = None
        for mf in rule["machine_fields"]:
            v = machine.get(mf, 0) or 0
            try:
                v = float(v)
            except (ValueError, TypeError):
                v = 0
            if v > 0:
                machine_val = v
                break

        label = rule["label"]
        if machine_val > 0:
            specs_checked[label] = machine_val
            if machine_val < required:
                fail_reasons.append(
                    f"{label}: machine {machine_val:.0f}mm < required {required:.0f}mm "
                    f"(part {job_val:.0f}mm + 10% clearance)"
                )
            # else: passes
        else:
            # Machine spec missing for this dimension -> cannot verify
            has_any_unverifiable = True
            unverified_reasons.append(
                f"{label}: spec not provided, cannot verify for {job_val:.0f}mm requirement"
            )

    if fail_reasons:
        return {"passed": False, "fail_reasons": fail_reasons, "unverified_reasons": [], "specs_checked": specs_checked}
    if has_any_unverifiable:
        return {"passed": None, "fail_reasons": [], "unverified_reasons": unverified_reasons, "specs_checked": specs_checked}
    return {"passed": True, "fail_reasons": [], "unverified_reasons": [], "specs_checked": specs_checked}


# =====================================================================
# 7. TOLERANCE GATE
# =====================================================================
def _check_tolerance_gate(machine: dict, required_tolerance: float) -> dict:
    """Hard gate for tolerance. Returns {passed, reason}."""
    if not required_tolerance or required_tolerance <= 0:
        return {"passed": True, "reason": None}

    machine_it = _machine_achievable_it(machine)
    required_it = _tolerance_to_it_grade(required_tolerance)

    if machine_it > required_it:
        return {
            "passed": False,
            "reason": (
                f"Machine achieves ~IT{machine_it}, job requires ~IT{required_it} "
                f"(+/-{required_tolerance}mm)"
            ),
        }
    return {"passed": True, "reason": None}


# =====================================================================
# 8. WEIGHT GATE
# =====================================================================
def _check_weight_gate(machine: dict, weight_kg: float) -> dict:
    if not weight_kg or weight_kg <= 0:
        return {"passed": True, "reason": None}
    max_w = machine.get("max_weight") or machine.get("table_load_capacity") or 0
    try:
        max_w = float(max_w)
    except (ValueError, TypeError):
        max_w = 0
    if max_w <= 0:
        return {"passed": True, "reason": None}  # No spec -> can't gate
    if max_w < weight_kg * 1.2:
        return {
            "passed": False,
            "reason": f"Part weight {weight_kg}kg exceeds machine capacity {max_w}kg",
        }
    return {"passed": True, "reason": None}


# =====================================================================
# 9. SINGLE OPERATION VALIDATION (core per-machine per-operation check)
# =====================================================================
def validate_machine_for_operation(machine: dict, operation: str, job: dict) -> dict:
    """
    Validate ONE machine against ONE operation with hard gates.

    Returns:
        {
            "result": "capable" | "unverified" | "too_small" | "wrong_type" | "tolerance_fail",
            "machine_id": str,
            "machine_name": str,
            "operation": str,
            "fail_reasons": [],
            "unverified_reasons": [],
            "specs": {},
        }
    """
    mt = (machine.get("machine_type") or "").lower()
    machine_name = f"{machine.get('machine_type', '')} - {machine.get('brand', '')} {machine.get('model', '')}".strip(" -")
    machine_id = machine.get("machine_id", "")

    base = {
        "machine_id": machine_id,
        "machine_name": machine_name,
        "machine_type": machine.get("machine_type", ""),
        "operation": operation,
        "fail_reasons": [],
        "unverified_reasons": [],
        "specs": {},
        "availability": machine.get("availability_status", "unknown"),
    }

    # Gate 1: Machine type compatibility
    if not _machine_can_do_operation(mt, operation):
        base["result"] = "wrong_type"
        base["fail_reasons"].append(
            f"{machine.get('machine_type', mt)} cannot perform '{operation}'"
        )
        return base

    # Gate 2: Dimension check
    dim_check = _check_dimension_gate(machine, job, operation)
    base["specs"] = dim_check["specs_checked"]

    if dim_check["passed"] is False:
        base["result"] = "too_small"
        base["fail_reasons"] = dim_check["fail_reasons"]
        return base

    if dim_check["passed"] is None:
        base["result"] = "unverified"
        base["unverified_reasons"] = dim_check["unverified_reasons"]
        return base

    # Gate 3: Tolerance check
    tol_check = _check_tolerance_gate(machine, job.get("tolerance", 0))
    if not tol_check["passed"]:
        base["result"] = "tolerance_fail"
        base["fail_reasons"].append(tol_check["reason"])
        return base

    # Gate 4: Weight check
    wt_check = _check_weight_gate(machine, job.get("weight_kg", 0))
    if not wt_check["passed"]:
        base["result"] = "too_small"
        base["fail_reasons"].append(wt_check["reason"])
        return base

    # All gates passed
    base["result"] = "capable"
    return base


# =====================================================================
# 10. NORMALIZE PROCESS NAMES
# =====================================================================
_PROCESS_ALIASES = {
    "cnc turning": "turning",
    "cnc lathe": "turning",
    "lathe work": "turning",
    "cnc milling": "milling",
    "face milling": "milling",
    "pocket milling": "milling",
    "profile milling": "milling",
    "slot milling": "milling",
    "end milling": "milling",
    "5-axis machining": "5axis",
    "5 axis machining": "5axis",
    "5-axis milling": "5axis",
    "surface grinding": "surface_grinding",
    "cylindrical grinding": "cylindrical_grinding",
    "centerless grinding": "cylindrical_grinding",
    "od grinding": "cylindrical_grinding",
    "id grinding": "cylindrical_grinding",
    "keyway cutting": "keyway",
    "keyway milling": "keyway",
    "broaching": "broaching",
    "wire edm": "edm_wire",
    "wire cut": "edm_wire",
    "wire cut edm": "edm_wire",
    "sink edm": "edm_sink",
    "die sink edm": "edm_sink",
    "spark erosion": "edm_sink",
    "external threading": "threading_external",
    "internal threading": "threading_internal",
    "tapping": "threading_internal",
    "thread cutting": "threading_external",
    "laser cutting": "laser_cutting",
    "plasma cutting": "laser_cutting",
    "waterjet cutting": "laser_cutting",
    "sheet metal work": "sheet_metal",
    "press brake bending": "bending",
    "bending": "bending",
    "welding": "welding",
    "fabrication": "welding",
    "mig welding": "welding",
    "tig welding": "welding",
    "arc welding": "welding",
    "spot welding": "welding",
    "fillet weld": "welding",
    "groove weld": "welding",
    "butt weld": "welding",
    "plug weld": "welding",
    "seam welding": "welding",
    "stud welding": "welding",
    "resistance welding": "welding",
    "submerged arc welding": "welding",
    "riveting": "riveting",
    "rivet": "riveting",
    "pop riveting": "riveting",
    "blind riveting": "riveting",
    "shoulder rivet": "riveting",
    "surface treatment": "surface_treatment",
    "pickling": "surface_treatment",
    "passivation": "surface_treatment",
    "electroplating": "surface_treatment",
    "anodizing": "surface_treatment",
    "powder coating": "surface_treatment",
    "painting": "surface_treatment",
    "shot blasting": "surface_treatment",
    "sand blasting": "surface_treatment",
    "deburring": "grinding_deburr",
    "deburr": "grinding_deburr",
    "edge grinding": "grinding_deburr",
    "weld grinding": "grinding_deburr",
    "shearing": "shearing",
    "punching": "punching",
    "heat treatment": "heat_treatment",
    "hardening": "heat_treatment",
    "tempering": "heat_treatment",
    "annealing": "heat_treatment",
    "gear hobbing": "gear_cutting",
    "gear shaping": "gear_cutting",
    "gear cutting": "gear_cutting",
    "boring": "boring",
    "drilling": "drilling",
    "deep hole drilling": "drilling",
    "reaming": "boring",
    "sawing": "sawing",
    "band saw": "sawing",
    "bandsaw": "sawing",
    "hacksaw": "sawing",
    "stock cutting": "sawing",
    "cut to length": "sawing",
    "cut to size": "sawing",
    "bar cutting": "sawing",
    "material cutting": "sawing",
    "cut raw stock": "sawing",
    "cut raw material": "sawing",
    "cut raw steel": "sawing",
    "power saw": "sawing",
    "cold saw": "sawing",
}


def normalize_operation(raw_process: str) -> str:
    """Normalize a raw process string to a standard operation key."""
    p = raw_process.lower().strip()
    if p in OPERATION_MACHINE_MAP:
        return p
    if p in _PROCESS_ALIASES:
        return _PROCESS_ALIASES[p]

    # Keyword detection (priority-ordered: compound patterns first)
    if "deburr" in p or "chamfer" in p:
        return "grinding_deburr"
    if "grind" in p and ("weld" in p or "edge" in p or "burr" in p or "burn" in p):
        return "grinding_deburr"
    if "weld" in p or "fabricat" in p:
        return "welding"
    if "turn" in p or "lathe" in p:
        return "turning"
    if "mill" in p:
        return "milling"
    if "grind" in p:
        return "grinding"
    if "drill" in p:
        return "drilling"
    if "bore" in p or "boring" in p:
        return "boring"
    if "rivet" in p:
        return "riveting"
    if "pickle" in p or "passivat" in p or "anodiz" in p or "electroplat" in p or "powder coat" in p or "shot blast" in p or "sand blast" in p:
        return "surface_treatment"
    if "edm" in p:
        return "edm_wire"
    if "saw" in p or "bandsaw" in p or "hacksaw" in p:
        return "sawing"
    if "cut" in p and any(kw in p for kw in ["stock", "length", "size", "raw", "bar", "material", "piece", "end piece", "billet"]):
        return "sawing"
    if "laser" in p or "plasma" in p or "waterjet" in p or "water jet" in p:
        return "laser_cutting"
    if "cut" in p:
        if any(kw in p for kw in ["sheet", "plate", "profile", "contour", "pattern", "shape"]):
            return "laser_cutting"
        return "sawing"
    if "sheet" in p or "press" in p or "bend" in p:
        return "sheet_metal"
    if "heat" in p or "harden" in p or "temper" in p:
        return "heat_treatment"
    if "gear" in p or "hob" in p:
        return "gear_cutting"
    if "5.axis" in p or "5-axis" in p or "5 axis" in p:
        return "5axis"
    if "thread" in p or "tap" in p:
        return "threading_external"
    if "key" in p or "slot" in p:
        return "keyway"
    if "broach" in p:
        return "broaching"
    if "surface" in p and ("treat" in p or "finish" in p or "coat" in p):
        return "surface_treatment"
    if "face" in p or "facing" in p:
        return "facing"
    if "shear" in p or "guillotine" in p:
        return "shearing"
    if "punch" in p and "press" not in p:
        return "punching"
    if "forg" in p:
        return "milling"
    if "profil" in p:
        return "milling"

    # Fuzzy alias match (fallback only)
    for alias, op in _PROCESS_ALIASES.items():
        if alias in p or p in alias:
            return op

    return p


# =====================================================================
# 11. INFER OPERATIONS FROM PART GEOMETRY (fallback)
# =====================================================================
def infer_operations_from_geometry(geometry: str, job: dict) -> list:
    """When AI doesn't detect specific processes, infer from geometry."""
    mapping = {
        "cylindrical": ["turning"],
        "conical": ["turning"],
        "tube_pipe": ["turning", "boring"],
        "circular_flat": ["turning"],
        "rectangular": ["milling"],
        "complex": ["milling"],
        "sheet_metal": ["sheet_metal", "laser_cutting", "bending"],
        "fabrication": ["welding", "laser_cutting", "drilling", "bending"],
        "assembly": ["welding", "drilling", "riveting"],
        "spherical": ["turning"],
    }
    ops = mapping.get(geometry, ["milling"])

    # If tolerance is tight, likely needs grinding
    tol = job.get("tolerance", 0)
    if tol and float(tol) <= 0.02:
        if geometry in ("cylindrical", "conical", "tube_pipe"):
            if "cylindrical_grinding" not in ops:
                ops.append("cylindrical_grinding")
        else:
            if "surface_grinding" not in ops:
                ops.append("surface_grinding")

    return ops


# =====================================================================
# 12. MAIN: VALIDATE ALL VENDOR MACHINES AGAINST ALL OPERATIONS
# =====================================================================
def validate_vendor_strict(
    vendor: dict,
    machines: list,
    job: dict,
    operations: list,
) -> dict:
    """
    Run strict physics-based validation for a vendor across ALL required operations.

    Args:
        vendor: Vendor document (vendor_id, company_name, etc.)
        machines: List of machine documents for this vendor
        job: Job requirements dict (length, width, height, diameter, tolerance, etc.)
        operations: List of normalized operation strings

    Returns:
        {
            "category": "confirmed_capable" | "likely_capable" | "partial_match"
                       | "excluded_too_small" | "excluded_wrong_type",
            "operations_summary": {
                "operation_name": {
                    "status": "capable" | "unverified" | "too_small" | "wrong_type",
                    "best_machine": {...} or None,
                    "all_candidates": [...]
                }
            },
            "capable_operations": [...],
            "unverified_operations": [...],
            "failed_operations": [...],
            "coverage_pct": float,
            "best_machines": [...],
            "unverified_machines": [...],
            "failed_machines": [...],
        }
    """
    if not operations:
        operations = ["milling"]  # Default fallback

    active_machines = [m for m in machines if m.get("is_active", True)]
    if not active_machines:
        return _empty_result("excluded_wrong_type", operations)

    operations_summary = {}
    capable_ops = []
    unverified_ops = []
    failed_ops = []
    best_machines_map = {}  # machine_id -> machine info
    unverified_machines_map = {}
    failed_machines_list = []

    for op in operations:
        op_results = []
        best_for_op = None
        best_status = "wrong_type"  # worst status

        for machine in active_machines:
            result = validate_machine_for_operation(machine, op, job)
            op_results.append(result)

            # Track the best result for this operation
            if result["result"] == "capable":
                if best_status != "capable":
                    best_status = "capable"
                    best_for_op = result
                elif best_for_op is None:
                    best_for_op = result
            elif result["result"] == "unverified" and best_status not in ("capable",):
                best_status = "unverified"
                if best_for_op is None or best_for_op["result"] not in ("capable",):
                    best_for_op = result
            elif result["result"] == "too_small" and best_status not in ("capable", "unverified"):
                best_status = "too_small"
                if best_for_op is None or best_for_op["result"] not in ("capable", "unverified"):
                    best_for_op = result
            elif result["result"] == "tolerance_fail" and best_status not in ("capable", "unverified"):
                best_status = "tolerance_fail"
                if best_for_op is None or best_for_op["result"] not in ("capable", "unverified"):
                    best_for_op = result

        operations_summary[op] = {
            "status": best_status,
            "best_machine": _sanitize_machine_result(best_for_op) if best_for_op else None,
            "candidates_checked": len(op_results),
        }

        if best_status == "capable":
            capable_ops.append(op)
            if best_for_op:
                mid = best_for_op["machine_id"]
                if mid not in best_machines_map:
                    best_machines_map[mid] = {
                        "machine_id": mid,
                        "machine_name": best_for_op["machine_name"],
                        "machine_type": best_for_op["machine_type"],
                        "specs": best_for_op["specs"],
                        "availability": best_for_op["availability"],
                        "operations_covered": [op],
                    }
                else:
                    best_machines_map[mid]["operations_covered"].append(op)
        elif best_status == "unverified":
            unverified_ops.append(op)
            if best_for_op:
                mid = best_for_op["machine_id"]
                if mid not in unverified_machines_map:
                    unverified_machines_map[mid] = {
                        "machine_id": mid,
                        "machine_name": best_for_op["machine_name"],
                        "machine_type": best_for_op["machine_type"],
                        "specs": best_for_op["specs"],
                        "unverified_reasons": best_for_op["unverified_reasons"],
                        "operations": [op],
                    }
                else:
                    unverified_machines_map[mid]["operations"].append(op)
        else:
            failed_ops.append(op)
            if best_for_op:
                failed_machines_list.append({
                    "machine_name": best_for_op["machine_name"],
                    "machine_type": best_for_op["machine_type"],
                    "operation": op,
                    "result": best_for_op["result"],
                    "fail_reasons": best_for_op["fail_reasons"],
                    "specs": best_for_op["specs"],
                })
            else:
                failed_machines_list.append({
                    "machine_name": "No machine found",
                    "machine_type": "",
                    "operation": op,
                    "result": "wrong_type",
                    "fail_reasons": [f"No machine in vendor's shop can perform '{op}'"],
                    "specs": {},
                })

    # Determine overall category
    total_ops = len(operations)
    capable_count = len(capable_ops)
    unverified_count = len(unverified_ops)
    coverage = (capable_count / total_ops * 100) if total_ops > 0 else 0

    if capable_count == total_ops:
        category = "confirmed_capable"
    elif capable_count + unverified_count == total_ops and capable_count > 0:
        category = "likely_capable"
    elif capable_count + unverified_count == total_ops and capable_count == 0:
        category = "likely_capable"  # All unverified but right types
    elif capable_count > 0:
        category = "partial_match"
    elif unverified_count > 0:
        category = "likely_capable"
    else:
        # All failed - distinguish too_small vs wrong_type
        too_small_fails = [f for f in failed_machines_list if f["result"] in ("too_small", "tolerance_fail")]
        if too_small_fails:
            category = "excluded_too_small"
        else:
            category = "excluded_wrong_type"

    return {
        "category": category,
        "operations_summary": operations_summary,
        "capable_operations": capable_ops,
        "unverified_operations": unverified_ops,
        "failed_operations": failed_ops,
        "coverage_pct": round(coverage, 1),
        "best_machines": list(best_machines_map.values())[:5],
        "unverified_machines": list(unverified_machines_map.values())[:5],
        "failed_machines": failed_machines_list[:5],
        "total_operations": total_ops,
    }


def _sanitize_machine_result(result: dict) -> dict:
    """Pick only serializable fields from a machine validation result."""
    return {
        "machine_id": result.get("machine_id", ""),
        "machine_name": result.get("machine_name", ""),
        "machine_type": result.get("machine_type", ""),
        "result": result.get("result", ""),
        "fail_reasons": result.get("fail_reasons", []),
        "unverified_reasons": result.get("unverified_reasons", []),
        "specs": result.get("specs", {}),
        "availability": result.get("availability", "unknown"),
    }


def _empty_result(category: str, operations: list) -> dict:
    return {
        "category": category,
        "operations_summary": {op: {"status": "wrong_type", "best_machine": None, "candidates_checked": 0} for op in operations},
        "capable_operations": [],
        "unverified_operations": [],
        "failed_operations": operations,
        "coverage_pct": 0.0,
        "best_machines": [],
        "unverified_machines": [],
        "failed_machines": [{"machine_name": "No machines", "operation": op, "result": "wrong_type", "fail_reasons": ["Vendor has no active machines"], "specs": {}} for op in operations],
        "total_operations": len(operations),
    }


# =====================================================================
# BACKWARD COMPAT: Keep old function signatures working
# =====================================================================
def has_complete_specs(machine: dict) -> bool:
    """Check if a machine has all critical dimension fields filled."""
    mt = (machine.get("machine_type") or "").lower()
    cat = _classify_machine_type(mt)
    critical = {
        "turning": ["max_length", "max_diameter"],
        "vtl": ["max_diameter", "max_length"],
        "vmc": ["max_x", "max_y", "max_z"],
        "hmc": ["max_x", "max_y", "max_z"],
        "milling": ["max_x", "max_y", "max_z"],
        "5axis": ["max_x", "max_y", "max_z"],
        "boring": ["bore_diameter"],
        "drilling": ["max_diameter"],
        "surface_grinder": ["max_x", "max_y"],
        "cylindrical_grinder": ["max_length", "max_diameter"],
        "press_brake": ["max_x"],
        "laser": ["max_x", "max_y"],
        "gear": ["max_diameter"],
    }
    required = critical.get(cat, [])
    if not required:
        return True
    for field in required:
        val = machine.get(field)
        if not val or float(val) <= 0:
            return False
    return True


def categorize_vendor_match(vendor, machines, job_requirements, process_list):
    """Backward-compatible wrapper around validate_vendor_strict."""
    ops = [normalize_operation(p) for p in process_list] if process_list else []
    if not ops:
        geom = job_requirements.get("part_geometry", "")
        ops = infer_operations_from_geometry(geom, job_requirements)

    result = validate_vendor_strict(vendor, machines, job_requirements, ops)

    # Map new categories to old ones for compatibility
    cat_map = {
        "confirmed_capable": "fully_capable",
        "likely_capable": "unverified",
        "partial_match": "fully_capable",
        "excluded_too_small": "too_small",
        "excluded_wrong_type": "wrong_type",
    }

    return {
        "category": cat_map.get(result["category"], result["category"]),
        "best_machines": result["best_machines"],
        "unverified_machines": result["unverified_machines"],
        "failed_machines": result["failed_machines"],
        "coverage_pct": result["coverage_pct"],
        "validation_details": [],
        "has_complete_specs": all(has_complete_specs(m) for m in machines if m.get("is_active", True)),
    }
