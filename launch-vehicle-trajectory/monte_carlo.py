"""Monte Carlo dispersion analysis of the final launch vehicle design."""
import csv
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from orbit import R_EARTH, orbital_elements_3d
from rocket import Rocket

# ---------- settings ----------
N_FLIGHTS = 200
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(HERE, "monte_carlo_results.csv")     # written next to this file  # change this name for each new experiment
BASE_SEED = 12345                                              # fixed seed: results are reproducible
DT = 0.05                                                      # time step (0.01 is slower but more precise)
MAX_STEPS = 200_000
MIN_PERIGEE_M = 150_000.0                                      # success: circularized and perigee above this

# 1-sigma dispersions (Gaussian)
SIGMA_THRUST = 0.02
SIGMA_MASS = 0.02
SIGMA_CD = 0.10
SIGMA_KICK_DEG = 0.2

# nominal vehicle (final design)
NOMINAL_STAGES = [
    {"m_dry": 40.0, "fuel_mass": 760.0, "m_dot": 7.80, "v_exhaust": 2770.0},
    {"m_dry": 8.0,  "fuel_mass": 200.0, "m_dot": 0.9,  "v_exhaust": 3410.0},
]
NOMINAL_KICK_DEG = 8.0
NOMINAL_CD = 0.47
AREA = 0.01
KICK_ALTITUDE = 100.0
TARGET_APOGEE = 300_000
PAYLOAD_MASS = 20.0
LAUNCH_LATITUDE = 28.5
LAUNCH_AZIMUTH = 90.0

CSV_COLUMNS = ["flight", "f_thrust1", "f_thrust2", "f_dry1", "f_fuel1", "f_dry2",
               "f_fuel2", "f_cd", "kick_deg", "outcome", "apogee_km", "perigee_km",
               "eccentricity", "inclination", "steps", "runtime_s"]

NOMINAL_FACTORS = {"f_thrust1": 1.0, "f_thrust2": 1.0, "f_dry1": 1.0, "f_fuel1": 1.0,
                   "f_dry2": 1.0, "f_fuel2": 1.0, "f_cd": 1.0, "kick_deg": NOMINAL_KICK_DEG}


def build_stages(factors):
    """Stage list for one flight, with the sampled multipliers applied."""
    s1, s2 = NOMINAL_STAGES
    return [
        {"m_dry": s1["m_dry"] * factors["f_dry1"],
         "fuel_mass": s1["fuel_mass"] * factors["f_fuel1"],
         "m_dot": s1["m_dot"] * factors["f_thrust1"],
         "v_exhaust": s1["v_exhaust"]},
        {"m_dry": s2["m_dry"] * factors["f_dry2"],
         "fuel_mass": s2["fuel_mass"] * factors["f_fuel2"],
         "m_dot": s2["m_dot"] * factors["f_thrust2"],
         "v_exhaust": s2["v_exhaust"]},
    ]


def fly(factors):
    """Fly one vehicle with the given multipliers and classify the result."""
    t0 = time.time()
    rocket = Rocket(
        stages=build_stages(factors),
        kick_altitude=KICK_ALTITUDE,
        kick_angle=math.radians(factors["kick_deg"]),
        Cd=NOMINAL_CD * factors["f_cd"],
        A=AREA,
        target_apogee=TARGET_APOGEE,
        payload_mass=PAYLOAD_MASS,
        launch_latitude=LAUNCH_LATITUDE,
        launch_azimuth=LAUNCH_AZIMUTH,
    )
    traj = rocket.simulate(dt=DT, use_drag=True, max_steps=MAX_STEPS,
                           orbit_fraction=0.001, quiet=True)
    steps = len(traj)
    el = orbital_elements_3d(*traj[-1, :6])

    apogee_km = perigee_km = ecc = inc = float("nan")
    if rocket.circularized:
        apogee_km = el["apogee"] / 1000
        perigee_km = el["perigee"] / 1000
        ecc = el["eccentricity"]
        inc = el["inclination"]
        outcome = "success" if el["perigee"] >= MIN_PERIGEE_M else "low_orbit"
    elif steps > MAX_STEPS:
        outcome = "never_circularized"
    else:
        outcome = "crashed"

    return {"outcome": outcome, "apogee_km": apogee_km, "perigee_km": perigee_km,
            "eccentricity": ecc, "inclination": inc, "steps": steps,
            "runtime_s": time.time() - t0}


def sample_factors(i):
    """Random multipliers for flight i. Each flight has its own seed, so results are repeatable."""
    rng = np.random.default_rng(BASE_SEED + i)
    return {
        "f_thrust1": 1 + SIGMA_THRUST * rng.standard_normal(),
        "f_thrust2": 1 + SIGMA_THRUST * rng.standard_normal(),
        "f_dry1": 1 + SIGMA_MASS * rng.standard_normal(),
        "f_fuel1": 1 + SIGMA_MASS * rng.standard_normal(),
        "f_dry2": 1 + SIGMA_MASS * rng.standard_normal(),
        "f_fuel2": 1 + SIGMA_MASS * rng.standard_normal(),
        "f_cd": 1 + SIGMA_CD * rng.standard_normal(),
        "kick_deg": NOMINAL_KICK_DEG + SIGMA_KICK_DEG * rng.standard_normal(),
    }


def run_one_flight(i):
    """Run flight i and return one row for the CSV."""
    factors = sample_factors(i)
    try:
        result = fly(factors)
    except Exception as exc:   # one bad flight must not stop the whole batch
        result = {"outcome": "error:" + type(exc).__name__, "apogee_km": float("nan"),
                  "perigee_km": float("nan"), "eccentricity": float("nan"),
                  "inclination": float("nan"), "steps": 0, "runtime_s": 0.0}
    row = {"flight": i}
    row.update(factors)
    row.update(result)
    return row


def main(n_flights=N_FLIGHTS):
    nominal = fly(NOMINAL_FACTORS)
    print("nominal flight (no noise):", nominal["outcome"],
          f"| apogee={nominal['apogee_km']:.1f} km | perigee={nominal['perigee_km']:.1f} km")

    workers = max(1, (os.cpu_count() or 1) - 1)
    print(f"running {n_flights} flights on {workers} cores ...", flush=True)

    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for done, row in enumerate(executor.map(run_one_flight, range(n_flights)), start=1):
            rows.append(row)
            if done % 10 == 0 or done == n_flights:
                print(f"  {done}/{n_flights} done | {time.time() - t0:.0f} s", flush=True)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== summary ===")
    outcomes = {}
    for row in rows:
        outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
    for name, count in sorted(outcomes.items(), key=lambda kv: -kv[1]):
        print(f"  {name:20s} {count:4d}  ({100*count/len(rows):.1f}%)")

    good = [r for r in rows if r["outcome"] == "success"]
    if good:
        apo = np.array([r["apogee_km"] for r in good])
        print(f"\nsuccessful flights: orbit altitude mean={apo.mean():.1f} km | "
              f"std={apo.std():.1f} km | min={apo.min():.1f} | max={apo.max():.1f}")
    print(f"\nfull results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()