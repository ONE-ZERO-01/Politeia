/// @file resource_exchange.cpp
/// @brief 对称资源交换规则、资源产出/消耗、生存阈值
///
/// 物理背景（研究方案 §2.6.2）：
///   交换规则必须是标签对称的：交换 i↔j 后结果只变符号。
///   不平等不是规则偏袒产生的，而是从状态差异中自发涌现的。
///
/// 交换公式：
///   A_i = w_i × ε_i      （综合能力 = 财富 × 技术）
///   Δw = η × (A_i − A_j) / (A_i + A_j) × min(w_i, w_j)
///
/// 物理类比：引力 F=Gm1m2/r² 也是完全对称的，但大质量体依然吸引更多物质。
/// 同理，交换规则对称，但能力强者自然获益更多。
///
/// 资源产出：
///   dw = R(x) × ε × dt − consumption × dt
///   R(x) = base_production × max(0, −V(x))
///   在地形势阱中心（V < 0），产出高；远离势阱，产出低。
///   技术水平 ε 放大同一块土地的产出——这就是 ε 的乘性效应。

#include "interaction/resource_exchange.hpp"
#include "analysis/network_analysis.hpp"

#include <cmath>
#include <algorithm>

namespace politeia {

Real exchange_resources(
    ParticleData& particles,
    const CellList& cells,
    const ExchangeParams& params,
    InteractionNetwork* network,
    const Real* terrain_potential_at_particle,
    const Real* river_proximity_at_particle
) {
    const Real cutoff_sq = params.cutoff * params.cutoff;
    const Real eta = params.exchange_rate;
    const bool barrier = params.terrain_barrier_enabled && terrain_potential_at_particle != nullptr;
    const Real inv_barrier_scale = barrier ? (1.0 / params.terrain_barrier_scale) : 0.0;
    const bool river_bonus = params.river_exchange_enabled && river_proximity_at_particle != nullptr;

    Real* __restrict__ w = particles.w_data();
    const Real* __restrict__ x = particles.x_data();
    const Real* __restrict__ eps = particles.eps_data();
    const Index n = particles.count();

    Real total_transferred = 0.0;

    cells.for_each_pair(x, n, cutoff_sq,
        [&](Index i, Index j, Real dx, Real dy, Real r2) {
            const Real wi = w[i];
            const Real wj = w[j];

            if (wi <= 0.0 || wj <= 0.0) return;

            const Real Ai = wi * eps[i];
            const Real Aj = wj * eps[j];
            const Real A_sum = Ai + Aj;

            if (A_sum < 1e-15) return;

            Real dw = eta * (Ai - Aj) / A_sum * std::min(wi, wj);

            if (barrier) {
                Real delta_h = std::abs(terrain_potential_at_particle[i]
                                      - terrain_potential_at_particle[j]);
                dw *= std::exp(-delta_h * inv_barrier_scale);
            }
            if (river_bonus) {
                const Real prox = std::min(
                    std::max(0.0, river_proximity_at_particle[i]),
                    std::max(0.0, river_proximity_at_particle[j])
                );
                dw *= 1.0 + params.river_exchange_strength * prox;
            }

            w[i] += dw;
            w[j] -= dw;

            if (network && std::abs(dw) > 1e-15) {
                network->record_transfer(i, j, dw);
            }

            total_transferred += std::abs(dw);
        }
    );

    return total_transferred;
}

void apply_resource_dynamics(
    ParticleData& particles,
    Real dt,
    Real consumption_rate,
    Real base_production,
    const Real* terrain_potential_at_particle,
    const Real* density_factor,
    const Real* river_proximity_at_particle,
    bool river_resource_enabled,
    Real river_resource_strength,
    Real river_resource_alpha
) {
    Real* __restrict__ w = particles.w_data();
    const Real* __restrict__ eps = particles.eps_data();
    const Index n = particles.count();

    #pragma omp parallel for schedule(static) if(n > 256)
    for (Index i = 0; i < n; ++i) {
        Real local_resource = 0.0;
        if (terrain_potential_at_particle != nullptr) {
            local_resource = base_production * std::max(0.0, -terrain_potential_at_particle[i]);
        }
        if (river_resource_enabled && river_proximity_at_particle != nullptr && local_resource > 0.0) {
            const Real prox = std::max(0.0, river_proximity_at_particle[i]);
            local_resource *= 1.0 + river_resource_strength * std::pow(prox, river_resource_alpha);
        }
        Real production = local_resource * eps[i] * dt;

        if (density_factor != nullptr) {
            production *= density_factor[i];
        }

        Real consumption = consumption_rate * dt;
        w[i] += production - consumption;
    }
}

Index apply_survival_threshold(
    ParticleData& particles,
    Real threshold
) {
    Index deaths = 0;
    const Index n = particles.count();

    #pragma omp parallel for schedule(static) reduction(+:deaths) if(n > 256)
    for (Index i = 0; i < n; ++i) {
        if (particles.status(i) == ParticleStatus::Alive && particles.wealth(i) < threshold) {
            particles.mark_dead(i);
            ++deaths;
        }
    }

    return deaths;
}

} // namespace politeia
