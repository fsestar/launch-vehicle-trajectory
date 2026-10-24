"""Create the README figures: the ascent-to-orbit trajectory and the 3D azimuth comparison."""
import math
import os

import matplotlib.pyplot as plt
import numpy as np

from orbit import R_EARTH
from rocket import Rocket

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")

STAGES = [
    {"m_dry": 40.0, "fuel_mass": 760.0, "m_dot": 7.80, "v_exhaust": 2770.0},
    {"m_dry": 8.0,  "fuel_mass": 200.0, "m_dot": 0.9,  "v_exhaust": 3410.0},
]


def fly(azimuth_deg, dt):
    rocket = Rocket(stages=STAGES, kick_altitude=100.0, kick_angle=math.radians(8.0),
                    Cd=0.47, A=0.01, target_apogee=300_000, payload_mass=20.0,
                    launch_latitude=28.5, launch_azimuth=azimuth_deg)
    return rocket.simulate(dt=dt, use_drag=True, orbit_fraction=1.0, quiet=True)


def plot_launch_to_orbit(out_path):
    traj = fly(90.0, dt=0.01)
    t = np.linspace(0, 2*np.pi, 300)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(R_EARTH*np.cos(t)/1000, R_EARTH*np.sin(t)/1000, color="green", label="Earth surface")
    ax.plot(traj[:, 0]/1000, traj[:, 1]/1000, color="red", linewidth=1.5,
            label="Full trajectory (ascent + orbit)")
    ax.set_aspect("equal")
    ax.grid(True)
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_title("Launch to Orbit: Ascent, Coast, Circularization")
    ax.legend()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_orbit_3d(out_path):
    tr_east = fly(90.0, dt=0.05)
    tr_45 = fly(45.0, dt=0.05)
    R = R_EARTH / 1000
    fig = plt.figure(figsize=(9, 9))
    ax = fig.add_subplot(111, projection="3d")
    u = np.linspace(0, 2*np.pi, 40)
    v = np.linspace(0, np.pi, 20)
    ax.plot_wireframe(R*np.outer(np.cos(u), np.sin(v)), R*np.outer(np.sin(u), np.sin(v)),
                      R*np.outer(np.ones_like(u), np.cos(v)),
                      color="lightgreen", linewidth=0.4, alpha=0.6)
    t = np.linspace(0, 2*np.pi, 200)
    ax.plot(R*np.cos(t), R*np.sin(t), 0*t, color="green", linewidth=1.2, label="Equator")
    step = 20
    ax.plot(tr_east[::step, 0]/1000, tr_east[::step, 1]/1000, tr_east[::step, 2]/1000,
            color="red", linewidth=1.5, label="Azimuth 90 (i = 28.5°)")
    ax.plot(tr_45[::step, 0]/1000, tr_45[::step, 1]/1000, tr_45[::step, 2]/1000,
            color="blue", linewidth=1.5, label="Azimuth 45 (i = 51.6°)")
    ax.set_xlim(-7000, 7000)
    ax.set_ylim(-7000, 7000)
    ax.set_zlim(-7000, 7000)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_zlabel("Z (km)")
    ax.set_title("3D Orbits from Latitude 28.5: Effect of Launch Azimuth")
    ax.legend(loc="upper left", fontsize=8)
    ax.view_init(elev=20, azim=35)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    plot_launch_to_orbit(os.path.join(FIG_DIR, "launch_to_orbit.png"))
    print("saved figures/launch_to_orbit.png")
    plot_orbit_3d(os.path.join(FIG_DIR, "orbit3d.png"))
    print("saved figures/orbit3d.png")


if __name__ == "__main__":
    main()