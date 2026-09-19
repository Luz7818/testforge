"""TestForge: a mutation-guided test quality agent.

LLM coding assistants generate unit tests that *pass* but are weak: they
rarely detect real bugs. TestForge closes the loop — candidate tests must
survive a multi-signal quality gate (correctness, determinism, falsifiability
against seeded mutants) and are iteratively strengthened using feedback about
mutants that survived, i.e. bugs the tests failed to catch.

Reference points for the design (see docs/report.md):
- Meta, "Mutation-Guided LLM-based Test Generation at Meta" (FSE 2025, ACH)
- MutGen, "Mutation-Guided Unit Test Generation with an LLM" (arXiv:2506.02954)
"""

__version__ = "0.1.0"
