# Supplementary Technical Report on Litvin Envelope-Generated Noncircular Internal-Ring Planet Gears for Piston Drive

## Executive summary

This supplement focuses strictly on **Litvin-style envelope generation** for **noncircular internal-ring + planet** conjugate pairs used as a piston-motion function generator under **100–300 °C**, **forward-only rotation**, **~14,000 RPM average planet spin (variable instantaneous)**, **high load**, **fixed tooth-pair meshing**, and a **10,000 h life target**. Key design constraints used verbatim from the program context include: piston stroke **50 mm** and allowable piston position error **±0.25 mm** (±0.5% stroke), plus motion-law tolerance on the order of **±5° crank** (requirement basis; crank definition unspecified).

The dominant takeaway is that longevity is limited less by “generic gear life” and more by **phase-local tribology + phase-local metrology**, because noncircular gears can have **phase-dependent tooth geometry** and (in your architecture) can experience **repeat-contact** of the same flank regions unless you intentionally create repetition/hunting. Noncircular teeth can have **independent baselines per tooth flank**, which makes phase-resolved accuracy control essential. citeturn37view0turn41view1

Actionable recommendations for a 1–2 engine program:

- **Build in “synthetic hunting” by design first, then by control**: Make the gear-ratio function periodic with **multiple identical repetitions per engine revolution** so each planet tooth can legally run on a *set* of ring teeth that are geometrically equivalent. This is consistent with the requirement that the gear-ratio function must be periodic for continuous motion transfer and with the idea of hunting-tooth combinations (classically used to avoid repeat tooth-on-tooth contact). citeturn37view0turn26view0turn26view2  
- **Target phase-local micro-geometry and load distribution** near the highest load regions (near TDC in your use case): prioritize **contact localization** (crowning) and **controlled backlash** concepts; these are standard levers to reduce transmission error sensitivity and avoid edge contact in planetary gear trains. citeturn18view1turn18view2  
- **Make λ (specific film thickness / composite roughness) a top-level control target**, not an afterthought: ISO micropitting guidance is explicitly built around *minimum local specific film thickness*; NASA testing also shows strong life trends versus specific film thickness (and large benefits to superfinishing). citeturn6view3turn10view3turn34view0turn10view2  
- **Adopt pressurized jet lubrication + active drainage/evacuation** rather than relying on dip/splash at your implied surface speeds: high pitch-line velocity drives scoring risk unless cooling is improved; standards and test literature emphasize keeping gears from dipping into oil at higher pitch-line velocities and using oil pans/drainage to reduce foaming/churning. citeturn10view0turn26view1turn26view2  
- **Use sensor-based observability to separate wear from thermal/elastic effects**: compute a phase-resolved “equivalent mesh phase error” from piston tracking and the local slope of the motion law, then estimate slow wear states with an observer that regresses out thermal expansion and compliance. (This is a design proposal; equations provided below are the recommended starting point.)

A minimal but high-yield validation stack is: **twin-disc scuffing/LOL screening** at relevant entrainment speeds and oil temperatures, **FZG/FVA-style micropitting screening**, then an **instrumented noncircular ring–planet rig** measuring transmission error (TE), oil/metal debris, and piston tracking error under duty-cycle acceleration. High-velocity twin-disc work demonstrates feasibility and highlights strong benefits of superfinished surfaces on time-to-failure under scuffing/LOL conditions. citeturn35view0turn10view2

## Litvin envelope-generation essentials for internal ring–planet pairs

Litvin’s core enabling idea for noncircular gears is that **noncircular tooth surfaces can be obtained as an envelope of a family of tool surfaces**, using *the same categories of tools used for circular gears* (rack cutters, hobs, shapers). citeturn6view0turn6view1 The conjugacy condition is enforced through an **imaginary rolling** construction: conjugated tooth shapes are provided by the imaginary rolling of the **tool centrode** over the **gear centrode**, with the required rolling realized by properly relating tool motion and gear motion during cutting. citeturn6view1

For your specific architecture (planet rolling on a **noncircular internal ring**), two implications matter most:

**Internal noncircular ring manufacturing is not a “rack-cutter by default” problem.** A practical noncircular gear reference notes that **only outer noncircular gears can be produced using a reference rack**, while **inner (internal) noncircular gears require a pinion-type cutter** (i.e., shaping / generating with an internal-capable cutter concept). citeturn6view2 In parallel, manufacturing literature explicitly emphasizes that noncircular hobbing has limitations including **inability to process internal gears** and higher risk of undercut in high-curvature, low-tooth-count cases—while **gear shaping** is presented as the universal alternative. citeturn16view0

**Periodicity is a first-principles constraint if you want repeatable sectors (your “repetition count” lever).** A manufacturing review states directly that to continuously transfer motion, the **gear ratio function must be periodic**, and its period must be compatible with each gear’s period through integers (a natural-numbers relationship). citeturn37view0 This is the theoretical door you need for the program concept of “more repetitions as pseudo tooth hunting”: design the ring/planet so that the motion law is implemented in **N identical repeats** around the ring, creating **N geometrically equivalent tooth sets**.

A further point that is easy to underestimate: in noncircular gears, **each tooth flank can have an independent baseline** (i.e., teeth are not necessarily interchangeable the way involute spur gear teeth often are in practice). citeturn37view0 This is why “synthetic hunting” must be engineered so that the alternate teeth a planet tooth may run on are genuinely equivalent in generated geometry (or equivalent within your tight motion-law tolerance).

## Manufacturing, tolerancing, and metrology implications for high-tolerance motion law

### Manufacturing routes that match Litvin envelope assumptions

A practical manufacturing synthesis for your ring gear is:

- **CNC gear shaping with pinion-type cutters** as the baseline for the internal ring, because shaping is explicitly positioned as able to overcome the “internal gear / concave pitch curve / undercut” limitations associated with hobbing in noncircular contexts. citeturn16view0turn6view2  
- **CNC-enabled free-form methods (including WEDM) as prototyping/backstop**, since modern CNC methods are described as enabling noncircular gears with free-form profiles and are also used for internal gears; WEDM is discussed as a viable method (with cost tradeoffs) for custom shapes and undercut sections. citeturn37view0

### What “tolerance” means when teeth can be phase-unique

Two standards-oriented cautions apply immediately:

- **ISO flank tolerance classes are for individual cylindrical involute gears and require experienced interpretation for performance**; the standard explicitly cautions against directly mapping “loose gear” tolerances to assembled performance. citeturn28view0  
- **Surface texture is treated separately** from many flank classification standards; ISO inspection practice for surface texture and contact pattern checking is a dedicated document and frames surface texture as influencing: transmission accuracy (noise/vibration), surface load carrying ability (pitting/scuffing/wear), and bending strength (root fillet condition). citeturn41view1turn28view1

For a high-tolerance piston motion law, the practical implication is: *you need phase-resolved acceptance*, not just an overall “gear grade.”

A robust approach is to define a **phase-indexed tolerance map** rather than a single tolerance number:

- For each motion-law phase bin, specify allowable limits on:  
  (i) **equivalent mesh phase error** derived from piston tracking (defined below), and  
  (ii) a small set of geometric descriptors measured on a CMM/gear metrology machine (profile/lead/pitch-like metrics mapped onto the local generated tooth geometry).

Because “each tooth flank has an independent baseline” is possible in noncircular gears, you should assume *by default* that the tooth-to-tooth repeatability problem is harder than a typical involute gear. citeturn37view0

### Surface finish targets that are evidence-backed

Three independent threads justify investing early in surface finish:

- A petroleum/industrial gear standard requires (for conventional gears) **loaded-face tooth surface finish measured along the pitch line** on the order of **0.8 µm Ra** for higher pitch-line-velocity regimes, and tighter ISO gear accuracy grades at higher pitch-line velocity; it also explicitly requires **hunting tooth combinations** and mandates avoiding oil dip at elevated pitch-line velocities. citeturn26view2turn26view1  
- NASA data on lubrication regimes and wear/fatigue emphasize the specific film thickness concept and show that **superfinished specimens (<0.1 µm Ra) exhibit significantly higher scuffing load capacity** than ~0.4 µm Ra ground specimens under high rolling/sliding conditions. citeturn10view2  
- Controlled experiments show micropitting is **extremely sensitive to surface roughness**, and that Λ ratio alone is an inadequate predictor if roughness amplitude changes; “low enough roughness” can strongly suppress severe micropitting even at low Λ in their test regime. citeturn34view0

Taken together, the most defensible recommendation is to treat **superfinishing (or at minimum optimized grinding lay + low Ra/Rz)** as a primary life lever—not cosmetic.

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["CNC gear shaping internal gear cutter","noncircular gear internal ring gear example","gear tooth contact pattern bluing inspection","gear oil jet lubrication nozzle gear mesh"],"num_per_query":1}

## Control levers to maximize longevity over 10,000 hours

This section prioritizes the levers you can realistically pull without compromising Litvin conjugacy.

### Geometric levers

**Repetition count (designed-in synthetic hunting).** Your program concept—“increase repetitions of the motion law per engine revolution to increase the number of ring teeth in a planet tooth’s set”—is best implemented by enforcing **periodic symmetry** in the gear-ratio function and in the generated geometry sector-to-sector.

A manufacturing review states that for continuous motion transfer the **gear ratio function must be periodic**, and the period must relate to each gear’s period through natural numbers. citeturn37view0 This gives a direct design recipe:

- Choose an integer repeat count **N_rep** such that the motion law for one engine revolution is represented as **N_rep identical pitch-curve sectors** around the internal ring (and compatibility holds for the planet).  
- Then, your controller can legally “hunt” by indexing contact from one repeat-sector to another while still meshing equivalent geometry.

This is conceptually aligned with the hunting-tooth objective defined in standards: avoiding repeat contact of the same tooth pairs by ensuring contact cycles through other teeth before repeating. citeturn26view0turn26view2

**Variable tooth density/size within a tooth set.** In noncircular gears, “variable tooth density” along the perimeter is often inherent because the pitch geometry varies with phase; moreover, noncircular teeth can be baseline-unique. citeturn37view0 However, **intentionally changing the effective tooth size/module by phase** is only safe if the mating member’s geometry is designed as the conjugate envelope for that exact variation. In practical terms, this drives you toward:

- explicitly modeling generated surfaces (Litvin-style) and  
- validating undercut/interference across all phases, which is flagged as a real issue in noncircular manufacturing discussions. citeturn16view0turn15search12

A pragmatic compromise (high leverage, lower risk) is to keep the generated tooth form “tool-consistent” but allow **phase-dependent micro-geometry** (small profile/lead modifications) and **phase-dependent structural stiffness** (below).

**Phase-dependent reinforcement near high-stress regions (near TDC).** This is one of your strongest leverage points because your load is not uniform by phase.

Without assuming your exact torque history (unspecified), a defensible strategy is to design near-TDC sectors to reduce contact stress and bending stress by:

- larger local rim thickness / web thickness,
- increased face width *where packaging allows* in the high-load arc, and/or
- local compliance shaping to reduce peak Hertz stress.

The reason to treat this as a first-class lever is that planetary trains are described as **extremely sensitive to alignment errors**, producing large transmission errors, edge contact, and uneven load distribution; recommended mitigations include localization of bearing contact and backlash control via surface modifications. citeturn18view1turn18view2

**Local micro-geometry (crowning, tip relief, controlled contact localization).** Two points matter for your system:

- You care about preserving a motion law; therefore you care about **transmission error (TE)** and phase noise.  
- You have forward-only rotation; therefore only **one flank’s micro-geometry is continuously load-critical** (you can exploit directional optimization, with the obvious caution that off-flank behavior still matters for assembly and transients).

The NASA planetary-gear analysis explicitly ties reduction of TE sensitivity and avoidance of edge contact to **localized bearing contact** and **controlled backlash via surface modifications**. citeturn18view1turn18view2  
Separately, ISO inspection guidance frames surface texture and related form (waviness/undulations) as a cause of transmission errors and gear noise in certain circumstances, reinforcing that micro-geometry and surface finish are coupled to dynamic behavior. citeturn41view1

### Materials, heat treatment, and coatings

Your temperature band (100–300 °C) strongly favors **carburized “hot-hard” gear steels** developed for aerospace/high-performance gearing, because hardness and rolling contact fatigue performance can degrade in conventional carburized steels as temperatures rise.

Evidence-backed candidates:

- **Carburized M50NiL / CBS-50 NiL family**: A NASA gear endurance report ran spur gears at **10,000 rpm** and **1.71 GPa maximum Hertz stress** and found **VIM-VAR M50NiL gears had 10% surface fatigue life 4.5× (vs VIM-VAR 9310) and 11.5× (vs VAR 9310)** under their test conditions. citeturn20view0 The CBS-50 NiL datasheet states it is a carburizing bearing and gear steel designed for **service temperatures up to 600 °F (316 °C)**. citeturn6view8  
- **Pyrowear 53**: Datasheet hot-hardness/tempering data show case hardness on the order of **~61 HRC at a 288 °C tempering temperature** (converted), indicating useful hardness retention near the top end of your temperature band (with the usual caveat: actual retained hardness depends on the final heat treat and time-at-temperature). citeturn6view7  
- **Ferrium C61/C64 class**: NASA reporting on advanced gear alloys provides hardness data for C61/C64 test gears (core hardness ~48–49 HRC in their test set) and shows mean endurance limits in single-tooth bending fatigue testing; it also notes scatter and the need to optimize residual stress profiles from carburization/peening. citeturn22view1turn22view0  

Nitrided steels remain useful, but treat them as a design branch rather than the default for the highest load/highest TE-stability demand, because your internal ring distortion control, case depth requirements, and contact stress regime are unspecified. Still, nitriding is explicitly described as a diffusion-based surface treatment carried out at elevated temperatures and forming nitride phases (fundamental mechanism), and tribology literature exists on micropitting performance of nitrided gears. citeturn42search1turn42search2

**Coatings** can be high leverage *if* you manage adhesion, residual stress, and rolling-contact fatigue interactions:

- **CrN (PVD/PACVD family)**: A major coating supplier lists **CrN** with **max service temperature ~700 °C** and hardness by nanoindentation around **18 ± 3 GPa** (application dependent). citeturn32view1turn31search0  
- **Hydrogen-free DLC / ta-C**: A ta‑C product sheet lists **max service temperature ~450 °C** with nano-hardness **35–55 GPa** and low friction coefficient in PoD testing. citeturn33view0  
- **Thermal stability of doped ta‑C**: Peer-reviewed work reports Si/SiC/ta‑C composite coatings stable up to **~600 °C** (context: air/oxidation/annealing effects), supporting the plausibility of high-temperature-capable DLC variants. citeturn31search2  

Given the 10,000 h target and tight motion-law tolerance, coatings should be screened through **rolling–sliding contact fatigue** tests (see test plan) before committing, because some coatings improve scuffing yet can reduce pitting resistance depending on system pairing (coating/substrate/oil). citeturn31search19

### Lubrication and oil-management levers

Your life target is strongly coupled to keeping the system out of severe boundary lubrication for most of the duty cycle.

- **Micropitting capacity is explicitly calculated from local specific film thickness.** ISO micropitting methodology is built on comparing *minimum* local specific film thickness in the contact area to a permissible value; micropitting can arrest, but if it progresses it can reduce tooth accuracy and raise dynamic loads/noise, and can develop into macropitting and other failures. citeturn6view3  
- **Scuffing risk is explicitly linked to temperature, sliding, roughness, material, and lubricant**, and a single momentary overload can initiate severe scuffing; ISO scuffing guidance models interfacial temperature as bulk + flash components and treats lubricant film breakdown as the initiating mechanism. citeturn10view4turn10view5  
- **Film thickness (λ) is not optional**: NASA gear life work defines specific film thickness (λ ratio) as film thickness divided by composite roughness; it notes that when specific film thickness is **<1**, bearing life is considerably reduced and gear life correlates positively with film thickness; it also provides regime cutoffs (boundary <0.4, mixed 0.4–1.0, full EHL >1.0). citeturn10view2turn10view3  
- **High speed makes cooling and oil delivery dominant**: oil-jet lubrication literature shows that as pitch line velocity increases at constant into-mesh lubrication, the limiting scoring load can be drastically reduced due to inadequate cooling; it also emphasizes radial jets with adequate pressure/flow as the most effective for cooling and temperature reduction. citeturn10view0  
- **Oil quantity and windage/churning matter at high speed**: experiments attribute high-speed gear power loss largely to windage and churning, and pressurized jet lubrication analyses often intentionally avoid sump contact to eliminate churning loss. citeturn13view0turn12view1  
- **Standards explicitly discourage oil dip at higher pitch-line velocities**: one industrial gear standard states that for pressurized oil systems with pitch-line velocities above ~15 m/s, casing should be designed so gears do not dip into oil, and above ~10 m/s an oil pan should be used to ensure rapid drainage and minimize foaming. citeturn26view1  

### Dynamic control levers

**Sun-phase micro-indexing / drift / dither** is plausible *if and only if* you stay inside the “legal conjugacy set.” The safest path is:

1) **Design** N_rep identical motion-law sectors (geometric equivalence), then  
2) use control to **move contact among equivalent sectors**.

A relevant planetary-gear NASA report emphasizes that backlash control and modifications of contacting surfaces can reduce TE and improve load distribution; while this is shown for circular-gear planetary drives, it supports the general use of controlled backlash as a systematic lever. citeturn18view1turn18view2

Separately, hunting tooth combinations are required in conventional high-speed gearing standards to prevent repeated tooth pairing; your programmable version is to create equivalence classes of teeth (via repetition design) and schedule shifts. citeturn26view2turn26view0

## Phase-resolved risk indices and equations for piston-error observability and control

This section provides a rigorous, implementation-oriented mapping from measured piston error to an equivalent mesh/phase error, which is the right currency for wear/backlash management and motion-law preservation.

### Definitions and assumptions

Let:

- θ = engine reference phase (crank angle or your internal phase variable). **Exact definition is unspecified**; treat it consistently in software.
- φ = the internally controlled “gear phase” that parameterizes the motion law (e.g., sun phase or an equivalent monotonically increasing phase variable). Exact choice is architecture-dependent.
- x_nom(θ) = nominal piston position profile (your target motion law), and x_meas(θ) is measured.
- e_x(θ) = x_meas(θ) − x_nom(θ). Requirement: |e_x(θ)| ≤ 0.25 mm over the full cycle.

Assume your measurement system can produce x_meas(θ) with sufficient resolution and time alignment (sensor design below).

### Equivalent phase error mapping

Linearize the motion law position around the nominal phase:

\[
x(\phi) \approx x(\phi_0) + \frac{dx}{d\phi}\bigg|_{\phi_0}\,(\phi-\phi_0)
\]

Define the **equivalent phase error** as:

\[
\Delta\phi_{\text{eq}}(\theta) \;\triangleq\; \frac{e_x(\theta)}{\left.\dfrac{dx}{d\phi}\right|_{\theta}}
\]

Then the **allowable phase error** implied by your piston tolerance becomes phase-dependent:

\[
|\Delta\phi_{\text{eq}}(\theta)| \;\le\; \Delta\phi_{\max}(\theta)
\quad\text{with}\quad
\Delta\phi_{\max}(\theta) \;\triangleq\; \frac{0.25\ \text{mm}}{\left|\left.\dfrac{dx}{d\phi}\right|_{\theta}\right|}
\]

This highlights an engineering reality that matches your intuition: near phases where \(dx/d\phi\) is small (often near TDC/BDC plateaus, depending on motion law), the allowable phase error becomes extremely tight.

### Phase-resolved risk indices (recommended)

Implement three normalized indices per phase bin:

1) **Motion-law integrity index**
\[
R_x(\theta) \;=\; \frac{|e_x(\theta)|}{0.25\ \text{mm}}
\]

2) **Transmission-equivalent index**
\[
R_{\phi}(\theta) \;=\; \frac{|\Delta\phi_{\text{eq}}(\theta)|}{\Delta\phi_{\max}(\theta)} \;=\; \frac{|e_x(\theta)|}{0.25\ \text{mm}}
\]
(Algebraically identical under the linear mapping above, but keep both in software because you will often change the mapping basis from θ to φ.)

3) **Tribology indices**
- Micropitting safety factor S_λ comparing minimum local λ to permissible λ (per ISO micropitting method). citeturn6view3turn10view3  
- Scuffing risk as a temperature margin using flash/integral temperature methods; the scuffing frameworks explicitly treat bulk+flash contact temperature and a critical threshold. citeturn10view4turn10view5  

Your control objective is to keep R_x ≤ 1 everywhere while driving tribology safety factors above thresholds.

### Observer structure to separate wear from thermal/elastic effects

Model the equivalent phase error as a sum of components:

\[
\Delta\phi_{\text{eq}}(\theta,t) =
\underbrace{\Delta\phi_{\text{wear}}(\theta,t)}_{\text{slow, accumulative}}
+
\underbrace{\Delta\phi_{\text{elas}}(\theta,t)}_{\text{load-dependent}}
+
\underbrace{\Delta\phi_{\text{therm}}(\theta,t)}_{\text{temperature-dependent}}
+
\eta(\theta,t)
\]

Recommended estimation structure for a first engine program:

- Represent **Δφ_wear(θ,t)** with a low-order periodic basis (e.g., Fourier up to K harmonics or spline knots aligned to repeat sectors).  
- Regress **Δφ_elas** against estimated torque/load proxies (e.g., cylinder pressure estimate, motor torque estimate, or measured gear tooth strain if available).  
- Regress **Δφ_therm** against measured temperatures (oil supply, casing, ring, planet bearing region).  
- Use a **Kalman filter or recursive least squares** with strong process noise separation (wear is random walk; thermal/elastic are driven).

The output of the estimator is a “wear map” over phase (and optionally over repeat-sector index) that can be used for controlled indexing.

## Sensor/control architecture for synthetic hunting while preserving motion law

### Recommended sensing stack

Because you already plan crank-like sensing on each gear, the key is turning signals into observability sufficient for phase-resolved wear.

Minimum viable stack:

- **Absolute or multi-tooth encoders** for: (i) sun phase, (ii) at least one planet spin phase (and ideally planet carrier/center phase), and (iii) an engine reference phase. (Exact gear count and which members are sensed are unspecified; choose the set that makes φ observable with minimal drift.)
- **Temperature sensors**: oil supply, oil return, ring housing, planet bearing region, plus at least one tooth-region proxy temperature if feasible.
- **Oil condition**: inline ferrous debris / particle count and differential temperature across the gear compartment (proxy for loss). (Standards and NASA work repeatedly highlight lubricant condition and contamination/aeration as scuffing contributors.) citeturn10view5turn10view0
- **Optional high value**: casing accelerometers for mesh-frequency content plus a TE proxy (even if indirect) tied to piston excitation.

### Control strategy that respects conjugacy

Implement synthetic hunting in two layers:

**Layer A: Discrete sector scheduling (design-enabled).** If you have N_rep identical sectors in the ring/planet geometry, allow the controller to select which sector index k is “active.” The commanded offset is then approximately:

\[
\delta\phi_{\text{sector}} = k\cdot \frac{2\pi}{N_{\text{rep}}}
\]

This is the lowest-risk version because it stays inside the designed equivalence class.

**Layer B: Micro-indexing within sector (test-gated).** Add a bounded small offset δφ_micro(t) within a sector to spread contact over adjacent teeth *only if* those teeth are designed to be equivalent (or if test shows acceptable conjugacy error). Bound δφ_micro using the piston tolerance through Δφ_max(θ).

**Dither for system ID**: If you choose identification dither, keep it extremely small and low frequency, and only in phases where \(dx/d\phi\) is large (where Δφ_max is generous). Gate dither off near TDC/BDC if slope is small.

### Control-loop block diagram

```mermaid
flowchart LR
  Ref[Nominal motion law x_nom(θ), φ_nom(θ)] --> Err[e_x(θ)=x_meas-x_nom]
  Enc[Gear/phase sensors] --> Est[State estimator: wear + thermal + elastic]
  Temps[Oil & structure temperatures] --> Est
  Load[Load proxy: torque/pressure] --> Est
  Est --> Map[Phase wear map Δφ_wear(θ)]
  Map --> Sel[Sector selector + micro-index scheduler]
  Sel --> Cmd[φ command: φ_nom + δφ_sector + δφ_micro]
  Cmd --> Act[Sun-phase actuator / indexing mechanism]
  Act --> Plant[Ring–planet noncircular mesh + piston linkage]
  Plant --> Enc
  Plant --> Piston[Piston position x_meas(θ)]
  Piston --> Err
  OilCtrl[Oil jets / drainage / evacuation control] --> Plant
  Est --> OilCtrl
```

## Oil troughs, evacuation control, and maintaining λ > 1 where possible

The oil system is not a support subsystem here—it is a primary life-control subsystem.

### Principles supported by standards and experiments

- Avoiding oil dip at higher pitch-line velocities reduces foaming and supports stable lubrication/cooling; an oil pan is explicitly recommended above certain pitch-line velocities for rapid drainage. citeturn26view1  
- At high speeds, scoring risk can rise rapidly if cooling is inadequate; radial jets with sufficient pressure/flow can reduce tooth temperatures and improve scoring/scuffing resistance. citeturn10view0  
- Windage and churning are major contributors to losses at high speed; eliminating sump contact eliminates major churning losses in jet-lubricated designs. citeturn13view0turn12view1  
- λ regime matters: full EHL is typically associated with λ > 1, while boundary/mixed regimes are lower; operating in boundary increases wear risk and surface distress. citeturn10view3turn6view3  

### Practical trough/evacuation guidance for your architecture

Because exact geometry (ring diameter, module, face width, helix angle, oil type/viscosity curve) is unspecified, the guidance below is framed as design rules and test-validated knobs.

**Trough sizing and placement (goal: predictable oil availability, minimal dip contact).**
- Use a **shallow, actively drained collection trough** located so that centrifugal throw-off from the mesh (and windage-driven oil mist) is captured before aeration dominates.  
- Design the cavity so the gears **do not dip** in steady state at your peak speed operating condition; implement a scavenge path sized to keep the free oil level below the gear path (per the standard’s intent at elevated pitch-line velocities). citeturn26view1  

**Variable bath vs active evacuation.**
- For low-speed or startup modes, a limited bath/splash may assist initial wetting, but high-speed operation should transition to **jet + rapid drainage** to reduce churning and heating. The rationale is directly supported by the speed dependence of churning/windage losses and by the explicit discouragement of dip at higher pitch-line velocities. citeturn13view0turn26view1  

**Jet strategy (cooling and film formation).**
- Include at least two controllable jet modes: **into-mesh** (film supply) and **radial/targeted cooling jets** (temperature control). Radial jets are described as highly effective when adequate pressure and flow are provided. citeturn10view0  
- Make jet control phase-aware if possible: increase flow/pressure in the high-load/high-slip phases (near TDC in your duty cycle) to preserve λ and suppress scuffing.

**Maintain λ > 1 where you can; otherwise manage mixed-lube deliberately.**
- Use λ estimation as a supervisory variable: compute minimum local λ per phase bin using film thickness estimation + measured roughness (and update as surfaces run-in). ISO micropitting guidance explicitly hinges on minimum local specific film thickness. citeturn6view3turn10view3  
- Surface finish is an equal partner with viscosity: roughness amplitude strongly drives micropitting even at fixed λ, so treat polishing/superfinishing as a lubricant “multiplier.” citeturn34view0turn10view2  

## Tables for materials/treatments and control levers

### Candidate materials and surface systems

All values below are **source-backed where cited**; otherwise marked as qualitative because key parameters (case depth, exact tempering, retained austenite target, shot peening, hardness spec) are **unspecified**.

| Option | What it is | Temperature suitability for 100–300 °C | Hardness / hot-hardness evidence | Toughness / fatigue evidence | Manufacturing risk | Notes for your use case |
|---|---|---|---|---|---|---|
| Carburized **M50NiL** (VIM‑VAR) | High hot-hardness carburizing steel | NASA testing context includes high performance and notes higher temperature capability; report cites capability ~589 K (316 °C) | Not a datasheet hardness table in-source; characterized as “high-hot-hardness” | Spur gear tests at 10,000 rpm and 1.71 GPa Hertz stress show 10% surface fatigue life **4.5× vs VIM‑VAR 9310** and **11.5× vs VAR 9310** (test-specific) | Moderate (heat treat + distortion control) | Strong candidate for your top-end temperature and life; still needs scuffing/micropitting screening at your oil temps. citeturn20view0 |
| **CBS‑50 NiL** | Carburizing bearing & gear steel (Carpenter) | Designed for service temps **up to 316 °C** | Datasheet focuses on behavior and tempering curves; service-temperature statement is explicit | Positioned for excellent rolling contact fatigue and high core toughness | Moderate | Very aligned to your 300 °C ceiling; still requires your specific contact stress and oil compatibility confirmation. citeturn6view8 |
| **Pyrowear 53** | Carburizing gear steel | Used as baseline in aerospace gear studies; datasheet includes hot hardness data | Case hardness shown about **61 HRC at 288 °C temper** (converted) | Used as comparator in advanced alloy studies; performance depends on process | Moderate | Good baseline; may be outperformed by NiL steels for hot-hardness life, but remains viable if distortion control and cost rule. citeturn6view7turn22view0 |
| **Ferrium C61/C64** | Advanced UHS gear alloys | Intended for high-performance gearing; pitting/scoring tests noted as WIP in source | Test gear hardness: core ~48–49 HRC; case depth reported | Single-tooth bending fatigue testing suggests improved mean endurance behavior but with scatter; residual stress optimization emphasized | Higher (process maturity, cost) | Consider if bending fatigue dominates and supply chain supports it; treat as “Phase 2 material” after baseline rig learnings. citeturn22view1turn22view0 |
| Nitrided steels | Nitrided diffusion layer on suitable base steel | Nitriding process occurs at elevated temperature; layers add wear resistance (general) | Mechanism described; specialized micropitting studies exist for nitrided gears | Micropitting performance studied in literature (details not extracted here) | Lower distortion risk; but contact fatigue interactions need validation | Useful branch if distortion control is paramount, but validate micropitting/scuffing in your oil/temp regime early. citeturn42search1turn42search2 |
| **CrN coating** on hardened steel | Hard CrN coating | Supplier lists max service temp ~700 °C | Hardness ~18 ± 3 GPa, service temp listed | RCF effects depend on system; not guaranteed | Moderate-high (adhesion, residual stress) | Candidate for scuffing margin; test for pitting/micropitting and coating fatigue. citeturn32view1turn31search0 |
| **ta‑C (DLC)** coating | Hydrogen-free DLC | Max service temp listed ~450 °C | Hardness 35–55 GPa listed | Can improve scuffing/abrasion but may affect pitting depending on stack | High (process control) | Use only with a test-gated pathway; attractive for low friction at high temp, but must prove rolling–sliding endurance. citeturn33view0turn31search19 |

### Control levers ranked by effectiveness, complexity, and risk

| Lever | Effectiveness (expected) | Complexity | Risk | Implementation notes |
|---|---:|---:|---:|---|
| Designed-in **N_rep motion-law repetitions** (sector equivalence) | Very high | Medium | Low–Medium | Grounded in periodic function requirement; enables legal index shifts among equivalent teeth. citeturn37view0 |
| **Jet lubrication + active drainage/evacuation** | Very high | Medium | Medium | Essential at high surface speed; supported by high-speed scoring/cooling evidence and oil-dip avoidance guidance. citeturn10view0turn26view1 |
| Surface finish upgrade (superfinish / controlled lay) | High | Medium | Low–Medium | Strongly supported by scuffing and micropitting sensitivity to roughness. citeturn10view2turn34view0 |
| Phase-dependent crowning/contact localization | High | Medium | Medium | Supported as an TE/edge-contact mitigation in planetary trains; must be phase-validated due to noncircular geometry. citeturn18view1 |
| Sensor-based **wear observer + sector scheduling** | High | High | Medium | Requires good time alignment and stable estimation; yields phase-resolved wear map. |
| Sun-phase micro-indexing within sector | Medium–High | High | Medium–High | Only after sector equivalence is proven; keep bounded by Δφ_max(θ). |
| Coatings (CrN / DLC variants) | Medium–High | Medium–High | High | Must pass rolling–sliding and contact fatigue screening; coating fatigue risk is nontrivial. citeturn31search19turn32view1 |
| Exotic alloys (UHS) | Medium | Medium | Medium | Use once failure modes are well characterized (bending vs surface fatigue). citeturn22view0 |

## Validation plan, accelerated testing, and metrics

### Failure-mode logic for this application

Your system is phase-local and forward-only, so the dominant risks are expected to be **surface distress (micropitting → pitting), scuffing, and phase-local wear** that perturbs the motion law—rather than symmetric wear.

ISO micropitting guidance explicitly warns that progressive micropitting reduces tooth accuracy and increases dynamic loads/noise, potentially progressing to macropitting and other failures. citeturn6view3  
ISO scuffing guidance stresses that a single momentary overload can initiate scuffing, driven by local film breakdown at high contact temperatures. citeturn10view4turn10view5

```mermaid
flowchart TD
  A[Phase-local operating point] --> B{Lubrication regime}
  B -->|λ > 1 (full EHL)| C[Low wear risk; monitor TE + debris]
  B -->|0.4 < λ ≤ 1 (mixed)| D[Micropitting / mild wear risk]
  B -->|λ ≤ 0.4 (boundary)| E[High wear + scuffing susceptibility]
  D --> F{Micropitting arrests?}
  F -->|Yes| G[Stable roughness/run-in; continue monitoring]
  F -->|No| H[Accuracy loss → higher dynamics]
  H --> I[Macropitting / spalling risk]
  E --> J{Contact temperature margin}
  J -->|High margin| K[Adhesive wear/scoring onset]
  J -->|Low margin| L[Scuffing event → rapid failure]
  C --> M{Bending stress near TDC}
  M -->|High| N[Root fatigue / tooth breakage risk]
  M -->|Moderate| O[OK]
```

### Test stack for a 1–2 engine program

**Stage 1: Tribology screening (fast feedback).**
- **High-velocity twin-disc tests** to screen scuffing/LOL susceptibility and quantify the benefit of candidate surface finishes/coatings. High-velocity twin-disc work demonstrates rigs capable of high entrainment velocity and high injection temperatures and reports strong TOF gains for superfinished surfaces under LOL. citeturn35view0  
- Add a **surface-finish matrix** (ground vs superfinished; different lay directions) because surface texture is explicitly tied to endurance and transmission accuracy considerations. citeturn41view1turn34view0  

**Metrics:** friction vs time, time-to-failure (TOF), post-test surface damage classification, roughness evolution (Ra/Rz + areal parameters if possible), and debris generation rate.

**Stage 2: Micropitting capacity and film-thickness validation.**
- Run **FZG/FVA-style micropitting tests** (or equivalent) to calibrate your λ models and surface finish targets. ISO micropitting guidance is explicitly based on minimum local specific film thickness and emphasizes the role of operating parameters and roughness. citeturn6view3turn10view3  

**Metrics:** micropitting area fraction by phase surrogate, profile deviation growth, oil condition and particulate counts.

**Stage 3: Instrumented noncircular ring–planet rig (architecture-specific).**
Build a rig that reproduces:
- variable instantaneous speed due to varying radius (your noncircular pitch geometry),
- realistic oil delivery/drainage,
- realistic thermal boundary conditions (heat soak to 300 °C if required),
- sensor timing and the control loop.

**Metrics (must-have):**
- piston tracking error e_x(θ) and derived Δφ_eq(θ),
- TE proxy / mesh-frequency vibration content,
- phase-resolved oil temperature and debris counts,
- backlash proxy (from Δφ_wear state) validated intermittently by direct measurement during teardown intervals.

**Stage 4: Engine test (short then extended).**
Start with a controlled **200–500 h** program to validate estimator stability, oil management, and early-life run-in behavior, then extend.

### Prioritized implementation plan

For the fastest path to a credible 10,000 h design:

1) **Lock the repetition strategy (N_rep) and prove sector equivalence** in CAD + manufacturing simulation; this is the foundation for safe synthetic hunting. citeturn37view0  
2) **Design the oil system around jet + drainage, not bath**, and instrument it for temperature/flow/foaming indicators; standards and high-speed literature strongly support avoiding dip contact at higher surface speeds. citeturn26view1turn10view0  
3) **Choose the baseline material as a hot-hard carburized steel** (CBS-50 NiL / M50NiL class) unless packaging or cost forbids; the evidence base for surface fatigue advantage and service temperature alignment is strong. citeturn6view8turn20view0  
4) **Set surface finish targets early** and validate them on twin-disc + micropitting tests; roughness sensitivity is too strong to treat late. citeturn10view2turn34view0  
5) **Implement the estimator + sector scheduler** and prove you can keep |e_x| ≤ 0.25 mm over thermal/load swings; only then add micro-indexing and/or coatings.

