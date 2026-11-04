from siftgrain_state.contract import age_seconds, validate
from siftgrain_state.signatures import SignatureVerifier, signature_status


def same_json(left: object, right: object) -> bool:
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        assert isinstance(right, dict)
        return left.keys() == right.keys() and all(same_json(left[key], right[key]) for key in left)
    if type(left) is list:
        assert isinstance(right, list)
        return len(left) == len(right) and all(
            same_json(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def check_packet(packet: dict, verifier: SignatureVerifier | None = None) -> dict:
    validate(packet)
    actions = {row["id"]: row for row in packet["actions"]}
    observations = {row["id"]: row for row in packet["observations"]}
    baselines = {row["id"]: row for row in packet.get("baselines", [])}
    signatures = {}
    baseline_signatures = {}
    if packet["schema_version"] in (2, 3):
        signatures = {key: signature_status(row, verifier) for key, row in observations.items()}
        baseline_signatures = {
            key: signature_status(row, verifier) for key, row in baselines.items()
        }
    results = []
    for requirement in sorted(packet["requirements"], key=lambda row: row["id"]):
        action_id = requirement["action_id"]
        action = (
            "not_required"
            if action_id is None
            else {"succeeded": "confirmed", "failed": "contradicted", "unknown": "unobserved"}[
                actions.get(action_id, {"status": "unknown"})["status"]
            ]
        )
        observation = observations.get(requirement["observation_id"])
        outcome, reason = "unobserved", "missing observation"
        if observation is not None:
            age = age_seconds(packet["as_of"], observation["observed_at"])
            if observation["subject"] != requirement["subject"]:
                reason = "subject mismatch"
            elif age < 0:
                reason = "future observation"
            elif age > requirement["max_age_seconds"]:
                reason = "stale observation"
            else:
                value = observation["state"]
                for key in requirement["path"]:
                    if type(value) is not dict or key not in value:
                        reason = "missing object path"
                        break
                    value = value[key]
                else:
                    outcome, reason = compare(requirement, value)
                    if packet["schema_version"] in (2, 3):
                        signing = signatures[observation["id"]]
                        if signing == "invalid" or (
                            packet.get("require_signatures") and signing != "verified"
                        ):
                            outcome, reason = "unobserved", "signature not verified"
                        elif requirement.get("baseline_id") is not None:
                            baseline = baselines.get(requirement["baseline_id"])
                            outcome, reason = compare_baseline(
                                packet,
                                requirement,
                                observation,
                                baseline,
                                value,
                                outcome,
                                reason,
                                baseline_signatures.get(requirement["baseline_id"], "unsigned"),
                            )
        status = (
            "contradicted"
            if "contradicted" in (action, outcome)
            else "confirmed"
            if outcome == "confirmed" and action in ("confirmed", "not_required")
            else "unconfirmed"
            if outcome == "unconfirmed"
            else "unobserved"
        )
        results.append(
            {
                "id": requirement["id"],
                "action": action,
                "outcome": outcome,
                "status": status,
                "reason": reason,
                "action_id": action_id,
                "observation_id": requirement["observation_id"],
            }
        )
        if packet["schema_version"] in (2, 3):
            results[-1]["signature"] = signatures.get(requirement["observation_id"], "unsigned")
    counts = {
        status: sum(row["status"] == status for row in results)
        for status in (
            ("confirmed", "contradicted", "unobserved", "unconfirmed")
            if packet["schema_version"] in (2, 3)
            else ("confirmed", "contradicted", "unobserved")
        )
    }
    return {
        "schema_version": packet["schema_version"],
        "results": results,
        "counts": counts,
        "exit_code": int(any(row["status"] != "confirmed" for row in results)),
    }


def compare(requirement: dict, value) -> tuple[str, str]:
    check, expected = requirement.get("check", "equal"), requirement["expected"]
    if check == "range":
        matches = type(value) in (int, float)
        for side, direction in (("min", 1), ("max", -1)):
            if matches and side in expected:
                inclusive = expected.get(side + "_inclusive", True)
                matches = (
                    (value >= expected[side] if inclusive else value > expected[side])
                    if direction == 1
                    else (value <= expected[side] if inclusive else value < expected[side])
                )
    elif check == "contains":
        matches = type(value) is list and any(same_json(item, expected) for item in value)
    elif check == "regex":
        from siftgrain_state.checks import safe_regex

        matches = (
            type(value) is str
            and len(value) <= 4096
            and safe_regex(expected).fullmatch(value) is not None
        )
    elif check in ("unchanged", "changed_from_baseline"):
        return "unobserved", "missing baseline"
    else:
        matches = same_json(value, expected)
    return (
        ("confirmed", "expected value observed")
        if matches
        else ("contradicted", "different value observed")
    )


def compare_baseline(packet, requirement, observation, baseline, value, outcome, reason, signing):
    if baseline is None:
        return "unobserved", "missing baseline"
    if baseline["subject"] != requirement["subject"]:
        return "unobserved", "baseline subject mismatch"
    if age_seconds(observation["observed_at"], baseline["observed_at"]) <= 0:
        return "unobserved", "baseline must precede observation"
    if signing == "invalid" or (packet.get("require_signatures") and signing != "verified"):
        return "unobserved", "baseline signature not verified"
    before = baseline["state"]
    for key in requirement["path"]:
        if type(before) is not dict or key not in before:
            return "unobserved", "missing baseline object path"
        before = before[key]
    changed = not same_json(before, value)
    check = requirement.get("check", "equal")
    if check in ("unchanged", "changed_from_baseline"):
        matches = changed if check == "changed_from_baseline" else not changed
        return (
            ("confirmed", "baseline comparison satisfied")
            if matches
            else ("contradicted", "baseline comparison failed")
        )
    if outcome == "confirmed" and requirement.get("requires_change") and not changed:
        return "unconfirmed", "no observed change"
    return outcome, reason
