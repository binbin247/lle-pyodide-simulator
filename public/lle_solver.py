import json
import math

import numpy as np


class LLESolver:
    def __init__(self):
        self.rng = np.random.default_rng(20260701)
        self.n = 512
        self.step = 0
        self.t = 0.0
        self.params = {
            "alpha": -5.0,
            "pump": 3.94,
            "d2": -0.0444,
            "d3": 0.0,
            "d4": 0.0,
            "tauR": 0.0,
            "dt": 8e-4,
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
            self.psi *= np.exp((1j * abs2 - tau_r * d_abs2) * dt)
        else:
            self.psi *= np.exp(1j * abs2 * dt)

        psi_freq = np.fft.fft(self.psi)
        psi_freq *= self._linear
        self.psi = np.fft.ifft(psi_freq)
        self.psi += self.params["pump"] * dt

        if not np.all(np.isfinite(self.psi)):
            raise FloatingPointError("LLE state contains NaN or Inf; reduce dt or pump.")

        self.step += 1
        self.t += dt

    def _refresh_linear(self):
        p = self.params
        dint = (
            p["d2"] * self.mu**2 / 2.0
            + p["d3"] * self.mu**3 / 6.0
            + p["d4"] * self.mu**4 / 24.0
        )
        linear = -(1.0 + 1j * p["alpha"]) + 1j * dint
        self._linear = np.exp(linear * p["dt"])

    def _initial_state(self, n):
        noise = 1e-3 * (self.rng.standard_normal(n) + 1j * self.rng.standard_normal(n))
        return noise.astype(np.complex128)

    @staticmethod
    def _make_mu(n):
        return np.fft.fftfreq(n, d=1.0 / n)

    @staticmethod
    def _clean_params(params):
        cleaned = {
            "alpha": float(params.get("alpha", 0.0)),
            "pump": max(0.0, float(params.get("pump", 0.0))),
            "d2": float(params.get("d2", 0.0)),
            "d3": float(params.get("d3", 0.0)),
            "d4": float(params.get("d4", 0.0)),
            "tauR": float(params.get("tauR", 0.0)),
            "dt": max(1e-7, float(params.get("dt", 8e-4))),
            "stepsPerFrame": max(1, int(round(float(params.get("stepsPerFrame", 50))))),
        }
        for key, value in cleaned.items():
            if not math.isfinite(value):
                raise ValueError(f"Parameter {key} is not finite.")
        return cleaned
