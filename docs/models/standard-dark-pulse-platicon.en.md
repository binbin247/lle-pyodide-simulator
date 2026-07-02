# Standard dark pulse (platicon)

[中文](./standard-dark-pulse-platicon.md)

## Simulation equations

This is a normal-dispersion single-field LLE for dark-pulse / platicon dynamics.
It keeps second-order dispersion and one local mode shift, and intentionally
omits Raman, $d_3$, and $d_4$:

$$
\frac{\partial \psi}{\partial t}
=
\left[-(1+i\alpha)+iD_{\mathrm{int}}(\mu)+i|\psi|^2\right]\psi+F.
$$

The integrated dispersion is

$$
D_{\mathrm{int}}(\mu)
=
\frac{d_2\mu^2}{2}
+\Delta_{\mathrm{shift}}\delta_{\mu,\mu_{\mathrm{shift}}}.
$$

Here $d_2>0$ is normal dispersion in the current normalized convention,
$\mu_{\mathrm{shift}}$ is the selected integer mode, and
$\Delta_{\mathrm{shift}}$ is the mode-shift strength normalized to $\kappa/2$.
A positive `Mode shift strength` increases $D_{\mathrm{int}}$ at that mode. The
implementation shifts one mode only; it does not automatically perturb
$\pm\mu$ symmetrically.

## Physical picture

In normal dispersion, a bright soliton is not the natural stable state. The system
can instead form switching fronts between two continuous-wave backgrounds. These
fronts enclose a broad dark notch or flat-top structure: a dark pulse, also called
a platicon.

The local mode shift changes the integrated dispersion of one mode, emulating an
avoided mode crossing or a local perturbation near the pumped mode. This provides
a practical route for a normal-dispersion cavity to enter a low-noise dark-pulse
state.

Read the four plots as follows:

- `Temporal field`: look for a dark notch or flat-top switching-front structure
  on a high background.
- `Comb spectrum`: check the normal-dispersion comb and the lines near the
  shifted mode.
- `Intracavity energy`: check whether the dark-pulse state settles.
- `Temporal evolution`: check whether the notch remains, drifts, or breaks up.

## Demo

1. Select `Standard dark pulse (platicon)` in `MODEL`.
2. Keep the defaults: `grid = 512`, `Detuning = 4`, `Pump power = 3.94`,
   `D2 = 0.02`, `Mode shift position = 0`, `Mode shift strength = 4`.
3. Click `Play` and look for a dark notch on a high background.
4. Scan `Mode shift strength`: a weak shift may not trigger a stable dark pulse,
   while a very strong shift may create irregular spectra.
5. Change `Mode shift position` to see how the local perturbation reshapes the
   comb spectrum.
6. Scan `Detuning` and compare the platicon width, energy, and spectral bandwidth.

This model is for teaching and fast exploration. It isolates the role of normal
dispersion and a local mode perturbation; it does not include thermal dynamics,
full mode-family coupling, or a complete avoided-crossing model.

## References

- X. Xue, Y. Xuan, Y. Liu, P.-H. Wang, S. Chen, J. Wang, D. E. Leaird, M. Qi, and A. M. Weiner, "Mode-locked dark pulse Kerr combs in normal-dispersion microresonators," *Nature Photonics* **9**, 594-600 (2015). <https://doi.org/10.1038/nphoton.2015.137>
- H. Wang, B. Shen, Y. Yu, Z. Yuan, C. Bao, W. Jin, L. Chang, M. A. Leal, A. Feshali, M. Paniccia, J. E. Bowers, and K. Vahala, "Self-regulating soliton switching waves in microresonators," *Physical Review A* **106**, 053508 (2022). <https://doi.org/10.1103/PhysRevA.106.053508>
