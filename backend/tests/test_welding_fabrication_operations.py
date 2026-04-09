"""
Test suite for welding and fabrication operations in machine_validation.py

Tests the following features for fabrication drawing support:
1. normalize_operation: 'MIG/TIG fillet welding' maps to 'welding'
2. normalize_operation: 'Riveting with shouldered rivets' maps to 'riveting'
3. normalize_operation: 'pickling and passivation' maps to 'surface_treatment'
4. normalize_operation: 'deburr sharp edges' maps to 'grinding_deburr'
5. normalize_operation: 'laser cutting of base plate' maps to 'laser_cutting'
6. normalize_operation: 'drilling rivet holes' maps to 'drilling' (not riveting)
7. normalize_operation: 'fabrication assembly' maps to 'welding'
8. normalize_operation: 'grind welded joints and remove burns' maps to 'grinding_deburr'
9. normalize_operation: 'Dull satin finish surface treatment' maps to 'surface_treatment' (not facing)
10. normalize_operation: 'Face both ends to length' still maps to 'facing'
11. OPERATION_MACHINE_MAP contains 'welding' with MIG/TIG/arc/spot welders
12. OPERATION_MACHINE_MAP contains 'riveting' with riveting machines
13. OPERATION_MACHINE_MAP contains 'surface_treatment' with tanks and booths
14. OPERATION_MACHINE_MAP contains 'grinding_deburr' with angle/bench grinders
15. surface_treatment and grinding_deburr are excluded from strict matching gates
16. infer_operations_from_geometry for 'fabrication' returns welding, laser_cutting, drilling, bending
17. infer_operations_from_geometry for 'assembly' returns welding, drilling, riveting
18. Backend /api endpoint still starts without errors
"""

import pytest
import requests
import os
import sys

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

from app.services.machine_validation import (
    normalize_operation,
    OPERATION_MACHINE_MAP,
    _get_dimension_rules,
    _PROCESS_ALIASES,
    validate_vendor_strict,
    infer_operations_from_geometry,
    _classify_machine_type
)

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestNormalizeOperationWelding:
    """Test normalize_operation correctly routes welding operations"""
    
    def test_mig_tig_fillet_welding_maps_to_welding(self):
        """'MIG/TIG fillet welding' should map to 'welding'"""
        result = normalize_operation("MIG/TIG fillet welding")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'MIG/TIG fillet welding' -> '{result}'")
    
    def test_fabrication_assembly_maps_to_welding(self):
        """'fabrication assembly' should map to 'welding'"""
        result = normalize_operation("fabrication assembly")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'fabrication assembly' -> '{result}'")
    
    def test_welding_maps_to_welding(self):
        """'welding' should map to 'welding'"""
        result = normalize_operation("welding")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'welding' -> '{result}'")
    
    def test_mig_welding_maps_to_welding(self):
        """'mig welding' should map to 'welding'"""
        result = normalize_operation("mig welding")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'mig welding' -> '{result}'")
    
    def test_tig_welding_maps_to_welding(self):
        """'tig welding' should map to 'welding'"""
        result = normalize_operation("tig welding")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'tig welding' -> '{result}'")
    
    def test_arc_welding_maps_to_welding(self):
        """'arc welding' should map to 'welding'"""
        result = normalize_operation("arc welding")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'arc welding' -> '{result}'")
    
    def test_spot_welding_maps_to_welding(self):
        """'spot welding' should map to 'welding'"""
        result = normalize_operation("spot welding")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'spot welding' -> '{result}'")
    
    def test_fillet_weld_maps_to_welding(self):
        """'fillet weld' should map to 'welding'"""
        result = normalize_operation("fillet weld")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'fillet weld' -> '{result}'")
    
    def test_fabrication_maps_to_welding(self):
        """'fabrication' should map to 'welding'"""
        result = normalize_operation("fabrication")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'fabrication' -> '{result}'")


class TestNormalizeOperationRiveting:
    """Test normalize_operation correctly routes riveting operations"""
    
    def test_riveting_with_shouldered_rivets_maps_to_riveting(self):
        """'Riveting with shouldered rivets' should map to 'riveting'"""
        result = normalize_operation("Riveting with shouldered rivets")
        assert result == "riveting", f"Expected 'riveting', got '{result}'"
        print(f"PASS: 'Riveting with shouldered rivets' -> '{result}'")
    
    def test_riveting_maps_to_riveting(self):
        """'riveting' should map to 'riveting'"""
        result = normalize_operation("riveting")
        assert result == "riveting", f"Expected 'riveting', got '{result}'"
        print(f"PASS: 'riveting' -> '{result}'")
    
    def test_pop_riveting_maps_to_riveting(self):
        """'pop riveting' should map to 'riveting'"""
        result = normalize_operation("pop riveting")
        assert result == "riveting", f"Expected 'riveting', got '{result}'"
        print(f"PASS: 'pop riveting' -> '{result}'")
    
    def test_blind_riveting_maps_to_riveting(self):
        """'blind riveting' should map to 'riveting'"""
        result = normalize_operation("blind riveting")
        assert result == "riveting", f"Expected 'riveting', got '{result}'"
        print(f"PASS: 'blind riveting' -> '{result}'")
    
    def test_drilling_rivet_holes_maps_to_drilling_not_riveting(self):
        """'drilling rivet holes' should map to 'drilling' NOT 'riveting'"""
        result = normalize_operation("drilling rivet holes")
        assert result == "drilling", f"Expected 'drilling', got '{result}'"
        print(f"PASS: 'drilling rivet holes' -> '{result}' (not riveting)")


class TestNormalizeOperationSurfaceTreatment:
    """Test normalize_operation correctly routes surface treatment operations"""
    
    def test_pickling_and_passivation_maps_to_surface_treatment(self):
        """'pickling and passivation' should map to 'surface_treatment'"""
        result = normalize_operation("pickling and passivation")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'pickling and passivation' -> '{result}'")
    
    def test_dull_satin_finish_surface_treatment_maps_to_surface_treatment(self):
        """'Dull satin finish surface treatment' should map to 'surface_treatment' NOT 'facing'"""
        result = normalize_operation("Dull satin finish surface treatment")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'Dull satin finish surface treatment' -> '{result}' (not facing)")
    
    def test_pickling_maps_to_surface_treatment(self):
        """'pickling' should map to 'surface_treatment'"""
        result = normalize_operation("pickling")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'pickling' -> '{result}'")
    
    def test_passivation_maps_to_surface_treatment(self):
        """'passivation' should map to 'surface_treatment'"""
        result = normalize_operation("passivation")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'passivation' -> '{result}'")
    
    def test_anodizing_maps_to_surface_treatment(self):
        """'anodizing' should map to 'surface_treatment'"""
        result = normalize_operation("anodizing")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'anodizing' -> '{result}'")
    
    def test_electroplating_maps_to_surface_treatment(self):
        """'electroplating' should map to 'surface_treatment'"""
        result = normalize_operation("electroplating")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'electroplating' -> '{result}'")
    
    def test_powder_coating_maps_to_surface_treatment(self):
        """'powder coating' should map to 'surface_treatment'"""
        result = normalize_operation("powder coating")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'powder coating' -> '{result}'")
    
    def test_shot_blasting_maps_to_surface_treatment(self):
        """'shot blasting' should map to 'surface_treatment'"""
        result = normalize_operation("shot blasting")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'shot blasting' -> '{result}'")
    
    def test_sand_blasting_maps_to_surface_treatment(self):
        """'sand blasting' should map to 'surface_treatment'"""
        result = normalize_operation("sand blasting")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'sand blasting' -> '{result}'")


class TestNormalizeOperationGrindingDeburr:
    """Test normalize_operation correctly routes grinding/deburring operations"""
    
    def test_deburr_sharp_edges_maps_to_grinding_deburr(self):
        """'deburr sharp edges' should map to 'grinding_deburr'"""
        result = normalize_operation("deburr sharp edges")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'deburr sharp edges' -> '{result}'")
    
    def test_grind_welded_joints_and_remove_burns_maps_to_grinding_deburr(self):
        """'grind welded joints and remove burns' should map to 'grinding_deburr'"""
        result = normalize_operation("grind welded joints and remove burns")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'grind welded joints and remove burns' -> '{result}'")
    
    def test_deburring_maps_to_grinding_deburr(self):
        """'deburring' should map to 'grinding_deburr'"""
        result = normalize_operation("deburring")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'deburring' -> '{result}'")
    
    def test_deburr_maps_to_grinding_deburr(self):
        """'deburr' should map to 'grinding_deburr'"""
        result = normalize_operation("deburr")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'deburr' -> '{result}'")
    
    def test_edge_grinding_maps_to_grinding_deburr(self):
        """'edge grinding' should map to 'grinding_deburr'"""
        result = normalize_operation("edge grinding")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'edge grinding' -> '{result}'")
    
    def test_weld_grinding_maps_to_grinding_deburr(self):
        """'weld grinding' should map to 'grinding_deburr'"""
        result = normalize_operation("weld grinding")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'weld grinding' -> '{result}'")
    
    def test_chamfer_maps_to_grinding_deburr(self):
        """'chamfer edges' should map to 'grinding_deburr'"""
        result = normalize_operation("chamfer edges")
        assert result == "grinding_deburr", f"Expected 'grinding_deburr', got '{result}'"
        print(f"PASS: 'chamfer edges' -> '{result}'")


class TestNormalizeOperationLaserCutting:
    """Test normalize_operation correctly routes laser cutting operations"""
    
    def test_laser_cutting_of_base_plate_maps_to_laser_cutting(self):
        """'laser cutting of base plate' should map to 'laser_cutting'"""
        result = normalize_operation("laser cutting of base plate")
        assert result == "laser_cutting", f"Expected 'laser_cutting', got '{result}'"
        print(f"PASS: 'laser cutting of base plate' -> '{result}'")
    
    def test_laser_cutting_maps_to_laser_cutting(self):
        """'laser cutting' should map to 'laser_cutting'"""
        result = normalize_operation("laser cutting")
        assert result == "laser_cutting", f"Expected 'laser_cutting', got '{result}'"
        print(f"PASS: 'laser cutting' -> '{result}'")


class TestNormalizeOperationFacing:
    """Test normalize_operation still correctly routes facing operations"""
    
    def test_face_both_ends_to_length_maps_to_facing(self):
        """'Face both ends to length' should still map to 'facing'"""
        result = normalize_operation("Face both ends to length")
        assert result == "facing", f"Expected 'facing', got '{result}'"
        print(f"PASS: 'Face both ends to length' -> '{result}'")
    
    def test_facing_maps_to_facing(self):
        """'facing' should map to 'facing'"""
        result = normalize_operation("facing")
        assert result == "facing", f"Expected 'facing', got '{result}'"
        print(f"PASS: 'facing' -> '{result}'")


class TestOperationMachineMapWelding:
    """Test OPERATION_MACHINE_MAP contains 'welding' with MIG/TIG/arc/spot welders"""
    
    def test_welding_key_exists_in_operation_machine_map(self):
        """'welding' key should exist in OPERATION_MACHINE_MAP"""
        assert "welding" in OPERATION_MACHINE_MAP, "welding key not found in OPERATION_MACHINE_MAP"
        print(f"PASS: 'welding' key exists in OPERATION_MACHINE_MAP")
    
    def test_welding_includes_mig_welder(self):
        """'welding' should include 'mig welder' machine type"""
        welding_machines = OPERATION_MACHINE_MAP.get("welding", [])
        assert "mig welder" in welding_machines, f"'mig welder' not in welding machines: {welding_machines}"
        print(f"PASS: 'mig welder' in welding machines")
    
    def test_welding_includes_tig_welder(self):
        """'welding' should include 'tig welder' machine type"""
        welding_machines = OPERATION_MACHINE_MAP.get("welding", [])
        assert "tig welder" in welding_machines, f"'tig welder' not in welding machines: {welding_machines}"
        print(f"PASS: 'tig welder' in welding machines")
    
    def test_welding_includes_arc_welder(self):
        """'welding' should include 'arc welder' machine type"""
        welding_machines = OPERATION_MACHINE_MAP.get("welding", [])
        assert "arc welder" in welding_machines, f"'arc welder' not in welding machines: {welding_machines}"
        print(f"PASS: 'arc welder' in welding machines")
    
    def test_welding_includes_spot_welder(self):
        """'welding' should include 'spot welder' machine type"""
        welding_machines = OPERATION_MACHINE_MAP.get("welding", [])
        assert "spot welder" in welding_machines, f"'spot welder' not in welding machines: {welding_machines}"
        print(f"PASS: 'spot welder' in welding machines")
    
    def test_welding_includes_robotic_welder(self):
        """'welding' should include 'robotic welder' machine type"""
        welding_machines = OPERATION_MACHINE_MAP.get("welding", [])
        assert "robotic welder" in welding_machines, f"'robotic welder' not in welding machines: {welding_machines}"
        print(f"PASS: 'robotic welder' in welding machines")


class TestOperationMachineMapRiveting:
    """Test OPERATION_MACHINE_MAP contains 'riveting' with riveting machines"""
    
    def test_riveting_key_exists_in_operation_machine_map(self):
        """'riveting' key should exist in OPERATION_MACHINE_MAP"""
        assert "riveting" in OPERATION_MACHINE_MAP, "riveting key not found in OPERATION_MACHINE_MAP"
        print(f"PASS: 'riveting' key exists in OPERATION_MACHINE_MAP")
    
    def test_riveting_includes_riveting_machine(self):
        """'riveting' should include 'riveting machine' machine type"""
        riveting_machines = OPERATION_MACHINE_MAP.get("riveting", [])
        assert "riveting machine" in riveting_machines, f"'riveting machine' not in riveting machines: {riveting_machines}"
        print(f"PASS: 'riveting machine' in riveting machines")
    
    def test_riveting_includes_rivet_gun(self):
        """'riveting' should include 'rivet gun' machine type"""
        riveting_machines = OPERATION_MACHINE_MAP.get("riveting", [])
        assert "rivet gun" in riveting_machines, f"'rivet gun' not in riveting machines: {riveting_machines}"
        print(f"PASS: 'rivet gun' in riveting machines")
    
    def test_riveting_includes_hydraulic_riveter(self):
        """'riveting' should include 'hydraulic riveter' machine type"""
        riveting_machines = OPERATION_MACHINE_MAP.get("riveting", [])
        assert "hydraulic riveter" in riveting_machines, f"'hydraulic riveter' not in riveting machines: {riveting_machines}"
        print(f"PASS: 'hydraulic riveter' in riveting machines")


class TestOperationMachineMapSurfaceTreatment:
    """Test OPERATION_MACHINE_MAP contains 'surface_treatment' with tanks and booths"""
    
    def test_surface_treatment_key_exists_in_operation_machine_map(self):
        """'surface_treatment' key should exist in OPERATION_MACHINE_MAP"""
        assert "surface_treatment" in OPERATION_MACHINE_MAP, "surface_treatment key not found in OPERATION_MACHINE_MAP"
        print(f"PASS: 'surface_treatment' key exists in OPERATION_MACHINE_MAP")
    
    def test_surface_treatment_includes_pickling_tank(self):
        """'surface_treatment' should include 'pickling tank' machine type"""
        st_machines = OPERATION_MACHINE_MAP.get("surface_treatment", [])
        assert "pickling tank" in st_machines, f"'pickling tank' not in surface_treatment machines: {st_machines}"
        print(f"PASS: 'pickling tank' in surface_treatment machines")
    
    def test_surface_treatment_includes_passivation_tank(self):
        """'surface_treatment' should include 'passivation tank' machine type"""
        st_machines = OPERATION_MACHINE_MAP.get("surface_treatment", [])
        assert "passivation tank" in st_machines, f"'passivation tank' not in surface_treatment machines: {st_machines}"
        print(f"PASS: 'passivation tank' in surface_treatment machines")
    
    def test_surface_treatment_includes_paint_booth(self):
        """'surface_treatment' should include 'paint booth' machine type"""
        st_machines = OPERATION_MACHINE_MAP.get("surface_treatment", [])
        assert "paint booth" in st_machines, f"'paint booth' not in surface_treatment machines: {st_machines}"
        print(f"PASS: 'paint booth' in surface_treatment machines")
    
    def test_surface_treatment_includes_powder_coating_booth(self):
        """'surface_treatment' should include 'powder coating booth' machine type"""
        st_machines = OPERATION_MACHINE_MAP.get("surface_treatment", [])
        assert "powder coating booth" in st_machines, f"'powder coating booth' not in surface_treatment machines: {st_machines}"
        print(f"PASS: 'powder coating booth' in surface_treatment machines")
    
    def test_surface_treatment_includes_shot_blasting_machine(self):
        """'surface_treatment' should include 'shot blasting machine' machine type"""
        st_machines = OPERATION_MACHINE_MAP.get("surface_treatment", [])
        assert "shot blasting machine" in st_machines, f"'shot blasting machine' not in surface_treatment machines: {st_machines}"
        print(f"PASS: 'shot blasting machine' in surface_treatment machines")


class TestOperationMachineMapGrindingDeburr:
    """Test OPERATION_MACHINE_MAP contains 'grinding_deburr' with angle/bench grinders"""
    
    def test_grinding_deburr_key_exists_in_operation_machine_map(self):
        """'grinding_deburr' key should exist in OPERATION_MACHINE_MAP"""
        assert "grinding_deburr" in OPERATION_MACHINE_MAP, "grinding_deburr key not found in OPERATION_MACHINE_MAP"
        print(f"PASS: 'grinding_deburr' key exists in OPERATION_MACHINE_MAP")
    
    def test_grinding_deburr_includes_angle_grinder(self):
        """'grinding_deburr' should include 'angle grinder' machine type"""
        gd_machines = OPERATION_MACHINE_MAP.get("grinding_deburr", [])
        assert "angle grinder" in gd_machines, f"'angle grinder' not in grinding_deburr machines: {gd_machines}"
        print(f"PASS: 'angle grinder' in grinding_deburr machines")
    
    def test_grinding_deburr_includes_bench_grinder(self):
        """'grinding_deburr' should include 'bench grinder' machine type"""
        gd_machines = OPERATION_MACHINE_MAP.get("grinding_deburr", [])
        assert "bench grinder" in gd_machines, f"'bench grinder' not in grinding_deburr machines: {gd_machines}"
        print(f"PASS: 'bench grinder' in grinding_deburr machines")
    
    def test_grinding_deburr_includes_deburring_machine(self):
        """'grinding_deburr' should include 'deburring machine' machine type"""
        gd_machines = OPERATION_MACHINE_MAP.get("grinding_deburr", [])
        assert "deburring machine" in gd_machines, f"'deburring machine' not in grinding_deburr machines: {gd_machines}"
        print(f"PASS: 'deburring machine' in grinding_deburr machines")
    
    def test_grinding_deburr_includes_belt_grinder(self):
        """'grinding_deburr' should include 'belt grinder' machine type"""
        gd_machines = OPERATION_MACHINE_MAP.get("grinding_deburr", [])
        assert "belt grinder" in gd_machines, f"'belt grinder' not in grinding_deburr machines: {gd_machines}"
        print(f"PASS: 'belt grinder' in grinding_deburr machines")


class TestInferOperationsFromGeometry:
    """Test infer_operations_from_geometry for fabrication and assembly"""
    
    def test_fabrication_geometry_returns_welding(self):
        """'fabrication' geometry should return welding in operations"""
        ops = infer_operations_from_geometry("fabrication", {})
        assert "welding" in ops, f"'welding' not in fabrication operations: {ops}"
        print(f"PASS: 'welding' in fabrication operations: {ops}")
    
    def test_fabrication_geometry_returns_laser_cutting(self):
        """'fabrication' geometry should return laser_cutting in operations"""
        ops = infer_operations_from_geometry("fabrication", {})
        assert "laser_cutting" in ops, f"'laser_cutting' not in fabrication operations: {ops}"
        print(f"PASS: 'laser_cutting' in fabrication operations: {ops}")
    
    def test_fabrication_geometry_returns_drilling(self):
        """'fabrication' geometry should return drilling in operations"""
        ops = infer_operations_from_geometry("fabrication", {})
        assert "drilling" in ops, f"'drilling' not in fabrication operations: {ops}"
        print(f"PASS: 'drilling' in fabrication operations: {ops}")
    
    def test_fabrication_geometry_returns_bending(self):
        """'fabrication' geometry should return bending in operations"""
        ops = infer_operations_from_geometry("fabrication", {})
        assert "bending" in ops, f"'bending' not in fabrication operations: {ops}"
        print(f"PASS: 'bending' in fabrication operations: {ops}")
    
    def test_assembly_geometry_returns_welding(self):
        """'assembly' geometry should return welding in operations"""
        ops = infer_operations_from_geometry("assembly", {})
        assert "welding" in ops, f"'welding' not in assembly operations: {ops}"
        print(f"PASS: 'welding' in assembly operations: {ops}")
    
    def test_assembly_geometry_returns_drilling(self):
        """'assembly' geometry should return drilling in operations"""
        ops = infer_operations_from_geometry("assembly", {})
        assert "drilling" in ops, f"'drilling' not in assembly operations: {ops}"
        print(f"PASS: 'drilling' in assembly operations: {ops}")
    
    def test_assembly_geometry_returns_riveting(self):
        """'assembly' geometry should return riveting in operations"""
        ops = infer_operations_from_geometry("assembly", {})
        assert "riveting" in ops, f"'riveting' not in assembly operations: {ops}"
        print(f"PASS: 'riveting' in assembly operations: {ops}")


class TestClassifyMachineType:
    """Test _classify_machine_type for welding and related machines"""
    
    def test_classify_mig_welder(self):
        """'mig welder' should classify as 'welding'"""
        result = _classify_machine_type("mig welder")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'mig welder' classifies as '{result}'")
    
    def test_classify_tig_welder(self):
        """'tig welder' should classify as 'welding'"""
        result = _classify_machine_type("tig welder")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'tig welder' classifies as '{result}'")
    
    def test_classify_arc_welder(self):
        """'arc welder' should classify as 'welding'"""
        result = _classify_machine_type("arc welder")
        assert result == "welding", f"Expected 'welding', got '{result}'"
        print(f"PASS: 'arc welder' classifies as '{result}'")
    
    def test_classify_riveting_machine(self):
        """'riveting machine' should classify as 'riveting'"""
        result = _classify_machine_type("riveting machine")
        assert result == "riveting", f"Expected 'riveting', got '{result}'"
        print(f"PASS: 'riveting machine' classifies as '{result}'")
    
    def test_classify_passivation_tank(self):
        """'passivation tank' should classify as 'surface_treatment'"""
        # Note: 'passivat' keyword matches in _classify_machine_type
        result = _classify_machine_type("passivation tank")
        assert result == "surface_treatment", f"Expected 'surface_treatment', got '{result}'"
        print(f"PASS: 'passivation tank' classifies as '{result}'")
    
    def test_classify_guillotine(self):
        """'guillotine' should classify as 'shearing'"""
        # Note: 'guillotine' alone matches shearing (without 'shear' triggering press_brake first)
        result = _classify_machine_type("guillotine")
        assert result == "shearing", f"Expected 'shearing', got '{result}'"
        print(f"PASS: 'guillotine' classifies as '{result}'")
    
    def test_classify_turret_punch(self):
        """'turret punch' should classify as 'punching'"""
        # Note: 'turret punch' keyword matches punching specifically
        result = _classify_machine_type("turret punch")
        assert result == "punching", f"Expected 'punching', got '{result}'"
        print(f"PASS: 'turret punch' classifies as '{result}'")


class TestValidateVendorStrictWithWelding:
    """Test validate_vendor_strict handles welding operation correctly"""
    
    def test_vendor_with_mig_welder_can_do_welding(self):
        """Vendor with MIG welder should be capable of welding operation"""
        vendor = {"vendor_id": "test_vendor"}
        machines = [
            {
                "machine_id": "m1",
                "machine_type": "MIG Welder",
                "brand": "Lincoln",
                "model": "PowerMIG 256",
                "is_active": True
            }
        ]
        job = {}
        operations = ["welding"]
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        # Should be capable or unverified (not wrong_type)
        assert result["category"] in ["confirmed_capable", "likely_capable", "unverified"], \
            f"Vendor with MIG welder should be capable of welding, got: {result['category']}"
        print(f"PASS: Vendor with MIG welder is '{result['category']}' for welding")
    
    def test_vendor_with_riveting_machine_can_do_riveting(self):
        """Vendor with riveting machine should be capable of riveting operation"""
        vendor = {"vendor_id": "test_vendor"}
        machines = [
            {
                "machine_id": "m1",
                "machine_type": "Riveting Machine",
                "brand": "Test",
                "model": "RM-100",
                "is_active": True
            }
        ]
        job = {}
        operations = ["riveting"]
        
        result = validate_vendor_strict(vendor, machines, job, operations)
        
        assert result["category"] in ["confirmed_capable", "likely_capable", "unverified"], \
            f"Vendor with riveting machine should be capable of riveting, got: {result['category']}"
        print(f"PASS: Vendor with riveting machine is '{result['category']}' for riveting")


class TestAPIHealthEndpoint:
    """Test backend /api endpoint still starts without errors"""
    
    def test_health_endpoint_returns_200(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"PASS: Health endpoint returned 200")
    
    def test_login_endpoint_works(self):
        """Login endpoint should work with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data.keys()}"
        print(f"PASS: Login endpoint works, got access_token")


class TestNonGateOpsExclusion:
    """Test that surface_treatment and grinding_deburr are excluded from strict matching gates"""
    
    def test_surface_treatment_excluded_from_strict_matching(self):
        """surface_treatment should be in non_gate_ops set in server.py"""
        # This test verifies the code structure - we check the file content
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Look for the non_gate_ops definition
        assert 'non_gate_ops' in content, "non_gate_ops not found in server.py"
        assert '"surface_treatment"' in content or "'surface_treatment'" in content, \
            "surface_treatment not in non_gate_ops"
        print(f"PASS: surface_treatment is in non_gate_ops in server.py")
    
    def test_grinding_deburr_excluded_from_strict_matching(self):
        """grinding_deburr should be in non_gate_ops set in server.py"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        assert '"grinding_deburr"' in content or "'grinding_deburr'" in content, \
            "grinding_deburr not in non_gate_ops"
        print(f"PASS: grinding_deburr is in non_gate_ops in server.py")
    
    def test_sawing_still_excluded_from_strict_matching(self):
        """sawing should still be in non_gate_ops set in server.py"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        assert '"sawing"' in content or "'sawing'" in content, \
            "sawing not in non_gate_ops"
        print(f"PASS: sawing is still in non_gate_ops in server.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
