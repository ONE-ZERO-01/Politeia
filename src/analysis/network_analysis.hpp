#pragma once

#include "core/types.hpp"
#include "core/particle_data.hpp"
#include "domain/cell_list.hpp"

#include <vector>
#include <unordered_map>

namespace politeia {

/// Tracks net resource flow between particle pairs over a time window.
/// After accumulation, extracts "de facto dominance" relationships
/// to detect hierarchy emergence without pre-built superior_i pointers.
class InteractionNetwork {
public:
    InteractionNetwork() = default;

    /// Record a resource transfer from j to i (positive means i gains).
    void record_transfer(Index i, Index j, Real amount);

    /// Reset accumulated flows (call at each analysis window).
    void reset();

    /// Build directed dominance graph from accumulated flows.
    /// An edge i→j exists if net flow from j to i exceeds threshold.
    /// Returns adjacency list: dominator[j] = i means i dominates j.
    [[nodiscard]] std::vector<Index> build_dominance_graph(
        Index n_particles,
        Real threshold
    ) const;

    [[nodiscard]] std::size_t num_edges() const { return flows_.size(); }

private:
    struct PairKey {
        Index lo, hi;  // lo < hi always
        bool operator==(const PairKey& o) const { return lo == o.lo && hi == o.hi; }
    };

    struct PairKeyHash {
        std::size_t operator()(const PairKey& k) const {
            return std::hash<Index>()(k.lo) ^ (std::hash<Index>()(k.hi) << 32);
        }
    };

    // net_flow > 0 means lo gains from hi; < 0 means hi gains from lo
    std::unordered_map<PairKey, Real, PairKeyHash> flows_;
};

/// Hierarchy metrics computed from dominance graph.
struct HierarchyMetrics {
    Index max_depth = 0;           // H(t): maximum tree depth
    Real mean_branching = 0.0;     // B(t): average children per non-leaf
    Index largest_component = 0;   // size of largest connected subtree
    Index n_components = 0;        // C(t): number of independent roots
    Real largest_fraction = 0.0;   // F(t): largest_component / N
    Real psi = 0.0;                // Ψ: feudalism-centralism order parameter
    Real power_gini = 0.0;         // Gini coefficient of effective power
};

/// Compute hierarchy metrics from a dominance graph (adjacency: dominator[j] = i).
/// Index(-1) means no dominator (root node).
[[nodiscard]] HierarchyMetrics compute_hierarchy_metrics(
    const std::vector<Index>& dominator,
    const ParticleData& particles
);

/// Compute effective power for each particle from dominance tree + wealth.
/// Power_i = sum of w_j for all j in subtree(i).
[[nodiscard]] std::vector<Real> compute_effective_power(
    const std::vector<Index>& dominator,
    const ParticleData& particles
);

/// Build dominator vector directly from explicit superior_i pointers (Phase 13+).
/// This replaces the inferred dominance graph for hierarchy metrics computation.
/// Returns dominator[i] = superior(i), with dead/invalid superiors set to NO_PARENT.
[[nodiscard]] std::vector<Index> build_dominator_from_superior(
    const ParticleData& particles
);

} // namespace politeia
