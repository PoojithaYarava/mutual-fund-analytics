-- Basic analytics queries aligned to the capstone brief.

-- 1. Top 5 funds by AUM
SELECT fund_house, aum_crore
FROM fact_aum
ORDER BY aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month
SELECT substr(nav_date, 1, 7) AS year_month, AVG(nav_value) AS avg_nav
FROM fact_nav
GROUP BY substr(nav_date, 1, 7)
ORDER BY year_month;

-- 3. SIP inflow year-over-year growth
SELECT month_period, sip_inflow_crore, yoy_growth_pct
FROM fact_sip
ORDER BY month_period;

-- 4. Transactions by state
SELECT i.state, SUM(t.amount_inr) AS total_amount_inr
FROM fact_transactions t
JOIN dim_investor i ON i.investor_id = t.investor_id
GROUP BY i.state
ORDER BY total_amount_inr DESC;

-- 5. Funds with expense ratio below 1 percent
SELECT amfi_code, scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1
ORDER BY expense_ratio_pct ASC;

-- 6. Top 10 schemes by Sharpe ratio
SELECT scheme_name, category, sharpe_ratio
FROM fact_performance_analytics
ORDER BY sharpe_ratio DESC
LIMIT 10;

-- 7. Category-level average alpha
SELECT category, AVG(alpha) AS avg_alpha
FROM fact_performance_analytics
GROUP BY category
ORDER BY avg_alpha DESC;

-- 8. Benchmark correlation metrics
SELECT *
FROM report_benchmark_correlation_metrics
ORDER BY computed_statistical_beta DESC;

-- 9. SIP backtest summary
SELECT *
FROM report_sip_backtest_simulation
ORDER BY absolute_sip_return_pct DESC;

-- 10. Sector concentration by fund
SELECT *
FROM fact_portfolio_concentration
ORDER BY top_10_concentration_pct DESC;
