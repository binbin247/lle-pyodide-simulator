import math
from pathlib import Path

import numpy as np


namespace = {}
solver_source = Path(__file__).resolve().parents[1] / "public" / "lle_solver.py"
exec(solver_source.read_text(encoding="utf-8"), namespace)
LLESolver = namespace["LLESolver"]
PlaticonSolver = namespace["PlaticonSolver"]
StokesSolitonSolver = namespace["StokesSolitonSolver"]
TurnkeySolitonSolver = namespace["TurnkeySolitonSolver"]
MulticolorSolitonSolver = namespace["MulticolorSolitonSolver"]
RamanSsfSolver = namespace["RamanSsfSolver"]


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


def test_standard_defaults_use_soliton_ansatz_seed():
    solver = LLESolver()
    snap = solver.snapshot()
    assert snap["normalizedParams"]["alpha"] == 10.0
    assert snap["peak"] > 1.0
    assert snap["energy"] > 0.01


def configure_platicon(solver, n=256, **params):
    base = {
        "alpha": 4.0,
        "pump": 3.94,
        "d2": 0.02,
        "modeShiftMu": 0,
        "modeShiftStrength": 4.0,
        "dt": 8e-4,
        "stepsPerFrame": 50,
    }
    base.update(params)
    solver.configure({"n": n, "params": base, "reset": True})
    return base


def test_platicon_solver_snapshot_is_finite():
    solver = PlaticonSolver()
    configure_platicon(solver)
    for _ in range(3):
        snap = solver.run_steps()
    assert snap["modelId"] == "platicon"
    assert len(snap["intensity"]) == 256
    assert np.all(np.isfinite(snap["intensity"]))
    assert np.all(np.isfinite(snap["spectrumDb"]))


def test_platicon_default_seed_has_dark_notch():
    solver = PlaticonSolver()
    snap = solver.snapshot()
    intensity = snap["intensity"]
    assert snap["modelId"] == "platicon"
    assert snap["peak"] > 0.1
    assert np.min(intensity) < 0.5 * np.max(intensity)
    assert snap["energy"] > 0.01


def test_platicon_mode_shift_changes_only_selected_mode():
    solver = PlaticonSolver()
    configure_platicon(solver, n=256, d2=0.0, modeShiftMu=7, modeShiftStrength=3.5)
    dint = solver._dint()
    shifted = np.where(solver.mu == 7)[0]
    assert len(shifted) == 1
    assert dint[shifted[0]] == 3.5
    assert np.count_nonzero(np.abs(dint) > 1e-12) == 1


def test_platicon_mode_shift_rounds_and_clamps_to_grid():
    solver = PlaticonSolver()
    configure_platicon(solver, n=256, modeShiftMu=7.6)
    assert solver.snapshot()["normalizedParams"]["modeShiftMu"] == 8
    configure_platicon(solver, n=256, modeShiftMu=9999)
    assert solver.snapshot()["normalizedParams"]["modeShiftMu"] == 127
    configure_platicon(solver, n=256, modeShiftMu=-9999)
    assert solver.snapshot()["normalizedParams"]["modeShiftMu"] == -128


def test_platicon_adaptive_dt_satisfies_dispersion_aliasing_bound():
    solver = PlaticonSolver()
    configure_platicon(
        solver,
        n=4096,
        d2=0.25,
        modeShiftMu=0,
        modeShiftStrength=20.0,
        dt=0.005,
    )
    params = solver.snapshot()["normalizedParams"]
    max_phase_per_step = float(np.max(np.abs(solver._dint())) * params["dt"])
    assert max_phase_per_step < math.pi, max_phase_per_step
    assert params["dt"] < 8e-4


def test_platicon_grid_rebuild_resets_field():
    solver = PlaticonSolver()
    configure_platicon(solver, n=256)
    solver.run_steps()
    configure_platicon(solver, n=512)
    snap = solver.snapshot()
    assert len(snap["intensity"]) == 512
    assert solver.step == 0


def configure_stokes(solver, n=256, **params):
    base = {
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


def configure_turnkey(solver, n=128, **params):
    base = {
        "laserDetuning": 5.0,
        "pump": math.sqrt(3.0),
        "d2": 0.015,
        "beta": 0.5,
        "lockingBandwidth": 15.0,
        "feedbackPhase": 0.3 * math.pi,
        "noise": 1e-5,
        "dt": 5e-4,
        "stepsPerFrame": 10,
    }
    base.update(params)
    solver.configure({"n": n, "params": base, "reset": True})
    return base


def test_turnkey_solver_snapshot_and_export_are_finite():
    solver = TurnkeySolitonSolver()
    configure_turnkey(solver)
    for _ in range(3):
        snap = solver.run_steps()
    assert snap["modelId"] == "turnkey"
    assert len(snap["primaryIntensity"]) == 128
    assert len(snap["backwardIntensity"]) == 128
    assert math.isfinite(snap["lockedDetuning"])
    assert np.all(np.isfinite(snap["primaryIntensity"]))
    state = solver.export_state()
    assert len(state["psiP_real"]) == 128
    assert isinstance(state["rhoB_real"], float)


def test_turnkey_locked_detuning_responds_to_feedback_parameters():
    solver = TurnkeySolitonSolver()
    configure_turnkey(solver, lockingBandwidth=0.0)
    for _ in range(3):
        solver.run_steps()
    unlocked = solver.snapshot()["lockedDetuning"]
    configure_turnkey(solver, lockingBandwidth=15.0, feedbackPhase=0.3 * math.pi)
    for _ in range(3):
        solver.run_steps()
    locked = solver.snapshot()["lockedDetuning"]
    assert math.isfinite(locked)
    assert abs(locked - unlocked) > 1e-9


def test_turnkey_adaptive_dt_satisfies_aliasing_bound():
    solver = TurnkeySolitonSolver()
    configure_turnkey(solver, n=4096, d2=0.25, dt=0.005)
    params = solver.snapshot()["normalizedParams"]
    max_phase_per_step = float(np.max(np.abs(params["d2"] * solver.mu**2)) * params["dt"])
    assert max_phase_per_step < math.pi, max_phase_per_step


def configure_multicolor(solver, n=128, **params):
    base = {
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
        "dt": 2e-5,
        "stepsPerFrame": 10,
    }
    base.update(params)
    solver.configure({"n": n, "params": base, "reset": True})
    return base


def test_multicolor_solver_snapshot_and_export_are_finite():
    solver = MulticolorSolitonSolver()
    configure_multicolor(solver)
    for _ in range(3):
        snap = solver.run_steps()
    assert snap["modelId"] == "multicolor"
    assert len(snap["primaryIntensity"]) == 128
    assert len(snap["signalIntensity"]) == 128
    assert len(snap["idlerIntensity"]) == 128
    assert np.all(np.isfinite(snap["primaryIntensity"]))
    assert np.all(np.isfinite(snap["signalIntensity"]))
    assert np.all(np.isfinite(snap["idlerIntensity"]))
    state = solver.export_state()
    assert len(state["psiP_real"]) == 128
    assert len(state["psiS_real"]) == 128
    assert len(state["psiI_real"]) == 128


def test_multicolor_adaptive_dt_satisfies_aliasing_bound():
    solver = MulticolorSolitonSolver()
    configure_multicolor(
        solver,
        n=4096,
        d2P=1.0,
        d2S=-1.0,
        d2I=1.0,
        fsrMismatchI=40.0,
        dt=0.005,
    )
    params = solver.snapshot()["normalizedParams"]
    primary_phase = np.abs(params["d2P"] * solver.mu**2 / 2.0)
    signal_phase = np.abs(params["fsrMismatchS"] * solver.mu + params["d2S"] * solver.mu**2 / 2.0)
    idler_phase = np.abs(params["fsrMismatchI"] * solver.mu + params["d2I"] * solver.mu**2 / 2.0)
    max_phase_per_step = float(max(np.max(primary_phase), np.max(signal_phase), np.max(idler_phase)) * params["dt"])
    assert max_phase_per_step < math.pi, max_phase_per_step


def configure_raman(solver, n=128, **params):
    base = {
        "dtnNorm": 11.829136663739904,
        "ffNorm": 9.784017373364096,
        "d2Norm": 1.65414364640884,
        "fR": 0.02,
        "tau1Fs": 11.1,
        "tau2Fs": 35.0,
        "fsrGHz": 1000.0,
        "qMillion": 4.0,
        "wavelengthNm": 1550.0,
        "noise": 1e-4,
        "dt": 5e-5,
        "stepsPerFrame": 10,
    }
    base.update(params)
    solver.configure({"n": n, "params": base, "reset": True})
    return base


def test_raman_solver_snapshot_metrics_and_export_are_finite():
    solver = RamanSsfSolver()
    configure_raman(solver)
    for _ in range(3):
        snap = solver.run_steps()
    assert snap["modelId"] == "raman"
    assert len(snap["intensity"]) == 128
    assert np.all(np.isfinite(snap["intensity"]))
    assert math.isfinite(snap["pulseWidthFs"])
    assert math.isfinite(snap["selfFrequencyShiftThz"])
    assert snap["referenceParams"]["fsrGHz"] == 1000.0
    state = solver.export_state()
    assert len(state["psi_real"]) == 128
    assert "referenceParams" in state


def test_raman_adaptive_dt_satisfies_aliasing_bound():
    solver = RamanSsfSolver()
    configure_raman(solver, n=4096, d2Norm=8.0, dt=0.005)
    params = solver.snapshot()["normalizedParams"]
    max_phase_per_step = float(np.max(np.abs(params["d2Norm"] * solver.mu**2 / 2.0)) * params["dt"])
    assert max_phase_per_step < math.pi, max_phase_per_step


if __name__ == "__main__":
    test_zero_pump_decay()
    test_grid_rebuild()
    test_basic_lle_finite_with_raman_toggle()
    test_adaptive_dt_satisfies_dispersion_aliasing_bound()
    test_user_dt_is_preserved_when_aliasing_safe()
    test_standard_defaults_use_soliton_ansatz_seed()
    test_platicon_solver_snapshot_is_finite()
    test_platicon_default_seed_has_dark_notch()
    test_platicon_mode_shift_changes_only_selected_mode()
    test_platicon_mode_shift_rounds_and_clamps_to_grid()
    test_platicon_adaptive_dt_satisfies_dispersion_aliasing_bound()
    test_platicon_grid_rebuild_resets_field()
    test_stokes_solver_snapshot_is_finite()
    test_stokes_grid_rebuild_resets_both_fields()
    test_stokes_export_contains_dual_fields()
    test_stokes_adaptive_dt_satisfies_aliasing_bound()
    test_stokes_defaults_follow_matlab_system_parameters()
    test_stokes_default_uses_fast_fig_s1_scan_stride()
    test_stokes_detuning_is_fixed_at_zero()
    test_turnkey_solver_snapshot_and_export_are_finite()
    test_turnkey_locked_detuning_responds_to_feedback_parameters()
    test_turnkey_adaptive_dt_satisfies_aliasing_bound()
    test_multicolor_solver_snapshot_and_export_are_finite()
    test_multicolor_adaptive_dt_satisfies_aliasing_bound()
    test_raman_solver_snapshot_metrics_and_export_are_finite()
    test_raman_adaptive_dt_satisfies_aliasing_bound()
    print("solver tests passed")
