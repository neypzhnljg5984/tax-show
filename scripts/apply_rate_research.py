#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把费率查证结果写回 data/policy_2026.json。

背景：初版把「养老/失业/工伤」费率统一当作模型值，这是偷懒。
经查证：
  · 养老保险单位费率全国统一 16%（国办发〔2019〕13号），仅个别省份经国务院同意执行更低费率；
  · 失业保险实行总费率 1% 的阶段性降费政策（人社部发〔2024〕40号），单位/个人分配各省略有差异；
  · 工伤保险一类行业全国基准费率 0.2%（人社部发〔2015〕71号），部分省份按结存情况阶段性下调 20% 或 50%。
本脚本按查证结果逐省覆盖费率，并把可信度从"整组一个标签"改为"逐险种一个标签"。
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PATH = os.path.join(ROOT, "data", "policy_2026.json")

# ---- 全国性依据 ----
S_PENSION = "https://www.gz.gov.cn/ysgz/tzzc/gjzc/content/post_5618402.html"       # 国办发〔2019〕13号
S_INJURY = "https://www.beijing.gov.cn/zhengce/zhengcefagui/201905/t20190522_58707.html"  # 人社部发〔2015〕71号
S_UNEMP = "https://law.esnai.cn/do.aspx?controller=home&action=show&lawid=219820"  # 人社部发〔2024〕40号（经沪人社规〔2024〕25号引用）
S_RATE2026 = "http://g0-cache.51shebao.com/article/detail/8258"   # 2026年多地费率调整汇总
S_RATE2025 = "http://g0-cache.51shebao.com/article/detail/8101"   # 2025年多地降费汇总
S_UNEMP2025 = "https://www.163.com/dy/article/KCCNFNAK05568W0A.html"  # 2025年失业/工伤/医保降费汇总
S_RRB = "https://www.rrb365.com/news/20260825130209.html"

# 每省覆盖：键为省 id，值为需覆盖的字段。
# pension/medical/unemp 为 (单位, 个人)；injury 为单位费率。
# conf_* 取值 high（官方原文）/ medium（官方转述、转载）/ low（跨年沿用或存在阶段性政策不确定）/ model（统一假设）
PATCH = {
    "beijing": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.008, 0.002), conf_unemp="medium",
        injury=0.002, conf_injury="medium",
        note_rate="北京失业保险长期执行单位0.8%、个人0.2%；工伤一类行业按全国基准0.2%。"),

    "tianjin": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "hebei": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        medical=(0.065, 0.02), conf_medical="medium", src_medical=S_RRB,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium",
        note_rate="河北医保单位费率6.5%（石家庄市明确2026年继续按6.5%执行）。"),

    "shanxi": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "neimenggu": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="high", src_unemp=S_UNEMP2025,
        injury=0.001, conf_injury="low", src_injury=S_UNEMP2025,
        note_rate="内蒙古失业保险单位、个人各0.5%（官方转述）。工伤保险按基金结存月数下调：结存≥24个月下调50%（一类约0.1%）、18-23个月下调20%；该阶段性政策原执行至2025年底，2026年是否延续未核实。"),

    "liaoning": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="high",
        src_injury="https://www.ln.gov.cn/web/qmzx/5.15zwgkr(d20j)/zcztc/msbz/2026051514464579096/index.shtml",
        note_rate="辽宁辽人社〔2026〕1号：自2026年1月1日起一类行业基准费率由0.3%下调为0.2%（执行至2028年12月31日）。"),

    "jilin": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium", src_injury=S_RATE2026,
        note_rate="吉林工伤按全国基准费率并实行浮动：一类行业只上浮不下浮，基准费率为0.2%。"),

    "heilongjiang": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "shanghai": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        medical=(0.10, 0.02), conf_medical="low",
        src_medical="http://g0-cache.51shebao.com/article/detail/8101",
        unemp=(0.005, 0.005), conf_unemp="high", src_unemp=S_UNEMP,
        injury=0.002, conf_injury="high",
        src_injury="https://law.esnai.cn/view/229964/",
        note_rate="上海失业单位、个人各0.5%（沪人社规〔2024〕25号）。工伤一类按全国基准0.2%（沪人社规〔2026〕2号，2026-01-01起）。医保单位费率原本9.5%＋地方附加0.5%＝10%，阶段性降至9%的政策有效期至2026年2月28日，本表按恢复后的10%测算，若已延续降费则实际为9%。"),

    "jiangsu": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="high",
        src_injury="http://www.js.gov.cn/art/2024/1/9/art_64797_11121019.html",
        note_rate="江苏苏人社规〔2023〕2号：一类行业基准费率0.2%，且一类行业不向下浮动（有效期至2028年12月31日）。"),

    "zhejiang": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="high", src_unemp=S_UNEMP2025,
        injury=0.002, conf_injury="medium",
        note_rate="浙江失业保险单位、个人各0.5%（阶段性降费，官方转述）；养老保险单位费率经政策解读确认为16%。"),

    "anhui": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "fujian": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        medical=(0.065, 0.02), conf_medical="low", src_medical=S_RATE2026,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="high", src_injury=S_RATE2026,
        note_rate="福建明确一类至八类工伤基准费率为0.2%~1.9%（按全国基准）。福建医保费率存在城市差异：2026年厦门为单位7.5%、个人2%。"),

    "jiangxi": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "shandong": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.0016, conf_injury="low", src_injury=S_RATE2025,
        note_rate="山东2025年度工伤保险行业基准费率整体下调20%（一类0.2%→0.16%）；2026年度是否继续按下调后费率执行未核实。"),

    "henan": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="low",
        note_rate="河南历年多次实施阶段性降低工伤保险费率，2026年是否仍有下调未核实，本表按全国基准0.2%测算。"),

    "hubei": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "hunan": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "guangdong": dict(
        pension=(0.15, 0.08), conf_pension="low", src_pension=S_PENSION,
        medical=(0.0685, 0.02), conf_medical="high", src_medical=S_RATE2026,
        unemp=(0.008, 0.002), conf_unemp="medium",
        injury=0.002, conf_injury="low",
        note_rate="广东医保采用广州市2026年度口径：单位6.85%（含生育0.85%）、个人2%，自2026年1月1日起由阶段性4.5%恢复。失业保险单位0.8%、个人0.2%。养老保险单位费率按15%测算（低于全国16%），建议以粤人社最新文件复核。"),

    "guangxi": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "hainan": dict(
        pension=(0.14, 0.08), conf_pension="medium",
        unemp=(0.005, 0.005), conf_unemp="high", src_unemp=S_UNEMP2025,
        injury=0.001, conf_injury="low", src_injury=S_UNEMP2025,
        medical=(0.065, 0.02), conf_medical="medium", src_medical=S_UNEMP2025,
        note_rate="海南企业养老单位费率14%（低于全国16%）。医保单位费率6%（不含生育，政策至2026年12月31日）＋生育保险后约6.5%。工伤保险按降费政策在现行费率基础上下调50%（一类约0.1%），原执行至2025年底，2026年是否延续未核实。"),

    "chongqing": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "sichuan": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.006, 0.004), conf_unemp="high", src_unemp=S_UNEMP2025,
        injury=0.0024, conf_injury="high", src_injury=S_RATE2026,
        note_rate="四川失业单位0.6%、个人0.4%（官方转述）。工伤自2026年7月1日起一类行业基准费率0.24%（即按全国基准下调20%）。"),

    "guizhou": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "yunnan": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "xizang": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "shaanxi": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium", src_injury=S_RATE2025,
        note_rate="陕西延续阶段性降低工伤保险费率，但明确一类行业费率不下调，故一类为0.2%。"),

    "gansu": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.007, 0.003), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "qinghai": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.0016, conf_injury="low", src_injury=S_RATE2025,
        note_rate="青海2025年阶段性降低工伤保险费率：按行业基准费率下调20%（一类0.2%→0.16%），原执行至2025年12月31日，2026年是否延续未核实。"),

    "ningxia": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),

    "xinjiang": dict(
        pension=(0.16, 0.08), conf_pension="high", src_pension=S_PENSION,
        unemp=(0.005, 0.005), conf_unemp="medium",
        injury=0.002, conf_injury="medium"),
}

# 未逐省核实的医疗费率统一标注为模型值（保留原数值），并补充缺失的省
MEDICAL_MODEL = {
    "beijing": 0.098, "tianjin": 0.10, "shanxi": 0.07, "neimenggu": 0.065, "liaoning": 0.07,
    "jilin": 0.07, "heilongjiang": 0.07, "jiangsu": 0.08, "zhejiang": 0.085, "anhui": 0.065,
    "jiangxi": 0.065, "henan": 0.08, "hubei": 0.08, "hunan": 0.08, "guangxi": 0.065,
    "chongqing": 0.085, "guizhou": 0.085, "yunnan": 0.08, "xizang": 0.08, "gansu": 0.065,
    "ningxia": 0.08, "xinjiang": 0.08,
}

with open(PATH, encoding="utf-8") as f:
    doc = json.load(f)

by_id = {p["id"]: p for p in doc["provinces"]}
missing = [k for k in by_id if k not in PATCH]
if missing:
    print("!! 缺少费率覆盖的省份:", missing)
    sys.exit(1)

for pid, patch in PATCH.items():
    p = by_id[pid]
    r = p["rates"]
    c = p["conf"]
    s = p["src"]

    if "pension" in patch:
        u, i = patch["pension"]
        r["pension_u"], r["pension_i"] = u, i
    if "medical" in patch:
        u, i = patch["medical"]
        r["medical_u"], r["medical_i"] = u, i
    elif pid in MEDICAL_MODEL:
        r["medical_u"] = MEDICAL_MODEL[pid]
        c["medical"] = "model"
    if "unemp" in patch:
        u, i = patch["unemp"]
        r["unemp_u"], r["unemp_i"] = u, i
    if "injury" in patch:
        r["injury_u"] = patch["injury"]

    # 逐险种可信度
    c["pension"] = patch.get("conf_pension", "model")
    c["unemp"] = patch.get("conf_unemp", "model")
    c["injury"] = patch.get("conf_injury", "model")
    if "conf_medical" in patch:
        c["medical"] = patch["conf_medical"]
    elif "medical" not in patch:
        c.setdefault("medical", "model")

    for key in ("pension", "medical", "unemp", "injury"):
        sk = "src_" + key
        if sk in patch:
            s[key] = patch[sk]
        elif key == "pension":
            s["pension"] = S_PENSION
        elif key == "injury":
            s["injury"] = S_INJURY
        elif key == "unemp":
            s["unemp"] = S_UNEMP

    if "note_rate" in patch:
        p["notes"].append(patch["note_rate"])

    c.pop("rates", None)   # 用逐险种可信度替代原来的整组标签

doc["meta"]["rate_sources"] = {
    "pension": {"doc": "国办发〔2019〕13号《降低社会保险费率综合方案》：企业职工基本养老保险单位缴费比例高于16%的可降至16%；个人缴费比例8%全国统一。", "url": S_PENSION},
    "unemp": {"doc": "人社部发〔2024〕40号等延续实施失业保险援企稳岗政策：失业保险继续执行1%的总费率（各省在单位与个人之间分配略有差异）。", "url": S_UNEMP},
    "injury": {"doc": "人社部发〔2015〕71号：工伤保险行业基准费率一类至八类为0.2%、0.4%、0.7%、0.9%、1.1%、1.3%、1.6%、1.9%。", "url": S_INJURY},
}
doc["meta"]["notes"].append(
    "费率数据已按险种逐省查证：养老与工伤一类行业有全国统一基准，失业为全国1%总费率；"
    "标注为“模型值”的医疗费率及少数存在阶段性政策的工伤费率，仍为公开常见口径，未能逐省核到2026年官方原文。")

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

print("已更新", len(PATCH), "个省份的费率与逐险种可信度")
stat = {}
for p in doc["provinces"]:
    for k in ("pension", "medical", "unemp", "injury"):
        stat[k + ":" + p["conf"][k]] = stat.get(k + ":" + p["conf"][k], 0) + 1
for k in sorted(stat):
    print("  %-18s %d 省" % (k, stat[k]))
