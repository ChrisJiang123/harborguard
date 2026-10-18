# Historical acceptance evidence

`pr6-final-integration-results.json` is preserved unchanged from PR #6 head
`5af2ae08d9baf6aa53fe58cacd6552986eed76a2`. The accompanying
`pr6-final-integration-report.md` is an English translation of that historical
report, whose original text remains available at that commit. Both describe old
main `5817b9c` and template C `78d3957`; they are not acceptance results for a
later main, including `782d04d` mentioned when this archive was created.

The historical sonar model was `stub`, the Agent was `template`, and Recovery
reported 6 clear / 4 blocked / 2 unsurveyed. The real-YOLO candidate available
when the archive was created reported 6 / 3 / 3. Historical statements about
conflict-free merges, C not yet being merged, rejection producing only logs,
or A lacking recovery must not be reused as current findings.

For current interfaces and approval/rejection persistence, see
[frontend integration](../frontend-integration.md). For the newer test results,
PR dependencies and remaining issues, see
[final integration report](../final-integration-report.md). Always check the
exact source SHA and date of those reports before treating them as current.
