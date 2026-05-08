#include <gtest/gtest.h>
#include "core/particle_data.hpp"

using namespace politeia;

TEST(ParticleDataTest, InitialState) {
    ParticleData pd(100);
    EXPECT_EQ(pd.count(), 0u);
    EXPECT_GE(pd.capacity(), 100u);
}

TEST(ParticleDataTest, AddParticle) {
    ParticleData pd(10);

    Vec2 pos = {1.0, 2.0};
    Vec2 mom = {0.5, -0.5};
    Index idx = pd.add_particle(pos, mom, 10.0, 1.5, 20.0);

    EXPECT_EQ(idx, 0u);
    EXPECT_EQ(pd.count(), 1u);

    auto p = pd.position(0);
    EXPECT_DOUBLE_EQ(p[0], 1.0);
    EXPECT_DOUBLE_EQ(p[1], 2.0);

    auto m = pd.momentum(0);
    EXPECT_DOUBLE_EQ(m[0], 0.5);
    EXPECT_DOUBLE_EQ(m[1], -0.5);

    EXPECT_DOUBLE_EQ(pd.wealth(0), 10.0);
    EXPECT_DOUBLE_EQ(pd.epsilon(0), 1.5);
    EXPECT_DOUBLE_EQ(pd.age(0), 20.0);
    EXPECT_EQ(pd.status(0), ParticleStatus::Alive);
}

TEST(ParticleDataTest, AddMultiple) {
    ParticleData pd(4);
    for (int i = 0; i < 4; ++i) {
        Vec2 pos = {static_cast<Real>(i), static_cast<Real>(i * 2)};
        Vec2 mom = {0.0, 0.0};
        (void)pd.add_particle(pos, mom, static_cast<Real>(i + 1), 1.0, 0.0);
    }
    EXPECT_EQ(pd.count(), 4u);

    EXPECT_DOUBLE_EQ(pd.wealth(2), 3.0);
    auto p3 = pd.position(3);
    EXPECT_DOUBLE_EQ(p3[0], 3.0);
    EXPECT_DOUBLE_EQ(p3[1], 6.0);
}

TEST(ParticleDataTest, AutoGrow) {
    ParticleData pd(2);

    for (int i = 0; i < 10; ++i) {
        (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    }
    EXPECT_EQ(pd.count(), 10u);
    EXPECT_GE(pd.capacity(), 10u);

    EXPECT_DOUBLE_EQ(pd.wealth(9), 1.0);
}

TEST(ParticleDataTest, MarkDeadAndCompact) {
    ParticleData pd(10);

    (void)pd.add_particle({1.0, 1.0}, {0.0, 0.0}, 10.0, 1.0, 0.0);
    (void)pd.add_particle({2.0, 2.0}, {0.0, 0.0}, 20.0, 2.0, 0.0);
    (void)pd.add_particle({3.0, 3.0}, {0.0, 0.0}, 30.0, 3.0, 0.0);
    (void)pd.add_particle({4.0, 4.0}, {0.0, 0.0}, 40.0, 4.0, 0.0);
    EXPECT_EQ(pd.count(), 4u);

    pd.mark_dead(1);
    pd.mark_dead(2);

    Index removed = pd.compact();
    EXPECT_EQ(removed, 2u);
    EXPECT_EQ(pd.count(), 2u);

    EXPECT_DOUBLE_EQ(pd.wealth(0), 10.0);
    EXPECT_DOUBLE_EQ(pd.wealth(1), 40.0);

    auto p0 = pd.position(0);
    EXPECT_DOUBLE_EQ(p0[0], 1.0);
    auto p1 = pd.position(1);
    EXPECT_DOUBLE_EQ(p1[0], 4.0);

    EXPECT_DOUBLE_EQ(pd.epsilon(0), 1.0);
    EXPECT_DOUBLE_EQ(pd.epsilon(1), 4.0);
}

TEST(ParticleDataTest, CultureVector) {
    const int cdim = 3;
    ParticleData pd(10, cdim);

    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    pd.culture(0, 0) = 0.5;
    pd.culture(0, 1) = -0.3;
    pd.culture(0, 2) = 0.8;

    EXPECT_DOUBLE_EQ(pd.culture(0, 0), 0.5);
    EXPECT_DOUBLE_EQ(pd.culture(0, 1), -0.3);
    EXPECT_DOUBLE_EQ(pd.culture(0, 2), 0.8);
    EXPECT_EQ(pd.culture_dim(), cdim);
}

TEST(ParticleDataTest, SetPositionAndMomentum) {
    ParticleData pd(10);
    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    pd.set_position(0, {5.0, 7.0});
    pd.set_momentum(0, {-1.0, 2.0});

    auto pos = pd.position(0);
    EXPECT_DOUBLE_EQ(pos[0], 5.0);
    EXPECT_DOUBLE_EQ(pos[1], 7.0);

    auto mom = pd.momentum(0);
    EXPECT_DOUBLE_EQ(mom[0], -1.0);
    EXPECT_DOUBLE_EQ(mom[1], 2.0);
}

TEST(ParticleDataTest, CompactPreservesCulture) {
    const int cdim = 2;
    ParticleData pd(10, cdim);

    (void)pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    pd.culture(0, 0) = 0.1;
    pd.culture(0, 1) = 0.2;

    (void)pd.add_particle({1.0, 1.0}, {0.0, 0.0}, 2.0, 2.0, 0.0);
    pd.culture(1, 0) = 0.3;
    pd.culture(1, 1) = 0.4;

    (void)pd.add_particle({2.0, 2.0}, {0.0, 0.0}, 3.0, 3.0, 0.0);
    pd.culture(2, 0) = 0.5;
    pd.culture(2, 1) = 0.6;

    pd.mark_dead(1);
    pd.compact();

    EXPECT_EQ(pd.count(), 2u);
    EXPECT_DOUBLE_EQ(pd.culture(0, 0), 0.1);
    EXPECT_DOUBLE_EQ(pd.culture(0, 1), 0.2);
    EXPECT_DOUBLE_EQ(pd.culture(1, 0), 0.5);
    EXPECT_DOUBLE_EQ(pd.culture(1, 1), 0.6);
}
