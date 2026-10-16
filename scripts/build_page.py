#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把计算结果注入页面模板，生成自包含的 index.html（无需联网、无外部依赖）"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA = os.path.join(ROOT, "data")

with open(os.path.join(DATA, "results.json"), encoding="utf-8") as f:
    res = json.load(f)
with open(os.path.join(DATA, "policy_2026.json"), encoding="utf-8") as f:
    pol = json.load(f)
with open(os.path.join(BASE, "page_template.html"), encoding="utf-8") as f:
    tpl = f.read()

FIELDS_MONEY = ("unit_social", "unit_pf", "company_cost", "ind_social", "ind_pf",
                "monthly_tax", "cash", "indirect_tax", "final_value")
FIELDS_RATIO = ("ratio", "cash_ratio", "loss_ratio")


def slim(rows):
    out = []
    for r in rows:
        d = {"salary": r["salary"]}
        for k in FIELDS_MONEY:
            d[k] = round(r[k], 2)
        for k in FIELDS_RATIO:
            d[k] = round(r[k], 5)
        d["base_pension"] = round(r["base_pension"], 2)
        d["base_medical"] = round(r["base_medical"], 2)
        d["base_pf"] = round(r["base_pf"], 2)
        out.append(d)
    return out


payload = {
    "meta": res["meta"],
    "provinces": res["provinces"],
    "results": [{"id": r["id"], "rows": slim(r["rows"])} for r in res["results"]],
    "national": [{k: (round(v, 5) if isinstance(v, float) else v) for k, v in n.items()}
                 for n in res["national"]],
    "validation": res["validation"],
    "analysis": res["analysis"],
}

blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
html = tpl.replace("/*__DATA__*/", blob)
out_path = os.path.join(ROOT, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print("已生成:", out_path)
print("页面大小: %.1f KB" % (len(html.encode("utf-8")) / 1024))
print("数据载荷: %.1f KB" % (len(blob.encode("utf-8")) / 1024))
print("校验:", payload["validation"]["checked"], "组, 失败", len(payload["validation"]["errors"]))
