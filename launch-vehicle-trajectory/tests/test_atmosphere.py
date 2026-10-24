import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from atmosphere import RHO_SEA_LEVEL, SCALE_HEIGHT, air_density


def test_sea_level_density():
    assert math.isclose(air_density(0.0), 1.225, rel_tol=1e-12)


def test_density_drops_by_e_per_scale_height():
    ratio = air_density(SCALE_HEIGHT) / RHO_SEA_LEVEL
    assert math.isclose(ratio, math.exp(-1), rel_tol=1e-12)


def test_density_decreases_with_altitude():
    assert air_density(1_000.0) > air_density(10_000.0) > air_density(100_000.0)


if __name__ == "__main__":
    test_sea_level_density()
    test_density_drops_by_e_per_scale_height()
    test_density_decreases_with_altitude()
    print("all atmosphere tests passed")