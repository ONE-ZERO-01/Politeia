#!/usr/bin/env python3
"""
Generate historically-motivated initial conditions for Politeia.

Calibrated against HYDE 3.3 dataset (Klein Goldewijk et al. 2023):
  - 10,000 BCE global population = 4,501,152
  - Regional fractions derived from HYDE 3.3 country-level baseline estimates
  - Geographic centers from archaeological site locations

References:
  [1] HYDE 3.3 (Klein Goldewijk et al. 2023): gridded population 10,000 BCE–2023 CE
      https://landuse.sites.uu.nl/datasets/
  [2] McEvedy & Jones (1978): Atlas of World Population History
  [3] Biraben (1980): regional prehistoric population estimates
  [4] Brilliant Maps / Our World In Data: HYDE 3.3 country-level aggregation
  [5] Goldewijk, K. et al. (2017): ESSD 9, 927–953 (HYDE 3.2 methodology)

Usage:
    python generate_genesis.py --n 100000 --era 10000bce --output genesis.csv
    python generate_genesis.py --n 500000 --era 10000bce --output genesis_500k.csv
    python generate_genesis.py --n 4501152 --era 10000bce --output examples/genesis_hyde_baseline.csv
    python generate_genesis.py --n 50000  --era 70000bce --output genesis_paleolithic.csv
"""

import argparse
import numpy as np
import csv


# ═══════════════════════════════════════════════════════════════════════════
# HYDE 3.3 Calibrated Regional Data — 10,000 BCE
#
# Global total: 4,501,152 (HYDE 3.3 baseline scenario)
#
# Continental breakdown (HYDE 3.3):
#   Asia:          1,183,783 (26.3%)
#   North America: 1,184,755 (26.3%)
#   South America: 1,097,849 (24.4%)
#   Europe:          481,591 (10.7%)
#   Oceania:         324,198 ( 7.2%)
#   Africa:          228,973 ( 5.1%)
#
# Sub-regional fractions below are derived from HYDE 3.3 country-level data,
# aggregated into archaeological culture areas. Each region's 'fraction'
# sums to the continent's HYDE share (within rounding).
# ═══════════════════════════════════════════════════════════════════════════

HYDE_GLOBAL_POPULATION_10000BCE = 4_501_152

REGIONS_10000BCE = {
    # ── North America (26.3%) ─────────────────────────────────────────
    # HYDE: Mexico 810K, USA 234K, Canada 17K, Guatemala 52K, others ~72K
    'mesoamerica': {
        'centers': [
            (-99.0, 19.5),    # Valley of Mexico
            (-90.0, 15.0),    # Guatemala highlands
            (-96.0, 17.0),    # Oaxaca
            (-89.0, 20.5),    # Yucatán
            (-87.0, 14.0),    # Honduras
        ],
        'sigma': 2.5,
        'fraction': 0.167,    # ~750K: Mexico 810K + Central America
        'eps': 1.0,
        'wealth': 7.0,
        'description': 'Mesoamerica — HYDE: 810K (Mexico) + Central America',
        'hyde_pop': 886_194,
    },
    'north_america_east': {
        'centers': [
            (-90.0, 35.0),    # Mississippi Valley
            (-80.0, 35.0),    # Appalachian region
            (-75.0, 40.0),    # Eastern seaboard
            (-85.0, 30.0),    # Gulf Coast
        ],
        'sigma': 5.0,
        'fraction': 0.040,    # ~180K
        'eps': 1.0,
        'wealth': 6.0,
        'description': 'Eastern North America — Clovis/post-Clovis traditions',
        'hyde_pop': 150_000,
    },
    'north_america_west': {
        'centers': [
            (-120.0, 38.0),   # California
            (-115.0, 35.0),   # Great Basin
            (-110.0, 33.0),   # Southwest
            (-122.0, 48.0),   # Pacific Northwest
        ],
        'sigma': 4.0,
        'fraction': 0.035,
        'eps': 1.0,
        'wealth': 6.0,
        'description': 'Western North America — HYDE: ~100K (US west + Canada)',
        'hyde_pop': 101_228,
    },
    'north_america_plains': {
        'centers': [
            (-100.0, 40.0),   # Great Plains
            (-104.0, 45.0),   # Northern Plains
            (-95.0, 33.0),    # Southern Plains
        ],
        'sigma': 5.0,
        'fraction': 0.021,
        'eps': 1.0,
        'wealth': 5.5,
        'description': 'Great Plains — Folsom/Plano bison hunters',
        'hyde_pop': 47_333,
    },

    # ── South America (24.4%) ─────────────────────────────────────────
    # HYDE: Brazil 415K, Peru 242K, Colombia 129K, Bolivia 105K, others ~207K
    'south_america_andes': {
        'centers': [
            (-76.0, -12.0),   # Peruvian coast/highlands
            (-65.0, -17.0),   # Bolivian altiplano
            (-78.0, -2.0),    # Ecuador highlands
            (-72.0, 5.0),     # Colombian highlands
        ],
        'sigma': 2.5,
        'fraction': 0.120,    # ~540K: Peru 242K + Bolivia 105K + Colombia 129K + Ecuador 70K
        'eps': 1.0,
        'wealth': 6.5,
        'description': 'Andean region — HYDE: Peru 242K + Bolivia 105K + Colombia 129K',
        'hyde_pop': 545_448,
    },
    'south_america_brazil': {
        'centers': [
            (-49.0, -15.0),   # Brazilian highlands (Lagoa Santa)
            (-43.0, -23.0),   # SE Brazil coast
            (-55.0, -10.0),   # Central Brazil
            (-60.0, -3.0),    # Amazon basin
        ],
        'sigma': 4.0,
        'fraction': 0.092,    # ~415K
        'eps': 1.0,
        'wealth': 5.5,
        'description': 'Brazil — HYDE: 415K, Lagoa Santa + Amazon foragers',
        'hyde_pop': 415_018,
    },
    'south_america_south': {
        'centers': [
            (-58.0, -34.0),   # Pampas
            (-70.0, -33.0),   # Chile
            (-57.0, -25.0),   # Paraguay
        ],
        'sigma': 3.5,
        'fraction': 0.032,    # ~144K
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'Southern South America — HYDE: Argentina 28K + Chile 35K + others',
        'hyde_pop': 137_383,
    },

    # ── Asia (26.3%) ──────────────────────────────────────────────────
    # HYDE: China 217K, Nepal 107K, Uzbekistan 102K, India 85K,
    #       Kazakhstan 108K, Iran 38K, Iraq 36K, Turkey 40K, etc.

    # Fertile Crescent / Levant
    'levant': {
        'centers': [
            (35.5, 32.0),     # Jordan Valley (Natufian core)
            (35.0, 33.5),     # Lebanon (HYDE: 21K)
            (36.5, 34.0),     # Syrian coast
            (36.0, 36.5),     # Aleppo region
        ],
        'sigma': 1.0,
        'fraction': 0.013,    # ~59K: Israel 12K + Syria 27K + Lebanon 21K
        'eps': 1.5,
        'wealth': 12.0,
        'description': 'Levant — Natufian, HYDE: Israel 12K + Syria 27K + Lebanon 21K',
        'hyde_pop': 59_375,
    },
    'mesopotamia': {
        'centers': [
            (44.0, 33.5),     # Tigris (future Baghdad)
            (46.0, 31.0),     # Lower Euphrates
            (43.0, 36.5),     # Upper Tigris
            (40.0, 37.0),     # Göbekli Tepe / SE Turkey
        ],
        'sigma': 1.5,
        'fraction': 0.016,    # ~72K: Iraq 36K + part of Turkey
        'eps': 1.3,
        'wealth': 11.0,
        'description': 'Mesopotamia — HYDE: Iraq 36K + SE Anatolia',
        'hyde_pop': 71_998,
    },
    'anatolia': {
        'centers': [
            (34.0, 38.0),     # Central Anatolia (future Çatalhöyük)
            (30.0, 40.0),     # Western Anatolia
            (36.0, 40.0),     # Eastern Anatolia
            (41.0, 40.0),     # NE Anatolia / Georgia (HYDE: 25K)
        ],
        'sigma': 2.0,
        'fraction': 0.014,    # ~65K: Turkey 40K + Georgia 25K
        'eps': 1.2,
        'wealth': 9.0,
        'description': 'Anatolia — HYDE: Turkey 40K + Georgia/Armenia 35K',
        'hyde_pop': 64_651,
    },

    # Iran and Central Asia
    'iran_plateau': {
        'centers': [
            (52.0, 33.0),     # Zagros foothills
            (58.0, 36.0),     # NE Iran
            (51.0, 36.0),     # Alborz
        ],
        'sigma': 2.5,
        'fraction': 0.008,    # ~38K
        'eps': 1.1,
        'wealth': 8.0,
        'description': 'Iranian Plateau — HYDE: Iran 38K',
        'hyde_pop': 38_101,
    },
    'central_asia': {
        'centers': [
            (68.0, 39.0),     # Fergana Valley
            (59.0, 42.0),     # Amu Darya
            (73.0, 42.0),     # Tian Shan foothills
            (69.0, 41.0),     # Uzbekistan (HYDE: 102K)
            (75.0, 41.0),     # Kyrgyzstan (HYDE: 28K)
        ],
        'sigma': 3.0,
        'fraction': 0.050,    # ~225K: Kazakhstan 108K + Uzbekistan 102K + Tajikistan 25K + Kyrgyzstan 28K
        'eps': 1.0,
        'wealth': 6.5,
        'description': 'Central Asia — HYDE: Kazakhstan 108K + Uzbekistan 102K + others',
        'hyde_pop': 258_398,
    },

    # South Asia
    'south_asia': {
        'centers': [
            (84.0, 28.0),     # Nepal (HYDE: 107K!)
            (76.0, 28.5),     # Upper Ganges-Yamuna
            (72.0, 30.0),     # Punjab
            (80.0, 22.0),     # Central India
            (77.0, 15.0),     # Deccan
            (80.5, 7.0),      # Sri Lanka (HYDE: 32K)
        ],
        'sigma': 2.5,
        'fraction': 0.048,    # ~216K: India 85K + Nepal 107K + Sri Lanka 32K + Bangladesh 10K
        'eps': 1.0,
        'wealth': 7.0,
        'description': 'South Asia — HYDE: Nepal 107K + India 85K + Sri Lanka 32K',
        'hyde_pop': 234_027,
    },

    # East Asia
    'yellow_river': {
        'centers': [
            (109.0, 34.5),    # Wei River Valley
            (113.0, 35.0),    # Middle Yellow River
            (117.0, 36.0),    # Lower Yellow River (Shandong)
        ],
        'sigma': 2.0,
        'fraction': 0.028,    # ~126K: ~60% of China 217K
        'eps': 1.2,
        'wealth': 9.0,
        'description': 'Yellow River basin — millet domestication, HYDE China: 217K',
        'hyde_pop': 130_387,
    },
    'yangtze_south_china': {
        'centers': [
            (112.0, 30.0),    # Middle Yangtze (rice origin)
            (120.0, 31.0),    # Lower Yangtze
            (106.0, 29.5),    # Sichuan basin
            (110.0, 23.0),    # Guangxi/Guangdong
        ],
        'sigma': 2.5,
        'fraction': 0.023,    # ~87K + Taiwan 6K
        'eps': 1.1,
        'wealth': 8.0,
        'description': 'Yangtze + South China — rice domestication, HYDE: ~40% of China + Taiwan',
        'hyde_pop': 92_503,
    },
    'northeast_asia': {
        'centers': [
            (127.0, 37.5),    # Korean peninsula (HYDE: S.Korea 11K + N.Korea 11K)
            (135.0, 36.0),    # Japan (HYDE: 5K, Jōmon)
            (130.0, 43.0),    # Manchuria
            (105.0, 48.0),    # Mongolia (HYDE: 15K)
        ],
        'sigma': 3.0,
        'fraction': 0.010,    # ~42K
        'eps': 1.0,
        'wealth': 6.0,
        'description': 'NE Asia — HYDE: Korea 22K + Japan 5K + Mongolia 15K',
        'hyde_pop': 41_716,
    },

    # Southeast Asia
    'southeast_asia': {
        'centers': [
            (100.0, 15.0),    # Thailand (HYDE: 14K)
            (108.0, 16.0),    # Vietnam (HYDE: 21K)
            (104.0, 12.0),    # Cambodia (HYDE: 10K)
            (106.0, 17.0),    # Laos (HYDE: 11K)
            (97.0, 20.0),     # Myanmar (HYDE: 20K)
            (120.0, 14.0),    # Philippines (HYDE: 16K)
            (110.0, -7.0),    # Java/Indonesia (HYDE: 21K)
        ],
        'sigma': 3.0,
        'fraction': 0.025,    # ~113K
        'eps': 1.0,
        'wealth': 6.0,
        'description': 'SE Asia — HYDE: Vietnam 21K + Indonesia 21K + Myanmar 20K + others',
        'hyde_pop': 113_583,
    },

    # Siberia / Former USSR (non-Central-Asia)
    'siberia_russia': {
        'centers': [
            (90.0, 55.0),     # Western Siberia
            (105.0, 52.0),    # Lake Baikal
            (40.0, 55.0),     # Central Russia
            (130.0, 62.0),    # Yakutia
        ],
        'sigma': 6.0,
        'fraction': 0.011,    # ~50K: Siberia + Far East (European Russia allocated to europe_eastern)
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'Russia/Siberia — HYDE: ~93K (from USSR 727K residual)',
        'hyde_pop': 93_274,
    },

    # Arabia
    'arabia': {
        'centers': [
            (44.0, 15.0),     # Yemen (HYDE: 1K)
            (45.0, 24.0),     # Central Arabia
            (50.0, 26.0),     # Gulf coast
            (40.0, 22.0),     # Hejaz
        ],
        'sigma': 2.5,
        'fraction': 0.005,    # ~21K: Saudi 17K + others
        'eps': 1.0,
        'wealth': 5.5,
        'description': 'Arabia — HYDE: Saudi 17K + Oman 3K + Yemen 1K',
        'hyde_pop': 20_882,
    },

    # ── Europe (10.7%) ────────────────────────────────────────────────
    # HYDE: Ukraine 99K, France 17K, Spain 18K, Italy 13K, UK 2K, etc.
    'europe_eastern': {
        'centers': [
            (35.0, 50.0),     # Ukraine (HYDE: 99K)
            (30.0, 52.0),     # Belarus (HYDE: 21K)
            (25.0, 48.0),     # Romania (HYDE: 3K)
            (20.0, 52.0),     # Poland
            (45.0, 48.0),     # Pontic-Caspian steppe
        ],
        'sigma': 3.0,
        'fraction': 0.055,    # ~248K: Ukraine 99K + Belarus 21K + Moldova 11K + European Russia ~117K
        'eps': 1.0,
        'wealth': 6.0,
        'description': 'Eastern Europe — HYDE: Ukraine 99K + Belarus 21K + Moldova 11K',
        'hyde_pop': 152_831,
    },
    'europe_mediterranean': {
        'centers': [
            (14.0, 41.0),     # Italy (HYDE: 13K)
            (23.0, 38.0),     # Greece (HYDE: 0.5K)
            (-4.0, 37.0),     # Iberia (HYDE: Spain 18K + Portugal 7K)
            (15.0, 45.0),     # Balkans
        ],
        'sigma': 2.0,
        'fraction': 0.030,    # ~135K
        'eps': 1.1,
        'wealth': 7.0,
        'description': 'Mediterranean Europe — HYDE: Spain 18K + Italy 13K + Portugal 7K',
        'hyde_pop': 53_590,
    },
    'europe_atlantic': {
        'centers': [
            (2.0, 47.0),      # France (HYDE: 17K)
            (-5.0, 52.0),     # British Isles (HYDE: UK 2K)
            (-3.0, 43.0),     # Bay of Biscay
            (4.0, 51.0),      # Low Countries
        ],
        'sigma': 2.0,
        'fraction': 0.012,    # ~54K
        'eps': 1.0,
        'wealth': 6.5,
        'description': 'Atlantic Europe — HYDE: France 17K + Belgium/Netherlands 2K + UK 2K',
        'hyde_pop': 21_082,
    },
    'europe_central_north': {
        'centers': [
            (10.0, 51.0),     # Germany (HYDE: 7K)
            (15.0, 48.0),     # Austria/Czechia
            (20.0, 50.0),     # Carpathian basin (Hungary 2K + Slovakia 2K)
            (12.0, 57.0),     # Southern Scandinavia (HYDE: Denmark 0.5K + Sweden 0.2K)
            (25.0, 62.0),     # Finland (HYDE: 0.4K)
        ],
        'sigma': 2.5,
        'fraction': 0.010,    # ~45K
        'eps': 1.0,
        'wealth': 5.5,
        'description': 'Central/North Europe — HYDE: Germany 7K + Hungary 2K + Scandinavia 1K',
        'hyde_pop': 15_746,
    },

    # Caucasus
    'caucasus': {
        'centers': [
            (44.5, 42.0),     # Georgia (HYDE: 25K)
            (44.5, 40.0),     # Armenia (HYDE: 10K)
            (49.0, 40.5),     # Azerbaijan (HYDE: 21K)
        ],
        'sigma': 1.5,
        'fraction': 0.012,    # ~56K
        'eps': 1.1,
        'wealth': 7.0,
        'description': 'Caucasus — HYDE: Georgia 25K + Azerbaijan 21K + Armenia 10K',
        'hyde_pop': 55_343,
    },

    # ── Oceania (7.2%) ────────────────────────────────────────────────
    # HYDE: Australia 315K, Papua New Guinea 10K
    'australia': {
        'centers': [
            (133.0, -25.0),   # Central Australia
            (145.0, -38.0),   # SE Australia (Murray-Darling)
            (152.0, -28.0),   # NE Australia
            (116.0, -32.0),   # SW Australia
        ],
        'sigma': 5.0,
        'fraction': 0.070,    # ~315K
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'Australia — HYDE: 315K, 50,000+ years of occupation',
        'hyde_pop': 314_500,
    },
    'melanesia': {
        'centers': [
            (146.0, -6.0),    # Papua New Guinea highlands (HYDE: 10K)
        ],
        'sigma': 2.0,
        'fraction': 0.002,    # ~10K
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'Melanesia — HYDE: PNG 10K',
        'hyde_pop': 9_698,
    },

    # ── Africa (5.1%) ─────────────────────────────────────────────────
    # HYDE: Congo DR 22K, North Africa ~40K, Ethiopia 16K, Nigeria 17K,
    #       Uganda 13K, Kenya 10K, Chad 10K, Niger 10K, etc.
    'nile_east_africa': {
        'centers': [
            (31.2, 30.0),     # Lower Nile / Egypt (HYDE: 14K)
            (32.5, 25.0),     # Upper Nile
            (33.5, 15.5),     # Sudan (HYDE: 12K)
            (38.0, 7.0),      # Ethiopia (HYDE: 16K)
            (36.0, -1.5),     # Kenya (HYDE: 10K)
            (32.0, 0.5),      # Uganda (HYDE: 13K)
        ],
        'sigma': 2.0,
        'fraction': 0.019,    # ~85K
        'eps': 1.1,
        'wealth': 8.0,
        'description': 'Nile/East Africa — HYDE: Ethiopia 16K + Egypt 14K + Uganda 13K + Kenya 10K',
        'hyde_pop': 84_021,
    },
    'west_central_africa': {
        'centers': [
            (3.0, 7.5),       # Nigeria (HYDE: 17K)
            (20.0, 2.0),      # Congo DR (HYDE: 22K)
            (-4.0, 7.0),      # Ivory Coast (HYDE: 5K)
            (13.0, 28.0),     # Libya (HYDE: 7K)
            (10.0, 32.0),     # Tunisia (HYDE: 5K)
            (3.0, 35.0),      # Algeria (HYDE: 12K)
            (-1.0, 12.0),     # Burkina Faso / Niger
        ],
        'sigma': 3.0,
        'fraction': 0.024,    # ~109K
        'eps': 1.0,
        'wealth': 6.0,
        'description': 'West/Central/North Africa — HYDE: Congo 22K + Nigeria 17K + Morocco 17K + Algeria 12K',
        'hyde_pop': 108_656,
    },
    'southern_africa': {
        'centers': [
            (28.0, -26.0),    # Highveld
            (18.5, -34.0),    # Cape (HYDE: South Africa 90)
            (35.0, -15.0),    # Mozambique/Malawi
        ],
        'sigma': 3.0,
        'fraction': 0.008,    # ~36K
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'Southern/SE Africa — HYDE: Tanzania 8K + Malawi 3K + Zimbabwe 0.7K',
        'hyde_pop': 36_296,
    },
}

# ─── 70,000 BCE scenario (Out of Africa) ────────────────────────────────
REGIONS_70000BCE = {
    'east_africa_core': {
        'centers': [
            (36.0, -1.5), (35.0, -3.5), (38.0, 7.0), (32.0, 0.5),
            (34.0, -6.0), (37.0, 3.0),
        ],
        'sigma': 3.0,
        'fraction': 0.70,
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'East Africa core — main human population',
    },
    'south_africa_70k': {
        'centers': [
            (28.0, -30.0), (18.5, -34.0), (25.0, -25.0),
        ],
        'sigma': 3.0,
        'fraction': 0.15,
        'eps': 1.0,
        'wealth': 5.0,
        'description': 'Southern Africa — Blombos Cave culture',
    },
    'north_africa_70k': {
        'centers': [(10.0, 32.0), (3.0, 35.0)],
        'sigma': 3.0,
        'fraction': 0.10,
        'eps': 1.0,
        'wealth': 4.0,
        'description': 'North Africa — Aterian culture',
    },
    'levant_70k': {
        'centers': [(35.5, 32.0), (36.0, 34.0)],
        'sigma': 1.5,
        'fraction': 0.05,
        'eps': 1.0,
        'wealth': 4.0,
        'description': 'Levant — earliest out-of-Africa scouts',
    },
}


def generate_population(n_total, regions, seed=42):
    """Generate initial conditions based on regional population distribution."""
    rng = np.random.default_rng(seed)

    fractions = {k: v['fraction'] for k, v in regions.items()}
    total_frac = sum(fractions.values())
    for k in fractions:
        fractions[k] /= total_frac

    records = []

    for region_name, cfg in regions.items():
        n_region = max(1, int(round(n_total * fractions[region_name])))
        centers = cfg['centers']
        sigma = cfg['sigma']

        for _ in range(n_region):
            cx, cy = centers[rng.integers(len(centers))]
            lon = cx + rng.normal(0, sigma)
            lat = cy + rng.normal(0, sigma)
            lon = np.clip(lon, -180, 180)
            lat = np.clip(lat, -85, 85)

            age = rng.uniform(15.0, 45.0)
            sex = int(rng.random() < 0.5)
            w = cfg['wealth'] * rng.uniform(0.5, 1.5)
            eps = cfg['eps'] * rng.uniform(0.8, 1.2)
            c0 = rng.normal(0, 1)
            c1 = rng.normal(0, 1)

            records.append({
                'x': lon, 'y': lat,
                'w': round(w, 2), 'eps': round(eps, 4),
                'age': round(age, 1), 'sex': sex,
                'c0': round(c0, 4), 'c1': round(c1, 4),
                'region': region_name,
            })

    rng.shuffle(records)
    actual_n = len(records)

    region_counts = {}
    for r in records:
        region_counts[r['region']] = region_counts.get(r['region'], 0) + 1

    continent_map = {
        'mesoamerica': 'N.America', 'north_america_east': 'N.America',
        'north_america_west': 'N.America', 'north_america_plains': 'N.America',
        'south_america_andes': 'S.America', 'south_america_brazil': 'S.America',
        'south_america_south': 'S.America',
        'levant': 'Asia', 'mesopotamia': 'Asia', 'anatolia': 'Asia',
        'iran_plateau': 'Asia', 'central_asia': 'Asia', 'south_asia': 'Asia',
        'yellow_river': 'Asia', 'yangtze_south_china': 'Asia',
        'northeast_asia': 'Asia', 'southeast_asia': 'Asia',
        'siberia_russia': 'Asia', 'arabia': 'Asia', 'caucasus': 'Asia',
        'europe_eastern': 'Europe', 'europe_mediterranean': 'Europe',
        'europe_atlantic': 'Europe', 'europe_central_north': 'Europe',
        'australia': 'Oceania', 'melanesia': 'Oceania',
        'nile_east_africa': 'Africa', 'west_central_africa': 'Africa',
        'southern_africa': 'Africa',
    }

    print(f"Generated {actual_n} agents across {len(regions)} regions:")
    print(f"{'Region':<28s} {'Count':>7s} {'%':>6s}  Description")
    print("-" * 90)
    for rname, rcfg in sorted(regions.items(),
                               key=lambda x: -region_counts.get(x[0], 0)):
        cnt = region_counts.get(rname, 0)
        pct = 100.0 * cnt / actual_n
        hyde_str = f" [HYDE: {rcfg.get('hyde_pop', '?'):,}]" if 'hyde_pop' in rcfg else ''
        print(f"  {rname:<26s} {cnt:>7d} {pct:>5.1f}%  {rcfg['description']}")

    print("\n  Continental totals:")
    cont_totals = {}
    for rname, cnt in region_counts.items():
        cont = continent_map.get(rname, 'Other')
        cont_totals[cont] = cont_totals.get(cont, 0) + cnt
    hyde_cont = {'N.America': 26.3, 'S.America': 24.4, 'Asia': 26.3,
                 'Europe': 10.7, 'Oceania': 7.2, 'Africa': 5.1}
    for cont in ['N.America', 'S.America', 'Asia', 'Europe', 'Oceania', 'Africa']:
        cnt = cont_totals.get(cont, 0)
        pct = 100.0 * cnt / actual_n
        target = hyde_cont.get(cont, 0)
        print(f"    {cont:<12s} {cnt:>7d} ({pct:>5.1f}%)  [HYDE target: {target}%]")

    return records


def write_csv(records, filepath):
    """Write initial conditions CSV."""
    fieldnames = ['x', 'y', 'w', 'eps', 'age', 'sex', 'c0', 'c1']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = {k: r[k] for k in fieldnames}
            writer.writerow(row)
    print(f"\nWritten: {filepath} ({len(records)} agents)")


def main():
    parser = argparse.ArgumentParser(
        description='Generate HYDE 3.3-calibrated initial conditions for Politeia')
    parser.add_argument('--n', type=int, default=100000,
                        help='Total number of agents (default: 100000)')
    parser.add_argument('--era', default='10000bce',
                        choices=['70000bce', '10000bce'],
                        help='Starting era (default: 10000bce)')
    parser.add_argument('--output', default=None,
                        help='Output CSV file path')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('--summary-only', action='store_true',
                        help='Print summary without writing file')
    args = parser.parse_args()

    if args.era == '70000bce':
        regions = REGIONS_70000BCE
        era_label = '70,000 BCE (Out of Africa)'
    else:
        regions = REGIONS_10000BCE
        era_label = '10,000 BCE (Neolithic transition) — HYDE 3.3 calibrated'

    print(f"=== Politeia Genesis: {era_label} ===")
    print(f"Total agents: {args.n:,}")
    if args.era == '10000bce':
        ratio = HYDE_GLOBAL_POPULATION_10000BCE / args.n
        print(f"Representation ratio: 1 agent = {ratio:.1f} real people")
        print(f"HYDE 3.3 global population at 10,000 BCE: {HYDE_GLOBAL_POPULATION_10000BCE:,}")
    print()

    records = generate_population(args.n, regions, seed=args.seed)

    if not args.summary_only:
        output = args.output or f"genesis_{args.era}_{args.n}.csv"
        write_csv(records, output)

        lons = [r['x'] for r in records]
        lats = [r['y'] for r in records]
        print(f"\nSpatial extent:")
        print(f"  Longitude: [{min(lons):.1f}, {max(lons):.1f}]")
        print(f"  Latitude:  [{min(lats):.1f}, {max(lats):.1f}]")
        print(f"\nSuggested Politeia config:")
        print(f"  initial_conditions_file = {output}")
        print(f"  domain_xmin = -180")
        print(f"  domain_xmax = 180")
        print(f"  domain_ymin = -85")
        print(f"  domain_ymax = 85")


if __name__ == '__main__':
    main()
