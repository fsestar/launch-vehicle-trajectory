"""Orbital mechanics: orbital elements from an Earth-centred state vector."""
import math

import numpy as np

G = 6.674e-11            # m^3 kg^-1 s^-2
M_EARTH = 5.972e24       # kg
R_EARTH = 6371000.0      # m
MU = G * M_EARTH         # gravitational parameter, m^3/s^2


def orbital_elements_3d(x, y, z, vx, vy, vz):
    """Orbital elements from position (m) and velocity (m/s) in Earth-centred coordinates.

    Returns a dict. For a bound orbit ("closed": True) it contains the semi-major axis,
    eccentricity, apogee and perigee (altitudes above the surface, m) and inclination (deg).
    For an unbound orbit ("closed": False) the orbital fields are None.
    """
    r = np.sqrt(x**2 + y**2 + z**2)
    v = np.sqrt(vx**2 + vy**2 + vz**2)
    epsilon = (v**2) / 2 - MU / r                 # specific orbital energy
    hx = y*vz - z*vy                              # specific angular momentum h = r x v
    hy = z*vx - x*vz
    hz = x*vy - y*vx
    h = np.sqrt(hx**2 + hy**2 + hz**2)

    if epsilon < 0:
        a = -MU / (2*epsilon)
        e = np.sqrt(max(0.0, 1 + (2*epsilon*h**2) / MU**2))
        inclination = math.degrees(math.acos(hz / h)) if h > 0 else 0.0
        return {"closed": True, "semi_major_axis": a, "eccentricity": e,
                "apogee": a*(1 + e) - R_EARTH, "perigee": a*(1 - e) - R_EARTH,
                "inclination": inclination}
    return {"closed": False, "semi_major_axis": None, "eccentricity": None,
            "apogee": None, "perigee": None, "inclination": None}