# Sweep Comparison

## Per-Round Fits

| Label | Basis | Fit points | Fitted logical error per round |
| --- | --- | ---: | ---: |
| baseline | memory_x | 4 | 0.18389 |
| baseline | memory_z | 4 | 0.18173 |
| decoder_holdout | memory_x | 4 | 0.184331 |
| decoder_holdout | memory_z | 4 | 0.23562 |
| decoder_improved | memory_x | 4 | 0.166954 |
| decoder_improved | memory_z | 4 | 0.168197 |
| decoder_kfold | memory_x | 4 | 0.198919 |
| decoder_kfold | memory_z | 4 | 0.228656 |
| postselect25 | memory_x | 4 | 0.153178 |
| postselect25 | memory_z | 4 | 0.144653 |

## Sweep Rows

| Label | Basis | Rounds | LER | Uncertainty | Per-round LER | Mean detector rate | Kept fraction | Failures | Shots |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| baseline | memory_x | 3 | 0.2025 | 0.00899 | 0.0794584 | 0.189583 | 1 | 405 | 2000 |
| baseline | memory_x | 5 | 0.358 | 0.0107 | 0.111283 | 0.246863 | 1 | 716 | 2000 |
| baseline | memory_x | 7 | 0.4715 | 0.0112 | 0.167924 | 0.294705 | 1 | 943 | 2000 |
| baseline | memory_z | 1 | 0.021 | 0.00321 | 0.021 | 0.104125 | 1 | 42 | 2000 |
| baseline | memory_z | 3 | 0.1675 | 0.00835 | 0.0635741 | 0.188083 | 1 | 335 | 2000 |
| baseline | memory_z | 5 | 0.367 | 0.0108 | 0.11634 | 0.247625 | 1 | 734 | 2000 |
| baseline | memory_z | 7 | 0.468 | 0.0112 | 0.162383 | 0.294938 | 1 | 936 | 2000 |
| decoder_holdout | memory_x | 1 | 0.027 | 0.00513 | 0.027 | 0.103438 | 1 | 27 | 1000 |
| decoder_holdout | memory_x | 3 | 0.217 | 0.013 | 0.0864048 | 0.189583 | 1 | 217 | 1000 |
| decoder_holdout | memory_x | 5 | 0.346 | 0.015 | 0.104924 | 0.246863 | 1 | 346 | 1000 |
| decoder_holdout | memory_x | 7 | 0.473 | 0.0158 | 0.170479 | 0.294705 | 1 | 473 | 1000 |
| decoder_holdout | memory_z | 1 | 0.021 | 0.00453 | 0.021 | 0.104125 | 1 | 21 | 1000 |
| decoder_holdout | memory_z | 3 | 0.175 | 0.012 | 0.0668804 | 0.188083 | 1 | 175 | 1000 |
| decoder_holdout | memory_z | 5 | 0.357 | 0.0152 | 0.110737 | 0.247625 | 1 | 357 | 1000 |
| decoder_holdout | memory_z | 7 | 0.491 | 0.0158 | 0.218341 | 0.294938 | 1 | 491 | 1000 |
| decoder_improved | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| decoder_improved | memory_x | 3 | 0.1995 | 0.00894 | 0.0780495 | 0.189583 | 1 | 399 | 2000 |
| decoder_improved | memory_x | 5 | 0.347 | 0.0106 | 0.105439 | 0.246863 | 1 | 694 | 2000 |
| decoder_improved | memory_x | 7 | 0.4605 | 0.0111 | 0.152073 | 0.294705 | 1 | 921 | 2000 |
| decoder_improved | memory_z | 1 | 0.021 | 0.00321 | 0.021 | 0.104125 | 1 | 42 | 2000 |
| decoder_improved | memory_z | 3 | 0.1645 | 0.00829 | 0.0622654 | 0.188083 | 1 | 329 | 2000 |
| decoder_improved | memory_z | 5 | 0.3585 | 0.0107 | 0.111557 | 0.247625 | 1 | 717 | 2000 |
| decoder_improved | memory_z | 7 | 0.4585 | 0.0111 | 0.149609 | 0.294938 | 1 | 917 | 2000 |
| decoder_kfold | memory_x | 1 | 0.0265 | 0.00359 | 0.0265 | 0.103438 | 1 | 53 | 2000 |
| decoder_kfold | memory_x | 3 | 0.2005 | 0.00895 | 0.0785181 | 0.189583 | 1 | 401 | 2000 |
| decoder_kfold | memory_x | 5 | 0.355 | 0.0107 | 0.109654 | 0.246863 | 1 | 710 | 2000 |
| decoder_kfold | memory_x | 7 | 0.4795 | 0.0112 | 0.183192 | 0.294705 | 1 | 959 | 2000 |
| decoder_kfold | memory_z | 1 | 0.021 | 0.00321 | 0.021 | 0.104125 | 1 | 42 | 2000 |
| decoder_kfold | memory_z | 3 | 0.1645 | 0.00829 | 0.0622654 | 0.188083 | 1 | 329 | 2000 |
| decoder_kfold | memory_z | 5 | 0.364 | 0.0108 | 0.114625 | 0.247625 | 1 | 728 | 2000 |
| decoder_kfold | memory_z | 7 | 0.489 | 0.0112 | 0.21015 | 0.294938 | 1 | 978 | 2000 |
| postselect25 | memory_x | 1 | 0 | 0 | 0 | 0.103438 | 0.5585 | 0 | 1117 |
| postselect25 | memory_x | 3 | 0.0710383 | 0.00949 | 0.0248987 | 0.189583 | 0.366 | 52 | 732 |
| postselect25 | memory_x | 5 | 0.270378 | 0.0198 | 0.072064 | 0.246863 | 0.2515 | 136 | 503 |
| postselect25 | memory_x | 7 | 0.446254 | 0.0201 | 0.136424 | 0.294705 | 0.307 | 274 | 614 |
| postselect25 | memory_z | 1 | 0 | 0 | 0 | 0.104125 | 0.553 | 0 | 1106 |
| postselect25 | memory_z | 3 | 0.0677507 | 0.00925 | 0.0236881 | 0.188083 | 0.369 | 50 | 738 |
| postselect25 | memory_z | 5 | 0.267686 | 0.0194 | 0.0710656 | 0.247625 | 0.2615 | 140 | 523 |
| postselect25 | memory_z | 7 | 0.436893 | 0.02 | 0.127988 | 0.294938 | 0.309 | 270 | 618 |
