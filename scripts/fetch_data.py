#!/usr/bin/env python3
"""
抓取台股季配息 ETF 與綠能環保類股資料,輸出 data.json 供 build_report.py 使用。

資料來源(全部為 TWSE 公開 OpenAPI,無需金鑰):
  - ETF 歷次收益分配公告: https://www.twse.com.tw/rwd/zh/ETF/etfDiv
  - 全市場每日收盤行情: https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
  - 個股歷史收盤價(波動率用): https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY
  - 上市公司基本資料(產業別): https://openapi.twse.com.tw/v1/opendata/t187ap03_L
"""

import json
import re
import ssl
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
DATA_PATH = BASE_DIR / "docs" / "data.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (etf-report-bot)"}

ETF_DIV_URL = "https://www.twse.com.tw/rwd/zh/ETF/etfDiv?response=json"
STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
COMPANY_INFO_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TAIEX_URL = "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date}&selectType=ALL"


def http_get_json(url, retries=3, timeout=20):
    last_err = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1)
    raise RuntimeError(f"請求失敗: {url} ({last_err})")


def roc_to_iso(roc_str):
    """'115年10月19日' -> '2026-10-19'; '1151016' -> '2026-10-16'"""
    m = re.match(r"(\d{2,3})年(\d{1,2})月(\d{1,2})日", roc_str)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        return date(y + 1911, mo, d).isoformat()
    m2 = re.match(r"(\d{3})(\d{2})(\d{2})$", roc_str)
    if m2:
        y, mo, d = (int(x) for x in m2.groups())
        return date(y + 1911, mo, d).isoformat()
    return None


def fetch_etf_distributions():
    data = http_get_json(ETF_DIV_URL)
    return data.get("data", [])


def classify_etf_frequency(rows, min_events, max_events):
    by_code = defaultdict(list)
    for row in rows:
        by_code[row[0]].append(row)

    result = {}
    for code, events in by_code.items():
        name = events[0][1]
        amounts, dated_events = [], []
        for e in events:
            iso = roc_to_iso(e[2])
            amt = None
            if e[5] is not None:
                try:
                    amt = float(e[5])
                    amounts.append(amt)
                except (TypeError, ValueError):
                    pass
            if iso:
                dated_events.append((iso, amt))
        dated_events.sort(key=lambda x: x[0])
        event_count = len(events)
        result[code] = {
            "name": name,
            "event_count": event_count,
            "is_quarterly": min_events <= event_count <= max_events,
            "total_amount": sum(amounts),
            "amount_count": len(amounts),
            "dated_events": dated_events,
        }
    return result


def latest_and_next(dated_events, today):
    """回傳 (最新一筆已公告日期+金額, 下次預估資訊)"""
    if not dated_events:
        return None, None
    past_or_today = [e for e in dated_events if e[0] <= today.isoformat()]
    future = [e for e in dated_events if e[0] > today.isoformat()]

    latest = past_or_today[-1] if past_or_today else dated_events[0]

    if future:
        next_date = future[0][0]
        confirmed = True
    else:
        last_date = date.fromisoformat(dated_events[-1][0])
        nd = last_date
        while nd < today:
            nd = nd + timedelta(days=91)
        next_date = nd.isoformat()
        confirmed = False

    days = (date.fromisoformat(next_date) - today).days
    return {"date": latest[0], "amount": latest[1]}, {
        "date": next_date,
        "confirmed": confirmed,
        "days": days,
    }


def fetch_etf_prices(codes):
    data = http_get_json(STOCK_DAY_ALL_URL)
    out, as_of = {}, None
    wanted = set(codes)
    for row in data:
        if row.get("Code") in wanted:
            try:
                out[row["Code"]] = float(row.get("ClosingPrice") or 0)
                as_of = roc_to_iso(row["Date"])
            except ValueError:
                continue
    return out, as_of


def fetch_recent_closes(stock_no, months, delay):
    today = date.today()
    closes = []
    y, m = today.year, today.month
    for _ in range(months):
        ym = f"{y}{m:02d}01"
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={ym}&stockNo={stock_no}&response=json"
        try:
            j = http_get_json(url, retries=2)
        except RuntimeError:
            j = None
        if j and j.get("stat") == "OK":
            for row in j.get("data", []):
                try:
                    closes.append(float(str(row[6]).replace(",", "")))
                except (ValueError, IndexError):
                    continue
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        time.sleep(delay)
    return closes


def annualized_volatility_pct(closes):
    if len(closes) < 5:
        return None
    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1]
    ]
    if len(returns) < 5:
        return None
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return (var ** 0.5) * (252 ** 0.5) * 100


def fetch_green_energy_top10(industry_code, top_n):
    companies = http_get_json(COMPANY_INFO_URL)
    codes = {c["公司代號"]: c["公司簡稱"] for c in companies if c.get("產業別") == industry_code}

    quotes = http_get_json(STOCK_DAY_ALL_URL)
    rows, as_of = [], None
    for r in quotes:
        code = r.get("Code")
        if code not in codes:
            continue
        try:
            close = float(r["ClosingPrice"])
            chg = float(r["Change"])
            prev = close - chg
            pct = chg / prev * 100 if prev > 0 else None
        except (KeyError, ValueError):
            continue
        if pct is None:
            continue
        as_of = roc_to_iso(r["Date"])
        rows.append({"code": code, "name": codes[code], "close": close, "change": chg, "pct": pct})

    rows.sort(key=lambda r: -r["pct"])
    return rows[:top_n], as_of, len(codes)


def fetch_taiex():
    """發行量加權股價指數(TAIEX)最新一筆收盤值與漲跌"""
    rows = http_get_json(TAIEX_URL)
    if not rows:
        return None
    last = rows[-1]
    try:
        value = float(str(last["TAIEX"]).replace(",", ""))
        change = float(str(last["Change"]).replace(",", ""))
    except (KeyError, ValueError):
        return None
    prev = value - change
    pct = change / prev * 100 if prev else None
    return {
        "date": roc_to_iso(last["Date"]),
        "value": value,
        "change": change,
        "pct": pct,
    }


def fetch_institutional_flow(date_iso, top_n):
    """三大法人(外資+投信+自營商)當日買賣超排行,回傳買超/賣超各前 top_n 檔(單位:張)"""
    date_str = date_iso.replace("-", "")
    data = http_get_json(T86_URL.format(date=date_str), retries=2)
    rows = data.get("data", []) if isinstance(data, dict) else []
    flows = []
    for r in rows:
        try:
            code = r[0].strip()
            name = r[1].strip()
            net_shares = int(r[18].replace(",", ""))
        except (IndexError, ValueError, AttributeError):
            continue
        flows.append({"code": code, "name": name, "net_lots": round(net_shares / 1000)})

    flows.sort(key=lambda x: -x["net_lots"])
    top_buy = [f for f in flows if f["net_lots"] > 0][:top_n]
    top_sell = sorted([f for f in flows if f["net_lots"] < 0], key=lambda x: x["net_lots"])[:top_n]
    return top_buy, top_sell


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    today = date.today()

    print("[1/4] 下載 ETF 收益分配公告 ...", flush=True)
    div_rows = fetch_etf_distributions()
    freq_info = classify_etf_frequency(
        div_rows, config["min_events_for_quarterly"], config["max_events_for_quarterly"]
    )
    quarterly_codes = [c for c, v in freq_info.items() if v["is_quarterly"]]
    if config.get("exclude_bond_etfs", True):
        quarterly_codes = [c for c in quarterly_codes if not c.endswith("B")]
    print(f"      季配息候選 ETF: {len(quarterly_codes)} 支")

    print("[2/4] 下載 ETF 現價 ...", flush=True)
    prices, price_as_of = fetch_etf_prices(quarterly_codes)

    candidates = []
    for code in quarterly_codes:
        price = prices.get(code)
        if not price:
            continue
        lot_price = price * 1000
        if lot_price > config["max_lot_price"]:
            continue
        info = freq_info[code]
        if info["amount_count"] == 0:
            continue
        annualized_distribution = (info["total_amount"] / info["amount_count"]) * 4
        yield_pct = annualized_distribution / price * 100
        if yield_pct < config["min_dividend_yield_pct"]:
            continue
        latest, next_info = latest_and_next(info["dated_events"], today)
        candidates.append({
            "code": code,
            "name": info["name"],
            "price": price,
            "event_count_this_year": info["event_count"],
            "dividend_yield_pct_est": yield_pct,
            "latest_distribution": latest,
            "next_distribution": next_info,
        })
    print(f"      價格+殖利率初篩: {len(candidates)} 支")

    print("[3/4] 估算近期波動率 ...", flush=True)
    for c in candidates:
        closes = fetch_recent_closes(
            c["code"], config["volatility_lookback_months"], config["request_delay_seconds"]
        )
        c["annualized_volatility_pct"] = annualized_volatility_pct(closes)

    etfs = [
        c for c in candidates
        if c["annualized_volatility_pct"] is not None
        and c["annualized_volatility_pct"] <= config["max_annualized_volatility_pct"]
    ]
    etfs.sort(key=lambda c: (-c["dividend_yield_pct_est"], c["annualized_volatility_pct"]))
    etfs = etfs[: config["top_n_etf"]]

    print("[4/5] 下載綠能環保類股資料 ...", flush=True)
    green_top, green_as_of, green_total = fetch_green_energy_top10(
        config["green_energy_industry_code"], config["top_n_green_energy"]
    )

    print("[5/5] 下載加權指數與三大法人買賣超 ...", flush=True)
    taiex = fetch_taiex()
    try:
        top_buy, top_sell = fetch_institutional_flow(price_as_of, config["top_n_institutional"])
    except RuntimeError as exc:
        print(f"      三大法人資料抓取失敗,略過: {exc}")
        top_buy, top_sell = [], []

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "price_as_of": price_as_of,
        "etfs": etfs,
        "green_energy": {
            "as_of": green_as_of,
            "universe_count": green_total,
            "top": green_top,
        },
        "taiex": taiex,
        "institutional_flow": {
            "as_of": price_as_of,
            "top_buy": top_buy,
            "top_sell": top_sell,
        },
        "config": config,
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成,寫入 {DATA_PATH}(ETF {len(etfs)} 支,綠能股 {len(green_top)} 支)")


if __name__ == "__main__":
    main()
