#include <gtest/gtest.h>
#include "interaction/tech_spread.hpp"
#include "domain/cell_list.hpp"

using namespace politeia;

TEST(TechSpreadTest, DriftIncreasesEps) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);
    pd.culture(0, 0) = 2.0;
    pd.culture(0, 1) = 1.0;

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    Real eps_before = pd.epsilon(0);

    TechParams params;
    params.drift_rate = 0.1;
    params.jump_base_rate = 0.0;
    params.wealth_jump_rate_pos = 0.0;
    params.wealth_jump_rate_neg = 0.0;

    std::mt19937_64 rng(42);
    (void)evolve_technology(pd, cl, params, 1.0, rng);

    EXPECT_GT(pd.epsilon(0), eps_before);
}

TEST(TechSpreadTest, SpreadFromHighToLow) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 3.0, 25.0);  // high ε
    (void)pd.add_particle({5.5, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);  // low ε

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    TechParams params;
    params.spread_rate = 0.5;
    params.drift_rate = 0.0;
    params.jump_base_rate = 0.0;
    params.wealth_jump_rate_pos = 0.0;
    params.wealth_jump_rate_neg = 0.0;

    std::mt19937_64 rng(42);
    Real eps1_before = pd.epsilon(1);
    (void)evolve_technology(pd, cl, params, 1.0, rng);

    EXPECT_GT(pd.epsilon(1), eps1_before) << "Low-ε particle should learn from high-ε neighbor";
}

TEST(TechSpreadTest, NoSpreadBeyondRange) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({2.0, 5.0}, {0.0, 0.0}, 10.0, 5.0, 25.0);
    (void)pd.add_particle({15.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    TechParams params;
    params.spread_rate = 0.5;
    params.drift_rate = 0.0;
    params.jump_base_rate = 0.0;
    params.wealth_jump_rate_pos = 0.0;
    params.wealth_jump_rate_neg = 0.0;

    std::mt19937_64 rng(42);
    (void)evolve_technology(pd, cl, params, 1.0, rng);

    EXPECT_DOUBLE_EQ(pd.epsilon(1), 1.0) << "Far particle should not change ε";
}

TEST(TechSpreadTest, PoissonJumpsOccur) {
    ParticleData pd(100, 2);
    for (int i = 0; i < 100; ++i) {
        Index idx = pd.add_particle({50.0, 50.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);
        pd.culture(idx, 0) = 3.0;
    }

    CellList cl;
    cl.init(0.0, 100.0, 0.0, 100.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    TechParams params;
    params.drift_rate = 0.0;
    params.spread_rate = 0.0;
    params.jump_base_rate = 0.1;
    params.wealth_jump_rate_pos = 0.0;
    params.wealth_jump_rate_neg = 0.0;

    std::mt19937_64 rng(42);
    JumpStats stats = evolve_technology(pd, cl, params, 1.0, rng);

    EXPECT_GT(stats.eps_jumps, 0u) << "Should have some ε breakthroughs";
}

TEST(TechSpreadTest, WealthJumpsConserveSurvival) {
    ParticleData pd(10, 2);
    for (int i = 0; i < 10; ++i) {
        (void)pd.add_particle({50.0, 50.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);
    }

    CellList cl;
    cl.init(0.0, 100.0, 0.0, 100.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    TechParams params;
    params.drift_rate = 0.0;
    params.spread_rate = 0.0;
    params.jump_base_rate = 0.0;
    params.wealth_jump_rate_pos = 0.0;
    params.wealth_jump_rate_neg = 0.5;
    params.wealth_jump_fraction = 0.9;

    std::mt19937_64 rng(42);
    (void)evolve_technology(pd, cl, params, 1.0, rng);

    for (Index i = 0; i < pd.count(); ++i) {
        EXPECT_GE(pd.wealth(i), 0.0) << "Wealth should never go negative";
    }
}

TEST(TechSpreadTest, MeanEpsilon) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 2.0, 0.0);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 4.0, 0.0);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 6.0, 0.0);

    Real mean = compute_mean_epsilon(pd);
    EXPECT_DOUBLE_EQ(mean, 4.0);
}
