# Signed U-statistic energy: offline sensitivity analysis

Only existing parsed cloud responses are used. No model calls or test-based parameter selection.

For independent IID samples from P and Q, let a = E||X-X′|| and b = E||Y-Y′||. The V numerator has expectation E²(P,Q) + a/n + b/m. Under P=Q, this becomes (1/n+1/m)a. Replacing within-sample denominators n²,m² by n(n−1),m(m−1) gives an unbiased signed numerator for E²(P,Q). It can be negative.

The signed regularized score divides that numerator by the random positive denominator 2dXY+30. Neither random-denominator normalization nor positive-part clipping preserves exact unbiasedness, so signed and clipped U ratios are reported side by side. No square root is applied to signed U. Main-manuscript Proposition 2 (Supplement G) establishes unified one-sided (2*eps/delta0) and two-sided (4*eps/delta0) Lipschitz bounds for both V and U regularized energy ratios on the cone 0 <= h <= 2d.

All new V/U comparisons use the same cells with at least two valid observations per side. Legacy V results allowing one valid observation are retained in results.json, rather than silently mixing validity rules. Enrollment self-centering uses 256 independent bootstrap draws per cell and alpha=1. All thresholds are fitted on B. B3v3 is primary; B6v6 is the budget-matched S1 sensitivity analysis.

| Scenario | Calibration | Score | EER | FRR | FAR | Threshold |
| --- | --- | --- | --- | --- | --- | --- |
| E_clean | B3v3 | v_e2 | 13.33% | 40.00% | 0.00% | 10.24584649 |
| E_clean | B3v3 | v_norm | 0.00% | 10.00% | 0.00% | 0.32411559 |
| E_clean | B3v3 | v_reg | 10.00% | 20.00% | 0.00% | 0.14851773 |
| E_clean | B3v3 | v_reg_self | 4.44% | 10.00% | 0.00% | 0.07304445 |
| E_clean | B3v3 | u_e2 | 4.44% | 10.00% | 0.00% | 3.75624049 |
| E_clean | B3v3 | u_reg_signed | 0.00% | 10.00% | 0.00% | 0.03937841 |
| E_clean | B3v3 | u_reg_clipped | 1.11% | 10.00% | 0.00% | 0.07256364 |
| E_jitter8 | B3v3 | v_e2 | 14.00% | 55.00% | 0.00% | 10.24584649 |
| E_jitter8 | B3v3 | v_norm | 3.11% | 100.00% | 0.00% | 0.32411559 |
| E_jitter8 | B3v3 | v_reg | 10.00% | 51.00% | 0.00% | 0.14851773 |
| E_jitter8 | B3v3 | v_reg_self | 6.56% | 68.00% | 0.00% | 0.07304445 |
| E_jitter8 | B3v3 | u_e2 | 8.89% | 13.00% | 0.00% | 3.75624049 |
| E_jitter8 | B3v3 | u_reg_signed | 1.11% | 37.00% | 0.00% | 0.03937841 |
| E_jitter8 | B3v3 | u_reg_clipped | 2.44% | 21.00% | 0.00% | 0.07256364 |
| S1_CF0_CF21 | B3v3 | v_e2 | 1.10% | 7.14% | 1.10% | 10.24584649 |
| S1_CF0_CF21 | B3v3 | v_norm | 0.00% | 0.00% | 6.04% | 0.32411559 |
| S1_CF0_CF21 | B3v3 | v_reg | 0.00% | 0.00% | 2.20% | 0.14851773 |
| S1_CF0_CF21 | B3v3 | v_reg_self | 0.00% | 0.00% | 0.00% | 0.07304445 |
| S1_CF0_CF21 | B3v3 | u_e2 | 0.00% | 0.00% | 0.00% | 3.75624049 |
| S1_CF0_CF21 | B3v3 | u_reg_signed | 0.00% | 0.00% | 0.00% | 0.03937841 |
| S1_CF0_CF21 | B3v3 | u_reg_clipped | 0.00% | 0.00% | 0.00% | 0.07256364 |
| S1_CF0_CF21 | B6v6 | v_e2 | 1.10% | 7.14% | 0.00% | 8.12865437 |
| S1_CF0_CF21 | B6v6 | v_norm | 0.00% | 0.00% | 0.00% | 0.22149346 |
| S1_CF0_CF21 | B6v6 | v_reg | 0.00% | 0.00% | 0.00% | 0.11309983 |
| S1_CF0_CF21 | B6v6 | v_reg_self | 0.00% | 0.00% | 0.00% | 0.06083043 |
| S1_CF0_CF21 | B6v6 | u_e2 | 0.00% | 0.00% | 0.00% | 3.83722899 |
| S1_CF0_CF21 | B6v6 | u_reg_signed | 0.00% | 0.00% | 0.00% | 0.05347355 |
| S1_CF0_CF21 | B6v6 | u_reg_clipped | 0.00% | 0.00% | 0.00% | 0.05897198 |
| S1_CF21_OR21 | B3v3 | v_e2 | 0.00% | 0.00% | 0.00% | 10.24584649 |
| S1_CF21_OR21 | B3v3 | v_norm | 0.00% | 0.00% | 4.40% | 0.32411559 |
| S1_CF21_OR21 | B3v3 | v_reg | 0.00% | 0.00% | 0.55% | 0.14851773 |
| S1_CF21_OR21 | B3v3 | v_reg_self | 0.00% | 0.00% | 0.55% | 0.07304445 |
| S1_CF21_OR21 | B3v3 | u_e2 | 0.55% | 14.29% | 0.00% | 3.75624049 |
| S1_CF21_OR21 | B3v3 | u_reg_signed | 0.00% | 21.43% | 0.00% | 0.03937841 |
| S1_CF21_OR21 | B3v3 | u_reg_clipped | 0.55% | 0.00% | 0.55% | 0.07256364 |
| S1_CF21_OR21 | B6v6 | v_e2 | 0.00% | 21.43% | 0.00% | 8.12865437 |
| S1_CF21_OR21 | B6v6 | v_norm | 0.00% | 7.14% | 0.00% | 0.22149346 |
| S1_CF21_OR21 | B6v6 | v_reg | 0.00% | 7.14% | 0.00% | 0.11309983 |
| S1_CF21_OR21 | B6v6 | v_reg_self | 0.00% | 0.00% | 0.55% | 0.06083043 |
| S1_CF21_OR21 | B6v6 | u_e2 | 0.55% | 14.29% | 0.00% | 3.83722899 |
| S1_CF21_OR21 | B6v6 | u_reg_signed | 0.00% | 0.00% | 0.00% | 0.05347355 |
| S1_CF21_OR21 | B6v6 | u_reg_clipped | 0.55% | 7.14% | 0.00% | 0.05897198 |
| S1_CF0_OR21 | B3v3 | v_e2 | 7.14% | 7.14% | 0.00% | 10.24584649 |
| S1_CF0_OR21 | B3v3 | v_norm | 0.00% | 0.00% | 2.20% | 0.32411559 |
| S1_CF0_OR21 | B3v3 | v_reg | 0.00% | 0.00% | 0.55% | 0.14851773 |
| S1_CF0_OR21 | B3v3 | v_reg_self | 0.00% | 0.00% | 0.00% | 0.07304445 |
| S1_CF0_OR21 | B3v3 | u_e2 | 0.00% | 7.14% | 0.00% | 3.75624049 |
| S1_CF0_OR21 | B3v3 | u_reg_signed | 0.00% | 14.29% | 0.00% | 0.03937841 |
| S1_CF0_OR21 | B3v3 | u_reg_clipped | 0.00% | 0.00% | 0.00% | 0.07256364 |
| S1_CF0_OR21 | B6v6 | v_e2 | 7.14% | 7.14% | 0.00% | 8.12865437 |
| S1_CF0_OR21 | B6v6 | v_norm | 0.00% | 0.00% | 0.00% | 0.22149346 |
| S1_CF0_OR21 | B6v6 | v_reg | 0.00% | 7.14% | 0.00% | 0.11309983 |
| S1_CF0_OR21 | B6v6 | v_reg_self | 0.00% | 0.00% | 0.00% | 0.06083043 |
| S1_CF0_OR21 | B6v6 | u_e2 | 0.00% | 7.14% | 0.00% | 3.83722899 |
| S1_CF0_OR21 | B6v6 | u_reg_signed | 0.00% | 0.00% | 0.00% | 0.05347355 |
| S1_CF0_OR21 | B6v6 | u_reg_clipped | 0.00% | 7.14% | 0.00% | 0.05897198 |

Jitter rows average ten fixed seeds on the same response pool to evaluate coordinate perturbation sensitivity.

Benchmark cross-checks are copied from frozen results/benchmark JSON with their original protocol and thresholds, while Table S9 evaluates V and U estimators over identical n_c, m_c >= 2 cells. Under regularized energy, all three B-full directional-shift/quantization rows retain 0.00% re-swept EER and 0.00% frozen FAR while crossing clean frozen cutoffs (100.00% flagging rate).

Implementation checks enumerate 32 IID Bernoulli sample outcomes to verify the null expectations, exhibit negative U values and clipping bias, reject n=1, and compare V against the canonical implementation on 100 random pairs. Protected source/log hashes are checked before and after the run.
