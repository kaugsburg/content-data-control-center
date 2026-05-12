"""
Compares Claude-extracted page data against master sheet data.
Returns a list of mismatch dicts, one per differing data point.
"""

import re


def _normalize_str(value) -> str:
    if value is None:
        return ""
    return re.sub(r"[^\w\s]", "", str(value).lower().strip())


def _normalize_number(value) -> float | None:
    if value is None:
        return None
    cleaned = re.sub(r"[$,\s]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _fuzzy_match(a: str, b: str) -> bool:
    """True if the key words of a appear in b or vice versa."""
    a_norm = _normalize_str(a)
    b_norm = _normalize_str(b)
    # Check direct containment first
    if a_norm in b_norm or b_norm in a_norm:
        return True
    # Check if all significant words from a appear in b
    words_a = set(w for w in a_norm.split() if len(w) > 2)
    words_b = set(w for w in b_norm.split() if len(w) > 2)
    if words_a and words_a.issubset(words_b):
        return True
    if words_b and words_b.issubset(words_a):
        return True
    return False


def _best_cost_match(master_label: str, cost_mentions: list[dict]) -> dict | None:
    """
    Find the cost_mention from the page whose label best matches the master label.
    Returns the best match or None.
    """
    for mention in cost_mentions:
        if _fuzzy_match(master_label, mention.get("label", "")):
            return mention
    return None


def compare(
    url: str,
    extracted: dict,
    master_company_rows: list[dict],
    master_general_rows: list[dict],
) -> list[dict]:
    """
    Compare extracted page data against master data.
    Returns a list of mismatch dicts.
    """
    mismatches = []
    extracted_companies = extracted.get("companies", [])
    cost_mentions = extracted.get("cost_mentions", [])

    # --- Company-level checks (BBB, rating, lawsuit) ---
    for master_row in master_company_rows:
        company = str(master_row.get("Company", "")).strip()
        data_type = str(master_row.get("Data Type", "")).strip().lower()
        master_val = str(master_row.get("Value", "")).strip()

        matched_company = next(
            (c for c in extracted_companies if _fuzzy_match(company, c.get("company_name", ""))),
            None,
        )

        if matched_company is None:
            continue

        found_val = None
        context = None

        if data_type == "bbb_score":
            found_val = matched_company.get("bbb_score")
            context = matched_company.get("bbb_context")
        elif data_type == "rating":
            found_val = matched_company.get("rating")
            context = matched_company.get("rating_context")
        elif data_type == "lawsuit":
            found_val = matched_company.get("lawsuit_summary")
            context = matched_company.get("lawsuit_context")
        elif "cost" in data_type:
            # For company cost types, look in cost_mentions with company name in label
            company_label = f"{company} {data_type.replace('company_', '').replace('_', ' ')}"
            match = _best_cost_match(company_label, cost_mentions)
            if match:
                if "low" in data_type:
                    found_val = match.get("cost_low")
                elif "high" in data_type:
                    found_val = match.get("cost_high")
                else:
                    found_val = match.get("cost_avg")
                context = match.get("context_snippet")

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
    # Build a search label from Category + Data Type and find the best matching
    # cost mention on the page based on that label.
    for master_row in master_general_rows:
        category = str(master_row.get("Category", "")).strip()
        data_type = str(master_row.get("Data Type", "")).strip().lower()
        master_val = str(master_row.get("Value", "")).strip()

        # Combine category and data type into a label to search against page cost labels
        search_label = f"{category} {data_type.replace('_', ' ')}"
        match = _best_cost_match(search_label, cost_mentions)

        if match is None:
            continue

        found_val = None
        context = match.get("context_snippet")

        if "low" in data_type:
            found_val = match.get("cost_low")
        elif "high" in data_type:
            found_val = match.get("cost_high")
        elif "avg" in data_type:
            found_val = match.get("cost_avg")

        if found_val is None:
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
    numeric_types = {"cost_low", "cost_high", "cost_avg", "company_cost_low",
                     "company_cost_high", "company_cost_avg", "rating"}

    if data_type in numeric_types:
        found_num = _normalize_number(found)
        master_num = _normalize_number(master)
        if found_num is not None and master_num is not None:
            if abs(found_num - master_num) < 0.01:
                return None
            return f"Page shows {found_num}, master says {master_num}"

    if _normalize_str(found) == _normalize_str(master):
        return None

    return f"Page shows '{found}', master says '{master}'"
