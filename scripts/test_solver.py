import math
from pathlib import Path

import numpy as np


namespace = {}
solver_source = Path(__file__).resolve().parents[1] / "public" / "lle_solver.py"
exec(solver_source.read_text(encoding="utf-8"), namespace)
LLESolver = namespace["LLESolver"]
StokesSolitonSolver = namespace["StokesSolitonSolver"]


def configure(solver, n=256, **params):
    base = {
        "alpha": -2.0,
        "pump": 0.0,
        "d2": -0.02,
        "d3": 0.0,
        "d4": 0.0,
        "tauR": 0.0,
        "dt": 8e-4,
        "stepsPerFrame": 320,
    }
    base.update(params)
    solver.configure({"n": n, "params": base, "reset": True})
    return base


def test_zero_pump_decay():
    solver = LLESolver()
    configure(solver, pump=0.0)
    before = solver.snapshot()["energy"]
    for _ in range(5):
        solver.run_steps()
    after = solver.snapshot()["energy"]
    assert after < before, (before, after)


def test_grid_rebuild():
    solver = LLESolver()
    configure(solver, n=256)
    assert len(solver.snapshot()["intensity"]) == 256
    configure(solver, n=512)
    assert len(solver.snapshot()["intensity"]) == 512
    assert solver.step == 0


def test_basic_lle_finite_with_raman_toggle():
    solver = LLESolver()
    configure(solver, pump=1.5, d3=0.01, d4=-0.001, tauR=0.02)
    for _ in range(20):
        snap = solver.run_steps()
    assert snap["peak"] > 0
    assert all(value == value for value in snap["intensity"])


def test_adaptive_dt_satisfies_dispersion_aliasing_bound():
    solver = LLESolver()
    configure(solver, n=4096, d2=-0.25, d3=0.05, d4=0.01, dt=0.005)
    params = solver.snapshot()["normalizedParams"]
    dint = (
        params["d2"] * solver.mu**2 / 2.0
        + params["d3"] * solver.mu**3 / 6.0
        + params["d4"] * solver.mu**4 / 24.0
    )
    max_phase_per_step = float(np.max(np.abs(dint)) * params["dt"])
    assert max_phase_per_step < math.pi, max_phase_per_step
    assert params["dt"] < 8e-4


def test_user_dt_is_preserved_when_aliasing_safe():
    solver = LLESolver()
    configure(solver, n=512, d2=0.0, d3=0.0, d4=0.0, dt=2e-4)
    params = solver.snapshot()["normalizedParams"]
    assert params["dt"] == 2e-4


def configure_stokes(solver, n=256, **params):
    base = {
        "alphaP": 20.0,
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
        "dt": 5e-5,
        "stepsPerFrame": 10,
    }
    base.update(params)
    solver.configure({"n": n, "params": base, "reset": True})
    return base


def test_stokes_solver_snapshot_is_finite():
    solver = StokesSolitonSolver()
    configure_stokes(solver)
    for _ in range(5):
        snap = solver.run_steps()
    assert snap["modelId"] == "stokes"
    assert len(snap["primaryIntensity"]) == 256
    assert len(snap["stokesIntensity"]) == 256
    assert np.all(np.isfinite(snap["primaryIntensity"]))
    assert np.all(np.isfinite(snap["stokesIntensity"]))


def test_stokes_grid_rebuild_resets_both_fields():
    solver = StokesSolitonSolver()
    configure_stokes(solver, n=256)
    solver.run_steps()
    configure_stokes(solver, n=512)
    snap = solver.snapshot()
    assert len(snap["primaryIntensity"]) == 512
    assert len(snap["stokesIntensity"]) == 512
    assert solver.step == 0


def test_stokes_export_contains_dual_fields():
    solver = StokesSolitonSolver()
    configure_stokes(solver, n=256)
    solver.run_steps()
    state = solver.export_state()
    assert state["modelId"] == "stokes"
    assert len(state["psiP_real"]) == 256
    assert len(state["psiP_imag"]) == 256
    assert len(state["psiS_real"]) == 256
    assert len(state["psiS_imag"]) == 256


def test_stokes_adaptive_dt_satisfies_aliasing_bound():
    solver = StokesSolitonSolver()
    configure_stokes(solver, n=4096, d2P=0.25, d2S=-0.25, fsrMismatch=1.0, dt=0.005)
    params = solver.snapshot()["normalizedParams"]
    primary_phase = np.abs(params["d2P"] * solver.mu**2)
    stokes_phase = np.abs(params["d2S"] * solver.mu**2 + params["fsrMismatch"] * solver.mu)
    max_phase_per_step = float(max(np.max(primary_phase), np.max(stokes_phase)) * params["dt"])
    assert max_phase_per_step < math.pi, max_phase_per_step
    assert params["dt"] < 5e-5


def test_stokes_defaults_follow_matlab_system_parameters():
    solver = StokesSolitonSolver()
    configure_stokes(solver, n=128)
    params = solver.snapshot()["normalizedParams"]
    assert params["overlap"] == 0.5
    assert params["fR"] == 0.18
    assert params["ramanGainP"] == 0.35 * 0.18 * 2.0
    assert params["ramanGainS"] == 0.35 * 0.18 * 2.0
    assert params["wavelengthRatio"] == 1550.0 / 1630.0
    assert params["tauR"] == 3.3e-4


def test_stokes_default_uses_fast_fig_s1_scan_stride():
    solver = StokesSolitonSolver()
    params = solver.snapshot()["normalizedParams"]
    assert params["stepsPerFrame"] == 1000
    assert len(solver.snapshot()["primaryIntensity"]) == 1024


def test_stokes_detuning_is_fixed_at_zero():
    solver = StokesSolitonSolver()
    configure_stokes(solver, n=128, alphaS=21.93)
    params = solver.snapshot()["normalizedParams"]
    assert params["alphaS"] == 0.0


if __name__ == "__main__":
    test_zero_pump_decay()
    test_grid_rebuild()
    test_basic_lle_finite_with_raman_toggle()
    test_adaptive_dt_satisfies_dispersion_aliasing_bound()
    test_user_dt_is_preserved_when_aliasing_safe()
    test_stokes_solver_snapshot_is_finite()
    test_stokes_grid_rebuild_resets_both_fields()
    test_stokes_export_contains_dual_fields()
    test_stokes_adaptive_dt_satisfies_aliasing_bound()
    test_stokes_defaults_follow_matlab_system_parameters()
    test_stokes_default_uses_fast_fig_s1_scan_stride()
    test_stokes_detuning_is_fixed_at_zero()
    print("solver tests passed")
