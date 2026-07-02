# Standard soliton

[English](./standard-soliton.en.md)

## 仿真的方程

这是单场、归一化的 Lugiato-Lefever equation (LLE)，用于描述异常色散微腔中的 bright
dissipative Kerr soliton。慢时间为 $t$，环向坐标为 $\phi\in[-\pi,\pi)$，相对模式编号为
$\mu$，腔内归一化场为 $\psi(\phi,t)$：

$$
\frac{\partial \psi}{\partial t}
=
\left[-(1+i\alpha)+iD_{\mathrm{int}}(\mu)+i|\psi|^2\right]\psi
+F+i\tau_R\psi\frac{\partial |\psi|^2}{\partial \phi}.
$$

频域色散为

$$
D_{\mathrm{int}}(\mu)
=
\frac{d_2\mu^2}{2}
+\frac{d_3\mu^3}{6}
+\frac{d_4\mu^4}{24}.
$$

参数含义很直接：$\alpha$ 是泵浦-腔模失谐，$F$ 是泵浦幅度，$d_2,d_3,d_4$ 是归一化
integrated dispersion，$\tau_R$ 是 Raman shock 系数。当前求解器采用一阶 split-step：
时域更新 Kerr/Raman 项，频域更新损耗、失谐和色散项，最后显式加入泵浦。

## 物理图像

Standard soliton 的核心平衡是：连续波泵浦补偿腔损耗，Kerr 非线性提供强度相关相移，
异常色散 $d_2<0$ 平衡该非线性相移，从而形成局域亮脉冲。

四张图可以这样读：

- `Temporal field`：看 $|\psi|^2$ 是否形成窄的亮峰。
- `Comb spectrum`：看泵浦附近是否出现宽而连续的 comb envelope。
- `Intracavity energy`：看腔内平均能量是否趋于稳定。
- `Temporal evolution`：看孤子是否漂移、分裂或进入不稳定状态。

增加失谐通常会改变孤子宽度和峰值强度。$d_3$ 或 $d_4$ 会引入高阶色散，可产生不对称频谱或
dispersive-wave 特征。非零 $\tau_R$ 通过
$i\tau_R\psi\partial_\phi|\psi|^2$ 改变非线性相位，可用于探索 Raman
self-frequency-shift 类效应。

## Demo

1. 在 `MODEL` 中选择 `Standard soliton`。
2. 保持默认值：`grid = 512`, `Detuning = 10`, `Pump power = 3.94`,
   `D2 = -0.0444`, `D3 = 0`, `D4 = 0`, `tauR = 0`。
3. 点击 `Play`，先确认时域中出现一个稳定亮脉冲。
4. 缓慢扫描 `Detuning`，观察脉冲变窄、峰值变化以及能量曲线的响应。
5. 将 `D3` 或 `D4` 调成非零，观察频谱不对称和可能的窄峰结构。
6. 将 `tauR` 从 0 小幅增加，观察脉冲和频谱的偏移趋势。

如果结果发散或频谱出现明显数值噪声，先减小 `dt` 或降低 `Pump power`。求解器会用
$\max |D_{\mathrm{int}}|\,dt < \pi$ 的 aliasing 条件自动限制过大的积分步长，但这不能替代
更高阶、更精确的积分器。

## 参考文献

- T. Herr, V. Brasch, J. D. Jost, C. Y. Wang, N. M. Kondratiev, M. L. Gorodetsky, and T. J. Kippenberg, "Temporal solitons in optical microresonators," *Nature Photonics* **8**, 145-152 (2014). <https://doi.org/10.1038/nphoton.2013.343>
