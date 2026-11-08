# Plan: Startup Funding Tracker (Last 6 Months) - United States & Canada

## 1. Scope & Timeframe
- **Timeframe**: May 2026 – November 2026 (Last 6 months relative to Nov 4, 2026)
- **Geography**: United States and Canada
- **Focus**: Seed, Series A, Series B, Series C+, and notable late-stage rounds (excluding IPOs/M&A unless specified)

## 2. Data Sources & Collection Strategy
- **Primary Sources**:
  - Crunchbase (Funding rounds, amounts, investors)
  - PitchBook (Private market data)
  - TechCrunch / VentureBeat / Financial Post (News announcements)
  - CB Insights (Market reports)
- **Secondary Sources**:
  - Company press releases
  - SEC filings (Form D in US)
  - Canadian Securities Administrators (SEDAR filings)
- **Automation/Tools**:
  - Web scraping/API (if available) or manual extraction from news aggregators
  - Search queries: "startup funding [Month] [Year] US Canada", "Series A funding [Month] [Year] North America"

## 3. Data Structure (Spreadsheet/Database Columns)
| Date | Company Name | Industry | Location (City, State/Province) | Country | Round Type | Amount (USD/CAD) | Lead Investors | Source Link |
|------|--------------|----------|---------------------------------|---------|------------|------------------|----------------|-------------|

## 4. Execution Phases

### Phase 1: Initial Data Gathering (May 2026 – Oct 2026)
- **Task 1.1**: Retrieve monthly summaries for May, June, July, August, September, October 2026.
- **Task 1.2**: Filter for US and Canada.
- **Task 1.3**: Populate the initial list in `funding_tracker.csv` or `funding_tracker.md`.

### Phase 2: November 2026 Update (Current Month)
- **Task 2.1**: Daily/Weekly scrape for November 1–4, 2026 (and ongoing).
- **Task 2.2**: Append new entries to the tracker.

### Phase 3: Maintenance & Updates
- **Task 3.1**: Weekly audit for corrections (amount adjustments, investor updates).
- **Task 3.2**: Monthly summary generation (Total funding by sector, top investors).

## 5. Implementation Steps (Workspace Files)
1. **Create Tracker File**: `startup_funding_tracker.csv` (or `.md` for readability in Arena viewer).
2. **Create Research Log**: `research_log.md` (to track sources and search queries).
3. **Create Summary Report**: `monthly_summary_report.md`.

## 6. Next Steps for Immediate Action
- Perform web searches for May 2026 – October 2026 funding rounds in US/Canada.
- Compile initial entries into the tracker.
- Set up a process for November 2026 ongoing updates.

## 7. Update Cadence
- **Initial Build**: Immediate (covering May–Oct 2026).
- **Ongoing**: Weekly updates for new rounds in November 2026 and beyond.
