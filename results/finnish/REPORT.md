# Test 3: Finnish

300 items per dataset, zero-shot. SIB-200, Belebele and MASSIVE are parallel: the same items in English and in Finnish. ScandiSent-fi is native Finnish (no English version). Accuracy; ±5 points of sampling noise on 300 items, much less on the paired English → Finnish differences.

## Accuracy

Conditions: **en** = EN text, EN question; **fi-en** = FI text, EN question; **fi** = FI text, FI question.

| Model | SIB-200 topic en | SIB-200 topic fi-en | SIB-200 topic fi | Belebele reading en | Belebele reading fi-en | Belebele reading fi | MASSIVE intent en | MASSIVE intent fi-en | MASSIVE intent fi | ScandiSent-fi fi-en | ScandiSent-fi fi |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Decider 4B v2 | 0.827 | 0.837 | 0.833 | 0.950 | 0.913 | 0.903 | 0.987 | 0.947 | 0.963 | 0.917 | 0.913 |
| Decider 2B | 0.837 | 0.817 | 0.803 | 0.890 | 0.790 | 0.800 | 0.977 | 0.873 | 0.893 | 0.907 | 0.903 |
| Kev 9B | 0.847 | 0.843 | 0.863 | 0.830 | 0.820 | 0.803 | 0.953 | 0.933 | 0.913 | 0.953 | 0.947 |
| Kev 4B | 0.857 | 0.860 | 0.860 | 0.747 | 0.717 | 0.703 | 0.953 | 0.920 | 0.937 | 0.920 | 0.913 |
| Kev 0.8B | 0.810 | 0.740 | 0.743 | 0.637 | 0.490 | 0.493 | 0.923 | 0.610 | 0.757 | 0.847 | 0.830 |
| GLiNER2.5-multi-Decide | 0.793 | 0.717 | 0.730 | 0.273 | 0.280 | 0.267 | 0.840 | 0.667 | 0.670 | 0.880 | 0.890 |
| CLM 8B | 0.420 | 0.257 | 0.280 | 0.447 | 0.267 | 0.267 | 0.550 | 0.363 | 0.153 | 0.767 | 0.500 |
| LLM Qwen 3.8 27B (Leviathan) | 0.873 | 0.883 | 0.857 | 0.933 | 0.867 | 0.863 | 0.977 | 0.937 | 0.957 | 0.953 | 0.953 |

Chance: SIB 0.14 (most frequent topic 0.24), Belebele 0.25, MASSIVE 0.10, ScandiSent 0.50.

**Training data.** Decider 4B v2's card lists "MASSIVE (multilingual)" in its training mixture (train split; our items are from the test split, and the card says evaluation rows were de-duplicated against training rows), and marks massive-en-US as trained for the Decider family: for Decider, MASSIVE is a trained task, not zero-shot. Belebele is on the card's list of datasets kept out of training. SIB-200 (FLORES) and ScandiSent are not listed.

## English → Finnish on the same items

Accuracy change from the English condition, paired by item, with a bootstrap 95% interval.

| Model | Dataset | FI text, EN question | FI text, FI question |
|---|---|--:|--:|
| Decider 4B v2 | SIB-200 topic (7) | +0.010 [-0.023, +0.043] | +0.007 [-0.030, +0.043] |
| Decider 4B v2 | Belebele reading (4) | -0.037 [-0.063, -0.013] | -0.047 [-0.073, -0.020] |
| Decider 4B v2 | MASSIVE intent (10) | -0.040 [-0.067, -0.017] | -0.023 [-0.043, -0.003] |
| Decider 2B | SIB-200 topic (7) | -0.020 [-0.057, +0.020] | -0.033 [-0.073, +0.007] |
| Decider 2B | Belebele reading (4) | -0.100 [-0.143, -0.057] | -0.090 [-0.130, -0.047] |
| Decider 2B | MASSIVE intent (10) | -0.103 [-0.140, -0.067] | -0.083 [-0.120, -0.050] |
| Kev 9B | SIB-200 topic (7) | -0.003 [-0.033, +0.023] | +0.017 [-0.013, +0.047] |
| Kev 9B | Belebele reading (4) | -0.010 [-0.050, +0.030] | -0.027 [-0.067, +0.013] |
| Kev 9B | MASSIVE intent (10) | -0.020 [-0.050, +0.010] | -0.040 [-0.073, -0.003] |
| Kev 4B | SIB-200 topic (7) | +0.003 [-0.030, +0.037] | +0.003 [-0.030, +0.037] |
| Kev 4B | Belebele reading (4) | -0.030 [-0.060, +0.003] | -0.043 [-0.073, -0.010] |
| Kev 4B | MASSIVE intent (10) | -0.033 [-0.067, +0.000] | -0.017 [-0.047, +0.013] |
| Kev 0.8B | SIB-200 topic (7) | -0.070 [-0.113, -0.027] | -0.067 [-0.117, -0.013] |
| Kev 0.8B | Belebele reading (4) | -0.147 [-0.203, -0.090] | -0.143 [-0.203, -0.087] |
| Kev 0.8B | MASSIVE intent (10) | -0.313 [-0.367, -0.260] | -0.167 [-0.213, -0.117] |
| GLiNER2.5-multi-Decide | SIB-200 topic (7) | -0.077 [-0.123, -0.027] | -0.063 [-0.113, -0.013] |
| GLiNER2.5-multi-Decide | Belebele reading (4) | +0.007 [-0.050, +0.060] | -0.007 [-0.060, +0.047] |
| GLiNER2.5-multi-Decide | MASSIVE intent (10) | -0.173 [-0.223, -0.127] | -0.170 [-0.223, -0.113] |
| CLM 8B | SIB-200 topic (7) | -0.163 [-0.220, -0.107] | -0.140 [-0.213, -0.067] |
| CLM 8B | Belebele reading (4) | -0.180 [-0.253, -0.110] | -0.180 [-0.253, -0.110] |
| CLM 8B | MASSIVE intent (10) | -0.187 [-0.243, -0.137] | -0.397 [-0.453, -0.340] |
| LLM Qwen 3.8 27B (Leviathan) | SIB-200 topic (7) | +0.010 [-0.013, +0.033] | -0.017 [-0.043, +0.010] |
| LLM Qwen 3.8 27B (Leviathan) | Belebele reading (4) | -0.067 [-0.103, -0.033] | -0.070 [-0.107, -0.033] |
| LLM Qwen 3.8 27B (Leviathan) | MASSIVE intent (10) | -0.040 [-0.067, -0.017] | -0.020 [-0.040, -0.003] |

## Macro-F1 and calibration (ECE)

ECE is not meaningful for the LLM (one label, all probability on it).

| Model | Dataset | Condition | Accuracy | Macro-F1 | ECE |
|---|---|---|--:|--:|--:|
| Decider 4B v2 | SIB-200 topic (7) | en | 0.827 | 0.815 | 0.064 |
| Decider 4B v2 | SIB-200 topic (7) | fi-en | 0.837 | 0.822 | 0.087 |
| Decider 4B v2 | SIB-200 topic (7) | fi | 0.833 | 0.819 | 0.079 |
| Decider 4B v2 | Belebele reading (4) | en | 0.950 | 0.950 | 0.019 |
| Decider 4B v2 | Belebele reading (4) | fi-en | 0.913 | 0.913 | 0.026 |
| Decider 4B v2 | Belebele reading (4) | fi | 0.903 | 0.903 | 0.018 |
| Decider 4B v2 | MASSIVE intent (10) | en | 0.987 | 0.986 | 0.041 |
| Decider 4B v2 | MASSIVE intent (10) | fi-en | 0.947 | 0.946 | 0.046 |
| Decider 4B v2 | MASSIVE intent (10) | fi | 0.963 | 0.964 | 0.066 |
| Decider 4B v2 | ScandiSent-fi (2) | fi-en | 0.917 | 0.917 | 0.048 |
| Decider 4B v2 | ScandiSent-fi (2) | fi | 0.913 | 0.913 | 0.050 |
| Decider 2B | SIB-200 topic (7) | en | 0.837 | 0.822 | 0.041 |
| Decider 2B | SIB-200 topic (7) | fi-en | 0.817 | 0.813 | 0.061 |
| Decider 2B | SIB-200 topic (7) | fi | 0.803 | 0.793 | 0.061 |
| Decider 2B | Belebele reading (4) | en | 0.890 | 0.889 | 0.021 |
| Decider 2B | Belebele reading (4) | fi-en | 0.790 | 0.791 | 0.052 |
| Decider 2B | Belebele reading (4) | fi | 0.800 | 0.800 | 0.053 |
| Decider 2B | MASSIVE intent (10) | en | 0.977 | 0.977 | 0.007 |
| Decider 2B | MASSIVE intent (10) | fi-en | 0.873 | 0.875 | 0.030 |
| Decider 2B | MASSIVE intent (10) | fi | 0.893 | 0.896 | 0.026 |
| Decider 2B | ScandiSent-fi (2) | fi-en | 0.907 | 0.907 | 0.053 |
| Decider 2B | ScandiSent-fi (2) | fi | 0.903 | 0.903 | 0.060 |
| Kev 9B | SIB-200 topic (7) | en | 0.847 | 0.838 | 0.075 |
| Kev 9B | SIB-200 topic (7) | fi-en | 0.843 | 0.841 | 0.086 |
| Kev 9B | SIB-200 topic (7) | fi | 0.863 | 0.854 | 0.095 |
| Kev 9B | Belebele reading (4) | en | 0.830 | 0.828 | 0.049 |
| Kev 9B | Belebele reading (4) | fi-en | 0.820 | 0.818 | 0.072 |
| Kev 9B | Belebele reading (4) | fi | 0.803 | 0.801 | 0.073 |
| Kev 9B | MASSIVE intent (10) | en | 0.953 | 0.953 | 0.133 |
| Kev 9B | MASSIVE intent (10) | fi-en | 0.933 | 0.934 | 0.141 |
| Kev 9B | MASSIVE intent (10) | fi | 0.913 | 0.916 | 0.103 |
| Kev 9B | ScandiSent-fi (2) | fi-en | 0.953 | 0.953 | 0.015 |
| Kev 9B | ScandiSent-fi (2) | fi | 0.947 | 0.947 | 0.016 |
| Kev 4B | SIB-200 topic (7) | en | 0.857 | 0.849 | 0.105 |
| Kev 4B | SIB-200 topic (7) | fi-en | 0.860 | 0.855 | 0.126 |
| Kev 4B | SIB-200 topic (7) | fi | 0.860 | 0.851 | 0.116 |
| Kev 4B | Belebele reading (4) | en | 0.747 | 0.750 | 0.099 |
| Kev 4B | Belebele reading (4) | fi-en | 0.717 | 0.717 | 0.088 |
| Kev 4B | Belebele reading (4) | fi | 0.703 | 0.704 | 0.105 |
| Kev 4B | MASSIVE intent (10) | en | 0.953 | 0.954 | 0.157 |
| Kev 4B | MASSIVE intent (10) | fi-en | 0.920 | 0.923 | 0.188 |
| Kev 4B | MASSIVE intent (10) | fi | 0.937 | 0.938 | 0.167 |
| Kev 4B | ScandiSent-fi (2) | fi-en | 0.920 | 0.920 | 0.058 |
| Kev 4B | ScandiSent-fi (2) | fi | 0.913 | 0.913 | 0.043 |
| Kev 0.8B | SIB-200 topic (7) | en | 0.810 | 0.799 | 0.088 |
| Kev 0.8B | SIB-200 topic (7) | fi-en | 0.740 | 0.739 | 0.078 |
| Kev 0.8B | SIB-200 topic (7) | fi | 0.743 | 0.735 | 0.128 |
| Kev 0.8B | Belebele reading (4) | en | 0.637 | 0.637 | 0.107 |
| Kev 0.8B | Belebele reading (4) | fi-en | 0.490 | 0.491 | 0.061 |
| Kev 0.8B | Belebele reading (4) | fi | 0.493 | 0.493 | 0.064 |
| Kev 0.8B | MASSIVE intent (10) | en | 0.923 | 0.925 | 0.177 |
| Kev 0.8B | MASSIVE intent (10) | fi-en | 0.610 | 0.575 | 0.139 |
| Kev 0.8B | MASSIVE intent (10) | fi | 0.757 | 0.771 | 0.289 |
| Kev 0.8B | ScandiSent-fi (2) | fi-en | 0.847 | 0.847 | 0.069 |
| Kev 0.8B | ScandiSent-fi (2) | fi | 0.830 | 0.830 | 0.046 |
| GLiNER2.5-multi-Decide | SIB-200 topic (7) | en | 0.793 | 0.795 | 0.151 |
| GLiNER2.5-multi-Decide | SIB-200 topic (7) | fi-en | 0.717 | 0.715 | 0.110 |
| GLiNER2.5-multi-Decide | SIB-200 topic (7) | fi | 0.730 | 0.718 | 0.182 |
| GLiNER2.5-multi-Decide | Belebele reading (4) | en | 0.273 | 0.260 | 0.145 |
| GLiNER2.5-multi-Decide | Belebele reading (4) | fi-en | 0.280 | 0.265 | 0.135 |
| GLiNER2.5-multi-Decide | Belebele reading (4) | fi | 0.267 | 0.252 | 0.141 |
| GLiNER2.5-multi-Decide | MASSIVE intent (10) | en | 0.840 | 0.846 | 0.236 |
| GLiNER2.5-multi-Decide | MASSIVE intent (10) | fi-en | 0.667 | 0.695 | 0.183 |
| GLiNER2.5-multi-Decide | MASSIVE intent (10) | fi | 0.670 | 0.667 | 0.175 |
| GLiNER2.5-multi-Decide | ScandiSent-fi (2) | fi-en | 0.880 | 0.879 | 0.041 |
| GLiNER2.5-multi-Decide | ScandiSent-fi (2) | fi | 0.890 | 0.890 | 0.030 |
| CLM 8B | SIB-200 topic (7) | en | 0.420 | 0.400 | 0.277 |
| CLM 8B | SIB-200 topic (7) | fi-en | 0.257 | 0.211 | 0.481 |
| CLM 8B | SIB-200 topic (7) | fi | 0.280 | 0.122 | 0.485 |
| CLM 8B | Belebele reading (4) | en | 0.447 | 0.446 | 0.347 |
| CLM 8B | Belebele reading (4) | fi-en | 0.267 | 0.266 | 0.418 |
| CLM 8B | Belebele reading (4) | fi | 0.267 | 0.267 | 0.422 |
| CLM 8B | MASSIVE intent (10) | en | 0.550 | 0.523 | 0.189 |
| CLM 8B | MASSIVE intent (10) | fi-en | 0.363 | 0.319 | 0.306 |
| CLM 8B | MASSIVE intent (10) | fi | 0.153 | 0.065 | 0.470 |
| CLM 8B | ScandiSent-fi (2) | fi-en | 0.767 | 0.759 | 0.076 |
| CLM 8B | ScandiSent-fi (2) | fi | 0.500 | 0.333 | 0.476 |
| LLM Qwen 3.8 27B (Leviathan) | SIB-200 topic (7) | en | 0.873 | 0.866 | 0.127 |
| LLM Qwen 3.8 27B (Leviathan) | SIB-200 topic (7) | fi-en | 0.883 | 0.879 | 0.117 |
| LLM Qwen 3.8 27B (Leviathan) | SIB-200 topic (7) | fi | 0.857 | 0.850 | 0.143 |
| LLM Qwen 3.8 27B (Leviathan) | Belebele reading (4) | en | 0.933 | 0.933 | 0.067 |
| LLM Qwen 3.8 27B (Leviathan) | Belebele reading (4) | fi-en | 0.867 | 0.866 | 0.133 |
| LLM Qwen 3.8 27B (Leviathan) | Belebele reading (4) | fi | 0.863 | 0.863 | 0.137 |
| LLM Qwen 3.8 27B (Leviathan) | MASSIVE intent (10) | en | 0.977 | 0.977 | 0.023 |
| LLM Qwen 3.8 27B (Leviathan) | MASSIVE intent (10) | fi-en | 0.937 | 0.938 | 0.063 |
| LLM Qwen 3.8 27B (Leviathan) | MASSIVE intent (10) | fi | 0.957 | 0.957 | 0.043 |
| LLM Qwen 3.8 27B (Leviathan) | ScandiSent-fi (2) | fi-en | 0.953 | 0.953 | 0.047 |
| LLM Qwen 3.8 27B (Leviathan) | ScandiSent-fi (2) | fi | 0.953 | 0.953 | 0.047 |

## Option order in Finnish (Belebele)

Accuracy by where the correct answer is listed. An order-blind model is level across A-D (±~10 points of noise with ~75 items per position).

| Model | Condition | A | B | C | D |
|---|---|--:|--:|--:|--:|
| Decider 4B v2 | en | 0.93 | 0.95 | 0.94 | 0.99 |
| Decider 4B v2 | fi-en | 0.88 | 0.90 | 0.93 | 0.94 |
| Decider 4B v2 | fi | 0.88 | 0.87 | 0.91 | 0.94 |
| Decider 2B | en | 0.88 | 0.86 | 0.90 | 0.91 |
| Decider 2B | fi-en | 0.81 | 0.73 | 0.78 | 0.84 |
| Decider 2B | fi | 0.83 | 0.75 | 0.79 | 0.84 |
| Kev 9B | en | 0.75 | 0.81 | 0.84 | 0.91 |
| Kev 9B | fi-en | 0.75 | 0.80 | 0.88 | 0.84 |
| Kev 9B | fi | 0.77 | 0.77 | 0.87 | 0.80 |
| Kev 4B | en | 0.75 | 0.67 | 0.76 | 0.81 |
| Kev 4B | fi-en | 0.71 | 0.62 | 0.77 | 0.77 |
| Kev 4B | fi | 0.70 | 0.61 | 0.76 | 0.76 |
| Kev 0.8B | en | 0.72 | 0.57 | 0.59 | 0.69 |
| Kev 0.8B | fi-en | 0.51 | 0.46 | 0.43 | 0.59 |
| Kev 0.8B | fi | 0.49 | 0.47 | 0.41 | 0.61 |
| GLiNER2.5-multi-Decide | en | 0.36 | 0.08 | 0.30 | 0.37 |
| GLiNER2.5-multi-Decide | fi-en | 0.23 | 0.11 | 0.41 | 0.36 |
| GLiNER2.5-multi-Decide | fi | 0.23 | 0.10 | 0.39 | 0.34 |
| CLM 8B | en | 0.41 | 0.43 | 0.46 | 0.49 |
| CLM 8B | fi-en | 0.23 | 0.27 | 0.22 | 0.36 |
| CLM 8B | fi | 0.25 | 0.29 | 0.18 | 0.36 |
| LLM Qwen 3.8 27B (Leviathan) | en | 0.91 | 0.92 | 0.94 | 0.96 |
| LLM Qwen 3.8 27B (Leviathan) | fi-en | 0.83 | 0.82 | 0.90 | 0.91 |
| LLM Qwen 3.8 27B (Leviathan) | fi | 0.84 | 0.82 | 0.90 | 0.89 |
