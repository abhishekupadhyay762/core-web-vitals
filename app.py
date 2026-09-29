import streamlit as st
import gspread
import requests
import time
import pandas as pd
import json

# Page Configuration - Full Width Layout without Sidebar
st.set_page_config(
    page_title="Core Web Vitals & PageSpeed Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    .main .block-container { max-width: 1350px; padding-top: 1.5rem; padding-bottom: 3rem; }
    .hero-title { font-size: 2.3rem; font-weight: 800; color: #1A1D20; letter-spacing: -0.5px; margin-bottom: 0.2rem; }
    .hero-title span { background: linear-gradient(135deg, #FF4B4B 0%, #FF8C00 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero-subtitle { font-size: 1.05rem; color: #6C757D; margin-bottom: 1.5rem; }
    div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E0E0E0; padding: 14px 18px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; font-weight: 600; padding: 8px 18px; border-radius: 8px; }
    .table-section-title { font-size: 1.2rem; font-weight: 700; color: #212529; margin-top: 1rem; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# Safe helper for secrets
def get_secret(key, default=""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default

# Safe helper to compute integer mean without crashing on NaN
def safe_avg(series):
    numeric_s = pd.to_numeric(series, errors="coerce").dropna()
    if not numeric_s.empty:
        mean_val = numeric_s.mean()
        if not pd.isna(mean_val):
            return int(mean_val)
    return 0

# --- PASSWORD CHECK ---
def check_password():
    correct_password = get_secret("APP_PASSWORD", "Damco2026!")

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>🔒 Core Web Vitals Suite</h2>", unsafe_allow_html=True)
        st.caption("<p style='text-align: center;'>Enter passcode to unlock dashboard</p>", unsafe_allow_html=True)
        
        password_input = st.text_input("Passcode", type="password", placeholder="Enter passcode...")
        
        if st.button("Unlock Dashboard", type="primary", use_container_width=True):
            if password_input == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password. Please try again.")
            
    return False

if not check_password():
    st.stop()

# --- HEADER ---
c_title, c_lock = st.columns([5, 1])
with c_title:
    st.markdown("<div class='hero-title'>⚡ Core Web Vitals <span>Complete PageSpeed Suite</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Separate Detailed Tables for Mobile & Desktop: Real Field Data, Scores, and Lab Metrics.</div>", unsafe_allow_html=True)
with c_lock:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔒 Lock App", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- SETTINGS ---
with st.expander("⚙️ API Keys & Configuration Settings", expanded=False):
    col_api, col_sec = st.columns(2)
    with col_api:
        default_api_key = get_secret("PAGESPEED_API_KEY", "")
        api_key = st.text_input("Google PageSpeed API Key", value=default_api_key, type="password")
    with col_sec:
        st.write("**Google Service Account Status:**")
        has_gcp_secret = False
        try:
            if "gcp_service_account" in st.secrets:
                has_gcp_secret = True
        except Exception:
            has_gcp_secret = False

        if has_gcp_secret:
            st.success("✅ Google Credentials active via Secrets!")
        else:
            st.info("ℹ️ Upload `.json` key file below if syncing with Google Sheets.")

if "api_key" not in st.session_state or api_key:
    st.session_state["api_key"] = api_key

# --- COMPLETE PAGESPEED API PARSER ---
def fetch_full_pagespeed(url, strategy, key):
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={key}&strategy={strategy}&category=performance&category=accessibility&category=best-practices&category=seo"
    try:
        response = requests.get(api_url, timeout=45)
        data = response.json()

        # 1. FIELD DATA (Real Chrome User Experience - 28 Day Aggregated CrUX)
        loading_exp = data.get('loadingExperience', {})
        field_metrics = loading_exp.get('metrics', {})
        raw_cwv = loading_exp.get('overall_category', '')

        if raw_cwv == 'FAST':
            cwv_status = "✅ Passed"
        elif raw_cwv in ['AVERAGE', 'SLOW']:
            cwv_status = "❌ Failed"
        else:
            cwv_status = "⚪ No Data"

        field_lcp = f"{field_metrics['LARGEST_CONTENTFUL_PAINT_MS']['percentile'] / 1000:.1f} s" if 'LARGEST_CONTENTFUL_PAINT_MS' in field_metrics else "N/A"
        field_inp = f"{field_metrics['INTERACTION_TO_NEXT_PAINT_MS']['percentile']} ms" if 'INTERACTION_TO_NEXT_PAINT_MS' in field_metrics else "N/A"
        field_cls = f"{field_metrics['CUMULATIVE_LAYOUT_SHIFT_SCORE']['percentile'] / 100:.2f}" if 'CUMULATIVE_LAYOUT_SHIFT_SCORE' in field_metrics else "N/A"
        field_fcp = f"{field_metrics['FIRST_CONTENTFUL_PAINT_MS']['percentile'] / 1000:.1f} s" if 'FIRST_CONTENTFUL_PAINT_MS' in field_metrics else "N/A"
        field_ttfb = f"{field_metrics['EXPERIMENTAL_TIME_TO_FIRST_BYTE']['percentile'] / 1000:.1f} s" if 'EXPERIMENTAL_TIME_TO_FIRST_BYTE' in field_metrics else "N/A"

        # 2. CATEGORY SCORES & AGENTIC BROWSING
        lh = data.get('lighthouseResult', {})
        cats = lh.get('categories', {})
        audits = lh.get('audits', {})

        perf_score = int(cats.get('performance', {}).get('score', 0) * 100) if cats.get('performance') and cats.get('performance', {}).get('score') is not None else "N/A"
        a11y_score = int(cats.get('accessibility', {}).get('score', 0) * 100) if cats.get('accessibility') and cats.get('accessibility', {}).get('score') is not None else "N/A"
        bp_score = int(cats.get('best-practices', {}).get('score', 0) * 100) if cats.get('best-practices') and cats.get('best-practices', {}).get('score') is not None else "N/A"
        seo_score = int(cats.get('seo', {}).get('score', 0) * 100) if cats.get('seo') and cats.get('seo', {}).get('score') is not None else "N/A"

        agentic_pass = 0
        if audits.get('is-on-https', {}).get('score') == 1: agentic_pass += 1
        if audits.get('robots-txt', {}).get('score') != 0: agentic_pass += 1
        if audits.get('canonical', {}).get('score') != 0: agentic_pass += 1
        agentic_browsing = f"🟢 {agentic_pass}/3" if agentic_pass == 3 else f"🟡 {agentic_pass}/3"

        # 3. LAB METRICS
        lab_fcp = audits.get('first-contentful-paint', {}).get('displayValue', 'N/A')
        lab_lcp = audits.get('largest-contentful-paint', {}).get('displayValue', 'N/A')
        lab_tbt = audits.get('total-blocking-time', {}).get('displayValue', 'N/A')
        lab_cls = audits.get('cumulative-layout-shift', {}).get('displayValue', 'N/A')
        lab_si = audits.get('speed-index', {}).get('displayValue', 'N/A')

        return {
            "cwv_status": cwv_status,
            "field_lcp": field_lcp,
            "field_inp": field_inp,
            "field_cls": field_cls,
            "field_fcp": field_fcp,
            "field_ttfb": field_ttfb,
            "perf_score": perf_score,
            "a11y_score": a11y_score,
            "bp_score": bp_score,
            "seo_score": seo_score,
            "agentic_browsing": agentic_browsing,
            "lab_fcp": lab_fcp,
            "lab_lcp": lab_lcp,
            "lab_tbt": lab_tbt,
            "lab_cls": lab_cls,
            "lab_si": lab_si,
        }
    except Exception:
        return {
            "cwv_status": "ERROR", "field_lcp": "Error", "field_inp": "Error", "field_cls": "Error", "field_fcp": "Error", "field_ttfb": "Error",
            "perf_score": "Error", "a11y_score": "Error", "bp_score": "Error", "seo_score": "Error", "agentic_browsing": "Error",
            "lab_fcp": "Error", "lab_lcp": "Error", "lab_tbt": "Error", "lab_cls": "Error", "lab_si": "Error"
        }

def get_gspread_client(uploaded_file):
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            return gspread.service_account_from_dict(creds_dict)
    except Exception:
        pass

    if uploaded_file is not None:
        creds_dict = json.load(uploaded_file)
        return gspread.service_account_from_dict(creds_dict)
    return None

# --- MAIN TABS ---
tab1, tab2 = st.tabs(["🌐 Complete PageSpeed Audit (Instant)", "📊 Google Sheet Auto-Sync"])

# ==================== TAB 1: INSTANT COMPLETE AUDIT ====================
with tab1:
    st.write("### Paste URLs to Run Complete PageSpeed Insights Audit")
    st.caption("Fetches 100% of PageSpeed Insights data separated cleanly into Mobile and Desktop tables.")

    default_urls = "https://www.damcogroup.com/data-collection-services"
    url_text = st.text_area("Webpage URLs", value=default_urls, height=100, placeholder="https://example.com")

    col_run, col_space = st.columns([1, 4])
    with col_run:
        run_direct_audit = st.button("🚀 Start Full Audit", type="primary", use_container_width=True)

    if run_direct_audit:
        curr_key = st.session_state.get("api_key", "")
        raw_urls = [u.strip() for u in url_text.split("\n") if u.strip().startswith("http")]

        if not curr_key:
            st.error("⚠️ PageSpeed API Key missing. Please expand '⚙️ API Keys & Configuration Settings' above.")
        elif not raw_urls:
            st.error("⚠️ Please enter at least one valid URL starting with http:// or https://")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            mob_rows = []
            desk_rows = []

            for i, url in enumerate(raw_urls):
                progress = (i + 1) / len(raw_urls)
                progress_bar.progress(progress)

                status_text.markdown(f"⏳ **Auditing Mobile ({i+1}/{len(raw_urls)}):** `{url}`")
                mob = fetch_full_pagespeed(url, "mobile", curr_key)
                time.sleep(1.5)

                status_text.markdown(f"⏳ **Auditing Desktop ({i+1}/{len(raw_urls)}):** `{url}`")
                desk = fetch_full_pagespeed(url, "desktop", curr_key)
                time.sleep(1.5)

                # Mobile Row
                mob_rows.append({
                    "URL": url,
                    "CWV Assessment": mob["cwv_status"],
                    "Real LCP": mob["field_lcp"],
                    "Real INP": mob["field_inp"],
                    "Real CLS": mob["field_cls"],
                    "Real FCP": mob["field_fcp"],
                    "Real TTFB": mob["field_ttfb"],
                    "Performance": mob["perf_score"],
                    "Accessibility": mob["a11y_score"],
                    "Best Practices": mob["bp_score"],
                    "SEO": mob["seo_score"],
                    "Agentic Browsing": mob["agentic_browsing"],
                    "Lab FCP": mob["lab_fcp"],
                    "Lab LCP": mob["lab_lcp"],
                    "Lab TBT": mob["lab_tbt"],
                    "Lab CLS": mob["lab_cls"],
                    "Lab Speed Index": mob["lab_si"],
                })

                # Desktop Row
                desk_rows.append({
                    "URL": url,
                    "CWV Assessment": desk["cwv_status"],
                    "Real LCP": desk["field_lcp"],
                    "Real INP": desk["field_inp"],
                    "Real CLS": desk["field_cls"],
                    "Real FCP": desk["field_fcp"],
                    "Real TTFB": desk["field_ttfb"],
                    "Performance": desk["perf_score"],
                    "Accessibility": desk["a11y_score"],
                    "Best Practices": desk["bp_score"],
                    "SEO": desk["seo_score"],
                    "Agentic Browsing": desk["agentic_browsing"],
                    "Lab FCP": desk["lab_fcp"],
                    "Lab LCP": desk["lab_lcp"],
                    "Lab TBT": desk["lab_tbt"],
                    "Lab CLS": desk["lab_cls"],
                    "Lab Speed Index": desk["lab_si"],
                })

            progress_bar.progress(100)
            status_text.success("🎉 PageSpeed Audit Completed!")

            df_mob = pd.DataFrame(mob_rows)
            df_desk = pd.DataFrame(desk_rows)

            # Store in session state for tab switching
            st.session_state["df_mob"] = df_mob
            st.session_state["df_desk"] = df_desk

    if "df_mob" in st.session_state and "df_desk" in st.session_state:
        df_m = st.session_state["df_mob"]
        df_d = st.session_state["df_desk"]

        # High level KPIs
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Pages", len(df_m))
        k2.metric("Avg Mob Perf", f"{safe_avg(df_m['Performance'])}/100")
        k3.metric("Avg Desk Perf", f"{safe_avg(df_d['Performance'])}/100")
        k4.metric("Avg Mob SEO", f"{safe_avg(df_m['SEO'])}/100")
        k5.metric("Avg Desk SEO", f"{safe_avg(df_d['SEO'])}/100")

        st.divider()

        # SEPARATE DEVICE TABS
        sub_tab_mob, sub_tab_desk, sub_tab_combined = st.tabs([
            "📱 Mobile Metrics Table", 
            "💻 Desktop Metrics Table", 
            "📊 Side-by-Side Comparison"
        ])

        with sub_tab_mob:
            st.markdown("<div class='table-section-title'>📱 Mobile Performance Audit Results</div>", unsafe_allow_html=True)
            st.dataframe(df_m, use_container_width=True)

            csv_m = df_m.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Mobile Report CSV", data=csv_m, file_name="mobile_pagespeed_report.csv", mime="text/csv")

        with sub_tab_desk:
            st.markdown("<div class='table-section-title'>💻 Desktop Performance Audit Results</div>", unsafe_allow_html=True)
            st.dataframe(df_d, use_container_width=True)

            csv_d = df_d.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Desktop Report CSV", data=csv_d, file_name="desktop_pagespeed_report.csv", mime="text/csv")

        with sub_tab_combined:
            st.markdown("<div class='table-section-title'>📊 Combined Mobile vs Desktop Comparison Table</div>", unsafe_allow_html=True)
            combined_df = pd.merge(df_m[["URL", "Performance", "Real LCP", "Lab LCP"]], df_d[["URL", "Performance", "Real LCP", "Lab LCP"]], on="URL", suffixes=(" (Mobile)", " (Desktop)"))
            st.dataframe(combined_df, use_container_width=True)

            csv_all = pd.concat([df_m.add_prefix("Mob_"), df_d.add_prefix("Desk_")], axis=1).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Complete (Mobile + Desktop) CSV", data=csv_all, file_name="complete_pagespeed_report.csv", mime="text/csv")


# ==================== TAB 2: GOOGLE SHEET AUTO-SYNC ====================
with tab2:
    st.write("### Sync All PageSpeed Metrics to Google Sheets")
    st.caption("Pulls URLs from Column A of your Google Sheet and updates columns with complete Mobile & Desktop metrics.")

    c_sname, c_json = st.columns([2, 2])
    with c_sname:
        sheet_name_input = st.text_input("Google Sheet Name", value="BPO Webpage")
    with c_json:
        uploaded_json_file = None
        if not has_gcp_secret:
            uploaded_json_file = st.file_uploader("Upload Service Account `.json` Key", type=["json"])
        else:
            st.success("✅ Google Credentials ready from Streamlit Secrets")

    run_sheet_sync = st.button("🔄 Sync & Update Google Sheet", type="primary")

    if run_sheet_sync:
        curr_key = st.session_state.get("api_key", "")
        gc = get_gspread_client(uploaded_json_file)

        if not curr_key:
            st.error("⚠️ PageSpeed API Key missing. Check configuration expander above.")
        elif gc is None:
            st.error("⚠️ Service Account JSON key is missing. Upload your `.json` key file above.")
        else:
            try:
                with st.spinner(f"Opening Google Sheet '{sheet_name_input}'..."):
                    sh = gc.open(sheet_name_input)
                    worksheet = sh.sheet1
                    urls = worksheet.col_values(1)[1:]

                st.info(f"Loaded **{len(urls)} URLs** from Google Sheet `{sheet_name_input}`. Running full PageSpeed audit...")

                headers = [
                    # Mobile
                    "Mob Perf", "Mob A11y", "Mob BestPrac", "Mob SEO", "Mob Agentic", "Mob Real CWV", "Mob Real LCP", "Mob Real INP", "Mob Real CLS", "Mob Real FCP", "Mob Real TTFB", "Mob Lab LCP", "Mob Lab TBT",
                    # Desktop
                    "Desk Perf", "Desk A11y", "Desk BestPrac", "Desk SEO", "Desk Agentic", "Desk Real CWV", "Desk Real LCP", "Desk Real INP", "Desk Real CLS", "Desk Real FCP", "Desk Real TTFB", "Desk Lab LCP", "Desk Lab TBT"
                ]
                worksheet.update(range_name='B1:AA1', values=[headers])

                progress_bar = st.progress(0)
                status_text = st.empty()

                all_sheet_results = []
                display_rows = []

                for i, url in enumerate(urls):
                    url_str = url.strip()
                    progress = (i + 1) / len(urls)
                    progress_bar.progress(progress)

                    if not url_str or not url_str.startswith("http"):
                        all_sheet_results.append([""] * len(headers))
                        continue

                    status_text.markdown(f"⏳ **Auditing ({i+1}/{len(urls)}):** `{url_str}`")

                    mob = fetch_full_pagespeed(url_str, "mobile", curr_key)
                    time.sleep(1.2)
                    desk = fetch_full_pagespeed(url_str, "desktop", curr_key)
                    time.sleep(1.2)

                    row_vals = [
                        # Mobile
                        mob["perf_score"], mob["a11y_score"], mob["bp_score"], mob["seo_score"], mob["agentic_browsing"], mob["cwv_status"], mob["field_lcp"], mob["field_inp"], mob["field_cls"], mob["field_fcp"], mob["field_ttfb"], mob["lab_lcp"], mob["lab_tbt"],
                        # Desktop
                        desk["perf_score"], desk["a11y_score"], desk["bp_score"], desk["seo_score"], desk["agentic_browsing"], desk["cwv_status"], desk["field_lcp"], desk["field_inp"], desk["field_cls"], desk["field_fcp"], desk["field_ttfb"], desk["lab_lcp"], desk["lab_tbt"]
                    ]
                    all_sheet_results.append(row_vals)
                    display_rows.append([url_str] + row_vals)

                if all_sheet_results:
                    end_row = len(all_sheet_results) + 1
                    worksheet.update(range_name=f"B2:AA{end_row}", values=all_sheet_results)
                    status_text.success(f"🎉 **Success!** Updated Google Sheet `{sheet_name_input}` with complete Mobile & Desktop PageSpeed metrics!")

                    df_cols = ["URL"] + headers
                    df_sheet = pd.DataFrame(display_rows, columns=df_cols)
                    st.dataframe(df_sheet, use_container_width=True)

                    csv = df_sheet.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Report CSV", data=csv, file_name="sheet_full_audit.csv", mime="text/csv")

            except Exception as e:
                st.error(f"❌ Google Sheet Error: {e}")
