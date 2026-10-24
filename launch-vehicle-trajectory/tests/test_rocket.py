import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orbit import orbital_elements_3d
from rocket import Rocket

STAGES = [
    {"m_dry": 40.0, "fuel_mass": 760.0, "m_dot": 7.80, "v_exhaust": 2770.0},
    {"m_dry": 8.0,  "fuel_mass": 200.0, "m_dot": 0.9, "v_exhaust": 3410.0},
]


def fly_final_design(dt):
    rocket = Rocket(stages=STAGES, kick_altitude=100.0, kick_angle=math.radians(8.0),
                    Cd=0.47, A=0.01, target_apogee=300_000, payload_mass=20.0,
                    launch_latitude=28.5, launch_azimuth=90.0)
    traj = rocket.simulate(dt=dt, use_drag=True, orbit_fraction=0.001, quiet=True)
    return rocket, orbital_elements_3d(*traj[-1, :6])


def test_final_design_reaches_300_km_orbit_at_dt_0_05():
    rocket, el = fly_final_design(dt=0.05)
    assert rocket.circularized
    assert el["closed"]
    assert abs(el["apogee"] / 1000 - 300.143) < 0.01
    assert abs(el["perigee"] / 1000 - 299.803) < 0.01


def test_final_design_inclination_is_28_5():
    _, el = fly_final_design(dt=0.05)
    assert math.isclose(el["inclination"], 28.5, abs_tol=1e-3)


def test_final_design_orbit_is_nearly_circular():
    _, el = fly_final_design(dt=0.05)
    assert el["eccentricity"] < 1e-4


if __name__ == "__main__":
    test_final_design_reaches_300_km_orbit_at_dt_0_05()
    test_final_design_inclination_is_28_5()
    test_final_design_orbit_is_nearly_circular()
    print("all rocket tests passed")