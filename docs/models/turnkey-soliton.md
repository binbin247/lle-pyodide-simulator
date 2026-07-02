# Turnkey soliton (self-injection locking)

[English](./turnkey-soliton.en.md)

## 仿真的方程

该模型描述未隔离泵浦激光器和微腔之间的自注入锁定。浏览器实现采用
基于自注入锁定补充材料的归一化 coupled model，包含腔内主传播场
$\psi(\phi,t)$、内部反向散射变量 $\rho_B(t)$ 和由反馈决定的锁定失谐。

物理量层面仍从微腔输入输出方程出发：腔内主场 $A$ 以总损耗 $\kappa$ 衰减，
由外部输入 $\sqrt{\kappa_{\mathrm{ext}}}s_{\mathrm{in}}$ 驱动，并通过后向散射
产生返回激光器的反馈场。自注入锁定的效果不是在 LLE 中额外加入一个独立可视化的
反向孤子，而是通过返回光改变激光频率，从而使有效泵浦-腔模失谐
$\delta_{\mathrm{lock}}$ 随腔内功率和反馈相位动态调整。页面采用
$t=\kappa T/2$、$\psi=\sqrt{2g/\kappa}\,A$ 的损耗半宽归一化。

主场方程写成

$$
\begin{aligned}
\frac{\partial \psi}{\partial t}
&=-(1+i\alpha)\psi
+i\frac{d_2}{2}\frac{\partial^2\psi}{\partial \phi^2} \\
&\quad +i\left(|\psi|^2+2|\rho_B|^2\right)\psi
+i\beta\rho_B+F .
\end{aligned}
$$

反向散射变量和锁定失谐用简化的归一化动力学表示：

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

这里 $P=\langle|\psi|^2\rangle$ 是归一化腔内功率，$\alpha_L$ 是自由运行激光与腔模的失谐，
$\beta$ 是归一化后向散射强度，$K$ 是反馈锁定带宽，$\phi_\mathrm{fb}$ 是反馈相位，
$F$ 是泵浦幅度。
当前界面不单独绘制 $\rho_B$；它作为内部变量影响锁定后的有效失谐和主场演化。

## 物理图像

Turnkey soliton 的核心是：腔内后向散射光返回激光器，改变激光的有效频率。
当反馈相位和锁定带宽合适时，激光会被拉到能直接进入 soliton existence range 的工作点。
因此系统不需要传统的快速扫频或主动反馈，也能在打开泵浦后进入孤子态。

四张图可以这样读：

- `Temporal field`：查看主传播场 $|\psi|^2$ 是否形成局域脉冲。
- `Comb spectrum`：确认主场 comb 是否变宽并形成 soliton-like spectrum。
- `Intracavity energy`：检查 $\langle|\psi|^2\rangle$ 表示的归一化主场腔内功率是否锁定到稳定平台。
- `Soliton state`：显示 Kerr-tilted response、locking equilibrium 和当前状态点。
  黑点为实时的锁定失谐与归一化腔内功率。

相图中的红色虚线使用和求解器一致的自注入锁定平衡方程；黑色实线表示 Kerr tilt。

## Demo

1. 在 `MODEL` 中选择 `Turnkey soliton (self-injection locking)`。
2. 保持默认值：`grid = 512`, `Pump power = sqrt(3)`, `D2 = 0.015`,
   `beta = 0.5`, `lockingBandwidth = 15`, `feedbackPhase = 0.3*pi`,
   `laserDetuning = 5`。
3. 点击 `Play`，观察主场是否形成稳定局域脉冲。
4. 扫描 `laserDetuning`，比较自由激光失谐变化对 locked detuning 和孤子进入过程的影响。
5. 扫描 `feedbackPhase` 或 `lockingBandwidth`，寻找 turnkey access 较稳定的区域。

该模型用于交互式理解 self-injection locking 机制。它不是完整的半导体激光器速率方程模型，
也没有包含热效应、激光增益动态和器件封装细节。

## 参考文献

- B. Shen et al., "Integrated turnkey soliton microcombs," *Nature* **582**, 365-369 (2020). [https://doi.org/10.1038/s41586-020-2358-x](https://doi.org/10.1038/s41586-020-2358-x)
- Supplementary information for "Integrated turnkey soliton microcombs."
