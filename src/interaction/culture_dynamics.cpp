#include "interaction/culture_dynamics.hpp"

#include <cmath>
#include <algorithm>
#include <numeric>
#include <vector>

namespace politeia {

Real culture_distance(const ParticleData& particles, Index i, Index j) {
    const int d = particles.culture_dim();
    Real dist_sq = 0.0;
    for (int k = 0; k < d; ++k) {
        Real diff = particles.culture(i, k) - particles.culture(j, k);
        dist_sq += diff * diff;
    }
    return std::sqrt(dist_sq);
}

Real culture_force_modifier(Real culture_dist, const CultureParams& params) {
    if (culture_dist < params.repulsion_threshold) {
        // Similar culture: attraction. Modifier ∈ (0, 1].
        Real t = culture_dist / params.repulsion_threshold;
        return params.attraction_strength * (1.0 - t);
    } else {
        // Dissimilar culture: repulsion. Modifier ∈ [-1, 0).
        Real excess = culture_dist - params.repulsion_threshold;
        return -params.repulsion_strength * std::tanh(excess);
    }
}

void evolve_culture(
    ParticleData& particles,
    const CellList& cells,
    const CultureParams& params,
    Real dt
) {
    const Index n = particles.count();
    const int cd = particles.culture_dim();
    const Real cutoff_sq = params.interaction_range * params.interaction_range;
    const Real* __restrict__ x = particles.x_data();
    const Real rate = params.assimilation_rate * dt;

    // Accumulate culture changes (don't modify in-place during iteration)
    std::vector<Real> dcv(n * cd, 0.0);
    std::vector<int> n_interactions(n, 0);

    cells.for_each_pair(x, n, cutoff_sq,
        [&](Index i, Index j, Real dx, Real dy, Real r2) {
            if (particles.status(i) != ParticleStatus::Alive) return;
            if (particles.status(j) != ParticleStatus::Alive) return;

            Real cdist = culture_distance(particles, i, j);

            // Only assimilate if cultures are somewhat similar
            if (cdist > params.repulsion_threshold * 2.0) return;

            // Assimilation strength decreases with cultural distance
            Real strength = std::exp(-cdist * cdist / (2.0 * params.repulsion_threshold * params.repulsion_threshold));

            for (int k = 0; k < cd; ++k) {
                Real diff = particles.culture(j, k) - particles.culture(i, k);
                dcv[i * cd + k] += rate * strength * diff;
                dcv[j * cd + k] -= rate * strength * diff;
            }

            n_interactions[i]++;
            n_interactions[j]++;
        }
    );

    // Apply accumulated changes
    for (Index i = 0; i < n; ++i) {
        if (particles.status(i) != ParticleStatus::Alive) continue;
        for (int k = 0; k < cd; ++k) {
            particles.culture(i, k) += dcv[i * cd + k];
        }
    }
}

Real compute_culture_order_param(const ParticleData& particles) {
    const Index n = particles.count();
    const int cd = particles.culture_dim();

    if (n == 0 || cd == 0) return 0.0;

    // Compute average of normalized culture vectors
    std::vector<Real> avg(cd, 0.0);
    Index alive_count = 0;

    for (Index i = 0; i < n; ++i) {
        if (particles.status(i) != ParticleStatus::Alive) continue;

        // Compute |c⃗_i|
        Real norm = 0.0;
        for (int k = 0; k < cd; ++k) {
            norm += particles.culture(i, k) * particles.culture(i, k);
        }
        norm = std::sqrt(norm);

        if (norm < 1e-15) continue;

        for (int k = 0; k < cd; ++k) {
            avg[k] += particles.culture(i, k) / norm;
        }
        alive_count++;
    }

    if (alive_count == 0) return 0.0;

    Real Q = 0.0;
    for (int k = 0; k < cd; ++k) {
        avg[k] /= alive_count;
        Q += avg[k] * avg[k];
    }

    return std::sqrt(Q);
}

std::vector<Real> compute_culture_correlation(
    const ParticleData& particles,
    int n_bins,
    Real max_r
) {
    std::vector<Real> corr(n_bins, 0.0);
    std::vector<Index> counts(n_bins, 0);

    const Index n = particles.count();
    const int cd = particles.culture_dim();
    const Real bin_width = max_r / n_bins;

    for (Index i = 0; i < n; ++i) {
        if (particles.status(i) != ParticleStatus::Alive) continue;
        for (Index j = i + 1; j < n; ++j) {
            if (particles.status(j) != ParticleStatus::Alive) continue;

            auto pi = particles.position(i);
            auto pj = particles.position(j);
            Real dx = pj[0] - pi[0];
            Real dy = pj[1] - pi[1];
            Real r = std::sqrt(dx * dx + dy * dy);

            if (r >= max_r) continue;

            int bin = static_cast<int>(r / bin_width);
            if (bin >= n_bins) bin = n_bins - 1;

            // Cosine similarity of culture vectors
            Real dot = 0.0, ni2 = 0.0, nj2 = 0.0;
            for (int k = 0; k < cd; ++k) {
                dot += particles.culture(i, k) * particles.culture(j, k);
                ni2 += particles.culture(i, k) * particles.culture(i, k);
                nj2 += particles.culture(j, k) * particles.culture(j, k);
            }
            Real norm = std::sqrt(ni2 * nj2);
            if (norm > 1e-15) {
                corr[bin] += dot / norm;
            }
            counts[bin]++;
        }
    }

    for (int b = 0; b < n_bins; ++b) {
        if (counts[b] > 0) corr[b] /= counts[b];
    }

    return corr;
}

} // namespace politeia
