# Launch Vehicle Trajectory and Performance Simulation — Decision Log

This log records the main technical decisions made during development, the reasons for them, the problems encountered, and what was learned. Decisions that were later changed are marked as **Superseded**, with a pointer to the decision that replaced them.

## Current status (final design)

| Item | Value |
|---|---|
| Stage-1 mass flow rate (m_dot) | 7.80 kg/s |
| Nominal liftoff TWR | 2.143 |
| Final orbit | apogee 300.1 km, perigee 299.8 km (dt = 0.01: 300.06 / 299.94 km) |
| Eccentricity | ~9×10⁻⁶ |
| Inclination (latitude 28.5°, azimuth 90°) | 28.5° |
| Monte Carlo (200 flights) | 200 / 200 success (Wilson 95 %: 98.1 %–100 %) |

---

## Session 1 — State vector and RK4 integrator

### Decision: state vector as a single numpy array `[x, y, vx, vy]`

**Problem:** the simulation needs one data structure that describes the full system state at every instant.

**Options considered:** separate variables (`x, y, vx, vy`) or one numpy array (state vector).

**Decision:** one numpy array.

**Rationale:** an array allows element-wise arithmetic on the whole state (addition, scalar multiplication), which RK4 needs. It also extends easily when mass and other variables are added.

**Outcome:** when mass was added in Session 3, `rk4_step` and `simulate` needed no changes.

### Decision: RK4 instead of the closed-form solution

**Problem:** the original code used closed-form projectile equations (`x = vx0·t`, `y = vy0·t − ½gt²`), which are only valid for pure gravity with no drag.

**Options considered:** keep the closed form; explicit Euler; RK4.

**Decision:** RK4.

**Rationale:** once velocity-dependent forces such as drag are added, no closed form exists. RK4 evaluates the derivative at four points per step and combines them with weights, giving much higher accuracy than Euler. It is a standard method for physical simulation.

**Outcome:** with drag off, the RK4 result matched the closed-form solution exactly. This validated the implementation.

---

## Session 2 — Aerodynamic drag

### Decision: quadratic drag with constant air density

> **Superseded in Session 7** (altitude-dependent density).

**Problem:** the trajectory needed a drag force to be realistic.

**Decision:** `F_drag = ½ · ρ · V² · Cd · A`, with a constant `ρ = 1.225 kg/m³` (sea-level density).

**Rationale:** the goal at this stage was a proof of concept. A constant density avoided unnecessary complexity.

**Outcome:** with drag, range dropped from about 880 m to about 610 m, the apogee was lower, and the path became asymmetric (steeper descent).

**Known limitation:** constant density is not realistic at high altitude. This was accepted for now.

### Decision: `use_drag` flag

**Problem:** comparing trajectories with and without drag required switching drag on and off without copying code.

**Decision:** a boolean parameter `use_drag=True` passed through `derivatives`, `rk4_step`, and `simulate`.

**Rationale:** avoids code duplication (DRY) and lets both cases run through one function.

---

## Session 3 — Thrust and variable mass

### Decision: add mass to the state vector

**Decision:** the state becomes `[x, y, vx, vy, m]`.

**Rationale:** a burning rocket loses mass continuously, and mass changes acceleration through F = ma.

### Decision: thrust from mass flow rate

> **Superseded in Session 6** (stage fuel is tracked separately from total mass).

**Decision:** `F_thrust = m_dot · v_exhaust`, with thrust cut off when `m ≤ m_dry`.

**Rationale:** this is the standard rocket propulsion relation. The cutoff prevents negative mass and unlimited thrust.

### Problem solved: unrealistic thrust-to-weight ratio

**Symptom:** the vehicle reached about 1870 m/s, and drag (which grows with V²) cancelled most of the thrust.

**Diagnosis:** the initial TWR was about 18, far above the 1.2–3 range of real rockets.

**Fix:** dry mass 20 → 200 kg, fuel 50 → 430 kg, giving TWR ≈ 2.

**Lesson:** check key physical ratios such as TWR before running long simulations.

---

## Session 4 — Gravity turn

### Decision: temporary "stateless" kick (local `kicked` flag inside `simulate`)

> **Superseded in Session 5** (state moved into the `Rocket` class).

**Problem:** the thrust must change from straight up to along the velocity vector. This needs a one-time kick, because the horizontal velocity starts at zero and has no direction to follow.

**Options considered:** store the kick state in a class, or use a local variable in `simulate`.

**Decision:** a local variable for now, to test the physics quickly.

**Known limitation:** the state is spread across several functions. This will not scale to staging, so a class is needed later.

### Experiment: effect of kick angle on the trajectory

**Method:** six kick angles from 2° to 30°, with the apogee and range recorded for each.

| Kick angle | Max altitude (m) | Final range (m) | Range / altitude |
|---|---|---|---|
| 2° | 97,955 | 71,009 | 0.72 |
| 5° | 70,079 | 130,492 | 1.86 |
| 10° | 27,167 | 145,147 | 5.34 |
| 15° | 8,070 | 96,673 | 11.98 |
| 20° | 3,424 | 40,425 | 11.81 |
| 30° | 1,099 | 11,870 | 10.80 |

**Insight:** there is a trade-off between apogee and range. Apogee falls steadily as the kick angle grows. Range rises to a peak near 10° (about 145 km) and then falls.

**Next step:** choose the kick angle from the mission goal (orbit versus maximum altitude), not as an arbitrary number.

---

## Session 5 — Refactoring into an object-oriented `Rocket` class

### Decision: rewrite the vehicle as a class

**Problem:** the kick state in Session 4 was spread across functions and did not scale.

**Decision:** a `Rocket` class holding all parameters and state (including `kicked`) as attributes.

**Rationale:** data and behaviour stay together in one object. This suits staging and multiple engines, which come later.

**Method:** the rewrite was done step by step: `__init__`, then a simple `speed` method, then `derivatives`, `get_state`/`set_state`, `rk4_step`, `try_kick`, and finally `simulate`.

**Validation:** the class version matched the Session 4 function version (max altitude 27,167 m, range 145,147 m).

**Bug found and fixed:** the drag coefficient was typed as `0.05` instead of `0.5`, reducing drag tenfold and inflating altitude and range. A direct comparison with the earlier results exposed it.

**Lesson:** a single small typo can significantly change physical results. A direct comparison with earlier results finds such bugs quickly.

---

## Session 6 — Staging

### Decision: model each stage as a dictionary, not a class

**Rationale:** each stage holds only a few constant values (`m_dry`, `fuel_mass`, `m_dot`, `v_exhaust`) and no complex behaviour. A dictionary is simpler and sufficient.

### Bug fixed: remaining stage fuel was not tracked separately from total mass

**Problem:** the condition `if m > m_dry` worked for a single stage, but with several stages `m` includes the upper stages, so it cannot detect the end of the current stage's fuel.

**Fix:** add `stage_fuel_remaining` to the state. It tracks only the current stage's fuel.

### Experiment: does staging always improve performance?

**Method:** two vehicles with the same initial mass (780 kg). One has two stages (stage 1: 16,250 N; stage 2: 6,000 N). The other has one stage carrying all the fuel with the stage-1 engine.

| | Two-stage | No staging (same mass) |
|---|---|---|
| Max altitude | 40,515 m | 41,868 m |
| Final range | 134,922 m | 165,199 m |

**Insight:** the unstaged vehicle did better. The stage-2 engine had a much lower thrust (6,000 N against 16,250 N). In this suborbital ballistic path, the weak acceleration after separation cancelled the benefit of the lower mass.

**Lesson:** the benefit of staging depends on matching each engine to its stage, not only on dropping dead weight. The result may differ for real orbital trajectories.

### Note: control variables when comparing experiments

The first staging comparison pitted a two-stage vehicle against a lighter single-stage vehicle. That changed two things at once (staging and initial mass), so it was misleading. A fair comparison keeps the initial mass the same and changes only the staging.

---

## Session 7 — Altitude-dependent air density

### Decision: exponential density model

**Problem:** the constant density (Session 2) is not valid for a vehicle reaching tens or hundreds of kilometres.

**Decision:** `ρ(h) = ρ₀ · exp(−h/H)`, with `H = 8500 m` (scale height of the atmosphere).

**Implementation:** `air_density(altitude)` as a standalone function, not a method, because it describes the environment, not the vehicle.

**Result:** apogee rose from 40,515 m to 139,310 m (about 3.4×), and range from 134,922 m to 1,432,591 m (about 10.6×).

**New limitation:** at ranges above 1,400 km and altitudes above the Kármán line (100 km), the flat-Earth assumption and constant downward gravity are no longer valid. The Earth is spherical, and at this scale the direction of gravity and the curvature of the surface matter.

**Next step:** move to a 3D model with Earth-centred coordinates and altitude-dependent gravity, using Newton's law of gravitation instead of a constant `g`.

---

## Session 8 — Spherical Earth model (Newtonian gravity)

### Decision: switch to Earth-centred coordinates

**Problem:** for ranges above 1,400 km, the flat-Earth assumption is wrong (an angular error of about 12.6° at that range).

**Decision:** express position as distance from Earth's centre, and replace constant `g` with Newtonian gravity: `a = −(GM/r³)·[x, y]`.

**Validation:** at the surface (`r = R_earth`), Newton's formula gives 9.8195 m/s², consistent with the old `g = 9.81` (difference below 0.1 %).

**Result:** apogee rose from 139,310 m to 200,928 m, and ground range (measured as arc length on the spherical surface) from 1,432,591 m to 2,053,264 m.

**Physical explanation:** gravity falls off with distance from Earth's centre (as 1/r²), so the vehicle at high altitude feels less pull. Earth's curvature also adds range, as it does for real ballistic missiles.

**Sanity check:** the circular orbital speed at apogee (about 7,788 m/s) is far above the vehicle's speed (a few hundred m/s), so the path is still suborbital, not an accidental orbit.

**Known limitation (fixed in Session 8, Fix below):** `try_kick` still treated "vertical" as the fixed Y axis.

### Fix: generalise `try_kick` to local radial and tangential vectors

**Problem:** the previous `try_kick` assumed "vertical" means the fixed Y axis, which is correct only near the launch point.

**Fix:** compute unit radial and tangential vectors from the instantaneous position.

**Validation:** because the kick happens near X ≈ 0, where the radial vector is essentially the Y axis, the results were identical (apogee 200,928 m, range 2,053,264 m).

---

## Session 9 — Optimising the kick angle

### Experiment 1: maximise apogee

**Method:** `scipy.optimize.minimize_scalar` over kick angles from 1° to 45°.

**Result:** the optimum sits at the lower boundary (kick ≈ 1°), with apogee 1,206,754 m.

**Insight:** this is a boundary solution. Maximum altitude alone is the wrong goal for an orbital vehicle: a nearly vertical launch has almost no horizontal speed and cannot reach orbit even at orbital altitude.

### Experiment 2: maximise tangential speed at 150 km

**Method:** the objective is the horizontal (tangential) speed at 150 km, which relates directly to the orbit insertion condition.

**Result:** the optimum moved to 11.3°, with tangential speed 4,398 m/s.

**Gap to orbit:** circular orbital speed at 150 km is 7,818 m/s. The vehicle reached about 56 % of it, so more Δv is needed (stronger engine, more stages, or more fuel).

**Consistency check:** 11.3° agrees with the hand-scan from Session 4 (best range near 10°).

---

## Session 10 — Realistic parameter scaling (Falcon 9 ratios)

### Decision: rescale parameters using Falcon 9 ratios

**Problem:** earlier parameters were arbitrary. For example, the stage-2 dry-to-fuel ratio was 50 %, against about 3.6 % for Falcon 9.

**Method:** take key ratios from public Falcon 9 data (dry mass per stage, initial TWR, stage-2 to stage-1 thrust ratio), apply them to a smaller vehicle, and keep the chemical exhaust velocities unchanged (they do not depend on scale).

**New parameters:**
- Stage 1: m_dry = 40 kg, fuel = 760 kg, m_dot = 5.0 kg/s, v_exhaust = 2770 m/s
- Stage 2: m_dry = 8 kg, fuel = 200 kg, m_dot = 0.5 kg/s, v_exhaust = 3410 m/s

**Validation:** calculated burn times (152 s and 401 s) were close to Falcon 9's (about 162 s and 397 s).

### Bug: stage-2 TWR below 1 after separation

**Problem:** copying the Falcon 9 stage thrust ratio gave a stage-2 TWR of 0.84, so the stage could not lift its own weight.

**Root cause:** Falcon 9's second stage ignites at high altitude and horizontal speed, where a low TWR is acceptable. This vehicle's kick happens low in the atmosphere.

**Fix:** stage-2 m_dot raised from 0.5 to 0.9 kg/s (TWR about 1.5).

**Lesson:** copying a real vehicle's ratios without matching the flight scenario can give invalid results.

### Bug investigation: TWR 1.4 vehicle fell back before stage separation

**Symptom:** the optimiser gave the same result for every stage-2 m_dot, because the vehicle never reached stage 2.

**Diagnosis:** with TWR about 1.4 the vehicle accelerated slowly, its trajectory bent over early, and it fell back before stage 1 burned out.

**Fix:** stage-1 m_dot raised from 5.0 to 7.1 kg/s (TWR about 2.0).

### Milestone: ideal Δv exceeds escape velocity

**Finding:** using the Tsiolkovsky equation, the two-stage ideal Δv is about 14,994 m/s (stage 1: 3,884; stage 2: 11,110). Earth's escape velocity is about 11,056 m/s.

**Caveat:** this is the ideal figure. Simulated results depend on the flight path, and the apparent escape speed of 14,220 m/s seen in one run came from a sensitive point on the optimum. See the investigation below.

**Result:** the vehicle no longer returned to Earth, because the simulation's ground-return condition does not hold for a vehicle that reaches orbital energy.

**New limitation:** the loop condition `while altitude ≥ 0` assumes the vehicle always falls back. This does not hold for high-Δv vehicles.

### Bug investigation: optimiser curve and printed result disagreed

**Symptom:** `minimize_scalar` reported 14,114 m/s at 8.086°, but the plotted curve (30 points between 1° and 60°) peaked at about 4,850 m/s.

**Diagnosis:** a fine scan (0.05° steps) between 7.5° and 8.7° showed a sharp cliff. Between 7.9° and 8.0°, tangential speed jumped from about 10,500 to 14,100 m/s, and it stayed near that value until about 8.4°. A coarse 2° grid missed this narrow, important region.

**Fix:** dense sampling (40 points) in the 7°–9° band using `np.concatenate`.

**Lesson:** numerical optimisers can find narrow features that coarse plots miss. Always confirm an optimum with dense sampling around it.

---

## Session 11 — Engine cutoff via Vis-Viva

### Decision: cut thrust when the Vis-Viva target speed is reached

> **Superseded in Session 12** (orbital elements from energy and angular momentum).

**Approach:** compute `target_speed` from the current distance and a target apogee using Vis-Viva, and cut thrust when the instantaneous speed reached it.

**Implementation:** `target_apogee` added to `__init__`, and `target_speed` recalculated in every call to `derivatives`.

### Bug investigation: apogee overshoot (Vis-Viva ignores direction)

**Symptom:** with a target apogee of 300 km, the vehicle reached 4 to 8.7 million metres for kick angles of 3°, 5°, and 8°. At 10° it fell before reaching the target speed.

**Diagnosis:** Vis-Viva assumes the velocity is purely tangential at cutoff. The gravity turn leaves a significant radial component, which produces an orbit with much higher eccentricity than predicted.

**Root cause:** Vis-Viva constrains only the speed magnitude (orbital energy), not its direction. Predicting apogee needs the angular momentum as well.

**Correct approach (real-world pattern):** (1) burn until enough Δv is reached; (2) let the vehicle coast to its natural apogee, where radial speed becomes zero; (3) circularise there with a Vis-Viva burn.

---

## Session 12 — Orbital elements tool

### Decision: `orbital_elements()` from specific energy ε and angular momentum h

**Implementation:** the function takes x, y, vx, vy and returns the semi-major axis, eccentricity, apogee, and perigee.

### Bug fixed: detection of fuel depletion

**Problem:** `stage_fuel_remaining ≤ 0` detected the moment of stage-1 separation, not the end of all fuel, because the value is refilled after separation.

**Fix:** use the minimum total mass, which decreases monotonically.

### Fix: one-time engine cutoff flag (anti-chattering)

**Problem:** checking "apogee ≥ target" at every step made the engine switch on and off repeatedly, because drag and gravity lowered the predicted apogee back below the target during brief coasts.

**Fix:** a flag `engine_cutoff` that, once set to True, stays True. The engine never restarts.

**Result:** with kick = 8°, apogee was 300,086 m (target 300,000 m), and perigee improved from about −6,000,000 m to −149,130 m.

**Milestone:** first time the vehicle reached the target apogee on a physically sensible ellipse.

---

## Session 13 — Coast phase and circularisation burn

### Decision: detect apogee by a sign change in radial velocity

**Implementation:** track `v_radial = (x·vx + y·vy)/r` at each step. A change from positive to negative means apogee has been passed.

### Decision: model the circularisation burn as an instantaneous speed change

**Implementation:** at apogee (v_radial ≈ 0), rescale the velocity to the circular speed `v_circular = √(GM/r)`.

**Simplification acknowledged:** the burn has no duration and no propellant cost, similar to the instantaneous initial kick.

### Milestone: first stable, nearly circular orbit

**Result** (kick = 8°, target apogee 300 km, stage-1 m_dot = 7.10 kg/s at that stage of development): eccentricity 4.7×10⁻⁸, apogee 300,044 m, perigee 300,043 m.

**Significance:** this completes the launch-to-orbit sequence: ascent, gravity turn, staging, realistic atmosphere and gravity, smart cutoff, coast, and circularisation.

---

## Session 14 — Payload mass

### Decision: payload is a constant mass, not a decreasing one

**Rationale:** unlike propellant (which burns continuously) or stage dry mass (which drops at separation), the payload stays with the vehicle from launch to orbit.

### Finding: 2 % extra mass breaks the 8° kick

**Result:** adding 20 kg (about 2 % of total mass) lowered the liftoff TWR from 1.989 to 1.950, and the 8° kick no longer produced an orbit. This confirms high sensitivity near the optimum (the cliff from Session 10).

### Fix: stage-1 m_dot raised from 7.10 to 7.24 kg/s

**Result:** a stable, nearly circular orbit at 284,952 m was restored with a real payload.

### Validation: plot of the post-circularisation orbit only

**Method:** find the circularisation moment as the largest jump in speed, then plot only the trajectory after it.

**Result:** the post-circularisation path alone is a smooth, closed circle, confirming the numerical eccentricity visually.

---

## Session 15 — Introduction to 3D orbital mechanics

**Concepts introduced (not yet implemented):**
- State vector extended to 8 elements: `[x, y, z, vx, vy, vz, m, fuel]`.
- 3D gravity: the 2D vector formula with a z component added.
- Inclination: the angle between the orbit plane and the equatorial plane.
- Physical constraint: the lowest inclination reachable without a plane-change manoeuvre equals the launch latitude. This is why launch sites lie near the equator (Cape Canaveral, Baikonur).
- Azimuth: the horizontal direction of the kick (north, south, east, west). Together with the kick angle it fixes the 3D kick direction.
- Initial position from latitude and longitude: `x₀ = R cos φ cos λ`, `y₀ = R cos φ sin λ`, `z₀ = R sin φ`.

---

## Session 16 — 3D implementation

### Decision: extend the model to 3D with an 8-element vector state

**Implementation:** state `[x, y, z, vx, vy, vz, m, fuel]`; new parameters `launch_latitude` and `launch_azimuth`; 3D gravity, drag, and thrust; `try_kick` using local radial, east, and north vectors with azimuth; `orbital_elements_3d` using the cross-product angular momentum and returning inclination.

**Validation:**
- Latitude 0 reproduced the 2D result exactly (apogee ≈ perigee ≈ 284,952 m).
- An eastward launch from latitude 28.5° gave inclination 28.5°, matching the minimum-inclination rule.

**Known limitations:** Earth's rotation is not modelled; launch longitude is fixed at 0°; the east/north basis is undefined exactly at the poles.

### Experiment: effect of launch azimuth on inclination (latitude 28.5°)

**Method:** launches at azimuths 0° to 180°, comparing simulated inclination with `cos(i) = cos(lat)·sin(az)`.

**Result:** agreement to three decimals in all eight cases. Azimuth 90° gives the lowest inclination (28.5°). Azimuth 45° gives 51.58°, close to the ISS. Orbital altitude was the same in every case.

**Limitation:** the Earth's rotation, which would help an eastward launch, is not modelled.

---

## Session 17 — Monte Carlo dispersion analysis

### Setup

200 random flights, `dt = 0.05`, a fixed seed per flight for reproducibility, and 7 parallel workers.

Gaussian noise (1σ): stage thrust 2 %, stage dry and fuel mass 2 %, drag coefficient 10 %, kick angle 0.2°. Success means circularised with perigee ≥ 150 km.

### Pilot study at stage-1 m_dot = 7.24 kg/s

**Result:** 105 successes (52.5 %), 94 crashes (47.0 %), 1 low orbit. Successful orbits: mean 296.8 km, standard deviation 13.7 km, with a tail down to 204 km.

**Findings:**
- Liftoff TWR is the dominant factor (effect size d = +2.04). Stage-1 thrust (+1.31), stage-1 fuel (−0.78), stage-2 fuel (−0.52), and kick angle (−0.47) follow.
- The success rate has a sharp cliff against TWR: it goes from 0 % to 100 % between about 1.95 and 2.02. The nominal TWR of 1.989 sits on the steep part.
- Ballistic failures come from low TWR, not from orbit accuracy: a flight that lifts off correctly reaches a precise orbit.

**Prediction error (recorded deliberately):** I predicted more than 95 % at 7.40 kg/s, based on the nominal point only. The actual result was 86 %. I had not accounted for how far the noise spreads TWR around its nominal value. **Lesson:** estimate the success rate from the distribution of TWR (nominal ± dispersion), not from the nominal point alone.

### Result at 7.40 kg/s

**Result:** 172 of 200 successes (86.0 %; 95 % interval 81.2 %–90.8 %). Nominal TWR 2.033, only about 1.5 % above the cliff, which is less than one standard deviation of TWR dispersion (about ±2.5 %). A 100 % success rate was therefore not reachable at this margin.

### Result at 7.60 kg/s

**Result:** 198 of 200 successes (99 %; Wilson 95 % interval 96.4 %–99.6 %). Nominal TWR 2.087. Both failures had TWR of about 1.96 and 2.00. The Wald interval was dropped, because it is not valid for rates near 100 %.

**Check of the two failures:** I re-ran both with the same sampled inputs at `dt = 0.05` and `dt = 0.01`. Both crashed each time, with identical step counts at `dt = 0.05`. Both had stage-1 fuel 3.5 % and 7 % above nominal and thrust 1–2 % below nominal. The crashes are physical, not numerical.

### Result at 7.80 kg/s (final design)

**Result:** 200 of 200 successes (100 %; Wilson 95 % interval 98.1 %–100 %). Nominal TWR 2.143, about 2.5 standard deviations above the cliff. Final altitude 300.3 ± 0.2 km (range 299.9–301.0 km).

**Comparison with 7.60:** the success-rate difference is not statistically significant, but 7.80 has no failures and a tighter altitude spread.

**Decision:** adopt 7.80 kg/s as the reference design.

**Limitation:** with n = 200 and zero failures, the success rate has only a lower bound (about 98 %).

### Convergence check of the final design (dt)

**Method:** nominal flight at `dt` = 0.01, 0.02, 0.05, and 0.1.

| dt | Apogee (km) | Perigee (km) | Eccentricity |
|---|---|---|---|
| 0.01 (reference) | 300.064 | 299.942 | 9.16e-6 |
| 0.02 | 300.104 | 299.880 | 1.68e-5 |
| 0.05 (Monte Carlo) | 300.143 | 299.803 | 2.55e-5 |
| 0.1 | 300.479 | 299.527 | 7.14e-5 |

**Conclusion:** the difference between `dt = 0.01` and `dt = 0.05` is below 0.2 km. `dt = 0.05` is valid for the Monte Carlo study.

### Open items

- Convergence check for borderline flights (close to the TWR cliff) at `dt = 0.01`. Low priority, because the final design has essentially no such flights.
- Earth's rotation, a more realistic atmosphere (U.S. Standard Atmosphere 1976), and propellant cost for the circularisation burn are listed as limitations in the README.