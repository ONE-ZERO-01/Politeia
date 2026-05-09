#include "climate/climate_grid.hpp"
#include "force/terrain_loader.hpp"

#include <gtest/gtest.h>
#include <cmath>
#include <fstream>

using namespace politeia;

TEST(ClimateGridTest, ProceduralGeneration) {
    ClimateGrid cg;
    EXPECT_FALSE(cg.loaded());

    cg.generate_procedural(64, 128, -180, -90, 180, 90);
    EXPECT_TRUE(cg.loaded());
    EXPECT_EQ(cg.nrows(), 64);
    EXPECT_EQ(cg.ncols(), 128);
}

TEST(ClimateGridTest, EquatorWarmerThanPoles) {
    ClimateGrid cg;
    cg.generate_procedural(64, 128, -180, -90, 180, 90);

    auto equator = cg.cell_at(0.0, 0.0);
    auto arctic = cg.cell_at(0.0, 80.0);
    EXPECT_GT(equator.temperature, arctic.temperature);
}

TEST(ClimateGridTest, EquatorWetterThanDesert) {
    ClimateGrid cg;
    cg.generate_procedural(64, 128, -180, -90, 180, 90);

    auto equator = cg.cell_at(0.0, 5.0);
    auto desert = cg.cell_at(0.0, 30.0);
    EXPECT_GT(equator.precipitation, desert.precipitation);
}

TEST(ClimateGridTest, FactorsAtMildClimate) {
    ClimateGrid cg;
    cg.generate_procedural(64, 128, -180, -90, 180, 90);

    auto f = cg.factors_at(0.0, 20.0, 0.01, 0.5, 0.5);
    EXPECT_GT(f.production_factor, 0.0);
    EXPECT_GT(f.carrying_factor, 0.0);
    EXPECT_GE(f.friction_factor, 1.0);
    EXPECT_GE(f.plague_factor, 1.0);
}

TEST(ClimateGridTest, HarshClimateHighMortality) {
    ClimateGrid cg;
    cg.generate_procedural(64, 128, -180, -90, 180, 90);

    auto mild = cg.factors_at(0.0, 20.0, 0.1, 0.5, 0.5);
    auto harsh = cg.factors_at(0.0, 80.0, 0.1, 0.5, 0.5);
    EXPECT_GT(harsh.mortality_addition, mild.mortality_addition);
}

TEST(ClimateGridTest, ElevationLapseRate) {
    TerrainGrid tg;
    tg.generate_synthetic(64, 128, -180, -90, 180, 90, "ridge");

    ClimateGrid cg;
    cg.generate_procedural(64, 128, -180, -90, 180, 90, &tg);

    ClimateGrid cg_flat;
    cg_flat.generate_procedural(64, 128, -180, -90, 180, 90);

    auto with_elev = cg.cell_at(0.0, 0.0);
    auto without_elev = cg_flat.cell_at(0.0, 0.0);
    EXPECT_LE(with_elev.temperature, without_elev.temperature);
}

TEST(ClimateGridTest, UnloadedReturnsDefaults) {
    ClimateGrid cg;
    auto c = cg.cell_at(50.0, 50.0);
    EXPECT_NEAR(c.temperature, 15.0, 1e-10);
    EXPECT_NEAR(c.precipitation, 800.0, 1e-10);

    auto f = cg.factors_at(50.0, 50.0, 0.1, 0.5, 0.5);
    EXPECT_NEAR(f.production_factor, 1.0, 1e-10);
}

TEST(ClimateGridTest, StaticModeNoChange) {
    ClimateGrid cg;
    cg.generate_procedural(32, 64, -180, -90, 180, 90);

    auto before = cg.cell_at(0.0, 0.0);
    cg.advance(1000, ClimateTimeMode::Static, 0.0, 0.0, 100.0, 0.01);
    auto after = cg.cell_at(0.0, 0.0);

    EXPECT_NEAR(before.temperature, after.temperature, 1e-10);
}

TEST(ClimateGridTest, DriftModeChangesTemp) {
    ClimateGrid cg;
    cg.generate_procedural(32, 64, -180, -90, 180, 90);

    auto before = cg.cell_at(0.0, 0.0);
    cg.advance(10000, ClimateTimeMode::Drift, 0.01, 0.0, 100.0, 0.01);
    auto after = cg.cell_at(0.0, 0.0);

    EXPECT_NE(before.temperature, after.temperature);
}

TEST(ClimateGridTest, SeasonalModeOscillates) {
    ClimateGrid cg;
    cg.generate_procedural(32, 64, -180, -90, 180, 90);

    cg.advance(0, ClimateTimeMode::Seasonal, 0.0, 5.0, 100.0, 0.01);
    auto t0 = cg.cell_at(0.0, 0.0).temperature;

    cg.advance(2500, ClimateTimeMode::Seasonal, 0.0, 5.0, 100.0, 0.01);
    auto t_half = cg.cell_at(0.0, 0.0).temperature;

    EXPECT_NE(t0, t_half);
}

TEST(ClimateGridTest, DriftSchedule) {
    ClimateGrid cg;
    cg.generate_procedural(32, 64, -180, -90, 180, 90);
    cg.set_drift_schedule("0:-2.0, 5000:0.0, 10000:3.0");

    cg.advance(100, ClimateTimeMode::Drift, 0.0, 0.0, 100.0, 0.01);
    auto t_cold = cg.cell_at(0.0, 0.0).temperature;

    cg.advance(11000, ClimateTimeMode::Drift, 0.0, 0.0, 100.0, 0.01);
    auto t_warm = cg.cell_at(0.0, 0.0).temperature;

    EXPECT_GT(t_warm, t_cold);
}

TEST(ClimateGridTest, AsciiLoadSave) {
    const std::string path = "test_climate_tmp.asc";

    {
        std::ofstream f(path);
        // Temperature band header
        f << "ncols 4\n"
          << "nrows 3\n"
          << "xllcorner 0\n"
          << "yllcorner 0\n"
          << "cellsize 10\n"
          << "NODATA_value -9999\n";
        // Temperature data (north to south, each row on its own line)
        f << "24 24 24 24\n";
        f << "22 22 22 22\n";
        f << "20 20 20 20\n";
        // Precipitation band header
        f << "ncols 4\n"
          << "nrows 3\n"
          << "xllcorner 0\n"
          << "yllcorner 0\n"
          << "cellsize 10\n"
          << "NODATA_value -9999\n";
        // Precipitation data (north to south)
        f << "600 600 600 600\n";
        f << "700 700 700 700\n";
        f << "800 800 800 800\n";
    }

    ClimateGrid cg;
    cg.load_ascii(path);
    EXPECT_TRUE(cg.loaded());
    EXPECT_EQ(cg.nrows(), 3);
    EXPECT_EQ(cg.ncols(), 4);

    auto c = cg.cell_at(15.0, 10.0);
    EXPECT_GT(c.temperature, 0.0);
    EXPECT_GT(c.precipitation, 0.0);

    std::remove(path.c_str());
}
