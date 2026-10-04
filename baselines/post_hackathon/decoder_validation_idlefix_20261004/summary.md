# Sweep Comparison

## Per-Round Fits

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2. Postselected series are excluded (their kept fraction changes with r).

| Label | Basis | Fit points | Error per round | 1-sigma | Amplitude A | Excluded points |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | memory_x | 4 | 0.0350496 | 0.00120773 | 1 | 0 |
| baseline | memory_z | 4 | 0.0279089 | 0.00104493 | 1 | 0 |
| gated_kfold | memory_x | 4 | 0.0345901 | 0.00119745 | 1 | 0 |
| gated_kfold | memory_z | 4 | 0.0279089 | 0.00104493 | 1 | 0 |
| in_sample_improved | memory_x | 4 | 0.0300326 | 0.0010941 | 1 | 0 |
| in_sample_improved | memory_z | 4 | 0.0269234 | 0.00102203 | 1 | 0 |
| kfold | memory_x | 4 | 0.0300326 | 0.0010941 | 1 | 0 |
| kfold | memory_z | 4 | 0.0274735 | 0.0010348 | 1 | 0 |

## Sweep Rows

| Label | Basis | Rounds | LER | Uncertainty | Per-round LER | Mean detector rate | Kept fraction | Failures | Shots |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| baseline | memory_x | 3 | 0.0945 | 0.00654 | 0.0337234 | 0.135833 | 1 | 189 | 2000 |
| baseline | memory_x | 5 | 0.162 | 0.00824 | 0.0376623 | 0.143175 | 1 | 324 | 2000 |
| baseline | memory_x | 7 | 0.202 | 0.00898 | 0.035632 | 0.147696 | 1 | 404 | 2000 |
| baseline | memory_z | 1 | 0.0215 | 0.00324 | 0.0215 | 0.104125 | 1 | 43 | 2000 |
| baseline | memory_z | 3 | 0.0805 | 0.00608 | 0.0284179 | 0.135875 | 1 | 161 | 2000 |
| baseline | memory_z | 5 | 0.127 | 0.00745 | 0.0284608 | 0.142738 | 1 | 254 | 2000 |
| baseline | memory_z | 7 | 0.1685 | 0.00837 | 0.0285106 | 0.14767 | 1 | 337 | 2000 |
| gated_kfold | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| gated_kfold | memory_x | 3 | 0.098 | 0.00665 | 0.0350688 | 0.135833 | 1 | 196 | 2000 |
| gated_kfold | memory_x | 5 | 0.153 | 0.00805 | 0.0352259 | 0.143175 | 1 | 306 | 2000 |
| gated_kfold | memory_x | 7 | 0.202 | 0.00898 | 0.035632 | 0.147696 | 1 | 404 | 2000 |
| gated_kfold | memory_z | 1 | 0.0215 | 0.00324 | 0.0215 | 0.104125 | 1 | 43 | 2000 |
| gated_kfold | memory_z | 3 | 0.0805 | 0.00608 | 0.0284179 | 0.135875 | 1 | 161 | 2000 |
| gated_kfold | memory_z | 5 | 0.127 | 0.00745 | 0.0284608 | 0.142738 | 1 | 254 | 2000 |
| gated_kfold | memory_z | 7 | 0.1685 | 0.00837 | 0.0285106 | 0.14767 | 1 | 337 | 2000 |
| in_sample_improved | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| in_sample_improved | memory_x | 3 | 0.0855 | 0.00625 | 0.030299 | 0.135833 | 1 | 171 | 2000 |
| in_sample_improved | memory_x | 5 | 0.134 | 0.00762 | 0.0302441 | 0.143175 | 1 | 268 | 2000 |
| in_sample_improved | memory_x | 7 | 0.178 | 0.00855 | 0.030465 | 0.147696 | 1 | 356 | 2000 |
| in_sample_improved | memory_z | 1 | 0.021 | 0.00321 | 0.021 | 0.104125 | 1 | 42 | 2000 |
| in_sample_improved | memory_z | 3 | 0.0795 | 0.00605 | 0.0280435 | 0.135875 | 1 | 159 | 2000 |
| in_sample_improved | memory_z | 5 | 0.1205 | 0.00728 | 0.0268287 | 0.142738 | 1 | 241 | 2000 |
| in_sample_improved | memory_z | 7 | 0.164 | 0.00828 | 0.0276015 | 0.14767 | 1 | 328 | 2000 |
| kfold | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| kfold | memory_x | 3 | 0.0855 | 0.00625 | 0.030299 | 0.135833 | 1 | 171 | 2000 |
| kfold | memory_x | 5 | 0.134 | 0.00762 | 0.0302441 | 0.143175 | 1 | 268 | 2000 |
| kfold | memory_x | 7 | 0.178 | 0.00855 | 0.030465 | 0.147696 | 1 | 356 | 2000 |
| kfold | memory_z | 1 | 0.0215 | 0.00324 | 0.0215 | 0.104125 | 1 | 43 | 2000 |
| kfold | memory_z | 3 | 0.0815 | 0.00612 | 0.0287929 | 0.135875 | 1 | 163 | 2000 |
| kfold | memory_z | 5 | 0.1205 | 0.00728 | 0.0268287 | 0.142738 | 1 | 241 | 2000 |
| kfold | memory_z | 7 | 0.1685 | 0.00837 | 0.0285106 | 0.14767 | 1 | 337 | 2000 |
