# 2026-03-07 Bass Analysis Benchmark and A/B Evaluation

## Notes

- [x] Inspect evaluation tooling
- [x] Define benchmark configs
- [ ] Run benchmarks on Hysteria
- [ ] Run benchmarks on Trooper
- [ ] Collect metrics
- [ ] Produce report
- [ ] Analyze failure modes
- [ ] Propose next engineering step

## Constraints

- [ ] Do not modify or commit files under `/Users/wojciechgula/Projects/DeChord/test songs`
- [ ] Keep benchmark comparisons fair: same input audio, BPM hints, subdivision, and tab pipeline settings; only vary stem-analysis configuration
- [ ] Do not redesign architecture; only add minimal evaluation helpers if required
- [ ] Run `make reset` before final verification and handoff

## Workflow Notes

- [x] Work directly in the repository without SUPERPOWERS skills or autonomous agent workflows, per user instruction
- [x] Subagent-driven development is intentionally not applied because the user explicitly prohibited autonomous agent workflows for this task
- [x] Apply TDD only if benchmark helper code changes become necessary; pure benchmark execution/reporting does not create a meaningful red-green cycle on its own
