#include <gtest/gtest.h>
#include "population/reproduction.hpp"
#include "population/mortality.hpp"
#include "domain/cell_list.hpp"

using namespace politeia;

TEST(PopulationTest, FertilityCurve) {
    ReproductionParams params;

    // Before puberty
    EXPECT_DOUBLE_EQ(fertility(10.0, params), 0.0);
    // After menopause
    EXPECT_DOUBLE_EQ(fertility(50.0, params), 0.0);
    // At peak: should be max_fertility
    Real f_peak = fertility(params.peak_fertility_age, params);
    EXPECT_NEAR(f_peak, params.max_fertility, 0.001);
    // Between puberty and menopause: positive
    Real f_20 = fertility(20.0, params);
    EXPECT_GT(f_20, 0.0);
    EXPECT_LE(f_20, params.max_fertility);
}

TEST(PopulationTest, ProductivityFactor) {
    // Child: low
    EXPECT_LT(productivity_factor(5.0), 0.5);
    // Prime age: high
    EXPECT_GT(productivity_factor(30.0), 0.9);
    // Old age: declining
    EXPECT_LT(productivity_factor(70.0), productivity_factor(30.0));
    // Newborn: zero
    EXPECT_NEAR(productivity_factor(0.0), 0.0, 1e-10);
}

TEST(PopulationTest, AgeAdvancement) {
    ParticleData pd(5);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 20.0);
    (void)pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 30.0);

    advance_age(pd, 1.0);

    EXPECT_DOUBLE_EQ(pd.age(0), 21.0);
    EXPECT_DOUBLE_EQ(pd.age(1), 31.0);
}

TEST(PopulationTest, GompertzMortality) {
    // Old particles should die more frequently than young ones
    const int trials = 10000;
    std::mt19937_64 rng(42);

    int young_deaths = 0;
    int old_deaths = 0;
    MortalityParams params;
    params.gompertz_alpha = 1e-4;
    params.gompertz_beta = 0.085;
    params.accident_rate = 0.0;
    params.survival_threshold = 0.0;
    params.max_age = 200.0;

    for (int t = 0; t < trials; ++t) {
        ParticleData pd_young(2);
        (void)pd_young.add_particle({0.0, 0.0}, {0.0, 0.0}, 100.0, 1.0, 20.0);
        Index d = apply_mortality(pd_young, params, 1.0, rng);
        young_deaths += d;

        ParticleData pd_old(2);
        (void)pd_old.add_particle({0.0, 0.0}, {0.0, 0.0}, 100.0, 1.0, 70.0);
        d = apply_mortality(pd_old, params, 1.0, rng);
        old_deaths += d;
    }

    EXPECT_GT(old_deaths, young_deaths)
        << "Old people should die more than young. young=" << young_deaths << " old=" << old_deaths;
}

TEST(PopulationTest, ReproductionBasic) {
    ParticleData pd(20);
    // Two fertile-age particles close together with enough wealth
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);
    (void)pd.add_particle({5.5, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    ReproductionParams params;
    params.max_fertility = 1.0;  // high probability for testing
    std::mt19937_64 rng(42);

    // Try many times since reproduction is probabilistic
    Index total_births = 0;
    for (int t = 0; t < 100; ++t) {
        cl.build(pd.x_data(), pd.count());
        total_births += attempt_reproduction(pd, cl, params, 0.0, rng);
    }

    EXPECT_GT(total_births, 0u) << "Should have at least some births";
    EXPECT_GT(pd.count(), 2u) << "Population should have grown";
}

TEST(PopulationTest, NoBreedingIfPoor) {
    ParticleData pd(10);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 0.01, 1.0, 25.0);  // too poor
    (void)pd.add_particle({5.5, 5.0}, {0.0, 0.0}, 0.01, 1.0, 25.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    ReproductionParams params;
    params.max_fertility = 1.0;
    std::mt19937_64 rng(42);

    Index births = attempt_reproduction(pd, cl, params, 0.0, rng);
    EXPECT_EQ(births, 0u);
}

TEST(PopulationTest, NoBreedingIfTooYoung) {
    ParticleData pd(10);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 5.0);  // too young
    (void)pd.add_particle({5.5, 5.0}, {0.0, 0.0}, 10.0, 1.0, 5.0);

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    ReproductionParams params;
    params.max_fertility = 1.0;
    std::mt19937_64 rng(42);

    Index births = attempt_reproduction(pd, cl, params, 0.0, rng);
    EXPECT_EQ(births, 0u);
}
