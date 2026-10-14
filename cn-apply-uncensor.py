#!/usr/bin/env python3
"""cn: add the fork's uncensored control vector to a setup-generated config.

Upstream setup has no --uncensored; the engine flags are the same ones the
fork's setup wrote (verified against the fork deployment's live configs). The
vector ships in this branch at data/uncensor/, so in the image it sits at
/opt/strata/data/uncensor/ - the fork's path, which the moved configs already
reference. Idempotent: a config that carries a vector is left alone.
"""
import json
import sys

path = sys.argv[1]
cfg = json.load(open(path))
args = cfg.setdefault("args", [])
if not any(x == "--control-vector-scaled" for x in args):
    args += [
        "--control-vector-scaled",
        "/opt/strata/data/uncensor/qwen-nvfp4-gptq-uncensored.gguf:1.0",
        "--control-vector-layer-range", "8", "33",
        "--cvec-mode", "project", "--cvec-dir", "per-layer",
    ]
cfg["uncensored"] = True
json.dump(cfg, open(path, "w"), indent=1)
print(f"[cn] uncensored control vector written into {path}")
