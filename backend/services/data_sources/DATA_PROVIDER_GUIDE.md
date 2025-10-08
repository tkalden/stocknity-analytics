# Data Provider Adapter System

## 🎯 Overview

This system uses the **Adapter Pattern** to make swapping data providers as easy as changing one line of config!

### Current Providers

| Provider | Status | Cost | Use Case |
|----------|--------|------|----------|
| **Yahoo Finance** | ✅ Implemented | Free | Development, MVP |
| **Finviz** | ✅ Implemented | Free | Screening, sector search |
| **Financial Modeling Prep** | 📝 Ready to implement | $29/mo | Production |
| **Alpha Vantage** | 📋 Planned | $49/mo | Alternative |

---

## 🚀 Quick Start

### Using the System

```python
from backend.services.data_sources.base_provider import DataProviderFactory, DataProviderType

# Option 1: Auto-select based on config
provider = DataProviderFactory.create(
    DataProviderFactory.get_recommended_provider()
)

# Option 2: Explicit selection
provider = DataProviderFactory.create(DataProviderType.YAHOO)

# Fetch data (same interface for ALL providers!)
data = await provider.fetch_stock('AAPL')
print(f"{data.ticker}: ${data.current_price:.2f}")
print(f"ROE: {data.roe:.2%}")
print(f"Source: {data.source}")
```

---

## 🔧 Configuration

### Method 1: Environment Variable (Recommended)

```bash
# .env file
DATA_PROVIDER=yahoo  # Options: yahoo, finviz, fmp, alpha_vantage
```

### Method 2: Code

```python
# config.py
PRIMARY_PROVIDER = DataProviderType.YAHOO
FALLBACK_PROVIDER = DataProviderType.FINVIZ
```

---

## 📊 Provider Comparison

### Yahoo Finance (Current - Free)

**Pros:**
- ✅ Free
- ✅ Good data coverage
- ✅ Real-time prices
- ✅ No API key needed

**Cons:**
- ❌ Unofficial (web scraping)
- ❌ Rate limited (~2000 calls/day)
- ❌ Can break without notice
- ❌ Not suitable for production at scale

**Use for:** MVP, development, validation

---

### Financial Modeling Prep (Production - $29/mo)

**Pros:**
- ✅ Official API with SLA
- ✅ 5,000 calls/day = 1,250 stocks with full data
- ✅ Reliable
- ✅ Great documentation
- ✅ Batch endpoints (efficient!)
- ✅ Production-ready

**Cons:**
- ⚠️ Costs $29/mo
- ⚠️ Needs implementation (~2 hours)

**Use for:** Production, scale

**Break-even:** 3 premium users ($9.99/mo each) = $29.97 revenue > $29 cost ✅

---

## 🔄 Upgrade Path

### From Free Tier to Production

**Step 1: Validate Product**
```bash
# Use Yahoo (free) during MVP
export DATA_PROVIDER=yahoo
```

**Step 2: Get Revenue**
```bash
# Get 3-5 paying users
# Revenue: 5 users × $9.99 = $49.95/mo
```

**Step 3: Upgrade to FMP**
```bash
# 1. Sign up at https://financialmodelingprep.com/
# 2. Get API key
# 3. Implement FMPProvider (use template in fmp_provider.py)
# 4. Update config:
export DATA_PROVIDER=fmp
export FMP_API_KEY=your_key_here
```

**Step 4: Zero Downtime Migration**
```python
# Your code doesn't change!
# Same interface, better data:
provider = DataProviderFactory.create(
    DataProviderFactory.get_recommended_provider()
)
data = await provider.fetch_stock('AAPL')  # Now using FMP!
```

---

## 🏗️ Architecture Benefits

### 1. **Easy Swapping**
Change provider by changing ONE config value. No code changes!

### 2. **Consistent Interface**
All providers return the same `StockData` format. Your guru strategies don't care about the source.

### 3. **Fallback Strategy**
```python
# Try primary, fallback to secondary
try:
    provider = DataProviderFactory.create(DataProviderType.FMP)
    data = await provider.fetch_stock('AAPL')
except:
    provider = DataProviderFactory.create(DataProviderType.YAHOO)
    data = await provider.fetch_stock('AAPL')
```

### 4. **Cost Estimation**
```python
# Know your costs before running
cost_info = provider.get_cost_estimate({
    'fetch_stock': 500,  # 500 individual fetches
    'fetch_batch': 10    # 10 batch operations
})
print(f"Monthly cost: ${cost_info['cost_usd_monthly']}")
```

---

## 📝 Adding a New Provider

### Example: Adding Polygon.io

**Step 1: Create Provider File**
```python
# providers/polygon_provider.py
from backend.services.data_sources.base_provider import BaseDataProvider

class PolygonProvider(BaseDataProvider):
    # Implement all abstract methods
    async def fetch_stock(self, ticker):
        # Your implementation
        pass
```

**Step 2: Register in Factory**
```python
# base_provider.py > DataProviderFactory.create()
elif provider_type == DataProviderType.POLYGON:
    from backend.services.data_sources.providers.polygon_provider import PolygonProvider
    return PolygonProvider(**kwargs)
```

**Step 3: Use It**
```python
provider = DataProviderFactory.create(DataProviderType.POLYGON)
data = await provider.fetch_stock('AAPL')  # Works!
```

---

## 🎓 Best Practices

### For Development
```python
# Use free tier with aggressive caching
DATA_PROVIDER=yahoo
CACHE_TTL=3600  # 1 hour
```

### For MVP (First Users)
```python
# Yahoo with cache + rate limiting
DATA_PROVIDER=yahoo
CACHE_TTL=1800  # 30 minutes
RATE_LIMIT=10   # 10 calls/minute
```

### For Production (Paying Users)
```python
# Paid API with shorter cache
DATA_PROVIDER=fmp
FMP_API_KEY=your_key
CACHE_TTL=300   # 5 minutes (fresh data)
```

---

## 💰 Cost Planning

### Scenario: 100 Active Users

**Without Caching:**
```
100 users × 10 stock lookups/day = 1,000 lookups
1,000 lookups × 4 API calls = 4,000 API calls/day
Requires: FMP Starter ($29/mo) ✅
```

**With 1-Hour Caching:**
```
100 users × 10 stock lookups/day = 1,000 lookups
80% cache hit rate = 200 actual API calls
200 × 4 = 800 API calls/day
Could use: Free tier! But FMP ($29) recommended for reliability
```

---

## 🚨 Important Notes

1. **Yahoo is NOT production-ready**
   - Use only for MVP/development
   - Upgrade to paid API before launch

2. **Implement FMP when revenue > $30/mo**
   - 3-4 paying users = break-even

3. **Cache aggressively**
   - Fundamentals change slowly (cache 1-6 hours)
   - Saves 80-90% of API costs

4. **Monitor usage**
   - Use `get_cost_estimate()` to predict costs
   - Set up alerts for API limit approaching

---

## 📚 See Also

- `base_provider.py` - Abstract interface
- `providers/yahoo_provider.py` - Free tier implementation
- `providers/fmp_provider.py` - Production template
- `aggregator.py` - Uses providers with caching

---

## 🎯 Summary

**Current State:**
- ✅ Using Yahoo Finance (free)
- ✅ Adapter pattern ready
- ✅ Easy to swap providers

**When to Upgrade:**
- 📈 When you get 3+ paying users
- 🚀 Before public launch
- 💼 When targeting enterprise clients

**How to Upgrade:**
- 🔧 Implement FMPProvider (2 hours)
- ⚙️ Change DATA_PROVIDER=fmp
- ✨ No other code changes needed!

