#include "analysis/polity.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <unordered_set>

namespace politeia {

const char* polity_type_name(PolityType t) noexcept {
    switch (t) {
        case PolityType::Band:     return "band";
        case PolityType::Tribe:    return "tribe";
        case PolityType::Chiefdom: return "chiefdom";
        case PolityType::State:    return "state";
        case PolityType::Empire:   return "empire";
    }
    return "unknown";
}

PolityType classify_polity(Index population, Index depth) {
    if (population >= 5000)                          return PolityType::Empire;
    if (population >= 1000)                          return PolityType::State;
    if (population >= 300  || depth >= 3)             return PolityType::Chiefdom;
    if (population >= 50   || depth >= 2)             return PolityType::Tribe;
    return PolityType::Band;
}

namespace {

/// Find the root of particle i by walking up the superior chain.
/// Returns the local index of the root. If the superior is off-rank,
/// treats i as its own root.
Index find_root(const ParticleData& particles, Index i) {
    Index cur = i;
    int steps = 0;
    constexpr int MAX_CHAIN = 200;

    while (steps < MAX_CHAIN) {
        Id sup_gid = particles.superior(cur);
        if (sup_gid < 0) return cur;

        Index sup_local = particles.gid_to_local(sup_gid);
        if (sup_local == static_cast<Index>(-1)) return cur;
        if (particles.status(sup_local) != ParticleStatus::Alive) return cur;

        cur = sup_local;
        ++steps;
    }
    return cur;
}

/// Compute depth of particle i in the hierarchy tree (root = depth 0).
Index compute_depth(const ParticleData& particles, Index i) {
    Index depth = 0;
    Index cur = i;
    constexpr int MAX_CHAIN = 200;

    while (depth < MAX_CHAIN) {
        Id sup_gid = particles.superior(cur);
        if (sup_gid < 0) break;

        Index sup_local = particles.gid_to_local(sup_gid);
        if (sup_local == static_cast<Index>(-1)) break;
        if (particles.status(sup_local) != ParticleStatus::Alive) break;

        cur = sup_local;
        ++depth;
    }
    return depth;
}

} // anonymous namespace

std::vector<PolityInfo> detect_polities(const ParticleData& particles) {
    const Index n = particles.count();

    // Step 1: assign each alive particle to its root
    std::unordered_map<Index, std::vector<Index>> root_to_members;

    for (Index i = 0; i < n; ++i) {
        if (particles.status(i) != ParticleStatus::Alive) continue;
        Index root = find_root(particles, i);
        root_to_members[root].push_back(i);
    }

    // Step 2: build PolityInfo for each root
    std::vector<PolityInfo> polities;
    polities.reserve(root_to_members.size());

    for (auto& [root_idx, members] : root_to_members) {
        PolityInfo info{};
        info.root_local = root_idx;
        info.root_gid = particles.global_id(root_idx);
        info.population = members.size();

        Real sum_w = 0.0;
        Real sum_L = 0.0;
        Index n_subordinates = 0;
        Real cx = 0.0, cy = 0.0;
        Real xmin = std::numeric_limits<Real>::max();
        Real xmax = std::numeric_limits<Real>::lowest();
        Real ymin = std::numeric_limits<Real>::max();
        Real ymax = std::numeric_limits<Real>::lowest();
        Index max_depth = 0;

        for (Index m : members) {
            Real w = particles.wealth(m);
            sum_w += w;
            auto pos = particles.position(m);
            cx += pos[0];
            cy += pos[1];
            xmin = std::min(xmin, pos[0]);
            xmax = std::max(xmax, pos[0]);
            ymin = std::min(ymin, pos[1]);
            ymax = std::max(ymax, pos[1]);

            if (m != root_idx) {
                sum_L += particles.loyalty(m);
                ++n_subordinates;
            }

            Index d = compute_depth(particles, m);
            if (d > max_depth) max_depth = d;
        }

        info.total_wealth = sum_w;
        info.depth = max_depth;
        info.mean_loyalty = (n_subordinates > 0)
            ? sum_L / static_cast<Real>(n_subordinates) : 0.0;
        info.centroid = {
            cx / static_cast<Real>(members.size()),
            cy / static_cast<Real>(members.size())
        };
        info.territory_area = (xmax - xmin) * (ymax - ymin);
        info.total_power = sum_w; // simplified: total wealth of the polity
        info.type = classify_polity(info.population, info.depth);

        polities.push_back(info);
    }

    // Sort by population descending
    std::sort(polities.begin(), polities.end(),
        [](const PolityInfo& a, const PolityInfo& b) {
            return a.population > b.population;
        });

    return polities;
}

std::vector<PolityEvent> detect_polity_events(
    const std::vector<PolityInfo>& prev_polities,
    const std::vector<PolityInfo>& curr_polities,
    Real time
) {
    std::vector<PolityEvent> events;

    // Build sets of root gids for fast lookup
    std::unordered_map<Id, const PolityInfo*> prev_map;
    for (auto& p : prev_polities) {
        if (p.population > 1) prev_map[p.root_gid] = &p;
    }

    std::unordered_map<Id, const PolityInfo*> curr_map;
    for (auto& p : curr_polities) {
        if (p.population > 1) curr_map[p.root_gid] = &p;
    }

    // Detect formations: polities in curr but not in prev
    for (auto& [gid, info] : curr_map) {
        if (prev_map.find(gid) == prev_map.end()) {
            PolityEvent ev;
            ev.time = time;
            ev.type = PolityEventType::Formation;
            ev.polity_gid = gid;
            ev.other_gid = -1;
            ev.pop_before = 0;
            ev.pop_after = info->population;
            events.push_back(ev);
        }
    }

    // Detect collapses: polities in prev but not in curr
    for (auto& [gid, info] : prev_map) {
        if (curr_map.find(gid) == curr_map.end()) {
            PolityEvent ev;
            ev.time = time;
            ev.type = PolityEventType::Collapse;
            ev.polity_gid = gid;
            ev.other_gid = -1;
            ev.pop_before = info->population;
            ev.pop_after = 0;
            events.push_back(ev);
        }
    }

    // Detect significant growth (possible merger) or shrinkage (possible split)
    for (auto& [gid, curr_info] : curr_map) {
        auto it = prev_map.find(gid);
        if (it == prev_map.end()) continue;
        const PolityInfo* prev_info = it->second;

        auto pop_prev = static_cast<Real>(prev_info->population);
        auto pop_curr = static_cast<Real>(curr_info->population);

        if (pop_curr > pop_prev * 1.5 && pop_curr - pop_prev > 10) {
            PolityEvent ev;
            ev.time = time;
            ev.type = PolityEventType::Merger;
            ev.polity_gid = gid;
            ev.other_gid = -1;
            ev.pop_before = prev_info->population;
            ev.pop_after = curr_info->population;
            events.push_back(ev);
        }

        if (pop_curr < pop_prev * 0.5 && pop_prev - pop_curr > 10) {
            PolityEvent ev;
            ev.time = time;
            ev.type = PolityEventType::Split;
            ev.polity_gid = gid;
            ev.other_gid = -1;
            ev.pop_before = prev_info->population;
            ev.pop_after = curr_info->population;
            events.push_back(ev);
        }
    }

    return events;
}

PolitySummary summarize_polities(
    const std::vector<PolityInfo>& polities,
    Real time
) {
    PolitySummary s{};
    s.time = time;
    s.n_polities = polities.size();

    Index total_pop = 0;
    Real sum_sq = 0.0;

    for (auto& p : polities) {
        total_pop += p.population;
        if (p.population > 1) ++s.n_multi;
        if (p.population > s.largest_pop) s.largest_pop = p.population;

        switch (p.type) {
            case PolityType::Band:     ++s.n_bands;     break;
            case PolityType::Tribe:    ++s.n_tribes;    break;
            case PolityType::Chiefdom: ++s.n_chiefdoms; break;
            case PolityType::State:    ++s.n_states;    break;
            case PolityType::Empire:   ++s.n_empires;   break;
        }
    }

    s.mean_pop = (s.n_polities > 0)
        ? static_cast<Real>(total_pop) / static_cast<Real>(s.n_polities) : 0.0;

    // HHI: sum of (share_i)^2 where share_i = pop_i / total_pop
    if (total_pop > 0) {
        for (auto& p : polities) {
            Real share = static_cast<Real>(p.population)
                         / static_cast<Real>(total_pop);
            sum_sq += share * share;
        }
        s.hhi = sum_sq;
    }

    return s;
}

} // namespace politeia
