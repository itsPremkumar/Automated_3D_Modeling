# Autodesk Fusion 360 API Capabilities (Automated)

The Autodesk Fusion 360 Python API (`adsk.core`, `adsk.fusion`, `adsk.cam`) exposes massive portions of the native CAD software's functionality to scripts. When combined with an AI agent sending payloads via a local Model Context Protocol (MCP) server, we achieve "Zero-Touch UI Automation".

Below is an outline of what the API is capable of, and what the limits are.

## 1. Highly Mature Capabilities (Perfect for Automation)

### Parametric B-Rep Modeling (`adsk.fusion`)
* **Capability:** You can programmatically create Sketches, Extrusions, Revolve features, Sweeps, Lofts, Fillets, and Chamfers. 
* **AI Use Case:** You can prompt an AI to "write a Fusion 360 script to generate a 50x50mm parametric box with 5mm rounded corners", and send that payload via MCP to be drawn natively.

### Bulk Exporting & Translation (`adsk.core`)
* **Capability:** The `ExportManager` can autonomously take any active design and translate it into `.step`, `.iges`, `.stl`, `.dxf`, `.f3d`, and `.obj` formats.
* **AI Use Case:** You can write a single script that loops through 100 Fusion 360 files in a folder and exports them all to `.step` overnight without human intervention.

### User Parameter Modification
* **Capability:** You can access the `design.userParameters` dictionary to change mathematical variables (e.g., `gear_teeth = 40`).
* **AI Use Case:** Building a web interface where a customer enters custom dimensions, and a background AI script updates the Fusion 360 model and exports an STL for printing automatically.

## 2. Moderately Mature Capabilities (Partial Automation)

### Computer Aided Manufacturing (CAM) (`adsk.cam`)
* **Capability:** You can write scripts to create Setups, generate basic 2D milling toolpaths (Contour, Pocket), and post-process them into G-Code using `.cps` post-processors.
* **Limitations:** Advanced 5-axis operations, tool library management, and complex fixture setups are difficult to script completely "headless". Often, it requires the user to set up a manual CAM Template in the GUI first, which the script then applies and computes.

### Render Workspace
* **Capability:** You can programmatically assign physical materials (e.g., Aluminum, Wood) and trigger local or cloud renders.
* **Limitations:** Fine-tuning lighting environments, HDRI maps, and camera depth-of-field programmatically is highly complex and usually requires manual tweaking.

## 3. Limited or Unsupported Capabilities

### Finite Element Analysis / Simulation (FEA)
* **Capability:** Very limited. The API does not currently support full programmatic creation of Static Stress or Thermal simulation studies.
* **Workaround:** You can programmatically generate the geometry, but a human must click "Solve" in the Simulation workspace.

### Generative Design
* **Capability:** The Generative Design solver is cloud-based and heavily locked behind Autodesk's UI tokens. You cannot script a full generative design study via the local Python API.
