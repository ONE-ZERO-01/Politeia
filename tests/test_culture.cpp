#include <gtest/gtest.h>
#include "interaction/culture_dynamics.hpp"
#include "domain/cell_list.hpp"

#include <cmath>

using namespace politeia;

TEST(CultureTest, DistanceZeroForSame) {
    ParticleData pd(5, 3);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    pd.culture(0, 0) = 1.0; pd.culture(0, 1) = 0.0; pd.culture(0, 2) = 0.0;
    pd.culture(1, 0) = 1.0; pd.culture(1, 1) = 0.0; pd.culture(1, 2) = 0.0;

    EXPECT_NEAR(culture_distance(pd, 0, 1), 0.0, 1e-12);
}

TEST(CultureTest, DistanceNonZero) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    pd.culture(0, 0) = 1.0; pd.culture(0, 1) = 0.0;
    pd.culture(1, 0) = 0.0; pd.culture(1, 1) = 1.0;

    EXPECT_NEAR(culture_distance(pd, 0, 1), std::sqrt(2.0), 1e-12);
}

TEST(CultureTest, AssimilationConverges) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({5.5, 5.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    pd.culture(0, 0) = 1.0; pd.culture(0, 1) = 0.0;
    pd.culture(1, 0) = 0.0; pd.culture(1, 1) = 1.0;

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);

    CultureParams params;
    params.assimilation_rate = 0.5;

    Real dist_before = culture_distance(pd, 0, 1);

    for (int i = 0; i < 100; ++i) {
        cl.build(pd.x_data(), pd.count());
        evolve_culture(pd, cl, params, 0.01);
    }

    Real dist_after = culture_distance(pd, 0, 1);
    EXPECT_LT(dist_after, dist_before) << "Culture distance should decrease through assimilation";
}

TEST(CultureTest, NoAssimilationBeyondRange) {
    ParticleData pd(5, 2);
    (void)pd.add_particle({2.0, 5.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({15.0, 5.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    pd.culture(0, 0) = 1.0; pd.culture(0, 1) = 0.0;
    pd.culture(1, 0) = 0.0; pd.culture(1, 1) = 1.0;

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);

    CultureParams params;

    cl.build(pd.x_data(), pd.count());
    evolve_culture(pd, cl, params, 0.01);

    EXPECT_DOUBLE_EQ(pd.culture(0, 0), 1.0);
    EXPECT_DOUBLE_EQ(pd.culture(1, 1), 1.0);
}

TEST(CultureTest, OrderParamUniform) {
    // All culture vectors pointing same direction → Q ≈ 1
    ParticleData pd(10, 2);
    for (int i = 0; i < 10; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
        pd.culture(i, 0) = 1.0;
        pd.culture(i, 1) = 0.0;
    }
    Real Q = compute_culture_order_param(pd);
    EXPECT_NEAR(Q, 1.0, 0.01);
}

TEST(CultureTest, OrderParamDiverse) {
    // Culture vectors in opposite directions → Q ≈ 0
    ParticleData pd(10, 2);
    for (int i = 0; i < 5; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
        pd.culture(i, 0) = 1.0;
        pd.culture(i, 1) = 0.0;
    }
    for (int i = 5; i < 10; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
        pd.culture(i, 0) = -1.0;
        pd.culture(i, 1) = 0.0;
    }
    Real Q = compute_culture_order_param(pd);
    EXPECT_NEAR(Q, 0.0, 0.01);
}

TEST(CultureTest, ForceModifierSign) {
    CultureParams params;
    params.repulsion_threshold = 1.5;

    // Similar cultures → attraction (positive)
    EXPECT_GT(culture_force_modifier(0.5, params), 0.0);
    // Very different cultures → repulsion (negative)
    EXPECT_LT(culture_force_modifier(3.0, params), 0.0);
    // At threshold → zero
    EXPECT_NEAR(culture_force_modifier(params.repulsion_threshold, params), 0.0, 0.01);
}
