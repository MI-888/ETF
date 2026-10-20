#!/usr/bin/env python3
"""讀取 docs/data.json,產生 docs/index.html(台股季配息ETF篩選報告)。"""

import html
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "docs" / "data.json"
OUTPUT_PATH = BASE_DIR / "docs" / "index.html"

CSS = """
  :root {
    --bg: #EDF2E7; --bg-grid: rgba(30, 43, 32, 0.055);
    --surface: #F8FBF4; --surface-raised: #FFFFFF;
    --ink: #1E2B20; --ink-soft: #51604F; --ink-faint: #7C8B79;
    --accent: #B8872E; --accent-deep: #8C6418; --accent-wash: rgba(184, 135, 46, 0.12);
    --good: #3D7A5C; --warn: #A6482E; --warn-wash: rgba(166, 72, 46, 0.1);
    --rule: #C7D2BC; --rule-soft: #DCE4D4;
  }
  :root[data-theme="dark"] {
    --bg: #11160F; --bg-grid: rgba(231, 238, 223, 0.045);
    --surface: #1A2217; --surface-raised: #202B1C;
    --ink: #E7EEDF; --ink-soft: #9CAC93; --ink-faint: #71806C;
    --accent: #E0B158; --accent-deep: #F3CE86; --accent-wash: rgba(224, 177, 88, 0.14);
    --good: #6FBB92; --warn: #DD8F6E; --warn-wash: rgba(221, 143, 110, 0.12);
    --rule: #2B362A; --rule-soft: #212B1F;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #11160F; --bg-grid: rgba(231, 238, 223, 0.045);
      --surface: #1A2217; --surface-raised: #202B1C;
      --ink: #E7EEDF; --ink-soft: #9CAC93; --ink-faint: #71806C;
      --accent: #E0B158; --accent-deep: #F3CE86; --accent-wash: rgba(224, 177, 88, 0.14);
      --good: #6FBB92; --warn: #DD8F6E; --warn-wash: rgba(221, 143, 110, 0.12);
      --rule: #2B362A; --rule-soft: #212B1F;
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background-color: var(--bg);
    background-image: linear-gradient(var(--bg-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--bg-grid) 1px, transparent 1px);
    background-size: 28px 28px;
    color: var(--ink);
    font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", "Segoe UI", sans-serif;
    line-height: 1.6;
  }
  .page { max-width: 880px; margin: 0 auto; padding: 48px 20px 80px; }
  .masthead { border-top: 3px solid var(--ink); border-bottom: 1px solid var(--rule); padding: 22px 0 20px; margin-bottom: 28px; }
  .masthead-row { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; flex-wrap: wrap; }
  .masthead-eyebrow { font-size: .74rem; letter-spacing: .12em; color: var(--ink-faint); font-weight: 600; }
  h1 { font-family: "Noto Serif TC", serif; font-weight: 700; font-size: clamp(1.7rem, 4vw, 2.3rem); margin: 6px 0 4px; text-wrap: balance; }
  .masthead-sub { color: var(--ink-soft); font-size: .95rem; max-width: 62ch; }
  .masthead-date { font-variant-numeric: tabular-nums; font-size: .85rem; color: var(--ink-faint); white-space: nowrap; }
  .disclaimer { background: var(--warn-wash); border: 1px solid color-mix(in srgb, var(--warn) 35%, transparent); border-radius: 3px; padding: 14px 16px; font-size: .86rem; margin-bottom: 36px; display: flex; gap: 10px; }
  .disclaimer strong { color: var(--warn); }
  .disclaimer-mark { flex: none; font-weight: 700; color: var(--warn); }
  .stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--rule); border: 1px solid var(--rule); margin-bottom: 40px; }
  .stat { background: var(--surface); padding: 16px 18px; text-align: center; }
  .stat-num { font-family: "Noto Serif TC", serif; font-variant-numeric: tabular-nums; font-size: 1.9rem; color: var(--accent-deep); font-weight: 700; line-height: 1; }
  .stat-label { font-size: .78rem; color: var(--ink-soft); margin-top: 6px; }
  .stat-sub { font-size: .72rem; color: var(--ink-faint); margin-top: 2px; }
  section.report { margin-bottom: 52px; }
  .section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; border-bottom: 2px solid var(--ink); padding-bottom: 8px; margin-bottom: 6px; flex-wrap: wrap; }
  .section-head h2 { font-family: "Noto Serif TC", serif; font-size: 1.3rem; margin: 0; }
  .section-head .count { font-size: .82rem; color: var(--ink-faint); font-variant-numeric: tabular-nums; }
  .criteria { list-style: none; margin: 14px 0 26px; padding: 0; display: grid; gap: 6px; }
  .criteria li { display: flex; gap: 10px; font-size: .86rem; color: var(--ink-soft); padding: 7px 0; border-bottom: 1px dashed var(--rule-soft); }
  .criteria li:last-child { border-bottom: none; }
  .criteria .tag { flex: none; font-size: .72rem; font-weight: 700; color: var(--accent-deep); background: var(--accent-wash); border-radius: 2px; padding: 2px 7px; white-space: nowrap; }
  .intro-note { font-size: .86rem; color: var(--ink-soft); margin: 10px 0 20px; max-width: 72ch; }
  .table-wrap { overflow-x: auto; border: 1px solid var(--rule); background: var(--surface); }
  table { width: 100%; border-collapse: collapse; min-width: 640px; }
  thead th { text-align: left; font-size: .72rem; letter-spacing: .06em; color: var(--ink-faint); font-weight: 600; padding: 10px 14px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
  tbody td { padding: 12px 14px; border-bottom: 1px solid var(--rule-soft); font-size: .9rem; vertical-align: middle; }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: var(--accent-wash); }
  .code { font-family: ui-monospace, Consolas, monospace; font-variant-numeric: tabular-nums; color: var(--ink-faint); font-size: .82rem; }
  .name { font-weight: 600; }
  a.stock-link { color: inherit; text-decoration: none; border-bottom: 1px dashed transparent; }
  a.stock-link:hover { color: var(--accent-deep); border-bottom-color: var(--accent-deep); }
  .num { font-variant-numeric: tabular-nums; text-align: right; }
  td.num, th.num { text-align: right; }
  .yield-pill { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--accent-deep); }
  .div-cell { min-width: 150px; }
  .div-amt { font-variant-numeric: tabular-nums; font-weight: 700; white-space: nowrap; }
  .div-amt .unit { font-weight: 400; color: var(--ink-faint); font-size: .78rem; }
  .div-meta { font-size: .74rem; color: var(--ink-faint); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .div-countdown { font-size: .74rem; font-weight: 600; white-space: nowrap; margin-top: 2px; }
  .div-countdown.soon { color: var(--accent-deep); }
  .div-countdown.est { color: var(--ink-faint); font-weight: 400; font-style: italic; }
  .risk-cell { display: flex; align-items: center; gap: 8px; min-width: 120px; }
  .risk-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--rule-soft); position: relative; overflow: hidden; }
  .risk-bar > span { position: absolute; inset: 0 auto 0 0; border-radius: 3px; background: var(--good); }
  .risk-bar.mid > span { background: color-mix(in srgb, var(--good) 50%, var(--warn) 50%); }
  .risk-bar.high > span { background: var(--warn); }
  .risk-num { font-variant-numeric: tabular-nums; font-size: .78rem; color: var(--ink-soft); width: 3.4em; text-align: right; }
  .gain-pill { display: inline-flex; align-items: center; gap: 3px; font-variant-numeric: tabular-nums; font-weight: 700; color: var(--good); }
  .loss-pill { display: inline-flex; align-items: center; gap: 3px; font-variant-numeric: tabular-nums; font-weight: 700; color: var(--warn); }
  .taiex-banner { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; border: 1px solid var(--rule); background: var(--surface); padding: 14px 18px; margin-bottom: 20px; }
  .taiex-banner .label { font-size: .82rem; color: var(--ink-faint); }
  .taiex-banner .value { font-family: "Noto Serif TC", serif; font-variant-numeric: tabular-nums; font-size: 1.5rem; font-weight: 700; }
  .flow-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 640px) { .flow-grid { grid-template-columns: 1fr; } }
  .flow-col h3 { font-size: .9rem; margin: 0 0 8px; color: var(--ink-soft); font-weight: 600; }
  .foot-note { font-size: .78rem; color: var(--ink-faint); margin-top: 10px; }
  .chart-wrap { border: 1px solid var(--rule); background: var(--surface); padding: 12px 16px 6px; overflow-x: auto; }
  .chart-wrap svg { display: block; min-width: 560px; width: 100%; height: auto; }
  .chart-grid { stroke: var(--rule-soft); stroke-width: 1; }
  .chart-axis { stroke: var(--ink-faint); stroke-width: 1; }
  .chart-tick { font-size: 11px; fill: var(--ink-faint); font-variant-numeric: tabular-nums; }
  .chart-axis-label { font-size: 11.5px; fill: var(--ink-soft); }
  .chart-point { fill: var(--accent-deep); stroke: var(--surface); stroke-width: 1.5; }
  .chart-label { font-size: 11px; font-weight: 600; fill: var(--ink); }
  footer { border-top: 1px solid var(--rule); padding-top: 22px; font-size: .8rem; color: var(--ink-faint); display: grid; gap: 6px; }
  footer a { color: var(--accent-deep); }
  @media (max-width: 560px) { .stat-row { grid-template-columns: 1fr; } .masthead-row { flex-direction: column; align-items: flex-start; } }
"""


def esc(s):
    return html.escape(str(s), quote=True)


def stock_url(code):
    return f"https://tw.stock.yahoo.com/quote/{code}.TW"


def stock_link_cell(code, text, cls):
    return f'<a class="{cls} stock-link" href="{esc(stock_url(code))}" target="_blank" rel="noopener">{esc(text)}</a>'


def risk_class(vol, warn_at=25, high_at=30):
    if vol >= high_at:
        return "high"
    if vol >= warn_at:
        return "mid"
    return ""


def countdown_html(nxt):
    if nxt is None:
        return ""
    if nxt["confirmed"]:
        d = nxt["days"]
        label = "下次除息:今天" if d == 0 else f"下次除息:{d}天後"
        return f'<div class="div-countdown soon">{esc(label)}</div>'
    return f'<div class="div-countdown est">預估下次約{nxt["days"]}天後</div>'


def etf_row(e):
    vol = e["annualized_volatility_pct"]
    vol_pct_of_bar = min(vol / 35 * 100, 100)
    latest = e.get("latest_distribution")
    div_cell = ""
    if latest:
        unit = "元/單位"
        div_cell = (
            f'<div class="div-amt">{latest["amount"]:.2f} <span class="unit">{unit}</span></div>'
            f'<div class="div-meta">已配息(除息日 {esc(latest["date"])})</div>'
            f'{countdown_html(e.get("next_distribution"))}'
        )
    return f"""
          <tr>
            <td class="code">{stock_link_cell(e['code'], e['code'], 'code')}</td><td class="name">{stock_link_cell(e['code'], e['name'], 'name')}</td>
            <td class="num">{e['price']:.2f}</td>
            <td class="num"><span class="yield-pill">{e['dividend_yield_pct_est']:.2f}%</span></td>
            <td class="div-cell">{div_cell}</td>
            <td class="num">{e['event_count_this_year']}</td>
            <td><div class="risk-cell"><div class="risk-bar {risk_class(vol)}"><span style="width:{vol_pct_of_bar:.0f}%"></span></div><span class="risk-num">{vol:.1f}%</span></div></td>
          </tr>"""


def green_row(r):
    sign = "▲" if r["pct"] >= 0 else "▼"
    return f"""
          <tr><td class="code">{stock_link_cell(r['code'], r['code'], 'code')}</td><td class="name">{stock_link_cell(r['code'], r['name'], 'name')}</td>
          <td class="num">{r['close']:.2f}</td><td class="num">{r['change']:+.2f}</td>
          <td class="num"><span class="gain-pill">{sign} {r['pct']:.2f}%</span></td></tr>"""


def flow_row(r, kind):
    cls = "gain-pill" if kind == "buy" else "loss-pill"
    return f"""
          <tr><td class="code">{stock_link_cell(r['code'], r['code'], 'code')}</td><td class="name">{stock_link_cell(r['code'], r['name'], 'name')}</td>
          <td class="num"><span class="{cls}">{r['net_lots']:+,}</span></td></tr>"""


def scatter_chart(etfs):
    left, right, top, bottom = 46, 620, 16, 340
    xmax, ymax = 35, max(18, (max((e["dividend_yield_pct_est"] for e in etfs), default=18) + 2))

    def X(v):
        return left + min(v, xmax) / xmax * (right - left)

    def Y(v):
        return bottom - min(v, ymax) / ymax * (bottom - top)

    gridlines = "".join(
        f'<line class="chart-grid" x1="{X(gx):.1f}" y1="{top}" x2="{X(gx):.1f}" y2="{bottom}"></line>'
        for gx in (10, 20, 30)
    ) + "".join(
        f'<line class="chart-grid" x1="{left}" y1="{Y(gy):.1f}" x2="{right}" y2="{Y(gy):.1f}"></line>'
        for gy in range(5, int(ymax), 5)
    )
    points = ""
    for e in etfs:
        vol = e["annualized_volatility_pct"]
        px, py = X(vol), Y(e["dividend_yield_pct_est"])
        anchor = "end" if px > right - 60 else "start"
        dx = -8 if anchor == "end" else 8
        points += (
            f'<circle class="chart-point" cx="{px:.1f}" cy="{py:.1f}" r="5"></circle>'
            f'<text class="chart-label" x="{px + dx:.1f}" y="{py - 8:.1f}" text-anchor="{anchor}">{esc(e["code"])}</text>'
        )
    return f"""
    <div class="chart-wrap">
      <svg viewBox="0 0 640 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ETF殖利率與波動率散佈圖">
        {gridlines}
        <line class="chart-axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"></line>
        <line class="chart-axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"></line>
        <text class="chart-tick" x="{left}" y="{bottom+16}" text-anchor="middle">0</text>
        <text class="chart-tick" x="{X(10):.1f}" y="{bottom+16}" text-anchor="middle">10</text>
        <text class="chart-tick" x="{X(20):.1f}" y="{bottom+16}" text-anchor="middle">20</text>
        <text class="chart-tick" x="{X(30):.1f}" y="{bottom+16}" text-anchor="middle">30%</text>
        <text class="chart-axis-label" x="{right}" y="{bottom}" dy="-6" text-anchor="end">波動率(風險) →</text>
        <text class="chart-axis-label" x="{left}" y="{top}" dy="-4">↑ 殖利率</text>
        {points}
      </svg>
    </div>"""


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    etfs = data["etfs"]
    green = data["green_energy"]
    cfg = data["config"]
    taiex = data.get("taiex")
    flow = data.get("institutional_flow") or {"top_buy": [], "top_sell": [], "as_of": None}
    flow_buy = flow.get("top_buy") or []
    flow_sell = flow.get("top_sell") or []
    flow_as_of = flow.get("as_of") or "-"

    etfs_with_change = [e for e in etfs if e.get("change_pct") is not None]
    up_count = sum(1 for e in etfs_with_change if e["change_pct"] > 0)
    down_count = sum(1 for e in etfs_with_change if e["change_pct"] < 0)
    flat_count = len(etfs_with_change) - up_count - down_count
    top_up_etf = max(etfs_with_change, key=lambda e: e["change_pct"], default=None)
    top_down_etf = min(etfs_with_change, key=lambda e: e["change_pct"], default=None)

    stat_cards = f"""
    <div class="stat-row">
      <div class="stat"><div class="stat-num">{up_count}漲 {down_count}跌 {flat_count}平</div><div class="stat-label">今日 ETF 漲跌家數</div></div>
      <div class="stat"><div class="stat-num gain-pill">▲ {top_up_etf['change_pct']:.2f}%</div><div class="stat-label">今日領漲 ETF</div><div class="stat-sub">{esc(top_up_etf['name'])}({esc(top_up_etf['code'])})</div></div>
      <div class="stat"><div class="stat-num loss-pill">▼ {top_down_etf['change_pct']:.2f}%</div><div class="stat-label">今日領跌 ETF</div><div class="stat-sub">{esc(top_down_etf['name'])}({esc(top_down_etf['code'])})</div></div>
    </div>""" if top_up_etf and top_down_etf else ""

    taiex_banner = ""
    if taiex:
        sign = "▲" if taiex["change"] >= 0 else "▼"
        cls = "gain-pill" if taiex["change"] >= 0 else "loss-pill"
        pct_txt = f"{taiex['pct']:+.2f}%" if taiex.get("pct") is not None else ""
        taiex_banner = f"""
  <div class="taiex-banner">
    <span class="label">加權指數({esc(taiex['date'])})</span>
    <span class="value">{taiex['value']:,.2f}</span>
    <span class="{cls}">{sign} {taiex['change']:+,.2f} ({pct_txt})</span>
  </div>"""

    etf_rows = "".join(etf_row(e) for e in etfs)
    green_rows = "".join(green_row(r) for r in green["top"])
    flow_buy_rows = "".join(flow_row(r, "buy") for r in flow_buy) or '<tr><td colspan="3" class="foot-note">今日無資料</td></tr>'
    flow_sell_rows = "".join(flow_row(r, "sell") for r in flow_sell) or '<tr><td colspan="3" class="foot-note">今日無資料</td></tr>'

    html_out = f"""<meta charset="utf-8">
<title>季配息股票 / ETF 篩選報告</title>
<style>{CSS}</style>
<div class="page">
  <header class="masthead">
    <div class="masthead-row">
      <div>
        <div class="masthead-eyebrow">台股公開數據 · 客觀篩選快報</div>
        <h1>季配息股票 / ETF 篩選報告</h1>
        <div class="masthead-sub">殖利率偏高、近期有季度配息紀錄、波動率相對較低的台股上市 ETF。</div>
      </div>
      <div class="masthead-date">資料基準日 {esc(data.get('price_as_of') or '-')}</div>
    </div>
  </header>

  <div class="disclaimer">
    <span class="disclaimer-mark">!</span>
    <div>
      <strong>本報告不構成投資建議或推薦。</strong>
      內容為依固定規則對台灣證交所公開數據做的機械式篩選,製作者不是持證財務顧問。
      務必自行核實並評估風險,必要時諮詢持證顧問。
    </div>
  </div>

  {taiex_banner}

  {stat_cards}

  <section class="report">
    <div class="section-head">
      <h2>ETF</h2>
      <span class="count">{len(etfs)} 檔 · 台灣證交所上市 ETF(不含債券型)</span>
    </div>
    <ul class="criteria">
      <li><span class="tag">季配息</span>今年以來 TWSE 公告的收益分配次數落在 {cfg['min_events_for_quarterly']}~{cfg['max_events_for_quarterly']} 次之間</li>
      <li><span class="tag">價格</span>每張(1000受益單位) ≤ {cfg['max_lot_price']:,} 元</li>
      <li><span class="tag">殖利率</span>推估年化殖利率 ≥ {cfg['min_dividend_yield_pct']}%,<em>為粗略推估,非保證配息</em></li>
      <li><span class="tag">風險</span>近{cfg['volatility_lookback_months']}個月年化波動率 ≤ {cfg['max_annualized_volatility_pct']}%,並排除代號以 B 結尾的債券型 ETF</li>
    </ul>
    <div class="table-wrap">
      <table>
        <thead><tr><th>代號</th><th>名稱</th><th class="num">現價</th><th class="num">推估殖利率</th><th>最新配息</th><th class="num">今年配息次數</th><th>近期波動率(風險代理)</th></tr></thead>
        <tbody>{etf_rows}</tbody>
      </table>
    </div>
    <div class="foot-note">殖利率為今年至今配息的粗略年化推估,會隨每次實際配息金額變動,也可能含本金退還,不代表總報酬率。「預估下次」是用約3個月週期往後推算,尚未經基金公司公告確認。</div>
  </section>

  <section class="report">
    <div class="section-head">
      <h2>殖利率 vs 波動率</h2>
      <span class="count">{len(etfs)} 檔 ETF 風險/報酬總覽</span>
    </div>
    <p class="intro-note">橫軸是近{cfg['volatility_lookback_months']}個月年化波動率(風險代理指標,越右邊波動越大),縱軸是推估年化殖利率(越上面殖利率越高)。左上角代表「殖利率較高、波動較低」,右下角相反。</p>
    {scatter_chart(etfs)}
    <div class="foot-note">座標依本頁上方 ETF 表格的「推估殖利率」與「近期波動率」繪製。</div>
  </section>

  <section class="report">
    <div class="section-head">
      <h2>三大法人買賣超排行</h2>
      <span class="count">前{len(flow_buy)}/{len(flow_sell)}檔 · {esc(flow_as_of)} 收盤後公告</span>
    </div>
    <p class="intro-note">外資、投信、自營商三大法人當日買賣超合計排行(單位:張,1張=1000股),含個股與ETF。<strong>與上方「季配息」篩選條件無關</strong>,純粹是資金流向,不代表後市表現或公司基本面;ETF 常因造市/避險機制出現巨量買賣超,不一定代表法人對該標的看法。</p>
    <div class="flow-grid">
      <div class="flow-col">
        <h3>買超最多</h3>
        <div class="table-wrap">
          <table><thead><tr><th>代號</th><th>名稱</th><th class="num">買超(張)</th></tr></thead><tbody>{flow_buy_rows}</tbody></table>
        </div>
      </div>
      <div class="flow-col">
        <h3>賣超最多</h3>
        <div class="table-wrap">
          <table><thead><tr><th>代號</th><th>名稱</th><th class="num">賣超(張)</th></tr></thead><tbody>{flow_sell_rows}</tbody></table>
        </div>
      </div>
    </div>
    <div class="foot-note">資料來源:TWSE 三大法人買賣超日報。買超/賣超張數為外資(不含自營商)、投信、自營商(含避險)三者合計後的淨額。</div>
  </section>

  <section class="report">
    <div class="section-head">
      <h2>綠能個股漲幅排行</h2>
      <span class="count">前{len(green['top'])}檔 · 綠能環保類股共{green['universe_count']}檔 · {esc(green.get('as_of') or '-')} 收盤</span>
    </div>
    <p class="intro-note">範圍限定在 TWSE 公司基本資料「產業別」標註為「綠能環保業」的 {green['universe_count']} 檔上市公司,依漲跌幅由高到低取前{len(green['top'])}檔。<strong>與上方「季配息」篩選條件無關</strong>,純粹是當日股價表現,不代表公司基本面或後市表現。</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>代號</th><th>名稱</th><th class="num">收盤價</th><th class="num">漲跌</th><th class="num">漲跌幅</th></tr></thead>
        <tbody>{green_rows}</tbody>
      </table>
    </div>
    <div class="foot-note">「綠能環保業」依 TWSE 公開資料的產業別分類認定,僅含證交所上市公司,不含上櫃綠能股。</div>
  </section>

  <footer>
    <div>資料來源:台灣證券交易所(TWSE)公開 OpenAPI。本頁由 GitHub Actions 於每個交易日 14:30(台北時間)自動重新抓取並發布。</div>
    <div>產生時間(UTC): {esc(data.get('generated_at_utc') or '-')}</div>
    <div>本頁僅供參考,不構成要約、勸誘或投資建議;過去的配息與波動率不代表未來表現。</div>
  </footer>
</div>
"""
    OUTPUT_PATH.write_text(html_out, encoding="utf-8")
    print(f"寫入 {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
