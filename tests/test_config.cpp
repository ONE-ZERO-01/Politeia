#include <gtest/gtest.h>
#include "core/config.hpp"

#include <fstream>
#include <filesystem>

using namespace politeia;

TEST(ConfigTest, DefaultValues) {
    SimConfig cfg = default_config();
    EXPECT_DOUBLE_EQ(cfg.dt, constants::DEFAULT_DT);
    EXPECT_DOUBLE_EQ(cfg.temperature, constants::DEFAULT_TEMPERATURE);
    EXPECT_EQ(cfg.initial_particles, 1000u);
    EXPECT_EQ(cfg.culture_dim, constants::DEFAULT_CULTURE_DIM);
}

TEST(ConfigTest, LoadFromFile) {
    const std::string test_file = "test_config_tmp.cfg";

    {
        std::ofstream out(test_file);
        out << "# Test config\n"
            << "dt = 0.005\n"
            << "initial_particles = 500\n"
            << "temperature = 2.5\n"
            << "culture_dim = 4\n"
            << "output_dir = test_output\n";
    }

    SimConfig cfg = load_config(test_file);

    EXPECT_DOUBLE_EQ(cfg.dt, 0.005);
    EXPECT_EQ(cfg.initial_particles, 500u);
    EXPECT_DOUBLE_EQ(cfg.temperature, 2.5);
    EXPECT_EQ(cfg.culture_dim, 4);
    EXPECT_EQ(cfg.output_dir, "test_output");

    // Unchanged defaults
    EXPECT_DOUBLE_EQ(cfg.friction, constants::DEFAULT_FRICTION);
    EXPECT_DOUBLE_EQ(cfg.social_distance, constants::DEFAULT_SOCIAL_DISTANCE);

    std::filesystem::remove(test_file);
}

TEST(ConfigTest, MissingFileThrows) {
    EXPECT_THROW(load_config("nonexistent.cfg"), std::runtime_error);
}
