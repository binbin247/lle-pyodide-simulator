import json
import math

import numpy as np


DEFAULT_DT = 8e-4
MAX_REQUESTED_DT = 5e-3
MIN_DT = 1e-12
ALIASING_SAFETY = 0.5
DEFAULT_STOKES_DT = 5e-5


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


class SimulationManager:
    def __init__(self):
        self.model_id = "standard"
        self.solver = LLESolver()

    def configure(self, config):
        model_id = str(config.get("modelId", "standard"))
        if model_id not in {"standard", "platicon", "stokes"}:
            raise ValueError(f"Unknown modelId: {model_id}")
        if model_id != self.model_id:
            self.model_id = model_id
            if model_id == "stokes":
                self.solver = StokesSolitonSolver()
            elif model_id == "platicon":
                self.solver = PlaticonSolver()
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
