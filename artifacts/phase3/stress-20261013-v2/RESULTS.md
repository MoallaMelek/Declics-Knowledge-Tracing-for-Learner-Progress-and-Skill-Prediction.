# Frozen-model stress diagnostic

This is a fixed-checkpoint diagnostic on split 2026, not real musical validation or an exercise-disjoint fit. No model was retrained. Clean targets remain unchanged; dropout compares identical retained targets. Arbitrary 10/25 percent history-error and 30 percent dropout rates do not estimate real upstream error rates. The global-history logistic control is exploratory and separately identified.

| Domain | Model | Condition | Targets | Raw log loss | Delta vs same clean targets | Paired delta 95% |
|---|---|---|---|---|---|---|
| forget-se | dkt-7 | clean | 1683 | 0.592587 | +0.000000 | [+0.000000, +0.000000] |
| forget-se | dkt-7 | history_noise_10 | 1683 | 0.596247 | +0.003659 | [-0.004775, +0.010869] |
| forget-se | dkt-7 | history_noise_25 | 1683 | 0.615080 | +0.022493 | [+0.008611, +0.034718] |
| forget-se | dkt-7 | history_dropout_30 | 1157 | 0.613980 | +0.016119 | [+0.003855, +0.028143] |
| forget-se | dkt-7 | unknown_item_query | 1683 | 0.592587 | +0.000000 | [+0.000000, +0.000000] |
| forget-se | enhanced_gru-7 | clean | 1683 | 0.557586 | +0.000000 | [+0.000000, +0.000000] |
| forget-se | enhanced_gru-7 | history_noise_10 | 1683 | 0.559301 | +0.001715 | [-0.009274, +0.011406] |
| forget-se | enhanced_gru-7 | history_noise_25 | 1683 | 0.569274 | +0.011688 | [-0.003103, +0.023346] |
| forget-se | enhanced_gru-7 | history_dropout_30 | 1157 | 0.565864 | +0.007547 | [-0.002181, +0.018266] |
| forget-se | enhanced_gru-7 | unknown_item_query | 1683 | 0.647278 | +0.089693 | [+0.077498, +0.102561] |
| forget-se | item_pfa-0 | clean | 1683 | 0.593286 | +0.000000 | [+0.000000, +0.000000] |
| forget-se | item_pfa-0 | history_noise_10 | 1683 | 0.593039 | -0.000247 | [-0.004940, +0.004606] |
| forget-se | item_pfa-0 | history_noise_25 | 1683 | 0.594286 | +0.001000 | [-0.004362, +0.006974] |
| forget-se | item_pfa-0 | history_dropout_30 | 1157 | 0.587265 | -0.001483 | [-0.004508, +0.002292] |
| forget-se | item_pfa-0 | unknown_item_query | 1683 | 0.669617 | +0.076331 | [+0.060014, +0.092675] |
| forget-se | global_history_logistic | clean | 1683 | 0.563130 | +0.000000 | [+0.000000, +0.000000] |
| forget-se | global_history_logistic | history_noise_10 | 1683 | 0.565951 | +0.002821 | [-0.005354, +0.009532] |
| forget-se | global_history_logistic | history_noise_25 | 1683 | 0.567550 | +0.004420 | [-0.007494, +0.013926] |
| forget-se | global_history_logistic | history_dropout_30 | 1157 | 0.564994 | +0.006115 | [-0.001177, +0.014783] |
| forget-se | global_history_logistic | unknown_item_query | 1683 | 0.644426 | +0.081296 | [+0.067873, +0.096176] |
| music-mock | dkt-7 | clean | 2615 | 0.631374 | +0.000000 | [+0.000000, +0.000000] |
| music-mock | dkt-7 | history_noise_10 | 2615 | 0.638279 | +0.006905 | [+0.003398, +0.010626] |
| music-mock | dkt-7 | history_noise_25 | 2615 | 0.647460 | +0.016086 | [+0.008262, +0.024084] |
| music-mock | dkt-7 | history_dropout_30 | 1787 | 0.635879 | +0.006331 | [-0.001022, +0.011773] |
| music-mock | dkt-7 | unknown_item_query | 2615 | 0.631374 | +0.000000 | [+0.000000, +0.000000] |
| music-mock | enhanced_gru-7 | clean | 2615 | 0.623680 | +0.000000 | [+0.000000, +0.000000] |
| music-mock | enhanced_gru-7 | history_noise_10 | 2615 | 0.632158 | +0.008478 | [+0.004563, +0.012859] |
| music-mock | enhanced_gru-7 | history_noise_25 | 2615 | 0.641655 | +0.017975 | [+0.010056, +0.027639] |
| music-mock | enhanced_gru-7 | history_dropout_30 | 1787 | 0.630841 | +0.009785 | [+0.002234, +0.016382] |
| music-mock | enhanced_gru-7 | unknown_item_query | 2615 | 0.630620 | +0.006940 | [+0.001038, +0.013383] |
| music-mock | item_pfa-0 | clean | 2615 | 0.619393 | +0.000000 | [+0.000000, +0.000000] |
| music-mock | item_pfa-0 | history_noise_10 | 2615 | 0.629486 | +0.010093 | [+0.006008, +0.014367] |
| music-mock | item_pfa-0 | history_noise_25 | 2615 | 0.641402 | +0.022009 | [+0.014515, +0.030981] |
| music-mock | item_pfa-0 | history_dropout_30 | 1787 | 0.630583 | +0.013063 | [+0.007505, +0.018076] |
| music-mock | item_pfa-0 | unknown_item_query | 2615 | 0.618810 | -0.000583 | [-0.002222, +0.001300] |
| music-mock | global_history_logistic | clean | 2615 | 0.620713 | +0.000000 | [+0.000000, +0.000000] |
| music-mock | global_history_logistic | history_noise_10 | 2615 | 0.629307 | +0.008594 | [+0.004293, +0.012988] |
| music-mock | global_history_logistic | history_noise_25 | 2615 | 0.641133 | +0.020420 | [+0.012682, +0.028774] |
| music-mock | global_history_logistic | history_dropout_30 | 1787 | 0.631503 | +0.012987 | [+0.007327, +0.018203] |
| music-mock | global_history_logistic | unknown_item_query | 2615 | 0.620234 | -0.000480 | [-0.002326, +0.001626] |

History noise generally degrades these fixed forecasts, with statistical controls sometimes less sensitive in this cohort. Unknown-item substitution materially raises loss for item-aware models on FORGET-SE; DKT is item-blind and stays unchanged. In synthetic music, unknown-item effects are much smaller and can be slightly favorable for statistical controls. These negative findings reinforce abstention and task-specific validation rather than a universal neural-superiority claim.

Cold-start slices, source hashes and all per-target predictions are included in summary.json and the adjacent immutable diagnostic files. Previous 102-run study bytes remain unchanged.