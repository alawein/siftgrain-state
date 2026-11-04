# Shared code maintenance

src/siftgrain_state/output.py mirrors src/eval_audit/output.py in the sibling tool.
The exact duplicated functions are same_location(left, right),
validate_outputs(outputs, inputs, force), and atomic_write(path, content, force).
Both are stdlib-only and have no package-specific imports. Update the two copies
in one change and rerun both tools' alias, output-failure and competing-creation tests.

The runtime packages remain separately installable with zero core dependencies;
there is no shared runtime package to install. Duplication is deliberately limited
to this small output-safety module and the JSON serialization function. Per-file atomic publication does not provide a
multi-file transaction, crash recovery, or directory durability.

Both report modules also have an exact duplicated render_json(report) function:
json.dumps with sorted keys, two-space indentation, allow_nan=False, ASCII escaping
and one trailing LF. Corresponding tests check snapshot/strict finite JSON behavior.
HTML reports share escape-first behavior but their tables and explanations differ;
render_html is not an exact duplicated function. Both CLIs share validation-before-
write sequencing but main differs by input contract and is not copied byte-for-byte.

The mirrored `tests/test_shared_vectors.py` exercises existing-file rejection,
force replacement, hard-link input identity, competing creation, unsupported
link/replace, failed staging, second-output partial completion, sorted finite JSON,
trailing LF, and HTML text escaping. Only package import names differ. Seven shared
vectors pass in each tool; no shared behavior defect required a runtime patch.
