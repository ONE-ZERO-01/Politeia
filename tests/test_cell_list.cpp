#include <gtest/gtest.h>
#include "domain/cell_list.hpp"

using namespace politeia;

TEST(CellListTest, InitDimensions) {
    CellList cl;
    cl.init(0.0, 10.0, 0.0, 10.0, 2.5);
    EXPECT_GE(cl.nx(), 4);
    EXPECT_GE(cl.ny(), 4);
}

TEST(CellListTest, FindsAllPairsWithinCutoff) {
    CellList cl;
    cl.init(0.0, 10.0, 0.0, 10.0, 3.0);

    // Place 3 particles: 0 and 1 are close, 2 is far
    Real x[] = {1.0, 1.0,   2.0, 1.0,   8.0, 8.0};
    Index count = 3;

    cl.build(x, count);

    int pair_count = 0;
    bool found_01 = false;

    Real cutoff_sq = 3.0 * 3.0;
    cl.for_each_pair(x, count, cutoff_sq, [&](Index i, Index j, Real dx, Real dy, Real r2) {
        pair_count++;
        if ((i == 0 && j == 1) || (i == 1 && j == 0)) found_01 = true;
    });

    EXPECT_TRUE(found_01);
    // Particles 0-2 and 1-2 are far apart (~9.9), should not be found
    EXPECT_EQ(pair_count, 1);
}

TEST(CellListTest, PairSymmetry) {
    CellList cl;
    cl.init(0.0, 20.0, 0.0, 20.0, 5.0);

    Real x[] = {3.0, 3.0,   5.0, 3.0,   3.0, 5.0,   15.0, 15.0};
    Index count = 4;
    cl.build(x, count);

    // All pairs within cutoff=5 should have i < j
    Real cutoff_sq = 5.0 * 5.0;
    cl.for_each_pair(x, count, cutoff_sq, [](Index i, Index j, Real, Real, Real) {
        EXPECT_LT(i, j);
    });
}
