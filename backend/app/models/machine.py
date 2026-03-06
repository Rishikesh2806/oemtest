"""
Machine-related Pydantic Models
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class Machine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    machine_id: str
    vendor_id: str
    name: Optional[str] = None
    machine_category: Optional[str] = None
    machine_type: str
    brand: str
    model: str
    # Standard dimensions
    max_x: Optional[float] = None
    max_y: Optional[float] = None
    max_z: Optional[float] = None
    max_diameter: Optional[float] = None
    max_length: Optional[float] = None
    max_swing: Optional[float] = None
    # Boring/Drilling specific
    bore_diameter: Optional[float] = None
    outer_diameter: Optional[float] = None
    spindle_bore: Optional[float] = None
    spindle_travel: Optional[float] = None
    arm_length: Optional[float] = None
    max_depth: Optional[float] = None
    # VTL/Table specific
    table_diameter: Optional[float] = None
    table_size_x: Optional[float] = None
    table_size_y: Optional[float] = None
    pallet_size: Optional[float] = None
    max_weight: Optional[float] = None
    # Shaping specific
    max_stroke: Optional[float] = None
    stroke: Optional[float] = None
    # Gear specific
    max_module: Optional[float] = None
    min_teeth: Optional[int] = None
    # 5-Axis specific
    a_axis_range: Optional[float] = None
    c_axis_range: Optional[float] = None
    # Sheet Metal/Press specific
    tonnage: Optional[float] = None
    max_thickness: Optional[float] = None
    # Laser specific
    laser_power: Optional[float] = None
    # Welding specific
    amperage: Optional[float] = None
    # Heat Treatment specific
    max_temp: Optional[float] = None
    # Inspection specific
    accuracy: Optional[float] = None
    # Additive specific
    layer_thickness: Optional[float] = None
    # EDM specific
    max_taper_angle: Optional[float] = None
    # Common fields
    tolerance_capability: float = 0.1
    tolerance: Optional[float] = None
    axis_config: Optional[str] = None
    materials_supported: List[str] = []
    materials: Optional[List[str]] = None
    monthly_capacity_hours: int = 160
    is_active: bool = True
    # Availability status
    availability_status: str = "available"  # available, engaged, maintenance, offline
    engaged_until: Optional[str] = None  # ISO date when machine becomes available
    engaged_order_id: Optional[str] = None  # Order ID the machine is engaged with
    availability_note: Optional[str] = None  # Optional note about availability
    created_at: str = ""


class MachineCreate(BaseModel):
    name: Optional[str] = None
    machine_category: Optional[str] = None
    machine_type: str
    brand: str
    model: str
    # Standard dimensions
    max_x: Optional[float] = None
    max_y: Optional[float] = None
    max_z: Optional[float] = None
    max_diameter: Optional[float] = None
    max_length: Optional[float] = None
    max_swing: Optional[float] = None
    # Boring/Drilling specific
    bore_diameter: Optional[float] = None
    outer_diameter: Optional[float] = None
    spindle_bore: Optional[float] = None
    spindle_travel: Optional[float] = None
    arm_length: Optional[float] = None
    max_depth: Optional[float] = None
    # VTL/Table specific
    table_diameter: Optional[float] = None
    table_size_x: Optional[float] = None
    table_size_y: Optional[float] = None
    pallet_size: Optional[float] = None
    max_weight: Optional[float] = None
    # Shaping specific
    max_stroke: Optional[float] = None
    stroke: Optional[float] = None
    # Gear specific
    max_module: Optional[float] = None
    min_teeth: Optional[int] = None
    # 5-Axis specific
    a_axis_range: Optional[float] = None
    c_axis_range: Optional[float] = None
    # Sheet Metal/Press specific
    tonnage: Optional[float] = None
    max_thickness: Optional[float] = None
    # Laser specific
    laser_power: Optional[float] = None
    # Welding specific
    amperage: Optional[float] = None
    # Heat Treatment specific
    max_temp: Optional[float] = None
    # Inspection specific
    accuracy: Optional[float] = None
    # Additive specific
    layer_thickness: Optional[float] = None
    # EDM specific
    max_taper_angle: Optional[float] = None
    # Common fields
    tolerance_capability: float = 0.1
    tolerance: Optional[float] = None
    axis_config: Optional[str] = None
    materials_supported: List[str] = []
    materials: Optional[List[str]] = None
    monthly_capacity_hours: int = 160
    # Availability status
    availability_status: str = "available"
    engaged_until: Optional[str] = None
    availability_note: Optional[str] = None


class MachineAvailabilityUpdate(BaseModel):
    availability_status: str  # available, engaged, maintenance, offline
    engaged_until: Optional[str] = None
    availability_note: Optional[str] = None


# Machine Categories - 21 categories with dimension fields
MACHINE_CATEGORIES = {
    "CNC Turning/Lathe": {
        "types": ["CNC Lathe", "CNC Turning", "Swiss Lathe", "CNC Turn-Mill"],
        "dimension_fields": [
            {"key": "max_length", "label": "Max Turning Length (mm)", "type": "number"},
            {"key": "max_diameter", "label": "Max Turning Diameter (mm)", "type": "number"},
            {"key": "max_swing", "label": "Max Swing Over Bed (mm)", "type": "number"}
        ]
    },
    "VTL (Vertical Turret Lathe)": {
        "types": ["VTL", "Vertical Turret Lathe", "CNC VTL", "Double Column VTL"],
        "dimension_fields": [
            {"key": "max_diameter", "label": "Max Turning Diameter (mm)", "type": "number"},
            {"key": "max_length", "label": "Max Turning Height (mm)", "type": "number"},
            {"key": "table_diameter", "label": "Table Diameter (mm)", "type": "number"},
            {"key": "max_weight", "label": "Max Workpiece Weight (kg)", "type": "number"}
        ]
    },
    "VMC (Vertical Machining Center)": {
        "types": ["VMC", "CNC VMC", "High Speed VMC", "Heavy Duty VMC", "Double Column VMC"],
        "dimension_fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
            {"key": "table_size_x", "label": "Table Size X (mm)", "type": "number"},
            {"key": "table_size_y", "label": "Table Size Y (mm)", "type": "number"}
        ]
    },
    "HMC (Horizontal Machining Center)": {
        "types": ["HMC", "CNC HMC", "Pallet HMC", "High Speed HMC"],
        "dimension_fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
            {"key": "pallet_size", "label": "Pallet Size (mm)", "type": "number"}
        ]
    },
    "5-Axis Machining": {
        "types": ["5-Axis VMC", "5-Axis HMC", "5-Axis Mill-Turn", "5-Axis Gantry"],
        "dimension_fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
            {"key": "max_diameter", "label": "Max Part Diameter (mm)", "type": "number"},
            {"key": "a_axis_range", "label": "A-Axis Range (deg)", "type": "number"},
            {"key": "c_axis_range", "label": "C-Axis Range (deg)", "type": "number"}
        ]
    },
    "Conventional Lathe": {
        "types": ["Engine Lathe", "Turret Lathe", "Capstan Lathe", "Gap Bed Lathe", "Heavy Duty Lathe"],
        "dimension_fields": [
            {"key": "max_length", "label": "Center Distance (mm)", "type": "number"},
            {"key": "max_diameter", "label": "Swing Over Bed (mm)", "type": "number"},
            {"key": "spindle_bore", "label": "Spindle Bore (mm)", "type": "number"}
        ]
    },
    "Conventional Milling": {
        "types": ["Universal Milling", "Vertical Milling", "Horizontal Milling", "Knee Mill", "Bed Mill", "Ram Turret Mill"],
        "dimension_fields": [
            {"key": "max_x", "label": "Table Travel X (mm)", "type": "number"},
            {"key": "max_y", "label": "Table Travel Y (mm)", "type": "number"},
            {"key": "max_z", "label": "Head Travel Z (mm)", "type": "number"},
            {"key": "table_size_x", "label": "Table Size X (mm)", "type": "number"},
            {"key": "table_size_y", "label": "Table Size Y (mm)", "type": "number"}
        ]
    },
    "Boring Machine": {
        "types": ["Horizontal Boring Mill", "Vertical Boring Mill", "Jig Boring", "Line Boring", "CNC Boring Mill", "Floor Boring"],
        "dimension_fields": [
            {"key": "bore_diameter", "label": "Max Spindle Diameter (mm)", "type": "number"},
            {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
            {"key": "max_z", "label": "Z-Axis/Spindle Travel (mm)", "type": "number"}
        ]
    },
    "Shaping Machine": {
        "types": ["Shaper", "Planer", "Slotter", "CNC Shaper"],
        "dimension_fields": [
            {"key": "max_stroke", "label": "Max Stroke Length (mm)", "type": "number"},
            {"key": "max_x", "label": "Table Travel X (mm)", "type": "number"},
            {"key": "max_y", "label": "Table Travel Y (mm)", "type": "number"},
            {"key": "table_size_x", "label": "Table Size X (mm)", "type": "number"}
        ]
    },
    "Gear Manufacturing": {
        "types": ["Gear Hobbing", "Gear Shaping", "Gear Grinding", "Gear Shaving", "Bevel Gear Generator", "CNC Gear Hobbing"],
        "dimension_fields": [
            {"key": "max_diameter", "label": "Max Gear Diameter (mm)", "type": "number"},
            {"key": "max_module", "label": "Max Module (mm)", "type": "number"},
            {"key": "max_length", "label": "Max Face Width (mm)", "type": "number"},
            {"key": "min_teeth", "label": "Min No. of Teeth", "type": "number"}
        ]
    },
    "Grinding": {
        "types": ["Surface Grinder", "Cylindrical Grinder", "Centerless Grinder", "ID Grinder", "Tool & Cutter Grinder", "CNC Grinding"],
        "dimension_fields": [
            {"key": "max_x", "label": "Table Travel/Length (mm)", "type": "number"},
            {"key": "max_y", "label": "Table Width (mm)", "type": "number"},
            {"key": "max_diameter", "label": "Max Grinding Diameter (mm)", "type": "number"},
            {"key": "max_length", "label": "Max Grinding Length (mm)", "type": "number"}
        ]
    },
    "EDM": {
        "types": ["Wire EDM", "Sinker EDM", "Hole Drilling EDM", "CNC EDM"],
        "dimension_fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
            {"key": "max_taper_angle", "label": "Max Taper Angle (deg)", "type": "number"},
            {"key": "max_thickness", "label": "Max Workpiece Thickness (mm)", "type": "number"}
        ]
    },
    "Drilling Machine": {
        "types": ["Radial Drill", "Pillar Drill", "Bench Drill", "Gang Drill", "CNC Drilling", "Deep Hole Drilling"],
        "dimension_fields": [
            {"key": "max_diameter", "label": "Max Drilling Diameter (mm)", "type": "number"},
            {"key": "max_depth", "label": "Max Drilling Depth (mm)", "type": "number"},
            {"key": "spindle_travel", "label": "Spindle Travel (mm)", "type": "number"},
            {"key": "arm_length", "label": "Radial Arm Length (mm)", "type": "number"}
        ]
    },
    "Laser Cutting": {
        "types": ["CO2 Laser", "Fiber Laser", "Tube Laser", "3D Laser Cutting"],
        "dimension_fields": [
            {"key": "max_x", "label": "Cutting Area X (mm)", "type": "number"},
            {"key": "max_y", "label": "Cutting Area Y (mm)", "type": "number"},
            {"key": "max_thickness", "label": "Max Cutting Thickness (mm)", "type": "number"},
            {"key": "laser_power", "label": "Laser Power (kW)", "type": "number"}
        ]
    },
    "Plasma/Waterjet Cutting": {
        "types": ["Plasma Cutting", "Waterjet Cutting", "CNC Plasma", "Abrasive Waterjet"],
        "dimension_fields": [
            {"key": "max_x", "label": "Cutting Area X (mm)", "type": "number"},
            {"key": "max_y", "label": "Cutting Area Y (mm)", "type": "number"},
            {"key": "max_thickness", "label": "Max Cutting Thickness (mm)", "type": "number"}
        ]
    },
    "Sheet Metal/Press": {
        "types": ["Press Brake", "Hydraulic Press", "Mechanical Press", "Punch Press", "Shearing Machine", "Roll Forming"],
        "dimension_fields": [
            {"key": "max_length", "label": "Bed Length (mm)", "type": "number"},
            {"key": "max_thickness", "label": "Max Sheet Thickness (mm)", "type": "number"},
            {"key": "tonnage", "label": "Tonnage/Press Force (ton)", "type": "number"},
            {"key": "stroke", "label": "Stroke (mm)", "type": "number"}
        ]
    },
    "Welding": {
        "types": ["MIG Welding", "TIG Welding", "ARC Welding", "Spot Welding", "Seam Welding", "Laser Welding", "Robot Welding", "Submerged Arc Welding"],
        "dimension_fields": [
            {"key": "max_thickness", "label": "Max Weld Thickness (mm)", "type": "number"},
            {"key": "max_length", "label": "Max Weld Length (mm)", "type": "number"},
            {"key": "amperage", "label": "Max Amperage (A)", "type": "number"}
        ]
    },
    "Heat Treatment": {
        "types": ["Furnace", "Induction Hardening", "Case Hardening", "Annealing", "Quenching", "Tempering"],
        "dimension_fields": [
            {"key": "max_x", "label": "Chamber Length (mm)", "type": "number"},
            {"key": "max_y", "label": "Chamber Width (mm)", "type": "number"},
            {"key": "max_z", "label": "Chamber Height (mm)", "type": "number"},
            {"key": "max_temp", "label": "Max Temperature (C)", "type": "number"}
        ]
    },
    "Surface Treatment": {
        "types": ["Shot Blasting", "Sand Blasting", "Electroplating", "Anodizing", "Powder Coating", "Painting"],
        "dimension_fields": [
            {"key": "max_x", "label": "Max Part Length (mm)", "type": "number"},
            {"key": "max_y", "label": "Max Part Width (mm)", "type": "number"},
            {"key": "max_z", "label": "Max Part Height (mm)", "type": "number"},
            {"key": "max_weight", "label": "Max Part Weight (kg)", "type": "number"}
        ]
    },
    "Inspection/CMM": {
        "types": ["CMM", "Vision System", "Profile Projector", "Roughness Tester", "Hardness Tester", "3D Scanner"],
        "dimension_fields": [
            {"key": "max_x", "label": "Measuring Range X (mm)", "type": "number"},
            {"key": "max_y", "label": "Measuring Range Y (mm)", "type": "number"},
            {"key": "max_z", "label": "Measuring Range Z (mm)", "type": "number"},
            {"key": "accuracy", "label": "Accuracy (um)", "type": "number"}
        ]
    },
    "Additive Manufacturing": {
        "types": ["FDM", "SLA", "SLS", "DMLS", "SLM", "Binder Jetting", "Metal 3D Printing"],
        "dimension_fields": [
            {"key": "max_x", "label": "Build Volume X (mm)", "type": "number"},
            {"key": "max_y", "label": "Build Volume Y (mm)", "type": "number"},
            {"key": "max_z", "label": "Build Volume Z (mm)", "type": "number"},
            {"key": "layer_thickness", "label": "Min Layer Thickness (um)", "type": "number"}
        ]
    }
}
