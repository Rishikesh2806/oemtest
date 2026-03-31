# Multi-Operation Decomposition & Split-Vendor Matching — Feature Spec

**Status**: BACKLOG (Saved for future implementation)  
**Priority**: P1  
**Created**: Mar 30, 2026  
**Estimated Effort**: Large (4 phases)

---

## Overview
Upgrade the drawing analysis and vendor matching system to support multi-operation decomposition and split-vendor recommendations. Instead of matching entire RFQs to single vendors, the system will break drawings into individual manufacturing operations and find optimal vendor combinations.

---

## Phase 1 — Backend Core (Operations Engine)

### 1.1 Update Drawing Analysis
Update the GPT-5.2 Vision analysis prompt to extract individual manufacturing operations as a structured JSON array instead of a general summary. Each operation must include:
- Operation type (turning, milling, drilling, keyway, grinding, boring, threading, broaching, EDM, laser cutting, bending, welding)
- Machine required
- Dimensions
- Tolerance
- Sequence order
- Complexity (1-10)
- Whether it can be done by a separate vendor (`splittable: true/false`)

**Expected AI response format:**
```json
{
  "operations": [
    {
      "sequence": 1,
      "operation_type": "turning",
      "description": "Turn OD to 50mm, face both ends",
      "machine_required": "CNC Lathe",
      "dimensions": {"diameter": 50, "length": 120},
      "tolerance": "IT7",
      "complexity": 4,
      "splittable": true,
      "estimated_time_hours": 1.5
    },
    {
      "sequence": 2,
      "operation_type": "milling",
      "description": "Mill keyway 8mm wide x 4mm deep",
      "machine_required": "VMC",
      "dimensions": {"width": 8, "depth": 4, "length": 30},
      "tolerance": "IT8",
      "complexity": 5,
      "splittable": true,
      "estimated_time_hours": 0.75
    }
  ]
}
```

### 1.2 Create Operation Machine Mapping Table
Create `operation_machine_map` MongoDB collection mapping each operation type to compatible machine types:

| Operation | Compatible Machines |
|-----------|-------------------|
| turning | CNC Lathe, VTL, CNC Turning Center |
| milling | VMC, HMC, 5-Axis, CNC Milling |
| drilling | VMC, Drill Press, CNC Lathe (live tooling) |
| keyway | VMC, Slotting Machine, Broaching |
| grinding | Surface Grinder, Cylindrical Grinder, Centerless Grinder |
| boring | HMC, Boring Machine, VMC |
| threading | CNC Lathe, Thread Rolling, Tapping Machine |
| broaching | Broaching Machine |
| EDM | Wire EDM, Sinker EDM |
| laser_cutting | Laser Cutting Machine |
| bending | Press Brake, Bending Machine |
| welding | MIG Welder, TIG Welder, Spot Welder |

### 1.3 Build Operation-Vendor Matching Engine
New function `match_operations_to_vendors()`:
- Takes operations array from drawing analysis
- For each operation, finds all vendors with compatible machines (using operation_machine_map)
- Calculates each vendor's **coverage percentage** across all operations
- Identifies **gaps** where no vendor can perform an operation
- Finds optimal **2-vendor and 3-vendor combinations** that together cover all operations
- Returns structured result with operation-vendor mapping and recommended combinations

**Algorithm:**
```
for each operation:
    find vendors with machines matching operation_machine_map[operation.type]
    filter by dimension capability (machine envelope >= operation dimensions)
    filter by tolerance capability
    
calculate vendor_coverage = operations_covered / total_operations * 100

find combinations:
    for each pair (vendor_a, vendor_b):
        combined_coverage = union(vendor_a.ops, vendor_b.ops) / total * 100
        score = combined_coverage * 0.6 + city_match_bonus * 0.2 + rating_bonus * 0.2
    sort by score descending
```

---

## Phase 2 — Frontend Multi-View Results UI

### 2.1 View 1 — Operations Summary
- List each detected operation with machine required and vendor count
- Warning banner if no single vendor covers all operations
- Color-coded operation cards (green = many vendors, amber = few, red = none)

### 2.2 View 2 — Vendor Capability Matrix
- Table: vendors as rows, operations as columns
- Each cell: ✅ (can do, with machine name) or ❌ (cannot)
- Last column: coverage percentage
- Sorted by coverage % descending
- Highlight row for 100% coverage vendors

### 2.3 View 3 — Recommended Combinations
- When no single vendor covers everything, show 2-3 vendor pair/trio combos
- Each combo shows:
  - Which vendor handles which operations
  - Total coverage %
  - Whether vendors are in same city (logistics benefit)
  - Combined score
- "Request Combined Quote" button for each combination

### 2.4 View 4 — Production Sequence
- Timeline visualization of operations in sequence order
- Each step shows: operation name, vendor assigned, estimated hours
- Total estimated lead time
- Visual flow: Op1 (Vendor A) → Op2 (Vendor A) → Op3 (Vendor B) → ...

---

## Phase 3 — Combined RFQ System

### 3.1 Combined RFQ Backend
When buyer clicks "Request Combined Quote":
- Create ONE parent RFQ record with `is_combined: true`
- Create child operation assignments per vendor
- Each vendor receives notification with ONLY their assigned operations
- Vendor sees: "You are being asked to quote for Operations 1 and 2 (Turning + Keyway). Another vendor will handle Operation 3 (Drilling)."

### 3.2 Combined Quote Aggregation
- When all vendors in a combination submit quotes:
  - Buyer sees combined view: Vendor A quote + Vendor B quote + estimated transport
  - Total cost calculation with breakdown
  - Accept/reject combined or individual quotes

**DB Schema Addition:**
```json
{
  "combined_rfq_id": "crfq_xxx",
  "parent_rfq_id": "rfq_xxx",
  "vendor_assignments": [
    {
      "vendor_id": "v1",
      "operations": [1, 2],
      "status": "pending_quote"
    },
    {
      "vendor_id": "v2", 
      "operations": [3],
      "status": "pending_quote"
    }
  ],
  "combination_score": 92,
  "total_coverage": 100
}
```

---

## Phase 4 — Gap Handling

### 4.1 Zero-Vendor Operations
If an operation has zero capable vendors:
- Highlight in **red** in operations list
- Show message: "No verified vendors found for [operation]. This may require a specialist. Contact us for assistance."
- Notify admin via dashboard alert (new notification type: `operation_gap`)
- Suggest buyer describe the operation in detail for manual vendor search

### 4.2 Admin Gap Dashboard
- New section in Admin Dashboard showing operations with no vendor coverage
- Helps admin identify capability gaps in vendor network
- Actionable: "Invite vendors with [machine type]" button

---

## Files to Modify

### Backend
- `/app/backend/server.py` — Update `analyze_rfq_drawings()` prompt, add `match_operations_to_vendors()`, add combined RFQ endpoints
- New collection: `operation_machine_map` (seeded on startup)
- New collection: `combined_rfqs`

### Frontend  
- `/app/frontend/src/pages/CreateRFQ.jsx` — Update Step 4 with multi-view tabs
- New component: `/app/frontend/src/components/OperationsMatrix.jsx`
- New component: `/app/frontend/src/components/VendorCombinations.jsx`
- New component: `/app/frontend/src/components/ProductionTimeline.jsx`
- `/app/frontend/src/pages/RFQDetail.jsx` — Show operations breakdown + vendor assignments

---

## Dependencies
- Existing: GPT-5.2 Vision (Emergent LLM Key), MongoDB, vendor machines collection
- No new 3rd party integrations required

---

## Notes
- Vendor machine registration already exists with machine type, make/model, max dimensions, tolerance, availability
- Existing `evaluate_vendor_match()` will be enhanced, not replaced
- Backward compatible — RFQs without operations array continue to use current matching
