"""Rocket model: multi-stage vehicle flown in 3D from a launch site to orbit."""
import math

import numpy as np

from atmosphere import air_density
from orbit import MU, R_EARTH, orbital_elements_3d


class Rocket:
    """Two-stage (or more) vehicle with gravity turn, staging, smart cutoff and circularization.

    State vector (in order): [x, y, z, vx, vy, vz, m, stage_fuel_remaining].
    Coordinates are Earth-centred; z is the polar axis.
    """

    def __init__(self, stages, kick_altitude, kick_angle, Cd, A, target_apogee,
                 payload_mass, launch_latitude, launch_azimuth):
        self.stages = stages
        self.current_stage = 0
        self.kick_altitude = kick_altitude
        self.kick_angle = kick_angle
        self.Cd = Cd
        self.A = A
        self.target_apogee = target_apogee
        self.payload_mass = payload_mass
        self.launch_latitude = launch_latitude
        self.launch_azimuth = launch_azimuth

        self.engine_cutoff = False
        self.circularized = False
        self.prev_v_radial = None
        self.steps_since_circularized = 0

        total_mass = self.payload_mass
        for stage in self.stages:
            total_mass += stage["m_dry"] + stage["fuel_mass"]
        self.m = total_mass
        self.stage_fuel_remaining = self.stages[0]["fuel_mass"]

        phi = math.radians(self.launch_latitude)
        self.x = R_EARTH * math.cos(phi)
        self.y = 0.0
        self.z = R_EARTH * math.sin(phi)
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.kicked = False

    def speed(self):
        return np.sqrt(self.vx**2 + self.vy**2 + self.vz**2)

    def derivatives(self, use_drag=True):
        current = self.stages[self.current_stage]
        m_dot = current["m_dot"]
        v_exhaust = current["v_exhaust"]

        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        altitude = r - R_EARTH

        a_gravity_x = -(MU/r**3) * self.x
        a_gravity_y = -(MU/r**3) * self.y
        a_gravity_z = -(MU/r**3) * self.z

        if use_drag:
            rho = air_density(altitude)
            V = np.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
            F_drag = 0.5 * rho * V**2 * self.Cd * self.A
            a_drag_x = -(F_drag/self.m) * (self.vx/V) if V > 0 else 0
            a_drag_y = -(F_drag/self.m) * (self.vy/V) if V > 0 else 0
            a_drag_z = -(F_drag/self.m) * (self.vz/V) if V > 0 else 0
        else:
            a_drag_x = a_drag_y = a_drag_z = 0

        if not self.engine_cutoff:
            el = orbital_elements_3d(self.x, self.y, self.z, self.vx, self.vy, self.vz)
            if el["closed"] and el["apogee"] >= self.target_apogee:
                self.engine_cutoff = True

        if self.stage_fuel_remaining > 0 and not self.engine_cutoff:
            F_thrust = m_dot * v_exhaust
            dmdt = -m_dot
        else:
            F_thrust = 0
            dmdt = 0

        radial_x = self.x / r
        radial_y = self.y / r
        radial_z = self.z / r

        if altitude < self.kick_altitude:
            a_thrust_x = (F_thrust/self.m) * radial_x
            a_thrust_y = (F_thrust/self.m) * radial_y
            a_thrust_z = (F_thrust/self.m) * radial_z
        else:
            V = np.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
            a_thrust_x = (F_thrust/self.m) * (self.vx/V) if V > 0 else 0
            a_thrust_y = (F_thrust/self.m) * (self.vy/V) if V > 0 else 0
            a_thrust_z = (F_thrust/self.m) * (self.vz/V) if V > 0 else 0

        dvxdt = a_gravity_x + a_drag_x + a_thrust_x
        dvydt = a_gravity_y + a_drag_y + a_thrust_y
        dvzdt = a_gravity_z + a_drag_z + a_thrust_z

        return np.array([self.vx, self.vy, self.vz, dvxdt, dvydt, dvzdt, dmdt, dmdt])

    def get_state(self):
        return np.array([self.x, self.y, self.z, self.vx, self.vy, self.vz,
                         self.m, self.stage_fuel_remaining])

    def set_state(self, state):
        (self.x, self.y, self.z, self.vx, self.vy, self.vz,
         self.m, self.stage_fuel_remaining) = state

    def rk4_step(self, dt, use_drag=True):
        state = self.get_state()
        k1 = self.derivatives(use_drag)
        self.set_state(state + 0.5*dt*k1)
        k2 = self.derivatives(use_drag)
        self.set_state(state + 0.5*dt*k2)
        k3 = self.derivatives(use_drag)
        self.set_state(state + dt*k3)
        k4 = self.derivatives(use_drag)
        self.set_state(state + (dt/6)*(k1 + 2*k2 + 2*k3 + k4))

    def try_kick(self):
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        altitude = r - R_EARTH
        if not self.kicked and altitude >= self.kick_altitude:
            radial_x = self.x / r
            radial_y = self.y / r
            radial_z = self.z / r

            horiz = np.sqrt(self.x**2 + self.y**2)
            east_x = -self.y / horiz
            east_y = self.x / horiz
            east_z = 0.0

            north_x = radial_y*east_z - radial_z*east_y
            north_y = radial_z*east_x - radial_x*east_z
            north_z = radial_x*east_y - radial_y*east_x

            az = math.radians(self.launch_azimuth)
            horiz_x = math.cos(az)*north_x + math.sin(az)*east_x
            horiz_y = math.cos(az)*north_y + math.sin(az)*east_y
            horiz_z = math.cos(az)*north_z + math.sin(az)*east_z

            V = self.speed()
            c, s = math.cos(self.kick_angle), math.sin(self.kick_angle)
            self.vx = V * (c*radial_x + s*horiz_x)
            self.vy = V * (c*radial_y + s*horiz_y)
            self.vz = V * (c*radial_z + s*horiz_z)
            self.kicked = True

    def try_stage_separation(self):
        if self.stage_fuel_remaining <= 0 and self.current_stage < len(self.stages) - 1:
            self.m -= self.stages[self.current_stage]["m_dry"]
            self.current_stage += 1
            self.stage_fuel_remaining = self.stages[self.current_stage]["fuel_mass"]

    def try_circularization_burn(self):
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        v_radial = (self.x*self.vx + self.y*self.vy + self.z*self.vz) / r
        if self.engine_cutoff and not self.circularized and self.prev_v_radial is not None:
            if self.prev_v_radial > 0 and v_radial <= 0:
                scale = np.sqrt(MU / r) / self.speed()
                self.vx *= scale
                self.vy *= scale
                self.vz *= scale
                self.circularized = True
        self.prev_v_radial = v_radial

    def simulate(self, dt, use_drag=True, max_steps=950000,
                 stop_after_one_orbit=True, orbit_fraction=1.0, quiet=False):
        trajectory = [self.get_state()]
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        altitude = r - R_EARTH
        orbital_period = None

        while altitude >= 0:
            self.try_kick()
            self.try_stage_separation()
            self.try_circularization_burn()
            self.rk4_step(dt, use_drag)

            r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
            altitude = r - R_EARTH
            trajectory.append(self.get_state())

            if self.circularized and orbital_period is None:
                orbital_period = 2*np.pi*np.sqrt(r**3 / MU)

            if self.circularized and stop_after_one_orbit:
                self.steps_since_circularized += 1
                if self.steps_since_circularized * dt >= orbital_period * orbit_fraction:
                    break

            if len(trajectory) > max_steps:
                if not quiet:
                    print("warning: hit step cap")
                break

        return np.array(trajectory)