# Evidence And Sources

## Evidence Ladder

Grade evidence in this order:

1. **Strong**: annual/interim/quarterly filings, exchange announcements, official company IR, earnings calls, regulator/project records, tender wins, patents/standards, official order/capacity/customer disclosures.
2. **Medium**: reputable trade media, verified industry association data, credible supply-chain reporting, brokerage research when it cites primary evidence.
3. **Weak**: unsourced media claims, social posts, KOL threads, channel checks without documents, vague "market rumors".
4. **Unverified lead**: useful for a research queue only; never use as proof.

For current claims, use live sources when available. If not available, state the missing verification path.

## Market-Specific Checks

### A-share

- 年报、半年报、季报、临时公告、交易所问询函。
- 深交所互动易、上证 e 互动，只作为线索，需公告/财报交叉验证。
- 招投标、环评/能评、地方项目备案、专利、客户认证。
- 财务检查：应收账款、存货、合同负债、经营现金流、毛利率、关联交易、商誉、质押。

### Hong Kong

- HKEX filings, annual/interim reports, placings, connected transactions.
- Southbound eligibility, liquidity, mainland policy exposure, dilution risk.
- For China-linked industrial names, cross-check mainland filings and project records.

### US

- SEC filings, 10-K/10-Q/8-K/S-1/S-3, earnings transcripts, investor presentations.
- Customer concentration, backlog/RPO, capex plans, insider transactions, ATM/dilution risk.
- Export controls, sanctions, antitrust, and regulatory proceedings when relevant.

## Prediction-Market Checks

When using this repository's Polymarket/Kalshi signals:

- Prefer events with high volume, open interest, liquidity, and narrow spread.
- Watch `confidence` from `app.scoring.liquidity_confidence`.
- Read `topEvents` to understand which questions drive a factor.
- If `status` is `demo`, do not present the output as current market evidence.
- Compare multiple events before treating a factor as meaningful.

## Risk Boundaries

Avoid:

- Direct buy/sell instructions.
- Guaranteed-return language.
- Hype around illiquid names.
- Rumor-based recommendations.
- Material non-public information.
- Invented prices, market caps, customers, orders, or filings.

Always include a failure condition:

`什么情况说明这个判断错了：...`
