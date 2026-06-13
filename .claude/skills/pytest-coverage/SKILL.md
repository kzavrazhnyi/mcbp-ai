---
name: pytest-coverage
description: "Run pytest with coverage, discover lines missing coverage, and raise coverage to 100% iteratively. Trigger — EN: pytest coverage, coverage report, missing lines, 100% coverage, cov_annotate. Trigger — UA: покриття тестами, pytest coverage, знайти незакриті рядки коду, підняти покриття до 100%, cov_annotate звіт."
---

The goal is for the tests to cover all lines of code.

Generate a coverage report with:

pytest --cov --cov-report=annotate:cov_annotate

If you are checking for coverage of a specific module, you can specify it like this:

pytest --cov=your_module_name --cov-report=annotate:cov_annotate

You can also specify specific tests to run, for example:

pytest tests/test_your_module.py --cov=your_module_name --cov-report=annotate:cov_annotate

Open the cov_annotate directory to view the annotated source code.
There will be one file per source file. If a file has 100% source coverage, it means all lines are covered by tests, so you do not need to open the file.

For each file that has less than 100% test coverage, find the matching file in cov_annotate and review the file.

If a line starts with a ! (exclamation mark), it means that the line is not covered by tests.
Add tests to cover the missing lines.

Keep running the tests and improving coverage until all lines are covered.

## Trigger phrases (UA)

покриття тестами, pytest coverage, незакриті рядки коду, підняти покриття, cov_annotate звіт, 100% покриття, які рядки не покриті, coverage report
