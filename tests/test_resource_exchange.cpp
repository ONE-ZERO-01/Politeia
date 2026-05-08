#include <gtest/gtest.h>
#include "interaction/resource_exchange.hpp"
#include "domain/cell_list.hpp"

#include <cmath>
#include <numeric>

using namespace politeia;

TEST(ResourceExchangeTest, SymmetricRule) {
    // If two particles have equal ability, no net transfer
    ParticleData pd(10);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 0.0);
    (void)pd.add_particle({6.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 0.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    Real w0_before = pd.wealth(0);
    Real w1_before = pd.wealth(1);

    ExchangeParams params{0.1, 3.0};
    (void)exchange_resources(pd, cl, params);

    EXPECT_DOUBLE_EQ(pd.wealth(0), w0_before);
    EXPECT_DOUBLE_EQ(pd.wealth(1), w1_before);
}

TEST(ResourceExchangeTest, WealthConservation) {
    // Total wealth must be conserved in a closed exchange
    ParticleData pd(10);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 20.0, 2.0, 0.0);
    (void)pd.add_particle({6.0, 5.0}, {0.0, 0.0}, 5.0, 1.0, 0.0);
    (void)pd.add_particle({5.5, 6.0}, {0.0, 0.0}, 8.0, 1.5, 0.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    Real total_before = pd.wealth(0) + pd.wealth(1) + pd.wealth(2);

    ExchangeParams params{0.1, 3.0};
    (void)exchange_resources(pd, cl, params);

    Real total_after = pd.wealth(0) + pd.wealth(1) + pd.wealth(2);
    EXPECT_NEAR(total_after, total_before, 1e-10);
}

TEST(ResourceExchangeTest, StrongerGains) {
    // Particle with higher ability (w*ε) should gain wealth
    ParticleData pd(10);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 2.0, 0.0);  // A=20
    (void)pd.add_particle({6.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 0.0);  // A=10

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    ExchangeParams params{0.1, 3.0};
    (void)exchange_resources(pd, cl, params);

    EXPECT_GT(pd.wealth(0), 10.0);  // stronger gains
    EXPECT_LT(pd.wealth(1), 10.0);  // weaker loses
}

TEST(ResourceExchangeTest, NoBeyondCutoff) {
    // Particles beyond cutoff don't exchange
    ParticleData pd(10);
    (void)pd.add_particle({2.0, 5.0}, {0.0, 0.0}, 100.0, 5.0, 0.0);
    (void)pd.add_particle({15.0, 5.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    ExchangeParams params{0.1, 3.0};
    (void)exchange_resources(pd, cl, params);

    EXPECT_DOUBLE_EQ(pd.wealth(0), 100.0);
    EXPECT_DOUBLE_EQ(pd.wealth(1), 1.0);
}

TEST(ResourceExchangeTest, SurvivalThreshold) {
    ParticleData pd(10);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);   // above threshold
    (void)pd.add_particle({6.0, 5.0}, {0.0, 0.0}, 0.05, 1.0, 0.0);  // below threshold
    (void)pd.add_particle({7.0, 5.0}, {0.0, 0.0}, 0.5, 1.0, 0.0);   // above threshold

    Index deaths = apply_survival_threshold(pd, 0.1);
    EXPECT_EQ(deaths, 1u);
    EXPECT_EQ(pd.status(1), ParticleStatus::Dead);
    EXPECT_EQ(pd.status(0), ParticleStatus::Alive);
    EXPECT_EQ(pd.status(2), ParticleStatus::Alive);
}
