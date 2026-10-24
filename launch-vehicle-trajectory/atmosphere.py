"""Atmospheric density model: exponential profile with a single scale height."""
import numpy as np

RHO_SEA_LEVEL = 1.225   # kg/m^3, air density at the surface
SCALE_HEIGHT = 8500.0   # m, altitude at which density falls by a factor of e


def air_density(altitude):
    """Air density (kg/m^3) at altitude (m) above the surface."""
    return RHO_SEA_LEVEL * np.exp(-altitude / SCALE_HEIGHT)