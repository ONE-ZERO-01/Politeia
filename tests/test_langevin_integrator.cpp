#include <gtest/gtest.h>
#include "integrator/langevin_integrator.hpp"
#include "domain/cell_list.hpp"

#include <cmath>
#include <numeric>

using namespace politeia;

TEST(LangevinIntegratorTest, EnergyConservationDeterministic) {
    // γ=0, T=0: pure Velocity-Verlet, energy must be conserved.
    const Index N = 50;
    ParticleData pd(N);

    std::mt19937_64 rng(123);
    std::uniform_real_distribution<Real> pos_dist(10.0, 90.0);
    std::normal_distribution<Real> mom_dist(0.0, 0.5);

    for (Index i = 0; i < N; ++i) {
        Vec2 pos = {pos_dist(rng), pos_dist(rng)};
        Vec2 mom = {mom_dist(rng), mom_dist(rng)};
        (void)pd.add_particle(pos, mom, 1.0, 1.0, 0.0);
    }

    CellList cl;
    cl.init(0.0, 100.0, 0.0, 100.0, 2.5);

    // No terrain wells for this test
    TerrainParams terrain;

    LangevinIntegrator integrator(
        0.001,   // dt (small for good conservation)
        1.0,     // mass
        0.0,     // γ = 0 (deterministic)
        0.0,     // T = 0 (deterministic)
        {1.0, 1.0, 2.5},  // SocialForceParams
        terrain,
        0.0, 100.0, 0.0, 100.0
    );

    // Initial force computation
    {
        auto& f = pd.force_buffer();
        std::fill(f.begin(), f.end(), 0.0);
        cl.build(pd.x_data(), pd.count());
        (void)compute_social_forces(pd.x_data(), f.data(), pd.count(), cl, {1.0, 1.0, 2.5});
    }

    // Run a few steps and check energy conservation
    IntegratorState state;
    Real E0 = 0.0;
    for (int step = 0; step < 500; ++step) {
        state = integrator.step(pd, cl);
        if (step == 0) E0 = state.total_energy();
    }

    Real E_final = state.total_energy();
    Real relative_error = std::abs(E_final - E0) / (std::abs(E0) + 1e-15);

    // Energy should be conserved to within ~1% for dt=0.001 over 500 steps
    EXPECT_LT(relative_error, 0.01)
        << "E0=" << E0 << " E_final=" << E_final << " rel_err=" << relative_error;
}

TEST(LangevinIntegratorTest, LangevinHasFluctuations) {
    // γ>0, T>0: Langevin mode, kinetic energy should fluctuate around k_B*T per DOF.
    const Index N = 50;
    ParticleData pd(N);

    // 粒子间距 >> σ 以避免排斥力导致的数值爆炸
    std::mt19937_64 init_rng(999);
    std::uniform_real_distribution<Real> init_dist(10.0, 90.0);
    for (Index i = 0; i < N; ++i) {
        Real x = init_dist(init_rng);
        Real y = init_dist(init_rng);
        (void)pd.add_particle({x, y}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    }

    CellList cl;
    cl.init(0.0, 100.0, 0.0, 100.0, 2.5);

    TerrainParams terrain;

    Real T = 2.0;
    Real gamma = 5.0;
    LangevinIntegrator integrator(
        0.005, 1.0, gamma, T,
        {1.0, 1.0, 2.5}, terrain,
        0.0, 100.0, 0.0, 100.0
    );

    {
        auto& f = pd.force_buffer();
        std::fill(f.begin(), f.end(), 0.0);
        cl.build(pd.x_data(), pd.count());
        (void)compute_social_forces(pd.x_data(), f.data(), pd.count(), cl, {1.0, 1.0, 2.5});
    }

    // Equilibrate
    for (int step = 0; step < 5000; ++step) {
        (void)integrator.step(pd, cl);
    }

    // Sample kinetic energy
    Real ke_sum = 0.0;
    const int samples = 2000;
    for (int step = 0; step < samples; ++step) {
        auto state = integrator.step(pd, cl);
        ke_sum += state.kinetic_energy;
    }
    Real ke_avg = ke_sum / samples;

    // Equipartition: <KE> = N * d * k_B * T / 2 = N * 2 * T / 2 = N * T
    Real expected_ke = N * T;
    Real tolerance = 0.5 * expected_ke;  // 50% tolerance for finite N and sampling

    EXPECT_NEAR(ke_avg, expected_ke, tolerance)
        << "Expected <KE> ≈ " << expected_ke << ", got " << ke_avg;
}
