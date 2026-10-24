import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from orbit import MU, R_EARTH, orbital_elements_3d


def circular_state(lat_deg, az_deg, altitude=285_000.0):
    """Position and velocity of a circular orbit at the given altitude.

    The vehicle starts at latitude lat_deg and moves with azimuth az_deg, using the same
    east/north basis as the rocket model (azimuth 90 = due east).
    """
    phi = math.radians(lat_deg)
    r = R_EARTH + altitude
    pos = np.array([r*math.cos(phi), 0.0, r*math.sin(phi)])
    radial = pos / r
    horiz = math.hypot(pos[0], pos[1])
    east = np.array([-pos[1]/horiz, pos[0]/horiz, 0.0])
    north = np.cross(radial, east)
    az = math.radians(az_deg)
    tangent = math.cos(az)*north + math.sin(az)*east
    v = math.sqrt(MU / r)
    vel = v * tangent
    return pos, vel


def test_circular_orbit_has_zero_eccentricity():
    pos, vel = circular_state(lat_deg=0.0, az_deg=90.0)
    el = orbital_elements_3d(*pos, *vel)
    assert el["closed"]
    assert el["eccentricity"] < 1e-6
    assert math.isclose(el["apogee"], el["perigee"], rel_tol=1e-9)


def test_equatorial_eastward_orbit_has_zero_inclination():
    pos, vel = circular_state(lat_deg=0.0, az_deg=90.0)
    el = orbital_elements_3d(*pos, *vel)
    assert el["inclination"] < 1e-6


def test_eastward_launch_from_28_5_has_inclination_28_5():
    pos, vel = circular_state(lat_deg=28.5, az_deg=90.0)
    el = orbital_elements_3d(*pos, *vel)
    assert math.isclose(el["inclination"], 28.5, abs_tol=1e-6)


def test_inclination_matches_spherical_geometry():
    # cos(i) = cos(latitude) * sin(azimuth), checked at azimuth 45 deg
    lat, az = 28.5, 45.0
    pos, vel = circular_state(lat_deg=lat, az_deg=az)
    el = orbital_elements_3d(*pos, *vel)
    expected = math.degrees(math.acos(math.cos(math.radians(lat)) * math.sin(math.radians(az))))
    assert math.isclose(el["inclination"], expected, abs_tol=1e-6)


def test_unbound_state_reports_open_orbit():
    pos = np.array([R_EARTH, 0.0, 0.0])
    vel = np.array([0.0, 12000.0, 0.0])   # above escape speed at the surface
    el = orbital_elements_3d(*pos, *vel)
    assert not el["closed"]
    assert el["apogee"] is None


if __name__ == "__main__":
    test_circular_orbit_has_zero_eccentricity()
    test_equatorial_eastward_orbit_has_zero_inclination()
    test_eastward_launch_from_28_5_has_inclination_28_5()
    test_inclination_matches_spherical_geometry()
    test_unbound_state_reports_open_orbit()
    print("all orbit tests passed")