import time
import streamlit as st
import sheets
import page_fetcher
import extractor
import comparator
import doc_generator

st.set_page_config(
    page_title="Content Data Control Center",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Content Data Control Center")
st.caption("thisoldhouse.com — Automated data mismatch checker")

# ── Session state defaults ───────────────────────────────────────────────────
if "run_results" not in st.session_state:
    st.session_state.run_results = []
if "last_run_summary" not in st.session_state:
    st.session_state.last_run_summary = ""


# ── Sidebar — URL management ─────────────────────────────────────────────────
with st.sidebar:
    st.header("Page URLs")
    st.caption("URLs are stored in the 'URLs' tab of your Google Sheet.")

    if st.button("🔄 Refresh URL list", use_container_width=True):
        st.cache_data.clear()

    try:
        urls = sheets.read_urls()
        if urls:
            st.success(f"{len(urls)} URL(s) loaded")
            with st.expander("View URLs", expanded=False):
                for u in urls:
                    st.write(u)
        else:
            st.warning("No URLs found. Add URLs to the 'URLs' tab in your Google Sheet.")
            urls = []
    except Exception as e:
        st.error(f"Could not load URLs from Google Sheets:\n{e}")
        urls = []

    st.divider()
    st.caption("To add or remove pages, edit the **URLs** tab in your Google Sheet, then click Refresh.")


# ── Main area ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Run a Data Check")
    st.write(
        "Click the button below to check all tracked pages against your master data. "
        "Only pages with outdated data will appear in the results."
    )

with col2:
    st.metric("Pages to check", len(urls))

run_button = st.button(
    "▶ Run Data Check",
    type="primary",
    disabled=len(urls) == 0,
    use_container_width=False,
)

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_button:
    st.session_state.run_results = []
    st.session_state.last_run_summary = ""

    progress_bar = st.progress(0, text="Starting...")
    log = st.container()

    try:
        with log:
            st.info("Loading master data from Google Sheets...")
        master_company = sheets.read_master_company_data()
        master_general = sheets.read_general_cost_data()
        with log:
            st.success(
                f"Loaded {len(master_company)} company row(s) and "
                f"{len(master_general)} general cost row(s)."
            )
    except Exception as e:
        st.error(f"Could not load master data: {e}")
        st.stop()

    all_report_rows = []
    total = len(urls)

    for i, url in enumerate(urls):
        progress_bar.progress((i) / total, text=f"Checking page {i + 1} of {total}…")

        with log:
            st.write(f"**[{i+1}/{total}]** `{url}`")

        # Fetch page
        try:
            page_text, page_title = page_fetcher.fetch_page(url)
            with log:
                st.write(f"&nbsp;&nbsp;↳ Fetched: *{page_title}*")
        except Exception as e:
            with log:
                st.warning(f"&nbsp;&nbsp;↳ Could not fetch page — skipping. ({e})")
            continue

        # Extract with Claude
        try:
            extracted = extractor.extract_data_from_page(page_text)
        except Exception as e:
            with log:
                st.warning(f"&nbsp;&nbsp;↳ Extraction failed — skipping. ({e})")
            continue

        # Compare
        mismatches = comparator.compare(url, extracted, master_company, master_general)

        if not mismatches:
            with log:
                st.write("&nbsp;&nbsp;↳ ✅ Up to date — no mismatches.")
            time.sleep(1.5)
            continue

        with log:
            st.write(f"&nbsp;&nbsp;↳ ⚠️ {len(mismatches)} mismatch(es) found")

        # Create review doc
        doc_url = ""
        try:
            doc_url = doc_generator.create_review_doc(
                page_title=page_title,
                page_url=url,
                page_text=page_text,
                mismatches=mismatches,
            )
            with log:
                st.write(f"&nbsp;&nbsp;↳ 📄 [Review doc created]({doc_url})")
        except Exception as e:
            with log:
                st.warning(f"&nbsp;&nbsp;↳ Could not create review doc. ({e})")

        for m in mismatches:
            all_report_rows.append({**m, "doc_link": doc_url})

        time.sleep(1.5)

    progress_bar.progress(1.0, text="Done!")

    # Write to Audit Report sheet
    if all_report_rows:
        try:
            sheets.write_audit_report(all_report_rows)
        except Exception as e:
            st.error(f"Could not write to Audit Report tab: {e}")

    st.session_state.run_results = all_report_rows
    st.session_state.last_run_summary = (
        f"Run complete — {total} page(s) checked, "
        f"{len(all_report_rows)} mismatch(es) found."
    )

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.last_run_summary:
    st.divider()
    st.header("Results")

    results = st.session_state.run_results
    summary = st.session_state.last_run_summary

    if not results:
        st.success(f"✅ {summary}")
    else:
        st.warning(f"⚠️ {summary}")

        # Group by page URL so each page has one expander with its mismatches + doc link
        pages: dict[str, list[dict]] = {}
        for row in results:
            pages.setdefault(row["page_url"], []).append(row)

        for page_url, rows in pages.items():
            doc_link = rows[0].get("doc_link", "")
            label = f"**{page_url}** — {len(rows)} mismatch(es)"
            with st.expander(label, expanded=True):
                if doc_link:
                    st.markdown(f"📄 [Open Review Doc]({doc_link})")

                table_data = [
                    {
                        "Company / Category": r["company_or_category"],
                        "Data Type": r["data_type"],
                        "Found on Page": r["found_on_page"],
                        "Should Be": r["master_value"],
                        "Notes": r["notes"],
                    }
                    for r in rows
                ]
                st.table(table_data)

        st.info("All mismatches have been logged to the **Audit Report** tab in your Google Sheet.")
