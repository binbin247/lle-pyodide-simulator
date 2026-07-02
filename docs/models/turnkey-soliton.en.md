# Turnkey soliton (self-injection locking)

[中文](./turnkey-soliton.md)

## Simulation Equations

This model describes an unisolated pump laser coupled to a microresonator through
self-injection locking. The browser implementation uses a normalized coupled
mechanism model based on the self-injection-locking supplementary material, with
the forward intracavity field $\psi(\phi,t)$, an internal backscattering variable
$\rho_B(t)$, and a feedback-controlled locked detuning.

At the dimensional level, the model still starts from the microresonator
input-output equation: the forward intracavity field $A$ decays at the loaded
rate $\kappa$, is driven by $\sqrt{\kappa_{\mathrm{ext}}}s_{\mathrm{in}}$, and
produces a backscattered field that returns to the laser. Self-injection locking
does not introduce a separately plotted backward soliton in this UI. Instead,
the returned light changes the laser frequency, so the effective pump-resonance
detuning $\delta_{\mathrm{lock}}$ depends on intracavity power and feedback
phase. The page uses the loss-half-linewidth normalization
$t=\kappa T/2$ and $\psi=\sqrt{2g/\kappa}\,A$.

The forward field is modeled as

$$
\begin{aligned}
\frac{\partial \psi}{\partial t}
&=-(1+i\alpha)\psi
+i\frac{d_2}{2}\frac{\partial^2\psi}{\partial \phi^2} \\
&\quad +i\left(|\psi|^2+2|\rho_B|^2\right)\psi
+i\beta\rho_B+F .
\end{aligned}
$$

The backscattering variable and locked detuning are represented by the normalized
feedback dynamics

$$
\begin{aligned}
\frac{d\rho_B}{dt}
&=-\left(1+i\alpha-2iP-i|\rho_B|^2\right)\rho_B \\
&\quad +i\beta \langle\psi\rangle ,
\end{aligned}
$$

$$
\begin{aligned}
\alpha(t)
&\approx \alpha_L
+K\,\mathrm{Im}\left[
\frac{e^{i\phi_\mathrm{fb}}\rho_B}{i\beta F}
\right].
\end{aligned}
$$

$P=\langle|\psi|^2\rangle$ is the normalized intracavity power,
$\alpha_L$ is the free-running laser detuning, $\beta$ is the normalized
backscattering amplitude, $K$ is the feedback locking bandwidth, $\phi_\mathrm{fb}$
is the feedback phase, and $F$ is the pump amplitude. The current UI does not
plot $\rho_B$ as a separate field; it is an internal variable that changes the
locked detuning and the forward-field dynamics.

## Physical Picture

The backscattered resonator field returns to the pump laser and shifts its
effective frequency. For suitable feedback phase and locking bandwidth, the laser
is pulled toward a soliton-accessible operating point. The soliton can then appear
after turn-on without a conventional fast frequency scan or active feedback loop.

Read the panels as follows:

- `Temporal field`: inspect whether the forward field $|\psi|^2$ forms a localized pulse.
- `Comb spectrum`: check whether the forward comb broadens into a soliton-like spectrum.
- `Intracavity energy`: look for a stable normalized forward-field intracavity
  power plateau, represented by $\langle|\psi|^2\rangle$.
- `Soliton state`: shows the Kerr-tilted response, locking equilibrium, and the
  current operating point. The black dot is the real-time locked detuning and
  normalized intracavity power.

The red dashed curve uses the same self-injection-locking equilibrium equation as
the solver; the black curve is the Kerr tilt.

## Demo

1. Select `Turnkey soliton (self-injection locking)` in `MODEL`.
2. Keep the defaults: `grid = 512`, `Pump power = sqrt(3)`, `D2 = 0.015`,
   `beta = 0.5`, `lockingBandwidth = 15`, `feedbackPhase = 0.3*pi`,
   `laserDetuning = 5`.
3. Click `Play` and check whether a stable localized pulse forms.
4. Scan `laserDetuning` to see how the free-running laser detuning changes the
   locked detuning and soliton access.
5. Scan `feedbackPhase` or `lockingBandwidth` to find more robust turnkey access.

This is an interactive mechanism model, not a full semiconductor laser rate-equation
simulation. It omits thermal dynamics, gain dynamics, and package-level details.

## References

- B. Shen et al., "Integrated turnkey soliton microcombs," *Nature* **582**, 365-369 (2020). [https://doi.org/10.1038/s41586-020-2358-x](https://doi.org/10.1038/s41586-020-2358-x)
- Supplementary information for "Integrated turnkey soliton microcombs."
