#include <gtest/gtest.h>
#include "force/social_force.hpp"
#include "domain/cell_list.hpp"

#include <cmath>
#include <vector>

using namespace politeia;

TEST(SocialForceTest, NewtonThirdLaw) {
    CellList cl;
    cl.init(0.0, 10.0, 0.0, 10.0, 3.0);

    Real x[] = {3.0, 5.0,   4.5, 5.0};
    Index count = 2;
    cl.build(x, count);

    std::vector<Real> f(count * 2, 0.0);
    SocialForceParams params{1.0, 1.0, 2.5};
    (void)compute_social_forces(x, f.data(), count, cl, params);

    EXPECT_NEAR(f[0] + f[2], 0.0, 1e-12);
    EXPECT_NEAR(f[1] + f[3], 0.0, 1e-12);
}

TEST(SocialForceTest, RepulsiveWhenTooClose) {
    CellList cl;
    cl.init(0.0, 10.0, 0.0, 10.0, 3.0);

    Real x[] = {5.0, 5.0,   5.3, 5.0};
    Index count = 2;
    cl.build(x, count);

    std::vector<Real> f(count * 2, 0.0);
    SocialForceParams params{1.0, 1.0, 2.5};
    (void)compute_social_forces(x, f.data(), count, cl, params);

    EXPECT_LT(f[0], 0.0);
    EXPECT_GT(f[2], 0.0);
}

TEST(SocialForceTest, AttractiveAtComfortDistance) {
    CellList cl;
    cl.init(0.0, 10.0, 0.0, 10.0, 3.0);

    Real x[] = {4.0, 5.0,   5.5, 5.0};
    Index count = 2;
    cl.build(x, count);

    std::vector<Real> f(count * 2, 0.0);
    SocialForceParams params{1.0, 1.0, 2.5};
    (void)compute_social_forces(x, f.data(), count, cl, params);

    EXPECT_GT(f[0], 0.0);
    EXPECT_LT(f[2], 0.0);
}

TEST(SocialForceTest, NoInteractionBeyondVision) {
    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 3.0);

    Real x[] = {2.0, 5.0,   15.0, 5.0};
    Index count = 2;
    cl.build(x, count);

    std::vector<Real> f(count * 2, 0.0);
    SocialForceParams params{1.0, 1.0, 2.5};
    (void)compute_social_forces(x, f.data(), count, cl, params);

    EXPECT_DOUBLE_EQ(f[0], 0.0);
    EXPECT_DOUBLE_EQ(f[1], 0.0);
    EXPECT_DOUBLE_EQ(f[2], 0.0);
    EXPECT_DOUBLE_EQ(f[3], 0.0);
}
