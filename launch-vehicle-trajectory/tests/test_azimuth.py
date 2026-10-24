import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orbit import orbital_elements_3d
from rocket import Rocket

STAGES = [
    {"m_dry": 40.0, "fuel_mass": 760.0, "m_dot": 7.80, "v_exhaust": 2770.0},
    {"m_dry": 8.0,  "fuel_mass": 200.0, "m_dot": 0.9,  "v_exhaust": 3410.0},
]
LAUNCH_LATITUDE = 28.5
AZIMUTHS = [0, 30, 45, 60, 90, 120, 135, 180]


def simulated_inclination(azimuth_deg):
    rocket = Rocket(stages=STAGES, kick_altitude=100.0, kick_angle=math.radians(8.0),
                    Cd=0.47, A=0.01, target_apogee=300_000, payload_mass=20.0,
                    launch_latitude=LAUNCH_LATITUDE, launch_azimuth=azimuth_deg)
    traj = rocket.simulate(dt=0.05, use_drag=True, orbit_fraction=0.001, quiet=True)
    return orbital_elements_3d(*traj[-1, :6])["inclination"]


def expected_inclination(azimuth_deg):
    # spherical geometry: cos(i) = cos(latitude) * sin(azimuth)
    lat = math.radians(LAUNCH_LATITUDE)
    az = math.radians(azimuth_deg)
    return math.degrees(math.acos(math.cos(lat) * math.sin(az)))


def test_inclination_matches_spherical_geometry_for_all_azimuths():
    for az in AZIMUTHS:
        simulated = simulated_inclination(az)
        expected = expected_inclination(az)
        assert abs(simulated - expected) < 0.01, (
            f"azimuth {az}: simulated {simulated:.4f} deg, expected {expected:.4f} deg")


if __name__ == "__main__":
    test_inclination_matches_spherical_geometry_for_all_azimuths()
    print("all azimuth tests passed")