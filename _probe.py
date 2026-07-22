import inspect
import evaluation.runner as r

print("RunResult fields:", list(r.RunResult.__dataclass_fields__))
print("ExperimentResults fields:", list(r.ExperimentResults.__dataclass_fields__))
print("_compute_summary sig:", inspect.signature(r.ExperimentRunner._compute_summary))
# Show RunResult construction sites
import re
src = open("evaluation/runner.py").read()
for m in re.finditer(r"RunResult\(", src):
    line = src[: m.start()].count("\n") + 1
    print("RunResult at line", line)
