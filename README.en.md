# CyberMicrocomb

https://binbin247.github.io/CyberMicrocomb/

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
- Simple first-order split-step LLE solver with D2/D3/D4 and optional Raman
  shock term.
- Adaptive timestep selection from `max(|Dint|)` to keep
  `max(|Dint|) * dt < pi` and avoid dispersion-phase aliasing.
- Static deployment target for GitHub Pages.

## Model

The normalized model is

```text
dpsi/dt = [-(1 + i alpha) + i Dint(mu) + i |psi|^2] psi
          + F + i tauR psi d_theta |psi|^2
```

where

```text
Dint(mu) = d2 mu^2 / 2 + d3 mu^3 / 6 + d4 mu^4 / 24
```

The v1 solver uses a simple first-order split-step update:

1. Time-domain Kerr/Raman update.
2. FFT.
3. Frequency-domain linear update.
4. IFFT.
5. Explicit pump update.

This is intended for interactive exploration, not final publication-grade
integration.

## Local Development

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

## Tests and Build

```bash
npm run test
npm run build
```

The test command runs Python NumPy solver checks for decay, grid rebuild, and
Raman finite output.

## GitHub Pages

The included workflow builds the app as a static site and deploys it to GitHub
Pages. In the repository settings, set Pages source to GitHub Actions, then push
to `main`.

For this repository name, the production base path is:

```text
/CyberMicrocomb/
```

The workflow sets `GITHUB_PAGES=true`, which makes Vite use that base path.
