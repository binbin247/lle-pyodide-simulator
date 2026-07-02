# Standard dark pulse (platicon)

[English](./standard-dark-pulse-platicon.en.md)

## 仿真的方程

这是 normal-dispersion 的单场 LLE，用于演示 dark pulse / platicon。它保留二阶色散和一个局部
mode shift，不包含 Raman、$d_3$ 或 $d_4$：

$$
\frac{\partial \psi}{\partial t}
=
\left[-(1+i\alpha)+iD_{\mathrm{int}}(\mu)+i|\psi|^2\right]\psi+F.
$$

色散写成

$$
D_{\mathrm{int}}(\mu)
=
\frac{d_2\mu^2}{2}
+\Delta_{\mathrm{shift}}\delta_{\mu,\mu_{\mathrm{shift}}}.
$$

这里 $d_2>0$ 表示当前归一化约定下的 normal dispersion。
$\mu_{\mathrm{shift}}$ 是被扰动的整数模式，$\Delta_{\mathrm{shift}}$ 是归一化到
$\kappa/2$ 的模式偏移强度。正的 `Mode shift strength` 表示提高该模式的
$D_{\mathrm{int}}$。当前实现只移动一个模式，不自动同时移动 $\pm\mu$。

## 物理图像

在 normal dispersion 中，bright soliton 不是自然稳定态。系统更容易形成两个连续波背景之间的
switching fronts；这些 fronts 围成一个宽的暗缺口或平顶结构，就是 dark pulse / platicon。

局部 mode shift 的作用是人为改变某个模式的 integrated dispersion，等效模拟 avoided mode
crossing 或泵浦附近的局部模式扰动。它为 normal-dispersion 系统提供进入低噪声 dark-pulse
态的通道。

四张图可以这样读：

- `Temporal field`：看高背景上是否出现宽暗缺口或 flat-top switching-front 结构。
- `Comb spectrum`：看 normal-dispersion comb 是否形成，并注意被扰动模式附近的谱线变化。
- `Intracavity energy`：看 dark-pulse 态是否稳定。
- `Temporal evolution`：看暗缺口是否保持、漂移或破裂。

## Demo

1. 在 `MODEL` 中选择 `Standard dark pulse (platicon)`。
2. 保持默认值：`grid = 512`, `Detuning = 4`, `Pump power = 3.94`,
   `D2 = 0.02`, `Mode shift position = 0`, `Mode shift strength = 4`。
3. 点击 `Play`，观察时域中是否出现高背景上的暗缺口。
4. 扫描 `Mode shift strength`：太弱可能无法触发稳定 dark pulse，太强可能引入不规则谱。
5. 改变 `Mode shift position`，观察不同局部模式扰动对 comb spectrum 的影响。
6. 扫描 `Detuning`，比较 platicon 宽度、能量和频谱带宽的变化。

这个模型的目标是教学和快速探索：它突出 normal dispersion 与局部模式扰动的作用，不描述热效应、
多模族动力学或完整 avoided-crossing 耦合。

## 参考文献

- X. Xue, Y. Xuan, Y. Liu, P.-H. Wang, S. Chen, J. Wang, D. E. Leaird, M. Qi, and A. M. Weiner, "Mode-locked dark pulse Kerr combs in normal-dispersion microresonators," *Nature Photonics* **9**, 594-600 (2015). <https://doi.org/10.1038/nphoton.2015.137>
- H. Wang, B. Shen, Y. Yu, Z. Yuan, C. Bao, W. Jin, L. Chang, M. A. Leal, A. Feshali, M. Paniccia, J. E. Bowers, and K. Vahala, "Self-regulating soliton switching waves in microresonators," *Physical Review A* **106**, 053508 (2022). <https://doi.org/10.1103/PhysRevA.106.053508>
