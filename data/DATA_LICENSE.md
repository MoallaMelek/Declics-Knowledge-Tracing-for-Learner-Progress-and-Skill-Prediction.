# FORGET-SE v1 attribution and provenance

Sha, Alyssa; Pereira Nunes, Bernardo (2025). *FORGET-SE: A Dataset for Analysing Memory Decay and Interference in Software Engineering Knowledge Tracing*. figshare. https://doi.org/10.6084/m9.figshare.29146304.v1

Official card and release: https://figshare.com/articles/dataset/29146304
Metadata: https://api.figshare.com/v2/articles/29146304
CSV: https://ndownloader.figshare.com/files/54819392
License: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/

Original CSV is unchanged, 256876 bytes; MD5 f7d297747eda7d5cd0a704a1b710df5d. Metadata snapshot retained. Download audit on 2026-10-06: 10873 rows, 186 learners, 56 qid, 10 sequence_id. 5999 full scores, 4145 zero, 729 partial. 383 tied learner/log_id groups contain 949 rows. Original file has 514 within-user backwards log transitions; sort numerically per learner. Numeric log_id is deidentified timestamp/order, not seconds or calendar dates. No gaps or forgetting rate inferred.

Modification for binary experiment: define full credit as score >= 1-1e-8, fixed before model fitting; preserve original continuous score in evidence; group all learner/log_id ties before sequence construction and predict every original observation from the pre-group state. Duplicate KCs within a group retain separate labels and equal observation weight. No labels inside the group enter its own forecasts. Sequence IDs use declared ten-concept ontology; human concept names not supplied, so UI uses Concept SE 1–10. No fictitious music mapping.

CC BY applies to this original released data. The release does not establish musical relevance, exact clock units, or teaching benefit. Synthetic music is generated locally and has a separate manifest. SingKT/OcarinaKT recordings or logs are not included: reuse permissions unresolved. Project source files are preserved in the supplied folder and not redistributed by this repository.
