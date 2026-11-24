"""The eval harness runs offline against the rule-based baseline."""

from evals.run_evals import load_dataset, run


def test_dataset_has_messy_cases_including_injection():
    dataset = load_dataset()
    slices = {case.metadata["slice"] for case in dataset.cases}

    assert 8 <= len(dataset.cases) <= 10
    assert {"ordinary", "injection", "missing-field", "ambiguous"} <= slices


def test_baseline_passes_every_assertion():
    report = run(progress=False)

    assert not report.failures
    for case in report.cases:
        failed = [name for name, result in case.assertions.items() if not result.value]
        assert not failed, (case.name, failed)
    size = [case.scores["ReasonableSize"].value for case in report.cases]
    assert sum(size) / len(size) >= 0.8
