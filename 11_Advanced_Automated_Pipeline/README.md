# Universal AI CAD Robotics Pipeline
**Version:** 1.0 (Architecture v011)
**Core Technologies:** Python, Build123d, Trimesh, Fusion 360 MCP, URDF

---

## 1. Executive Summary
This project is an Enterprise-grade, Universal Modular CAD Pipeline. It transitions hardware engineering from manual CAD modeling into an **autonomous, code-driven, self-optimizing factory**.

The system is capable of mathematically generating complex 3D geometry (or importing external `.step` files), validating structural integrity, performing mesh repair, detecting physical assembly collisions, generating simulated robot physics (URDF), and utilizing AI heuristics to autonomously iterate and improve designs without human intervention.

---

## 2. System Architecture

The pipeline is entirely decoupled, separating the "Geometry" from the "Engineering Validation Engine".

*   **AI Orchestrator** -> Injects Config -> **Pipeline Engine**
*   **CAD Plugins** -> Geometry -> **Pipeline Engine**
*   **External .step Files** -> Boolean Edits -> **CAD Plugins**

The Pipeline Engine performs:
1.  **Validation & Repair:** Topology checks via Trimesh Healer.
2.  **Fusion 360 MCP:** Collision Detection, Exploded View Renders, Native F3D Export.
3.  **Outputs:** Manifests, BOMs, and Dynamic URDF XMLs.

### 2.1 The CAD Plugins (`src/plugins/`)
The system accepts any mathematical geometry logic as an isolated Python plugin. Plugins utilize `build123d` to procedurally generate components ranging from simple brackets to full 6-DOF robotic arms.
*   **Interface:** Every plugin must export a `build(config)` function returning the 3D assembly and a name identifier.
*   **External Integration:** Plugins can securely import external `.step` files (e.g., from GrabCAD) and perform programmatic Boolean modifications (cutting holes, hollowing out mass) before returning them to the pipeline.

### 2.2 Configuration Files (`config.json`)
A unified JSON schema governs the entire project. It contains:
*   `cad_parameters`: Dimensions, radii, lengths.
*   `manufacturing_rules`: Limits for structural safety (e.g., max stress MPa) and material densities.
*   `bom`: The Bill of Materials list.
*   `urdf_kinematics`: Defines exact parent/child joints, limits, and axis transformations for multi-link robots.

---

## 3. The Autonomous AI Orchestrator
The core differentiator of this project is the `ai_orchestrator.py` engine.
Rather than functioning as a static script, the Orchestrator acts as an AI Mechanical Engineer.

1.  **Goal Setting:** The orchestrator establishes a high-level target (e.g., "Maximize robotic arm length while maintaining structural safety").
2.  **Execution:** It triggers the Universal Pipeline with a specific plugin.
3.  **Feedback Loop:** The pipeline computes a Bending Stress Proxy based on torque, mass, and section modulus, outputting a `fitness.json` report.
4.  **Self-Correction:** If the physical limits are exceeded, the Orchestrator algorithmically modifies the parameters (e.g., reinforcing wall thickness) and loops the entire pipeline until the geometry safely passes manufacturing constraints.

---

## 4. Pipeline Engine Capabilities
When the Engine (`src/master_pipeline.py`) receives a generated or modified assembly, it automatically executes the following industrial workflows:

### 4.1 Automated Validation & Healing
Using `trimesh`, the pipeline performs watertight validation. If a plugin generates corrupt geometry or degenerate faces (common in complex Boolean operations), the pipeline automatically executes `fix_normals()`, `remove_degenerate_faces()`, and `fill_holes()` to guarantee printability.

### 4.2 Fusion 360 MCP Integration
The pipeline communicates directly with a local Autodesk Fusion 360 instance via a Model Context Protocol (MCP) server.
*   **Collision Testing:** It mathematically analyzes all intersecting Brep bodies in an assembly (`analyzeInterference`). If robot linkages overlap physically, the pipeline halts and reports a critical structural failure.
*   **Exploded Views:** It calculates the bounding box vectors of the assembly and visually blasts the components outward radially from the origin, taking native high-resolution Isometric screenshots.

### 4.3 Robotics Simulation (URDF)
By parsing the `urdf_kinematics` JSON array, the pipeline autonomously builds a mathematically exact Universal Robotic Description Format (`.urdf`) XML file. This maps all physical links, revolute joints, and kinematic limits, allowing the immediate import of the generated CAD directly into ROS (Robot Operating System) or NVIDIA Isaac Sim.

### 4.4 Enterprise Artifacts
For every iteration, the pipeline produces a cryptographically hashed manifest and a unified folder containing:
*   `assembly.step` (Universal B-Rep)
*   `assembly.3mf` & `.stl` (Modern Slicer Meshes)
*   `assembly.f3d` (Native Fusion 360 Archive)
*   `BOM.csv` (Supply Chain Shopping List)
*   `fitness.json` (Stress/Mass Simulation Scorecard)

---

## 5. Usage

To execute the pipeline manually with a specific plugin and configuration:

```bash
uv run --with build123d --with trimesh --python 3.12 src/master_pipeline.py --plugin src/plugins/6dof_arm.py --config config_6dof.json
```

To execute the self-improving AI Optimization loop:

```bash
uv run --python 3.12 src/ai_orchestrator.py
```
