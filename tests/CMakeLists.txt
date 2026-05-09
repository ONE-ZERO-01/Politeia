include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

include(GoogleTest)

# --- Test: ParticleData ---
add_executable(test_particle_data test_particle_data.cpp)
target_link_libraries(test_particle_data PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_particle_data)

# --- Test: Config ---
add_executable(test_config test_config.cpp)
target_link_libraries(test_config PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_config)

# --- Test: CellList ---
add_executable(test_cell_list test_cell_list.cpp)
target_link_libraries(test_cell_list PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_cell_list)

# --- Test: Social Force ---
add_executable(test_social_force test_social_force.cpp)
target_link_libraries(test_social_force PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_social_force)

# --- Test: Langevin Integrator ---
add_executable(test_langevin_integrator test_langevin_integrator.cpp)
target_link_libraries(test_langevin_integrator PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_langevin_integrator)

# --- Test: Resource Exchange ---
add_executable(test_resource_exchange test_resource_exchange.cpp)
target_link_libraries(test_resource_exchange PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_resource_exchange)

# --- Test: Order Parameters ---
add_executable(test_order_params test_order_params.cpp)
target_link_libraries(test_order_params PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_order_params)

# --- Test: Network Analysis ---
add_executable(test_network test_network.cpp)
target_link_libraries(test_network PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_network)

# --- Test: Tech Spread ---
add_executable(test_tech_spread test_tech_spread.cpp)
target_link_libraries(test_tech_spread PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_tech_spread)

# --- Test: Culture Dynamics ---
add_executable(test_culture test_culture.cpp)
target_link_libraries(test_culture PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_culture)

# --- Test: Population (Reproduction + Mortality) ---
add_executable(test_population test_population.cpp)
target_link_libraries(test_population PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_population)

# --- Test: Morton + SFC ---
add_executable(test_morton test_morton.cpp)
target_link_libraries(test_morton PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_morton)

# --- Test: Plague ---
add_executable(test_plague test_plague.cpp)
target_link_libraries(test_plague PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_plague)

# --- Test: Perf Monitor ---
add_executable(test_perf_monitor test_perf_monitor.cpp)
target_link_libraries(test_perf_monitor PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_perf_monitor)

# --- Test: Terrain Loader ---
add_executable(test_terrain_loader test_terrain_loader.cpp)
target_link_libraries(test_terrain_loader PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_terrain_loader)

# --- Test: Loyalty ---
add_executable(test_loyalty test_loyalty.cpp)
target_link_libraries(test_loyalty PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_loyalty)

# --- Test: Polity ---
add_executable(test_polity test_polity.cpp)
target_link_libraries(test_polity PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_polity)

# --- Test: Carrying Capacity ---
add_executable(test_carrying_capacity test_carrying_capacity.cpp)
target_link_libraries(test_carrying_capacity PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_carrying_capacity)

# --- Test: Climate Grid ---
add_executable(test_climate_grid test_climate_grid.cpp)
target_link_libraries(test_climate_grid PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_climate_grid)

# --- Test: River Field ---
add_executable(test_river_field test_river_field.cpp)
target_link_libraries(test_river_field PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_river_field)

# --- Test: Checkpoint ---
add_executable(test_checkpoint test_checkpoint.cpp)
target_link_libraries(test_checkpoint PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_checkpoint)

# --- Test: IC Loader ---
add_executable(test_ic_loader test_ic_loader.cpp)
target_link_libraries(test_ic_loader PRIVATE politeia_core GTest::gtest_main)
gtest_discover_tests(test_ic_loader)
