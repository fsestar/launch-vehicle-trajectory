# Launch Vehicle Trajectory and Performance Simulation

A from-scratch Python simulation of a two-stage launch vehicle: powered ascent with a
gravity turn, stage separation, a smart engine cutoff, a coast phase, a circularization
burn, and insertion into a stable low Earth orbit with a payload. The model uses a
spherical, Newtonian Earth in 3D, an altitude-dependent atmosphere, and a Monte Carlo
dispersion analysis of the final design.

![Full ascent-to-orbit trajectory](figures/launch_to_orbit.png)

## Project structure

| File | Purpose |
|---|---|
| `atmosphere.py` | Exponential air-density model |
| `orbit.py` | Orbital elements (semi-major axis, eccentricity, apogee, perigee, inclination) |
| `rocket.py` | The `Rocket` class: 3D flight, staging, cutoff, circularization |
| `monte_carlo.py` | Randomized dispersion study (200 flights, parallel) |
| `analyze_monte_carlo.py` | Statistics and the Monte Carlo figure |
| `plot_orbits.py` | Creates the figures in `figures/` |
| `tests/` | Unit and regression tests |

## Physics model

- **State vector:** `[x, y, z, vx, vy, vz, m, fuel]`, Earth-centered coordinates
- **Gravity:** Newtonian point-mass field, `a = -GM r / |r|^3`
- **Atmosphere:** exponential density `rho(h) = rho0 exp(-h/H)`, with `rho0 = 1.225 kg/m^3` and `H = 8500 m`
- **Drag:** `F_d = 1/2 rho v^2 Cd A`, opposing the velocity vector
- **Propulsion:** constant mass-flow thrust `F = m_dot v_e`, with staged mass bookkeeping and stage separation at burnout
- **Gravity turn:** a short vertical climb to 100 m, then a kick of `kick_angle` in a direction set by `launch_azimuth`. After the kick, thrust follows the velocity vector.
- **Orbit determination:** specific orbital energy and the angular-momentum vector give the semi-major axis, eccentricity, apogee, perigee, and inclination.
- **Engine cutoff:** thrust stops permanently once the predicted apogee reaches the target altitude.
- **Circularization:** when radial velocity changes sign at apogee, the speed is rescaled to the local circular speed `sqrt(GM/r)`.

## Validation

| Test | Expected | Result |
|---|---|---|
| 2D-equivalent case (latitude 0, azimuth 90) | apogee ≈ perigee ≈ 284.95 km | 284.953 km / 284.952 km |
| Inclination, launch from latitude 28.5°, azimuth 90° | 28.5° | 28.49999999999° |
| Inclination vs. launch azimuth (latitude 28.5°) | `cos(i) = cos(lat)·sin(az)` | matches to three decimals (see below) |
| Nominal flight, final design (m_dot = 7.80) | apogee ≈ 300 km | 300.1 km apogee, 299.8 km perigee |
| Final orbit eccentricity (final design, dt = 0.01) | ≈ 0 | ~9×10⁻⁶ |

**Inclination vs. azimuth** (latitude 28.5°): simulated values match the spherical-geometry formula.

| Azimuth (°) | 0 | 30 | 45 | 60 | 90 | 120 | 135 | 180 |
|---|---|---|---|---|---|---|---|---|
| Inclination (°) | 90.00 | 63.93 | 51.58 | 40.44 | 28.50 | 40.44 | 51.58 | 90.00 |

## Design and Monte Carlo analysis

Stage-1 mass flow rate was raised from 7.24 to 7.80 kg/s after a 200-flight dispersion study at 7.24 showed a sharp success cliff near `TWR ≈ 2.00`, and the nominal design sat only about one standard deviation above it.

Dispersions (Gaussian, 1σ): stage thrust 2 %, stage dry and fuel mass 2 %, drag coefficient 10 %, kick angle 0.2°. Success means circularized with perigee ≥ 150 km.

| Design (stage-1 m_dot) | Nominal TWR | Success | Final altitude (km) |
|---|---|---|---|
| 7.24 kg/s | 1.989 | 52.5 % | ~297 (successes), wide spread |
| 7.40 kg/s | 2.033 | 86.0 % | mostly ~300 |
| 7.60 kg/s | 2.087 | 99.0 % (2 crashes) | 300.1 ± 0.6 |
| **7.80 kg/s (final)** | **2.143** | **100 % (200 / 200)** | **300.3 ± 0.2** |

The 7.80 kg/s design has a Wilson 95 % confidence interval of 98.1 %–100 % for success. The two earlier crashes at 7.60 kg/s were reproduced with the same sampled inputs at both `dt = 0.05` and `dt = 0.01`, so they are physical outcomes near the TWR cliff, not numerical artifacts.

![Monte Carlo results at 7.80 kg/s](figures/mc_analysis.png)

## Limitations

- Earth's rotation is not modeled, so the eastward launch benefit is not included.
- Launch longitude is fixed at 0°; the east/north basis is undefined exactly at the poles.
- Engine cutoff and the circularization burn are idealized as instantaneous.
- Drag coefficient is constant (no Mach dependence); atmosphere is a single exponential, not the U.S. Standard Atmosphere 1976.
- No propellant cost is charged to the circularization burn.
- The Monte Carlo study uses `dt = 0.05` for speed. A convergence check on the final design (nominal flight, dt = 0.01 to 0.1) changes apogee by less than 0.5 km and perigee by less than 0.5 km, well within the design margin.
- The dispersion levels are assumed, not measured, so the absolute success rate depends on them.

## Running the code

Requires Python 3.9+. Install the dependencies once:

```bash
pip install -r requirements.txt
```

| Command | What it does |
|---|---|
| `python -m pytest tests -v` | Runs all unit and regression tests |
| `python monte_carlo.py` | Runs 200 randomized flights and writes `monte_carlo_results.csv` (about 2 minutes on a multi-core machine) |
| `python analyze_monte_carlo.py` | Prints statistics and saves `figures/mc_analysis.png` (needs the CSV from the previous step) |
| `python plot_orbits.py` | Saves `figures/launch_to_orbit.png` and `figures/orbit3d.png` |

## References

- U.S. Standard Atmosphere, 1976 (density and scale-height context)
- G. P. Sutton and O. Biblarz, *Rocket Propulsion Elements* (staging, thrust, specific impulse)
- R. H. Battin, *An Introduction to the Mathematics and Methods of Astrodynamics* (orbit elements and vis-viva)
- NASA Glenn Research Center, *Beginner's Guide to Rockets* (general reference)