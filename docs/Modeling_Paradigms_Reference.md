# Modeling Paradigms & Module Breakdown

This document provides a detailed breakdown of directories `01` through `10`. It explains the core CAD paradigms used, the libraries leveraged, and the purpose of each module in the repository before the introduction of the unified `11_Advanced_Automated_Pipeline`.

---

## 01. CadQuery
**Core Paradigm:** Parametric B-Rep (Boundary Representation)
**Description:** `CadQuery` is a foundational, script-based parametric modeling tool built on the OpenCASCADE kernel. It uses a "fluent" API where method calls are chained together sequentially.
*   **How it Works:** Geometry is constructed by selecting a face (e.g., `>Z`), moving the workplane, drawing a 2D sketch, and extruding it.
*   **Use Case:** Excellent for programmatic generation of mechanical parts, though complex scripts can become difficult to debug due to the hidden internal state of the chain.

---

## 02. Build123d
**Core Paradigm:** Context-Managed Parametric B-Rep *(Highly Recommended)*
**Description:** The modern successor to CadQuery. Instead of fluent chaining, it uses Python Context Managers (`with` blocks) to explicitly define the hierarchy of assemblies, parts, and sketches.
*   **How it Works:** You define a `with BuildPart()` block, and any sketches or extrusions executed inside that block implicitly apply to that part.
*   **Use Case:** The absolute best choice for AI-generated CAD and human-readable mechanical engineering scripts. It is the core geometry engine used in our flagship `v11` pipeline.

---

## 03. SolidPython
**Core Paradigm:** Constructive Solid Geometry (CSG)
**Description:** A Python wrapper for OpenSCAD. Instead of learning the domain-specific `.scad` language, developers write pure Python.
*   **How it Works:** Generates 3D space by adding or subtracting perfect mathematical primitives (Spheres, Cubes). It is extremely robust for boolean operations but lacks advanced B-Rep features like complex edge filleting.
*   **Use Case:** Fast generation of simple geometric shapes or parsing legacy OpenSCAD logic.

---

## 04. Blender (bpy)
**Core Paradigm:** Organic Polygon Meshes
**Description:** Automates Blender using its internal `bpy` python library. 
*   **How it Works:** It executes headless or GUI-based commands to manipulate vertices, edges, and faces of polygon meshes. 
*   **Use Case:** Ideal for organic character modeling, CGI VFX, or generating 3D printable `.stl` files that do not require exact CNC engineering tolerances.

---

## 05. Trimesh
**Core Paradigm:** Topology Analysis & Mesh Healing
**Description:** A pure Python library designed to read, analyze, and manipulate `.stl` and `.obj` mesh files.
*   **How it Works:** It loads the thousands of triangles that make up a mesh and performs scientific evaluations: calculating volume, finding the center of mass, or checking if the mesh is "watertight".
*   **Use Case:** Used extensively in the pipeline to heal degenerate faces and fix broken normals after complex Boolean cuts.

---

## 06. Engineering Models
**Core Paradigm:** Applied B-Rep CAD
**Description:** A directory containing fully functional, real-world mechanical parts (e.g., Pillow Blocks, Flange Shaft Couplings, Gears).
*   **How it Works:** These are complete `build123d` scripts that prove the system can generate actual hardware rather than just theoretical primitive cubes.
*   **Use Case:** Reference architectures for writing new CAD plugins.

---

## 07. Signed Distance Fields
**Core Paradigm:** Volumetric Mathematical Surfaces
**Description:** Generates complex 3D structures purely from distance-evaluating mathematical equations (SDFs), which are then converted to physical meshes using the Marching Cubes algorithm.
*   **How it Works:** Evaluates equations (like the Gyroid lattice) at every point in a 3D grid. If the value is negative, it is inside the object; if positive, it is outside.
*   **Use Case:** Generating extreme metamaterials, lightweight internal infills, or structures that are impossible to model manually.

---

## 08. File Conversion
**Core Paradigm:** Secure Interoperability Automation
**Description:** Cross-format conversion scripts that safely translate between CAD and Mesh formats.
*   **How it Works:** Uses OpenCASCADE to convert `STEP` -> `STL` and `Trimesh` for `STL` -> `OBJ`.
*   **Use Case:** Automating the handover from engineering teams (STEP) to 3D printing/manufacturing teams (STL/3MF).

---

## 09. Import and Modify
**Core Paradigm:** AI-Driven Boolean Editing
**Description:** Demonstrates how to take an external, static CAD file and programmatically modify it.
*   **How it Works:** Imports a raw `.step` file from the web, uses bounding boxes or topological queries to find specific faces, and performs Boolean subtractions (like drilling holes or slicing the model in half).
*   **Use Case:** Autonomous AI modification of downloaded vendor parts (e.g., automatically adding a mounting bracket to a downloaded motor CAD).

---

## 10. Fusion360 Automations
**Core Paradigm:** Headless UI API Execution
**Description:** Directly manipulates Autodesk Fusion 360 using Anthropic's Model Context Protocol (MCP).
*   **How it Works:** Bypasses the Fusion 360 graphical interface by injecting raw Python `adsk.core` scripts over a local websocket. 
*   **Use Case:** Native CAD collision detection, taking automated isometric screenshots, and exporting native `.f3d` archive files without a human clicking any buttons.
