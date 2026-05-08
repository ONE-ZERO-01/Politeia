#include "analysis/network_analysis.hpp"
#include "analysis/order_params.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <queue>

namespace politeia {

void InteractionNetwork::record_transfer(Index i, Index j, Real amount) {
    if (i == j || std::abs(amount) < 1e-15) return;

    Index lo = std::min(i, j);
    Index hi = std::max(i, j);
    Real sign = (i == lo) ? 1.0 : -1.0;

    flows_[{lo, hi}] += sign * amount;
}

void InteractionNetwork::reset() {
    flows_.clear();
}

std::vector<Index> InteractionNetwork::build_dominance_graph(
    Index n_particles,
    Real threshold
) const {
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    std::vector<Index> dominator(n_particles, NO_PARENT);

    // For each particle, find strongest dominator (largest net inflow from one source)
    std::vector<Real> best_flow(n_particles, 0.0);

    for (const auto& [key, net_flow] : flows_) {
        Index gainer, loser;
        Real abs_flow;

        if (net_flow > 0) {
            gainer = key.lo;
            loser = key.hi;
            abs_flow = net_flow;
        } else {
            gainer = key.hi;
            loser = key.lo;
            abs_flow = -net_flow;
        }

        if (abs_flow < threshold) continue;

        // gainer dominates loser
        if (abs_flow > best_flow[loser]) {
            best_flow[loser] = abs_flow;
            dominator[loser] = gainer;
        }
    }

    // Detect and break cycles (keep only strongest edge in each cycle)
    for (Index i = 0; i < n_particles; ++i) {
        if (dominator[i] == NO_PARENT) continue;

        // Walk up the chain, detect cycle
        std::vector<bool> visited(n_particles, false);
        Index node = i;
        while (node != NO_PARENT && !visited[node]) {
            visited[node] = true;
            node = dominator[node];
        }

        if (node != NO_PARENT && visited[node]) {
            // Found cycle: break the weakest link in the cycle
            Index cycle_node = node;
            Index weakest_node = cycle_node;
            Real weakest_flow = best_flow[cycle_node];

            Index curr = dominator[cycle_node];
            while (curr != cycle_node) {
                if (best_flow[curr] < weakest_flow) {
                    weakest_flow = best_flow[curr];
                    weakest_node = curr;
                }
                curr = dominator[curr];
            }
            dominator[weakest_node] = NO_PARENT;
        }
    }

    return dominator;
}

std::vector<Real> compute_effective_power(
    const std::vector<Index>& dominator,
    const ParticleData& particles
) {
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    const Index n = dominator.size();

    // Build children lists
    std::vector<std::vector<Index>> children(n);
    for (Index i = 0; i < n; ++i) {
        if (dominator[i] != NO_PARENT && dominator[i] < n) {
            children[dominator[i]].push_back(i);
        }
    }

    // Compute subtree wealth (power) via bottom-up traversal
    std::vector<Real> power(n, 0.0);
    std::vector<int> depth(n, 0);

    // Topological order: compute in-degree, process leaves first
    std::vector<int> in_deg(n, 0);
    for (Index i = 0; i < n; ++i) {
        if (dominator[i] != NO_PARENT && dominator[i] < n) {
            in_deg[dominator[i]]++;
        }
    }

    std::queue<Index> q;
    for (Index i = 0; i < n; ++i) {
        power[i] = std::max(0.0, (i < particles.count()) ? particles.wealth(i) : 0.0);
        if (in_deg[i] == 0) q.push(i);
    }

    while (!q.empty()) {
        Index node = q.front();
        q.pop();

        Index parent = dominator[node];
        if (parent != NO_PARENT && parent < n) {
            power[parent] += power[node];
            in_deg[parent]--;
            if (in_deg[parent] == 0) {
                q.push(parent);
            }
        }
    }

    return power;
}

HierarchyMetrics compute_hierarchy_metrics(
    const std::vector<Index>& dominator,
    const ParticleData& particles
) {
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    const Index n = dominator.size();

    HierarchyMetrics m;

    if (n == 0) return m;

    // Build children lists
    std::vector<std::vector<Index>> children(n);
    std::vector<Index> roots;

    for (Index i = 0; i < n; ++i) {
        if (dominator[i] == NO_PARENT) {
            roots.push_back(i);
        } else if (dominator[i] < n) {
            children[dominator[i]].push_back(i);
        }
    }

    m.n_components = roots.size();

    // BFS from each root to compute depths, component sizes
    std::vector<int> depth(n, 0);
    Index max_component_size = 0;

    int total_children = 0;
    int non_leaf_count = 0;

    for (Index root : roots) {
        std::queue<Index> bfs;
        bfs.push(root);
        Index comp_size = 0;

        while (!bfs.empty()) {
            Index node = bfs.front();
            bfs.pop();
            comp_size++;

            if (!children[node].empty()) {
                total_children += children[node].size();
                non_leaf_count++;
            }

            for (Index child : children[node]) {
                depth[child] = depth[node] + 1;
                if (depth[child] > static_cast<int>(m.max_depth)) {
                    m.max_depth = depth[child];
                }
                bfs.push(child);
            }
        }

        if (comp_size > max_component_size) {
            max_component_size = comp_size;
        }
    }

    m.largest_component = max_component_size;
    m.largest_fraction = (n > 0) ? static_cast<Real>(max_component_size) / n : 0.0;
    m.mean_branching = (non_leaf_count > 0) ? static_cast<Real>(total_children) / non_leaf_count : 0.0;

    // Ψ: feudalism-centralism parameter
    // For each second-level node (depth=1), compute self_wealth / subtree_wealth
    Real psi_sum = 0.0;
    int psi_count = 0;

    for (Index i = 0; i < n; ++i) {
        if (depth[i] == 1 && !children[i].empty()) {
            // This is a "lord" — compute subtree wealth
            std::queue<Index> sub_bfs;
            sub_bfs.push(i);
            Real subtree_w = 0.0;
            while (!sub_bfs.empty()) {
                Index node = sub_bfs.front();
                sub_bfs.pop();
                if (node < particles.count()) {
                    subtree_w += std::max(0.0, particles.wealth(node));
                }
                for (Index c : children[node]) sub_bfs.push(c);
            }
            Real self_w = (i < particles.count()) ? std::max(0.0, particles.wealth(i)) : 0.0;
            if (subtree_w > 1e-15) {
                psi_sum += self_w / subtree_w;
                psi_count++;
            }
        }
    }
    m.psi = (psi_count > 0) ? psi_sum / psi_count : 0.0;

    // Power Gini
    auto power = compute_effective_power(dominator, particles);
    // Filter alive particles only
    std::vector<Real> alive_power;
    for (Index i = 0; i < std::min(n, particles.count()); ++i) {
        if (particles.status(i) == ParticleStatus::Alive) {
            alive_power.push_back(power[i]);
        }
    }

    if (alive_power.size() > 1) {
        std::sort(alive_power.begin(), alive_power.end());
        Real total = std::accumulate(alive_power.begin(), alive_power.end(), 0.0);
        if (total > 1e-15) {
            Real weighted = 0.0;
            for (std::size_t i = 0; i < alive_power.size(); ++i) {
                weighted += static_cast<Real>(i + 1) * alive_power[i];
            }
            auto nn = static_cast<Real>(alive_power.size());
            m.power_gini = (2.0 * weighted) / (nn * total) - (nn + 1.0) / nn;
        }
    }

    return m;
}

std::vector<Index> build_dominator_from_superior(
    const ParticleData& particles
) {
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    const Index n = particles.count();
    std::vector<Index> dominator(n, NO_PARENT);

    for (Index i = 0; i < n; ++i) {
        if (particles.status(i) != ParticleStatus::Alive) continue;

        Id sup_gid = particles.superior(i);
        if (sup_gid < 0) continue;

        Index sup_local = particles.gid_to_local(sup_gid);
        if (sup_local != NO_PARENT &&
            particles.status(sup_local) == ParticleStatus::Alive)
        {
            dominator[i] = sup_local;
        }
    }

    return dominator;
}

} // namespace politeia
