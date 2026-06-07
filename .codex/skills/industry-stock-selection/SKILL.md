---
name: industry-stock-selection
description: Project-specific industry stock selection research workflow for this investment sentiment barometer. Use this skill when the user asks for 行业选股, 行业轮动, 板块机会, A股/港股/美股行业研究, prediction-market-driven investing, Polymarket/Kalshi signal interpretation, macro-to-sector mapping, or Serenity-style scarce-layer stock research using this repository. It turns the project's prediction-market dashboard signals into ranked industry research priorities, evidence checks, risks, and next verification steps. Research support only; no trade execution or guaranteed returns.
---

# Industry Stock Selection

## Core Rule

Use this skill to turn this repository's prediction-market signals into an industry stock research workflow:

`prediction-market events -> macro factors -> asset/industry pressure -> industry chain layers -> scarce constraints -> public companies -> evidence -> risks -> next checks`

Start with the judgment on industries and chain layers, then rank companies only as research priorities. Keep the trading decision with the user.

## Default Workflow

1. **Read or refresh local signals**
   - Prefer running `python3 .codex/skills/industry-stock-selection/scripts/summarize_dashboard.py --refresh --limit 160` from the repo root when current market information matters.
   - If network collection fails, use the script without `--refresh` or read `/api/dashboard`; clearly label the result as local/demo/latest cached data.
   - Inspect `factors`, `assetImpacts`, `topEvents`, and `errors`.

2. **Separate signal from stock selection**
   - Prediction markets estimate event probabilities, not equity fair value.
   - Convert only high-confidence, liquid, relevant events into macro/industry pressure.
   - Never jump from one event directly to a ticker.

3. **Rank industry directions first**
   - Use `references/signal-to-industry-map.md` for factor-to-industry mapping.
   - For each industry, explain whether the signal is a tailwind, headwind, volatility source, or only a watch item.
   - Keep obvious crowded areas in the comparison and explain why they rank lower when applicable.

4. **Map the industry chain**
   - Identify downstream demand, system integrators, modules/subsystems, components/devices, equipment, materials/consumables, infrastructure, and services.
   - Rank scarce layers before naming companies.
   - Prefer layers with low supplier count, long certification, limited capacity expansion, specialized process know-how, regulatory approval, or customer switching costs.

5. **Build and filter candidate companies**
   - For broad scans, aim for at least 15-25 candidate public companies across the relevant chain before narrowing to 3-7 priorities.
   - Classify each company as: controls scarce layer, supplies scarce layer, benefits from demand, cyclical beta, policy beta, or mainly story exposure.
   - For A-share/HK/US work, use market-specific evidence paths from `references/evidence-and-sources.md`.

6. **Grade evidence**
   - Use strong sources first: filings, exchange announcements, company IR, earnings calls, regulator/project records, tender data, patents/standards, official order or capacity disclosures.
   - Treat media, brokerage notes, and social posts as supporting evidence or lead generation.
   - For every top candidate, state evidence strength: strong, medium, weak, or unverified lead.

7. **Return a research-priority answer**
   - Lead with the best industry layers to research.
   - Then provide a ranked company table with: `公司 / 产业链位置 / 卡住的环节 / 为什么排这里 / 证据 / 主要风险 / 下一步核验`.
   - Include "什么情况说明这个判断错了".
   - If source coverage is thin, call the answer an initial pass and list exact checks to complete.

## Local Project Anchors

Use these repository modules when you need implementation context:

- `app/collectors.py` collects Polymarket and Kalshi events.
- `app/classification.py` maps events to categories and macro factors.
- `app/scoring.py` computes factor scores, asset impacts, confidence, and top events.
- `app/server.py` exposes `/api/refresh` and `/api/dashboard`.
- `data/sentiment.db` stores local snapshots when live data has been collected.

## Output Shape

For Chinese prompts, answer in Chinese. A typical opening:

`先排产业链层级，再排公司。基于当前预测市场信号，我会优先看：[行业/层级 1]、[行业/层级 2]、[行业/层级 3]。原因是这些地方更接近真实供需约束。`

For "which is worth buying", say:

`我会按研究优先级排序，交易决策仍然由你决定。`

## Boundaries

Do not provide guaranteed returns, direct buy/sell commands, invented prices, invented filings, rumored customer relationships, or material non-public information. If live/current data is needed and cannot be accessed, say exactly which facts need verification.

## References

- `references/signal-to-industry-map.md` - map this project's factors and asset impacts to industries.
- `references/evidence-and-sources.md` - source hierarchy, market-specific checks, and risk boundaries.
- `assets/thesis-template.md` - optional memo template for deeper writeups.
- `scripts/summarize_dashboard.py` - local helper that prints compact dashboard signals.
