# Standard soliton

[中文](./standard-soliton.md)

## Simulation equations

This is a single-field normalized Lugiato-Lefever equation (LLE) for bright
dissipative Kerr solitons in an anomalous-dispersion microresonator. The slow
time is $t$, the azimuthal coordinate is $\phi\in[-\pi,\pi)$, the relative mode
number is $\mu$, and the normalized intracavity field is $\psi(\phi,t)$:

$$
\frac{\partial \psi}{\partial t}
=
\left[-(1+i\alpha)+iD_{\mathrm{int}}(\mu)+i|\psi|^2\right]\psi
+F+i\tau_R\psi\frac{\partial |\psi|^2}{\partial \phi}.
$$

The frequency-domain integrated dispersion is

$$
D_{\mathrm{int}}(\mu)
=
\frac{d_2\mu^2}{2}
+\frac{d_3\mu^3}{6}
+\frac{d_4\mu^4}{24}.
$$

Here $\alpha$ is the pump-resonance detuning, $F$ is the pump amplitude,
$d_2,d_3,d_4$ are normalized integrated-dispersion coefficients, and $\tau_R$ is
the Raman shock coefficient. The solver uses a first-order split-step update:
Kerr/Raman terms in the time domain, loss-detuning-dispersion terms in the
frequency domain, and explicit pump injection.

## Physical picture

The standard soliton is set by a compact balance: the continuous-wave pump
compensates cavity loss, Kerr nonlinearity gives an intensity-dependent phase
shift, and anomalous dispersion ($d_2<0$) balances that nonlinear phase to form a
localized bright pulse.

Read the four plots as follows:

- `Temporal field`: check whether $|\psi|^2$ forms a narrow bright peak.
- `Comb spectrum`: check whether a broad comb envelope appears around the pump.
- `Intracavity energy`: check whether the mean intracavity energy settles.
- `Temporal evolution`: check whether the pulse drifts, splits, or destabilizes.

Increasing detuning usually changes the pulse width and peak intensity. Nonzero
$d_3$ or $d_4$ adds higher-order dispersion, which can generate asymmetric
spectra or dispersive-wave features. Nonzero $\tau_R$ changes the nonlinear
phase through $i\tau_R\psi\partial_\phi|\psi|^2$, enabling interactive
exploration of Raman self-frequency-shift-like behavior.

## Demo

1. Select `Standard soliton` in `MODEL`.
2. Keep the defaults: `grid = 512`, `Detuning = 10`, `Pump power = 3.94`,
   `D2 = -0.0444`, `D3 = 0`, `D4 = 0`, `tauR = 0`.
3. Click `Play` and first confirm that a stable bright pulse appears in the time
   domain.
4. Slowly scan `Detuning` and compare the pulse width, peak intensity, and
   energy trace.
5. Set `D3` or `D4` to a nonzero value to observe spectral asymmetry or narrow
   dispersive-wave-like features.
6. Increase `tauR` slightly from 0 to inspect Raman-induced pulse and spectral
   shifts.

If the state diverges or the spectrum becomes numerically noisy, reduce `dt` or
lower `Pump power` first. The solver clamps oversized timesteps using
$\max |D_{\mathrm{int}}|\,dt < \pi$ to reduce dispersion-phase aliasing, but
this does not replace a higher-order publication-grade integrator.

## References

- T. Herr, V. Brasch, J. D. Jost, C. Y. Wang, N. M. Kondratiev, M. L. Gorodetsky, and T. J. Kippenberg, "Temporal solitons in optical microresonators," *Nature Photonics* **8**, 145-152 (2014). <https://doi.org/10.1038/nphoton.2013.343>
