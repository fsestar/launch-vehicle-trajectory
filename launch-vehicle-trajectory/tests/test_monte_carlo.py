import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import monte_carlo as mc


def test_sampled_factors_are_reproducible():
    a = mc.sample_factors(7)
    b = mc.sample_factors(7)
    assert a == b


def test_different_flights_get_different_factors():
    assert mc.sample_factors(0) != mc.sample_factors(1)


def test_nominal_factors_give_nominal_stages():
    stages = mc.build_stages(mc.NOMINAL_FACTORS)
    for built, nominal in zip(stages, mc.NOMINAL_STAGES):
        for key in ("m_dry", "fuel_mass", "m_dot", "v_exhaust"):
            assert math.isclose(built[key], nominal[key], rel_tol=1e-12)


def test_nominal_flight_is_a_success_near_300_km():
    result = mc.fly(mc.NOMINAL_FACTORS)
    assert result["outcome"] == "success"
    assert abs(result["apogee_km"] - 300.14) < 0.5
    assert abs(result["perigee_km"] - 299.80) < 0.5


def test_outcome_column_only_has_known_labels():
    row = mc.run_one_flight(3)
    assert row["outcome"] in {"success", "crashed", "low_orbit", "never_circularized"}
    assert set(mc.CSV_COLUMNS) <= set(row.keys())


if __name__ == "__main__":
    test_sampled_factors_are_reproducible()
    test_different_flights_get_different_factors()
    test_nominal_factors_give_nominal_stages()
    test_nominal_flight_is_a_success_near_300_km()
    test_outcome_column_only_has_known_labels()
    print("all monte carlo tests passed")