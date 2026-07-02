# Raman soliton self-frequency shift

[中文](./raman-soliton-ssfs.md)

## Simulation Equations

This model demonstrates soliton self-frequency shift (SSFS) from a Raman
convolution. It is different from the simplified Raman shock term in
`Standard soliton`: here the delayed Raman response is represented by a response
function and an explicit convolution. The implementation follows
`/Users/binbin/Library/CloudStorage/OneDrive-个人/桌面/LN SSFS/Simulation/simulation2026`.

The normalized LLE is

$$
\frac{\partial \psi}{\partial t}
=-(1+i\alpha)\psi
+i\frac{d_2}{2}\frac{\partial^2\psi}{\partial\phi^2}
+i(1-f_R)|\psi|^2\psi
+\psi\, f_R\int h_R(\phi-\phi')|\psi(\phi')|^2\,d\phi'
+F .
$$

The browser solver evaluates the convolution by FFT:

$$
R_\mathrm{conv} =
i\,\mathcal{F}^{-1}\left[
\mathcal{F}\{|\psi|^2\}\mathcal{F}\{h_R\}
\right]\Delta\phi .
$$

The default Raman response uses the damped-oscillator form from the reference
code, controlled by `tau1Fs`, `tau2Fs`, and `fR`. The Raman strength is ramped
from zero to the requested value at startup to reduce numerical jumps.

## Physical Picture

The Raman response is delayed rather than instantaneous. A soliton intensity peak
drives a delayed nonlinear response, breaking spectral symmetry and shifting the
spectral centroid. This is the soliton self-frequency shift.

In addition to the four standard plots, this model shows:

- `pulse width fs`: the time-domain intensity FWHM converted with the selected `FSR`.
- `SSFS THz`: a spectral-power-centroid estimate of the self-frequency shift.

## Demo

1. Select `Raman soliton self-frequency shift` in `MODEL`.
2. Keep the defaults: `grid = 512`, `ffNorm ≈ 9.78`, `dtnNorm ≈ 11.83`,
   `fR = 0.020`, `tau1Fs = 11.1`, `tau2Fs = 35`, `FSR = 1000 GHz`,
   `Q = 4e6`.
3. Click `Play` and confirm that a stable soliton forms.
4. Watch whether `pulse width fs` and `SSFS THz` converge.
5. Scan `dtnNorm` to compare how pulse width and SSFS vary with detuning. Higher
   detuning strengthens the self-frequency shift, but it is also closer to a
   drop-out boundary, so increase it slowly while watching the energy trace.
6. Scan `fR` or `tau1Fs/tau2Fs` to test the Raman response.

This is a lightweight real-time SSFS model. v1 does not use SciPy curve fitting;
the pulse width and SSFS values are fast estimates for interactive exploration.

## References

- Local reference implementation: `/Users/binbin/Library/CloudStorage/OneDrive-个人/桌面/LN SSFS/Simulation/simulation2026/Soliton.py`.
- Raman response and SSFS parameter choices follow the local `simulation2026` sweep configuration used during development.
