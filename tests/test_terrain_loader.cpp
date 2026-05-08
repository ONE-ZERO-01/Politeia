#include "force/terrain_loader.hpp"
#include "core/particle_data.hpp"

#include <gtest/gtest.h>
#include <cmath>
#include <fstream>
#include <filesystem>

using namespace politeia;

// ─── Synthetic Terrain ──────────────────────────────────

TEST(TerrainGridTest, SyntheticValley) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    EXPECT_TRUE(grid.loaded());
    EXPECT_EQ(grid.nrows(), 101);
    EXPECT_EQ(grid.ncols(), 101);
    EXPECT_NEAR(grid.xmin(), 0.0, 1e-10);
    EXPECT_NEAR(grid.ymin(), 0.0, 1e-10);

    // Center of valley should have minimum elevation
    Real h_center = grid.elevation(50, 50);
    Real h_edge = grid.elevation(0, 0);
    EXPECT_LT(h_center, h_edge);
    EXPECT_NEAR(h_center, grid.h_min(), 1.0);
}

TEST(TerrainGridTest, SyntheticFlat) {
    TerrainGrid grid;
    grid.generate_synthetic(51, 51, 0, 0, 50, 50, "flat");

    EXPECT_TRUE(grid.loaded());
    EXPECT_NEAR(grid.elevation(25, 25), 0.0, 1e-10);
    EXPECT_NEAR(grid.h_min(), 0.0, 1e-10);
    EXPECT_NEAR(grid.h_max(), 0.0, 1e-10);

    auto grad = grid.gradient(25, 25);
    EXPECT_NEAR(grad[0], 0.0, 1e-8);
    EXPECT_NEAR(grad[1], 0.0, 1e-8);
}

TEST(TerrainGridTest, SyntheticRidge) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "ridge");

    Real h_center = grid.elevation(50, 50);
    Real h_edge = grid.elevation(0, 0);
    EXPECT_GT(h_center, h_edge);
}

// ─── Bilinear Interpolation ─────────────────────────────

TEST(TerrainGridTest, BilinearInterpolation) {
    TerrainGrid grid;
    grid.generate_synthetic(3, 3, 0, 0, 2, 2, "flat");

    // Flat terrain: interpolation anywhere = 0
    EXPECT_NEAR(grid.elevation(0.5, 0.5), 0.0, 1e-10);
    EXPECT_NEAR(grid.elevation(1.5, 1.5), 0.0, 1e-10);
}

TEST(TerrainGridTest, ClampOutOfBounds) {
    TerrainGrid grid;
    grid.generate_synthetic(11, 11, 0, 0, 10, 10, "valley");

    // Outside domain should clamp to edge
    Real h_inside = grid.elevation(0, 0);
    Real h_outside = grid.elevation(-5, -5);
    EXPECT_NEAR(h_inside, h_outside, 1e-10);
}

// ─── Gradient and Force ─────────────────────────────────

TEST(TerrainGridTest, GradientPointsToValley) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    // At (70, 50), gradient dh/dx should be positive (elevation increases away from center)
    auto grad = grid.gradient(70, 50);
    EXPECT_GT(grad[0], 0.0);

    // Force should point toward center (valley)
    auto f = grid.force(70, 50, 1.0);
    EXPECT_LT(f[0], 0.0);  // force pushes back toward center
}

TEST(TerrainGridTest, ForceAtCenter) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    // At center of symmetric valley, gradient ≈ 0
    auto grad = grid.gradient(50, 50);
    EXPECT_NEAR(grad[0], 0.0, 0.1);
    EXPECT_NEAR(grad[1], 0.0, 0.1);
}

// ─── Potential ───────────────────────────────────────────

TEST(TerrainGridTest, PotentialMinAtValley) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    Real v_center = grid.potential(50, 50, 1.0);
    Real v_edge = grid.potential(0, 0, 1.0);

    EXPECT_LT(v_center, v_edge);
    EXPECT_NEAR(v_center, 0.0, 1.0);  // center ≈ h_min, so V ≈ 0
}

TEST(TerrainGridTest, ScaleFactor) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    Real v1 = grid.potential(0, 0, 1.0);
    Real v2 = grid.potential(0, 0, 2.0);
    EXPECT_NEAR(v2, 2.0 * v1, 1e-10);
}

// ─── Batch Force Computation ────────────────────────────

TEST(TerrainGridTest, BatchForces) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    ParticleData particles(10, 4);
    Real positions[] = {70, 50, 30, 50, 50, 70, 50, 30, 50, 50,
                        60, 40, 40, 60, 80, 20, 20, 80, 10, 90};

    for (int i = 0; i < 10; ++i) {
        Vec2 pos = {positions[2*i], positions[2*i+1]};
        Vec2 mom = {0, 0};
        (void)particles.add_particle(pos, mom, 1.0, 1.0, 25.0);
    }

    std::vector<Real> forces(particles.count() * 2, 0.0);
    Real pe = compute_grid_terrain_forces(
        particles.x_data(), forces.data(), particles.count(), grid, 1.0);

    EXPECT_GT(pe, 0.0);
    // Particle at (70,50) should be pushed left (toward center)
    EXPECT_LT(forces[0], 0.0);
}

TEST(TerrainGridTest, BatchForcesUnloaded) {
    TerrainGrid grid;  // not loaded
    EXPECT_FALSE(grid.loaded());

    Real x[] = {50, 50};
    Real f[] = {0, 0};
    Real pe = compute_grid_terrain_forces(x, f, 1, grid, 1.0);
    EXPECT_NEAR(pe, 0.0, 1e-15);
    EXPECT_NEAR(f[0], 0.0, 1e-15);
    EXPECT_NEAR(f[1], 0.0, 1e-15);
}

// ─── Grid Terrain Potential ─────────────────────────────

TEST(TerrainGridTest, GridTerrainPotential) {
    TerrainGrid grid;
    grid.generate_synthetic(101, 101, 0, 0, 100, 100, "valley");

    // River valley (center) should be most negative (most fertile)
    Real v_center = grid_terrain_potential(50, 50, grid, 1.0);
    Real v_edge = grid_terrain_potential(0, 0, grid, 1.0);
    EXPECT_LT(v_center, v_edge);
    EXPECT_LT(v_center, 0.0);
}

// ─── ASCII File I/O ─────────────────────────────────────

TEST(TerrainGridTest, AsciiLoadSave) {
    namespace fs = std::filesystem;
    const std::string path = "/tmp/test_terrain.asc";

    // Write a small ASCII grid
    {
        std::ofstream out(path);
        out << "ncols 3\n"
            << "nrows 3\n"
            << "xllcorner 0\n"
            << "yllcorner 0\n"
            << "cellsize 1\n"
            << "NODATA_value -9999\n"
            << "10 20 30\n"   // row 2 (top = largest y)
            << "40 50 60\n"   // row 1
            << "70 80 90\n";  // row 0 (bottom = smallest y)
    }

    TerrainGrid grid;
    grid.load_ascii(path);

    EXPECT_EQ(grid.nrows(), 3);
    EXPECT_EQ(grid.ncols(), 3);
    EXPECT_NEAR(grid.h_min(), 10.0, 1e-10);
    EXPECT_NEAR(grid.h_max(), 90.0, 1e-10);

    // row 0 (bottom, y=0): 70 80 90
    EXPECT_NEAR(grid.at(0, 0), 70.0, 1e-10);
    EXPECT_NEAR(grid.at(0, 1), 80.0, 1e-10);
    EXPECT_NEAR(grid.at(0, 2), 90.0, 1e-10);

    // row 2 (top, y=2): 10 20 30
    EXPECT_NEAR(grid.at(2, 0), 10.0, 1e-10);
    EXPECT_NEAR(grid.at(2, 1), 20.0, 1e-10);
    EXPECT_NEAR(grid.at(2, 2), 30.0, 1e-10);

    // Bilinear at exact grid point (0, 0) should give at(0, 0) = 70
    EXPECT_NEAR(grid.elevation(0, 0), 70.0, 1e-10);
    // At (1, 1) → at(1, 1) = 50
    EXPECT_NEAR(grid.elevation(1, 1), 50.0, 1e-10);

    fs::remove(path);
}

// ─── Binary File I/O ────────────────────────────────────

TEST(TerrainGridTest, BinaryLoadSave) {
    namespace fs = std::filesystem;
    const std::string path = "/tmp/test_terrain.bin";

    // Write 3x3 binary
    {
        Real data[] = {70, 80, 90, 40, 50, 60, 10, 20, 30};
        std::ofstream out(path, std::ios::binary);
        out.write(reinterpret_cast<const char*>(data), sizeof(data));
    }

    TerrainGrid grid;
    grid.load_binary(path, 3, 3, 0, 0, 1.0);

    EXPECT_EQ(grid.nrows(), 3);
    EXPECT_NEAR(grid.at(0, 0), 70.0, 1e-10);
    EXPECT_NEAR(grid.at(2, 2), 30.0, 1e-10);

    fs::remove(path);
}
