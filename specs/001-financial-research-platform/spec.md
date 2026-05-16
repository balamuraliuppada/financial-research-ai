# Feature Specification: Financial Research AI Platform (Track B)

**Feature Branch**: `001-financial-research-platform`

**Created**: 2026-05-16

**Status**: Draft

**Input**: Track B — Advanced Financial Research Platform per the 2-Month development curriculum PDF.

---

## User Scenarios & Testing _(mandatory)_

### User Story 1 — Live Indian Stock Analysis (Priority: P1)

An investor wants to research an Indian stock (e.g. TCS, Reliance, HDFC Bank) by entering the company name or NSE ticker and immediately seeing the current price, intraday chart, RSI, moving averages, Bollinger Bands, and recent news with sentiment score — all on one screen.

**Why this priority**: This is the core value of the platform. Without live stock data and charting, nothing else matters.

**Independent Test**: Open the Dashboard, search "TCS", view the price card, click on the chart, switch periods (1D / 1W / 1M / 1Y), and verify the technical indicator overlays render with correct values.

**Acceptance Scenarios**:

1. **Given** the user types "RELIANCE" in the search box, **When** they confirm the symbol, **Then** the current price in INR, % change, RSI, MA20, and MA50 are displayed within 5 seconds.
2. **Given** the user selects the "1D" period, **When** the chart loads, **Then** data uses 5-minute intervals and overlays display correctly.
3. **Given** the market is closed (weekend/holiday), **When** the user loads a stock, **Then** a clear "Market Closed" badge is shown with the next open time in IST.
4. **Given** a network/API failure, **When** the primary data source is unavailable, **Then** the platform falls back to the secondary data source without showing a raw error to the user.

---

### User Story 2 — AI-Powered Research Assistant (Priority: P1)

A user wants to ask natural-language questions such as "Compare TCS and Infosys fundamentals" or "Should I buy HDFCBANK right now?" and receive a structured, data-backed answer drawn from live market data, technical signals, and fundamental metrics.

**Why this priority**: This is the differentiating Track B feature — LangGraph multi-step agent with 10+ financial tools.

**Independent Test**: Open the Assistant page, type "What is the RSI for INFY.NS and is it overbought?", verify the agent fetches live data and returns a specific numerical answer with a buy/hold/sell reasoning.

**Acceptance Scenarios**:

1. **Given** the user asks about a stock by company name (not ticker), **When** the agent responds, **Then** it correctly maps the company name to the NSE ticker (.NS suffix) without asking for clarification.
2. **Given** the user asks for portfolio optimization with 3 symbols, **When** the agent responds, **Then** it invokes the portfolio optimization tool and returns specific percentage allocations.
3. **Given** the user asks about gold or crude oil prices, **When** the agent responds, **Then** it uses the commodity tool to return current prices in USD with context.
4. **Given** the GOOGLE_API_KEY is missing, **When** the assistant is opened, **Then** a clear configuration error message is shown — no silent crash.

---

### User Story 3 — Portfolio Optimization (Priority: P2)

A user selects multiple Indian stocks and runs portfolio optimization to receive the Efficient Frontier chart, the optimal Sharpe-ratio allocation, minimum-volatility allocation, and risk metrics (VaR, CVaR, annualized return/volatility).

**Why this priority**: Core Track B advanced feature — Modern Portfolio Theory implementation is explicitly required and graded.

**Independent Test**: On the Optimizer page, select RELIANCE.NS, TCS.NS, INFY.NS, and HDFCBANK.NS, run optimization, and verify the scatter plot (Efficient Frontier) renders with at least 1,000 simulated portfolios and the recommended allocation sums to 100%.

**Acceptance Scenarios**:

1. **Given** 3+ stocks are selected, **When** the user clicks "Optimize", **Then** a Markowitz Efficient Frontier is rendered and the max-Sharpe-ratio portfolio weights are shown in a pie chart.
2. **Given** the optimization runs, **When** results appear, **Then** Risk Parity and Minimum Volatility allocations are also available as selectable views.
3. **Given** a stock with insufficient historical data is included, **When** the user runs optimization, **Then** a clear warning names the problematic symbol and suggests removing it.
4. **Given** the user views results, **When** they hover over a frontier point, **Then** the return, volatility, and Sharpe ratio for that portfolio are displayed.

---

### User Story 4 — Algorithmic Trading Signals (Priority: P2)

A user selects a stock and receives a composite buy/sell/hold signal backed by up to 9 technical indicators (RSI, MACD, Stochastic, EMA crossover, ADX, Supertrend, Bollinger Bands, ATR, OBV/VWAP), each with an individual signal direction and a combined confidence score.

**Why this priority**: Required Track B deliverable — "algorithmic trading signals" is listed as a bonus feature worth up to 20 extra points.

**Independent Test**: On the Signals page, enter "SBIN.NS", click "Generate Signals", and verify at least 6 individual indicator rows appear with their signal direction and that the composite score is displayed with a confidence percentage.

**Acceptance Scenarios**:

1. **Given** a valid NSE symbol, **When** signals are generated, **Then** all available indicators render their individual signal (BUY/SELL/HOLD) and the composite result (BUY/SELL/HOLD) with a confidence % is prominently shown.
2. **Given** insufficient historical data for an indicator, **When** signals are generated, **Then** that indicator row shows "Insufficient data" rather than a numeric error.
3. **Given** the user runs batch signals on multiple symbols, **When** results return, **Then** symbols are sortable by composite signal strength.

---

### User Story 5 — Options Pricing & Strategy Payoff (Priority: P2)

A user inputs an underlying stock price, strike price, expiry, volatility, and risk-free rate to compute Black-Scholes price and all Greeks (Delta, Gamma, Theta, Vega, Rho) for a call or put. They can also model multi-leg strategies (Iron Condor, Straddle, Bull Spread) and view the payoff diagram at expiry.

**Why this priority**: Explicitly required as a Track B advanced feature and listed as a bonus grading item.

**Independent Test**: On the Options page, enter S=1500, K=1500, T=30 days, r=6.5%, σ=25%, type=call — verify the calculated price and all 5 Greeks are shown. Then select "Straddle" strategy and verify the payoff chart renders correctly.

**Acceptance Scenarios**:

1. **Given** valid option inputs, **When** the user calculates, **Then** Black-Scholes price and Delta/Gamma/Theta/Vega/Rho are all displayed rounded to 4 decimal places.
2. **Given** the user selects a named strategy template (e.g. Iron Condor), **When** the strategy loads, **Then** the leg parameters are auto-populated and the P&L payoff chart is rendered.
3. **Given** time to expiry is 0 days, **When** the user calculates, **Then** the intrinsic value is returned correctly without a division-by-zero error.

---

### User Story 6 — Multi-Asset & Macro Dashboard (Priority: P3)

A user can view US Treasury yield curves, commodity prices (Gold, Silver, Crude, Natural Gas), major forex pairs (USD/INR, EUR/USD, etc.), global indices (Nifty50, Sensex, S&P 500, Nasdaq, VIX), and a cross-asset correlation matrix — all on one Multi-Asset page.

**Why this priority**: Required Track B multi-asset class analysis deliverable.

**Independent Test**: On the Multi-Asset page, verify at least 4 commodity rows, 6 forex pairs, the yield curve chart (3M / 5Y / 10Y / 30Y), and a global indices table all load without errors.

**Acceptance Scenarios**:

1. **Given** the user opens the Multi-Asset page, **When** data loads, **Then** the yield curve, commodity, forex, and indices sections all render within 8 seconds.
2. **Given** the user selects 3 assets for correlation, **When** correlation is computed, **Then** a colour-coded matrix is displayed with values between -1 and 1.
3. **Given** a commodity API fails, **When** the page loads, **Then** the failed row shows "Data unavailable" and other sections continue to work.

---

### User Story 7 — Real-Time Price & Technical Alerts (Priority: P3)

A user creates an alert (e.g. "notify me when TCS price crosses ₹4,000" or "RSI overbought above 70") and receives a real-time browser notification and an in-app notification badge when the condition triggers, without needing to manually refresh.

**Why this priority**: Required Track B deliverable — "real-time market alerts and notification system."

**Independent Test**: Create a price-above alert for a stock with a threshold already exceeded, wait up to 60 seconds, and verify a notification appears in the notification panel and the alert status changes to "Triggered."

**Acceptance Scenarios**:

1. **Given** a price-above alert is created, **When** the stock price exceeds the threshold, **Then** a WebSocket notification is pushed to the browser within the alert check interval.
2. **Given** the user has unread notifications, **When** they open the Notifications panel, **Then** each notification shows the stock symbol, trigger condition, and timestamp.
3. **Given** an alert is triggered, **When** the user views Alerts page, **Then** the alert status shows "Triggered" and can be reset or deleted.

---

### User Story 8 — Portfolio & Watchlist Management (Priority: P3)

A user can add stocks to a personal portfolio (with buy price and quantity), track current P&L per holding, add/remove stocks to a watchlist with personal notes, and view a persistent profile with risk tolerance and investment goal settings.

**Why this priority**: Required for database persistence — SQLAlchemy-backed portfolio, watchlist, and profile storage.

**Independent Test**: Add INFY.NS to the portfolio with 10 shares at ₹1,800, reload the page, and verify the holding persists with current P&L calculated against the live price.

**Acceptance Scenarios**:

1. **Given** the user adds a stock to the portfolio, **When** they reload the page, **Then** the holding is still present and P&L reflects the current live price.
2. **Given** the user adds a note to a watchlist item, **When** they reload, **Then** the note persists.
3. **Given** the user updates their risk profile to "Aggressive", **When** they revisit the Profile page, **Then** the selection is saved.

---

### Edge Cases

- What happens when an NSE stock symbol has no historical data for the requested period?
- How does the platform behave when all financial APIs are rate-limited simultaneously?
- What happens when a portfolio optimization is run with only 1 stock (underdetermined)?
- How does the options calculator handle negative implied volatility input?
- What happens when a WebSocket connection drops mid-session (alert pushes)?
- How are NaN and Infinity values from financial calculations handled before they reach the frontend?
- What happens if the database file is read-only or locked?
- How does the system behave during Indian market holidays?

---

## Requirements _(mandatory)_

### Functional Requirements

**Market Data & Stock Analysis**

- **FR-001**: System MUST fetch real-time price data for NSE-listed stocks using the `.NS` Yahoo Finance suffix.
- **FR-002**: System MUST fall back to a secondary data source when the primary source fails or is rate-limited.
- **FR-003**: System MUST compute and overlay RSI (14-period), MA20, MA50, and Bollinger Bands on price charts.
- **FR-004**: System MUST display Indian market status (open/closed) with IST timestamps and next open time.
- **FR-005**: System MUST format all monetary values in INR using Indian numbering (lakhs/crores).

**AI Agent**

- **FR-006**: System MUST route natural-language financial queries through a multi-step agentic AI workflow with at least 10 callable financial tools.
- **FR-007**: Agent MUST auto-resolve company names to NSE tickers without prompting the user for clarification.
- **FR-008**: Agent MUST return structured, source-cited answers including numerical data from tools.

**Portfolio Optimization**

- **FR-009**: System MUST compute the Efficient Frontier using Monte Carlo simulation with at least 1,000 random portfolios.
- **FR-010**: System MUST expose Maximum Sharpe Ratio, Minimum Volatility, and Risk Parity allocation models.
- **FR-011**: System MUST compute annualized return, annualized volatility, Sharpe ratio, VaR (95%), and CVaR for any portfolio.

**Trading Signals**

- **FR-012**: System MUST evaluate at least 6 technical indicators per stock and produce a composite BUY/SELL/HOLD signal with a percentage confidence score.
- **FR-013**: System MUST support batch signal generation for multiple symbols in a single request.

**Options Pricing**

- **FR-014**: System MUST compute Black-Scholes price and all 5 Greeks (Delta, Gamma, Theta, Vega, Rho) for European calls and puts.
- **FR-015**: System MUST compute Binomial Tree price for American options with early-exercise support.
- **FR-016**: System MUST render payoff-at-expiry diagrams for at least 5 named multi-leg strategies (Straddle, Iron Condor, Bull Spread, Bear Spread, Butterfly).

**Multi-Asset & Macro**

- **FR-017**: System MUST display live US Treasury yields (3M, 5Y, 10Y, 30Y) and render a yield curve chart.
- **FR-018**: System MUST display live prices for at least 5 commodities and 6 forex pairs.
- **FR-019**: System MUST compute and display a cross-asset correlation matrix for user-selected assets.

**Alerts**

- **FR-020**: System MUST support at least 5 alert types: price above, price below, RSI overbought, RSI oversold, volume spike.
- **FR-021**: System MUST push alert notifications to the browser in real time via a persistent connection without requiring a page refresh.

**Persistence**

- **FR-022**: System MUST persist portfolio holdings, watchlist items, alerts, notifications, and user profile across sessions using a relational database.
- **FR-023**: System MUST be deployable against a production-grade relational database via a `DATABASE_URL` environment variable without code changes.

**Caching & Rate Limiting**

- **FR-024**: System MUST cache frequently-requested market data responses to reduce external API calls and stay within free-tier rate limits.
- **FR-025**: System MUST enforce per-API rate limits and automatically pause requests to a failing data source after repeated failures to protect downstream availability.

**Security**

- **FR-026**: All backend API endpoints MUST require a valid API key passed via request header or environment-configured secret.
- **FR-027**: System MUST NOT expose raw API keys, database connection strings, or credentials in any HTTP response.

**CI/CD & Quality**

- **FR-028**: The repository MUST include an automated quality pipeline that runs on every code push to validate correctness and catch regressions before deployment.
- **FR-029**: System MUST handle NaN and Infinity values in all financial calculations before serializing responses to the frontend.

### Key Entities

- **Stock**: Symbol (NSE/BSE ticker), name, sector, live price, historical OHLCV candles.
- **Portfolio Holding**: User-owned stock with quantity, average buy price, current value, unrealised P&L.
- **Watchlist Item**: Tracked stock with optional personal note.
- **Alert**: Condition type, symbol, threshold value, status (active / triggered / disabled), trigger timestamp.
- **Notification**: Alert trigger event with message, timestamp, read status.
- **User Profile**: Name, email, risk tolerance, investment goal, experience level, preferred sectors.
- **Option Contract**: Underlying price, strike, expiry, type (call/put), computed price, Greeks.
- **Portfolio Optimisation Result**: Input symbols, model used, weights, performance metrics, frontier data.

---

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Users can search and view a complete stock analysis (price, chart, RSI, news) in under 5 seconds on a standard broadband connection.
- **SC-002**: The AI assistant answers financial queries using live data within 30 seconds for queries requiring up to 3 tool calls.
- **SC-003**: Portfolio optimization completes and renders the Efficient Frontier for up to 10 stocks within 15 seconds.
- **SC-004**: Algorithmic signals for a single stock are generated and displayed within 8 seconds.
- **SC-005**: Real-time alerts trigger and push a browser notification within 60 seconds of the condition being met.
- **SC-006**: All portfolio, watchlist, alert, and profile data survives a full application restart (persistence verified).
- **SC-007**: The platform remains functional (degraded gracefully) when any single external API is unavailable.
- **SC-008**: All 11 frontend pages render without console errors on a fresh load.
- **SC-009**: The backend API serves all endpoints correctly in a production deployment (Render / cloud target).
- **SC-010**: The automated pipeline completes without errors on a clean push to the main branch.

---

## Assumptions

- Users are accessing the platform from a desktop browser; mobile responsiveness is secondary.
- Free-tier API keys (Yahoo Finance, Alpha Vantage, NewsAPI) are sufficient for development and demo use; production scale is not required.
- Indian market focus (NSE/BSE) is primary; US market support is secondary and limited to indices/ETFs.
- The Gemini API key (`GOOGLE_API_KEY`) is provided as an environment variable; the platform does not manage LLM billing or usage caps.
- Sentiment analysis using TextBlob (polarity scoring) is the baseline; transformer-based (FinBERT) sentiment is an enhancement, not a launch blocker.
- The platform is a research/analysis tool — it does not execute live trades; all recommendations carry standard financial disclaimers.
- SQLite is used for local development; PostgreSQL is the production target via `DATABASE_URL`.
- A distributed cache is configured via environment variable and is used for response caching on high-frequency endpoints (stock price, signals).
- The automated quality pipeline targets the `main` branch and is hosted on the same platform as the source repository.
- Demo video (8–10 minutes), technical blog post, performance benchmarks, and security assessment document are required submission deliverables alongside the code.
