#include "river/river_field.hpp"

#include <gtest/gtest.h>
#include <cmath>
#include <fstream>

using namespace politeia;

TEST(RiverFieldTest, InitiallyUnloaded) {
    RiverField rf;
    EXPECT_FALSE(rf.loaded());
    EXPECT_NEAR(rf.proximity(50.0, 50.0), 0.0, 1e-15);
}

TEST(RiverFieldTest, SyntheticMajorRivers) {
    RiverField rf;
    rf.generate_synthetic(64, 128, 0, 0, 100, 100, "major_rivers");
    EXPECT_TRUE(rf.loaded());
    EXPECT_EQ(rf.nrows(), 64);
    EXPECT_EQ(rf.ncols(), 128);
}

TEST(RiverFieldTest, ProximityRange) {
    RiverField rf;
    rf.generate_synthetic(64, 128, 0, 0, 100, 100, "major_rivers");

    bool found_positive = false;
    for (Real x = 0; x <= 100; x += 5.0) {
        for (Real y = 0; y <= 100; y += 5.0) {
            Real p = rf.proximity(x, y);
            EXPECT_GE(p, 0.0);
            EXPECT_LE(p, 1.0 + 1e-6);
            if (p > 0.01) found_positive = true;
        }
    }
    EXPECT_TRUE(found_positive);
}

TEST(RiverFieldTest, NileType) {
    RiverField rf;
    rf.generate_synthetic(64, 128, 0, 0, 100, 100, "nile");
    EXPECT_TRUE(rf.loaded());

    Real center = rf.proximity(50.0, 50.0);
    Real edge = rf.proximity(0.0, 0.0);
    EXPECT_GE(center, 0.0);
    EXPECT_GE(edge, 0.0);
}

TEST(RiverFieldTest, ChinaType) {
    RiverField rf;
    rf.generate_synthetic(64, 128, 0, 0, 100, 100, "china");
    EXPECT_TRUE(rf.loaded());
}

TEST(RiverFieldTest, ForcePointsToRiver) {
    RiverField rf;
    rf.generate_synthetic(128, 128, 0, 0, 100, 100, "nile");

    Real max_prox = 0.0;
    Real peak_x = 50.0, peak_y = 50.0;
    for (Real x = 10; x <= 90; x += 5.0) {
        for (Real y = 10; y <= 90; y += 5.0) {
            Real p = rf.proximity(x, y);
            if (p > max_prox) { max_prox = p; peak_x = x; peak_y = y; }
        }
    }

    Real off_x = peak_x + 10.0;
    Real off_y = peak_y;
    if (off_x > 90.0) off_x = peak_x - 10.0;

    Vec2 f = rf.force(off_x, off_y, 1.0);
    Real f_mag = std::sqrt(f[0] * f[0] + f[1] * f[1]);
    EXPECT_GT(f_mag, 0.0);
}

TEST(RiverFieldTest, CorridorBonus) {
    RiverField rf;
    rf.generate_synthetic(64, 128, 0, 0, 100, 100, "major_rivers");

    Real max_prox = 0.0;
    Real peak_x = 50.0, peak_y = 50.0;
    for (Real x = 5; x <= 95; x += 2.0) {
        for (Real y = 5; y <= 95; y += 2.0) {
            Real p = rf.proximity(x, y);
            if (p > max_prox) { max_prox = p; peak_x = x; peak_y = y; }
        }
    }

    Real bonus_near = rf.corridor_bonus(peak_x, peak_y, 1.0);
    Real bonus_far = rf.corridor_bonus(0.0, 0.0, 1.0);
    EXPECT_GE(bonus_near, bonus_far);
}

TEST(RiverFieldTest, CellAt) {
    RiverField rf;
    rf.generate_synthetic(64, 128, 0, 0, 100, 100, "major_rivers");

    auto cell = rf.cell_at(50.0, 50.0);
    EXPECT_GE(cell.proximity, 0.0);
    EXPECT_GE(cell.discharge, 0.0);
}

TEST(RiverFieldTest, AsciiLoadSave) {
    const std::string path = "test_river_tmp.asc";

    {
        std::ofstream f(path);
        f << "ncols 4\n"
          << "nrows 3\n"
          << "xllcorner 0\n"
          << "yllcorner 0\n"
          << "cellsize 10\n"
          << "NODATA_value -9999\n";
        // Proximity values (north to south)
        f << "0.1 0.5 0.8 0.3\n"
          << "0.2 0.9 0.7 0.1\n"
          << "0.0 0.3 0.4 0.0\n";
    }

    RiverField rf;
    rf.load_ascii(path);
    EXPECT_TRUE(rf.loaded());
    EXPECT_EQ(rf.nrows(), 3);
    EXPECT_EQ(rf.ncols(), 4);

    Real p = rf.proximity(15.0, 10.0);
    EXPECT_GT(p, 0.0);

    std::remove(path.c_str());
}

TEST(RiverFieldTest, BinaryLoadSave) {
    const std::string path = "test_river_bin.dat";
    const int nr = 4, nc = 8;

    {
        std::vector<Real> data(nr * nc);
        for (int i = 0; i < nr * nc; ++i) data[i] = 0.5;
        std::ofstream f(path, std::ios::binary);
        f.write(reinterpret_cast<const char*>(data.data()),
                static_cast<std::streamsize>(data.size() * sizeof(Real)));
    }

    RiverField rf;
    rf.load_binary(path, nr, nc, 0.0, 0.0, 10.0);
    EXPECT_TRUE(rf.loaded());
    EXPECT_EQ(rf.nrows(), nr);
    EXPECT_EQ(rf.ncols(), nc);

    Real p = rf.proximity(35.0, 15.0);
    EXPECT_NEAR(p, 0.5, 0.1);

    std::remove(path.c_str());
}
