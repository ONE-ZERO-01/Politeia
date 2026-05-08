# Politeia 标准算例库

> 大多数完整算例由一对文件组成：`.cfg`（配置）+ `.csv`（初始条件）。
> 另外也包含少量可复用的配置片段，用于给现有完整算例叠加特定环境机制。
> 运行方式：`mpirun -np <N> build/src/politeia examples/<case>.cfg`

---

## 算例命名规则

```
<scenario>_<calibration>_<scale>.cfg
```

| 字段 | 含义 | 示例 |
|------|------|------|
| `scenario` | 场景类型 | `genesis`（创世纪）, `adam_eve`（亚当夏娃） |
| `calibration` | 校准数据源 | `hyde`（HYDE 3.3）, `manual`（手动设定） |
| `scale` | 粒子规模 | `100k`, `500k`, `1m` |

---

## 标准算例

### 1. genesis_hyde_100k — HYDE 创世纪（10万）⭐ 推荐

| 属性 | 值 |
|------|---|
| **文件** | `genesis_hyde_100k.cfg` + `genesis_hyde_100k.csv` |
| **时代** | 公元前 10,000 年（新石器过渡期） |
| **粒子数** | 100,000（1 agent ≈ 45 真实人口） |
| **校准源** | HYDE 3.3 (Klein Goldewijk et al. 2023) |
| **区域** | 29 个考古文化区，覆盖全球 |
| **模拟年** | 5,000 年 / phase（可分 3 个 phase 跑完 12,000 年） |
| **推荐进程** | 16–48（初始阶段人口递减后可用更少进程） |
| **生成工具** | `python3 scripts/generate_genesis.py --n 100000 --era 10000bce` |

**大洲分布（HYDE 3.3 校准）：**

| 大洲 | 占比 | HYDE 3.3 目标 | 主要区域 |
|------|------|-------------|---------|
| 北美洲 | 26.3% | 26.3% | 中美洲、东部/西部/大平原 |
| 南美洲 | 24.4% | 24.4% | 安第斯、巴西、南锥体 |
| 亚洲 | 26.3% | 26.3% | 新月沃地、中亚、南亚、东亚、东南亚 |
| 欧洲 | 10.7% | 10.7% | 东欧、地中海、大西洋、中北欧 |
| 大洋洲 | 7.2% | 7.2% | 澳大利亚、美拉尼西亚 |
| 非洲 | 5.1% | 5.1% | 尼罗河/东非、西/中非、南非 |

---

### 1b. genesis_hyde_baseline — HYDE 基线人口（1:1）

| 属性 | 值 |
|------|---|
| **文件** | `genesis_hyde_baseline.cfg` + **`genesis_hyde_baseline.csv`（需本地生成）** |
| **时代** | 公元前 10,000 年（与 `genesis_hyde_100k` 相同） |
| **粒子数** | **4,501,152**（与 HYDE 3.3 全球基线人口一致，**1 agent = 1 人**） |
| **用途** | 与历史人口数量严格对齐的生产级/论文级跑法；**算力与内存需求远高于 10 万算例** |
| **初始条件** | 大文件（约数百 MB），不纳入 Git；见 `examples/genesis_hyde_baseline.cfg` 文件头中的 `generate_genesis.py` 命令 |

---

### 2. genesis_100k — 初版创世纪（已弃用）

| 属性 | 值 |
|------|---|
| **文件** | `genesis_100k.cfg` + `genesis_100k.csv` |
| **说明** | 早期版本，区域分布未校准 HYDE 3.3 |
| **状态** | ⚠️ 已被 `genesis_hyde_100k` 取代 |

---

### 3. adam_eve — 亚当夏娃

| 属性 | 值 |
|------|---|
| **文件** | `adam_eve.cfg` + `adam_eve.csv` |
| **粒子数** | 2（最小可能初始条件） |
| **用途** | 人口增长测试、繁殖机制验证 |
| **快速测试** | `adam_eve_quick.cfg`（50 年） |

---

### 3b. riverfield_global_snippet — RiverField 全局配置片段

| 属性 | 值 |
|------|---|
| **文件** | `riverfield_global_snippet.cfg` |
| **类型** | 配置片段（**不是独立算例**，无单独 `.csv`） |
| **用途** | 给 `genesis_hyde_baseline.cfg` 等完整全局算例叠加 `RiverField` 河流走廊场 |
| **河流模式** | `river_mode = procedural` |
| **河流类型** | `river_type = major_rivers` |
| **默认耦合** | 资源产出、承载力、资源交换、技术传播开启；瘟疫增强与引导力可选 |
| **典型场景** | 验证“近大河更高产、更易交换、更快传播”的走廊效应 |

---

## 扩展算例（待生成）

> 使用 `generate_genesis.py` 可快速生成不同规模的算例：

| 算例名 | 命令 | 预估运算量 |
|--------|------|-----------|
| `genesis_hyde_500k` | `--n 500000 --era 10000bce` | 5× 基础 |
| `genesis_hyde_1m` | `--n 1000000 --era 10000bce` | 10× 基础 |
| `genesis_paleolithic_50k` | `--n 50000 --era 70000bce` | Out of Africa |

---

## 如何添加新算例

1. 在 `scripts/generate_genesis.py` 中定义区域数据（或修改现有 `REGIONS_*` 字典）
2. 运行脚本生成 `.csv`：
   ```bash
   python3 scripts/generate_genesis.py --n <N> --era <ERA> --output examples/<name>.csv
   ```
3. 复制已有 `.cfg` 并修改 `initial_conditions_file` 和 `initial_particles`
4. 更新本文件（`CASES.md`）

---

## 数据来源

| 数据集 | 用途 | 引用 |
|--------|------|------|
| **HYDE 3.3** | 区域人口分布校准 | Klein Goldewijk et al. (2023) |
| **McEvedy & Jones** | 历史人口交叉验证 | McEvedy & Jones (1978) |
| **Biraben** | 史前区域人口估计 | Biraben (1980) |
| **ETOPO1** | 真实地形势能面 | NOAA NCEI |
