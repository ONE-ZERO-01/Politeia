#include "io/checkpoint.hpp"
#include "core/particle_data.hpp"
#include "core/config.hpp"

#include <gtest/gtest.h>
#include <cmath>
#include <filesystem>

using namespace politeia;

class CheckpointTest : public ::testing::Test {
protected:
    void SetUp() override {
        ckpt_path = make_path();
        particles = std::make_unique<ParticleData>(64, culture_dim);
        cfg = default_config();
        cfg.culture_dim = culture_dim;

        for (int i = 0; i < 10; ++i) {
            Vec2 pos = {10.0 * i, 20.0 + i};
            Vec2 mom = {0.1 * i, -0.1 * i};
            Real w = 5.0 + i;
            Real eps = 1.0 + 0.1 * i;
            Real age = 20.0 + i;
            Index idx = particles->add_particle(pos, mom, w, eps, age);
            particles->sex(idx) = static_cast<uint8_t>(i % 2);
            for (int d = 0; d < culture_dim; ++d) {
                particles->culture(idx, d) = 0.1 * (i + d);
            }
        }
    }

    void TearDown() override {
        if (std::filesystem::exists(ckpt_path))
            std::filesystem::remove(ckpt_path);
    }

    static constexpr int culture_dim = 4;
    std::string ckpt_path;
    std::unique_ptr<ParticleData> particles;
    SimConfig cfg;

    static int next_id() { static int id = 0; return id++; }
    std::string make_path() {
        return "test_ckpt_" + std::to_string(next_id()) + "_" +
               std::to_string(::testing::UnitTest::GetInstance()->random_seed()) + ".bin";
    }
};

TEST_F(CheckpointTest, HeaderSize) {
    EXPECT_EQ(sizeof(CheckpointHeader), CHECKPOINT_HEADER_BYTES);
}

TEST_F(CheckpointTest, RecordSize) {
    uint32_t rs = checkpoint_record_size(4, 0);
    EXPECT_EQ(rs, (12 + 4 + 0) * sizeof(double));
}

TEST_F(CheckpointTest, PackUnpackRoundTrip) {
    std::vector<double> buf(64);

    int written = checkpoint_pack_particle(*particles, 3, buf.data(), culture_dim, 0);
    EXPECT_GT(written, 0);

    ParticleData restored(16, culture_dim);
    checkpoint_unpack_particle(restored, buf.data(), culture_dim, 0);

    EXPECT_EQ(restored.count(), 1u);
    auto rpos = restored.position(0);
    auto opos = particles->position(3);
    EXPECT_NEAR(rpos[0], opos[0], 1e-12);
    EXPECT_NEAR(rpos[1], opos[1], 1e-12);
    EXPECT_NEAR(restored.wealth(0), particles->wealth(3), 1e-12);
    EXPECT_NEAR(restored.epsilon(0), particles->epsilon(3), 1e-12);
    EXPECT_NEAR(restored.age(0), particles->age(3), 1e-12);
    for (int d = 0; d < culture_dim; ++d) {
        EXPECT_NEAR(restored.culture(0, d), particles->culture(3, d), 1e-12);
    }
}

TEST_F(CheckpointTest, WriteAndReadBack) {
    uint64_t step = 42;
    write_checkpoint(ckpt_path, *particles, cfg, "", step, 0, 1);

    EXPECT_TRUE(std::filesystem::exists(ckpt_path));
    EXPECT_GT(std::filesystem::file_size(ckpt_path), CHECKPOINT_HEADER_BYTES);

    auto header = read_checkpoint_header(ckpt_path);
    EXPECT_EQ(header.magic, CHECKPOINT_MAGIC);
    EXPECT_EQ(header.version, CHECKPOINT_VERSION);
    EXPECT_EQ(header.particle_count, 10u);
    EXPECT_EQ(header.step, step);
    EXPECT_EQ(header.culture_dim, static_cast<uint32_t>(culture_dim));

    ParticleData loaded(64, culture_dim);
    uint64_t loaded_step;
    double loaded_time;
    read_checkpoint(ckpt_path, loaded, loaded_step, loaded_time, 0, 1);

    EXPECT_EQ(loaded_step, step);
    EXPECT_EQ(loaded.count(), particles->count());

    for (Index i = 0; i < loaded.count(); ++i) {
        auto lp = loaded.position(i);
        auto op = particles->position(i);
        EXPECT_NEAR(lp[0], op[0], 1e-10);
        EXPECT_NEAR(lp[1], op[1], 1e-10);
        EXPECT_NEAR(loaded.wealth(i), particles->wealth(i), 1e-10);
        EXPECT_NEAR(loaded.epsilon(i), particles->epsilon(i), 1e-10);
        EXPECT_NEAR(loaded.age(i), particles->age(i), 1e-10);
    }
}

TEST_F(CheckpointTest, HeaderReadStandalone) {
    write_checkpoint(ckpt_path, *particles, cfg, "", 100, 0, 1);

    auto header = read_checkpoint_header(ckpt_path);
    EXPECT_EQ(header.magic, CHECKPOINT_MAGIC);
    EXPECT_EQ(header.particle_count, 10u);
    EXPECT_EQ(header.step, 100u);
}

TEST_F(CheckpointTest, CulturePreserved) {
    write_checkpoint(ckpt_path, *particles, cfg, "", 1, 0, 1);

    ParticleData loaded(64, culture_dim);
    uint64_t step;
    double time;
    read_checkpoint(ckpt_path, loaded, step, time, 0, 1);

    for (Index i = 0; i < loaded.count(); ++i) {
        for (int d = 0; d < culture_dim; ++d) {
            EXPECT_NEAR(loaded.culture(i, d), particles->culture(i, d), 1e-10);
        }
    }
}
