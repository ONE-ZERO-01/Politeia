#include "interaction/loyalty.hpp"
#include "core/particle_data.hpp"
#include "domain/cell_list.hpp"
#include "analysis/network_analysis.hpp"

#include <gtest/gtest.h>
#include <random>
#include <cmath>

using namespace politeia;

class LoyaltyTest : public ::testing::Test {
protected:
    void SetUp() override {
        particles = std::make_unique<ParticleData>(100, 4);
        cells.init(0, 100, 0, 100, 5.0);

        for (int i = 0; i < 5; ++i) {
            Vec2 pos = {50.0 + i * 2.0, 50.0};
            Vec2 mom = {0, 0};
            (void)particles->add_particle(pos, mom, 10.0 * (i + 1), 1.0, 25.0);
        }
        cells.build(particles->x_data(), particles->count());
    }

    Id gid(Index i) const { return particles->global_id(i); }

    std::unique_ptr<ParticleData> particles;
    CellList cells;
    LoyaltyParams params;
    std::mt19937_64 rng{42};
};

TEST_F(LoyaltyTest, InitialStateNoSuperior) {
    for (Index i = 0; i < particles->count(); ++i) {
        EXPECT_EQ(particles->superior(i), -1);
        EXPECT_NEAR(particles->loyalty(i), 0.0, 1e-15);
    }
}

TEST_F(LoyaltyTest, FormAttachments) {
    InteractionNetwork network;

    for (int round = 0; round < 100; ++round) {
        for (Index i = 0; i < 4; ++i) {
            network.record_transfer(i, 4, -1.0);
        }
    }

    Index formed = form_attachments(*particles, network, params);
    EXPECT_GT(formed, 0u);

    int count_attached = 0;
    for (Index i = 0; i < particles->count(); ++i) {
        if (particles->superior(i) == gid(4)) ++count_attached;
    }
    EXPECT_GT(count_attached, 0);
}

TEST_F(LoyaltyTest, EvolveLoyaltyIncrease) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.5;

    params.tax_drain = 0.0;
    params.culture_penalty = 0.0;
    params.noise_sigma = 0.0;

    Real L_before = particles->loyalty(0);
    evolve_loyalty(*particles, params, 1.0, rng);
    EXPECT_GT(particles->loyalty(0), L_before);
}

TEST_F(LoyaltyTest, EvolveLoyaltyDecrease) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.5;

    params.protection_gain = 0.0;
    params.tax_drain = 1.0;
    params.tax_rate = 0.5;
    params.culture_penalty = 0.0;
    params.noise_sigma = 0.0;

    Real L_before = particles->loyalty(0);
    evolve_loyalty(*particles, params, 1.0, rng);
    EXPECT_LT(particles->loyalty(0), L_before);
}

TEST_F(LoyaltyTest, Rebellion) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.05;

    params.rebel_threshold = 0.1;
    Index broken = process_loyalty_events(*particles, cells, params, rng);

    EXPECT_GE(broken, 1u);
    EXPECT_EQ(particles->superior(0), -1);
}

TEST_F(LoyaltyTest, Taxation) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.8;

    Real w0_before = particles->wealth(0);
    Real w4_before = particles->wealth(4);

    params.tax_rate = 0.1;
    apply_taxation(*particles, params, 1.0);

    EXPECT_LT(particles->wealth(0), w0_before);
    EXPECT_GT(particles->wealth(4), w4_before);

    Real tax = w0_before * 0.1 * 1.0;
    EXPECT_NEAR(w0_before - particles->wealth(0), tax, 1e-10);
}

TEST_F(LoyaltyTest, EffectivePower) {
    particles->superior(0) = gid(1);
    particles->loyalty(0) = 0.8;
    particles->superior(1) = gid(2);
    particles->loyalty(1) = 0.9;

    auto power = compute_effective_power(*particles);

    EXPECT_GT(power[2], 0.0);
    EXPECT_GT(power[3], 0.0);
    EXPECT_GT(power[4], 0.0);
}

TEST_F(LoyaltyTest, CompactWithMap) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.8;
    Id gid4 = gid(4);
    particles->mark_dead(2);

    Index old_count = particles->count();
    std::vector<Index> old_to_new;
    particles->compact_with_map(old_to_new);

    repair_superior_after_compact(*particles, old_to_new, old_count);

    EXPECT_EQ(old_to_new[4], 3u);
    // Superior is a global ID — it should survive compact unchanged
    EXPECT_EQ(particles->superior(0), gid4);
    // And gid_to_local should resolve correctly
    EXPECT_EQ(particles->gid_to_local(gid4), 3u);
}

TEST_F(LoyaltyTest, DeadSuperiorCleared) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.8;
    particles->mark_dead(4);

    evolve_loyalty(*particles, params, 1.0, rng);

    EXPECT_EQ(particles->superior(0), -1);
    EXPECT_NEAR(particles->loyalty(0), 0.0, 1e-15);
}

// ─── Phase 14: Succession Tests ──────────────────────────

TEST_F(LoyaltyTest, SuccessionHeirSelection) {
    particles->superior(1) = gid(4);  particles->loyalty(1) = 0.5;
    particles->superior(2) = gid(4);  particles->loyalty(2) = 0.9;
    particles->superior(3) = gid(4);  particles->loyalty(3) = 0.3;

    std::vector<Index> dying = {4};
    Index successions = process_succession(*particles, dying);

    EXPECT_EQ(successions, 1u);
    EXPECT_EQ(particles->superior(2), -1);
    // Others should point to heir (particle 2's global ID)
    EXPECT_EQ(particles->superior(1), gid(2));
    EXPECT_EQ(particles->superior(3), gid(2));
}

TEST_F(LoyaltyTest, SuccessionEstateDistribution) {
    particles->wealth(4) = 100.0;
    particles->superior(0) = gid(4);  particles->loyalty(0) = 0.8;
    particles->superior(1) = gid(4);  particles->loyalty(1) = 0.3;

    Real w0_before = particles->wealth(0);
    Real w1_before = particles->wealth(1);

    std::vector<Index> dying = {4};
    process_succession(*particles, dying);

    EXPECT_GT(particles->wealth(0) + particles->wealth(1),
              w0_before + w1_before);
    EXPECT_NEAR(particles->wealth(4), 0.0, 1e-10);
}

TEST_F(LoyaltyTest, SuccessionChainedLeaders) {
    particles->superior(0) = gid(2);  particles->loyalty(0) = 0.8;
    particles->superior(1) = gid(2);  particles->loyalty(1) = 0.7;
    particles->superior(2) = gid(4);  particles->loyalty(2) = 0.9;

    std::vector<Index> dying = {2};
    Index s = process_succession(*particles, dying);
    EXPECT_EQ(s, 1u);

    bool found_heir = false;
    for (Index i : {Index(0), Index(1)}) {
        Id sup = particles->superior(i);
        if (sup >= 0 && sup != gid(2)) {
            found_heir = true;
        }
    }
    EXPECT_TRUE(found_heir);
}

TEST_F(LoyaltyTest, InheritHierarchyFromParent) {
    particles->superior(0) = gid(4);
    particles->loyalty(0) = 0.8;

    Vec2 pos = {52.0, 50.0};
    Index child = particles->add_particle(pos, {0, 0}, 5.0, 1.0, 0.0);

    inherit_hierarchy(*particles, child, 0, 1);

    EXPECT_EQ(particles->superior(child), gid(4));
    EXPECT_GT(particles->loyalty(child), 0.0);
}

TEST_F(LoyaltyTest, InheritHierarchyIndependentParents) {
    Vec2 pos = {52.0, 50.0};
    Index child = particles->add_particle(pos, {0, 0}, 5.0, 1.0, 0.0);

    inherit_hierarchy(*particles, child, 0, 1);

    EXPECT_EQ(particles->superior(child), -1);
}

TEST_F(LoyaltyTest, InheritHierarchyLeaderParent) {
    particles->superior(0) = gid(3);
    particles->loyalty(0) = 0.8;

    Vec2 pos = {52.0, 50.0};
    Index child = particles->add_particle(pos, {0, 0}, 5.0, 1.0, 0.0);

    inherit_hierarchy(*particles, child, 3, 1);

    EXPECT_EQ(particles->superior(child), gid(3));
    EXPECT_NEAR(particles->loyalty(child), 0.8, 1e-10);
}

TEST_F(LoyaltyTest, ConquestStrongerWins) {
    particles->wealth(4) = 1000.0;
    particles->wealth(3) = 1.0;

    auto power = compute_effective_power(*particles);

    Index total_conquests = 0;
    for (int t = 0; t < 100; ++t) {
        total_conquests += attempt_conquest(*particles, cells, power, 5.0, rng);
        if (particles->superior(3) != -1) break;
    }

    bool any_attached = false;
    for (Index i = 0; i < particles->count(); ++i) {
        if (particles->superior(i) != -1) any_attached = true;
    }
    EXPECT_TRUE(any_attached || total_conquests > 0);
}
