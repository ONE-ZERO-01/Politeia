#include <gtest/gtest.h>
#include "population/plague.hpp"
#include "domain/cell_list.hpp"

using namespace politeia;

TEST(PlagueTest, NoTriggerAtLowDensity) {
    ParticleData pd(10, 2, 2);
    (void)pd.add_particle({5.0, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);

    CellList cl;
    cl.init(0.0, 100.0, 0.0, 100.0, 3.0);
    cl.build(pd.x_data(), pd.count());

    PlagueManager mgr;
    mgr.init(pd.count(), 2);

    PlagueParams params;
    params.trigger_density = 50.0;

    std::mt19937_64 rng(42);
    Index deaths = mgr.update(pd, cl, params, 0.01, 1.0, rng);

    EXPECT_EQ(deaths, 0u);
    EXPECT_FALSE(mgr.has_active_plague());
}

TEST(PlagueTest, ImmuneNotDie) {
    // 有免疫力的人不应该因瘟疫死亡
    ParticleData pd(20, 2, 2);

    for (int i = 0; i < 10; ++i) {
        Index idx = pd.add_particle(
            {5.0 + i * 0.3, 5.0}, {0.0, 0.0}, 10.0, 1.0, 25.0
        );
        pd.immunity(idx, 0) = 1.0;  // 对所有病原体完全免疫
        pd.immunity(idx, 1) = 1.0;
    }

    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 5.0);
    cl.build(pd.x_data(), pd.count());

    PlagueManager mgr;
    mgr.init(pd.count(), 2);

    PlagueParams params;
    params.trigger_density = 0.01;
    params.trigger_rate = 100.0;
    params.base_mortality = 1.0;
    params.recovery_time = 0.001;

    std::mt19937_64 rng(42);

    Index total_deaths = 0;
    for (int step = 0; step < 100; ++step) {
        cl.build(pd.x_data(), pd.count());
        total_deaths += mgr.update(pd, cl, params, 100.0, 1.0, rng);
    }

    // Most should survive due to immunity
    Index alive = 0;
    for (Index i = 0; i < pd.count(); ++i) {
        if (pd.status(i) == ParticleStatus::Alive) alive++;
    }
    EXPECT_GT(alive, 5u) << "Immune individuals should mostly survive plague";
}

TEST(PlagueTest, ImmunityInheritance) {
    ParticleData pd(10, 2, 3);

    Index a = pd.add_particle({0.0, 0.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);
    pd.immunity(a, 0) = 1.0;
    pd.immunity(a, 1) = 0.0;
    pd.immunity(a, 2) = 0.6;

    Index b = pd.add_particle({1.0, 0.0}, {0.0, 0.0}, 10.0, 1.0, 25.0);
    pd.immunity(b, 0) = 0.0;
    pd.immunity(b, 1) = 1.0;
    pd.immunity(b, 2) = 0.4;

    Index child = pd.add_particle({0.5, 0.0}, {0.0, 0.0}, 5.0, 1.0, 0.0);

    inherit_immunity(pd, child, a, b, 0.5);

    // child = 0.5 * (parent_avg)
    EXPECT_NEAR(pd.immunity(child, 0), 0.5 * 0.5, 1e-10);  // 0.5*(1+0)/2 = 0.25
    EXPECT_NEAR(pd.immunity(child, 1), 0.5 * 0.5, 1e-10);  // 0.5*(0+1)/2 = 0.25
    EXPECT_NEAR(pd.immunity(child, 2), 0.5 * 0.5, 1e-10);  // 0.5*(0.6+0.4)/2 = 0.25
}

TEST(PlagueTest, ResizeHandling) {
    PlagueManager mgr;
    mgr.init(10, 2);
    mgr.resize(20);
    mgr.resize(5);
}
