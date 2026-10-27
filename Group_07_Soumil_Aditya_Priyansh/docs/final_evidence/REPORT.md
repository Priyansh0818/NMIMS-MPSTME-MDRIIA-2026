# Experiment analysis

frozen held-out experiment

Audited runs: 100. Missing: 0. Audit errors: 0.

Inferential reporting ready: True.

Primary measure: restricted_completion_time_s: mission termination time when all 16 physical placements are correct; otherwise 1800 s

The raw files are measured 500 Hz physics samples, compressed as lossless CSV.

See analysis.json for source-linked metrics, audit failures and test definitions.

```json
{
  "available": true,
  "test": "Independent two-sided Welch t-test",
  "t": 7.837251099623215,
  "df": 49.0,
  "p": 3.391003307116647e-10,
  "ci95": [
    339.95892671474905,
    574.4170732852507
  ],
  "n_baseline": 50,
  "n_proposed": 50,
  "mean_baseline": 1800.0,
  "mean_proposed": 1342.8120000000001,
  "sd_baseline": 0.0,
  "sd_proposed": 412.4925065788147,
  "difference_baseline_minus_proposed": 457.1879999999999,
  "cohen_d": 1.5674502199246432
}
```