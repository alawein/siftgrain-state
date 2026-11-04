"""Development-only V8 differential check. Never imported by the product."""

import json
import math
import random
import shutil
import struct
import subprocess

from siftgrain_state.canonical import canonicalize

NODE_VERSION = "v22.23.2"


def main():
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node v22.23.2 required for independent V8 check")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    if version != NODE_VERSION:
        raise RuntimeError(f"Expected {NODE_VERSION}, found {version}")
    rng = random.Random(8785)
    values = [rng.getrandbits(64).to_bytes(8, "big").hex() for _ in range(100000)]
    values = [bits for bits in values if math.isfinite(struct.unpack(">d", bytes.fromhex(bits))[0])]
    script = (
        'let s="";process.stdin.on("data",x=>s+=x);process.stdin.on("end",()=>'
        "console.log(JSON.stringify(JSON.parse(s).map(x=>"
        'JSON.stringify(Buffer.from(x,"hex").readDoubleBE())))));'
    )
    result = subprocess.run(
        [node, "-e", script], input=json.dumps(values), text=True, capture_output=True, check=True
    )
    reference = json.loads(result.stdout)
    for bits, expected in zip(values, reference, strict=True):
        value = struct.unpack(">d", bytes.fromhex(bits))[0]
        actual = canonicalize(value).decode()
        if actual != expected:
            raise AssertionError((bits, actual, expected))
    print(f"PASS: {len(values)} finite binary64 values match Node {version} JSON.stringify")


if __name__ == "__main__":
    main()
