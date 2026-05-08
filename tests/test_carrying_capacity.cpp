#include <gtest/gtest.h>
#include "population/carrying_capacity.hpp"
#include "population/reproduction.hpp"
#include "interaction/resource_exchange.hpp"
#include "domain/cell_list.hpp"

using namespace politeia;

class CarryingCapacityTest : public ::testing::Test {
protected:
    static constexpr Real XMIN = 0, XMAX = 50, YMIN = 0, YMAX = 50;
    static constexpr Real CUTOFF = 5.0;

    ParticleData particles{100, 3};
    CellList cells;

    void SetUp() override {
        cells.init(XMIN, XMAX, YMIN, YMAX, CUTOFF);
    }

    void place_cluster(Real cx, Real cy, int count, Real spacing = 0.5) {
        int side = static_cast<int>(std::ceil(std::sqrt(count)));
        int placed = 0;
        for (int iy = 0; iy < side && placed < count; ++iy) {
            for (int ix = 0; ix < side && placed < count; ++ix) {
                Vec2 pos = {cx + ix * spacing, cy + iy * spacing};
                particles.add_particle(pos, {0, 0}, 5.0, 1.0, 25.0);
                ++placed;
            }
        }
    }
};

TEST_F(CarryingCapacityTest, DensityIncreasesWithCrowding) {
    place_cluster(10.0, 10.0, 1);
    cells.build(particles.x_data(), particles.count());
    auto d1 = compute_local_density(particles, cells, CUTOFF);
    EXPECT_GT(d1[0], 0.0);
    Real single_density = d1[0];

    place_cluster(10.5, 10.5, 9);
    cells.build(particles.x_data(), particles.count());
    auto d2 = compute_local_density(particles, cells, CUTOFF);
    EXPECT_GT(d2[0], single_density);
}

TEST_F(CarryingCapacityTest, CarryingCapacityProportionalToTerrain) {
    place_cluster(10.0, 10.0, 3);

    std::vector<Real> V(particles.count());
    V[0] = -2.0;  // fertile
    V[1] = -1.0;  // moderate
    V[2] = 0.5;   // barren

    auto K = compute_carrying_capacity(particles, 50.0, V.data());
    EXPECT_DOUBLE_EQ(K[0], 100.0);  // 50 * 2.0
    EXPECT_DOUBLE_EQ(K[1], 50.0);   // 50 * 1.0
    EXPECT_DOUBLE_EQ(K[2], 0.0);    // barren: max(0, -0.5) = 0
}

TEST_F(CarryingCapacityTest, SuppressionFactor) {
    EXPECT_DOUBLE_EQ(density_suppression(0.0, 10.0), 1.0);
    EXPECT_DOUBLE_EQ(density_suppression(5.0, 10.0), 0.5);
    EXPECT_DOUBLE_EQ(density_suppression(10.0, 10.0), 0.0);
    EXPECT_DOUBLE_EQ(density_suppression(15.0, 10.0), 0.0);
    EXPECT_DOUBLE_EQ(density_suppression(5.0, 0.0), 0.0);   // barren land
}

TEST_F(CarryingCapacityTest, ResourceCompetitionReducesProduction) {
    place_cluster(10.0, 10.0, 5);

    std::vector<Real> V(particles.count(), -1.0);  // all fertile
    Real base_prod = 0.5;
    Real consumption = 0.01;
    Real dt = 0.01;

    Real w_before = particles.wealth(0);
    apply_resource_dynamics(particles, dt, consumption, base_prod, V.data(), nullptr);
    Real gain_no_competition = particles.wealth(0) - w_before;

    for (Index i = 0; i < particles.count(); ++i) {
        particles.wealth(i) = 5.0;
    }

    std::vector<Real> dfactor(particles.count(), 0.3);
    w_before = particles.wealth(0);
    apply_resource_dynamics(particles, dt, consumption, base_prod, V.data(), dfactor.data());
    Real gain_with_competition = particles.wealth(0) - w_before;

    EXPECT_LT(gain_with_competition, gain_no_competition);
}

TEST_F(CarryingCapacityTest, FertilitySuppressionAtHighDensity) {
    Real age = 25.0;
    ReproductionParams params;
    params.max_fertility = 0.1;

    Real base_fert = fertility(age, params);
    EXPECT_GT(base_fert, 0.0);

    Real suppress_half = density_suppression(5.0, 10.0);
    Real suppress_full = density_suppression(10.0, 10.0);

    EXPECT_NEAR(suppress_half, 0.5, 1e-10);
    EXPECT_DOUBLE_EQ(suppress_full, 0.0);
}

TEST_F(CarryingCapacityTest, IsolatedParticlesLowDensity) {
    particles.add_particle({5.0, 5.0}, {0, 0}, 5.0, 1.0, 25.0);
    particles.add_particle({40.0, 40.0}, {0, 0}, 5.0, 1.0, 25.0);

    cells.build(particles.x_data(), particles.count());
    auto d = compute_local_density(particles, cells, CUTOFF);

    Real area = M_PI * CUTOFF * CUTOFF;
    Real expected = 1.0 / area;
    EXPECT_NEAR(d[0], expected, 1e-10);
    EXPECT_NEAR(d[1], expected, 1e-10);
}
