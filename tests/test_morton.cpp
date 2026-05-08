#include <gtest/gtest.h>
#include "domain/morton.hpp"
#include "domain/sfc_decomposition.hpp"

using namespace politeia;

TEST(MortonTest, EncodeDecodeRoundTrip) {
    for (std::uint32_t x = 0; x < 100; ++x) {
        for (std::uint32_t y = 0; y < 100; ++y) {
            MortonKey key = encode_morton_2d(x, y);
            std::uint32_t dx, dy;
            decode_morton_2d(key, dx, dy);
            EXPECT_EQ(dx, x) << "x mismatch at (" << x << "," << y << ")";
            EXPECT_EQ(dy, y) << "y mismatch at (" << x << "," << y << ")";
        }
    }
}

TEST(MortonTest, OrderPreservation) {
    // (0,0) < (1,0) < (0,1) < (1,1) in Z-order
    EXPECT_LT(encode_morton_2d(0, 0), encode_morton_2d(1, 0));
    EXPECT_LT(encode_morton_2d(1, 0), encode_morton_2d(0, 1));
    EXPECT_LT(encode_morton_2d(0, 1), encode_morton_2d(1, 1));
}

TEST(MortonTest, PointToMortonRoundTrip) {
    Real xmin = 0.0, xmax = 100.0, ymin = 0.0, ymax = 100.0;
    int level = 10;

    Real x = 37.5, y = 62.1;
    MortonKey key = point_to_morton(x, y, xmin, xmax, ymin, ymax, level);

    Real rx, ry;
    morton_to_point(key, rx, ry, xmin, xmax, ymin, ymax, level);

    Real cell_size = (xmax - xmin) / (1 << level);
    EXPECT_NEAR(rx, x, cell_size);
    EXPECT_NEAR(ry, y, cell_size);
}

TEST(MortonTest, SpatialLocality) {
    // 空间上相邻的点应该有相近的 Morton key
    Real xmin = 0.0, xmax = 100.0, ymin = 0.0, ymax = 100.0;
    int level = 10;

    MortonKey k1 = point_to_morton(50.0, 50.0, xmin, xmax, ymin, ymax, level);
    MortonKey k2 = point_to_morton(50.1, 50.1, xmin, xmax, ymin, ymax, level);
    MortonKey k_far = point_to_morton(90.0, 10.0, xmin, xmax, ymin, ymax, level);

    // 相邻点的 key 差应小于远距离点的 key 差
    auto diff_near = (k1 > k2) ? k1 - k2 : k2 - k1;
    auto diff_far = (k1 > k_far) ? k1 - k_far : k_far - k1;
    EXPECT_LT(diff_near, diff_far);
}

TEST(SFCDecompositionTest, InitSplits) {
    SFCDecomposition sfc;
    sfc.init(0.0, 100.0, 0.0, 100.0, 10, 0, 4);

    EXPECT_EQ(sfc.rank(), 0);
    EXPECT_EQ(sfc.nprocs(), 4);
    EXPECT_EQ(sfc.level(), 10);
    EXPECT_TRUE(sfc.local_key_min() < sfc.local_key_max());
}

TEST(SFCDecompositionTest, ComputeKeys) {
    SFCDecomposition sfc;
    sfc.init(0.0, 100.0, 0.0, 100.0, 10, 0, 1);

    ParticleData pd(5);
    (void)pd.add_particle({10.0, 20.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({50.0, 50.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);
    (void)pd.add_particle({90.0, 80.0}, {0.0, 0.0}, 1.0, 1.0, 0.0);

    auto keys = sfc.compute_keys(pd);
    EXPECT_EQ(keys.size(), 3u);

    // 不同位置应有不同的 key
    EXPECT_NE(keys[0], keys[1]);
    EXPECT_NE(keys[1], keys[2]);
}

TEST(SFCDecompositionTest, LoadStatsSerial) {
    SFCDecomposition sfc;
    sfc.init(0.0, 100.0, 0.0, 100.0, 10, 0, 1);

    auto stats = sfc.compute_load_stats(1000);
    EXPECT_EQ(stats.local_count, 1000u);
    EXPECT_NEAR(stats.efficiency, 1.0, 1e-10);
}

TEST(SFCDecompositionTest, BoundaryClamp) {
    // 边界点不应产生越界 key
    MortonKey k1 = point_to_morton(0.0, 0.0, 0.0, 100.0, 0.0, 100.0, 10);
    MortonKey k2 = point_to_morton(100.0, 100.0, 0.0, 100.0, 0.0, 100.0, 10);
    EXPECT_LE(k1, k2);
    // 不应崩溃或产生无效 key
    MortonKey k3 = point_to_morton(-0.1, -0.1, 0.0, 100.0, 0.0, 100.0, 10);
    (void)k3;
}
