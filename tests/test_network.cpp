#include <gtest/gtest.h>
#include "analysis/network_analysis.hpp"

using namespace politeia;

TEST(NetworkTest, RecordAndBuildDominance) {
    InteractionNetwork net;

    // i=0 consistently gains from i=1
    for (int t = 0; t < 10; ++t) {
        net.record_transfer(0, 1, 5.0);  // 0 gains 5 from 1
    }

    ParticleData pd(5);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 100.0, 1.0, 0.0);
    (void)pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 10.0, 1.0, 0.0);

    auto dom = net.build_dominance_graph(2, 1.0);

    // 0 dominates 1: dominator[1] = 0
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    EXPECT_EQ(dom[0], NO_PARENT);  // 0 is root
    EXPECT_EQ(dom[1], 0u);         // 1 is dominated by 0
}

TEST(NetworkTest, NoDominanceBelowThreshold) {
    InteractionNetwork net;
    net.record_transfer(0, 1, 0.01);

    auto dom = net.build_dominance_graph(2, 1.0);
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    EXPECT_EQ(dom[0], NO_PARENT);
    EXPECT_EQ(dom[1], NO_PARENT);
}

TEST(NetworkTest, HierarchyDepth) {
    // Chain: 0 → 1 → 2 → 3 (depth 3)
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    std::vector<Index> dom = {NO_PARENT, 0, 1, 2};

    ParticleData pd(10);
    for (int i = 0; i < 4; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 10.0 - i * 2, 1.0, 0.0);
    }

    auto m = compute_hierarchy_metrics(dom, pd);
    EXPECT_EQ(m.max_depth, 3u);
    EXPECT_EQ(m.n_components, 1u);
    EXPECT_NEAR(m.largest_fraction, 1.0, 0.01);
}

TEST(NetworkTest, MultipleComponents) {
    // Two independent trees: {0→1} and {2→3}
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    std::vector<Index> dom = {NO_PARENT, 0, NO_PARENT, 2};

    ParticleData pd(10);
    for (int i = 0; i < 4; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 5.0, 1.0, 0.0);
    }

    auto m = compute_hierarchy_metrics(dom, pd);
    EXPECT_EQ(m.n_components, 2u);
    EXPECT_NEAR(m.largest_fraction, 0.5, 0.01);
}

TEST(NetworkTest, EffectivePower) {
    // Tree: 0 is root, 1 and 2 are children of 0
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    std::vector<Index> dom = {NO_PARENT, 0, 0};

    ParticleData pd(5);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 10.0, 1.0, 0.0);
    (void)pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 5.0, 1.0, 0.0);
    (void)pd.add_particle({2.0, 0.0}, {0.0, 0.0}, 3.0, 1.0, 0.0);

    auto power = compute_effective_power(dom, pd);

    // Root (0) power = own(10) + child1(5) + child2(3) = 18
    EXPECT_NEAR(power[0], 18.0, 0.01);
    EXPECT_NEAR(power[1], 5.0, 0.01);
    EXPECT_NEAR(power[2], 3.0, 0.01);
}

TEST(NetworkTest, PsiFeudalism) {
    // Lord at depth=1 controls most of the subtree wealth → Ψ ≈ 1
    constexpr Index NO_PARENT = static_cast<Index>(-1);
    // King(0) → Lord(1) → Peasant(2)
    std::vector<Index> dom = {NO_PARENT, 0, 1};

    ParticleData pd(5);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 50.0, 1.0, 0.0);  // king
    (void)pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 40.0, 1.0, 0.0);  // lord (rich)
    (void)pd.add_particle({2.0, 0.0}, {0.0, 0.0}, 2.0, 1.0, 0.0);   // peasant (poor)

    auto m = compute_hierarchy_metrics(dom, pd);
    // Lord's self_wealth / subtree_wealth = 40 / (40+2) = 0.952
    EXPECT_GT(m.psi, 0.9);
}

TEST(NetworkTest, Reset) {
    InteractionNetwork net;
    net.record_transfer(0, 1, 10.0);
    EXPECT_GT(net.num_edges(), 0u);

    net.reset();
    EXPECT_EQ(net.num_edges(), 0u);
}

TEST(NetworkTest, BuildDominatorFromSuperior) {
    ParticleData pd(10, 2);
    // King (0), Lord A (1→0), Lord B (2→0), Peasant (3→1)
    (void)pd.add_particle({0, 0}, {0, 0}, 100, 1, 30);
    (void)pd.add_particle({1, 0}, {0, 0}, 50, 1, 30);
    (void)pd.add_particle({2, 0}, {0, 0}, 40, 1, 30);
    (void)pd.add_particle({3, 0}, {0, 0}, 10, 1, 20);
    (void)pd.add_particle({4, 0}, {0, 0}, 5, 1, 20);

    pd.superior(1) = 0;  pd.loyalty(1) = 0.8;
    pd.superior(2) = 0;  pd.loyalty(2) = 0.7;
    pd.superior(3) = 1;  pd.loyalty(3) = 0.9;
    // Particle 4 is independent

    auto dom = build_dominator_from_superior(pd);

    EXPECT_EQ(dom[0], static_cast<Index>(-1));  // king is root
    EXPECT_EQ(dom[1], 0u);  // lord A → king
    EXPECT_EQ(dom[2], 0u);  // lord B → king
    EXPECT_EQ(dom[3], 1u);  // peasant → lord A
    EXPECT_EQ(dom[4], static_cast<Index>(-1));  // independent

    auto hm = compute_hierarchy_metrics(dom, pd);
    EXPECT_EQ(hm.max_depth, 2u);     // king→lord→peasant = depth 2
    EXPECT_EQ(hm.n_components, 2u);   // two trees: {0,1,2,3} and {4}
    EXPECT_EQ(hm.largest_component, 4u);
    EXPECT_NEAR(hm.largest_fraction, 0.8, 1e-10);
    EXPECT_GT(hm.psi, 0.0);
}

TEST(NetworkTest, BuildDominatorFromSuperiorDeadSkipped) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({0, 0}, {0, 0}, 100, 1, 30);
    (void)pd.add_particle({1, 0}, {0, 0}, 50, 1, 30);

    pd.superior(1) = 0;  pd.loyalty(1) = 0.8;
    pd.mark_dead(0);

    auto dom = build_dominator_from_superior(pd);

    // Superior 0 is dead → particle 1 should have no parent
    EXPECT_EQ(dom[1], static_cast<Index>(-1));
}
