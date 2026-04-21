# Agentic Options Trader

## Overview
AI-powered options trading agent that reviews portfolios and makes recommendations. Backtested against historical data before live use.

## Tech Stack
- **Language**: Python
- **Agent Framework**: LangGraph
- **API**: FastAPI
- **Frontend**: TBD
- **Database**: DuckDB for data storage and analytical queries
- **Data Source**: Portfolios maintained in Google Sheets
- **Market Data**: Massive.com API for historical options chain data

## Project Structure
- `data/` — Raw and processed market data
- `src/` — Main application source code
- `tests/` — Test suite

## Development
- Use Python virtual environment (`venv`)
- Install dependencies: `pip install -r requirements.txt`
