# Reference Metadata Audit (33-Reference Inventory)

Verified inventory of all 33 bibliography entries (`[1]`–`[30]` in the main manuscript; `[4]`, `[16]`, `[25]`–`[30]`, and `[31]`–`[33]` in the Supplementary Material, where `[31]`–`[33]` are supplement-only). Sequential first-appearance order `[1]`–`[30]` is enforced in `paper/ieee/body.tex`, and structured BibTeX entries `ref1`–`ref33` are maintained in `paper/references.bib`.

## Main Manuscript References (`[1]`–`[30]`)

### [1] FrugalGPT: How to use large language models while reducing cost and improving performance
- **Authors**: L. Chen, M. Zaharia, and J. Zou
- **Venue**: *Transactions on Machine Learning Research*, Dec. 2024
- **Status**: Verified TMLR publication; cited for cost-quality LLM cascades (`Section 1`, `Section 2.1`, `Section 2.2`, `Section 7.1`).

### [2] RouteLLM: Learning to route LLMs from preference data
- **Authors**: I. Ong, A. Almahairi, V. Wu, W.-L. Chiang, T. Wu, J. E. Gonzalez, M. W. Kadous, and I. Stoica
- **Venue**: in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, 2025, pp. 34433–34448
- **Status**: Verified ICLR 2025 proceedings; cited for preference-trained LLM routing (`Section 1`, `Section 2.1`, `Section 2.2`, `Section 7.1`).

### [3] QoS-aware brokering for LLM-as-a-Service: SLA-constrained routing with drift detection
- **Authors**: O. Tibermacine and C. Tibermacine
- **Venue**: in *Proc. IEEE Int. Conf. Web Services (ICWS)*, 2026, pp. 925–933, doi: `10.1109/ICWS72778.2026.00112`
- **Status**: Verified IEEE ICWS 2026 proceedings and DOI; cited for SLA-constrained LLM brokering (`Section 1`, `Section 2.1`).

### [4] Model equality testing: Which model is this API serving?
- **Authors**: I. Gao, P. Liang, and C. Guestrin
- **Venue**: in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, 2025, pp. 86369–86382
- **Status**: Verified ICLR 2025 proceedings (`pp. 86369–86382`); cited for black-box output-distribution equality testing, adapted one-hot string MMD / $L_1$ baselines, and Study S5b native long-form continuation MMD benchmark (`Section 1`, `Section 2.1`, `Section 3.5`, `Section 5.2`, `Supplement M`).

### [5] Are you getting what you pay for? Auditing model substitution in LLM APIs
- **Authors**: W. Cai, T. Shi, X. Zhao, and D. Song
- **Venue**: *arXiv preprint arXiv:2504.04715*, Sep. 2025
- **Status**: Verified arXiv v2 preprint (`Sep. 2025`); cited for auditing model substitution vs. benign serving nondeterminism, adaptive routing evasion, and TEE hardware attestation (`Section 1`, `Section 2.1`, `Section 7.1`).

### [6] Auditing black-box LLM APIs with a rank-based uniformity test
- **Authors**: X. Zhu, Y. Ye, T. Qiu, H. Zhu, S. Tan, A. Mannan, J. Michala, R. A. Popa, and W. Neiswanger
- **Venue**: in *Proc. 14th Int. Conf. Learning Representations (ICLR)*, 2026
- **Status**: Verified ICLR 2026 peer-reviewed publication (upgraded from `arXiv:2506.06975`); in-text claim verified as black-box API rank-uniformity auditing using white-box reference probabilities (`Section 1`, `Section 2.1`).

### [7] One token is enough: Fingerprinting and verifying large language models from single-token output distributions
- **Authors**: T. Bruckner
- **Venue**: *arXiv preprint arXiv:2607.10252*, Jul. 2026
- **Status**: Verified arXiv preprint; cited for single-word categorical distribution baseline (40 multilingual prompts, 165 models, 7.3% EER; `Section 1`, `Section 2.1`).

### [8] RESTLess: Enhancing state-of-the-art REST API fuzzing with LLMs in cloud service computing
- **Authors**: T. Zheng, J. Shao, J. Dai, S. Jiang, X. Chen, and C. Shen
- **Venue**: *IEEE Trans. Services Computing*, vol. 17, no. 6, pp. 4225–4238, Nov.–Dec. 2024, doi: `10.1109/TSC.2024.3489441`
- **Status**: Verified IEEE TSC publication and DOI (`Section 2.1`).

### [9] UAC-AD: Unsupervised adversarial contrastive learning for anomaly detection on multi-modal data in microservice systems
- **Authors**: H. Liu, X. Huang, M. Jia, T. Jia, J. Han, Z. Wu, and Y. Li
- **Venue**: *IEEE Trans. Services Computing*, vol. 17, no. 6, pp. 3887–3900, Nov.–Dec. 2024, doi: `10.1109/TSC.2024.3411481`
- **Status**: Verified IEEE TSC publication and DOI (`Section 2.1`).

### [10] Concept drift-based checkpoint-restart for edge services rejuvenation
- **Authors**: L. Wang, J. Liu, and Q. He
- **Venue**: *IEEE Trans. Services Computing*, vol. 16, no. 3, pp. 1713–1725, May–Jun. 2023, doi: `10.1109/TSC.2022.3210086`
- **Status**: Verified IEEE TSC publication and DOI (`Section 2.1`).

### [11] A watermark for large language models
- **Authors**: J. Kirchenbauer, J. Geiping, Y. Wen, J. Katz, I. Miers, and T. Goldstein
- **Venue**: in *Proc. 40th Int. Conf. Machine Learning (ICML)*, vol. 202 of *PMLR*, 2023, pp. 17061–17084
- **Status**: Verified ICML / PMLR vol. 202 (`Section 2.1`).

### [12] Instructional fingerprinting of large language models
- **Authors**: J. Xu, F. Wang, M. D. Ma, P. W. Koh, C. Xiao, and M. Chen
- **Venue**: in *Proc. Conf. North American Chapter Assoc. Computational Linguistics (NAACL-HLT)*, 2024, pp. 3277–3306
- **Status**: Verified NAACL-HLT 2024 proceedings (`Section 2.1`).

### [13] FIT-Print: Toward false-claim-resistant model ownership verification via targeted fingerprint
- **Authors**: S. Shao, H. Zhu, Y. Li, H. Yao, T. Zhang, and Z. Qin
- **Venue**: *IEEE Trans. Inf. Forensics Security*, vol. 21, pp. 5612–5626, 2026, doi: `10.1109/TIFS.2026.3702542`
- **Status**: Verified IEEE TIFS vol. 21 and DOI; cited for targeted IP ownership-verification fingerprints addressing model-theft disputes rather than live MaaS endpoint consistency monitoring (`Section 2.1`).

### [14] Authorship attribution for neural text generation
- **Authors**: A. Uchendu, T. Le, K. Shu, and D. Lee
- **Venue**: in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, 2020, pp. 8384–8395
- **Status**: Verified EMNLP 2020 proceedings (`Section 2.1`).

### [15] Idiosyncrasies in large language models
- **Authors**: M. Sun, Y. Yin, Z. Xu, J. Z. Kolter, and Z. Liu
- **Venue**: in *Proc. 42nd Int. Conf. Machine Learning (ICML)*, vol. 267 of *PMLR*, 2025, pp. 57854–57885
- **Status**: Verified ICML 2025 / PMLR vol. 267 (`Section 2.1`).

### [16] LLMmap: Fingerprinting for large language models
- **Authors**: D. Pasquini, E. M. Kornaropoulos, and G. Ateniese
- **Venue**: in *Proc. 34th USENIX Security Symp. (USENIX Security 25)*, 2025, pp. 299–318
- **Status**: Verified USENIX Security 2025 proceedings pagination `pp. 299–318`; cited for active black-box LLM fingerprinting and Study S5a open-set parity benchmark (`Section 1`, `Section 2.1`, `Section 5.2`, `Section 6.4`, `Supplement M`).

### [17] TRAP: Targeted random adversarial prompt honeypot for black-box identification
- **Authors**: M. Gubri, D. Ulmer, H. Lee, S. Yun, and S. J. Oh
- **Venue**: in *Findings of the Assoc. Computational Linguistics: ACL 2024*, 2024, pp. 11496–11517
- **Status**: Verified Findings of ACL 2024 (`Section 2.1`).

### [18] Can LLMs generate random numbers? Evaluating LLM sampling in controlled domains
- **Authors**: A. K. Hopkins, A. Renda, and M. Carbin
- **Venue**: in *ICML Workshop on Sampling and Optimization in Discrete Space (SODS)*, 2023
- **Status**: Verified author order (`A. K. Hopkins, A. Renda, and M. Carbin`); cited for biased LLM sampling priors (`Section 2.1`).

### [19] Heads, tails, and AI fails: LLMs, randomness, and human judgments
- **Authors**: K. Van Koevering and J. Kleinberg
- **Venue**: *arXiv preprint arXiv:2406.00092*, Oct. 2026
- **Status**: Updated to latest arXiv v2 title and date (`Oct. 2026`); cited for biased LLM random-generation priors (`Section 2.1`).

### [20] A comparison of large language model and human performance on random number generation tasks
- **Authors**: R. M. Harrison
- **Venue**: *arXiv preprint arXiv:2408.09656*, Aug. 2024
- **Status**: Verified arXiv preprint; cited for biased LLM random-number generation (`Section 2.1`).

### [21] Deterministic or probabilistic? The psychology of LLMs as random number generators
- **Authors**: J. Coronado-Blázquez
- **Venue**: *arXiv preprint arXiv:2502.19965*, Feb. 2025
- **Status**: Verified arXiv preprint; cited for biased LLM random-number generation (`Section 2.1`).

### [22] Picking on the same person: Does algorithmic monoculture lead to outcome homogenization?
- **Authors**: R. Bommasani, K. A. Creel, A. Kumar, D. Jurafsky, and P. Liang
- **Venue**: in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 35, pp. 3663–3678, 2022
- **Status**: Verified NeurIPS 2022 vol. 35 pagination `pp. 3663–3678`; cited for shared-component outcome correlation across deployments (`Section 2.1`).

### [23] Algorithmic monoculture and social welfare
- **Authors**: J. Kleinberg and M. Raghavan
- **Venue**: *Proc. National Academy of Sciences (PNAS)*, vol. 118, no. 22, p. e2018340118, 2021
- **Status**: Verified PNAS vol. 118 no. 22 article `e2018340118`; cited for algorithmic monoculture across deployments (`Section 2.1`).

### [24] Thinking inertia: LLMs keep thinking when told not to
- **Authors**: D. Lei, K. Q. Lin, P. Lu, P. Torr, and J. Zou
- **Venue**: in *Advances in Neural Information Processing Systems (NeurIPS)*, 2026 (`arXiv:2610.11765`)
- **Status**: Verified NeurIPS 2026 accepted paper (`arXiv:2610.11765v2`); cited for visible pre-answer reasoning leakage under disabled thinking and answer-only directives across open answer spaces (`Section 2.1`, `Section 4`).

### [25] Multimedia Systems and Equipment — Colour Measurement and Management — Part 2-1: Colour Management — Default RGB Colour Space — sRGB
- **Authors**: International Electrotechnical Commission
- **Venue**: Standard IEC 61966-2-1:1999, 1999
- **Status**: Verified IEC standard; cited in main manuscript (`Section 3.1`) and supplement (`Supplement A`).

### [26] Divergence measures based on the Shannon entropy
- **Authors**: J. Lin
- **Venue**: *IEEE Trans. Inf. Theory*, vol. 37, no. 1, pp. 145–151, Jan. 1991
- **Status**: Verified IEEE TIT publication; cited in main manuscript (`Section 3.2`) and supplement (`Supplement G`).

### [27] Energy statistics: A class of statistics based on distances
- **Authors**: G. J. Székely and M. L. Rizzo
- **Venue**: *J. Stat. Plan. Inference*, vol. 143, no. 8, pp. 1249–1272, 2013
- **Status**: Verified JSPI publication; cited in main manuscript (`Section 3.3`) and supplement (`Supplement A`, `Supplement G`).

### [28] Testing for equal distributions in high dimension
- **Authors**: G. J. Székely and M. L. Rizzo
- **Venue**: *InterStat*, no. 5, pp. 1–16, Nov. 2004
- **Status**: Verified InterStat publication; cited in main manuscript (`Section 3.3`, `Section 3.5`) and supplement (`Supplement G`, `Supplement K`).

### [29] On the Bures–Wasserstein distance between positive definite matrices
- **Authors**: R. Bhatia, T. Jain, and Y. Lim
- **Venue**: *Expositiones Mathematicae*, vol. 37, no. 2, pp. 165–191, 2019
- **Status**: Verified publication; cited for the positive-definite covariance term in main manuscript (`Section 3.3`) and supplement (`Supplement G`).

### [30] Models API: Public model catalog and pricing
- **Authors**: OpenRouter
- **Venue**: `https://openrouter.ai/api/v1/models`, accessed Nov. 13 and Nov. 20, 2026 (archived offline)
- **Status**: Verified archived pricing snapshots; cited in main manuscript (`Section 5.2`, `Section 6.4`) and supplement (`Supplement K`, `Supplement M`).

## Supplement-Only References (`[31]`–`[33]`)

### [31] CSS Color Module Level 4
- **Authors**: World Wide Web Consortium
- **Venue**: Candidate Recommendation Draft, Nov. 3, 2026, sec. 19, "Sample code for color conversions"
- **Status**: Verified W3C CRD specification; cited in `Supplement A` (sRGB-to-CIELAB conversion).

### [32] CIE 1976 L\*a\*b\* colour space
- **Authors**: International Commission on Illumination
- **Venue**: *International Lighting Vocabulary*, 2nd ed., CIE S 017:2020, entry 17-23-076, 2020
- **Status**: Verified CIE standard entry; cited in `Supplement A` (CIELAB coordinate definition).

### [33] Information-type measures of difference of probability distributions and indirect observations
- **Authors**: I. Csiszár
- **Venue**: *Studia Sci. Math. Hungar.*, vol. 2, pp. 299–318, 1967
- **Status**: Verified exact plural title (`observations`) and pagination; cited in `Supplement G` (Proposition 1 proof, $f$-divergence data processing inequality).
