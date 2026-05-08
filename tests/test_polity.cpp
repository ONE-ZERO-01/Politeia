#include "analysis/polity.hpp"
#include "core/particle_data.hpp"

#include <gtest/gtest.h>
#include <algorithm>

using namespace politeia;

class PolityTest : public ::testing::Test {
protected:
    void SetUp() override {
        particles = std::make_unique<ParticleData>(100, 2);
    }

    Id gid(Index i) const { return particles->global_id(i); }

    std::unique_ptr<ParticleData> particles;
};

TEST_F(PolityTest, AllIndependent) {
    for (int i = 0; i < 10; ++i) {
        Vec2 pos = {10.0 * i, 10.0};
        particles->add_particle(pos, {0, 0}, 10.0, 1.0, 25.0);
    }

    auto polities = detect_polities(*particles);
    EXPECT_EQ(polities.size(), 10u);

    for (auto& p : polities) {
        EXPECT_EQ(p.population, 1u);
        EXPECT_EQ(p.depth, 0u);
        EXPECT_EQ(p.type, PolityType::Band);
    }
}

TEST_F(PolityTest, SingleHierarchy) {
    // Leader (0) with 3 subordinates
    for (int i = 0; i < 4; ++i) {
        Vec2 pos = {10.0 + i, 10.0};
        particles->add_particle(pos, {0, 0}, 10.0 * (4 - i), 1.0, 25.0);
    }

    particles->superior(1) = gid(0);  particles->loyalty(1) = 0.8;
    particles->superior(2) = gid(0);  particles->loyalty(2) = 0.7;
    particles->superior(3) = gid(0);  particles->loyalty(3) = 0.6;

    auto polities = detect_polities(*particles);

    // All 4 should be in one polity
    ASSERT_EQ(polities.size(), 1u);
    EXPECT_EQ(polities[0].population, 4u);
    EXPECT_EQ(polities[0].root_gid, gid(0));
    EXPECT_EQ(polities[0].depth, 1u);
    EXPECT_GT(polities[0].mean_loyalty, 0.0);
}

TEST_F(PolityTest, TwoPolities) {
    for (int i = 0; i < 6; ++i) {
        Vec2 pos = {10.0 + i * 5, 10.0};
        particles->add_particle(pos, {0, 0}, 10.0, 1.0, 25.0);
    }

    // Polity 1: 0 → {1, 2}
    particles->superior(1) = gid(0);  particles->loyalty(1) = 0.8;
    particles->superior(2) = gid(0);  particles->loyalty(2) = 0.7;

    // Polity 2: 3 → {4, 5}
    particles->superior(4) = gid(3);  particles->loyalty(4) = 0.9;
    particles->superior(5) = gid(3);  particles->loyalty(5) = 0.6;

    auto polities = detect_polities(*particles);
    ASSERT_EQ(polities.size(), 2u);

    EXPECT_EQ(polities[0].population, 3u);
    EXPECT_EQ(polities[1].population, 3u);
}

TEST_F(PolityTest, DeepChain) {
    // Chain: 4 → 3 → 2 → 1 → 0 (root)
    for (int i = 0; i < 5; ++i) {
        Vec2 pos = {10.0 + i, 10.0};
        particles->add_particle(pos, {0, 0}, 10.0, 1.0, 25.0);
    }

    particles->superior(1) = gid(0);  particles->loyalty(1) = 0.8;
    particles->superior(2) = gid(1);  particles->loyalty(2) = 0.7;
    particles->superior(3) = gid(2);  particles->loyalty(3) = 0.6;
    particles->superior(4) = gid(3);  particles->loyalty(4) = 0.5;

    auto polities = detect_polities(*particles);
    ASSERT_EQ(polities.size(), 1u);
    EXPECT_EQ(polities[0].population, 5u);
    EXPECT_EQ(polities[0].depth, 4u);
}

TEST_F(PolityTest, Classification) {
    EXPECT_EQ(classify_polity(1, 0),    PolityType::Band);
    EXPECT_EQ(classify_polity(30, 1),   PolityType::Band);
    EXPECT_EQ(classify_polity(50, 1),   PolityType::Tribe);
    EXPECT_EQ(classify_polity(200, 2),  PolityType::Tribe);
    EXPECT_EQ(classify_polity(300, 2),  PolityType::Chiefdom);
    EXPECT_EQ(classify_polity(800, 3),  PolityType::Chiefdom);
    EXPECT_EQ(classify_polity(1000, 3), PolityType::State);
    EXPECT_EQ(classify_polity(3000, 5), PolityType::State);
    EXPECT_EQ(classify_polity(5000, 5), PolityType::Empire);
    EXPECT_EQ(classify_polity(50000, 8),PolityType::Empire);
}

TEST_F(PolityTest, Summary) {
    for (int i = 0; i < 10; ++i) {
        Vec2 pos = {10.0 * i, 10.0};
        particles->add_particle(pos, {0, 0}, 10.0, 1.0, 25.0);
    }

    // One polity of 5 + 5 singletons
    for (int i = 1; i < 5; ++i) {
        particles->superior(i) = gid(0);
        particles->loyalty(i) = 0.5;
    }

    auto polities = detect_polities(*particles);
    auto summary = summarize_polities(polities, 1.0);

    EXPECT_EQ(summary.n_polities, 6u);  // 1 polity + 5 singletons
    EXPECT_EQ(summary.n_multi, 1u);
    EXPECT_EQ(summary.largest_pop, 5u);
    EXPECT_GT(summary.hhi, 0.0);
}

TEST_F(PolityTest, EventDetection) {
    for (int i = 0; i < 6; ++i) {
        Vec2 pos = {10.0 * i, 10.0};
        particles->add_particle(pos, {0, 0}, 10.0, 1.0, 25.0);
    }

    // Step 1: no polities
    std::vector<PolityInfo> prev;

    // Step 2: form a polity (0 → {1, 2})
    particles->superior(1) = gid(0);  particles->loyalty(1) = 0.8;
    particles->superior(2) = gid(0);  particles->loyalty(2) = 0.7;

    auto curr = detect_polities(*particles);
    auto events = detect_polity_events(prev, curr, 1.0);

    bool found_formation = false;
    for (auto& ev : events) {
        if (ev.type == PolityEventType::Formation) found_formation = true;
    }
    EXPECT_TRUE(found_formation);

    // Step 3: polity collapses
    particles->superior(1) = -1;
    particles->superior(2) = -1;

    auto next = detect_polities(*particles);
    auto events2 = detect_polity_events(curr, next, 2.0);

    bool found_collapse = false;
    for (auto& ev : events2) {
        if (ev.type == PolityEventType::Collapse) found_collapse = true;
    }
    EXPECT_TRUE(found_collapse);
}

TEST_F(PolityTest, Centroid) {
    // 3 particles at known positions
    (void)particles->add_particle({10.0, 20.0}, {0, 0}, 10.0, 1.0, 25.0);
    (void)particles->add_particle({20.0, 20.0}, {0, 0}, 10.0, 1.0, 25.0);
    (void)particles->add_particle({15.0, 30.0}, {0, 0}, 10.0, 1.0, 25.0);

    particles->superior(1) = gid(0);  particles->loyalty(1) = 0.8;
    particles->superior(2) = gid(0);  particles->loyalty(2) = 0.7;

    auto polities = detect_polities(*particles);
    ASSERT_EQ(polities.size(), 1u);

    EXPECT_NEAR(polities[0].centroid[0], 15.0, 1e-10);
    EXPECT_NEAR(polities[0].centroid[1], 23.333333, 0.001);
}

TEST_F(PolityTest, TypeNames) {
    EXPECT_STREQ(polity_type_name(PolityType::Band), "band");
    EXPECT_STREQ(polity_type_name(PolityType::Tribe), "tribe");
    EXPECT_STREQ(polity_type_name(PolityType::Chiefdom), "chiefdom");
    EXPECT_STREQ(polity_type_name(PolityType::State), "state");
    EXPECT_STREQ(polity_type_name(PolityType::Empire), "empire");
}
