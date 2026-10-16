#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 496 组计算结果导出成多工作表 Excel，便于自行核对与二次分析"""
import json
import os

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA = os.path.join(ROOT, "data")

with open(os.path.join(DATA, "results.json"), encoding="utf-8") as f:
    res = json.load(f)
with open(os.path.join(DATA, "policy_2026.json"), encoding="utf-8") as f:
    pol = json.load(f)

SAL = res["meta"]["salary_levels"]
COLS = [("salary", "税前月薪"), ("unit_social", "单位社保"), ("unit_pf", "单位公积金"),
        ("company_cost", "公司实际成本"), ("ind_social", "个人社保"), ("ind_pf", "个人公积金"),
        ("monthly_tax", "月均个税"), ("cash", "到手现金"), ("indirect_tax", "估算消费间接税"),
        ("final_value", "最终消费价值")]


def sheet_for(rows, name):
    d = {}
    for k, label in COLS:
        d[label] = [round(r[k], 2) for r in rows]
    d["最终消费价值/公司成本"] = [round(r["ratio"] * 100, 1) for r in rows]
    d["实际现金到手率"] = [round(r["cash_ratio"] * 100, 1) for r in rows]
    d["损耗比例"] = [round(r["loss_ratio"] * 100, 1) for r in rows]
    d["养老缴费基数"] = [round(r["base_pension"], 2) for r in rows]
    d["公积金缴存基数"] = [round(r["base_pf"], 2) for r in rows]
    return pd.DataFrame(d)


prov_rows = {}
for r in res["results"]:
    prov_rows[r["id"]] = r["rows"]

# 1) 全国合并长表
long_rows = []
for r in res["results"]:
    prov = next(p for p in pol["provinces"] if p["id"] == r["id"])
    for i, row in enumerate(r["rows"]):
        long_rows.append({
            "省份": r["name"], "地区": r["region"], "税前月薪": SAL[i],
            "单位社保": round(row["unit_social"], 2), "单位公积金": round(row["unit_pf"], 2),
            "公司实际成本": round(row["company_cost"], 2),
            "个人社保": round(row["ind_social"], 2), "个人公积金": round(row["ind_pf"], 2),
            "月均个税": round(row["monthly_tax"], 2), "到手现金": round(row["cash"], 2),
            "估算消费间接税": round(row["indirect_tax"], 2), "最终消费价值": round(row["final_value"], 2),
            "消费价值/公司成本(%)": round(row["ratio"] * 100, 1),
            "实际现金到手率(%)": round(row["cash_ratio"] * 100, 1),
            "损耗比例(%)": round(row["loss_ratio"] * 100, 1),
            "社保基数下限": round(prov["base"]["pension"][0], 2),
            "社保基数上限": round(prov["base"]["pension"][1], 2),
            "公积金基数下限": round(prov["pf"]["lo"], 2),
            "公积金基数上限": round(prov["pf"]["hi"], 2),
        })
df_long = pd.DataFrame(long_rows)

# 2) 全国平均
nat = []
for n in res["national"]:
    nat.append({
        "税前月薪": n["salary"],
        "平均单位社保": round(n["unit_social"], 2), "平均单位公积金": round(n["unit_pf"], 2),
        "平均公司成本": round(n["company_cost"], 2),
        "平均个人社保": round(n["ind_social"], 2), "平均个人公积金": round(n["ind_pf"], 2),
        "平均月均个税": round(n["monthly_tax"], 2), "平均到手现金": round(n["cash"], 2),
        "平均消费间接税": round(n["indirect_tax"], 2), "平均最终消费价值": round(n["final_value"], 2),
        "占比均值(%)": round(n["ratio"] * 100, 1), "占比中位数(%)": round(n["ratio_median"] * 100, 1),
        "占比最低(%)": round(n["ratio_min"] * 100, 1), "占比最高(%)": round(n["ratio_max"] * 100, 1),
    })
df_nat = pd.DataFrame(nat)

# 3) 政策参数表
prows = []
for p in pol["provinces"]:
    prows.append({
        "省份": p["name"], "地区": p["region"],
        "养老基数下限": p["base"]["pension"][0], "养老基数上限": p["base"]["pension"][1],
        "医保基数下限": p["base"]["medical"][0], "医保基数上限": p["base"]["medical"][1],
        "失业基数下限": p["base"]["unemp"][0], "失业基数上限": p["base"]["unemp"][1],
        "养老单位费率(%)": p["rates"]["pension_u"] * 100, "养老个人费率(%)": p["rates"]["pension_i"] * 100,
        "医保单位费率(%)": p["rates"]["medical_u"] * 100, "医保个人费率(%)": p["rates"]["medical_i"] * 100,
        "失业单位费率(%)": p["rates"]["unemp_u"] * 100, "失业个人费率(%)": p["rates"]["unemp_i"] * 100,
        "工伤单位费率(%)": p["rates"]["injury_u"] * 100,
        "公积金下限": p["pf"]["lo"], "公积金上限": p["pf"]["hi"],
        "公积金单位比例(%)": p["pf"]["u"] * 100, "公积金个人比例(%)": p["pf"]["i"] * 100,
        "最低工资": p["min_wage"],
        "基数可信度": p["conf"]["base"],
        "养老费率可信度": p["conf"]["pension"], "医保费率可信度": p["conf"]["medical"],
        "失业费率可信度": p["conf"]["unemp"], "工伤费率可信度": p["conf"]["injury"],
        "公积金可信度": p["conf"]["pf"], "最低工资可信度": p["conf"]["min_wage"],
        "政策依据": p["src"].get("base_doc", ""), "来源链接": p["src"].get("base", ""),
        "费率来源": p["src"].get("injury", ""),
    })
df_pol = pd.DataFrame(prows)

# 4) 16 档汇总对比（各省占当前档位比例矩阵）
mat = {}
for r in res["results"]:
    mat[r["name"]] = [round(x["ratio"] * 100, 1) for x in r["rows"]]
df_rank = pd.DataFrame(mat, index=["%d 元" % s for s in SAL]).T
df_rank.columns = ["%d元" % s for s in SAL]
df_rank = df_rank.sort_values("8000元", ascending=False)

out = os.path.join(ROOT, "全国工资税费与消费能力测算.xlsx")
with pd.ExcelWriter(out, engine="openpyxl") as w:
    df_long.to_excel(w, sheet_name="全国496组明细", index=False)
    df_nat.to_excel(w, sheet_name="全国平均", index=False)
    df_rank.to_excel(w, sheet_name="各省占比矩阵")
    df_pol.to_excel(w, sheet_name="政策参数与来源", index=False)
    for p in pol["provinces"]:
        df = sheet_for(prov_rows[p["id"]], p["short"])
        df.insert(0, "省份", p["name"])
        name = p["short"][:28]
        df.to_excel(w, sheet_name=name, index=False)

print("已生成:", out)
print("工作表数:", 4 + len(pol["provinces"]))
print("明细行数:", len(df_long))
