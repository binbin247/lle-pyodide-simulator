# CyberMicrocomb https://binbin247.github.io/CyberMicrocomb/

[English](./README.md) | [中文](./README.zh-CN.md)

面向微梳动力学的交互式浏览器端 LLE 模拟器。

CyberMicrocomb 是一个纯浏览器实时 Lugiato-Lefever 方程模拟器，基于
React、TypeScript、Vite、Pyodide、NumPy 和 Web Worker 构建。

浏览器负责用户界面。数值求解器通过 Pyodide 在 Web Worker 中本地运行，
因此页面加载完成后不需要 Flask/FastAPI 后端，也不需要服务器端计算。

## 功能

- 归一化参数控制。
- 中英文界面切换。
- 固定网格：256、512、1024、2048 和 4096 点。
- 参数实时更新，不重置当前光场。
- 使用 Plotly 绘制时域、频谱、能量和峰值曲线。
- 使用 Canvas 绘制 waterfall 历史，并用固定 300 帧 ring buffer 保存。
- 简单一阶分步傅里叶 LLE 求解器，支持 D2/D3/D4 和可选 Raman shock 项。
- 面向 GitHub Pages 的纯静态部署。

## 模型

归一化模型为

```text
dpsi/dt = [-(1 + i alpha) + i Dint(mu) + i |psi|^2] psi
          + F - tauR psi d_theta |psi|^2
```

其中

```text
Dint(mu) = d2 mu^2 / 2 + d3 mu^3 / 6 + d4 mu^4 / 24
```

v1 求解器使用简单一阶分步傅里叶更新：

1. 时域 Kerr/Raman 更新。
2. FFT。
3. 频域线性更新。
4. IFFT。
5. 显式泵浦更新。

该版本用于交互式探索，不作为最终论文级积分结果。

## 本地开发

```bash
npm install
npm run dev
```

打开终端输出的本地 Vite 地址，通常是：

```text
http://127.0.0.1:5173/
```

首次加载页面需要联网，从 Pyodide CDN 获取 Pyodide 和 NumPy。运行时加载完成后，
当前会话的计算会继续在浏览器本地执行。

## 测试与构建

```bash
npm run test
npm run build
```

测试命令会运行 Python NumPy 求解器检查，包括损耗衰减、网格重建和 Raman
输出有限性。

## GitHub Pages

仓库内置 workflow 会把应用构建成静态站点并部署到 GitHub Pages。在仓库设置中，
将 Pages source 设置为 GitHub Actions，然后推送到 `main`。

对于当前仓库名，生产环境 base path 为：

```text
/CyberMicrocomb/
```

workflow 会设置 `GITHUB_PAGES=true`，让 Vite 使用该 base path。
