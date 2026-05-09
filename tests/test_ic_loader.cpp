#include "io/ic_loader.hpp"
#include "core/particle_data.hpp"
#include "core/config.hpp"

#include <gtest/gtest.h>
#include <fstream>
#include <random>
#include <cmath>

using namespace politeia;

class ICLoaderTest : public ::testing::Test {
protected:
    void TearDown() override {
        if (!csv_path.empty()) std::remove(csv_path.c_str());
    }

    std::string csv_path;
    SimConfig cfg = default_config();
    std::mt19937_64 rng{42};
};

TEST_F(ICLoaderTest, BasicXY) {
    csv_path = "test_ic_basic.csv";
    {
        std::ofstream f(csv_path);
        f << "x,y\n"
          << "10.0,20.0\n"
          << "30.0,40.0\n"
          << "50.0,60.0\n";
    }

    ParticleData particles(16, cfg.culture_dim);
    Index loaded = load_initial_conditions(csv_path, particles, cfg, rng, 0);

    EXPECT_EQ(loaded, 3u);
    EXPECT_EQ(particles.count(), 3u);
    auto p0 = particles.position(0);
    EXPECT_NEAR(p0[0], 10.0, 1e-10);
    EXPECT_NEAR(p0[1], 20.0, 1e-10);
    auto p2 = particles.position(2);
    EXPECT_NEAR(p2[0], 50.0, 1e-10);
}

TEST_F(ICLoaderTest, AllColumns) {
    csv_path = "test_ic_full.csv";
    {
        std::ofstream f(csv_path);
        f << "x,y,w,eps,age,sex,c0,c1\n"
          << "10.0,20.0,100.0,2.5,30.0,1,0.8,0.2\n"
          << "30.0,40.0,50.0,1.5,25.0,0,0.3,0.7\n";
    }

    cfg.culture_dim = 2;
    cfg.gender_enabled = true;
    ParticleData particles(16, 2);
    Index loaded = load_initial_conditions(csv_path, particles, cfg, rng, 0);

    EXPECT_EQ(loaded, 2u);
    EXPECT_NEAR(particles.wealth(0), 100.0, 1e-10);
    EXPECT_NEAR(particles.epsilon(0), 2.5, 1e-10);
    EXPECT_NEAR(particles.age(0), 30.0, 1e-10);
    EXPECT_EQ(particles.sex(0), 1);
    EXPECT_NEAR(particles.culture(0, 0), 0.8, 1e-10);
    EXPECT_NEAR(particles.culture(0, 1), 0.2, 1e-10);
}

TEST_F(ICLoaderTest, DefaultsForMissingColumns) {
    csv_path = "test_ic_partial.csv";
    {
        std::ofstream f(csv_path);
        f << "x,y,w\n"
          << "10.0,20.0,50.0\n";
    }

    ParticleData particles(16, cfg.culture_dim);
    Index loaded = load_initial_conditions(csv_path, particles, cfg, rng, 0);

    EXPECT_EQ(loaded, 1u);
    EXPECT_NEAR(particles.wealth(0), 50.0, 1e-10);
    EXPECT_GT(particles.age(0), 0.0);
}

TEST_F(ICLoaderTest, NonRank0GetsZero) {
    csv_path = "test_ic_rank.csv";
    {
        std::ofstream f(csv_path);
        f << "x,y\n"
          << "10.0,20.0\n";
    }

    ParticleData particles(16, cfg.culture_dim);
    Index loaded = load_initial_conditions(csv_path, particles, cfg, rng, 1);

    EXPECT_EQ(loaded, 0u);
    EXPECT_EQ(particles.count(), 0u);
}

TEST_F(ICLoaderTest, AdamEveFile) {
    const std::string adam_eve = "examples/adam_eve.csv";
    std::ifstream check(adam_eve);
    if (!check.good()) {
        GTEST_SKIP() << "adam_eve.csv not found";
    }

    cfg.culture_dim = 2;
    ParticleData particles(16, 2);
    Index loaded = load_initial_conditions(adam_eve, particles, cfg, rng, 0);

    EXPECT_EQ(loaded, 2u);
    EXPECT_EQ(particles.count(), 2u);

    bool has_male = false, has_female = false;
    for (Index i = 0; i < particles.count(); ++i) {
        if (particles.sex(i) == 1) has_male = true;
        if (particles.sex(i) == 0) has_female = true;
    }
    EXPECT_TRUE(has_male);
    EXPECT_TRUE(has_female);
}
