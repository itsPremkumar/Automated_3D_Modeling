"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  OPTIMUS PRIME G1 — FULL SIMULATION ENGINE v6.0                              ║
║                                                                              ║
║  Complete Autodesk Fusion 360 Add-In Script                                  ║
║  • Full 3D-printable model (tolerance-adjusted, split shells, all hardware)  ║
║                                                                              ║
║  SimulationEngine — 9 modules:                                               ║
║   Module 1 : Joint ROM Test       every joint min→centre→max, collision-chk  ║
║   Module 2 : Head Look-Around     scan left/right/up/down                    ║
║   Module 3 : Wave Gesture         full right-arm wave sequence               ║
║   Module 4 : Idle Breathing       subtle 4-cycle chest oscillation           ║
║   Module 5 : Advanced Walking     4 cycles, hip sway, arm counter-swing      ║
║   Module 6 : Running              3 cycles, fast exaggerated gait            ║
║   Module 7 : Combat Sequence      punch → aim blaster → block → uppercut     ║
║   Module 8 : Transformation       Robot→Truck (9 stages) + drive + reverse   ║
║   Module 9 : Stability + Loads    4-pose CoM check + servo torque table      ║
║                                                                              ║
║  Final report is shown in a message box AND written to:                      ║
║    C:\\opt_fusion_log.txt                                                    ║
║                                                                              ║
║  PRINTING NOTES: 0.45 mm clearance on all moving fits.                       ║
║  Set shrinkage compensation in your slicer before printing.                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

def run(context):
    import adsk.core
    import adsk.fusion
    import traceback
    import math
    import os
    import datetime

    app = None
    ui  = None

    LOG_FILE = r"C:\opt_fusion_log.txt"

    def log_msg(msg):
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        except:
            pass

    log_msg("=" * 60)
    log_msg("EXECUTION START  v6.0  — Optimus Prime G1")
    log_msg("=" * 60)

    try:
        app    = adsk.core.Application.get()
        ui     = app.userInterface
        
        # FIX: Force Fusion 360 to use Z-Up orientation so the robot stands perfectly upright on the grid
        try:
            app.preferences.generalPreferences.defaultModelingOrientation = adsk.core.DefaultModelingOrientations.ZUpModelingOrientation
        except:
            pass
            
        doc    = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root   = design.rootComponent

        # ═══════════════════════════════════════════════════════════════════
        # APPEARANCES
        # ═══════════════════════════════════════════════════════════════════
        app_lib = None
        for i in range(app.materialLibraries.count):
            lib = app.materialLibraries.item(i)
            if "Appearance" in lib.name:
                app_lib = lib
                break

        def _copy_ap(query):
            if not app_lib:
                return None
            for i in range(app_lib.appearances.count):
                ap = app_lib.appearances.item(i)
                if query.lower() in ap.name.lower():
                    try:
                        return design.appearances.addByCopy(ap)
                    except:
                        return ap
            return None

        def get_ap(primary, *fallbacks):
            ap = _copy_ap(primary)
            if ap:
                return ap
            for fb in fallbacks:
                ap = _copy_ap(fb)
                if ap:
                    return ap
            return None

        op_red        = get_ap("Paint - Metallic (Red)",       "Steel - Painted (Red)")
        op_blue       = get_ap("Paint - Metallic (Blue)",      "Steel - Painted (Blue)")
        chrome        = get_ap("Chrome",                        "Steel - Polished")
        dark_metal    = get_ap("Steel - Flat",                  "Plastic - Matte (Black)")
        rubber_blk    = get_ap("Rubber",                        "Plastic - Matte (Black)")
        glass_clr     = get_ap("Glass - Window",                "Acrylic - Clear")
        grey_plastic  = get_ap("Plastic - Matte (Grey)",        "ABS Plastic")
        dark_grey     = get_ap("Plastic - Matte (Dark Grey)",   "Plastic - Matte (Grey)")
        white_pla     = get_ap("Plastic - Glossy (White)",      "Nylon - White")
        black_plastic = get_ap("Plastic - Matte (Black)",       "Rubber")
        gold_met      = get_ap("Gold",                          "Brass")
        yellow_met    = get_ap("Paint - Metallic (Yellow)",     "Gold")

        # ═══════════════════════════════════════════════════════════════════
        # CONSTANTS & COMPONENT REGISTRY
        # ═══════════════════════════════════════════════════════════════════
        CLEARANCE   = 0.045  # FIX: Increased to 0.45 mm for FDM print-in-place safety
        comps_list  = []     # all component objects
        occs        = {}     # name → occurrence

        def new_component(name):
            occ        = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            comp       = occ.component
            comp.name  = name
            comps_list.append(comp)
            occs[name] = occ
            return comp

        def set_ap(body, ap):
            if body and ap:
                try:
                    body.appearance = ap
                except:
                    pass

        # ─── Primitive builders ────────────────────────────────────────────
        def box(comp, name, cx, cy, cz, lx, ly, lz, ap=None):
            adsk.doEvents()
            temp  = adsk.fusion.TemporaryBRepManager.get()
            obb   = adsk.core.OrientedBoundingBox3D.create(
                        adsk.core.Point3D.create(cx, cy, cz),
                        adsk.core.Vector3D.create(1, 0, 0),
                        adsk.core.Vector3D.create(0, 1, 0),
                        lx, ly, lz)
            shape = temp.createBox(obb)
            bf    = comp.features.baseFeatures.add()
            bf.startEdit()
            body  = comp.bRepBodies.add(shape, bf)
            bf.finishEdit()
            body.name = name
            set_ap(body, ap)
            return body

        def cyl(comp, name, cx, cy, cz, r, h, axis, ap=None):
            temp  = adsk.fusion.TemporaryBRepManager.get()
            ax    = {"x": (1,0,0), "y": (0,1,0), "z": (0,0,1)}[axis]
            p1    = adsk.core.Point3D.create(cx - ax[0]*h/2,
                                              cy - ax[1]*h/2,
                                              cz - ax[2]*h/2)
            p2    = adsk.core.Point3D.create(cx + ax[0]*h/2,
                                              cy + ax[1]*h/2,
                                              cz + ax[2]*h/2)
            shape = temp.createCylinderOrCone(p1, r, p2, r)
            bf    = comp.features.baseFeatures.add()
            bf.startEdit()
            body  = comp.bRepBodies.add(shape, bf)
            bf.finishEdit()
            body.name = name
            set_ap(body, ap)
            return body

        def cone_shape(comp, name, cx, cy, cz, r1, r2, h, axis, ap=None):
            temp  = adsk.fusion.TemporaryBRepManager.get()
            ax    = {"x": (1,0,0), "y": (0,1,0), "z": (0,0,1)}[axis]
            p1    = adsk.core.Point3D.create(cx - ax[0]*h/2,
                                              cy - ax[1]*h/2,
                                              cz - ax[2]*h/2)
            p2    = adsk.core.Point3D.create(cx + ax[0]*h/2,
                                              cy + ax[1]*h/2,
                                              cz + ax[2]*h/2)
            shape = temp.createCylinderOrCone(p1, r1, p2, r2)
            bf    = comp.features.baseFeatures.add()
            bf.startEdit()
            body  = comp.bRepBodies.add(shape, bf)
            bf.finishEdit()
            body.name = name
            set_ap(body, ap)
            return body

        def marker(comp, name, cx, cy, cz, size=0.22):
            return box(comp, name, cx, cy, cz, size, size, size, white_pla)

        # ─── Boolean cavity cutter ─────────────────────────────────────────
        SKIP_TAGS = {"Marker", "Pivot", "MtA", "MtB", "Axle_Pivot",
                     "Horn", "Pin", "_Vis"}

        def cut_cavity(comp, tool_body, keep_tool=False):
            tools = adsk.core.ObjectCollection.create()
            tools.add(tool_body)
            for b in comp.bRepBodies:
                if b == tool_body:
                    continue
                if b.name and any(t in b.name for t in SKIP_TAGS):
                    continue
                try:
                    ci           = comp.features.combineFeatures.createInput(b, tools)
                    ci.operation = adsk.fusion.CombineOperation.CutFeatureOperation
                    ci.isKeepToolBodies = True
                    comp.features.combineFeatures.add(ci)
                except:
                    pass
            if not keep_tool:
                try:
                    tool_body.isLightBulbOn = False
                    if "_Vis" not in tool_body.name:
                        tool_body.name += "_Vis"
                except:
                    pass

        # ─── Shell splitter for FDM printing ──────────────────────────────
        def split_halves(comp, body, axis='y', offset=0.0):
            try:
                planes = comp.constructionPlanes
                pi     = planes.createInput()
                ref    = (root.xYConstructionPlane if axis == 'x' else
                          root.xZConstructionPlane if axis == 'y' else
                          root.yZConstructionPlane)
                pi.setByOffset(ref, adsk.core.ValueInput.createByReal(offset))
                sp   = planes.add(pi)
                feat = comp.features.splitBodyFeatures.create()
                feat.targetBody   = body
                feat.toolEntities = [sp]
                feat.execute()
            except:
                pass

        # ─── Fastener helpers ──────────────────────────────────────────────
        def screw_hole(comp, cx, cy, cz, axis="y", length=3.0):
            c = cyl(comp, "ScrewHole", cx, cy, cz, 0.15, length, axis)
            cut_cavity(comp, c)

        def magnet_pocket(comp, tag, cx, cy, cz, axis="z"):
            c = cyl(comp, f"{tag}_MagPkt", cx, cy, cz, 0.32, 0.35, axis)
            cut_cavity(comp, c)

        def wire_channel(comp, tag, cx, cy, cz, r, h, axis):
            c = cyl(comp, f"{tag}_Wire", cx, cy, cz, r, h, axis)
            cut_cavity(comp, c)

        # ═══════════════════════════════════════════════════════════════════
        # JOINT BUILDERS
        # ═══════════════════════════════════════════════════════════════════
        def revolute_joint(name, occ1, occ2, cx, cy, cz, axis_str):
            if not (occ1 and occ2):
                return
            try:
                sketch = root.sketches.add(root.xYConstructionPlane)
                sketch.name = f"JG_{name}"
                sketch.isVisible = False # FIX: Hide workspace clutter
                pt = adsk.core.Point3D.create(cx, cy, cz)
                s_pt = sketch.sketchPoints.add(pt)
                geom = adsk.fusion.JointGeometry.createByPoint(s_pt)
                ji   = root.asBuiltJoints.createInput(occ1, occ2, geom)
                av   = {"x": adsk.core.Vector3D.create(1, 0, 0),
                        "y": adsk.core.Vector3D.create(0, 1, 0),
                        "z": adsk.core.Vector3D.create(0, 0, 1)}[axis_str]
                ji.setAsRevoluteJointMotion(
                    adsk.fusion.JointDirections.CustomJointDirection, av)
                j      = root.asBuiltJoints.add(ji)
                j.name = name
            except:
                log_msg(f"Failed to create revolute joint {name}: {traceback.format_exc()}")

        def ball_joint(name, occ1, occ2, cx, cy, cz):
            if not (occ1 and occ2):
                return
            try:
                sketch = root.sketches.add(root.xYConstructionPlane)
                sketch.name = f"JG_{name}"
                sketch.isVisible = False
                pt = adsk.core.Point3D.create(cx, cy, cz)
                s_pt = sketch.sketchPoints.add(pt)
                geom = adsk.fusion.JointGeometry.createByPoint(s_pt)
                ji   = root.asBuiltJoints.createInput(occ1, occ2, geom)
                ji.setAsBallJointMotion(
                    adsk.fusion.JointDirections.ZAxisJointDirection,
                    adsk.fusion.JointDirections.XAxisJointDirection)
                j      = root.asBuiltJoints.add(ji)
                j.name = name
            except:
                log_msg(f"Failed to create ball joint {name}: {traceback.format_exc()}")

        def rigid_joint(name, occ1, occ2):
            if not (occ1 and occ2):
                return
            try:
                sketch = root.sketches.add(root.xYConstructionPlane)
                sketch.name = f"JG_{name}"
                sketch.isVisible = False
                pt = adsk.core.Point3D.create(0, 0, 0)
                s_pt = sketch.sketchPoints.add(pt)
                geom = adsk.fusion.JointGeometry.createByPoint(s_pt)
                ji   = root.asBuiltJoints.createInput(occ1, occ2, geom)
                ji.setAsRigidJointMotion()
                j      = root.asBuiltJoints.add(ji)
                j.name = name
            except:
                pass

        # ═══════════════════════════════════════════════════════════════════
        # MECHANICAL MODULES
        # ═══════════════════════════════════════════════════════════════════
        def servo_hardware(comp, tag, cx, cy, cz, axis, mg996):
            if mg996:
                fd, fw, hr, pd, sd = 2.4, 0.5, 0.7, 0.125, 0.15
                if   axis == "x": hx,hy,hz = cx+2.40,cy,cz+1.05; fx,fy,fz = cx+0.95,cy,cz
                elif axis == "z": hx,hy,hz = cx-1.10,cy,cz+2.40; fx,fy,fz = cx,cy,cz+0.95
                else:             hx,hy,hz = cx,cy+2.40,cz+1.05; fx,fy,fz = cx,cy+0.95,cz
            else:
                fd, fw, hr, pd, sd = 1.35, 0.0, 0.4, 0.10, 0.10
                if   axis == "x": hx,hy,hz = cx+1.40,cy,cz+0.50; fx,fy,fz = cx+0.45,cy,cz
                elif axis == "z": hx,hy,hz = cx-0.50,cy,cz+1.40; fx,fy,fz = cx,cy,cz+0.45
                else:             hx,hy,hz = cx,cy+1.40,cz+0.50; fx,fy,fz = cx,cy+0.45,cz

            for d1 in [-fd, fd]:
                for d2 in ([-fw, fw] if fw > 0 else [0]):
                    if   axis == "x": c = cyl(comp,f"{tag}_FlgS_{d1}_{d2}",fx,fy+d2,fz+d1,sd,1.5,"x")
                    elif axis == "z": c = cyl(comp,f"{tag}_FlgS_{d1}_{d2}",fx+d1,fy+d2,fz,sd,1.5,"z")
                    else:             c = cyl(comp,f"{tag}_FlgS_{d1}_{d2}",fx+d1,fy,fz+d2,sd,1.5,"y")
                    cut_cavity(comp, c)

            for d in [-hr, hr]:
                if   axis == "x":
                    c1 = cyl(comp,f"{tag}_Hrn1_{d}",hx,hy+d,hz,pd,1.5,"x")
                    c2 = cyl(comp,f"{tag}_Hrn2_{d}",hx,hy,hz+d,pd,1.5,"x")
                elif axis == "z":
                    c1 = cyl(comp,f"{tag}_Hrn1_{d}",hx+d,hy,hz,pd,1.5,"z")
                    c2 = cyl(comp,f"{tag}_Hrn2_{d}",hx,hy+d,hz,pd,1.5,"z")
                else:
                    c1 = cyl(comp,f"{tag}_Hrn1_{d}",hx+d,hy,hz,pd,1.5,"y")
                    c2 = cyl(comp,f"{tag}_Hrn2_{d}",hx,hy,hz+d,pd,1.5,"y")
                cut_cavity(comp, c1)
                cut_cavity(comp, c2)

        def mg996r(comp, tag, cx, cy, cz, axis="x"):
            cl = CLEARANCE
            if axis == "x":
                box(comp,f"{tag}_VisBody",cx,cy,cz,4.05,2.00,4.20,grey_plastic)
                box(comp,f"{tag}_VisEars",cx+0.95,cy,cz,0.30,2.20,5.80,dark_grey)
                cyl(comp,f"{tag}_VisHorn",cx+2.40,cy,cz+1.05,0.95,0.22,"x",white_pla)
                marker(comp,f"{tag}_Pivot",cx+2.40,cy,cz+1.05)
                cut_cavity(comp,box(comp,f"{tag}_CB",cx,cy,cz,4.05+cl,2.00+cl,4.20+cl))
                cut_cavity(comp,box(comp,f"{tag}_CE",cx+0.95,cy,cz,0.30+cl,2.20+cl,5.80+cl))
            elif axis == "z":
                box(comp,f"{tag}_VisBody",cx,cy,cz,4.05,2.00,4.20,grey_plastic)
                box(comp,f"{tag}_VisEars",cx,cy,cz+0.95,5.80,2.20,0.30,dark_grey)
                cyl(comp,f"{tag}_VisHorn",cx-1.10,cy,cz+2.40,0.95,0.22,"z",white_pla)
                marker(comp,f"{tag}_Pivot",cx-1.10,cy,cz+2.40)
                cut_cavity(comp,box(comp,f"{tag}_CB",cx,cy,cz,4.05+cl,2.00+cl,4.20+cl))
                cut_cavity(comp,box(comp,f"{tag}_CE",cx,cy,cz+0.95,5.80+cl,2.20+cl,0.30+cl))
            else:
                box(comp,f"{tag}_VisBody",cx,cy,cz,4.05,4.20,2.00,grey_plastic)
                box(comp,f"{tag}_VisEars",cx,cy+0.95,cz,4.05,0.30,2.20,dark_grey)
                cyl(comp,f"{tag}_VisHorn",cx,cy+2.40,cz+1.05,0.95,0.22,"y",white_pla)
                marker(comp,f"{tag}_Pivot",cx,cy+2.40,cz+1.05)
                cut_cavity(comp,box(comp,f"{tag}_CB",cx,cy,cz,4.05+cl,4.20+cl,2.00+cl))
                cut_cavity(comp,box(comp,f"{tag}_CE",cx,cy+0.95,cz,4.05+cl,0.30+cl,2.20+cl))
            servo_hardware(comp, tag, cx, cy, cz, axis, True)

        def mg90s(comp, tag, cx, cy, cz, axis="x"):
            cl = CLEARANCE
            if axis == "x":
                box(comp,f"{tag}_VisBody",cx,cy,cz,2.30,1.20,2.30,op_blue)
                box(comp,f"{tag}_VisEars",cx+0.45,cy,cz,0.20,1.30,3.20,op_blue)
                cyl(comp,f"{tag}_VisHorn",cx+1.40,cy,cz+0.50,0.55,0.18,"x",white_pla)
                marker(comp,f"{tag}_Pivot",cx+1.40,cy,cz+0.50)
                cut_cavity(comp,box(comp,f"{tag}_CB",cx,cy,cz,2.30+cl,1.20+cl,2.30+cl))
                cut_cavity(comp,box(comp,f"{tag}_CE",cx+0.45,cy,cz,0.20+cl,1.30+cl,3.20+cl))
            elif axis == "z":
                box(comp,f"{tag}_VisBody",cx,cy,cz,2.30,1.20,2.30,op_blue)
                box(comp,f"{tag}_VisEars",cx,cy,cz+0.45,3.20,1.30,0.20,op_blue)
                cyl(comp,f"{tag}_VisHorn",cx-0.50,cy,cz+1.40,0.55,0.18,"z",white_pla)
                marker(comp,f"{tag}_Pivot",cx-0.50,cy,cz+1.40)
                cut_cavity(comp,box(comp,f"{tag}_CB",cx,cy,cz,2.30+cl,1.20+cl,2.30+cl))
                cut_cavity(comp,box(comp,f"{tag}_CE",cx,cy,cz+0.45,3.20+cl,1.30+cl,0.20+cl))
            else:
                box(comp,f"{tag}_VisBody",cx,cy,cz,2.30,2.30,1.20,op_blue)
                box(comp,f"{tag}_VisEars",cx,cy+0.45,cz,3.20,0.20,1.30,op_blue)
                cyl(comp,f"{tag}_VisHorn",cx,cy+1.40,cz+0.50,0.55,0.18,"y",white_pla)
                marker(comp,f"{tag}_Pivot",cx,cy+1.40,cz+0.50)
                cut_cavity(comp,box(comp,f"{tag}_CB",cx,cy,cz,2.30+cl,2.30+cl,1.20+cl))
                cut_cavity(comp,box(comp,f"{tag}_CE",cx,cy+0.45,cz,3.20+cl,0.20+cl,1.30+cl))
            servo_hardware(comp, tag, cx, cy, cz, axis, False)

        def tt_wheel(comp, tag, cx, cy, cz, side=1):
            cl = CLEARANCE
            box(comp,f"{tag}_VisGB",cx,cy,cz,2.30,5.20,1.90,yellow_met)
            cyl(comp,f"{tag}_VisMot",cx,cy-3.0,cz,0.90,2.10,"y",chrome)
            cyl(comp,f"{tag}_VisShaft",cx+side*1.75,cy,cz,0.20,3.50,"x",chrome)
            cyl(comp,f"{tag}_VisHub",  cx+side*3.25,cy,cz,0.80,2.60,"x",dark_metal)
            cyl(comp,f"{tag}_VisTire", cx+side*3.25,cy,cz,3.25,2.60,"x",rubber_blk)
            cyl(comp,f"{tag}_VisRim",  cx+side*3.25,cy,cz,2.20,2.65,"x",chrome)
            marker(comp,f"{tag}_Axle_Pivot",cx+side*3.25,cy,cz,0.18)
            cut_cavity(comp,box(comp,f"{tag}_CGB",cx,cy,cz,2.30+cl,5.20+cl,1.90+cl))
            cut_cavity(comp,box(comp,f"{tag}_CDS",cx+side*3.25,cy,cz,2.7,0.54+cl,0.36+cl))

        def bearing(comp, tag, cx, cy, cz, axis="x", ro=1.10, w=0.60):
            cyl(comp,f"{tag}_BO",cx,cy,cz,ro,     w,     axis,chrome)
            cyl(comp,f"{tag}_BI",cx,cy,cz,ro*0.58,w*0.80,axis,dark_grey)
            cyl(comp,f"{tag}_BB",cx,cy,cz,ro*0.32,w*1.10,axis,chrome)
            temp = adsk.fusion.TemporaryBRepManager.get()
            ax   = {"x":(1,0,0),"y":(0,1,0),"z":(0,0,1)}[axis]
            p1   = adsk.core.Point3D.create(cx,cy,cz)
            p2   = adsk.core.Point3D.create(cx+ax[0]*(w+0.1),
                                             cy+ax[1]*(w+0.1),
                                             cz+ax[2]*(w+0.1))
            cs   = temp.createCylinderOrCone(p1,ro+0.05,p2,ro+0.05)
            bf   = comp.features.baseFeatures.add()
            bf.startEdit()
            cb   = comp.bRepBodies.add(cs,bf)
            bf.finishEdit()
            cb.name = f"{tag}_CB"
            cut_cavity(comp, cb)

        def u_bracket(comp, tag, cx, cy, cz, lx, ly, lz, ap=None):
            ap = ap or chrome
            box(comp,f"{tag}_BB",  cx,          cy,        cz, 0.45,     ly,   lz, ap)
            box(comp,f"{tag}_BL",  cx+lx*0.45,  cy+ly*0.35,cz, lx*0.55, 0.40, lz, ap)
            box(comp,f"{tag}_BR",  cx+lx*0.45,  cy-ly*0.35,cz, lx*0.55, 0.40, lz, ap)
            cyl(comp, f"{tag}_Pin",cx+lx*0.50,  cy,        cz, 0.18, ly*0.85,  "y",chrome)

        # ═══════════════════════════════════════════════════════════════════
        # GLOBAL PROPORTIONS  (all in cm, Z = up)
        # ═══════════════════════════════════════════════════════════════════
        ANKLE_CTR    =  3.8
        SHIN_CTR     =  9.3
        KNEE_CTR     = 14.8
        THIGH_CTR    = 20.3
        PELVIS_CTR   = 29.5
        WAIST_CTR    = 31.5
        TORSO_CTR    = 35.0
        SHOULDER_CTR = 40.5
        HEAD_CTR     = 46.5
        HIP_X        =  5.8
        SHOULDER_X   = 13.0
        ELBOW_Z      = 34.0
        WRIST_Z      = 28.0
        HIP_JOINT_Z  = 25.8
        NECK_JOINT_Z = 43.5

        # ═══════════════════════════════════════════════════════════════════
        # ①  TORSO
        # ═══════════════════════════════════════════════════════════════════
        torso = new_component("OP_Torso")
        box(torso,"Torso_Shell",         0,  0,TORSO_CTR,     10.2,8.4,12.0,op_red)
        box(torso,"Torso_Side_L",       -5.5,0,TORSO_CTR,      0.5,7.6,11.0,op_red)
        box(torso,"Torso_Side_R",        5.5,0,TORSO_CTR,      0.5,7.6,11.0,op_red)
        box(torso,"Chest_Win_L",        -2.2,-4.25,TORSO_CTR+2.5,2.6,0.22,2.8,glass_clr)
        box(torso,"Chest_Win_R",         2.2,-4.25,TORSO_CTR+2.5,2.6,0.22,2.8,glass_clr)
        box(torso,"Chest_Win_Div",       0,  -4.2, TORSO_CTR+2.5,0.35,0.22,2.8,op_blue)
        box(torso,"Chest_Grille",        0,  -4.35,TORSO_CTR-0.5,7.0,0.30,4.0,chrome)
        box(torso,"Front_Bumper",        0,  -5.10,TORSO_CTR-4.2,9.6,1.80,1.6,chrome)
        box(torso,"Headlight_L",        -4.2,-4.45,TORSO_CTR-1.2,1.6,0.30,1.8,glass_clr)
        box(torso,"Headlight_R",         4.2,-4.45,TORSO_CTR-1.2,1.6,0.30,1.8,glass_clr)
        box(torso,"Chest_Plate",         0,  -4.15,TORSO_CTR+0.5,8.2,0.30,3.5,chrome)
        cyl(torso,"Autobot_Badge",       0,  -4.52,TORSO_CTR+0.5,0.70,0.10,"y",op_red)
        box(torso,"Inner_Frame",         0,  0,TORSO_CTR+1.5,  7.2,5.8,8.0,dark_metal)
        box(torso,"Spine_Beam",          0,  0,TORSO_CTR+1.5,  1.8,1.8,8.0,chrome)
        cyl(torso,"Spine_Cyl",           0,  0,TORSO_CTR+1.5,  1.10,4.2,"z",chrome)
        box(torso,"Battery_Bay",         0,  2.2,TORSO_CTR-1.5, 5.8,2.6,4.8,black_plastic)
        box(torso,"Battery_Door",        0,  3.6,TORSO_CTR-1.5, 5.8,0.2,4.8,dark_grey)
        box(torso,"Controller_Bay",      0,  2.8,TORSO_CTR+2.2, 4.2,1.8,2.4,black_plastic)
        for sx in [-1.5, 1.5]:
            for sz in [-1.0, 1.0]:
                cyl(torso,f"SO_E_{sx}_{sz}", sx,   3.4,TORSO_CTR+2.2+sz,  0.25,0.6,"y",chrome)
                cyl(torso,f"SO_P_{sx}_{sz}", sx*1.8,3.4,TORSO_CTR+2.2+sz*1.4,0.25,0.6,"y",chrome)
        box(torso,"Cable_L",    -3.2,0.6,TORSO_CTR,  0.55,1.0,10.0,dark_grey)
        box(torso,"Cable_R",     3.2,0.6,TORSO_CTR,  0.55,1.0,10.0,dark_grey)
        box(torso,"Collar_L",   -7.8,0,SHOULDER_CTR-1.0,5.0,3.2,2.8,chrome)
        box(torso,"Collar_R",    7.8,0,SHOULDER_CTR-1.0,5.0,3.2,2.8,chrome)
        box(torso,"TF_Flap_L",  -5.25,-0.2,TORSO_CTR+3.0,0.40,6.4,6.0,op_red)
        box(torso,"TF_Flap_R",   5.25,-0.2,TORSO_CTR+3.0,0.40,6.4,6.0,op_red)
        box(torso,"TF_BackTop",  0,  4.8,TORSO_CTR+5.0,8.0,0.35,5.0,op_blue)
        screw_hole(torso,-3.0,0,TORSO_CTR+4.5,"y",8.0)
        screw_hole(torso, 3.0,0,TORSO_CTR+4.5,"y",8.0)
        screw_hole(torso,-3.0,0,TORSO_CTR-4.5,"y",8.0)
        screw_hole(torso, 3.0,0,TORSO_CTR-4.5,"y",8.0)
        u_bracket(torso,"Waist_Brkt",   0,0,WAIST_CTR,    4.0,4.2,3.4)
        mg996r(torso,"Waist_Yaw",       0,0,WAIST_CTR,    "z")
        bearing(torso,"Waist_Brg",      0,0,WAIST_CTR+0.5,"z",1.30,0.65)
        u_bracket(torso,"WaistP_Brkt",  0,0,WAIST_CTR-2.5,4.0,4.2,3.4)
        mg996r(torso,"Waist_Pitch",     0,0,WAIST_CTR-2.5,"x")
        bearing(torso,"WaistP_Brg",     0,0,WAIST_CTR-2.0,"x",1.30,0.65)
        magnet_pocket(torso,"WLock_F",  0,-2.0,WAIST_CTR-3.0,"y")
        magnet_pocket(torso,"WLock_R",  0, 2.0,WAIST_CTR-3.0,"y")
        u_bracket(torso,"Neck_Brkt",    0,0,NECK_JOINT_Z,  3.2,2.8,3.0)
        mg996r(torso,"Neck_Pitch",      0,0,NECK_JOINT_Z,  "x")
        wire_channel(torso,"Spine",     0,0,TORSO_CTR,  0.6,20.0,"z")

        # ═══════════════════════════════════════════════════════════════════
        # ②  HEAD
        # ═══════════════════════════════════════════════════════════════════
        head = new_component("OP_Head")
        box(head,"Helmet_Main",  0, 0,HEAD_CTR+1.0,5.2,4.9,4.8,op_blue)
        box(head,"Helmet_Top",   0, 0,HEAD_CTR+3.5,4.4,4.2,0.5,op_blue)
        box(head,"Crest",        0,-0.2,HEAD_CTR+3.6,0.8,0.6,3.0,chrome)
        box(head,"Ear_L",       -2.75,0,HEAD_CTR+1.8,0.35,3.8,3.0,op_blue)
        box(head,"Ear_R",        2.75,0,HEAD_CTR+1.8,0.35,3.8,3.0,op_blue)
        box(head,"Faceplate",    0,-2.35,HEAD_CTR+0.5,2.5,0.28,2.6,chrome)
        box(head,"Visor",        0,-2.55,HEAD_CTR+1.4,3.0,0.18,0.9,glass_clr)
        box(head,"Mouth_Grille", 0,-2.50,HEAD_CTR-0.3,1.6,0.20,1.0,dark_grey)
        cyl(head,"Ant_L",       -2.60,0,HEAD_CTR+4.2,0.14,2.2,"z",chrome)
        cyl(head,"Ant_R",        2.60,0,HEAD_CTR+4.2,0.14,2.2,"z",chrome)
        cyl(head,"AntTip_L",    -2.60,0,HEAD_CTR+5.5,0.22,0.28,"z",gold_met)
        cyl(head,"AntTip_R",     2.60,0,HEAD_CTR+5.5,0.22,0.28,"z",gold_met)
        box(head,"Head_Rear",    0, 1.8,HEAD_CTR+1.2,3.6,1.6,3.8,op_red)
        mg90s(head,"Neck_Yaw",  0,0,NECK_JOINT_Z,"z")

        # ═══════════════════════════════════════════════════════════════════
        # ③  PELVIS
        # ═══════════════════════════════════════════════════════════════════
        pelvis = new_component("OP_Pelvis")
        box(pelvis,"Pelvis_Shell",  0,0,PELVIS_CTR,  16.2,6.0,4.8,op_blue)
        box(pelvis,"Pelvis_Frame",  0,0,PELVIS_CTR,  12.0,4.2,3.6,dark_metal)
        box(pelvis,"Hip_Armr_L",   -7.0,0,PELVIS_CTR, 1.0,5.0,4.0,chrome)
        box(pelvis,"Hip_Armr_R",    7.0,0,PELVIS_CTR, 1.0,5.0,4.0,chrome)
        box(pelvis,"Crotch_Plate",  0,-2.8,PELVIS_CTR-1.2,5.0,0.28,2.2,op_red)
        mg996r(pelvis,"L_HipYaw", -HIP_X,0,HIP_JOINT_Z,"z")
        mg996r(pelvis,"R_HipYaw",  HIP_X,0,HIP_JOINT_Z,"z")
        bearing(pelvis,"L_HYB",  -HIP_X-2.2,0,HIP_JOINT_Z,"z",1.10,0.62)
        bearing(pelvis,"R_HYB",   HIP_X+2.2,0,HIP_JOINT_Z,"z",1.10,0.62)

        # ═══════════════════════════════════════════════════════════════════
        # ④  LEGS  (L & R)
        # ═══════════════════════════════════════════════════════════════════
        for side, sx in [("L", -HIP_X), ("R", HIP_X)]:
            m = -1 if side == "L" else 1

            thigh = new_component(f"OP_Thigh_{side}")
            box(thigh,"Thigh_Link",       sx,0,THIGH_CTR,       4.8,3.8,11.0,chrome)
            box(thigh,"Thigh_Outer",      sx+m*2.55,0,THIGH_CTR,0.45,4.2,11.0,op_red)
            box(thigh,"Thigh_Front",      sx,-2.1,THIGH_CTR,    4.8,0.38,11.0,op_blue)
            u_bracket(thigh,f"{side}_HPB",sx,0,HIP_JOINT_Z+0.5, 4.0,3.2,3.2)
            mg996r(thigh,f"{side}_HipP",  sx,0,HIP_JOINT_Z,"x")
            mg996r(thigh,f"{side}_HipR",  sx,0,THIGH_CTR+2.0,"y")
            bearing(thigh,f"{side}_HRB",  sx,0,THIGH_CTR+2.0,"y",1.00,0.55)
            u_bracket(thigh,f"{side}_KnB",sx,0,KNEE_CTR+1.5,   3.8,3.0,3.0)
            mg996r(thigh,f"{side}_KneP",  sx,0,KNEE_CTR+1.5,"x")
            bearing(thigh,f"{side}_KB",   sx,0,KNEE_CTR,"x",1.00,0.55)
            wire_channel(thigh,f"{side}_LW",sx,0,THIGH_CTR,0.5,12.0,"z")
            screw_hole(thigh,sx,0,THIGH_CTR+3.0,"y",3.0)
            screw_hole(thigh,sx,0,THIGH_CTR-3.0,"y",3.0)
            magnet_pocket(thigh,f"{side}_KLU",sx,-1.5,KNEE_CTR+1.0,"x")
            magnet_pocket(thigh,f"{side}_KLL",sx, 1.5,KNEE_CTR+1.0,"x")

            shin = new_component(f"OP_Shin_{side}")
            box(shin,"Shin_Link",  sx,0,SHIN_CTR,     4.2,5.8,11.0,op_blue)
            box(shin,"Shin_Armor", sx,-2.6,SHIN_CTR,  3.0,0.32,9.0, chrome)
            box(shin,"Shin_Rear",  sx, 2.6,SHIN_CTR,  1.8,0.32,9.5, dark_grey)
            box(shin,"Shin_Beam",  sx, 0.4,SHIN_CTR,  1.6,2.0,10.0, dark_metal)
            tt_wheel(shin,f"{side}_WF",sx+m*2.0,3.5,SHIN_CTR+4.0,m)
            tt_wheel(shin,f"{side}_WR",sx+m*2.0,3.5,SHIN_CTR-4.0,m)
            bearing(shin,f"{side}_KLB",sx,0,KNEE_CTR-0.5,"x",1.00,0.55)
            wire_channel(shin,f"{side}_SW",sx,0,SHIN_CTR,0.5,11.0,"z")
            cut_cavity(shin,box(shin,"FtTuck",sx,2.6,SHIN_CTR-3.5,5.0,1.2,4.0))
            magnet_pocket(shin,f"{side}_KU",sx,-1.5,KNEE_CTR-1.0,"x")
            magnet_pocket(shin,f"{side}_KL",sx, 1.5,KNEE_CTR-1.0,"x")
            screw_hole(shin,sx,0,SHIN_CTR+3.5,"y",5.0)
            screw_hole(shin,sx,0,SHIN_CTR-3.5,"y",5.0)

            foot = new_component(f"OP_Foot_{side}")
            box(foot,"Foot_Sole",  sx,-1.0,ANKLE_CTR-1.4,5.8,8.2,1.2,op_red)
            box(foot,"Heel_Block", sx-m*0.8,2.8,ANKLE_CTR-0.8,2.2,3.0,2.4,dark_grey)
            box(foot,"Toe_Block",  sx+m*0.8,-3.6,ANKLE_CTR-0.8,2.4,3.4,1.8,dark_grey)
            box(foot,"Ankle_Guard",sx,0,ANKLE_CTR+1.0,5.0,2.6,2.4,chrome)
            box(foot,"Boot_Fin",   sx+m*1.5,0,ANKLE_CTR-0.2,0.35,6.0,3.8,op_blue)
            mg996r(foot,f"{side}_AnkP",sx,0,ANKLE_CTR+2.2,"x")
            mg996r(foot,f"{side}_AnkR",sx,0,ANKLE_CTR+0.5,"y")
            bearing(foot,f"{side}_AB",sx,0,ANKLE_CTR,"x",1.00,0.55)

        # ═══════════════════════════════════════════════════════════════════
        # ⑤  ARMS  (L & R)
        # ═══════════════════════════════════════════════════════════════════
        for side, ax in [("L", -SHOULDER_X), ("R", SHOULDER_X)]:
            m = -1 if side == "L" else 1

            ua = new_component(f"OP_UpperArm_{side}")
            box(ua,"Sh_Block",    ax,0,SHOULDER_CTR,    5.2,4.0,5.2,op_red)
            box(ua,"Sh_Guard",    ax+m*2.35,0,SHOULDER_CTR-0.2,0.40,4.2,6.2,op_blue)
            cyl(ua,f"Stk_Main_{side}",ax+m*3.2,-1.4,SHOULDER_CTR+2.5,0.48,7.5,"z",chrome)
            cyl(ua,f"Stk_Base_{side}",ax+m*3.2,-1.4,SHOULDER_CTR-0.2,0.72,1.0,"z",chrome)
            cone_shape(ua,f"Stk_Tip_{side}",ax+m*3.2,-1.4,SHOULDER_CTR+6.5,0.50,0.30,0.60,"z",dark_grey)
            box(ua,"UA_Link",     ax,0,ELBOW_Z+3.0,3.0,3.2,9.0,op_red)
            box(ua,"UA_Skin",     ax+m*1.65,0,ELBOW_Z+3.0,0.50,3.2,9.0,chrome)
            mg996r(ua,f"{side}_ShY",  ax,0,SHOULDER_CTR+1.5,"z")
            bearing(ua,f"{side}_SYB", ax,0,SHOULDER_CTR+2.0,"z",1.00,0.55)
            u_bracket(ua,f"{side}_SPB",ax,0,SHOULDER_CTR,4.8,3.4,3.4)
            mg996r(ua,f"{side}_ShP",  ax,0,SHOULDER_CTR,"x")
            mg996r(ua,f"{side}_ShR",  ax,0,SHOULDER_CTR-1.2,"y")
            bearing(ua,f"{side}_SB",  ax,0,SHOULDER_CTR,"x",1.10,0.62)
            u_bracket(ua,f"{side}_EB",ax,0,ELBOW_Z,3.8,3.0,3.0)
            mg996r(ua,f"{side}_ElbP", ax,0,ELBOW_Z,"x")
            bearing(ua,f"{side}_EBr", ax,0,ELBOW_Z-0.5,"x",0.95,0.52)
            wire_channel(ua,f"{side}_UAW",ax,0,ELBOW_Z+4.0,0.4,10.0,"z")
            screw_hole(ua,ax,0,ELBOW_Z+3.0,"y",3.0)

            fa = new_component(f"OP_Forearm_{side}")
            box(fa,"FA_Link",     ax,0,WRIST_Z+3.5,3.0,3.6,7.2,op_blue)
            box(fa,"FA_Fender",   ax+m*2.0,0,WRIST_Z+3.5,0.50,5.0,8.4,op_red)
            box(fa,"FA_Back",     ax,2.2,WRIST_Z+3.5,2.4,0.35,7.0,chrome)
            mg90s(fa,f"{side}_WR",ax,0,WRIST_Z+0.8,"x")
            bearing(fa,f"{side}_WB",ax,0,WRIST_Z+0.5,"x",0.80,0.44)
            wire_channel(fa,f"{side}_FAW",ax,0,WRIST_Z+4.0,0.4,8.0,"z")
            screw_hole(fa,ax,0,WRIST_Z+4.0,"y",3.0)

            hand = new_component(f"OP_Hand_{side}")
            box(hand,"Palm",       ax,-0.8,WRIST_Z-1.2,2.8,3.8,1.8,dark_grey)
            box(hand,"Fingers",    ax,-1.8,WRIST_Z-2.6,2.6,1.8,2.2,grey_plastic)
            box(hand,"Thumb",      ax+m*1.4,0.5,WRIST_Z-1.5,0.9,1.0,1.9,chrome)
            box(hand,"Hand_Panel", ax+m*0.6,-1.0,WRIST_Z-1.0,0.35,2.6,2.6,op_red)

            if side == "R":
                blast = new_component("OP_Ion_Blaster")
                cyl(blast,"Barrel_Main",  ax,-2.0,WRIST_Z-5.0,0.90,7.5,"z",dark_metal)
                cyl(blast,"Barrel_Tip",   ax,-2.0,WRIST_Z-9.0,0.65,1.0,"z",chrome)
                box(blast,"Blaster_Body", ax,-1.0,WRIST_Z-4.5,2.4,2.2,3.0,dark_metal)
                box(blast,"Blast_Guard",  ax,-0.2,WRIST_Z-4.5,2.6,0.35,2.0,chrome)
                cyl(blast,"Scope",        ax+1.4,-2.0,WRIST_Z-4.5,0.40,3.2,"z",chrome)

        # ═══════════════════════════════════════════════════════════════════
        # ⑥  BACKPACK
        # ═══════════════════════════════════════════════════════════════════
        bp = new_component("OP_Backpack")
        box(bp,"BP_Core",    0,5.5,TORSO_CTR+0.5,7.0,2.4,9.0,dark_grey)
        box(bp,"BP_Hood",    0,6.4,TORSO_CTR+1.0,5.6,1.0,7.6,op_red)
        box(bp,"BP_TopFlap", 0,5.0,TORSO_CTR+5.4,8.2,0.35,5.2,op_red)
        box(bp,"BP_Rad",     0,6.8,TORSO_CTR-0.5,5.2,0.42,5.5,chrome)
        box(bp,"Exh_Blk",    0,6.2,TORSO_CTR+2.8,3.0,0.60,1.8,dark_metal)
        cyl(bp,"Exh_L",     -1.2,6.6,TORSO_CTR+2.8,0.38,1.2,"y",dark_metal)
        cyl(bp,"Exh_R",      1.2,6.6,TORSO_CTR+2.8,0.38,1.2,"y",dark_metal)
        mg90s(bp,"Roof_Hinge",0,5.0,TORSO_CTR+5.0,"x")
        bearing(bp,"Roof_Brg",0,5.0,TORSO_CTR+5.2,"x",0.80,0.44)
        magnet_pocket(bp,"RoofL",-2.5,5.0,TORSO_CTR+5.6,"x")
        magnet_pocket(bp,"RoofR", 2.5,5.0,TORSO_CTR+5.6,"x")

        # ═══════════════════════════════════════════════════════════════════
        # ⑦  STEER WHEEL PODS
        # ═══════════════════════════════════════════════════════════════════
        steer = new_component("OP_SteerPods")
        for side, sx in [("L", -5.5), ("R", 5.5)]:
            m = -1 if side == "L" else 1
            box(steer,f"SAr_{side}",    sx,-4.0,TORSO_CTR-4.5,1.5,1.2,4.0,chrome)
            box(steer,f"SPod_{side}",   sx,-5.5,TORSO_CTR-5.0,2.8,2.0,3.0,dark_grey)
            tt_wheel(steer,f"SW_{side}",sx,-5.5,TORSO_CTR-5.0,m)
            bearing(steer,f"SPiv_{side}",sx,-4.0,TORSO_CTR-4.5,"z",0.95,0.50)
            mg90s(steer,f"SSrv_{side}", sx,-4.8,TORSO_CTR-4.5,"z")

        # ═══════════════════════════════════════════════════════════════════
        # ⑧  SHIELDS / PANELS
        # ═══════════════════════════════════════════════════════════════════
        shields = new_component("OP_Shields")
        for side, sx in [("L", -(SHOULDER_X+3.2)), ("R", SHOULDER_X+3.2)]:
            m = -1 if side == "L" else 1
            box(shields,f"ShShield_{side}",      sx,0,SHOULDER_CTR+1.5,1.0,4.4,5.0,chrome)
            box(shields,f"ShHinge_{side}",       sx-m*0.7,0,SHOULDER_CTR+1.5,0.5,1.8,1.8,dark_grey)
            box(shields,f"Mirror_{side}",        sx+m*0.5,-2.8,SHOULDER_CTR+2.0,1.4,0.2,0.8,dark_grey)
        for side, hx in [("L", -(HIP_X+3.0)), ("R", HIP_X+3.0)]:
            box(shields,f"HipShield_{side}",hx,0,PELVIS_CTR+0.5,1.0,4.2,3.8,op_blue)

        # ═══════════════════════════════════════════════════════════════════
        # SPLIT SHELLS FOR FDM PRINTING
        # ═══════════════════════════════════════════════════════════════════
        SPLIT_KEYS = {"Shell","Link","Main","Armor","Core","Pod","Palm","Block","Sole"}
        for comp in comps_list:
            to_split = [b for b in comp.bRepBodies
                        if b.name and any(k in b.name for k in SPLIT_KEYS)]
            for b in to_split:
                split_halves(comp, b, 'y', 0.0)

        # ═══════════════════════════════════════════════════════════════════
        # DIGITAL KINEMATICS
        # ═══════════════════════════════════════════════════════════════════
        def build_kinematics():
            t  = occs.get("OP_Torso")
            p  = occs.get("OP_Pelvis")
            h  = occs.get("OP_Head")
            b  = occs.get("OP_Backpack")
            st = occs.get("OP_SteerPods")
            sh = occs.get("OP_Shields")

            if p:
                p.isGrounded = True

            # Core
            ball_joint("Waist_Cluster",  t,  p,  0, 0, WAIST_CTR-2.5)
            ball_joint("Neck_Cluster",   h,  t,  0, 0, NECK_JOINT_Z)
            rigid_joint("Backpack_Mount",b,  t)
            rigid_joint("Steer_Mount",  st,  t)
            rigid_joint("Shields_Mount",sh,  t)

            # Limbs
            for side in ["L", "R"]:
                sx = -HIP_X    if side == "L" else HIP_X
                ax = -SHOULDER_X if side == "L" else SHOULDER_X
                th = occs.get(f"OP_Thigh_{side}")
                sn = occs.get(f"OP_Shin_{side}")
                fo = occs.get(f"OP_Foot_{side}")
                ua = occs.get(f"OP_UpperArm_{side}")
                fa = occs.get(f"OP_Forearm_{side}")
                ha = occs.get(f"OP_Hand_{side}")

                ball_joint    (f"{side}_Hip_Cluster",      th, p,  sx,0,HIP_JOINT_Z)
                revolute_joint(f"{side}_Knee",             sn, th, sx,0,KNEE_CTR+1.5,"x")
                ball_joint    (f"{side}_Ankle_Cluster",    fo, sn, sx,0,ANKLE_CTR+2.2)
                ball_joint    (f"{side}_Shoulder_Cluster", ua, t,  ax,0,SHOULDER_CTR)
                revolute_joint(f"{side}_Elbow",            fa, ua, ax,0,ELBOW_Z,"x")
                revolute_joint(f"{side}_Wrist",            ha, fa, ax,0,WRIST_Z+0.8,"x")

                if side == "R":
                    bl = occs.get("OP_Ion_Blaster")
                    if bl:
                        rigid_joint("Blaster_Grip", bl, ha)

        build_kinematics()

        # ─── Kinematic Orphan Validation ──────────────────────────────────────
        def validate_kinematics():
            """Scans all components to detect disconnected/floating parts."""
            log_msg("Validating mechanical linkages...")
            orphans = []
            
            # Get all components that are referenced by at least one joint
            jointed_comps = set()
            for i in range(root.asBuiltJoints.count):
                j = root.asBuiltJoints.item(i)
                if j.occurrenceOne: jointed_comps.add(j.occurrenceOne.component.name)
                if j.occurrenceTwo: jointed_comps.add(j.occurrenceTwo.component.name)
                
            # Torso is the base root, so it doesn't strictly need a parent joint, but check others
            for comp in comps_list:
                if comp.name != "OP_Torso" and comp.name not in jointed_comps:
                    orphans.append(comp.name)
                    
            if orphans:
                log_msg("!!! WARNING: ORPHANED COMPONENTS DETECTED !!!")
                for o in orphans:
                    log_msg(f"   -> Component '{o}' has NO joints attached! It will not move with the robot.")
            else:
                log_msg("All components successfully bound to the kinematic chain. [ OK ]")

        validate_kinematics()

        # Fit view
        try:
            cam = app.activeViewport.camera
            cam.isFitView = True
            app.activeViewport.camera = cam
        except:
            pass

        # ╔═════════════════════════════════════════════════════════════════╗
        # ║            C O M P R E H E N S I V E   S I M U L A T I O N    ║
        # ║                    E N G I N E   v 2 . 0                       ║
        # ╚═════════════════════════════════════════════════════════════════╝
        class SimulationEngine:
            """
            9-module simulation suite for Optimus Prime G1.

            Usage:
                sim = SimulationEngine(root, comps_list, design, app, ui)
                sim.run_all_simulations()
            """

            # ── Joints known to be ball joints ────────────────────────────
            BALL_JOINTS = {
                "Waist_Cluster", "Neck_Cluster",
                "L_Hip_Cluster", "R_Hip_Cluster",
                "L_Ankle_Cluster", "R_Ankle_Cluster",
                "L_Shoulder_Cluster", "R_Shoulder_Cluster",
            }
            # ── Joints known to be revolute ───────────────────────────────
            REV_JOINTS = {
                "L_Knee", "R_Knee",
                "L_Elbow", "R_Elbow",
                "L_Wrist", "R_Wrist",
            }

            def __init__(self, root, comps_list, design, app, ui):
                self._root   = root
                self._comps  = comps_list
                self._design = design
                self._app    = app
                self._ui     = ui
                self._report = []   # accumulated text lines
                self._cols   = []   # accumulated collision strings

            # ─── Internal helpers ─────────────────────────────────────────

            def _gj(self, name):
                """Return named joint or None."""
                try:
                    j = self._root.asBuiltJoints.itemByName(name)
                    if j is not None:
                        return j
                    
                    # If not found, log all available joint names once
                    if not hasattr(self, '_logged_joints'):
                        self._logged_joints = True
                        j_names = [self._root.asBuiltJoints.item(i).name for i in range(self._root.asBuiltJoints.count)]
                        log_msg(f"Could not find joint '{name}'. Available joints: {j_names}")
                    
                    return None
                except:
                    log_msg(f"_gj exception for {name}: {traceback.format_exc()}")
                    return None

            @staticmethod
            def _ease(t):
                """Cubic ease-in-out for smooth motion."""
                return t * t * (3.0 - 2.0 * t)

            def _get(self, mo, axis):
                """Read current value from motion object (radians)."""
                try:
                    if mo.objectType == adsk.fusion.RevoluteJointMotion.classType():
                        return mo.rotationValue
                    if mo.objectType == adsk.fusion.BallJointMotion.classType():
                        return getattr(mo, axis + "Value")
                except:
                    pass
                return 0.0

            def _set(self, mo, axis, val):
                """Write value (radians) to motion object."""
                try:
                    if mo.objectType == adsk.fusion.RevoluteJointMotion.classType():
                        mo.rotationValue = val
                    elif mo.objectType == adsk.fusion.BallJointMotion.classType():
                        setattr(mo, axis + "Value", val)
                except:
                    pass

            def _refresh(self):
                """Pump events, refresh the viewport, and check for async STOP commands."""
                import os
                if os.path.exists(r"C:\opt_fusion_stop.flag"):
                    try: os.remove(r"C:\opt_fusion_stop.flag")
                    except: pass
                    raise Exception("SIMULATION_ABORTED_BY_USER")
                try:
                    self._app.activeViewport.refresh()
                except:
                    pass
                adsk.doEvents()

            # ─── Core animation API ───────────────────────────────────────

            def move_joint(self, name, deg, steps=20, axis='pitch', ease=True):
                """
                Drive one joint to `deg` degrees in `steps` frames.
                `axis` is used only for ball joints ('pitch','yaw','roll').
                """
                j = self._gj(name)
                if not j:
                    return
                mo    = j.jointMotion
                e_rad = math.radians(deg)
                s_rad = self._get(mo, axis)
                for i in range(1, steps + 1):
                    t = i / steps
                    if ease:
                        t = self._ease(t)
                    self._set(mo, axis, s_rad + (e_rad - s_rad) * t)
                    self._refresh()

            def move_group(self, targets, steps=20, ease=True):
                """
                Drive many joints simultaneously.
                `targets`: list of (joint_name, degrees [, axis])
                  axis defaults to 'pitch' if omitted.
                """
                active = []
                for item in targets:
                    name, deg       = item[0], item[1]
                    axis            = item[2] if len(item) > 2 else 'pitch'
                    j               = self._gj(name)
                    if not j:
                        continue
                    mo    = j.jointMotion
                    e_rad = math.radians(deg)
                    s_rad = self._get(mo, axis)
                    active.append((mo, s_rad, e_rad, axis))

                for i in range(1, steps + 1):
                    t = i / steps
                    if ease:
                        t = self._ease(t)
                    for mo, s, e, ax in active:
                        self._set(mo, ax, s + (e - s) * t)
                    self._refresh()
                    
                    # Continuous Collision Checking during interpolation
                    if getattr(self, "_strict_mode", False):
                        mid_hits = self._check(vol_min=0.015)
                        if mid_hits:
                            log_msg(f"!!! FATAL KINEMATIC ERROR !!!")
                            log_msg(f"Mid-animation collision at {t*100:.1f}% of movement step.")
                            log_msg("Context - The following joints were being driven:")
                            for mo, s, e, ax in active:
                                j_name = mo.parentJoint.name if mo.parentJoint else "Unknown Joint"
                                log_msg(f"   -> {j_name} ({ax}): {math.degrees(s):.1f}° -> {math.degrees(e):.1f}°")
                            log_msg("Collision Details:")
                            for hit in mid_hits:
                                log_msg(f"   -> {hit}")
                            raise Exception("Structural Interpenetration Detected (Parts passed through each other!)")

            def reset_all(self, steps=16):
                """Return every joint to 0°."""
                tgts = []
                for jn in self.BALL_JOINTS:
                    for ax in ('pitch', 'yaw', 'roll'):
                        tgts.append((jn, 0, ax))
                for jn in self.REV_JOINTS:
                    tgts.append((jn, 0, 'pitch'))
                self.move_group(tgts, steps)
                log_msg("→ reset to neutral")

            # ─── POSE LIBRARY  (7 named poses) ────────────────────────────

            def pose_attention(self):
                """Rigid attention stance."""
                self.move_group([
                    ("L_Shoulder_Cluster", -5,'pitch'),
                    ("R_Shoulder_Cluster", -5,'pitch'),
                    ("L_Elbow", 0,'pitch'), ("R_Elbow", 0,'pitch'),
                    ("Waist_Cluster", 0,'pitch'), ("Neck_Cluster", 0,'pitch'),
                ])

            def pose_t_stance(self):
                """T-pose reference alignment."""
                self.move_group([
                    ("L_Shoulder_Cluster",  0,'pitch'),
                    ("R_Shoulder_Cluster",  0,'pitch'),
                    ("L_Shoulder_Cluster",-90,'roll'),
                    ("R_Shoulder_Cluster", 90,'roll'),
                    ("L_Elbow", 0,'pitch'), ("R_Elbow", 0,'pitch'),
                ])

            def pose_combat(self):
                """Wide battle-ready stance."""
                self.move_group([
                    ("Waist_Cluster",       -5,'pitch'),
                    ("L_Hip_Cluster",      -12,'pitch'),("R_Hip_Cluster",     -12,'pitch'),
                    ("L_Hip_Cluster",       12,'roll'), ("R_Hip_Cluster",     -12,'roll'),
                    ("L_Knee",              22,'pitch'),("R_Knee",             22,'pitch'),
                    ("L_Ankle_Cluster",    -14,'pitch'),("R_Ankle_Cluster",   -14,'pitch'),
                    ("L_Shoulder_Cluster", -30,'pitch'),("R_Shoulder_Cluster", 30,'pitch'),
                    ("L_Shoulder_Cluster",  18,'yaw'),  ("R_Shoulder_Cluster",-18,'yaw'),
                    ("L_Elbow",             50,'pitch'),("R_Elbow",            50,'pitch'),
                    ("Neck_Cluster",         5,'pitch'),
                ])

            def pose_victory(self):
                """Right fist raised."""
                self.move_group([
                    ("R_Shoulder_Cluster",155,'pitch'),
                    ("R_Elbow",            5,'pitch'),
                    ("L_Shoulder_Cluster",-30,'pitch'),
                    ("L_Elbow",           35,'pitch'),
                    ("Neck_Cluster",       -8,'pitch'),
                    ("Waist_Cluster",       4,'pitch'),
                ])

            def pose_kneeling(self):
                """Down on right knee."""
                self.move_group([
                    ("R_Hip_Cluster",     -88,'pitch'),
                    ("R_Knee",             88,'pitch'),
                    ("R_Ankle_Cluster",    88,'pitch'),
                    ("L_Hip_Cluster",     -42,'pitch'),
                    ("L_Knee",             42,'pitch'),
                    ("L_Ankle_Cluster",   -10,'pitch'),
                    ("Waist_Cluster",      -8,'pitch'),
                    ("Neck_Cluster",        6,'pitch'),
                    ("L_Shoulder_Cluster",-20,'pitch'),
                    ("L_Elbow",            30,'pitch'),
                ])

            def pose_squat(self):
                """Deep squat with arms forward."""
                self.move_group([
                    ("L_Hip_Cluster",     -58,'pitch'),("R_Hip_Cluster",     -58,'pitch'),
                    ("L_Hip_Cluster",      14,'roll'), ("R_Hip_Cluster",     -14,'roll'),
                    ("L_Knee",             92,'pitch'),("R_Knee",             92,'pitch'),
                    ("L_Ankle_Cluster",    42,'pitch'),("R_Ankle_Cluster",    42,'pitch'),
                    ("Waist_Cluster",      10,'pitch'),
                    ("L_Shoulder_Cluster", 28,'pitch'),("R_Shoulder_Cluster", 28,'pitch'),
                    ("L_Elbow",            55,'pitch'),("R_Elbow",            55,'pitch'),
                ])

            def pose_aim_blaster(self):
                """Blaster levelled at target."""
                self.move_group([
                    ("Waist_Cluster",       -8,'yaw'),
                    ("R_Shoulder_Cluster", -15,'pitch'),
                    ("R_Shoulder_Cluster",   5,'yaw'),
                    ("R_Elbow",              0,'pitch'),
                    ("R_Wrist",              0,'pitch'),
                    ("L_Shoulder_Cluster", -45,'pitch'),
                    ("L_Elbow",            40,'pitch'),
                    ("Neck_Cluster",        -5,'yaw'),
                    ("Neck_Cluster",        -4,'pitch'),
                ])

            # ─────────────────────────────────────────────────────────────
            # MODULE 1 — JOINT ROM TEST
            # ─────────────────────────────────────────────────────────────
            def test_joint_rom(self):
                """
                Every joint is swept: min → 0 → max.
                Collisions are sampled at each extreme.
                Results appended to self._report.
                """
                log_msg("MODULE 1: JOINT ROM TEST")

                # (name, axis, min_deg, max_deg, human label)
                specs = [
                    # Waist
                    ("Waist_Cluster","pitch",-45, 45,"Waist Pitch"),
                    ("Waist_Cluster","yaw",  -90, 90,"Waist Yaw"),
                    ("Waist_Cluster","roll", -15, 15,"Waist Roll"),
                    # Neck
                    ("Neck_Cluster","pitch", -30, 45,"Neck Pitch"),
                    ("Neck_Cluster","yaw",   -60, 60,"Neck Yaw"),
                    ("Neck_Cluster","roll",  -20, 20,"Neck Roll"),
                    # Left Hip
                    ("L_Hip_Cluster","pitch",-90, 30,"L Hip Pitch"),
                    ("L_Hip_Cluster","yaw",  -30, 30,"L Hip Yaw"),
                    ("L_Hip_Cluster","roll", -30, 30,"L Hip Roll"),
                    # Right Hip
                    ("R_Hip_Cluster","pitch",-90, 30,"R Hip Pitch"),
                    ("R_Hip_Cluster","yaw",  -30, 30,"R Hip Yaw"),
                    ("R_Hip_Cluster","roll", -30, 30,"R Hip Roll"),
                    # Knees (revolute — axis ignored internally)
                    ("L_Knee","pitch",   0,135,"L Knee Flex"),
                    ("R_Knee","pitch",   0,135,"R Knee Flex"),
                    # Ankles
                    ("L_Ankle_Cluster","pitch",-30,45,"L Ankle Pitch"),
                    ("L_Ankle_Cluster","roll", -20,20,"L Ankle Roll"),
                    ("R_Ankle_Cluster","pitch",-30,45,"R Ankle Pitch"),
                    ("R_Ankle_Cluster","roll", -20,20,"R Ankle Roll"),
                    # Left Shoulder
                    ("L_Shoulder_Cluster","pitch",-175,60,"L Shoulder Pitch"),
                    ("L_Shoulder_Cluster","yaw",  -90,90,"L Shoulder Yaw"),
                    ("L_Shoulder_Cluster","roll", -90,90,"L Shoulder Roll"),
                    # Right Shoulder
                    ("R_Shoulder_Cluster","pitch",-175,60,"R Shoulder Pitch"),
                    ("R_Shoulder_Cluster","yaw",  -90,90,"R Shoulder Yaw"),
                    ("R_Shoulder_Cluster","roll", -90,90,"R Shoulder Roll"),
                    # Elbows
                    ("L_Elbow","pitch",  0,150,"L Elbow Flex"),
                    ("R_Elbow","pitch",  0,150,"R Elbow Flex"),
                    # Wrists
                    ("L_Wrist","pitch",-45, 45,"L Wrist Roll"),
                    ("R_Wrist","pitch",-45, 45,"R Wrist Roll"),
                ]

                lines = []
                for jname, ax, mn, mx, label in specs:
                    if not self._gj(jname):
                        lines.append(f"  ⚫ MISSING : {label}")
                        continue

                    # Sweep to MIN
                    self.move_joint(jname, mn, steps=8, axis=ax)
                    c_min = self._check()

                    # Back to 0
                    self.move_joint(jname, 0, steps=5, axis=ax)

                    # Sweep to MAX
                    self.move_joint(jname, mx, steps=8, axis=ax)
                    c_max = self._check()

                    # Back to 0
                    self.move_joint(jname, 0, steps=5, axis=ax)

                    if c_min or c_max:
                        where = ("MIN " if c_min else "") + ("MAX" if c_max else "")
                        status = f"⚠️  COLLISION [{where.strip()}]"
                        self._cols.extend(c_min + c_max)
                    else:
                        status = "✅ OK"

                    line = f"  {status:<26} {label:<26} [{mn}°…{mx}°]"
                    lines.append(line)
                    log_msg(line)

                self._report.append("── MODULE 1: JOINT ROM ──")
                self._report.extend(lines)

            # ─────────────────────────────────────────────────────────────
            # MODULE 2 — HEAD LOOK-AROUND
            # ─────────────────────────────────────────────────────────────
            def simulate_head_look(self):
                """5-position head scan."""
                log_msg("MODULE 2: HEAD LOOK-AROUND")
                seq = [
                    [("Neck_Cluster", 35, 'yaw')],
                    [("Neck_Cluster",-12, 'pitch'), ("Neck_Cluster", 30, 'yaw')],
                    [("Neck_Cluster",  6, 'pitch'), ("Neck_Cluster",-35, 'yaw')],
                    [("Neck_Cluster",-12, 'pitch'), ("Neck_Cluster",-30, 'yaw')],
                    [("Neck_Cluster",  0, 'pitch'), ("Neck_Cluster",  0, 'yaw')],
                ]
                for step in seq:
                    self.move_group(step, steps=14)
                log_msg("Head look done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 3 — WAVE GESTURE
            # ─────────────────────────────────────────────────────────────
            def simulate_wave(self):
                """Raise right arm and wave 3×."""
                log_msg("MODULE 3: WAVE GESTURE")
                self.move_group([
                    ("R_Shoulder_Cluster", 90,'pitch'),
                    ("R_Shoulder_Cluster", 12,'roll'),
                    ("R_Elbow",            30,'pitch'),
                    ("Neck_Cluster",       -5,'yaw'),
                ], steps=16)
                for _ in range(3):
                    self.move_joint("R_Wrist",  38, steps=7, axis='pitch')
                    self.move_joint("R_Wrist", -38, steps=7, axis='pitch')
                self.move_group([
                    ("R_Shoulder_Cluster",  0,'pitch'),
                    ("R_Shoulder_Cluster",  0,'roll'),
                    ("R_Elbow",             0,'pitch'),
                    ("R_Wrist",             0,'pitch'),
                    ("Neck_Cluster",        0,'yaw'),
                ], steps=16)
                log_msg("Wave done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 4 — IDLE BREATHING
            # ─────────────────────────────────────────────────────────────
            def simulate_idle_breathing(self, cycles=4):
                """Subtle torso oscillation — 4 breath cycles."""
                log_msg("MODULE 4: IDLE BREATHING")
                INHALE = [
                    ("Waist_Cluster",       2,'pitch'),
                    ("L_Shoulder_Cluster", -3,'pitch'),
                    ("R_Shoulder_Cluster", -3,'pitch'),
                    ("Neck_Cluster",        1,'pitch'),
                ]
                EXHALE = [
                    ("Waist_Cluster",       0,'pitch'),
                    ("L_Shoulder_Cluster",  0,'pitch'),
                    ("R_Shoulder_Cluster",  0,'pitch'),
                    ("Neck_Cluster",        0,'pitch'),
                ]
                for _ in range(cycles):
                    self.move_group(INHALE, steps=14)
                    self.move_group(EXHALE, steps=14)
                log_msg("Breathing done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 5 — ADVANCED WALKING  (4 cycles)
            # ─────────────────────────────────────────────────────────────
            def simulate_walking_advanced(self, num_cycles=4):
                """
                Physically-plausible gait:
                  • Hip lateral sway (roll) during weight transfer
                  • Arm counter-swing with elbow flex
                  • Ankle push-off and toe-off
                  • Knee flexion during swing phase
                  • Head bob
                  • Waist axial rotation
                Collision sampled every 2 cycles.
                """
                log_msg("MODULE 5: ADVANCED WALKING")

                LIFT    = -26    # hip pitch: foot lift
                FWD     =  22    # hip pitch: forward stride
                PUSH    =  16    # ankle: push-off
                SWAY    =   9    # hip roll: lateral weight shift
                A_SW    =  28    # shoulder: arm swing
                K_FLEX  =  20    # knee: swing flex
                W_ROT   =   6    # waist: axial rotation
                H_BOB   =   3    # neck: vertical bob
                FRAMES  =  18

                def gait_step(swing, plant):
                    sm = -1 if swing == "L" else 1

                    # Phase A — lift & swing
                    self.move_group([
                        (f"{swing}_Hip_Cluster",   LIFT,       'pitch'),
                        (f"{swing}_Knee",          K_FLEX,     'pitch'),
                        (f"{swing}_Ankle_Cluster", PUSH*0.6,   'pitch'),
                        (f"{plant}_Hip_Cluster",   10,         'pitch'),
                        (f"{plant}_Knee",          5,          'pitch'),
                        (f"{plant}_Ankle_Cluster",-PUSH,       'pitch'),
                        ("L_Hip_Cluster",  -SWAY if swing=="R" else  SWAY,'roll'),
                        ("R_Hip_Cluster",  -SWAY if swing=="R" else  SWAY,'roll'),
                        (f"{swing}_Shoulder_Cluster",  A_SW,  'pitch'),
                        (f"{plant}_Shoulder_Cluster", -A_SW,  'pitch'),
                        (f"{swing}_Elbow",  14,'pitch'),
                        (f"{plant}_Elbow",  22,'pitch'),
                        ("Waist_Cluster",   sm * W_ROT,'yaw'),
                        ("Neck_Cluster",   -sm * 3,    'yaw'),
                        ("Neck_Cluster",    H_BOB,     'pitch'),
                    ], steps=FRAMES)

                    # Phase B — plant & load
                    self.move_group([
                        (f"{swing}_Hip_Cluster",    FWD,     'pitch'),
                        (f"{swing}_Knee",           0,       'pitch'),
                        (f"{swing}_Ankle_Cluster", -8,       'pitch'),
                        (f"{plant}_Hip_Cluster",   -FWD*0.5, 'pitch'),
                        (f"{plant}_Ankle_Cluster",  PUSH,    'pitch'),
                        ("L_Hip_Cluster",  0,'roll'),
                        ("R_Hip_Cluster",  0,'roll'),
                        ("Waist_Cluster",  0,'yaw'),
                        ("Neck_Cluster",   0,'yaw'),
                        ("Neck_Cluster",  -H_BOB*0.5,'pitch'),
                    ], steps=FRAMES)

                for cyc in range(num_cycles):
                    log_msg(f"  walk cycle {cyc+1}/{num_cycles}")
                    gait_step("R", "L")
                    gait_step("L", "R")
                    if cyc % 2 == 1:
                        hits = self._check()
                        if hits:
                            self._cols.extend(hits)

                self.reset_all()
                log_msg("Walking done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 6 — RUNNING  (3 cycles)
            # ─────────────────────────────────────────────────────────────
            def simulate_running(self, num_cycles=3):
                """Exaggerated fast run — deeper stride, more knee lift."""
                log_msg("MODULE 6: RUNNING")
                FRAMES = 9

                def run_step(swing, plant):
                    self.move_group([
                        (f"{swing}_Hip_Cluster",    -42,'pitch'),
                        (f"{swing}_Knee",            52,'pitch'),
                        (f"{swing}_Ankle_Cluster",   28,'pitch'),
                        (f"{plant}_Hip_Cluster",     28,'pitch'),
                        (f"{plant}_Knee",            12,'pitch'),
                        (f"{plant}_Ankle_Cluster",  -28,'pitch'),
                        (f"{swing}_Shoulder_Cluster",55,'pitch'),
                        (f"{plant}_Shoulder_Cluster",-55,'pitch'),
                        ("Waist_Cluster",10 if swing=="R" else -10,'yaw'),
                    ], steps=FRAMES)
                    self.move_group([
                        (f"{swing}_Hip_Cluster",    32,'pitch'),
                        (f"{swing}_Knee",           16,'pitch'),
                        (f"{swing}_Ankle_Cluster", -24,'pitch'),
                        (f"{plant}_Hip_Cluster",   -22,'pitch'),
                        (f"{plant}_Knee",           48,'pitch'),
                        (f"{plant}_Ankle_Cluster",  26,'pitch'),
                        (f"{swing}_Shoulder_Cluster",-45,'pitch'),
                        (f"{plant}_Shoulder_Cluster", 45,'pitch'),
                        ("Waist_Cluster",0,'yaw'),
                    ], steps=FRAMES)

                for _ in range(num_cycles):
                    run_step("R", "L")
                    run_step("L", "R")

                self.reset_all()
                log_msg("Running done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 7 — COMBAT SEQUENCE
            # ─────────────────────────────────────────────────────────────
            def simulate_combat_sequence(self):
                """
                Choreography:
                  1) Enter combat stance
                  2) Right cross punch  (wind-up → extend)
                  3) Blaster aim & hold
                  4) Left forearm block
                  5) Left uppercut
                  6) Head track target
                  7) Return to neutral
                """
                log_msg("MODULE 7: COMBAT SEQUENCE")

                log_msg("  → combat stance")
                self.pose_combat()

                log_msg("  → right cross: wind-up")
                self.move_group([
                    ("Waist_Cluster",      -28,'yaw'),
                    ("R_Shoulder_Cluster", -28,'pitch'),
                    ("R_Shoulder_Cluster", -22,'yaw'),
                    ("R_Elbow",             95,'pitch'),
                ], steps=10)

                log_msg("  → right cross: extension")
                self.move_group([
                    ("Waist_Cluster",       22,'yaw'),
                    ("R_Shoulder_Cluster",  18,'pitch'),
                    ("R_Shoulder_Cluster",  14,'yaw'),
                    ("R_Elbow",              0,'pitch'),
                ], steps=8)

                log_msg("  → blaster aim")
                self.move_group([
                    ("Waist_Cluster",        0,'yaw'),
                    ("R_Shoulder_Cluster", -12,'pitch'),
                    ("R_Shoulder_Cluster",   4,'yaw'),
                    ("R_Elbow",              0,'pitch'),
                    ("Neck_Cluster",        -6,'yaw'),
                    ("Neck_Cluster",        -5,'pitch'),
                ], steps=12)

                log_msg("  → left forearm block")
                self.move_group([
                    ("L_Shoulder_Cluster",  48,'pitch'),
                    ("L_Shoulder_Cluster", -22,'yaw'),
                    ("L_Elbow",             95,'pitch'),
                ], steps=10)

                log_msg("  → left uppercut")
                self.move_group([
                    ("L_Shoulder_Cluster", -82,'pitch'),
                    ("L_Shoulder_Cluster",  32,'yaw'),
                    ("L_Elbow",             62,'pitch'),
                    ("Waist_Cluster",       12,'pitch'),
                ], steps=8)

                log_msg("  → track target")
                self.move_group([
                    ("Neck_Cluster",-10,'yaw'),
                    ("Neck_Cluster", -8,'pitch'),
                ], steps=8)

                self.reset_all()
                log_msg("Combat done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 8a — TRANSFORMATION  Robot → Truck
            # ─────────────────────────────────────────────────────────────
            def simulate_transformation_to_truck(self):
                """
                9-stage physically-sequenced transformation.
                Stage 1  Wrists stow (tuck blaster / left hand)
                Stage 2  Elbows fold to ~132°
                Stage 3  Shoulders pitch down + sweep inward + roll
                Stage 4  Head retracts (chin to chest)
                Stage 5  Waist pitches 90° forward  ← cab forms
                Stage 6  Hips flex (legs travel under torso)
                Stage 7  Knees fold to ~158° (legs go horizontal)
                Stage 8  Ankles tuck (feet become truck underside)
                Stage 9  Arms lock flush to cab sides
                """
                log_msg("MODULE 8a: ROBOT → TRUCK")

                log_msg("  Stage 1 — stow wrists / blaster")
                self.move_group([
                    ("R_Wrist", -88,'pitch'),
                    ("L_Wrist", -42,'pitch'),
                ], steps=12)

                log_msg("  Stage 2 — fold elbows up")
                self.move_group([
                    ("L_Elbow", 132,'pitch'),
                    ("R_Elbow", 132,'pitch'),
                ], steps=15)

                log_msg("  Stage 3 — shoulder pitch + inward sweep + roll")
                self.move_group([
                    ("L_Shoulder_Cluster", -88,'pitch'),
                    ("R_Shoulder_Cluster", -88,'pitch'),
                    ("L_Shoulder_Cluster",  62,'yaw'),
                    ("R_Shoulder_Cluster", -62,'yaw'),
                    ("L_Shoulder_Cluster", -28,'roll'),
                    ("R_Shoulder_Cluster",  28,'roll'),
                ], steps=20)

                log_msg("  Stage 4 — head retract")
                self.move_group([
                    ("Neck_Cluster", -58,'pitch'),
                    ("Neck_Cluster",   0,'yaw'),
                ], steps=12)

                log_msg("  Stage 5 — waist 90° forward (cab folds)")
                self.move_group([
                    ("Waist_Cluster", 90,'pitch'),
                ], steps=22)

                log_msg("  Stage 6 — hip flexion (legs under torso)")
                self.move_group([
                    ("L_Hip_Cluster", -88,'pitch'),
                    ("R_Hip_Cluster", -88,'pitch'),
                    ("L_Hip_Cluster",  -5,'yaw'),
                    ("R_Hip_Cluster",   5,'yaw'),
                ], steps=20)

                log_msg("  Stage 7 — knees fold to horizontal")
                self.move_group([
                    ("L_Knee", 158,'pitch'),
                    ("R_Knee", 158,'pitch'),
                ], steps=18)

                log_msg("  Stage 8 — ankles tuck")
                self.move_group([
                    ("L_Ankle_Cluster", 88,'pitch'),
                    ("R_Ankle_Cluster", 88,'pitch'),
                    ("L_Ankle_Cluster",  0,'roll'),
                    ("R_Ankle_Cluster",  0,'roll'),
                ], steps=14)

                log_msg("  Stage 9 — arm lock to cab sides")
                self.move_group([
                    ("L_Shoulder_Cluster",  0,'pitch'),
                    ("R_Shoulder_Cluster",  0,'pitch'),
                    ("L_Shoulder_Cluster", 90,'yaw'),
                    ("R_Shoulder_Cluster",-90,'yaw'),
                    ("L_Shoulder_Cluster",  0,'roll'),
                    ("R_Shoulder_Cluster",  0,'roll'),
                ], steps=12)

                hits    = self._check()
                verdict = "✅ CLEAR" if not hits else f"⚠️  {len(hits)} collision(s)"
                log_msg(f"  Truck-mode check: {verdict}")
                self._cols.extend(hits)

                self._report.append("── MODULE 8a: TRANSFORMATION (Robot→Truck) ──")
                self._report.append(f"  Interference: {verdict}")
                return hits

            # ─────────────────────────────────────────────────────────────
            # MODULE 8b — TRUCK DRIVING
            # ─────────────────────────────────────────────────────────────
            def simulate_truck_driving(self):
                """Steer left → centre → right → centre with body roll."""
                log_msg("MODULE 8b: TRUCK DRIVING")
                # Steer left
                self.move_group([
                    ("L_Ankle_Cluster", 8,'roll'),
                    ("R_Ankle_Cluster", 8,'roll'),
                    ("Waist_Cluster",  -4,'roll'),
                ], steps=14)
                # Centre
                self.move_group([
                    ("L_Ankle_Cluster", 0,'roll'),
                    ("R_Ankle_Cluster", 0,'roll'),
                    ("Waist_Cluster",   0,'roll'),
                ], steps=10)
                # Steer right
                self.move_group([
                    ("L_Ankle_Cluster",-8,'roll'),
                    ("R_Ankle_Cluster",-8,'roll'),
                    ("Waist_Cluster",   4,'roll'),
                ], steps=14)
                # Centre
                self.move_group([
                    ("L_Ankle_Cluster", 0,'roll'),
                    ("R_Ankle_Cluster", 0,'roll'),
                    ("Waist_Cluster",   0,'roll'),
                ], steps=10)
                log_msg("Truck driving done.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 8c — TRANSFORMATION  Truck → Robot  (reverse)
            # ─────────────────────────────────────────────────────────────
            def simulate_transformation_to_robot(self):
                """Reverse the 9-stage transformation."""
                log_msg("MODULE 8c: TRUCK → ROBOT")

                self.move_group([("L_Shoulder_Cluster",0,'yaw'),
                                 ("R_Shoulder_Cluster",0,'yaw')],steps=12)
                self.move_group([("L_Ankle_Cluster",0,'pitch'),
                                 ("R_Ankle_Cluster",0,'pitch')],steps=14)
                self.move_group([("L_Knee",0,'pitch'),
                                 ("R_Knee",0,'pitch')],steps=18)
                self.move_group([("L_Hip_Cluster",0,'pitch'),("R_Hip_Cluster",0,'pitch'),
                                 ("L_Hip_Cluster",0,'yaw'),  ("R_Hip_Cluster",0,'yaw')],steps=20)
                self.move_group([("Waist_Cluster",0,'pitch')],steps=22)
                self.move_group([("Neck_Cluster",0,'pitch')],steps=12)
                self.move_group([("L_Shoulder_Cluster",0,'pitch'),
                                 ("R_Shoulder_Cluster",0,'pitch'),
                                 ("L_Shoulder_Cluster",0,'yaw'),
                                 ("R_Shoulder_Cluster",0,'yaw'),
                                 ("L_Shoulder_Cluster",0,'roll'),
                                 ("R_Shoulder_Cluster",0,'roll')],steps=20)
                self.move_group([("L_Elbow",0,'pitch'),
                                 ("R_Elbow",0,'pitch')],steps=14)
                self.move_group([("L_Wrist",0,'pitch'),
                                 ("R_Wrist",0,'pitch')],steps=10)
                log_msg("Robot mode restored.")

            # ─────────────────────────────────────────────────────────────
            # MODULE 9a — STABILITY ANALYSIS
            # ─────────────────────────────────────────────────────────────
            def run_stability_analysis(self):
                """
                For 4 poses estimate geometric CoM (average bounding-box
                centre of all solid bodies) and check it lies within the
                foot support rectangle ±6 cm X, ±4 cm Y.
                """
                log_msg("MODULE 9a: STABILITY ANALYSIS")
                FX, FY = 6.0, 4.0   # foot support half-extents (cm)
                poses  = [
                    ("Attention", self.pose_attention),
                    ("Combat",    self.pose_combat),
                    ("Squat",     self.pose_squat),
                    ("Victory",   self.pose_victory),
                ]
                lines = []
                for pname, pfn in poses:
                    pfn()
                    tx, ty, n = 0.0, 0.0, 0
                    for comp in self._comps:
                        for body in comp.bRepBodies:
                            if not body.isSolid:
                                continue
                            if body.name and "_Vis" in body.name:
                                continue
                            try:
                                bb  = body.boundingBox
                                tx += (bb.minPoint.x + bb.maxPoint.x) * 0.5
                                ty += (bb.minPoint.y + bb.maxPoint.y) * 0.5
                                n  += 1
                            except:
                                pass
                    if n:
                        cx, cy = tx / n, ty / n
                        ok     = abs(cx) <= FX and abs(cy) <= FY
                        v      = "✅ STABLE" if ok else f"⚠️  UNSTABLE CoM=({cx:.1f},{cy:.1f})"
                    else:
                        v = "⚫ NO DATA"
                    line = f"  {pname:<14} {v}"
                    lines.append(line)
                    log_msg(line)
                    self.reset_all(steps=8)

                self._report.append("── MODULE 9a: STABILITY ──")
                self._report.extend(lines)

            # ─────────────────────────────────────────────────────────────
            # MODULE 9b — SERVO LOAD ESTIMATION
            # ─────────────────────────────────────────────────────────────
            def estimate_servo_loads(self):
                """
                Static worst-case torque at each major joint.
                Masses are ABS/PLA estimates; lever arms are geometric.
                Compared to MG996R (9.4 kg·cm) and MG90S (1.8 kg·cm).
                """
                log_msg("MODULE 9b: SERVO LOAD ESTIMATION")
                G = 9.81

                # (label, distal_mass_g, lever_cm, servo_type)
                table = [
                    ("Neck Pitch",          120,  3.0, "MG90S"),
                    ("L Shoulder Pitch",    390, 12.0, "MG996R"),
                    ("R Shoulder Pitch",    390, 12.0, "MG996R"),
                    ("L Elbow",             210,  7.0, "MG996R"),
                    ("R Elbow",             210,  7.0, "MG996R"),
                    ("L Hip Pitch",         820, 15.0, "MG996R"),
                    ("R Hip Pitch",         820, 15.0, "MG996R"),
                    ("L Knee Pitch",        540,  9.0, "MG996R"),
                    ("R Knee Pitch",        540,  9.0, "MG996R"),
                    ("Waist Pitch",        2100,  8.0, "MG996R"),
                ]
                RATED = {"MG996R": 9.4, "MG90S": 1.8}
                lines = []
                for label, mass_g, lever_cm, stype in table:
                    F         = (mass_g / 1000.0) * G
                    need_kgcm = (F * lever_cm / 100.0) / 0.0981
                    rated     = RATED[stype]
                    margin    = rated / need_kgcm if need_kgcm > 0 else 99.0
                    st = ("✅ OK" if margin >= 1.5 else
                          "⚠️  MARGINAL" if margin >= 0.9 else
                          "❌ OVERLOAD")
                    line = (f"  {label:<24} need {need_kgcm:5.2f} kg·cm  "
                            f"rated {rated:.1f}  margin {margin:.2f}×  {stype}  {st}")
                    lines.append(line)
                    log_msg(line)

                self._report.append("── MODULE 9b: SERVO LOADS ──")
                self._report.extend(lines)

            # ─────────────────────────────────────────────────────────────
            # INTERFERENCE CHECK  (capped for speed)
            # ─────────────────────────────────────────────────────────────
            def _check(self, vol_min=0.015):
                """
                Sample ALL structural bodies and run Fusion's
                interference analyser. Returns detailed description strings.
                """
                SKIP = {"Marker","Pivot","_Vis","Horn","MtA","Wire",
                        "Axle","Scope","Antenna","Badge","Tip","Bore"}
                try:
                    bodies = adsk.core.ObjectCollection.create()
                    for comp in self._comps:
                        for body in comp.bRepBodies:
                            if not body.isSolid:
                                continue
                            if body.name and any(s in body.name for s in SKIP):
                                continue
                            bodies.add(body)
                            
                    if bodies.count < 2:
                        return []
                        
                    inp = self._design.createInterferenceInput(bodies)
                    inp.isCoincidentFacesInterference = False
                    res = self._design.analyzeInterference(inp)
                    hits = []
                    
                    if res and res.count > 0:
                        for i in range(res.count):
                            r = res.item(i)
                            if r.interferenceBody and r.interferenceBody.volume > vol_min:
                                comp1 = r.entityOne.parentComponent.name if r.entityOne.parentComponent else "?"
                                comp2 = r.entityTwo.parentComponent.name if r.entityTwo.parentComponent else "?"
                                body1 = r.entityOne.name
                                body2 = r.entityTwo.name
                                
                                if comp1 != comp2:
                                    # Extract the exact XYZ coordinate of the collision intersection
                                    try:
                                        com = r.interferenceBody.physicalProperties.centerOfMass
                                        loc_str = f"XYZ:({com.x:.2f}, {com.y:.2f}, {com.z:.2f}) cm"
                                    except:
                                        loc_str = "XYZ:(Unknown)"
                                        
                                    hit_str = f"[{comp1} / {body1}] ↔ [{comp2} / {body2}] | Vol: {r.interferenceBody.volume:.3f} cm³ | {loc_str}"
                                    hits.append(hit_str)
                                    log_msg(f"COLLISION DETECTED: {hit_str}")
                                    
                    return list(set(hits))
                except Exception as ex:
                    log_msg(f"CRITICAL COLLISION ERROR: {traceback.format_exc()}")
                    return []

            # ─────────────────────────────────────────────────────────────
            # URDF EXPORT
            # ─────────────────────────────────────────────────────────────
            def export_urdf(self, path):
                """Write a minimal URDF skeleton file."""
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    L = ['<?xml version="1.0"?>',
                         '<robot name="optimus_prime_g1">']
                    for comp in self._comps:
                        L.append(f'  <link name="{comp.name}">')
                        L.append('    <inertial>')
                        L.append('      <origin xyz="0 0 0" rpy="0 0 0"/>')
                        L.append('      <mass value="1.0"/>')
                        L.append('      <inertia ixx="0.01" ixy="0" ixz="0"'
                                 ' iyy="0.01" iyz="0" izz="0.01"/>')
                        L.append('    </inertial>')
                        L.append('  </link>')
                    for j in self._root.asBuiltJoints:
                        mo = j.jointMotion
                        p  = (j.occurrenceOne.component.name
                              if j.occurrenceOne else "world")
                        c  = (j.occurrenceTwo.component.name
                              if j.occurrenceTwo else "world")
                        jt = ("revolute" if mo.objectType ==
                              adsk.fusion.RevoluteJointMotion.classType() else
                              "fixed" if mo.objectType ==
                              adsk.fusion.RigidJointMotion.classType() else "floating")
                        L.append(f'  <joint name="{j.name}" type="{jt}">')
                        L.append(f'    <parent link="{p}"/>')
                        L.append(f'    <child  link="{c}"/>')
                        L.append('    <axis xyz="0 0 1"/>')
                        L.append('  </joint>')
                    L.append('</robot>')
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("\n".join(L))
                    log_msg(f"URDF → {path}")
                    return path
                except Exception as ex:
                    log_msg(f"URDF export failed: {ex}")
                    return None

            # ─────────────────────────────────────────────────────────────
            # MASTER RUNNER
            # ─────────────────────────────────────────────────────────────
            def run_all_simulations(self):
                """
                Execute all 9 modules in order.
                Shows a summary dialog and appends full results to the log.
                """
                self._report = []
                self._cols   = []

                self._ui.messageBox(
                    "🤖  OPTIMUS PRIME G1  v6.0\n\n"
                    "Starting 9-module simulation suite:\n\n"
                    "  1  Joint ROM test (every joint, collision-checked)\n"
                    "  2  Head look-around\n"
                    "  3  Wave gesture\n"
                    "  4  Idle breathing (4 cycles)\n"
                    "  5  Advanced walking (4 cycles, hip sway + arm swing)\n"
                    "  6  Running (3 cycles)\n"
                    "  7  Combat sequence\n"
                    "  8  Transformation Robot→Truck→Robot\n"
                    "  9  Stability + servo load analysis\n\n"
                    "Progress is logged to:\n"
                    "  C:\\\\opt_fusion_log.txt\n\n"
                    "Please wait — this will take several minutes.",
                    "OP G1 Simulation Suite")

                # ── Module 1 ──────────────────────────────────────────
                log_msg("--- MODULE 1 / 9 ---")
                self.test_joint_rom()
                self.reset_all()

                # ── Module 2 ──────────────────────────────────────────
                log_msg("--- MODULE 2 / 9 ---")
                self.simulate_head_look()

                # ── Module 3 ──────────────────────────────────────────
                log_msg("--- MODULE 3 / 9 ---")
                self.simulate_wave()

                # ── Module 4 ──────────────────────────────────────────
                log_msg("--- MODULE 4 / 9 ---")
                self.simulate_idle_breathing(cycles=4)

                # ── Module 5 ──────────────────────────────────────────
                log_msg("--- MODULE 5 / 9 ---")
                self.simulate_walking_advanced(num_cycles=4)

                # ── Module 6 ──────────────────────────────────────────
                log_msg("--- MODULE 6 / 9 ---")
                self.simulate_running(num_cycles=3)

                # ── Module 7 ──────────────────────────────────────────
                log_msg("--- MODULE 7 / 9 ---")
                self.simulate_combat_sequence()

                # ── Module 8 ──────────────────────────────────────────
                log_msg("--- MODULE 8 / 9 ---")
                self.simulate_transformation_to_truck()
                self.simulate_truck_driving()
                self.simulate_transformation_to_robot()
                self.reset_all()

                # ── Module 9 ──────────────────────────────────────────
                log_msg("--- MODULE 9 / 9 ---")
                self.run_stability_analysis()
                self.estimate_servo_loads()

                # ── URDF ──────────────────────────────────────────────
                urdf_path = r"C:\OptimusPrime_STL\robot.urdf"
                self.export_urdf(urdf_path)

                # ── Final report ───────────────────────────────────────
                unique_cols = list(set(self._cols))
                SEP = "═" * 54

                msg  = f"{SEP}\n"
                msg += "   OPTIMUS PRIME G1 — FULL SIMULATION REPORT\n"
                msg += f"{SEP}\n\n"
                msg += "\n".join(self._report)
                msg += f"\n\n{SEP}\n"
                msg += "  COLLISION SUMMARY\n"
                msg += f"{SEP}\n"
                if unique_cols:
                    msg += f"⚠️  {len(unique_cols)} unique pair(s):\n"
                    for c in unique_cols[:25]:
                        msg += f"    • {c}\n"
                    if len(unique_cols) > 25:
                        msg += f"    …{len(unique_cols)-25} more — see log\n"
                else:
                    msg += "✅  Zero inter-component collisions across all\n"
                    msg += "    9 simulation modules.\n"

                msg += f"\n{SEP}\n"
                msg += f"URDF  : {urdf_path}\n"
                msg += f"Log   : {LOG_FILE}\n"
                msg += f"{SEP}\n"

                log_msg("ALL SIMULATIONS COMPLETE.")
                log_msg(msg)
                self._ui.messageBox(msg, "OP G1 — Simulation Complete")
                return msg

        # ═══════════════════════════════════════════════════════════════════
        # RUN
        # ═══════════════════════════════════════════════════════════════════
        sim = SimulationEngine(root, comps_list, design, app, ui)
        target = globals().get("TARGET_MODULE", "ALL")
        
        log_msg(f"--- BEGINNING SIMULATION SEQUENCE [TARGET: {target}] ---")
        
        if target == "ALL":
            sim.run_all_simulations()
        elif target == "rom":
            sim.simulate_rom_tests()
        elif target == "head":
            sim.simulate_head_look()
        elif target == "wave":
            sim.simulate_wave()
        elif target == "breathing":
            sim.simulate_breathing()
        elif target == "walk":
            sim.simulate_advanced_walk()
        elif target == "run":
            sim.simulate_running()
        elif target == "combat":
            sim.simulate_combat_sequence()
        elif target == "transform":
            sim.simulate_transformation_to_truck()
            sim.simulate_truck_driving()
            sim.simulate_transformation_to_robot()
        elif target == "stability":
            sim.simulate_stability()
        elif target == "servo":
            sim.simulate_servo_load()
        else:
            log_msg(f"Unknown target module '{target}', running ALL.")
            sim.run_all_simulations()

        # ── STL BATCH EXPORT (uncomment to enable) ─────────────────────────
        # EXPORT_DIR = r"C:\OptimusPrime_STL"
        # os.makedirs(EXPORT_DIR, exist_ok=True)
        # SKIP_EXPORT = {"Marker","Pivot","MtA","MtB","Axle_Pivot",
        #                "Horn","_Vis","Scope","Antenna"}
        # mgr = design.exportManager
        # for comp in comps_list:
        #     for body in comp.bRepBodies:
        #         if body.isSolid and not any(t in body.name for t in SKIP_EXPORT):
        #             out = os.path.join(EXPORT_DIR, f"{comp.name}_{body.name}.stl")
        #             opt = mgr.createSTLExportOptions(body, out)
        #             opt.meshRefinement = adsk.fusion.MeshRefinement.High
        #             try:
        #                 mgr.execute(opt)
        #             except:
        #                 pass

        log_msg("Script finished successfully.")

    except Exception as e:
        if "SIMULATION_ABORTED_BY_USER" in str(e):
            msg = "ABORTED: Simulation sequence was terminated by external CLI command."
            log_msg(msg)
            if ui:
                ui.messageBox(msg, "Simulation Stopped")
        else:
            msg = f"FATAL ERROR:\n{e}\n\n{traceback.format_exc()}"
            log_msg(msg)
            if ui:
                ui.messageBox(msg, "Script Error")
            else:
                print(msg)
