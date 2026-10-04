# Sweep Comparison

## Per-Round Fits

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2. Postselected series are excluded (their kept fraction changes with r).

| Label | Basis | Fit points | Error per round | 1-sigma | Amplitude A | Excluded points |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | memory_x | 4 | 0.0916058 | 0.00254422 | 1 | 0 |
| baseline | memory_z | 4 | 0.0679715 | 0.00195352 | 1 | 0 |
| in_sample_improved | memory_x | 4 | 0.0808433 | 0.0022731 | 1 | 0 |
| in_sample_improved | memory_z | 4 | 0.0629115 | 0.00183416 | 1 | 0 |
| kfold | memory_x | 4 | 0.0833721 | 0.00233418 | 1 | 0 |
| kfold | memory_z | 4 | 0.0642534 | 0.0018657 | 1 | 0 |
| postselect_q25 | memory_x | 0 |  |  |  | 4 |
| postselect_q25 | memory_z | 0 |  |  |  | 4 |

## Sweep Rows

| Label | Basis | Rounds | LER | 68% Wilson interval | Per-round LER | Mean detector rate | Kept fraction | Failures | Shots |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | memory_x | 1 | 0.0825 | 0.07655–0.08886 | 0.0825 | 0.146625 | 1 | 165 | 2000 |
| baseline | memory_x | 3 | 0.219 | 0.2099–0.2284 | 0.0873814 | 0.203146 | 1 | 438 | 2000 |
| baseline | memory_x | 5 | 0.3205 | 0.3102–0.331 | 0.0926301 | 0.213012 | 1 | 641 | 2000 |
| baseline | memory_x | 7 | 0.3995 | 0.3886–0.4105 | 0.102418 | 0.217723 | 1 | 799 | 2000 |
| baseline | memory_z | 1 | 0.047 | 0.04249–0.05196 | 0.047 | 0.1385 | 1 | 94 | 2000 |
| baseline | memory_z | 3 | 0.1795 | 0.1711–0.1882 | 0.0688888 | 0.197083 | 1 | 359 | 2000 |
| baseline | memory_z | 5 | 0.2625 | 0.2528–0.2725 | 0.0691672 | 0.2098 | 1 | 525 | 2000 |
| baseline | memory_z | 7 | 0.339 | 0.3285–0.3497 | 0.074731 | 0.216339 | 1 | 678 | 2000 |
| in_sample_improved | memory_x | 1 | 0.0735 | 0.06788–0.07955 | 0.0735 | 0.146625 | 1 | 147 | 2000 |
| in_sample_improved | memory_x | 3 | 0.1985 | 0.1897–0.2076 | 0.077582 | 0.203146 | 1 | 397 | 2000 |
| in_sample_improved | memory_x | 5 | 0.299 | 0.2889–0.3093 | 0.0833079 | 0.213012 | 1 | 598 | 2000 |
| in_sample_improved | memory_x | 7 | 0.3655 | 0.3548–0.3763 | 0.0855176 | 0.217723 | 1 | 731 | 2000 |
| in_sample_improved | memory_z | 1 | 0.043 | 0.03869–0.04777 | 0.043 | 0.1385 | 1 | 86 | 2000 |
| in_sample_improved | memory_z | 3 | 0.1625 | 0.1544–0.1709 | 0.0613973 | 0.197083 | 1 | 325 | 2000 |
| in_sample_improved | memory_z | 5 | 0.252 | 0.2424–0.2618 | 0.0654234 | 0.2098 | 1 | 504 | 2000 |
| in_sample_improved | memory_z | 7 | 0.324 | 0.3136–0.3346 | 0.0692846 | 0.216339 | 1 | 648 | 2000 |
| kfold | memory_x | 1 | 0.075 | 0.06932–0.0811 | 0.075 | 0.146625 | 1 | 150 | 2000 |
| kfold | memory_x | 3 | 0.1985 | 0.1897–0.2076 | 0.077582 | 0.203146 | 1 | 397 | 2000 |
| kfold | memory_x | 5 | 0.311 | 0.3007–0.3214 | 0.0884066 | 0.213012 | 1 | 622 | 2000 |
| kfold | memory_x | 7 | 0.373 | 0.3623–0.3839 | 0.0889012 | 0.217723 | 1 | 746 | 2000 |
| kfold | memory_z | 1 | 0.044 | 0.03964–0.04882 | 0.044 | 0.1385 | 1 | 88 | 2000 |
| kfold | memory_z | 3 | 0.169 | 0.1608–0.1775 | 0.0642313 | 0.197083 | 1 | 338 | 2000 |
| kfold | memory_z | 5 | 0.252 | 0.2424–0.2618 | 0.0654234 | 0.2098 | 1 | 504 | 2000 |
| kfold | memory_z | 7 | 0.329 | 0.3186–0.3396 | 0.0710543 | 0.216339 | 1 | 658 | 2000 |
| postselect_q25 | memory_x | 1 | 0 | 0–0.001217 |  | 0.146625 | 0.4105 | 0 | 821 |
| postselect_q25 | memory_x | 3 | 0.0726979 | 0.06294–0.08384 |  | 0.203146 | 0.3095 | 45 | 619 |
| postselect_q25 | memory_x | 5 | 0.190878 | 0.1753–0.2075 |  | 0.213012 | 0.296 | 113 | 592 |
| postselect_q25 | memory_x | 7 | 0.257367 | 0.2385–0.2772 |  | 0.217723 | 0.2545 | 131 | 509 |
| postselect_q25 | memory_z | 1 | 0 | 0–0.001159 |  | 0.1385 | 0.431 | 0 | 862 |
| postselect_q25 | memory_z | 3 | 0.0754148 | 0.06579–0.08632 |  | 0.197083 | 0.3315 | 50 | 663 |
| postselect_q25 | memory_z | 5 | 0.173139 | 0.1585–0.1889 |  | 0.2098 | 0.309 | 107 | 618 |
| postselect_q25 | memory_z | 7 | 0.233533 | 0.2152–0.253 |  | 0.216339 | 0.2505 | 117 | 501 |
