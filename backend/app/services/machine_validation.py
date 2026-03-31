"""
Strict Machine Capability Validation Engine for OEMLinker.

Enforces physics-based matching: vendors only appear in results if their machines
can physically and technically perform every required operation.

Categories:
  1. Fully Capable — specs confirmed, machine fits
  2. Capable but Unverified — right machine type, missing specs
  3. Wrong Machine Type — incompatible machine for the operation
  4. Machine Too Small — right type but dimensions insufficient
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 1. PROCESS → MACHINE COMPATIBILITY MATRIX
# ──────────────────────────────────────────────────────────────
PROCESS_MACHINE_COMPATIBILITY = {
    "turning": {
        "can": ["cnc lathe", "cnc turning", "turret lathe", "capstan lathe", "engine lathe",
                "gap bed lathe", "heavy duty lathe", "swiss lathe", "cnc turn-mill",
                "turn-mill center", "turn-mill", "vtl", "vertical turret lathe", "cnc vtl"],
        "cannot": ["vmc", "hmc", "drill press", "surface grinder", "cylindrical grinder",
                   "milling machine", "press brake", "edm", "laser", "broaching"]
    },
    "facing": {
        "can": ["cnc lathe", "cnc turning", "turret lathe", "engine lathe", "facing lathe",
                "cnc turn-mill", "turn-mill center", "vtl", "vertical turret lathe", "cnc vtl"],
        "cannot": ["vmc", "drill press", "surface grinder", "cylindrical grinder", "press brake"]
    },
    "milling": {
        "can": ["vmc", "cnc vmc", "hmc", "cnc hmc", "milling machine", "universal milling",
                "vertical milling", "horizontal milling", "bed mill", "knee mill",
                "5-axis vmc", "5-axis hmc", "5-axis mill-turn", "5-axis gantry",
                "cnc turn-mill", "turn-mill center", "double column vmc", "high speed vmc"],
        "cannot": ["cnc lathe", "turret lathe", "drill press", "surface grinder",
                   "cylindrical grinder", "press brake", "laser"]
    },
    "keyway": {
        "can": ["vmc", "cnc vmc", "hmc", "cnc hmc", "milling machine", "broaching machine",
                "shaping machine", "slotting machine", "5-axis vmc"],
        "cannot": ["cnc lathe", "turret lathe", "drill press", "surface grinder",
                   "cylindrical grinder", "press brake", "laser"]
    },
    "drilling": {
        "can": ["cnc lathe", "cnc turning", "cnc turn-mill", "turn-mill center",
                "drill press", "radial drill", "deep hole drill",
                "vmc", "cnc vmc", "hmc", "cnc hmc", "5-axis vmc"],
        "cannot": ["surface grinder", "cylindrical grinder", "press brake", "laser"]
    },
    "boring": {
        "can": ["boring machine", "floor boring", "cnc boring", "horizontal boring",
                "vmc", "cnc vmc", "hmc", "cnc hmc",
                "cnc lathe", "cnc turning", "vtl", "vertical turret lathe"],
        "cannot": ["drill press", "surface grinder", "cylindrical grinder", "press brake", "laser"]
    },
    "threading_external": {
        "can": ["cnc lathe", "cnc turning", "turret lathe", "engine lathe",
                "thread rolling machine", "cnc turn-mill", "turn-mill center"],
        "cannot": ["vmc", "drill press", "surface grinder", "press brake"]
    },
    "threading_internal": {
        "can": ["cnc lathe", "cnc turning", "vmc", "cnc vmc", "hmc", "cnc hmc",
                "tapping machine", "drill press", "cnc turn-mill"],
        "cannot": ["surface grinder", "cylindrical grinder", "press brake"]
    },
    "surface_grinding": {
        "can": ["surface grinder", "cnc surface grinder"],
        "cannot": ["cylindrical grinder", "vmc", "cnc lathe", "drill press", "press brake"]
    },
    "cylindrical_grinding": {
        "can": ["cylindrical grinder", "cnc cylindrical grinder", "universal grinder",
                "centerless grinder"],
        "cannot": ["surface grinder", "vmc", "cnc lathe", "drill press"]
    },
    "grinding": {
        "can": ["surface grinder", "cnc surface grinder", "cylindrical grinder",
                "cnc cylindrical grinder", "universal grinder", "centerless grinder",
                "tool & cutter grinder"],
        "cannot": ["vmc", "cnc lathe", "drill press", "press brake", "laser"]
    },
    "broaching": {
        "can": ["broaching machine", "vertical broaching", "horizontal broaching"],
        "cannot": ["cnc lathe", "drill press", "surface grinder", "press brake", "laser"]
    },
    "bending": {
        "can": ["press brake", "cnc press brake", "hydraulic press", "roll bending machine",
                "bending machine"],
        "cannot": ["cnc lathe", "vmc", "drill press", "surface grinder", "milling machine"]
    },
    "laser_cutting": {
        "can": ["laser cutting machine", "fiber laser", "co2 laser", "laser cutter"],
        "cannot": []  # Only laser machines
    },
    "edm_wire": {
        "can": ["wire edm", "wire cut edm", "cnc wire edm"],
        "cannot": []  # Only wire EDM
    },
    "edm_sink": {
        "can": ["sink edm", "die sink edm", "cnc sink edm", "sinker edm"],
        "cannot": ["wire edm"]
    },
    "welding": {
        "can": ["mig welder", "tig welder", "arc welder", "spot welder",
                "welding machine", "mig/mag", "tig", "arc", "robotic welder"],
        "cannot": []
    },
    "sheet_metal": {
        "can": ["press brake", "cnc press brake", "hydraulic press", "shearing machine",
                "punch press", "cnc punch", "laser cutting machine", "fiber laser",
                "co2 laser", "plasma cutting", "roll forming"],
        "cannot": ["cnc lathe", "surface grinder", "cylindrical grinder"]
    },
    "heat_treatment": {
        "can": ["heat treatment furnace", "furnace", "induction heater",
                "quenching tank", "tempering furnace"],
        "cannot": []
    },
}

# ──────────────────────────────────────────────────────────────
# 2. TOLERANCE → IT GRADE MAPPING
# ──────────────────────────────────────────────────────────────
TOLERANCE_IT_MAP = {
    0.001: "IT3",
    0.005: "IT5",
    0.01:  "IT6",
    0.02:  "IT6",
    0.025: "IT7",
    0.05:  "IT7",
    0.1:   "IT8",
    0.2:   "IT9",
    0.5:   "IT11",
    1.0:   "IT12",
}

# Machine type → minimum achievable IT grade (lower = tighter)
MACHINE_TOLERANCE_CAPABILITY = {
    "cnc": 6,        # IT6
    "cnc_grinder": 4, # IT4
    "manual": 8,      # IT8
    "conventional": 9, # IT9
    "press": 11,      # IT11
    "laser": 9,       # IT9
    "edm": 5,         # IT5
}

# Critical dimension fields per machine category
CRITICAL_SPECS = {
    "turning": ["max_length", "max_diameter"],
    "lathe": ["max_length", "max_diameter"],
    "vtl": ["max_diameter", "max_length"],
    "vmc": ["max_x", "max_y", "max_z"],
    "hmc": ["max_x", "max_y", "max_z"],
    "milling": ["max_x", "max_y", "max_z"],
    "5-axis": ["max_x", "max_y", "max_z"],
    "boring": ["bore_diameter", "max_x", "max_y"],
    "drilling": ["max_diameter", "max_depth"],
    "surface_grinder": ["max_x", "max_y"],
    "cylindrical_grinder": ["max_length", "max_diameter"],
    "press_brake": ["max_x", "tonnage"],
    "laser": ["max_x", "max_y", "max_thickness"],
    "edm": ["max_x", "max_y", "max_z"],
    "welding": ["amperage", "max_thickness"],
    "gear": ["max_diameter", "max_module"],
}


def _classify_machine(machine_type_lower: str) -> str:
    """Classify a machine type string into a broad category."""
    if any(k in machine_type_lower for k in ["lathe", "turn", "capstan"]):
        if "vtl" in machine_type_lower or "vertical turret" in machine_type_lower:
            return "vtl"
        return "turning"
    if any(k in machine_type_lower for k in ["vmc", "vertical machining"]):
        return "vmc"
    if any(k in machine_type_lower for k in ["hmc", "horizontal machining"]):
        return "hmc"
    if "5-axis" in machine_type_lower or "5 axis" in machine_type_lower:
        return "5-axis"
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
        return "surface_grinder"  # default grinder
    if any(k in machine_type_lower for k in ["press brake", "press", "bend", "shear"]):
        return "press_brake"
    if any(k in machine_type_lower for k in ["laser", "fiber laser", "co2 laser"]):
        return "laser"
    if any(k in machine_type_lower for k in ["wire edm", "wire cut"]):
        return "edm"
    if any(k in machine_type_lower for k in ["sink edm", "die sink", "sinker"]):
        return "edm"
    if "edm" in machine_type_lower:
        return "edm"
    if any(k in machine_type_lower for k in ["weld", "mig", "tig", "arc"]):
        return "welding"
    if any(k in machine_type_lower for k in ["gear", "hob"]):
        return "gear"
    if any(k in machine_type_lower for k in ["heat treat", "furnace"]):
        return "heat_treatment"
    return "other"


def has_complete_specs(machine: dict) -> bool:
    """Check if a machine has all critical dimension fields filled for its type."""
    mt = (machine.get("machine_type") or "").lower()
    cat = _classify_machine(mt)
    required_fields = CRITICAL_SPECS.get(cat, [])
    if not required_fields:
        return True  # No critical fields defined = assume complete
    filled = 0
    for field in required_fields:
        val = machine.get(field)
        if val and float(val) > 0:
            filled += 1
    return filled >= len(required_fields)


def _is_machine_compatible_with_process(machine_type_lower: str, process: str) -> bool:
    """Check if a machine type can perform a given manufacturing process."""
    compat = PROCESS_MACHINE_COMPATIBILITY.get(process)
    if not compat:
        return True  # Unknown process — allow all
    can_list = compat["can"]
    for allowed in can_list:
        if allowed in machine_type_lower or machine_type_lower in allowed:
            return True
    return False


def _tolerance_to_it_grade(tolerance_mm: float) -> int:
    """Convert a ± tolerance in mm to an approximate IT grade number."""
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


def _machine_it_capability(machine: dict) -> int:
    """Estimate the IT grade a machine can achieve."""
    mt = (machine.get("machine_type") or "").lower()
    tol = machine.get("tolerance") or machine.get("tolerance_capability")
    if tol and float(tol) > 0:
        return _tolerance_to_it_grade(float(tol))
    # Infer from machine type
    if "grind" in mt:
        return 5
    if "edm" in mt:
        return 5
    if "cnc" in mt:
        return 6
    if any(k in mt for k in ["conventional", "engine lathe", "turret lathe", "manual"]):
        return 9
    return 8  # default


def validate_machine_for_job(machine: dict, job_requirements: dict) -> dict:
    """
    Core validation function. Checks if a specific machine can perform the job.

    Args:
        machine: Machine document from MongoDB
        job_requirements: Dict with keys:
            - process (str): Required process (turning, milling, etc.)
            - length (float): Job part length in mm
            - width (float): Job part width in mm
            - height (float): Job part height in mm
            - diameter (float): Job part diameter in mm
            - inner_diameter (float): Inner bore diameter
            - thickness (float): Sheet/plate thickness
            - tolerance (float): Required tolerance in mm
            - weight_kg (float): Part weight
            - part_geometry (str): cylindrical, rectangular, etc.

    Returns:
        Dict with:
            - can_perform: True / False / None (unknown)
            - category: "fully_capable" / "unverified" / "wrong_type" / "too_small"
            - confidence: "high" / "medium" / "low" / "none"
            - fail_reasons: list of strings
            - warnings: list of strings
            - machine_specs: dict of relevant specs shown to user
    """
    mt = (machine.get("machine_type") or "").lower()
    machine_cat = _classify_machine(mt)
    process = (job_requirements.get("process") or "").lower().replace(" ", "_")
    result = {
        "can_perform": False,
        "category": "wrong_type",
        "confidence": "none",
        "fail_reasons": [],
        "warnings": [],
        "machine_specs": {},
    }

    # ── Step 1: Process-Machine Compatibility ──
    if process and not _is_machine_compatible_with_process(mt, process):
        compat = PROCESS_MACHINE_COMPATIBILITY.get(process, {})
        can_list = compat.get("can", [])[:5]
        result["fail_reasons"].append(
            f"{machine.get('machine_type', mt)} cannot perform {process}. "
            f"Required: {', '.join(can_list)}"
        )
        result["category"] = "wrong_type"
        return result

    # ── Step 2: Check if machine has complete specs ──
    complete = has_complete_specs(machine)
    if not complete:
        # Check if ANY size-dependent dimension is required
        needs_size = any(
            job_requirements.get(k, 0) and job_requirements[k] > 0
            for k in ["length", "width", "height", "diameter", "inner_diameter", "thickness"]
        )
        if needs_size:
            result["can_perform"] = None  # Unknown
            result["category"] = "unverified"
            result["confidence"] = "none"
            result["fail_reasons"].append(
                "Machine specifications not provided. Cannot verify capacity for this job."
            )
            result["warnings"].append(
                "Vendor has not entered machine dimensions. Contact vendor to verify."
            )
            # Still collect whatever specs exist
            result["machine_specs"] = _extract_machine_specs(machine, machine_cat)
            return result

    # ── Step 3: Physical Size Validation ──
    size_result = _validate_size(machine, machine_cat, job_requirements)
    if size_result["failed"]:
        result["category"] = "too_small"
        result["confidence"] = "high" if complete else "medium"
        result["fail_reasons"].extend(size_result["reasons"])
        result["machine_specs"] = size_result["specs"]
        return result
    result["warnings"].extend(size_result.get("warnings", []))
    result["machine_specs"] = size_result["specs"]

    # ── Step 4: Tolerance Validation ──
    req_tolerance = job_requirements.get("tolerance", 0)
    if req_tolerance and req_tolerance > 0:
        machine_it = _machine_it_capability(machine)
        required_it = _tolerance_to_it_grade(req_tolerance)
        if machine_it > required_it:
            result["fail_reasons"].append(
                f"Machine tolerance capability ~IT{machine_it} cannot achieve "
                f"required ±{req_tolerance}mm (~IT{required_it})"
            )
            result["category"] = "too_small"
            result["machine_specs"]["tolerance_it"] = f"IT{machine_it}"
            return result

    # ── Step 5: Weight Check ──
    weight = job_requirements.get("weight_kg", 0)
    max_weight = machine.get("max_weight") or 0
    if weight > 0 and max_weight > 0:
        if max_weight < weight * 1.2:
            result["fail_reasons"].append(
                f"Part weight {weight}kg exceeds machine capacity {max_weight}kg"
            )
            result["category"] = "too_small"
            result["machine_specs"]["max_weight_kg"] = max_weight
            return result

    # ── All checks passed ──
    result["can_perform"] = True
    result["category"] = "fully_capable"
    result["confidence"] = "high" if (complete and machine.get("specs_verified_by_admin")) else "medium"
    return result


def _validate_size(machine: dict, machine_cat: str, job: dict) -> dict:
    """Check physical dimension constraints. Returns {failed, reasons, warnings, specs}."""
    reasons = []
    warnings = []
    specs = _extract_machine_specs(machine, machine_cat)
    clearance = 1.1  # 10% clearance

    if machine_cat in ("turning", "vtl"):
        m_dia = machine.get("max_diameter") or machine.get("max_swing") or 0
        m_len = machine.get("max_length") or 0
        j_dia = job.get("diameter", 0) or job.get("outer_diameter", 0) or 0
        j_len = job.get("length", 0) or 0

        if j_dia > 0 and m_dia > 0 and m_dia < j_dia * clearance:
            reasons.append(
                f"Part diameter {j_dia}mm exceeds machine swing {m_dia}mm "
                f"(need ≥{j_dia * clearance:.0f}mm)"
            )
        elif j_dia > 0 and m_dia == 0:
            warnings.append("Diameter capacity unverified")

        if j_len > 0 and m_len > 0 and m_len < j_len * clearance:
            reasons.append(
                f"Part length {j_len}mm exceeds machine capacity {m_len}mm "
                f"(need ≥{j_len * clearance:.0f}mm)"
            )
        elif j_len > 0 and m_len == 0:
            warnings.append("Length capacity unverified")

    elif machine_cat in ("vmc", "hmc", "milling", "5-axis"):
        m_x = machine.get("max_x") or machine.get("table_size_x") or 0
        m_y = machine.get("max_y") or machine.get("table_size_y") or 0
        m_z = machine.get("max_z") or 0
        j_l = job.get("length", 0) or 0
        j_w = job.get("width", 0) or 0
        j_h = job.get("height", 0) or 0

        if j_l > 0 and m_x > 0 and m_x < j_l * clearance:
            reasons.append(f"X-travel {m_x}mm < part length {j_l}mm (need ≥{j_l * clearance:.0f}mm)")
        elif j_l > 0 and m_x == 0:
            warnings.append("X-travel capacity unverified")

        if j_w > 0 and m_y > 0 and m_y < j_w * clearance:
            reasons.append(f"Y-travel {m_y}mm < part width {j_w}mm (need ≥{j_w * clearance:.0f}mm)")
        elif j_w > 0 and m_y == 0:
            warnings.append("Y-travel capacity unverified")

        if j_h > 0 and m_z > 0 and m_z < j_h * clearance:
            reasons.append(f"Z-travel {m_z}mm < part height {j_h}mm (need ≥{j_h * clearance:.0f}mm)")
        elif j_h > 0 and m_z == 0:
            warnings.append("Z-travel capacity unverified")

    elif machine_cat == "boring":
        m_bore = machine.get("bore_diameter") or machine.get("max_diameter") or 0
        j_dia = job.get("diameter", 0) or job.get("inner_diameter", 0) or 0
        if j_dia > 0 and m_bore > 0 and m_bore < j_dia * clearance:
            reasons.append(f"Bore capacity {m_bore}mm < required {j_dia}mm")

    elif machine_cat == "drilling":
        m_drill_dia = machine.get("max_diameter") or machine.get("bore_diameter") or 0
        m_depth = machine.get("max_depth") or machine.get("max_z") or 0
        j_dia = job.get("diameter", 0) or 0
        j_depth = job.get("height", 0) or job.get("length", 0) or 0
        if j_dia > 0 and m_drill_dia > 0 and m_drill_dia < j_dia:
            reasons.append(f"Max drill diameter {m_drill_dia}mm < required {j_dia}mm")
        if j_depth > 0 and m_depth > 0 and m_depth < j_depth:
            reasons.append(f"Max drill depth {m_depth}mm < required {j_depth}mm")

    elif machine_cat in ("surface_grinder", "cylindrical_grinder"):
        m_len = machine.get("max_x") or machine.get("max_length") or 0
        m_width = machine.get("max_y") or machine.get("max_diameter") or 0
        j_len = job.get("length", 0) or 0
        j_width = job.get("width", 0) or job.get("diameter", 0) or 0
        if j_len > 0 and m_len > 0 and m_len < j_len:
            reasons.append(f"Grinding length {m_len}mm < part {j_len}mm")
        if j_width > 0 and m_width > 0 and m_width < j_width:
            reasons.append(f"Grinding width/dia {m_width}mm < part {j_width}mm")

    elif machine_cat == "press_brake":
        m_bend_len = machine.get("max_x") or machine.get("max_length") or 0
        m_tonnage = machine.get("tonnage") or 0
        j_len = job.get("length", 0) or 0
        j_thickness = job.get("thickness", 0) or 0
        if j_len > 0 and m_bend_len > 0 and m_bend_len < j_len:
            reasons.append(f"Bending length {m_bend_len}mm < part {j_len}mm")
        if j_thickness > 0 and m_tonnage > 0:
            # Rough tonnage estimate: thickness(mm) * length(m) * 8 (for mild steel)
            required_tonnage = j_thickness * (j_len / 1000) * 8 if j_len else j_thickness * 8
            if m_tonnage < required_tonnage:
                reasons.append(f"Tonnage {m_tonnage}T < estimated required {required_tonnage:.0f}T")

    elif machine_cat == "laser":
        m_x = machine.get("max_x") or 0
        m_y = machine.get("max_y") or 0
        m_thick = machine.get("max_thickness") or 0
        j_l = job.get("length", 0) or 0
        j_w = job.get("width", 0) or 0
        j_t = job.get("thickness", 0) or 0
        if j_l > 0 and m_x > 0 and m_x < j_l:
            reasons.append(f"Laser bed X {m_x}mm < sheet length {j_l}mm")
        if j_w > 0 and m_y > 0 and m_y < j_w:
            reasons.append(f"Laser bed Y {m_y}mm < sheet width {j_w}mm")
        if j_t > 0 and m_thick > 0 and m_thick < j_t:
            reasons.append(f"Max cutting thickness {m_thick}mm < required {j_t}mm")

    elif machine_cat == "gear":
        m_dia = machine.get("max_diameter") or 0
        j_dia = job.get("diameter", 0) or 0
        if j_dia > 0 and m_dia > 0 and m_dia < j_dia:
            reasons.append(f"Max gear diameter {m_dia}mm < required {j_dia}mm")

    return {"failed": len(reasons) > 0, "reasons": reasons, "warnings": warnings, "specs": specs}


def _extract_machine_specs(machine: dict, machine_cat: str) -> dict:
    """Extract relevant human-readable specs for display."""
    specs = {}
    name = f"{machine.get('machine_type', '')} - {machine.get('brand', '')} {machine.get('model', '')}".strip(" -")
    specs["machine_name"] = name

    if machine_cat in ("turning", "vtl"):
        if machine.get("max_diameter"):
            specs["max_diameter_mm"] = machine["max_diameter"]
        if machine.get("max_swing"):
            specs["max_swing_mm"] = machine["max_swing"]
        if machine.get("max_length"):
            specs["max_length_mm"] = machine["max_length"]
    elif machine_cat in ("vmc", "hmc", "milling", "5-axis"):
        for k in ("max_x", "max_y", "max_z"):
            if machine.get(k):
                specs[f"travel_{k[-1].upper()}_mm"] = machine[k]
        if machine.get("table_size_x"):
            specs["table_size"] = f"{machine['table_size_x']}x{machine.get('table_size_y', '')}mm"
    elif machine_cat == "boring":
        if machine.get("bore_diameter"):
            specs["bore_diameter_mm"] = machine["bore_diameter"]
    elif machine_cat == "press_brake":
        if machine.get("tonnage"):
            specs["tonnage"] = machine["tonnage"]
        if machine.get("max_x") or machine.get("max_length"):
            specs["bending_length_mm"] = machine.get("max_x") or machine.get("max_length")
    elif machine_cat == "laser":
        if machine.get("max_x"):
            specs["bed_x_mm"] = machine["max_x"]
        if machine.get("max_y"):
            specs["bed_y_mm"] = machine["max_y"]
        if machine.get("laser_power"):
            specs["laser_power_kw"] = machine["laser_power"]
    elif machine_cat == "gear":
        if machine.get("max_diameter"):
            specs["max_gear_diameter_mm"] = machine["max_diameter"]
        if machine.get("max_module"):
            specs["max_module"] = machine["max_module"]

    tol = machine.get("tolerance") or machine.get("tolerance_capability")
    if tol:
        specs["tolerance_mm"] = tol
    if machine.get("availability_status"):
        specs["availability"] = machine["availability_status"]

    return specs


def categorize_vendor_match(
    vendor: dict,
    machines: list,
    job_requirements: dict,
    process_list: list,
) -> dict:
    """
    Run strict validation across ALL of a vendor's machines for the given job.

    Returns:
        {
            "category": "fully_capable" | "unverified" | "wrong_type" | "too_small",
            "best_machines": [...],       # machines that passed
            "unverified_machines": [...],  # right type, missing specs
            "failed_machines": [...],      # with fail reasons
            "coverage_pct": float,         # % of processes this vendor can cover
            "validation_details": [...]    # per-machine validation results
        }
    """
    best_machines = []
    unverified_machines = []
    failed_machines = []
    all_validations = []

    # If no specific processes, infer from geometry
    if not process_list:
        geom = job_requirements.get("part_geometry", "")
        process_list = _infer_processes_from_geometry(geom)

    processes_covered = set()

    for machine in machines:
        if not machine.get("is_active", True):
            continue

        machine_id = machine.get("machine_id", "")

        # Check each required process
        for proc in process_list:
            proc_key = proc.lower().replace(" ", "_")
            vresult = validate_machine_for_job(machine, {**job_requirements, "process": proc_key})
            vresult["process"] = proc
            vresult["machine_id"] = machine_id
            vresult["machine_type"] = machine.get("machine_type", "")
            vresult["machine_name"] = f"{machine.get('machine_type', '')} - {machine.get('brand', '')} {machine.get('model', '')}".strip(" -")
            all_validations.append(vresult)

            if vresult["can_perform"] is True:
                processes_covered.add(proc_key)
                if machine_id not in [m.get("machine_id") for m in best_machines]:
                    best_machines.append({
                        "machine_id": machine_id,
                        "machine_name": vresult["machine_name"],
                        "machine_type": machine.get("machine_type", ""),
                        "specs": vresult["machine_specs"],
                        "confidence": vresult["confidence"],
                        "availability": machine.get("availability_status", "unknown"),
                        "processes_covered": [proc],
                    })
                else:
                    for bm in best_machines:
                        if bm["machine_id"] == machine_id:
                            bm["processes_covered"].append(proc)
                            break

            elif vresult["can_perform"] is None:
                # Unverified
                if machine_id not in [m.get("machine_id") for m in unverified_machines]:
                    unverified_machines.append({
                        "machine_id": machine_id,
                        "machine_name": vresult["machine_name"],
                        "machine_type": machine.get("machine_type", ""),
                        "specs": vresult["machine_specs"],
                        "warnings": vresult["warnings"],
                        "processes": [proc],
                    })
                else:
                    for um in unverified_machines:
                        if um["machine_id"] == machine_id:
                            um["processes"].append(proc)
                            break
            else:
                failed_machines.append({
                    "machine_id": machine_id,
                    "machine_name": vresult["machine_name"],
                    "machine_type": machine.get("machine_type", ""),
                    "process": proc,
                    "category": vresult["category"],
                    "fail_reasons": vresult["fail_reasons"],
                    "specs": vresult["machine_specs"],
                })

    # Determine overall category
    coverage = len(processes_covered) / len(process_list) * 100 if process_list else 0

    if best_machines and coverage >= 50:
        category = "fully_capable"
    elif unverified_machines and not best_machines:
        category = "unverified"
    elif failed_machines and not best_machines and not unverified_machines:
        # Distinguish wrong_type vs too_small
        wrong_types = [f for f in failed_machines if f["category"] == "wrong_type"]
        if len(wrong_types) == len(failed_machines):
            category = "wrong_type"
        else:
            category = "too_small"
    elif best_machines:
        category = "fully_capable"
    else:
        category = "wrong_type"

    return {
        "category": category,
        "best_machines": best_machines,
        "unverified_machines": unverified_machines,
        "failed_machines": failed_machines[:5],  # limit
        "coverage_pct": round(coverage, 1),
        "validation_details": all_validations,
        "has_complete_specs": all(has_complete_specs(m) for m in machines if m.get("is_active", True)),
    }


def _infer_processes_from_geometry(geometry: str) -> list:
    """Infer required processes from part geometry when not explicitly provided."""
    mapping = {
        "cylindrical": ["turning"],
        "conical": ["turning"],
        "tube_pipe": ["turning", "boring"],
        "circular_flat": ["turning"],
        "rectangular": ["milling"],
        "complex": ["milling"],
        "sheet_metal": ["sheet_metal"],
        "spherical": ["turning"],
    }
    return mapping.get(geometry, ["milling"])
