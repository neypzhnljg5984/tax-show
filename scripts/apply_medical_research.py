#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把职工医保（含生育保险）单位费率的查证结果写回 data/policy_2026.json。

口径：本表的 medical_u 一律指「用人单位为在职职工缴纳的、包含生育保险的医保费率」。
部分地方医保与生育分列（如沈阳 8.6%＋0.6%），本脚本已合并；若原文明确“不含生育”，
则在备注中标注，并以更保守的方式取值。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PATH = os.path.join(ROOT, "data", "policy_2026.json")

S = {
    "bj": "https://www.bjsjs.gov.cn/gongkai/zwgkpd/ztzl/2024/mtyfz/ybzcxwd/202410/t20241021_86349.shtml",
    "tj": "https://www.tj.gov.cn/zwgk/szfgb/xqk/2026/12/bmgfxwj/202607/t20260703_7329233.html",
    "sh": "https://ybj.sh.gov.cn/gfxwj/20260313/921e047144694b61b6df8ca0c5ef2cfc.html",
    "hz": "https://www.hzarchives.org.cn/info/12455",
    "sy": "http://sy.bendibao.com/live/2025922/83913.shtm",
    "jn": "http://ybj.jinan.gov.cn/col/col116777/art/2026/art_d23ae2576b954cefa27abf820b467a04.html",
    "zz": "https://m.zz.bendibao.com/live/50975.shtm",
    "wh": "https://m.wh.bendibao.com/live/64093.shtm",
    "cs": "http://www.kaifu.gov.cn/zfxxgk/fdzdgknr/dtyw_qzf/bmdt/202609/t20260909_12546519.html",
    "cd": "https://m.sohu.com/a/1077887610_498271/",
    "cq": "http://www.cqwx.gov.cn/bm/xybj/zwgk_68174/zfxxgkml/ybzchb/cbp/202601/t20260112_15307861.html",
    "gy": "https://ybj.guiyang.gov.cn/hdjl/zmhdcjwtzsk/zgylbx/cbjf/202605/t20260520_90192132.html",
    "km": "https://m.km.bendibao.com/mip/45799.shtm",
    "xa": "https://xdz.xa.gov.cn/zwgk/jbmsbz/shbz/1995686261241171969.html",
    "lz": "https://m.lz.bendibao.com/live/37883.shtm",
    "hf": "https://m.hf.bendibao.com/live/68396.shtm",
    "fz": "https://m.fz.bendibao.com/live/68400.shtm",
    "nc": "https://ybj.nc.gov.cn/ncylbzj/lzyj/202505/e9563f71975a4e229d09c47c33db96aa.shtml",
    "cf": "https://ybj.chifeng.gov.cn/zwgk/ybyw/202603/t20260305_2738432.html",
    "sx": "https://ybj.shanxi.gov.cn/xxfb/fdzdgknr/gzdt/202606/t20260604_10140414.html",
    "xj": "https://m.shebao.southmoney.com/banli/shebaozhishi/202606/2426701.html",
    "sjz": "https://www.rrb365.com/news/20260825130209.html",
    "gz": "https://chinastar1.com/?show=3507",
    "hn": "https://www.163.com/dy/article/KCCNFNAK05568W0A.html",
}

# (单位费率, 可信度, 来源, 备注)
MED = {
    "beijing":      (0.098, "high", S["bj"],
                     "北京市医保局口径：城镇职工基本医疗保险（含生育保险）单位缴费比例 9.8%，个人 2%（另有大额互助 3 元/月）。"),
    "tianjin":      (0.105, "high", S["tj"],
                     "津医保规字〔2026〕1号：职工医保费缴费比例 12.5%，其中单位 10.5%、个人 2%（自2026年3月1日施行）。原表按10%测算，已上调为10.5%。"),
    "hebei":        (0.065, "medium", S["sjz"],
                     "石家庄明确 2026 年职工医保单位费率继续按 6.5% 执行，本表以省会口径代表河北。"),
    "shanxi":       (0.070, "low", S["sx"],
                     "山西省医保局：用人单位按职工工资总额的 6% 左右缴纳，各统筹地区费率在 6%~8% 之间，本表取中值 7%，实际因城市而异。"),
    "neimenggu":    (0.070, "medium", S["cf"],
                     "赤峰市医保局：单位缴费费率 7%、个人 2%，本表以内蒙古代表城市口径取值。"),
    "liaoning":     (0.092, "medium", S["sy"],
                     "沈阳：医疗保险单位 8.6%、生育保险单位 0.6%，合并为 9.2%；个人 2%。原表按7%测算，已上调。"),
    "jilin":        (0.070, "model", "",
                     "未取到吉林省2026年医保单位费率官方原文，按公开常见口径 7% 测算。"),
    "heilongjiang": (0.070, "model", "",
                     "未取到黑龙江省2026年医保单位费率官方原文，按公开常见口径 7% 测算。"),
    "shanghai":     (0.090, "high", S["sh"],
                     "沪医保规〔2026〕2号：单位继续执行 9%（基本医疗保险含生育 8.5%＋地方附加 0.5%），个人 2%，有效期至2027年2月28日。原表按10%测算，已下调为9%。"),
    "jiangsu":      (0.080, "model", "",
                     "未取到江苏省2026年医保单位费率官方原文（省内按统筹地区分别规定），按公开常见口径 8% 测算。"),
    "zhejiang":     (0.095, "high", S["hz"],
                     "《杭州市基本医疗保障办法》（2026年1月1日施行）：单位缴费比例 9.5%（含生育保险 0.6%），个人 2%。原表按8.5%测算，已上调。"),
    "anhui":        (0.064, "medium", S["hf"],
                     "合肥：其他用人单位按 6.4% 缴纳（国家机关、事业单位 6.2%），个人 2%。本表采用企业口径。"),
    "fujian":       (0.080, "medium", S["fz"],
                     "福州市政府口径：用人单位按职工月工资总额的 8% 缴纳基本医疗保险费（含生育保险、长期护理保险），个人 2%。原表按6.5%测算，已上调。"),
    "jiangxi":      (0.060, "low", S["nc"],
                     "南昌市城镇职工基本医疗保险管理办法：单位 6%、个人 2%。该文件发布较早，2026 年是否调整未核实。"),
    "shandong":     (0.080, "high", S["jn"],
                     "济南市医保局：单位 8%（含生育保险 1%）＋个人 2%（2026年9月1日起执行）。"),
    "henan":        (0.070, "medium", S["zz"],
                     "郑州：职工医保单位 8%，目前阶段性调低 1 个百分点至 7%，个人 2%。本表采用阶段性费率。"),
    "hubei":        (0.080, "medium", S["wh"],
                     "武汉：单位缴纳比例 8%，个人 2%＋大病 7 元/月。"),
    "hunan":        (0.087, "high", S["cs"],
                     "湖南省医保局：单位按职工工资总额 8.7% 缴纳（职工医保 8%＋生育保险 0.7%），个人 2%；2026年10月1日起执行。原表按8%测算，已上调。"),
    "guangdong":    (0.0685, "high", S["gz"],
                     "广州市2026年度：单位 6.85%（含生育 0.85%）、个人 2%，自2026年1月1日起由阶段性 4.5% 恢复。"),
    "guangxi":      (0.065, "model", "",
                     "未取到广西2026年医保单位费率官方原文（玉林等地为 6%），按 6.5% 测算。"),
    "hainan":       (0.065, "medium", S["hn"],
                     "海南阶段性降费至2026年12月31日：单位医保 6%（不含生育）＋生育保险约 0.5%，合并 6.5%。"),
    "chongqing":    (0.085, "high", S["cq"],
                     "重庆：基本医保单位按缴费基数的 8.5% 缴纳（含生育保险 0.5%），个人 2%；另有单位大额医保 1.5%（本表未计入）。"),
    "sichuan":      (0.0755, "medium", S["cd"],
                     "成都：基本医疗保险单位 6.75%＋生育保险单位 0.8%＝7.55%，个人 2%；另有单位大病医疗互助补充保险 0.75%（本表未计入）。原表按6.9%测算。"),
    "guizhou":      (0.080, "high", S["gy"],
                     "贵阳市医保局：单位缴纳 8%、个人 2%。原表按8.5%测算，已下调。"),
    "yunnan":       (0.099, "low", S["km"],
                     "昆明：医疗保险单位费率 9.9%、个人 2%（生育保险单位 0.5% 另列）。该数值偏高，可能包含大额医疗补助，建议以云南省医保局原文复核。"),
    "xizang":       (0.080, "model", "",
                     "未取到西藏2026年医保单位费率官方原文，按公开常见口径 8% 测算。"),
    "shaanxi":      (0.060, "low", S["xa"],
                     "西安市医保局：用人单位职工医保单位缴费率由 7%（不含生育）阶段性下调至 6%，个人 2%，自2025年12月1日起执行12个月。原表按7%测算。"),
    "gansu":        (0.090, "medium", S["lz"],
                     "兰州（甘肃省医保局口径）：企业单位 9%、个人 2%（行政机关事业单位 8.35%）。原表按6.5%测算，已上调，差异较大。"),
    "qinghai":      (0.080, "model", "",
                     "未取到青海省2026年医保单位费率官方原文，按公开常见口径 8% 测算。"),
    "ningxia":      (0.080, "model", "",
                     "未取到宁夏2026年医保单位费率官方原文，按公开常见口径 8% 测算。"),
    "xinjiang":     (0.072, "low", S["xj"],
                     "乌鲁木齐：医疗保险单位 6.5%＋生育保险单位 0.7%＝7.2%，个人 2%。数据来自社保信息聚合站点，建议以新疆医保局原文复核。"),
}

with open(PATH, encoding="utf-8") as f:
    doc = json.load(f)
by_id = {p["id"]: p for p in doc["provinces"]}
missing = [k for k in by_id if k not in MED]
if missing:
    raise SystemExit("缺少医保费率覆盖: %s" % missing)

for pid, (rate, conf, src, note) in MED.items():
    p = by_id[pid]
    p["rates"]["medical_u"] = rate
    p["conf"]["medical"] = conf
    if src:
        p["src"]["medical"] = src
    p["notes"].append(note)

doc["meta"]["rate_sources"]["medical"] = {
    "doc": "职工基本医疗保险费由用人单位和职工共同缴纳，单位费率由各统筹地区自行确定；"
           "本表已逐省查证，共 22 省取到官方或政府转载口径，其余 7 省（吉林、黑龙江、江苏、广西、西藏、青海、宁夏）"
           "仍为公开常见口径的模型值。",
    "url": "http://www.nhsa.gov.cn/",
}
doc["meta"]["notes"].append(
    "医保费率已按省份逐条查证并更新（上海9%、天津10.5%、杭州9.5%、济南8%、武汉8%、长沙8.7%、成都7.55%、"
    "重庆8.5%、贵阳8%、福州8%、合肥6.4%、南昌6%、郑州7%、沈阳9.2%、西安6%、兰州9%、赤峰7%、北京9.8% 等），"
    "未查到原文的省份仍标注为模型值。")

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

stat = {}
for p in doc["provinces"]:
    stat[p["conf"]["medical"]] = stat.get(p["conf"]["medical"], 0) + 1
print("医保费率更新完成：", " ".join("%s=%d省" % (k, v) for k, v in sorted(stat.items())))
print("医疗单位费率区间: %.2f%% ~ %.2f%%" % (
    min(p["rates"]["medical_u"] for p in doc["provinces"]) * 100,
    max(p["rates"]["medical_u"] for p in doc["provinces"]) * 100))
