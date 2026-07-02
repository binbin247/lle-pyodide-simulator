import json
import math

import numpy as np


DEFAULT_DT = 8e-4
MAX_REQUESTED_DT = 5e-3
MIN_DT = 1e-12
ALIASING_SAFETY = 0.5
DEFAULT_STOKES_DT = 5e-5
DEFAULT_MULTICOLOR_DT = 2e-5
DEFAULT_RAMAN_DT = 5e-5
LIGHT_SPEED = 299792458.0


class LLESolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260701)
        self.n = 512
        self.step = 0
        self.t = 0.0
        self.params = {
            "alpha": 10.0,
            "pump": 3.94,
            "d2": -0.0444,
            "d3": 0.0,
            "d4": 0.0,
            "tauR": 0.0,
            "dt": DEFAULT_DT,
            "stepsPerFrame": 50,
        }
        self.mu = self._make_mu(self.n)
        self.psi = self._initial_state(self.n)
        self._linear = None
        self._refresh_linear()

    def configure(self, config):
        n = int(config["n"])
        reset = bool(config.get("reset", False))
        self.params = self._clean_params(config["params"])
        if reset or n != self.n:
            self.n = n
            self.mu = self._make_mu(n)
            self.psi = self._initial_state(n)
            self.step = 0
            self.t = 0.0
        self._refresh_linear()
        return {"ok": True}

    def update_params(self, params):
        self.params = self._clean_params(params)
        self._refresh_linear()
        return {"ok": True}

    def run_steps(self):
        self.advance_steps()
        return self.snapshot()

    def advance_steps(self):
        steps = int(self.params["stepsPerFrame"])
        for _ in range(max(1, steps)):
            self._step_once()

    def snapshot(self):
        intensity = np.abs(self.psi) ** 2
        spectrum = np.fft.fftshift(np.fft.fft(self.psi)) / self.n
        spectrum_db = 20.0 * np.log10(np.abs(spectrum) + 1e-12)
        history_row = 10.0 * np.log10(intensity + 1e-12)
        energy = float(np.mean(intensity))
        peak = float(np.max(intensity))
        return {
            "modelId": "standard",
            "step": int(self.step),
            "t": float(self.t),
            "intensity": intensity.astype(np.float32),
            "spectrumDb": spectrum_db.astype(np.float32),
            "historyRow": history_row.astype(np.float32),
            "energy": energy,
            "peak": peak,
            "normalizedParams": dict(self.params),
        }

    def export_state(self):
        return {
            "modelId": "standard",
            "n": self.n,
            "step": int(self.step),
            "t": float(self.t),
            "params": dict(self.params),
            "psi_real": self.psi.real.tolist(),
            "psi_imag": self.psi.imag.tolist(),
        }

    def _step_once(self):
        dt = self.params["dt"]
        abs2 = np.abs(self.psi) ** 2
        tau_r = self.params["tauR"]
        if tau_r != 0.0:
            d_abs2 = np.fft.ifft(1j * self.mu * np.fft.fft(abs2)).real
            self.psi *= np.exp(1j * (abs2 + tau_r * d_abs2) * dt)
        else:
            self.psi *= np.exp(1j * abs2 * dt)

        psi_freq = np.fft.fft(self.psi)
        psi_freq *= self._linear
        self.psi = np.fft.ifft(psi_freq)
        self.psi += self.params["pump"] * dt

        if not np.all(np.isfinite(self.psi)):
            raise FloatingPointError(
                "LLE state contains NaN or Inf; reduce pump or dispersion range."
            )

        self.step += 1
        self.t += dt

    def _refresh_linear(self):
        self._refresh_adaptive_dt()
        p = self.params
        dint = self._dint()
        linear = -(1.0 + 1j * p["alpha"]) + 1j * dint
        self._linear = np.exp(linear * p["dt"])

    def _refresh_adaptive_dt(self):
        max_abs_dint = float(np.max(np.abs(self._dint())))
        requested_dt = self.params["dt"]
        if max_abs_dint > 0.0:
            alias_safe_dt = ALIASING_SAFETY * math.pi / max_abs_dint
            self.params["dt"] = max(MIN_DT, min(requested_dt, alias_safe_dt))
        else:
            self.params["dt"] = requested_dt

    def _dint(self):
        p = self.params
        return (
            p["d2"] * self.mu**2 / 2.0
            + p["d3"] * self.mu**3 / 6.0
            + p["d4"] * self.mu**4 / 24.0
        )

    def _initial_state(self, n):
        p = self.params
        pump = p["pump"]
        alpha = p["alpha"]
        dispersion = abs(p["d2"])
        theta = np.linspace(-math.pi, math.pi, n, endpoint=False)
        radicand = 2.0 * alpha - 16.0 * alpha**2 / (math.pi**2 * pump**2) if pump > 0 else -1.0
        noise = 1e-4 * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))
        if pump <= 0.0 or alpha <= 0.0 or dispersion <= 0.0 or radicand < 0.0:
            return (10.0 * noise).astype(np.complex128)
        background = pump / alpha**2 - 1j * pump / alpha
        pulse = (
            4.0 * alpha / (math.pi * pump)
            + 1j * math.sqrt(max(0.0, radicand))
        ) / np.cosh(np.sqrt(alpha / dispersion) * theta)
        return (background + pulse + noise).astype(np.complex128)

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _clean_params(params):
        cleaned = {
            "alpha": float(params.get("alpha", 10.0)),
            "pump": max(0.0, float(params.get("pump", 0.0))),
            "d2": float(params.get("d2", 0.0)),
            "d3": float(params.get("d3", 0.0)),
            "d4": float(params.get("d4", 0.0)),
            "tauR": float(params.get("tauR", 0.0)),
            "dt": min(
                MAX_REQUESTED_DT,
                max(MIN_DT, float(params.get("dt", DEFAULT_DT))),
            ),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 50))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned


class PlaticonSolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260703)
        self.n = 512
        self.step = 0
        self.t = 0.0
        self.params = {
            "alpha": 4.0,
            "pump": 3.94,
            "d2": 0.02,
            "modeShiftMu": 0,
            "modeShiftStrength": 4.0,
            "dt": DEFAULT_DT,
            "stepsPerFrame": 50,
        }
        self.mu = self._make_mu(self.n)
        self.psi = self._initial_state(self.n)
        self._linear = None
        self._refresh_linear()

    def configure(self, config):
        n = int(config["n"])
        reset = bool(config.get("reset", False))
        self.params = self._clean_params(config["params"], n)
        if reset or n != self.n:
            self.n = n
            self.mu = self._make_mu(n)
            self.psi = self._initial_state(n)
            self.step = 0
            self.t = 0.0
        self._refresh_linear()
        return {"ok": True}

    def update_params(self, params):
        self.params = self._clean_params(params, self.n)
        self._refresh_linear()
        return {"ok": True}

    def run_steps(self):
        self.advance_steps()
        return self.snapshot()

    def advance_steps(self):
        steps = int(self.params["stepsPerFrame"])
        for _ in range(max(1, steps)):
            self._step_once()

    def snapshot(self):
        intensity = np.abs(self.psi) ** 2
        spectrum = np.fft.fftshift(np.fft.fft(self.psi)) / self.n
        spectrum_db = 20.0 * np.log10(np.abs(spectrum) + 1e-12)
        history_row = 10.0 * np.log10(intensity + 1e-12)
        return {
            "modelId": "platicon",
            "step": int(self.step),
            "t": float(self.t),
            "intensity": intensity.astype(np.float32),
            "spectrumDb": spectrum_db.astype(np.float32),
            "historyRow": history_row.astype(np.float32),
            "energy": float(np.mean(intensity)),
            "peak": float(np.max(intensity)),
            "normalizedParams": dict(self.params),
        }

    def export_state(self):
        return {
            "modelId": "platicon",
            "n": self.n,
            "step": int(self.step),
            "t": float(self.t),
            "params": dict(self.params),
            "psi_real": self.psi.real.tolist(),
            "psi_imag": self.psi.imag.tolist(),
        }

    def _step_once(self):
        dt = self.params["dt"]
        self.psi *= np.exp(1j * np.abs(self.psi) ** 2 * dt)

        psi_freq = np.fft.fft(self.psi)
        psi_freq *= self._linear
        self.psi = np.fft.ifft(psi_freq)
        self.psi += self.params["pump"] * dt

        if not np.all(np.isfinite(self.psi)):
            raise FloatingPointError(
                "Platicon state contains NaN or Inf; reduce pump, mode shift, or timestep."
            )

        self.step += 1
        self.t += dt

    def _refresh_linear(self):
        self._refresh_adaptive_dt()
        p = self.params
        linear = -(1.0 + 1j * p["alpha"]) + 1j * self._dint()
        self._linear = np.exp(linear * p["dt"])

    def _refresh_adaptive_dt(self):
        max_abs_dint = float(np.max(np.abs(self._dint())))
        requested_dt = self.params["dt"]
        if max_abs_dint > 0.0:
            alias_safe_dt = ALIASING_SAFETY * math.pi / max_abs_dint
            self.params["dt"] = max(MIN_DT, min(requested_dt, alias_safe_dt))
        else:
            self.params["dt"] = requested_dt

    def _dint(self):
        p = self.params
        dint = p["d2"] * self.mu**2 / 2.0
        shifted_mode = int(p["modeShiftMu"])
        dint = np.array(dint, dtype=np.float64, copy=True)
        dint[self.mu == shifted_mode] += p["modeShiftStrength"]
        return dint

    def _initial_state(self, n):
        p = self.params
        pump = p["pump"]
        alpha = p["alpha"]
        theta = np.linspace(-math.pi, math.pi, n, endpoint=False)
        noise = self._complex_noise(n, 1e-4)
        if pump <= 0.0 or not math.isfinite(alpha):
            return noise.astype(np.complex128)

        intensity = self._upper_cw_intensity(pump, alpha)
        psi_cw = pump / (1.0 + 1j * (alpha - intensity))
        half_width = math.pi / 3.0
        edge_width = max(
            0.04,
            math.sqrt(abs(p["d2"]) / max(abs(alpha), 1e-9)),
        )
        window = 0.5 * (
            np.tanh((theta + half_width) / edge_width)
            - np.tanh((theta - half_width) / edge_width)
        )
        psi = psi_cw * (1.0 - 0.9 * window) + noise
        return psi.astype(np.complex128)

    @staticmethod
    def _upper_cw_intensity(pump, alpha):
        coefficients = [1.0, -2.0 * alpha, alpha**2 + 1.0, -(pump**2)]
        roots = np.roots(coefficients)
        real_roots = [
            float(root.real)
            for root in roots
            if abs(root.imag) < 1e-7 and root.real > 0.0
        ]
        if real_roots:
            return max(real_roots)
        return max(0.0, pump**2 / (1.0 + alpha**2))

    def _complex_noise(self, n, scale):
        return scale * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _mode_bounds(n):
        half = n // 2
        return -half, half - 1

    @classmethod
    def _clean_params(cls, params, n):
        min_mu, max_mu = cls._mode_bounds(n)
        raw_mode_shift_mu = float(params.get("modeShiftMu", 0))
        if not math.isfinite(raw_mode_shift_mu):
            raw_mode_shift_mu = 0.0
        mode_shift_mu = int(round(raw_mode_shift_mu))
        cleaned = {
            "alpha": float(params.get("alpha", 4.0)),
            "pump": max(0.0, float(params.get("pump", 3.94))),
            "d2": float(params.get("d2", 0.02)),
            "modeShiftMu": min(max_mu, max(min_mu, mode_shift_mu)),
            "modeShiftStrength": float(params.get("modeShiftStrength", 4.0)),
            "dt": min(
                MAX_REQUESTED_DT,
                max(MIN_DT, float(params.get("dt", DEFAULT_DT))),
            ),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 50))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned


class StokesSolitonSolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260702)
        self.n = 1024
        self.step = 0
        self.t = 0.0
        self.params = {
            "alphaP": 39.1,
            "alphaS": 0.0,
            "pump": 12.247,
            "d2P": 0.02,
            "d2S": 0.02,
            "fsrMismatch": 0.0,
            "overlap": 0.5,
            "fR": 0.18,
            "ramanGainP": 0.35 * 0.18 * 2.0,
            "ramanGainS": 0.35 * 0.18 * 2.0,
            "wavelengthRatio": 1550.0 / 1630.0,
            "tauR": 3.3e-4,
            "noise": 1e-5,
            "dt": DEFAULT_STOKES_DT,
            "stepsPerFrame": 1000,
        }
        self.mu = self._make_mu(self.n)
        self.psi_p = self._initial_primary_state(self.n)
        self.psi_s = self._initial_stokes_state(self.n)
        self._linear_p = None
        self._linear_s = None
        self._refresh_linear()

    def configure(self, config):
        n = int(config["n"])
        reset = bool(config.get("reset", False))
        self.params = self._clean_params(config["params"])
        if reset or n != self.n:
            self.n = n
            self.mu = self._make_mu(n)
            self.psi_p = self._initial_primary_state(n)
            self.psi_s = self._initial_stokes_state(n)
            self.step = 0
            self.t = 0.0
        self._refresh_linear()
        return {"ok": True}

    def update_params(self, params):
        self.params = self._clean_params(params)
        self._refresh_linear()
        return {"ok": True}

    def run_steps(self):
        self.advance_steps()
        return self.snapshot()

    def advance_steps(self):
        steps = int(self.params["stepsPerFrame"])
        for _ in range(max(1, steps)):
            self._step_once()

    def snapshot(self):
        primary_intensity = np.abs(self.psi_p) ** 2
        stokes_intensity = np.abs(self.psi_s) ** 2
        primary_spectrum = np.fft.fftshift(np.fft.fft(self.psi_p)) / self.n
        stokes_spectrum = np.fft.fftshift(np.fft.fft(self.psi_s)) / self.n
        primary_spectrum_db = 20.0 * np.log10(np.abs(primary_spectrum) + 1e-12)
        stokes_spectrum_db = 20.0 * np.log10(np.abs(stokes_spectrum) + 1e-12)
        primary_history_row = 10.0 * np.log10(primary_intensity + 1e-12)
        stokes_history_row = 10.0 * np.log10(stokes_intensity + 1e-12)
        return {
            "modelId": "stokes",
            "step": int(self.step),
            "t": float(self.t),
            "primaryIntensity": primary_intensity.astype(np.float32),
            "stokesIntensity": stokes_intensity.astype(np.float32),
            "primarySpectrumDb": primary_spectrum_db.astype(np.float32),
            "stokesSpectrumDb": stokes_spectrum_db.astype(np.float32),
            "primaryHistoryRow": primary_history_row.astype(np.float32),
            "stokesHistoryRow": stokes_history_row.astype(np.float32),
            "primaryEnergy": float(np.mean(primary_intensity)),
            "stokesEnergy": float(np.mean(stokes_intensity)),
            "primaryPeak": float(np.max(primary_intensity)),
            "stokesPeak": float(np.max(stokes_intensity)),
            "normalizedParams": dict(self.params),
        }

    def export_state(self):
        return {
            "modelId": "stokes",
            "n": self.n,
            "step": int(self.step),
            "t": float(self.t),
            "params": dict(self.params),
            "psiP_real": self.psi_p.real.tolist(),
            "psiP_imag": self.psi_p.imag.tolist(),
            "psiS_real": self.psi_s.real.tolist(),
            "psiS_imag": self.psi_s.imag.tolist(),
        }

    def _step_once(self):
        p = self.params
        dt = p["dt"]
        primary_abs2 = np.abs(self.psi_p) ** 2
        stokes_abs2 = np.abs(self.psi_s) ** 2
        d_primary = self._d_theta(primary_abs2)
        d_stokes = self._d_theta(stokes_abs2)

        primary_nonlinear = (
            1j * primary_abs2
            - 1j * p["tauR"] * (d_primary + p["overlap"] * d_stokes)
            + p["overlap"]
            * (1j * (2.0 - p["fR"]) - p["ramanGainP"] / 2.0)
            * stokes_abs2
        )
        stokes_nonlinear = (
            1j * p["wavelengthRatio"] * stokes_abs2
            - 1j
            * p["wavelengthRatio"]
            * p["tauR"]
            * (p["overlap"] * d_primary + d_stokes)
            + p["overlap"]
            * p["wavelengthRatio"]
            * (1j * (2.0 - p["fR"]) + p["ramanGainS"] / 2.0)
            * primary_abs2
        )

        self.psi_p *= np.exp(primary_nonlinear * dt)
        self.psi_s *= np.exp(stokes_nonlinear * dt)

        primary_freq = np.fft.fft(self.psi_p)
        stokes_freq = np.fft.fft(self.psi_s)
        primary_freq *= self._linear_p
        stokes_freq *= self._linear_s
        self.psi_p = np.fft.ifft(primary_freq)
        self.psi_s = np.fft.ifft(stokes_freq)

        self.psi_p += p["pump"] * dt
        if p["noise"] > 0.0:
            self.psi_s += self._complex_noise(self.n, p["noise"]) * dt

        if not np.all(np.isfinite(self.psi_p)) or not np.all(np.isfinite(self.psi_s)):
            raise FloatingPointError(
                "Stokes state contains NaN or Inf; reduce pump, gain, or timestep."
            )

        self.step += 1
        self.t += dt

    def _refresh_linear(self):
        self._refresh_adaptive_dt()
        p = self.params
        linear_p = -1.0 - 1j * p["alphaP"] - 1j * p["d2P"] * self.mu**2
        linear_s = (
            -1.0
            - 1j * p["alphaS"]
            - 1j * p["d2S"] * self.mu**2
            - 1j * p["fsrMismatch"] * self.mu
        )
        self._linear_p = np.exp(linear_p * p["dt"])
        self._linear_s = np.exp(linear_s * p["dt"])

    def _refresh_adaptive_dt(self):
        p = self.params
        primary_phase = np.abs(p["d2P"] * self.mu**2)
        stokes_phase = np.abs(p["d2S"] * self.mu**2 + p["fsrMismatch"] * self.mu)
        max_abs_dint = float(max(np.max(primary_phase), np.max(stokes_phase)))
        requested_dt = p["dt"]
        if max_abs_dint > 0.0:
            alias_safe_dt = ALIASING_SAFETY * math.pi / max_abs_dint
            self.params["dt"] = max(MIN_DT, min(requested_dt, alias_safe_dt))
        else:
            self.params["dt"] = requested_dt

    def _d_theta(self, values):
        return np.fft.ifft(1j * self.mu * np.fft.fft(values)).real

    def _initial_primary_state(self, n):
        p = self.params
        pump = p["pump"]
        alpha = p["alphaP"]
        dispersion = abs(p["d2P"])
        theta = np.linspace(-math.pi, math.pi, n, endpoint=False)
        radicand = 2.0 * alpha - 16.0 * alpha**2 / (math.pi**2 * pump**2) if pump > 0 else -1.0
        if pump <= 0.0 or alpha <= 0.0 or dispersion <= 0.0 or radicand < 0.0:
            return self._complex_noise(n, 1e-3)
        background = pump / alpha**2 - 1j * pump / alpha
        pulse = (
            4.0 * alpha / (math.pi * pump)
            + 1j * math.sqrt(max(0.0, radicand))
        ) / np.cosh(np.sqrt(alpha / dispersion) * theta)
        return (background + pulse + self._complex_noise(n, 1e-4)).astype(np.complex128)

    def _initial_stokes_state(self, n):
        return self._complex_noise(n, max(self.params["noise"], 1e-8)).astype(np.complex128)

    def _complex_noise(self, n, scale):
        return scale * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _clean_params(params):
        cleaned = {
            "alphaP": float(params.get("alphaP", 39.1)),
            "alphaS": 0.0,
            "pump": max(0.0, float(params.get("pump", 12.247))),
            "d2P": float(params.get("d2P", 0.02)),
            "d2S": float(params.get("d2S", 0.02)),
            "fsrMismatch": float(params.get("fsrMismatch", 0.0)),
            "overlap": max(0.0, float(params.get("overlap", 0.5))),
            "fR": min(1.0, max(0.0, float(params.get("fR", 0.18)))),
            "ramanGainP": max(0.0, float(params.get("ramanGainP", 0.35 * 0.18 * 2.0))),
            "ramanGainS": max(0.0, float(params.get("ramanGainS", 0.35 * 0.18 * 2.0))),
            "wavelengthRatio": max(1e-9, float(params.get("wavelengthRatio", 1550.0 / 1630.0))),
            "tauR": max(0.0, float(params.get("tauR", 3.3e-4))),
            "noise": max(0.0, float(params.get("noise", 1e-5))),
            "dt": min(
                MAX_REQUESTED_DT,
                max(MIN_DT, float(params.get("dt", DEFAULT_STOKES_DT))),
            ),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 1000))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned


class TurnkeySolitonSolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260704)
        self.n = 512
        self.step = 0
        self.t = 0.0
        self.locked_detuning = 5.0
        self.params = {
            "laserDetuning": 5.0,
            "pump": math.sqrt(3.0),
            "d2": 0.015,
            "beta": 0.5,
            "lockingBandwidth": 15.0,
            "feedbackPhase": 0.3 * math.pi,
            "noise": 1e-5,
            "dt": 5e-4,
            "stepsPerFrame": 200,
        }
        self.mu = self._make_mu(self.n)
        self.psi = self._initial_state(self.n)
        self.rho_b = 1e-4 + 0j
        self._linear = None
        self._refresh_linear()

    def configure(self, config):
        n = int(config["n"])
        reset = bool(config.get("reset", False))
        self.params = self._clean_params(config["params"])
        if reset or n != self.n:
            self.n = n
            self.mu = self._make_mu(n)
            self.locked_detuning = self.params["laserDetuning"]
            self.psi = self._initial_state(n)
            self.rho_b = 1e-4 + 0j
            self.step = 0
            self.t = 0.0
        self._refresh_linear()
        return {"ok": True}

    def update_params(self, params):
        self.params = self._clean_params(params)
        self._refresh_linear()
        return {"ok": True}

    def run_steps(self):
        self.advance_steps()
        return self.snapshot()

    def advance_steps(self):
        steps = int(self.params["stepsPerFrame"])
        for _ in range(max(1, steps)):
            self._step_once()

    def snapshot(self):
        primary_intensity = np.abs(self.psi) ** 2
        backward_field = np.full(self.n, self.rho_b, dtype=np.complex128)
        backward_intensity = np.abs(backward_field) ** 2
        primary_spectrum = np.fft.fftshift(np.fft.fft(self.psi)) / self.n
        backward_spectrum = np.fft.fftshift(np.fft.fft(backward_field)) / self.n
        return {
            "modelId": "turnkey",
            "step": int(self.step),
            "t": float(self.t),
            "primaryIntensity": primary_intensity.astype(np.float32),
            "backwardIntensity": backward_intensity.astype(np.float32),
            "primarySpectrumDb": (20.0 * np.log10(np.abs(primary_spectrum) + 1e-12)).astype(np.float32),
            "backwardSpectrumDb": (20.0 * np.log10(np.abs(backward_spectrum) + 1e-12)).astype(np.float32),
            "primaryHistoryRow": (10.0 * np.log10(primary_intensity + 1e-12)).astype(np.float32),
            "backwardHistoryRow": (10.0 * np.log10(backward_intensity + 1e-12)).astype(np.float32),
            "primaryEnergy": float(np.mean(primary_intensity)),
            "backwardEnergy": float(np.mean(backward_intensity)),
            "primaryPeak": float(np.max(primary_intensity)),
            "backwardPeak": float(np.max(backward_intensity)),
            "lockedDetuning": float(self.locked_detuning),
            "normalizedParams": dict(self.params),
        }

    def export_state(self):
        return {
            "modelId": "turnkey",
            "n": self.n,
            "step": int(self.step),
            "t": float(self.t),
            "params": dict(self.params),
            "lockedDetuning": float(self.locked_detuning),
            "psiP_real": self.psi.real.tolist(),
            "psiP_imag": self.psi.imag.tolist(),
            "rhoB_real": float(self.rho_b.real),
            "rhoB_imag": float(self.rho_b.imag),
        }

    def _step_once(self):
        p = self.params
        dt = p["dt"]
        power = float(np.mean(np.abs(self.psi) ** 2))
        beta = max(abs(p["beta"]), 1e-9)
        target_detuning = self._solve_locking_equilibrium(power)
        self.locked_detuning += 0.05 * (target_detuning - self.locked_detuning)
        self.locked_detuning = float(np.clip(self.locked_detuning, -50.0, 80.0))
        self._refresh_linear()

        abs2 = np.abs(self.psi) ** 2
        self.psi *= np.exp(1j * (abs2 + 2.0 * abs(self.rho_b) ** 2) * dt)
        psi_freq = np.fft.fft(self.psi)
        psi_freq *= self._linear
        self.psi = np.fft.ifft(psi_freq)
        self.psi += p["pump"] * dt + 1j * p["beta"] * self.rho_b * dt

        mean_field = np.mean(self.psi)
        d_rho = (
            -(1.0 + 1j * self.locked_detuning - 2j * power - 1j * abs(self.rho_b) ** 2)
            * self.rho_b
            + 1j * p["beta"] * mean_field
        )
        self.rho_b += d_rho * dt
        if p["noise"] > 0.0:
            self.psi += self._complex_noise(self.n, p["noise"]) * dt

        if not np.all(np.isfinite(self.psi)) or not np.isfinite(self.rho_b):
            raise FloatingPointError(
                "Turnkey state contains NaN or Inf; reduce feedback, pump, or timestep."
            )

        self.step += 1
        self.t += dt

    @staticmethod
    def _locking_response(power, alpha, phase):
        # Supplementary Eq. S13 for the CW self-injection-locking response.
        denominator = (1.0 + (alpha - power) ** 2) * (1.0 + (alpha - 2.0 * power) ** 2)
        if denominator <= 0.0:
            return 0.0
        numerator = (
            (3.0 * power - 2.0 * alpha) * math.cos(phase)
            + (1.0 - 2.0 * power**2 + 3.0 * power * alpha - alpha**2) * math.sin(phase)
        )
        return numerator / denominator

    def _locking_equation(self, alpha, power):
        p = self.params
        return alpha - p["laserDetuning"] - p["lockingBandwidth"] * self._locking_response(
            power,
            alpha,
            p["feedbackPhase"],
        )

    def _solve_locking_equilibrium(self, power):
        p = self.params
        if p["lockingBandwidth"] <= 1e-12:
            return p["laserDetuning"]

        alpha = float(np.clip(self.locked_detuning, -50.0, 80.0))
        for _ in range(10):
            value = self._locking_equation(alpha, power)
            if abs(value) < 1e-8:
                break
            eps = 1e-4 * max(1.0, abs(alpha))
            slope = (
                self._locking_equation(alpha + eps, power)
                - self._locking_equation(alpha - eps, power)
            ) / (2.0 * eps)
            if not math.isfinite(slope) or abs(slope) < 1e-8:
                break
            alpha -= float(np.clip(value / slope, -2.0, 2.0))
            alpha = float(np.clip(alpha, -50.0, 80.0))
        return alpha

    def _refresh_linear(self):
        self._refresh_adaptive_dt()
        p = self.params
        linear = -1.0 - 1j * self.locked_detuning - 0.5j * p["d2"] * self.mu**2
        self._linear = np.exp(linear * p["dt"])

    def _refresh_adaptive_dt(self):
        max_abs_phase = float(np.max(np.abs(self.params["d2"] * self.mu**2 / 2.0)))
        requested_dt = self.params["dt"]
        if max_abs_phase > 0.0:
            alias_safe_dt = ALIASING_SAFETY * math.pi / max_abs_phase
            self.params["dt"] = max(MIN_DT, min(requested_dt, alias_safe_dt))
        else:
            self.params["dt"] = requested_dt

    def _initial_state(self, n):
        p = self.params
        pump = max(p["pump"], 1e-9)
        alpha = max(abs(p["laserDetuning"]), 1e-6)
        dispersion = max(abs(p["d2"]), 1e-9)
        theta = np.linspace(-math.pi, math.pi, n, endpoint=False)
        radicand = 2.0 * alpha - 16.0 * alpha**2 / (math.pi**2 * pump**2)
        noise = self._complex_noise(n, 1e-4)
        if radicand < 0.0:
            return (0.2 + noise).astype(np.complex128)
        background = pump / alpha**2 - 1j * pump / alpha
        pulse = (
            4.0 * alpha / (math.pi * pump)
            + 1j * math.sqrt(max(0.0, radicand))
        ) / np.cosh(np.sqrt(alpha / dispersion) * theta)
        return (background + pulse + noise).astype(np.complex128)

    def _complex_noise(self, n, scale):
        return scale * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _clean_params(params):
        cleaned = {
            "laserDetuning": float(params.get("laserDetuning", 5.0)),
            "pump": max(0.0, float(params.get("pump", math.sqrt(3.0)))),
            "d2": float(params.get("d2", 0.015)),
            "beta": max(0.0, float(params.get("beta", 0.5))),
            "lockingBandwidth": max(0.0, float(params.get("lockingBandwidth", 15.0))),
            "feedbackPhase": float(params.get("feedbackPhase", 0.3 * math.pi)),
            "noise": max(0.0, float(params.get("noise", 1e-5))),
            "dt": min(MAX_REQUESTED_DT, max(MIN_DT, float(params.get("dt", 5e-4)))),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 200))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned


class MulticolorSolitonSolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260705)
        self.n = 1024
        self.step = 0
        self.t = 0.0
        self.params = {
            "alphaP": 48.0,
            "alphaS": 25.0,
            "alphaI": 25.0,
            "pump": 17.0,
            "d2P": 0.201,
            "d2S": 0.0905,
            "d2I": -0.0877,
            "fsrMismatchS": 0.0,
            "fsrMismatchI": 18.1,
            "xpm": 1.73 / 4.33,
            "fwmRe": 1.73 / 4.33,
            "fwmIm": 0.0,
            "noise": 1e-5,
            "dt": DEFAULT_MULTICOLOR_DT,
            "stepsPerFrame": 500,
        }
        self.mu = self._make_mu(self.n)
        self.psi_p = self._initial_primary_state(self.n)
        self.psi_s = self._complex_noise(self.n, self.params["noise"])
        self.psi_i = self._complex_noise(self.n, self.params["noise"])
        self._linear_p = None
        self._linear_s = None
        self._linear_i = None
        self._refresh_linear()

    def configure(self, config):
        n = int(config["n"])
        reset = bool(config.get("reset", False))
        self.params = self._clean_params(config["params"])
        if reset or n != self.n:
            self.n = n
            self.mu = self._make_mu(n)
            self.psi_p = self._initial_primary_state(n)
            self.psi_s = self._complex_noise(n, max(self.params["noise"], 1e-9))
            self.psi_i = self._complex_noise(n, max(self.params["noise"], 1e-9))
            self.step = 0
            self.t = 0.0
        self._refresh_linear()
        return {"ok": True}

    def update_params(self, params):
        self.params = self._clean_params(params)
        self._refresh_linear()
        return {"ok": True}

    def run_steps(self):
        self.advance_steps()
        return self.snapshot()

    def advance_steps(self):
        steps = int(self.params["stepsPerFrame"])
        for _ in range(max(1, steps)):
            self._step_once()

    def snapshot(self):
        p_int = np.abs(self.psi_p) ** 2
        s_int = np.abs(self.psi_s) ** 2
        i_int = np.abs(self.psi_i) ** 2
        p_spec = np.fft.fftshift(np.fft.fft(self.psi_p)) / self.n
        s_spec = np.fft.fftshift(np.fft.fft(self.psi_s)) / self.n
        i_spec = np.fft.fftshift(np.fft.fft(self.psi_i)) / self.n
        return {
            "modelId": "multicolor",
            "step": int(self.step),
            "t": float(self.t),
            "primaryIntensity": p_int.astype(np.float32),
            "signalIntensity": s_int.astype(np.float32),
            "idlerIntensity": i_int.astype(np.float32),
            "primarySpectrumDb": (20.0 * np.log10(np.abs(p_spec) + 1e-12)).astype(np.float32),
            "signalSpectrumDb": (20.0 * np.log10(np.abs(s_spec) + 1e-12)).astype(np.float32),
            "idlerSpectrumDb": (20.0 * np.log10(np.abs(i_spec) + 1e-12)).astype(np.float32),
            "primaryHistoryRow": (10.0 * np.log10(p_int + 1e-12)).astype(np.float32),
            "signalHistoryRow": (10.0 * np.log10(s_int + 1e-12)).astype(np.float32),
            "idlerHistoryRow": (10.0 * np.log10(i_int + 1e-12)).astype(np.float32),
            "primaryEnergy": float(np.mean(p_int)),
            "signalEnergy": float(np.mean(s_int)),
            "idlerEnergy": float(np.mean(i_int)),
            "primaryPeak": float(np.max(p_int)),
            "signalPeak": float(np.max(s_int)),
            "idlerPeak": float(np.max(i_int)),
            "normalizedParams": dict(self.params),
        }

    def export_state(self):
        return {
            "modelId": "multicolor",
            "n": self.n,
            "step": int(self.step),
            "t": float(self.t),
            "params": dict(self.params),
            "psiP_real": self.psi_p.real.tolist(),
            "psiP_imag": self.psi_p.imag.tolist(),
            "psiS_real": self.psi_s.real.tolist(),
            "psiS_imag": self.psi_s.imag.tolist(),
            "psiI_real": self.psi_i.real.tolist(),
            "psiI_imag": self.psi_i.imag.tolist(),
        }

    def _step_once(self):
        p = self.params
        dt = p["dt"]
        p_abs = np.abs(self.psi_p) ** 2
        s_abs = np.abs(self.psi_s) ** 2
        i_abs = np.abs(self.psi_i) ** 2
        fwm = complex(p["fwmRe"], p["fwmIm"])

        primary_nl = (
            1j * (p_abs + 2.0 * p["xpm"] * (s_abs + i_abs)) * self.psi_p
            + 2j * np.conj(fwm) * self.psi_s * self.psi_i * np.conj(self.psi_p)
        )
        signal_nl = (
            1j * (s_abs + 2.0 * p["xpm"] * (p_abs + i_abs)) * self.psi_s
            + 1j * fwm * self.psi_p**2 * np.conj(self.psi_i)
        )
        idler_nl = (
            1j * (i_abs + 2.0 * p["xpm"] * (p_abs + s_abs)) * self.psi_i
            + 1j * fwm * self.psi_p**2 * np.conj(self.psi_s)
        )
        self.psi_p += primary_nl * dt
        self.psi_s += signal_nl * dt
        self.psi_i += idler_nl * dt

        p_freq = np.fft.fft(self.psi_p) * self._linear_p
        s_freq = np.fft.fft(self.psi_s) * self._linear_s
        i_freq = np.fft.fft(self.psi_i) * self._linear_i
        self.psi_p = np.fft.ifft(p_freq)
        self.psi_s = np.fft.ifft(s_freq)
        self.psi_i = np.fft.ifft(i_freq)

        self.psi_p += p["pump"] * dt
        if p["noise"] > 0.0:
            self.psi_s += self._complex_noise(self.n, p["noise"]) * dt
            self.psi_i += self._complex_noise(self.n, p["noise"]) * dt

        if (
            not np.all(np.isfinite(self.psi_p))
            or not np.all(np.isfinite(self.psi_s))
            or not np.all(np.isfinite(self.psi_i))
        ):
            raise FloatingPointError(
                "Multicolor state contains NaN or Inf; reduce pump, FWM, or timestep."
            )

        self.step += 1
        self.t += dt

    def _refresh_linear(self):
        self._refresh_adaptive_dt()
        p = self.params
        self._linear_p = np.exp((-1.0 - 1j * p["alphaP"] - 1j * p["d2P"] * self.mu**2 / 2.0) * p["dt"])
        self._linear_s = np.exp(
            (
                -1.0
                - 1j * p["alphaS"]
                - 1j * p["fsrMismatchS"] * self.mu
                - 1j * p["d2S"] * self.mu**2 / 2.0
            )
            * p["dt"]
        )
        self._linear_i = np.exp(
            (
                -1.0
                - 1j * p["alphaI"]
                - 1j * p["fsrMismatchI"] * self.mu
                - 1j * p["d2I"] * self.mu**2 / 2.0
            )
            * p["dt"]
        )

    def _refresh_adaptive_dt(self):
        p = self.params
        primary_phase = np.abs(p["d2P"] * self.mu**2 / 2.0)
        signal_phase = np.abs(p["fsrMismatchS"] * self.mu + p["d2S"] * self.mu**2 / 2.0)
        idler_phase = np.abs(p["fsrMismatchI"] * self.mu + p["d2I"] * self.mu**2 / 2.0)
        max_abs_phase = float(max(np.max(primary_phase), np.max(signal_phase), np.max(idler_phase)))
        requested_dt = p["dt"]
        if max_abs_phase > 0.0:
            alias_safe_dt = ALIASING_SAFETY * math.pi / max_abs_phase
            self.params["dt"] = max(MIN_DT, min(requested_dt, alias_safe_dt))
        else:
            self.params["dt"] = requested_dt

    def _initial_primary_state(self, n):
        p = self.params
        pump = max(p["pump"], 1e-9)
        alpha = max(p["alphaP"], 1e-6)
        dispersion = max(abs(p["d2P"]), 1e-9)
        theta = np.linspace(-math.pi, math.pi, n, endpoint=False)
        radicand = 2.0 * alpha - 16.0 * alpha**2 / (math.pi**2 * pump**2)
        background = pump / alpha**2 - 1j * pump / alpha
        if radicand < 0.0:
            return (background + self._complex_noise(n, 1e-4)).astype(np.complex128)
        pulse = (
            4.0 * alpha / (math.pi * pump)
            + 1j * math.sqrt(max(0.0, radicand))
        ) / np.cosh(np.sqrt(alpha / dispersion) * theta)
        return (background + pulse + self._complex_noise(n, 1e-4)).astype(np.complex128)

    def _complex_noise(self, n, scale):
        return scale * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _clean_params(params):
        cleaned = {
            "alphaP": float(params.get("alphaP", 48.0)),
            "alphaS": float(params.get("alphaS", 25.0)),
            "alphaI": float(params.get("alphaI", 25.0)),
            "pump": max(0.0, float(params.get("pump", 17.0))),
            "d2P": float(params.get("d2P", 0.201)),
            "d2S": float(params.get("d2S", 0.0905)),
            "d2I": float(params.get("d2I", -0.0877)),
            "fsrMismatchS": float(params.get("fsrMismatchS", 0.0)),
            "fsrMismatchI": float(params.get("fsrMismatchI", 18.1)),
            "xpm": max(0.0, float(params.get("xpm", 1.73 / 4.33))),
            "fwmRe": float(params.get("fwmRe", 1.73 / 4.33)),
            "fwmIm": float(params.get("fwmIm", 0.0)),
            "noise": max(0.0, float(params.get("noise", 1e-5))),
            "dt": min(MAX_REQUESTED_DT, max(MIN_DT, float(params.get("dt", DEFAULT_MULTICOLOR_DT)))),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 500))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned


class RamanSsfSolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260706)
        self.n = 512
        self.step = 0
        self.t = 0.0
        self.params = {
            "dtnNorm": 70.0,
            "ffNorm": 90.0,
            "d2Norm": 1.65414364640884,
            "fR": 0.02,
            "tau1Fs": 11.1,
            "tau2Fs": 35.0,
            "fsrGHz": 1000.0,
            "qMillion": 4.0,
            "wavelengthNm": 1550.0,
            "noise": 1e-4,
            "dt": DEFAULT_RAMAN_DT,
            "stepsPerFrame": 1000,
        }
        self.mu = self._make_mu(self.n)
        self.centered_mu = self._make_centered_mu(self.n)
        self.dtheta = 2.0 * math.pi / self.n
        self.psi = self._initial_state(self.n)
        self._linear = None
        self._response_fft = None
        self._refresh_linear()
        self._refresh_raman_response()

    def configure(self, config):
        n = int(config["n"])
        reset = bool(config.get("reset", False))
        old_response_key = self._response_key()
        self.params = self._clean_params(config["params"])
        response_changed = old_response_key != self._response_key()
        if reset or n != self.n:
            self.n = n
            self.mu = self._make_mu(n)
            self.centered_mu = self._make_centered_mu(n)
            self.dtheta = 2.0 * math.pi / n
            self.psi = self._initial_state(n)
            self.step = 0
            self.t = 0.0
            response_changed = True
        self._refresh_linear()
        if response_changed:
            self._refresh_raman_response()
        return {"ok": True}

    def update_params(self, params):
        old_response_key = self._response_key()
        self.params = self._clean_params(params)
        self._refresh_linear()
        if old_response_key != self._response_key():
            self._refresh_raman_response()
        return {"ok": True}

    def run_steps(self):
        self.advance_steps()
        return self.snapshot()

    def advance_steps(self):
        steps = int(self.params["stepsPerFrame"])
        for _ in range(max(1, steps)):
            self._step_once()

    def snapshot(self):
        intensity = np.abs(self.psi) ** 2
        spectrum = np.fft.fftshift(np.fft.fft(self.psi)) / self.n
        spectrum_power = np.abs(spectrum) ** 2
        spectrum_db = 20.0 * np.log10(np.abs(spectrum) + 1e-12)
        ssfs_thz, ssfs_mu = self._self_frequency_shift(spectrum_power)
        return {
            "modelId": "raman",
            "step": int(self.step),
            "t": float(self.t),
            "intensity": intensity.astype(np.float32),
            "spectrumDb": spectrum_db.astype(np.float32),
            "historyRow": (10.0 * np.log10(intensity + 1e-12)).astype(np.float32),
            "energy": float(np.mean(intensity)),
            "peak": float(np.max(intensity)),
            "pulseWidthFs": float(self._pulse_width_fs(intensity)),
            "selfFrequencyShiftThz": float(ssfs_thz),
            "selfFrequencyShiftMu": float(ssfs_mu),
            "normalizedParams": dict(self.params),
            "referenceParams": self._reference_params(),
        }

    def export_state(self):
        return {
            "modelId": "raman",
            "n": self.n,
            "step": int(self.step),
            "t": float(self.t),
            "params": dict(self.params),
            "referenceParams": self._reference_params(),
            "psi_real": self.psi.real.tolist(),
            "psi_imag": self.psi.imag.tolist(),
        }

    def _step_once(self):
        p = self.params
        dt = p["dt"]
        abs2 = np.abs(self.psi) ** 2
        ramp = self._raman_ramp()
        if p["fR"] > 0.0 and self._response_fft is not None:
            rconv = (
                1j
                * np.fft.fftshift(np.fft.ifft(np.fft.fft(abs2) * self._response_fft))
                * self.dtheta
            )
            nonlinear = 1j * (1.0 - ramp) * abs2 + (ramp / p["fR"]) * rconv
        else:
            nonlinear = 1j * abs2
        self.psi *= np.exp(nonlinear * dt)

        psi_freq = np.fft.fft(self.psi) * self._linear
        self.psi = np.fft.ifft(psi_freq)
        self.psi += math.sqrt(max(p["ffNorm"], 0.0)) * dt
        if p["noise"] > 0.0:
            self.psi += self._complex_noise(self.n, p["noise"]) * dt

        if not np.all(np.isfinite(self.psi)):
            raise FloatingPointError(
                "Raman SSFS state contains NaN or Inf; reduce pump, detuning, or timestep."
            )

        self.step += 1
        self.t += dt

    def _refresh_linear(self):
        self._refresh_adaptive_dt()
        p = self.params
        linear = -1.0 - 1j * p["dtnNorm"] - 1j * p["d2Norm"] * self.mu**2 / 2.0
        self._linear = np.exp(linear * p["dt"])

    def _refresh_adaptive_dt(self):
        max_abs_phase = float(np.max(np.abs(self.params["d2Norm"] * self.mu**2 / 2.0)))
        requested_dt = self.params["dt"]
        if max_abs_phase > 0.0:
            alias_safe_dt = ALIASING_SAFETY * math.pi / max_abs_phase
            self.params["dt"] = max(MIN_DT, min(requested_dt, alias_safe_dt))
        else:
            self.params["dt"] = requested_dt

    def _refresh_raman_response(self):
        response = self._raman_response_phi()
        self._response_fft = np.fft.fft(response)

    def _raman_response_phi(self):
        p = self.params
        if p["fR"] == 0.0 or p["tau1Fs"] == 0.0 or p["tau2Fs"] == 0.0:
            return np.zeros(self.n, dtype=np.complex128)
        theta = np.linspace(0.0, 2.0 * math.pi, self.n, endpoint=False)
        fsr_rad_s = p["fsrGHz"] * 1e9 * 2.0 * math.pi
        tau1 = p["tau1Fs"] * 1e-15
        tau2 = p["tau2Fs"] * 1e-15
        response = (
            p["fR"]
            / fsr_rad_s
            * (tau1**2 + tau2**2)
            / (tau1 * tau2**2)
            * np.exp(-theta / fsr_rad_s / tau2)
            * np.sin(theta / fsr_rad_s / tau1)
            * (theta >= 0.0)
        )
        return np.roll(response, self.n // 2).astype(np.complex128)

    def _raman_ramp(self):
        p = self.params
        if p["fR"] <= 0.0:
            return 0.0
        ramp_steps = max(1, int(2.0 * p["stepsPerFrame"]))
        if self.step < 0.1 * ramp_steps:
            return 0.0
        if self.step < 0.3 * ramp_steps:
            return p["fR"] * (self.step - 0.1 * ramp_steps) / (0.2 * ramp_steps)
        return p["fR"]

    def _initial_state(self, n):
        p = self.params
        ff = max(p["ffNorm"], 1e-9)
        dtn = max(p["dtnNorm"], 1e-9)
        theta = np.linspace(-math.pi, math.pi, n, endpoint=False)
        phi_tau = math.sqrt(max(p["d2Norm"], 1e-12) / (2.0 * dtn))
        background = math.sqrt(ff) / dtn**2 - 1j * math.sqrt(ff) / dtn
        radicand = 2.0 * dtn - 16.0 * dtn**2 / (math.pi**2 * ff)
        pulse = (
            4.0 * dtn / (math.pi * math.sqrt(ff))
            - 1j * math.sqrt(max(0.0, radicand))
        ) / np.cosh(theta / max(phi_tau, 1e-6))
        return (background + pulse + self._complex_noise(n, 1e-5)).astype(np.complex128)

    def _pulse_width_fs(self, intensity):
        peak = float(np.max(intensity))
        if peak <= 0.0:
            return 0.0
        centered = np.roll(intensity, self.n // 2 - int(np.argmax(intensity)))
        above = np.where(centered >= 0.5 * peak)[0]
        if above.size == 0:
            return 0.0
        width_phi = (above[-1] - above[0] + 1) * self.dtheta
        return width_phi / (2.0 * math.pi) / (self.params["fsrGHz"] * 1e9) * 1e15

    def _self_frequency_shift(self, spectrum_power):
        total = float(np.sum(spectrum_power))
        if total <= 0.0:
            return 0.0, 0.0
        ssfs_mu = float(np.sum(self.centered_mu * spectrum_power) / total)
        ssfs_thz = ssfs_mu * self.params["fsrGHz"] / 1000.0
        return ssfs_thz, ssfs_mu

    def _reference_params(self):
        return {
            "wavelengthNm": float(self.params["wavelengthNm"]),
            "fsrGHz": float(self.params["fsrGHz"]),
            "qMillion": float(self.params["qMillion"]),
            "d2Khz": float(self._d2_khz()),
        }

    def _d2_khz(self):
        wavelength_m = self.params["wavelengthNm"] * 1e-9
        omega0 = 2.0 * math.pi * LIGHT_SPEED / wavelength_m
        kappa_mhz = omega0 / (self.params["qMillion"] * 1e6) / 1e6
        return self.params["d2Norm"] * (kappa_mhz * 1e6 / 2.0) / 1e3

    def _response_key(self):
        p = self.params
        return (
            self.n,
            float(p["fR"]),
            float(p["tau1Fs"]),
            float(p["tau2Fs"]),
            float(p["fsrGHz"]),
        )

    def _complex_noise(self, n, scale):
        return scale * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _make_centered_mu(n):
        half = n // 2
        return np.arange(-half, half, dtype=float)

    @staticmethod
    def _clean_params(params):
        cleaned = {
            "dtnNorm": max(1e-9, float(params.get("dtnNorm", 70.0))),
            "ffNorm": max(0.0, float(params.get("ffNorm", 90.0))),
            "d2Norm": max(1e-12, float(params.get("d2Norm", 1.65414364640884))),
            "fR": min(1.0, max(0.0, float(params.get("fR", 0.02)))),
            "tau1Fs": max(1e-9, float(params.get("tau1Fs", 11.1))),
            "tau2Fs": max(1e-9, float(params.get("tau2Fs", 35.0))),
            "fsrGHz": max(1e-9, float(params.get("fsrGHz", 1000.0))),
            "qMillion": max(1e-9, float(params.get("qMillion", 4.0))),
            "wavelengthNm": max(1e-9, float(params.get("wavelengthNm", 1550.0))),
            "noise": max(0.0, float(params.get("noise", 1e-4))),
            "dt": min(MAX_REQUESTED_DT, max(MIN_DT, float(params.get("dt", DEFAULT_RAMAN_DT)))),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 1000))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned


class SimulationManager:
    def __init__(self):
        self.model_id = "standard"
        self.solver = LLESolver()

    def configure(self, config):
        model_id = str(config.get("modelId", "standard"))
        if model_id not in {"standard", "platicon", "stokes", "turnkey", "multicolor", "raman"}:
            raise ValueError(f"Unknown modelId: {model_id}")
        if model_id != self.model_id:
            self.model_id = model_id
            if model_id == "stokes":
                self.solver = StokesSolitonSolver()
            elif model_id == "platicon":
                self.solver = PlaticonSolver()
            elif model_id == "turnkey":
                self.solver = TurnkeySolitonSolver()
            elif model_id == "multicolor":
                self.solver = MulticolorSolitonSolver()
            elif model_id == "raman":
                self.solver = RamanSsfSolver()
            else:
                self.solver = LLESolver()
        return self.solver.configure(config)

    def update_params(self, params):
        return self.solver.update_params(params)

    def run_steps(self):
        return self.solver.run_steps()

    def advance_steps(self):
        return self.solver.advance_steps()

    def snapshot(self):
        return self.solver.snapshot()

    def export_state(self):
        return self.solver.export_state()
