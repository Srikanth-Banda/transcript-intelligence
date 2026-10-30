"""Run one call through Stages 1 and 2 in replay mode, for the video demo. Writes nothing; makes no network call.

Usage: TI_MODE=replay PYTHONPATH=src uv run python eval/demo_replay.py [index]   (index 0-99, default 41, a support case about the outage)
A cache miss raises an error instead of calling the model (see src/ti/llm.py), so this proves the run is replayable.
"""
import os
import sys

os.environ["TI_MODE"] = "replay"
from ti import stage1, stage2  # noqa: E402
from ti.common import Guard, stage0_types  # noqa: E402
from ti.llm import LLMClient  # noqa: E402
from ti.load import load_meetings  # noqa: E402

i = int(sys.argv[1]) if len(sys.argv) > 1 else 41
m = load_meetings()[i]
guard = Guard(refresh=False)
client = LLMClient()
print(f"mode=replay (no key, no network)\ncall: {m.meeting_id}  title: {m.title}\nStage 0 call type: {stage0_types().get(m.meeting_id)}\n")
r1 = stage1.classify(m, client, guard)
print("STAGE 1  theme:", r1.get("primary_theme"), "| area:", r1.get("product_area"), "| incident:", r1.get("incident"))
print("  evidence:", r1.get("evidence_quote"))
r2 = stage2.classify(m, client, guard)
print("STAGE 2  call score:", r2.get("call_score"), "| customer score:", r2.get("customer_score"), "| trajectory:", r2.get("traj_start"), "->", r2.get("traj_end"))
print("  evidence:", r2.get("evidence_quote"))
print(f"\ncache_hit: stage1={r1.get('cache_hit')} stage2={r2.get('cache_hit')}  cost this session: ${guard.cost:.4f}")
