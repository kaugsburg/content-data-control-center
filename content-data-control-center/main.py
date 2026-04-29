"""
Content Data Control Center
Run:  python main.py
"""

import sys
import time
import sheets
import page_fetcher
import extractor
import comparator
import doc_generator


def run():
    print("\n=== Content Data Control Center ===\n")

    # 1. Load data from Google Sheets
    print("Loading master data from Google Sheets...")
    try:
        urls = sheets.read_urls()
        master_company = sheets.read_master_company_data()
        master_general = sheets.read_general_cost_data()
    except Exception as e:
        print(f"ERROR: Could not load Google Sheets data.\n{e}")
        sys.exit(1)

    if not urls:
        print("No URLs found in the 'URLs' tab. Add page URLs to that tab and re-run.")
        sys.exit(0)

    print(f"  {len(urls)} URL(s) to check")
    print(f"  {len(master_company)} company data row(s)")
    print(f"  {len(master_general)} general cost row(s)\n")

    all_report_rows = []

    # 2. Process each URL
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")

        # Fetch page
        try:
            page_text, page_title = page_fetcher.fetch_page(url)
            print(f"  Fetched: \"{page_title}\" ({len(page_text)} chars)")
        except Exception as e:
            print(f"  SKIP — could not fetch page: {e}\n")
            continue

        # Extract data with Claude
        try:
            print("  Extracting data with AI...")
            extracted = extractor.extract_data_from_page(page_text)
        except Exception as e:
            print(f"  SKIP — extraction failed: {e}\n")
            continue

        companies_found = [c.get("company_name", "") for c in extracted.get("companies", [])]
        print(f"  Found companies: {companies_found or 'none'}")

        # Compare against master data
        mismatches = comparator.compare(url, extracted, master_company, master_general)

        if not mismatches:
            print("  ✓ No mismatches — page is up to date.\n")
            continue

        print(f"  ! {len(mismatches)} mismatch(es) found:")
        for m in mismatches:
            print(f"    - {m['company_or_category']} / {m['data_type']}: {m['notes']}")

        # Create Google Doc with highlighted mismatches
        try:
            doc_url = doc_generator.create_review_doc(
                page_title=page_title,
                page_url=url,
                page_text=page_text,
                mismatches=mismatches,
            )
        except Exception as e:
            print(f"  WARNING — could not create review doc: {e}")
            doc_url = ""

        # Collect rows for Audit Report
        for m in mismatches:
            all_report_rows.append({**m, "doc_link": doc_url})

        print()

        # Be polite — don't hammer the site with back-to-back requests
        if i < len(urls):
            time.sleep(1.5)

    # 3. Write all mismatches to Audit Report tab
    if all_report_rows:
        print(f"Writing {len(all_report_rows)} mismatch row(s) to Audit Report tab...")
        try:
            sheets.write_audit_report(all_report_rows)
        except Exception as e:
            print(f"ERROR: Could not write to Audit Report tab.\n{e}")
    else:
        print("All pages are up to date — nothing written to Audit Report.")

    print("\n=== Run complete ===\n")


if __name__ == "__main__":
    run()
