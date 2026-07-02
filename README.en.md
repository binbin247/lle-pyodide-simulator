# CyberMicrocomb

> [!IMPORTANT]
> **Start immediately:** [Open CyberMicrocomb](https://binbin247.github.io/CyberMicrocomb/)
>
> **URL:** https://binbin247.github.io/CyberMicrocomb/
>
> No download, installation, or environment setup is required. Open the link
> above and start microcomb simulations directly in your browser.

![CyberMicrocomb promotional banner](./public/cybermicrocomb-promo.png)

[中文](./README.md) | [English](./README.en.md)

Interactive browser-based LLE simulator for microcomb dynamics.

A browser-only real-time Lugiato-Lefever equation simulator built with React,
TypeScript, Vite, Pyodide, NumPy, and a Web Worker.

The browser owns the interface. The numerical solver runs locally in a worker
through Pyodide, so there is no Flask/FastAPI backend and no server-side
compute once the page has loaded.

## Features

- Normalized parameter controls.
- English and Chinese UI toggle.
- Fixed grids: 256, 512, 1024, 2048, and 4096 points.
- Real-time parameter updates without resetting the current field.
- Plotly time-domain, spectrum, and intracavity-energy plots.
- Canvas waterfall history with a fixed 300-frame ring buffer.
- In-app documentation panel for the selected model, including equations,
  physical picture, demo workflows, and references.
- Time-domain, spectrum, energy, and evolution views for single-field,
  two-field, and three-field models.
- Raman self-frequency-shift diagnostics for pulse width and spectral shift;
  turnkey self-injection-locking diagnostics for locked detuning and state
  diagrams.
- JSON export with model ID, parameters, current complex fields, complete data
  for the four visible plots, waterfall histories, and model-specific
  diagnostics.
- First-order split-step LLE solvers for interactive mechanism models including
  D2/D3/D4, local mode shifts, coupled fields, Raman shock terms, and
  Raman-response convolution.
- User-adjustable integration timestep `dt`, with oversized values clamped by
  `max(|Dint|) * dt < pi` to avoid dispersion-phase aliasing.
- Static deployment target for GitHub Pages.

## Models

The page currently includes six interactive normalized models. Each model has
its own equation notes, physical picture, demo workflow, and references:

- [Standard soliton](./docs/models/standard-soliton.en.md): anomalous-dispersion
  single-field LLE for bright dissipative Kerr soliton simulations, with optional
  higher-order dispersion and Raman-shock perturbations.
- [Standard dark pulse (platicon)](./docs/models/standard-dark-pulse-platicon.en.md):
  normal-dispersion single-field LLE with a local mode shift for dark pulse /
  platicon simulations.
- [Stokes soliton](./docs/models/stokes-soliton.en.md): primary / Stokes
  two-field coupled LLE for Raman-driven Stokes soliton simulations.
- [Turnkey soliton (self-injection locking)](./docs/models/turnkey-soliton.en.md):
  a normalized self-injection-locking model for turnkey soliton microcombs.
- [Multicolor soliton](./docs/models/multicolor-soliton.en.md): primary / signal /
  idler three-field coupled LLE for multicolor interband soliton dynamics.
- [Raman soliton self-frequency shift](./docs/models/raman-soliton-ssfs.en.md):
  soliton self-frequency shift with an explicit Raman-response convolution.

In the web app, the `Docs` button next to the `MODEL` selector opens the
documentation panel for the currently selected model.

These models are intended for fast physical intuition and interactive
exploration. Different literature models can use different normalization and
sign conventions; use each model documentation page as the source of truth for
its equations, parameter definitions, and scope.

## Local Development

To extend CyberMicrocomb with your own models, UI changes, or documentation,
first fork the repository to your GitHub account, then clone your fork:

```bash
git clone https://github.com/<your-github-name>/CyberMicrocomb.git
cd CyberMicrocomb
```

Install dependencies and start the local development server:

```bash
npm install
npm run dev
```

Open the printed local Vite URL, normally:

```text
http://127.0.0.1:5173/
```

The first page load needs network access to fetch Pyodide and NumPy from the
Pyodide CDN. After the runtime is loaded, the current session keeps computing
locally in the browser.

For secondary development, you can use your own coding agent directly inside the
local repository, such as Claude Code, Codex, or another code assistant. Let the
agent inspect the project structure, then modify model equations, default
parameters, documentation, export data, or frontend visualizations. Commit the
changes to your fork; if you want to contribute them back, open a pull request
from your fork.

## GitHub Pages

The included workflow builds the app as a static site and deploys it to GitHub
Pages. In the repository settings, set Pages source to GitHub Actions, then push
to `main`.

For this repository name, the production base path is:

```text
/CyberMicrocomb/
```

The workflow sets `GITHUB_PAGES=true`, which makes Vite use that base path.
