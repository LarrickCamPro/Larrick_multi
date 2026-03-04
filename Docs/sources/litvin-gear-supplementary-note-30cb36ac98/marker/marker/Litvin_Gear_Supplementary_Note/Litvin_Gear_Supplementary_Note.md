# **Supplementary Technical Note**

Litvin Noncircular Conjugate Gear Pair – Requirements, Wear Distribution, and Piston-Motion Monitoring

> Prepared for: Max Holden Date: 2026-02-20

#### **1. Scope and System Context**

This note supplements the primary deep-research document by translating the project-specific discussion into engineering requirements, risk drivers, and measurable monitoring variables for a Litvin-derived noncircular, conjugate gear pair that drives an opposed-piston motion law. The focus is deliberately limited to the Litvin pair (planet-to-internal ring) and to the implications of: (i) forward-only torque, (ii) phaselocked tooth pairing, (iii) intentional distribution of contact across multiple ring teeth per planet tooth, and (iv) piston-motion tolerance and sensing as the primary "health metric."

#### **1.1 Operating envelope assumed in this supplement**

- Temperature: 100.000 °C to 300.000 °C (373.150 K to 573.150 K).
- Engine speed: up to 7000.000 rpm (116.667 rev/s, 733.038 rad/s).
- Average gear speed: approximately 14000.000 rpm (1466.077 rad/s) for two motion-law iterations per engine revolution.
- Torque direction: single direction only (no reversal).
- Kinematics: noncircular planets rolling/meshing against a noncircular internal ring surface; tooth pairing is synchronized (repeat contacts).
- Life target: 10000.000 operating hours at/near the envelope above (≈ 4.200×10^9 engine revolutions; ≈ 8.400×10^9 average gear revolutions for 2× iteration).
- Primary/secondary inertial forces: largely cancelled at the engine level by opposed-piston geometry; local mesh forces remain governed by gas load and mesh stiffness.

## **2. Litvin Pair: Functional Requirements and Design Constraints**

A Litvin-style design/generation workflow for noncircular gears requires conjugate tooth flanks that satisfy enveloping-based kinematic compatibility across a phase-varying pitch radius. For this application, the gear pair is a motion-law generator. As a result, the design objective is not only strength but also long-term stability of the phase-resolved transmission error (TE) that maps directly to piston position.

### **2.1 Conjugacy and continuity requirements (motion-law integrity)**

- Conjugate flanks must preserve continuous rolling/meshing across the full operating phase range; avoid phase windows with abrupt contact condition changes (e.g., contact ratio or curvature discontinuities).
- Mesh stiffness should vary smoothly with phase; discrete stiffness steps appear as piston-motion "kinks" even if average backlash remains small.