"""
Compares Claude-extracted page data against master sheet data.
Returns a list of mismatch dicts, one per differing data point.
"""

import re


def _normalize_str(value) -> str:
    """Lowercase, strip whitespace and common punctuation for fuzzy matching."""
    if value is None:
        return ""
    return re.sub(r"[^\w.]", "", str(value).lower().strip())


def _normalize_number(value) -> float | None:
    """Strip $, commas and return as float, or None if unparseable."""
    if value is None:
        return None
    cleaned = re.sub(r"[$,\s]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _fuzzy_company_match(master_name: str, extracted_name: str) -> bool:
    """
    True if extracted company name contains the master name or vice versa
    (handles minor phrasing differences like 'Andersen' vs 'Andersen Windows').
    """
    a = _normalize_str(master_name)
    b = _normalize_str(extracted_name)
    return a in b or b in a


def compare(
    url: str,
    extracted: dict,
    master_company_rows: list[dict],
    master_general_rows: list[dict],
) -> list[dict]:
    """
    Compare extracted page data against both master data sources.

    Returns a list of mismatch dicts with keys:
        page_url, company_or_category, data_type,
        found_on_page, master_value, notes, context_snippet
    """
    mismatches = []

    extracted_companies = extracted.get("companies", [])
    extracted_general = extracted.get("general_costs", [])

    # --- Company-level checks ---
    for master_row in master_company_rows:
        company = str(master_row.get("Company", "")).strip()
        data_type = str(master_row.get("Data Type", "")).strip().lower()
        master_val = str(master_row.get("Value", "")).strip()

        # Find matching company in extracted data
        matched_company = next(
            (c for c in extracted_companies if _fuzzy_company_match(company, c.get("company_name", ""))),
            None,
        )

        if matched_company is None:
            # Company not found on this page — skip (may be a different page's data)
            continue

        found_val = None
        context = None

        if data_type == "bbb_score":
            found_val = matched_company.get("bbb_score")
            context = matched_company.get("bbb_context")
        elif data_type == "rating":
            found_val = matched_company.get("rating")
            context = matched_company.get("rating_context")
        elif data_type in ("company_cost_low", "cost_low"):
            found_val = matched_company.get("cost_low")
            context = matched_company.get("cost_context")
        elif data_type in ("company_cost_high", "cost_high"):
            found_val = matched_company.get("cost_high")
            context = matched_company.get("cost_context")
        elif data_type in ("company_cost_avg", "cost_avg"):
            found_val = matched_company.get("cost_avg")
            context = matched_company.get("cost_context")
        elif data_type == "lawsuit":
            found_val = matched_company.get("lawsuit_summary")
            context = matched_company.get("lawsuit_context")

        if found_val is None:
            mismatches.append({
                "page_url": url,
                "company_or_category": company,
                "data_type": data_type,
                "found_on_page": "NOT FOUND",
                "master_value": master_val,
                "notes": f"Could not find {data_type} for {company} on this page.",
                "context_snippet": None,
            })
            continue

        mismatch = _values_differ(data_type, str(found_val), master_val)
        if mismatch:
            mismatches.append({
                "page_url": url,
                "company_or_category": company,
                "data_type": data_type,
                "found_on_page": str(found_val),
                "master_value": master_val,
                "notes": mismatch,
                "context_snippet": context,
            })

    # --- General cost checks ---
    for master_row in master_general_rows:
        category = str(master_row.get("Category", "")).strip()
        data_type = str(master_row.get("Data Type", "")).strip().lower()
        master_val = str(master_row.get("Value", "")).strip()

        matched_general = next(
            (g for g in extracted_general if _fuzzy_company_match(category, g.get("category", ""))),
            None,
        )

        if matched_general is None:
            continue

        found_val = None
        context = matched_general.get("context_snippet")

        if data_type == "cost_low":
            found_val = matched_general.get("cost_low")
        elif data_type == "cost_high":
            found_val = matched_general.get("cost_high")
        elif data_type == "cost_avg":
            found_val = matched_general.get("cost_avg")

        if found_val is None:
            mismatches.append({
                "page_url": url,
                "company_or_category": category,
                "data_type": data_type,
                "found_on_page": "NOT FOUND",
                "master_value": master_val,
                "notes": f"Could not find {data_type} for category '{category}' on this page.",
                "context_snippet": None,
            })
            continue

        mismatch = _values_differ(data_type, str(found_val), master_val)
        if mismatch:
            mismatches.append({
                "page_url": url,
                "company_or_category": category,
                "data_type": data_type,
                "found_on_page": str(found_val),
                "master_value": master_val,
                "notes": mismatch,
                "context_snippet": context,
            })

    return mismatches


def _values_differ(data_type: str, found: str, master: str) -> str | None:
    """
    Compare two values. Returns a human-readable note if they differ, else None.
    Uses numeric comparison for cost/rating types, string comparison for others.
    """
    numeric_types = {"cost_low", "cost_high", "cost_avg", "company_cost_low",
                     "company_cost_high", "company_cost_avg", "rating"}

    if data_type in numeric_types:
        found_num = _normalize_number(found)
        master_num = _normalize_number(master)
        if found_num is None or master_num is None:
            # Fall through to string comparison
            pass
        elif abs(found_num - master_num) < 0.01:
            return None
        else:
            return f"Page shows {found_num}, master says {master_num}"

    # String comparison (BBB score, lawsuit, etc.)
    if _normalize_str(found) == _normalize_str(master):
        return None

    return f"Page shows '{found}', master says '{master}'"
