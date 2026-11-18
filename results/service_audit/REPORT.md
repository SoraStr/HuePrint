# Offline Service-Audit Analyses

All outputs are new. Original responses and prior frozen results remain untouched. No model/API calls.

## Same-family negative pairs

Pairs are distinct declared labels within a versioned family/vendor map, not verified or ordered tier downgrades. B rows are calibration resubstitution; A/B share 480 original responses, so A is not an independent calibration holdout. Threshold transfers to other cohorts can mismatch sample sizes.

| Cohort | Same-family negatives | Energy EER | Frozen FAR / FRR | Hybrid EER |
| --- | ---: | ---: | ---: | ---: |
| A_fresh | 604 | 10.10% | 1.32% / 51.79% | 12.42% |
| B20x6 | 20 | 0.00% | 0.00% / 0.00% | 0.00% |
| B_full | 20 | 0.00% | 0.00% / 0.00% | 0.00% |
| E | 20 | 10.00% | 0.00% / 30.00% | 10.00% |
| S3_color_within | 38 | 0.00% | 0.00% / 0.00% | 5.00% |

## Offline mixed routing

Twenty fixed seeds; 5–95% ranges quantify simulation variability, not confidence intervals over independent deployments. p=1 is genuine rejection. The simulation does not establish a universal sample requirement for 20% fallback.

| Protocol | Query calls | Detection at 20% fallback | Seed range | Pure-clean FRR |
| --- | ---: | ---: | ---: | ---: |
| B20_q3 | 60 | 11.28% | 4.39%–20.11% | 1.00% |
| B40_q7 | 280 | 0.33% | 0.00%–1.17% | 0.00% |
| S3_10_q3 | 30 | 55.97% | 51.25%–61.11% | 39.00% |
| S3_10_q7 | 70 | 12.45% | 7.83%–16.14% | 3.75% |

Full probability grids, subgroup values and per-pair simulation outcomes are in routing.csv/routing_seeds.csv/routing_pairs.csv.

## Operational overhead

Usage and per-request latency come from immutable logs, including invalid responses. No billed dollar cost is recorded. Cost formula: (input_tokens * input_USD_per_M + output_tokens * output_USD_per_M)/1e6. The 1/5 USD-per-million column is an explicitly hypothetical price scenario, not an invoice or verified vendor rate; no cached-input discount assumed. Enrollment and subsequent query costs are separate. Timestamps are completion times and collection spans include scheduling and retry gaps. Concurrency estimates replay recorded request durations in deterministic list order on ideal c workers, assuming duration independence and zero dispatch overhead; these are not measured concurrent audit wall times.

Two common-rate scenarios additionally use the saved OpenRouter catalog snapshot accessed 2026-11-13: GPT-4o input/output $2.50/$10 per million, and Llama-3.3 input/output $0.71/$0.71 per million. These are current catalog rate scenarios, not the actual aliases' rates, minimum-provider quotes or historical bills. No cached-input discount is applied.

| Query cohort | Median calls | Median input/output tokens | Median GPT-4o-rate USD | Median Llama-rate USD | Estimated c=8 seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| B20x6 | 60 | 4798.5 / 560.0 | 0.01877 | 0.00425 | 61.14 |
| E20x6 | 60 | 4126.5 / 450.0 | 0.01643 | 0.00341 | 48.91 |
| S1_CF21 | 120 | 9222.0 / 980.0 | 0.03574 | 0.00847 | 59.49 |
| S1_OR21 | 120 | 8848.5 / 1016.0 | 0.03674 | 0.00765 | 68.60 |
| S3_color | 150 | 9840.0 / 1091.5 | 0.03449 | 0.00769 | 116.25 |
| S3_word | 150 | 7051.5 / 381.5 | 0.02184 | 0.00540 | 104.39 |
| S4a | 80 | 5502.5 / 1860.5 | 0.03186 | 0.00513 | 56.35 |

Each column summarizes target-level values independently. Enrollment is separate in overhead_per_target.csv. Formula-based price scenarios must not be described as measured billed costs. Concurrent times are ideal scheduling estimates, not actual concurrent audit measurements.

## Local timing

Measured wall time of already-loaded one-reference/one-query scoring only, warm-up excluded. Includes per-cell distance calculation and, for permutation, 999 null samples and aggregation. Excludes API/network, parsing, disk I/O, enrollment and full all-pairs search; hardware/load-dependent.

| Budget | Method | Median ms | P95 ms |
| --- | --- | ---: | ---: |
| 20 cells, 3v3 | regularized_energy | 0.124 | 0.147 |
| 20 cells, 3v3 | stratified_energy_999_permutations | 2.393 | 2.566 |
| 40 cells, 8v7 | regularized_energy | 0.315 | 0.356 |
| 40 cells, 8v7 | stratified_energy_999_permutations | 10.147 | 10.406 |
| 10 cells, 8v7 | regularized_energy | 0.077 | 0.084 |
| 10 cells, 8v7 | stratified_energy_999_permutations | 2.511 | 2.660 |
