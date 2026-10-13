# Actual repeated-split experiment results

Experiment `axis7-v2-20261013-controlled`. Raw forecasts primary; separate temperature calibration secondary.

| Domain | Model | Runs | Mean AUC | Mean raw log loss | Split SD log loss | Mean calibrated log loss |
|---|---|---:|---:|---:|---:|---:|
| forget-se | bkt | 3 | 0.5969 | 0.6609 | 0.0063 | 0.6614 |
| forget-se | dkt | 6 | 0.7203 | 0.6066 | 0.0119 | 0.6085 |
| forget-se | enhanced_gru | 6 | 0.7610 | 0.5689 | 0.0106 | 0.5709 |
| forget-se | enhanced_gru_no_outcome | 6 | 0.7237 | 0.6045 | 0.0057 | 0.6101 |
| forget-se | exposure | 3 | 0.6014 | 0.6695 | 0.0069 | 0.6778 |
| forget-se | item_attention | 6 | 0.7263 | 0.6004 | 0.0169 | 0.6020 |
| forget-se | item_attention_no_item | 6 | 0.6860 | 0.6269 | 0.0229 | 0.6310 |
| forget-se | item_pfa | 3 | 0.7266 | 0.5980 | 0.0044 | 0.6017 |
| forget-se | pfa | 3 | 0.5915 | 0.6680 | 0.0094 | 0.6685 |
| forget-se | prior | 3 | 0.5808 | 0.6753 | 0.0111 | 0.6858 |
| forget-se | sakt | 6 | 0.7124 | 0.6128 | 0.0132 | 0.6144 |
| music-mock | bkt | 3 | 0.6831 | 0.6247 | 0.0033 | 0.6245 |
| music-mock | dkt | 6 | 0.6609 | 0.6353 | 0.0041 | 0.6351 |
| music-mock | enhanced_gru | 6 | 0.6802 | 0.6270 | 0.0033 | 0.6266 |
| music-mock | enhanced_gru_no_outcome | 6 | 0.6240 | 0.6541 | 0.0051 | 0.6546 |
| music-mock | exposure | 3 | 0.5783 | 0.6685 | 0.0056 | 0.6689 |
| music-mock | item_attention | 6 | 0.6456 | 0.6461 | 0.0016 | 0.6457 |
| music-mock | item_attention_no_item | 6 | 0.6730 | 0.6321 | 0.0006 | 0.6306 |
| music-mock | item_pfa | 3 | 0.6928 | 0.6196 | 0.0039 | 0.6194 |
| music-mock | pfa | 3 | 0.6933 | 0.6191 | 0.0040 | 0.6189 |
| music-mock | prior | 3 | 0.4957 | 0.6773 | 0.0048 | 0.6785 |
| music-mock | sakt | 6 | 0.5797 | 0.6711 | 0.0027 | 0.6687 |

Every selected winner comes from validation loss, not this descriptive table. See per-split results for paired learner intervals against the validation-selected strongest statistical control. No winning claim is guaranteed.

FORGET-SE is software engineering, not musical transfer.
Music-mock is synthetic, not learner validation.
Repeated splits overlap learners: split SD is descriptive, not three independent population replications.
Bootstrap conditions on a fitted checkpoint and test learner set.
Item forecasts condition atomic bundles, not individual note difficulty.
No real elapsed-time features, unmeasured learning gains, or invented prerequisites.