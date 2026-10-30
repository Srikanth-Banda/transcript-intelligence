"""Merge the candidate's console reviews (exported from the Review Console db) with the frozen model outputs.

Input: raw review docs in a directory (reviews_s1/*.json, reviews_s2/*.json). Output: eval/stage{1,2}_review_verdicts.json
in the shape ti.nbhelpers.load_verdicts expects. Model answers are joined from outputs/, never shown to the reviewer.
"""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
raw = Path(sys.argv[1])
s1 = pd.read_csv(ROOT / "outputs/stage1/stage1_final.csv").set_index("meeting_id")
s2 = pd.read_csv(ROOT / "outputs/stage2/stage2_final.csv").set_index("meeting_id")
truthy = lambda v: str(v).strip().lower() in ("true", "1", "yes")

out1 = []
for p in sorted((raw / "reviews_s1").glob("*.json")):
    d = json.loads(p.read_text()); m = s1.loc[d["meetingId"]]
    d["model"] = {"theme": m.primary_theme, "area": m.product_area, "incident": truthy(m.incident)}
    out1.append(d)
out2 = []
for p in sorted((raw / "reviews_s2").glob("*.json")):
    d = json.loads(p.read_text()); m = s2.loc[d["meetingId"]]
    d["modelCallScore"] = float(m.call_score)
    d["modelCustomerScore"] = None if pd.isna(m.customer_score) else float(m.customer_score)
    out2.append(d)
for n, items, extra in ((1, out1, {}), (2, out2, {})):
    (ROOT / f"eval/stage{n}_review_verdicts.json").write_text(json.dumps(
        {"stage": n, "reviewer": "candidate", "n": len(items), "items": items}, indent=1))
print(len(out1), len(out2))
