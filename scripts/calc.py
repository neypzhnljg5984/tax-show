#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
按《计算方法.txt》口径计算全国31个省级行政区（省/直辖市/自治区口径，广东取广州口径）
16个月薪档位的：单位社保、单位公积金、公司人工成本、个人社保、个人公积金、
月均个税、到手现金、消费环节间接税、最终消费价值与核心比例。

计算全部使用未舍入的中间值，输出时再四舍五入。
"""
import json
import math
import os
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT, "data")

with open(os.path.join(DATA_DIR, "policy_2026.json"), encoding="utf-8") as f:
    POLICY = json.load(f)

META = POLICY["meta"]
SALARIES = META["salary_levels"]
INDIRECT = META["indirect_tax_rate"]
BASIC_DEDUCTION = META["basic_deduction_annual"]
BRACKETS = META["pit_brackets_annual"]
PF_RATE = 0.07  # 单位、个人各7%（各地允许区间内）

R = 2  # 计算中间保留到分


def clamp(x, lo, hi):
    """缴费基数 = min(max(月薪, 下限), 上限)"""
    return min(max(x, lo), hi)


def annual_pit(taxable):
    """综合所得年度税率表（累进）"""
    if taxable <= 0:
        return 0.0
    for b in BRACKETS:
        if b["up_to"] is None or taxable <= b["up_to"]:
            return taxable * b["rate"] - b["quick"]


def calc_one(prov, salary):
    """单个（省, 月薪）组合的完整计算"""
    base = prov["base"]
    rates = prov["rates"]
    pf = prov["pf"]

    bp = clamp(salary, *base["pension"])
    bm = clamp(salary, *base["medical"])
    bu = clamp(salary, *base["unemp"])
    bi = clamp(salary, *base["injury"])
    bpf = clamp(salary, pf["lo"], pf["hi"])

    # ---- 个人承担的社保 ----
    ind_pension = bp * rates["pension_i"]
    ind_medical = bm * rates["medical_i"]
    ind_unemp = bu * rates["unemp_i"]
    ind_social = ind_pension + ind_medical + ind_unemp

    # ---- 单位承担的社保（生育保险已并入医保，不重复计算）----
    unit_pension = bp * rates["pension_u"]
    unit_medical = bm * rates["medical_u"]
    unit_unemp = bu * rates["unemp_u"]
    unit_injury = bi * rates["injury_u"]
    unit_social = unit_pension + unit_medical + unit_unemp + unit_injury

    # ---- 住房公积金（个人资产，不是税款）----
    ind_pf = bpf * pf["i"]
    unit_pf = bpf * pf["u"]

    # ---- 公司实际人工成本 ----
    cost = salary + unit_social + unit_pf

    # ---- 个人所得税（全年工资不变，月均口径）----
    annual_income = salary * 12
    annual_deduct = ind_social * 12 + ind_pf * 12 + BASIC_DEDUCTION
    taxable = max(0.0, annual_income - annual_deduct)
    annual_tax = annual_pit(taxable)
    monthly_tax = annual_tax / 12.0

    # ---- 个人税后到手现金 ----
    cash = salary - ind_social - ind_pf - monthly_tax

    # ---- 消费环节间接税与最终消费价值 ----
    indirect = cash * INDIRECT
    final_value = cash * (1 - INDIRECT)

    ratio = final_value / cost if cost else 0.0
    cash_ratio = cash / cost if cost else 0.0

    # 全部保留未舍入中间值，展示时再舍入（避免逐项先舍入导致累计误差）
    return OrderedDict([
        ("salary", float(salary)),
        ("base_pension", bp),
        ("base_medical", bm),
        ("base_pf", bpf),
        ("unit_social", unit_social),
        ("unit_pf", unit_pf),
        ("company_cost", cost),
        ("ind_social", ind_social),
        ("ind_pf", ind_pf),
        ("monthly_tax", monthly_tax),
        ("cash", cash),
        ("indirect_tax", indirect),
        ("final_value", final_value),
        ("ratio", ratio),
        ("cash_ratio", cash_ratio),
        ("loss_ratio", 1 - ratio),
        ("breakdown", OrderedDict([
            ("unit_pension", unit_pension),
            ("unit_medical", unit_medical),
            ("unit_unemp", unit_unemp),
            ("unit_injury", unit_injury),
            ("ind_pension", ind_pension),
            ("ind_medical", ind_medical),
            ("ind_unemp", ind_unemp),
            ("annual_tax", annual_tax),
        ])),
    ])


def validate(prov, salary, row):
    """《计算方法.txt》第四部分第10条的逐档交叉检查（基于未舍入中间值）"""
    errs = []
    b = prov["base"]
    if not (b["pension"][0] - 1e-9 <= row["base_pension"] <= b["pension"][1] + 1e-9):
        errs.append("养老基数越界")
    if not (prov["pf"]["lo"] - 1e-9 <= row["base_pf"] <= prov["pf"]["hi"] + 1e-9):
        errs.append("公积金基数越界")
    # 公司成本 = 税前工资 + 单位社保 + 单位公积金
    if abs(row["company_cost"] - (salary + row["unit_social"] + row["unit_pf"])) > 1e-6:
        errs.append("公司成本构成错误")
    # 到手现金 = 税前 - 个人社保 - 个人公积金 - 个税
    if abs(row["cash"] - (salary - row["ind_social"] - row["ind_pf"] - row["monthly_tax"])) > 1e-6:
        errs.append("到手现金构成错误")
    # 最终消费价值 = 到手现金 × 90%
    if abs(row["final_value"] - row["cash"] * 0.9) > 1e-6:
        errs.append("最终消费价值比例错误")
    # 核心比例 = 最终消费价值 / 公司成本
    if abs(row["ratio"] - row["final_value"] / row["company_cost"]) > 1e-12:
        errs.append("核心比例定义错误")
    # 到手现金率
    if abs(row["cash_ratio"] - row["cash"] / row["company_cost"]) > 1e-12:
        errs.append("到手现金率定义错误")
    # 个人社保不得包含单位缴费
    if row["ind_social"] >= row["unit_social"] * 3:
        errs.append("个人社保疑似混入单位缴费")
    # 工资高于上限时必须封顶
    if salary > b["pension"][1] and abs(row["base_pension"] - b["pension"][1]) > 1e-9:
        errs.append("高薪未封顶")
    # 工资低于下限时必须按下限
    if salary < b["pension"][0] and abs(row["base_pension"] - b["pension"][0]) > 1e-9:
        errs.append("低薪未保底")
    # 生育保险不得重复计算
    if not prov["base"]["maternity_merged"]:
        errs.append("生育保险未合并说明")
    return errs


def round_row(row):
    """展示用：金额四舍五入到元，比例保留1位小数由前端处理"""
    out = dict(row)
    for k in ("salary", "base_pension", "base_medical", "base_pf", "unit_social", "unit_pf",
              "company_cost", "ind_social", "ind_pf", "monthly_tax", "cash",
              "indirect_tax", "final_value"):
        out[k] = int(round(row[k]))
    return out


def main():
    provinces = POLICY["provinces"]
    errors = []
    results = []

    for prov in provinces:
        rows = []
        for s in SALARIES:
            row = calc_one(prov, s)
            errs = validate(prov, s, row)
            if errs:
                errors.append({"province": prov["id"], "salary": s, "errors": errs})
            rows.append(row)
        results.append({"id": prov["id"], "name": prov["name"], "short": prov["short"],
                        "region": prov["region"], "rows": rows})

    # ---------- 全国（31省等权）平均与中位数 ----------
    national = []
    for i, s in enumerate(SALARIES):
        keys = ["unit_social", "unit_pf", "company_cost", "ind_social", "ind_pf",
                "monthly_tax", "cash", "indirect_tax", "final_value", "ratio", "cash_ratio", "loss_ratio"]
        row = OrderedDict([("salary", s)])
        for k in keys:
            vals = sorted(r["rows"][i][k] for r in results)
            n = len(vals)
            mean = sum(vals) / n
            median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
            row[k] = mean
            row[k + "_median"] = median
            row[k + "_min"] = vals[0]
            row[k + "_max"] = vals[-1]
        national.append(row)

    # ---------- 各省在典型档位上的排名 ----------
    ranking = {}
    for s in SALARIES:
        idx = SALARIES.index(s)
        arr = [{"id": r["id"], "name": r["name"], "ratio": r["rows"][idx]["ratio"],
                "company_cost": r["rows"][idx]["company_cost"],
                "final_value": r["rows"][idx]["final_value"]} for r in results]
        arr.sort(key=lambda x: -x["ratio"])
        ranking[str(s)] = arr

    # ---------- 省级汇总（3000/8000/20000/50000档）----------
    province_summary = []
    for r in results:
        idx = {s: i for i, s in enumerate(SALARIES)}
        province_summary.append({
            "id": r["id"], "name": r["name"], "short": r["short"], "region": r["region"],
            "ratio_3000": r["rows"][idx[3000]]["ratio"],
            "ratio_8000": r["rows"][idx[8000]]["ratio"],
            "ratio_20000": r["rows"][idx[20000]]["ratio"],
            "ratio_50000": r["rows"][idx[50000]]["ratio"],
            "cost_8000": r["rows"][idx[8000]]["company_cost"],
            "final_8000": r["rows"][idx[8000]]["final_value"],
        })
    province_summary.sort(key=lambda x: -x["ratio_8000"])

    # ---------- 关键收入段分析所需的结构化数据 ----------
    analysis = {}
    for r in results:
        prov = next(p for p in provinces if p["id"] == r["id"])
        floor_binds = [s for s in SALARIES if s < prov["base"]["pension"][0]]
        cap_binds = [s for s in SALARIES if s > prov["base"]["pension"][1]]
        pf_cap_binds = [s for s in SALARIES if s > prov["pf"]["hi"]]
        below_minwage = [s for s in SALARIES if s < prov["min_wage"]]
        analysis[r["id"]] = {
            "pension_floor": prov["base"]["pension"][0],
            "pension_cap": prov["base"]["pension"][1],
            "pf_floor": prov["pf"]["lo"],
            "pf_cap": prov["pf"]["hi"],
            "min_wage": prov["min_wage"],
            "floor_binds_salaries": floor_binds,
            "cap_binds_salaries": cap_binds,
            "pf_cap_binds_salaries": pf_cap_binds,
            "below_min_wage_salaries": below_minwage,
        }

    out = {
        "meta": META,
        "provinces": [],
        "results": [{"id": r["id"], "name": r["name"], "short": r["short"], "region": r["region"],
                     "rows": r["rows"], "rows_display": [round_row(x) for x in r["rows"]]}
                    for r in results],
        "national": national,
        "ranking": ranking,
        "province_summary": province_summary,
        "analysis": analysis,
        "validation": {"errors": errors, "checked": len(provinces) * len(SALARIES)},
    }
    for p in provinces:
        out["provinces"].append({
            "id": p["id"], "name": p["name"], "short": p["short"], "region": p["region"],
            "base": p["base"], "rates": p["rates"], "pf": p["pf"], "min_wage": p["min_wage"],
            "conf": p["conf"], "src": p["src"], "notes": p["notes"],
        })

    with open(os.path.join(DATA_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    # ---------- CSV 输出（便于核对）----------
    def write_csv(path, header, rows):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(",".join(header) + "\n")
            for r in rows:
                f.write(",".join(str(x) for x in r) + "\n")

    for r in results:
        header = ["税前月薪", "单位社保", "单位公积金", "公司实际成本", "个人社保", "个人公积金",
                  "月均个税", "到手现金", "估算消费间接税", "最终消费价值", "消费价值/公司成本"]
        rows = []
        disp = [round_row(y) for y in r["rows"]]
        for x in disp:
            rows.append([x["salary"], x["unit_social"], x["unit_pf"], x["company_cost"],
                         x["ind_social"], x["ind_pf"], x["monthly_tax"], x["cash"],
                         x["indirect_tax"], x["final_value"], f'{x["ratio"]*100:.1f}%'])
        write_csv(os.path.join(DATA_DIR, "table_%s.csv" % r["id"]), header, rows)

    # 全国等权平均表
    header = ["税前月薪", "平均单位社保", "平均单位公积金", "平均公司成本", "平均个人社保",
              "平均个人公积金", "平均月均个税", "平均到手现金", "平均消费间接税",
              "平均最终消费价值", "消费价值/公司成本(均值)", "消费价值/公司成本(中位)"]
    rows = []
    for n in national:
        rows.append([n["salary"], round(n["unit_social"]), round(n["unit_pf"]), round(n["company_cost"]),
                     round(n["ind_social"]), round(n["ind_pf"]), round(n["monthly_tax"]), round(n["cash"]),
                     round(n["indirect_tax"]), round(n["final_value"]),
                     f'{n["ratio"]*100:.1f}%', f'{n["ratio_median"]*100:.1f}%'])
    write_csv(os.path.join(DATA_DIR, "table_national_average.csv"), header, rows)

    print("省份数:", len(provinces), "档位数:", len(SALARIES))
    print("校验组合数:", out["validation"]["checked"], " 校验失败:", len(errors))
    if errors:
        for e in errors[:20]:
            print("  !!", e)
    print("\n全国等权平均：最终消费价值/公司成本")
    for n in national:
        print("  月薪%7d -> 成本%9.0f 消费%9.0f 占比%5.1f%% (中位%5.1f%%)" % (
            n["salary"], n["company_cost"], n["final_value"], n["ratio"] * 100, n["ratio_median"] * 100))
    print("\n8000元档占比排名（前5/后5）：")
    for x in province_summary[:5]:
        print("  %-8s %.1f%%" % (x["short"], x["ratio_8000"] * 100))
    for x in province_summary[-5:]:
        print("  %-8s %.1f%%" % (x["short"], x["ratio_8000"] * 100))


if __name__ == "__main__":
    main()
