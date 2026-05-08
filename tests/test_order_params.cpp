#include <gtest/gtest.h>
#include "analysis/order_params.hpp"

using namespace politeia;

TEST(OrderParamsTest, GiniPerfectEquality) {
    ParticleData pd(10);
    for (int i = 0; i < 10; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 5.0, 1.0, 0.0);
    }
    Real g = compute_gini(pd);
    EXPECT_NEAR(g, 0.0, 1e-10);
}

TEST(OrderParamsTest, GiniMaxInequality) {
    ParticleData pd(10);
    for (int i = 0; i < 9; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 0.0, 1.0, 0.0);
    }
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 100.0, 1.0, 0.0);

    Real g = compute_gini(pd);
    // For N=10 with one person holding everything: G = (N-1)/N = 0.9
    EXPECT_NEAR(g, 0.9, 0.01);
}

TEST(OrderParamsTest, GiniModerateInequality) {
    ParticleData pd(100);
    for (int i = 0; i < 100; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, static_cast<Real>(i + 1), 1.0, 0.0);
    }
    Real g = compute_gini(pd);
    // Uniform distribution on [1,100]: Gini ≈ 0.33
    EXPECT_GT(g, 0.25);
    EXPECT_LT(g, 0.40);
}

TEST(OrderParamsTest, WealthStats) {
    ParticleData pd(5);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 2.0, 1.0, 0.0);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 3.0, 1.0, 0.0);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 4.0, 1.0, 0.0);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 5.0, 1.0, 0.0);

    auto stats = compute_wealth_stats(pd);
    EXPECT_DOUBLE_EQ(stats.mean, 3.0);
    EXPECT_DOUBLE_EQ(stats.median, 3.0);
    EXPECT_DOUBLE_EQ(stats.min_val, 1.0);
    EXPECT_DOUBLE_EQ(stats.max_val, 5.0);
    EXPECT_DOUBLE_EQ(stats.total, 15.0);
}

TEST(OrderParamsTest, WealthHistogram) {
    ParticleData pd(10);
    for (int i = 0; i < 5; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    }
    for (int i = 0; i < 5; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 9.0, 1.0, 0.0);
    }

    auto hist = compute_wealth_histogram(pd, 10, 10.0);
    EXPECT_EQ(hist[1], 5u);  // bin [1,2): values=1.0
    EXPECT_EQ(hist[9], 5u);  // bin [9,10): values=9.0
}
