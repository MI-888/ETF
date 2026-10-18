# ETF 季配息篩選報告

自動抓取台灣證交所(TWSE)公開資料,篩選符合「季配息、價格不高、殖利率偏高、波動率相對較低」的
上市 ETF,並附上綠能環保類股當日漲幅排行。**不構成投資建議或推薦。**

## 自動更新

GitHub Actions 會在每個交易日(週一到週五)**台北時間 14:30** 自動重新抓取資料、
重新產生報告,並發布到 GitHub Pages。也可以在 GitHub 的 Actions 分頁手動點選
「Run workflow」立即重跑一次。

## 本機執行

```bash
pip install -r requirements.txt
python scripts/fetch_data.py    # 抓資料 -> docs/data.json
python scripts/build_report.py  # 產生網頁 -> docs/index.html
```

## 調整篩選條件

編輯 `config.json`(價格上限、殖利率門檻、波動率上限等),重新執行上面兩個腳本即可。

## 限制與免責聲明

- 僅覆蓋證交所**上市** ETF,不含上櫃 ETF、債券型 ETF(代號以 B 結尾者排除)。
- 「季配息」判定依今年以來 TWSE 公告的收益分配次數(3~4 次)推斷,新上市或政策
  剛調整的 ETF 可能被誤判。
- 殖利率為粗略年化推估,不是保證配息,配息也可能含本金退還。
- 波動率僅為風險代理指標,不代表完整風險評估。
- 本報告內容僅供參考,不構成任何投資建議,使用者需自行查證並承擔投資風險。
