from pathlib import Path


namespace = {}
solver_source = Path(__file__).resolve().parents[1] / "public" / "lle_solver.py"
exec(solver_source.read_text(encoding="utf-8"), namespace)
LLESolver = namespace["LLESolver"]


def configure(solver, n=256, **params):
    base = {
        "alpha": -2.0,
        "pump": 0.0,
        "d2": -0.02,
        "d3": 0.0,
        "d4": 0.0,
        "tauR": 0.0,
        "dt": 1e-3,
        "stepsPerFrame": 10,
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


if __name__ == "__main__":
    test_zero_pump_decay()
    test_grid_rebuild()
    test_basic_lle_finite_with_raman_toggle()
    print("solver tests passed")
