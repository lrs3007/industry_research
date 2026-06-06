# Global Investment Market Sentiment Barometer

一个基于 Polymarket 和 Kalshi 预测市场信息的全球投资市场情绪晴雨表 MVP。

第一版能力：

- 采集 Polymarket / Kalshi 公开市场数据。
- 统一预测市场事件为标准 `MarketSnapshot`。
- 将事件映射到宏观因子：风险偏好、通胀压力、美联储鹰派压力、地缘风险、能源冲击、政策不确定性、科技监管压力和 Crypto 情绪。
- 将宏观因子映射到资产和行业影响。
- 提供本地 dashboard、事件雷达、因子强度、资产热力图。
- API 不可用时自动使用 demo fallback，方便验证产品流程。

## 运行

```bash
./start.sh
```

停止服务：

```bash
./stop.sh
```

也可以手动运行：

```bash
python3 -m app.server --host 127.0.0.1 --port 8787
```

打开：

```text
http://127.0.0.1:8787
```

刷新实时数据：

```text
http://127.0.0.1:8787/api/refresh
```

## 测试

```bash
python3 -m unittest discover -s tests
```

## 数据说明

当前版本使用公开 REST 接口：

- Polymarket Gamma API: `https://gamma-api.polymarket.com`
- Kalshi Trade API: `https://external-api.kalshi.com/trade-api/v2`

预测市场价格不是绝对真实概率。评分会按成交量、未平仓量、流动性和买卖价差进行置信度降权。低流动性、宽价差、临近结算或规则含糊的事件需要人工复核。
