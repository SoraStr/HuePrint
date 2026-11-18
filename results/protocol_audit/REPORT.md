# Offline Protocol, Sub-Provider, and Permutation-Routing Summary

All computations are strictly read-only on raw logs and prior frozen artifacts.

## 1. S1 Cross-Gateway Subgroup Stratification (9 Standard vs. 5 Reasoning-Override Models)

| Scenario | Group | Models | Perm Reject (p<=0.05) | Energy EER | Energy FRR/FAR (B tau) | Hybrid EER |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| CF0_CF21 | All 14 | 14 | 1/14 (7.14%) | 0.00% | 0.00% / 2.20% | 0.00% |
| CF0_CF21 | 9 Standard (no reasoning override) | 9 | 1/9 (11.11%) | 0.00% | 0.00% / 1.39% | 0.00% |
| CF0_CF21 | 5 Reasoning (OR effort=low) | 5 | 0/5 (0.00%) | 0.00% | 0.00% / 15.00% | 0.00% |
| CF21_OR21 | All 14 | 14 | 4/14 (28.57%) | 0.00% | 0.00% / 0.55% | 0.00% |
| CF21_OR21 | 9 Standard (no reasoning override) | 9 | 2/9 (22.22%) | 0.00% | 0.00% / 0.00% | 0.00% |
| CF21_OR21 | 5 Reasoning (OR effort=low) | 5 | 2/5 (40.00%) | 0.00% | 0.00% / 5.00% | 0.00% |
| CF0_OR21 | All 14 | 14 | 6/14 (42.86%) | 0.00% | 0.00% / 0.00% | 0.00% |
| CF0_OR21 | 9 Standard (no reasoning override) | 9 | 4/9 (44.44%) | 0.00% | 0.00% / 0.00% | 0.00% |
| CF0_OR21 | 5 Reasoning (OR effort=low) | 5 | 2/5 (40.00%) | 0.00% | 0.00% / 0.00% | 0.00% |

## 2. Mixed-Routing Detection: Frozen Midpoint (tau_mid) vs. 999-Permutation Test (alpha=0.05)

| Protocol | Subgroup | Query Calls | tau_mid @ p=0.8 (20% fallback) | tau_mid Clean FRR (p=1) | Perm @ p=0.8 (20% fallback) | Perm Clean FRR (p=1) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B20_q3 | all_distinct_labels | 60 | 11.28% (4.39%–20.11%) | 1.00% | 8.56% (4.22%–12.67%) | 4.50% |
| B20_q3 | same_family | 60 | 7.50% (0.00%–15.25%) | 1.11% | 9.00% (4.75%–15.25%) | 5.00% |
| B40_q7 | all_distinct_labels | 280 | 0.33% (0.00%–1.17%) | 0.00% | 33.28% (27.61%–40.00%) | 0.00% |
| B40_q7 | same_family | 280 | 0.00% (0.00%–0.00%) | 0.00% | 25.75% (10.00%–40.00%) | 0.00% |
| S3_10_q3 | all_distinct_labels | 30 | 55.97% (51.25%–61.11%) | 39.00% | 6.66% (2.59%–11.87%) | 4.75% |
| S3_10_q3 | same_family | 30 | 39.21% (28.82%–52.76%) | 35.79% | 6.45% (2.50%–10.66%) | 3.95% |
| S3_10_q7 | all_distinct_labels | 70 | 12.45% (7.83%–16.14%) | 3.75% | 17.57% (11.29%–22.64%) | 4.50% |
| S3_10_q7 | same_family | 70 | 5.00% (0.00%–10.53%) | 1.58% | 16.71% (10.13%–23.82%) | 3.95% |
| S1_CF0_OR21_20_q3 | all_distinct_labels | 60 | 29.95% (24.97%–37.99%) | 11.07% | 19.53% (12.06%–25.93%) | 16.07% |
| S1_CF0_OR21_20_q3 | same_family | 60 | 14.64% (7.02%–26.31%) | 4.17% | 19.52% (11.79%–28.69%) | 15.83% |
| S1_CF21_OR21_20_q3 | all_distinct_labels | 60 | 26.37% (21.95%–33.52%) | 18.57% | 15.22% (9.18%–22.64%) | 13.93% |
| S1_CF21_OR21_20_q3 | same_family | 60 | 13.10% (7.02%–19.17%) | 13.75% | 18.10% (7.14%–28.57%) | 15.83% |

## 3. S3 Provider Mixing & Reasoning-Token Cost Tail

- Multi-provider targets in S3 color: 7/20 (odd vs. even provider-share TV distance mean=0.0419, max=0.1200).
- Scenario G per-audit query USD across 20 S3 targets: min=$0.0292, median=$0.0345, p90=$0.0422, max(19/20)=$0.0432, max(all 20, s3-deepseek-v3.2)=$0.2711.

## 4. Table 5 vs. Table 7 Valid-Cell Rule on Dataset E

- Cells excluded in Table 7 due to min(n_ref, n_query) < 2: 1 ([{'target_id': 'gw-gemini-3.6-flash', 'cell': 'rgb_warm|zh', 'n_valid_ref': 2, 'n_valid_query': 1}]).
