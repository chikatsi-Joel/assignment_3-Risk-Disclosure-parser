# edgar_fetcher.py — SEC EDGAR API client
# Fetches 10-K and 10-Q filing metadata and HTML documents.
# Requires User-Agent header per SEC policy.

import time
import requests
from typing import Optional

HEADERS_DATA = {
    "User-Agent": "FinancialIntelligencePlatform samuelpiedjou@gmail.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}
HEADERS_WWW = {
    "User-Agent": "FinancialIntelligencePlatform samuelpiedjou@gmail.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}

EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions"
EDGAR_ARCHIVES    = "https://www.sec.gov/Archives/edgar/data"

# ─── Bank catalog ──────────────────────────────────────────────────
BANKS_CATALOG: dict[str, dict] = {
    "JPMorgan Chase": {
        "cik": "19617",
        "ticker": "JPM",
        "description": "Largest US bank by total assets (~$3.9T)",
        "sector": "Money-Center Bank",
    },
    "Bank of America": {
        "cik": "70858",
        "ticker": "BAC",
        "description": "Second-largest US bank (~$3.3T assets)",
        "sector": "Money-Center Bank",
    },
    "Wells Fargo": {
        "cik": "72971",
        "ticker": "WFC",
        "description": "Consumer & commercial banking giant",
        "sector": "Money-Center Bank",
    },
    "Citigroup": {
        "cik": "831001",
        "ticker": "C",
        "description": "Global universal bank with 200+ countries",
        "sector": "Money-Center Bank",
    },
    "Goldman Sachs": {
        "cik": "886982",
        "ticker": "GS",
        "description": "Premier investment & capital markets bank",
        "sector": "Investment Bank",
    },
    "Morgan Stanley": {
        "cik": "895421",
        "ticker": "MS",
        "description": "Wealth management & investment banking",
        "sector": "Investment Bank",
    },
    "U.S. Bancorp": {
        "cik": "36104",
        "ticker": "USB",
        "description": "Largest regional bank in the US",
        "sector": "Regional Bank",
    },
    "PNC Financial": {
        "cik": "713676",
        "ticker": "PNC",
        "description": "Major Mid-Atlantic regional bank",
        "sector": "Regional Bank",
    },
    "Truist Financial": {
        "cik": "92122",
        "ticker": "TFC",
        "description": "Southeast US regional bank (BB&T + SunTrust)",
        "sector": "Regional Bank",
    },
    "Capital One": {
        "cik": "927628",
        "ticker": "COF",
        "description": "Consumer credit & digital banking",
        "sector": "Consumer Bank",
    },
    "Charles Schwab": {
        "cik": "316709",
        "ticker": "SCHW",
        "description": "Brokerage-turned-bank powerhouse",
        "sector": "Brokerage/Bank",
    },
    "American Express": {
        "cik": "4962",
        "ticker": "AXP",
        "description": "Premium card network & issuer",
        "sector": "Consumer Credit",
    },
}


def _get(url: str, host_headers: dict, timeout: int = 25) -> requests.Response:
    """Shared GET with retry on 429."""
    for attempt in range(3):
        resp = requests.get(url, headers=host_headers, timeout=timeout)
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def get_company_filings(cik: str, form_type: str = "10-K", count: int = 8) -> list[dict]:
    """Return a list of recent filings for one company from EDGAR."""
    cik_padded = cik.zfill(10)
    url = f"{EDGAR_SUBMISSIONS}/CIK{cik_padded}.json"
    data = _get(url, HEADERS_DATA).json()

    recent       = data.get("filings", {}).get("recent", {})
    forms        = recent.get("form", [])
    accessions   = recent.get("accessionNumber", [])
    dates        = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    results: list[dict] = []
    for i, form in enumerate(forms):
        if form != form_type or len(results) >= count:
            continue
        acc_nodash = accessions[i].replace("-", "")
        results.append({
            "accession":      accessions[i],
            "accession_nd":   acc_nodash,
            "date":           dates[i],
            "form":           form,
            "cik":            cik,
            "primary_doc":    primary_docs[i] if i < len(primary_docs) else "",
            "description":    descriptions[i] if i < len(descriptions) else "",
            "base_url":       f"{EDGAR_ARCHIVES}/{cik}/{acc_nodash}/",
            "index_url":      f"{EDGAR_ARCHIVES}/{cik}/{acc_nodash}/{accessions[i]}-index.htm",
        })

    time.sleep(0.12)  # Respect SEC 10 req/s limit
    return results


def fetch_filing_html(cik: str, acc_nd: str, primary_doc: str) -> str:
    """Download the main HTML document for a filing."""
    url = f"{EDGAR_ARCHIVES}/{cik}/{acc_nd}/{primary_doc}"
    resp = _get(url, HEADERS_WWW, timeout=40)
    time.sleep(0.12)
    return resp.text


def get_all_banks_latest_filing(form_type: str = "10-K") -> dict[str, Optional[dict]]:
    """Fetch the most recent filing metadata for every bank in the catalog."""
    result: dict[str, Optional[dict]] = {}
    for name, info in BANKS_CATALOG.items():
        try:
            filings = get_company_filings(info["cik"], form_type=form_type, count=1)
            result[name] = filings[0] if filings else None
        except Exception:
            result[name] = None
    return result
