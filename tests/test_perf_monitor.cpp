#include "analysis/perf_monitor.hpp"

#include <gtest/gtest.h>
#include <thread>
#include <chrono>

using namespace politeia;

TEST(PerfMonitorTest, PhaseTiming) {
    PerfMonitor pm;
    pm.reset();

    pm.start(PerfMonitor::Dynamics);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    pm.stop(PerfMonitor::Dynamics);

    EXPECT_GT(pm.step_time(PerfMonitor::Dynamics), 0.005);
    EXPECT_LT(pm.step_time(PerfMonitor::Dynamics), 0.1);

    EXPECT_NEAR(pm.step_time(PerfMonitor::Exchange), 0.0, 1e-12);
}

TEST(PerfMonitorTest, StepTotal) {
    PerfMonitor pm;
    pm.reset();

    pm.start(PerfMonitor::Dynamics);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    pm.stop(PerfMonitor::Dynamics);

    pm.start(PerfMonitor::Exchange);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    pm.stop(PerfMonitor::Exchange);

    double total = pm.step_total();
    double sum = pm.step_time(PerfMonitor::Dynamics) + pm.step_time(PerfMonitor::Exchange);
    EXPECT_NEAR(total, sum, 1e-12);
    EXPECT_GT(total, 0.008);
}

TEST(PerfMonitorTest, Accumulation) {
    PerfMonitor pm;
    pm.reset();

    for (int i = 0; i < 3; ++i) {
        pm.start(PerfMonitor::Dynamics);
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
        pm.stop(PerfMonitor::Dynamics);
        pm.step_done();
    }

    EXPECT_GT(pm.accumulated(PerfMonitor::Dynamics), 0.004);
    EXPECT_GE(pm.accumulated(PerfMonitor::Dynamics),
              pm.step_time(PerfMonitor::Dynamics));
}

TEST(PerfMonitorTest, Reset) {
    PerfMonitor pm;
    pm.start(PerfMonitor::IO);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    pm.stop(PerfMonitor::IO);

    pm.reset();
    EXPECT_NEAR(pm.accumulated(PerfMonitor::IO), 0.0, 1e-12);
    EXPECT_NEAR(pm.step_time(PerfMonitor::IO), 0.0, 1e-12);
}

TEST(PerfMonitorTest, LoadReportSerial) {
    PerfMonitor pm;
    pm.reset();

    pm.start(PerfMonitor::Dynamics);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    pm.stop(PerfMonitor::Dynamics);

    auto report = pm.compute_load_report(1000, 0.5);

    // Serial: max = min = avg = local
    EXPECT_NEAR(report.global_max, report.local_total, 1e-12);
    EXPECT_NEAR(report.global_min, report.local_total, 1e-12);
    EXPECT_NEAR(report.global_avg, report.local_total, 1e-12);
    EXPECT_NEAR(report.efficiency, 1.0, 1e-12);
    EXPECT_FALSE(report.needs_rebalance);
    EXPECT_EQ(report.global_max_particles, 1000u);
    EXPECT_EQ(report.global_min_particles, 1000u);
}

TEST(PerfMonitorTest, LoadReportRebalanceTrigger) {
    PerfMonitor pm;
    pm.reset();

    // efficiency = 1.0 in serial, should NOT trigger at 0.5
    pm.start(PerfMonitor::Dynamics);
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
    pm.stop(PerfMonitor::Dynamics);

    auto report = pm.compute_load_report(100, 0.5);
    EXPECT_FALSE(report.needs_rebalance);
}

TEST(PerfMonitorTest, FormatReport) {
    PerfMonitor pm;
    pm.reset();

    pm.start(PerfMonitor::Dynamics);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    pm.stop(PerfMonitor::Dynamics);

    auto report = pm.compute_load_report(500);
    std::string s = pm.format_report(report);

    EXPECT_FALSE(s.empty());
    EXPECT_NE(s.find("eff="), std::string::npos);
    EXPECT_NE(s.find("max="), std::string::npos);
}

TEST(PerfMonitorTest, FormatBreakdown) {
    PerfMonitor pm;
    pm.reset();

    pm.start(PerfMonitor::Dynamics);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    pm.stop(PerfMonitor::Dynamics);

    pm.start(PerfMonitor::IO);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    pm.stop(PerfMonitor::IO);

    std::string s = pm.format_breakdown();
    EXPECT_NE(s.find("dynamics="), std::string::npos);
    EXPECT_NE(s.find("io="), std::string::npos);
}

TEST(PerfMonitorTest, PhaseNames) {
    EXPECT_EQ(std::string(PerfMonitor::phase_names[PerfMonitor::Dynamics]), "dynamics");
    EXPECT_EQ(std::string(PerfMonitor::phase_names[PerfMonitor::IO]), "io");
    EXPECT_EQ(std::string(PerfMonitor::phase_names[PerfMonitor::Migration]), "migration");
}
