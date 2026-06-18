# Stocknity — Backend

Flask API backend for a stock portfolio management app. Port 8080.

## Services

- `python main.py` — starts Flask on port 8080
- Redis (Docker) — `docker run -d --name stocknity-redis -p 6379:6379 redis:7-alpine`
- Java market data service — `/Users/tenzinkalden/projects/stocknity-market-data` (port 8090, Chronicle Queue + Alpaca WebSocket)
- Frontend (React) — `/Users/tenzinkalden/projects/stocknity-ui` (port 3000)

## Starting locally

```bash
# Redis
docker start stocknity-redis

# Spring Boot API (from stocknity-api directory)
PORT=8080 java -XX:TieredStopAtLevel=1 -Xss512k -jar target/*.jar

# Flask analytics (from this directory)
source venv/bin/activate
python main.py

# Frontend
cd /Users/tenzinkalden/projects/stocknity-ui
npm start
```

If port 8080 is stuck: `lsof -ti:8080 | xargs kill -9`

If Redis cache is stale: `docker exec stocknity-redis redis-cli FLUSHALL`

## Data source architecture

Swappable via `STOCK_DATA_SOURCE` env var (set in `.env`).

| Value | Source | Notes |
|-------|--------|-------|
| `yfinance` | yfinance batch download | **Default. Free, reliable. annual_return + dividend + price.** |
| `massive` | Polygon.io + yfinance | Polygon for real-time price/change, yfinance for return/dividend. Requires `POLYGON_API_KEY`. |
| `fmp` | Financial Modeling Prep | Real P/E, P/B, PEG. Free tier too restricted (per-symbol, 250 req/day). Pay $14/mo for Starter to use at scale. |

Key files:
- `services/sources/base.py` — `StockDataSource` ABC + `FetchResult` dataclass
- `services/sources/yfinance_source.py` — single `yf.download(actions=True)` call covers return + dividend + price
- `services/sources/massive.py` — Polygon snapshot + yfinance batch
- `services/sources/fmp.py` — FMP stable API (profile + ratios-ttm per ticker)
- `services/sources/__init__.py` — factory (`get_data_source()`)
- `services/massive_fetcher.py` — thin wrapper; also owns `SECTOR_TICKERS` dict (shared by all sources)

## DataFrame schema (all sources must return these columns)

```
Ticker, pe, pb, fpe, peg, dividend, annual_return, today_change, price
```

Columns a source can't provide should be `None`, not 0. Chart scoring uses `fillna(0)`.

## Chart scoring (`services/chart.py`)

Scoring is **source-agnostic** — uses `fillna(0)`, weights apply to whatever is present:

- **Value**: `(1/pe)*40 + (dividend*100).clip(40) + stability_from_return*0.4`
- **Growth**: `annual_return*0.9 + today_change*0.1`
- **Dividend**: top 5 by `dividend * 100` (as %)

24h Redis cache per chart type. Flush cache after changing data source or fixing bugs.

## Real-time prices (Java service)

`/Users/tenzinkalden/projects/stocknity-market-data`

- Alpaca IEX WebSocket → Chronicle Queue (off-heap ring buffer) → Redis pub/sub → browser WebSocket
- Run: `java --add-opens java.base/java.lang.reflect=ALL-UNNAMED --add-opens java.base/java.nio=ALL-UNNAMED --add-exports java.base/sun.nio.ch=ALL-UNNAMED -jar target/stocknity-market-data-1.0.0.jar`
- Frontend mock mode (for off-hours): `REACT_APP_MOCK_PRICES=true` in `stocknity-ui/.env.local`

## Frontend env (`/Users/tenzinkalden/projects/stocknity-ui/.env.local`)

```
REACT_APP_API_BASE_URL=http://localhost:8080/api
REACT_APP_PRICE_WS_URL=ws://localhost:8090/ws/prices
REACT_APP_MOCK_PRICES=true
```

## Product roadmap

### Tier 1 — Ship now (weeks)
- [ ] Alpaca paper trading — place orders from UI, track P&L, positions
- [ ] AI trade assistant — Claude API reads portfolio + sector data, gives buy/sell reasoning
- [ ] Portfolio analytics — Sharpe ratio, drawdown, sector exposure, correlation matrix
- [ ] Price alerts — WebSocket already running, add alert rules persisted in Redis

### Tier 2 — Growth (months)
- [ ] Live trading via Alpaca — real money, flip env var from paper to live
- [ ] Level 2 order book — Alpaca paid tier ($9/mo)
- [ ] AI agent loop — monitors positions, suggests rebalances, executes with one-click approval
- [ ] News sentiment signals — MT Newswires already available, wire into trade ideas
- [ ] Backtesting UI — `services/backtesting.py` exists, needs frontend wiring

### Tier 3 — Monetize (6-12 months)
- [ ] Freemium — free screener/charts, paywall AI + trading ($20-50/mo)
- [ ] Strategy portfolios — user picks a strategy, AI auto-rebalances
- [ ] API access — sell signal data to developers

### Architecture decisions for trading path
- Order execution: route through Java service (not Flask) — Chronicle Queue already there
- Flask stays for analytics, auth, portfolio reads only
- Alpaca handles broker-dealer compliance — no license needed on our side
- Paper trading → live trading is one env var: `ALPACA_BASE_URL`

### What will actually kill this project
1. **Data costs at scale** — yfinance gets blocked at ~1000 concurrent users; budget $200-2000/mo for real-time fundamentals
2. **Regulatory gray zone** — AI giving specific trade advice = potential RIA requirement; frame as "educational" until legal review
3. **Trust** — users won't put real money in a new app; paper trading + track record first
4. **Python Flask under trading load** — fine for analytics, not for order routing; Java service is the right path for execution

### Moat
Not latency — retail orders settle in ms at Alpaca regardless. The moat is **AI that understands your specific portfolio** and acts on it. No existing retail app does this well.

## Known issues / gotchas

- `yfinance fast_info.last_dividend_value` is broken in v1.4.1 — use `yf.download(actions=True)` instead
- macOS Gatekeeper can quarantine venv `.so` files after reinstall: `xattr -r -d com.apple.quarantine venv/`
- numpy 2.x breaks pyarrow: keep `numpy<2`
- FMP V3 (`/api/v3/`) is legacy-only after Aug 2025 — use `/stable/` endpoints
- FMP free tier: ratios-ttm only works for ~5 major tickers (AAPL, MSFT, NVDA, META, AMD)
