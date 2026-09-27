import streamlit as st
import gspread
import requests
import time
import pandas as pd
import json

# Page Configuration - Full Width Layout without Sidebar
st.set_page_config(
    page_title="Core Web Vitals Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for Sleek, Professional Dashboard
st.markdown("""
<style>
    /* Hide Sidebar completely if any remains */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Main container styling */
    .main .block-container {
        max-width: 1200px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }
    
    /* Header styling */
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #1A1D20;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .hero-title span {
        background: linear-gradient(135deg, #FF4B4B 0%, #FF8C00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #6C757D;
        margin-bottom: 1.8rem;
    }
    
    /* Settings Expander styling */
    .settings-card {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 1.5rem;
    }
    
    /* Metric Card styling */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        padding: 10px 20px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Safe helper to access Streamlit secrets
def get_secret(key, default=""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default

# --- 1. PASSWORD PROTECTION ---
def check_password():
    """Returns True if the user entered the correct password."""
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

# --- 2. HEADER ---
c_title, c_lock = st.columns([5, 1])
with c_title:
    st.markdown("<div class='hero-title'>⚡ Core Web Vitals <span>Audit Suite</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Dual-Audit Mobile & Desktop LCP, CLS, and INP metrics in real-time.</div>", unsafe_allow_html=True)
with c_lock:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔒 Lock App", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 3. TOP SETTINGS PANEL (CLEAN & COLLAPSIBLE) ---
with st.expander("⚙️ API Keys & Authentication Settings", expanded=False):
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

# Save API Key in session state for convenience
if "api_key" not in st.session_state or api_key:
    st.session_state["api_key"] = api_key

# --- HELPER FUNCTIONS ---
def get_metrics(url, strategy, key):
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={key}&strategy={strategy}"
    try:
        response = requests.get(api_url, timeout=35)
        data = response.json()

        lh = data.get('lighthouseResult', {})
        audits = lh.get('audits', {})
        score = int(lh.get('categories', {}).get('performance', {}).get('score', 0) * 100)
        lcp = audits.get('largest-contentful-paint', {}).get('displayValue', 'N/A')
        cls = audits.get('cumulative-layout-shift', {}).get('displayValue', 'N/A')

        field_metrics = data.get('loadingExperience', {}).get('metrics', {})

        if 'INTERACTION_TO_NEXT_PAINT_MS' in field_metrics:
            inp_value = f"{field_metrics['INTERACTION_TO_NEXT_PAINT_MS']['percentile']} ms (Real)"
        else:
            tbt = audits.get('total-blocking-time', {}).get('displayValue', 'N/A')
            inp_value = f"{tbt} (TBT Proxy)"

        return [score, lcp, cls, inp_value]
    except Exception:
        return ["Error", "Error", "Error", "Error"]

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

# --- MAIN DASHBOARD TABS ---
tab1, tab2 = st.tabs(["🌐 Instant Direct URL Audit", "📊 Google Sheet Auto-Sync"])

# ==================== TAB 1: INSTANT DIRECT URL AUDIT ====================
with tab1:
    st.write("### Paste URLs to Audit")
    st.caption("Enter one URL per line. No Google Sheet or JSON file required.")

    default_urls = "https://www.google.com\nhttps://www.wikipedia.org"
    url_text = st.text_area("Webpage URLs", value=default_urls, height=130, placeholder="https://example.com\nhttps://example.com/blog")

    col_run, col_space = st.columns([1, 4])
    with col_run:
        run_direct_audit = st.button("🚀 Start Instant Audit", type="primary", use_container_width=True)

    if run_direct_audit:
        curr_key = st.session_state.get("api_key", "")
        raw_urls = [u.strip() for u in url_text.split("\n") if u.strip().startswith("http")]

        if not curr_key:
            st.error("⚠️ PageSpeed API Key missing. Please expand '⚙️ API Keys & Authentication Settings' above.")
        elif not raw_urls:
            st.error("⚠️ Please enter at least one valid URL starting with http:// or https://")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            results = []
            headers = [
                "URL", "Mobile Score", "Mobile LCP", "Mobile CLS", "Mobile INP / TBT",
                "Desktop Score", "Desktop LCP", "Desktop CLS", "Desktop INP / TBT"
            ]

            for i, url in enumerate(raw_urls):
                progress = (i + 1) / len(raw_urls)
                progress_bar.progress(progress)
                status_text.markdown(f"⏳ **Auditing page ({i+1}/{len(raw_urls)}):** `{url}`")

                mob = get_metrics(url, "mobile", curr_key)
                time.sleep(1.2)
                desk = get_metrics(url, "desktop", curr_key)
                time.sleep(1.2)

                results.append([url] + mob + desk)

            progress_bar.progress(100)
            status_text.success("🎉 Audit finished successfully!")

            df = pd.DataFrame(results, columns=headers)

            # Calculate High-level Summary Metrics
            valid_mob = pd.to_numeric(df["Mobile Score"], errors="coerce").dropna()
            valid_desk = pd.to_numeric(df["Desktop Score"], errors="coerce").dropna()

            avg_mob = int(valid_mob.mean()) if not valid_mob.empty else 0
            avg_desk = int(valid_desk.mean()) if not valid_desk.empty else 0

            st.divider()

            # KPI CARDS
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Pages Audited", len(results))
            k2.metric("Avg Mobile Score", f"{avg_mob} / 100", delta="🟢 Good" if avg_mob>=90 else "🟡 Needs Imp." if avg_mob>=50 else "🔴 Poor")
            k3.metric("Avg Desktop Score", f"{avg_desk} / 100", delta="🟢 Good" if avg_desk>=90 else "🟡 Needs Imp." if avg_desk>=50 else "🔴 Poor")
            
            good_pages = len(df[(pd.to_numeric(df["Mobile Score"], errors="coerce") >= 90) & (pd.to_numeric(df["Desktop Score"], errors="coerce") >= 90)])
            k4.metric("Top Performers (90+)", f"{good_pages} / {len(results)}", delta="Passed All")

            st.divider()

            # RESULTS TABLE
            st.write("### 📋 Core Web Vitals Summary Table")
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Mobile Score": st.column_config.ProgressColumn("Mobile Score", format="%d", min_value=0, max_value=100),
                    "Desktop Score": st.column_config.ProgressColumn("Desktop Score", format="%d", min_value=0, max_value=100),
                }
            )

            # VISUAL COMPARISON CHART
            if not valid_mob.empty and not valid_desk.empty:
                st.write("### 📊 Mobile vs Desktop Performance Comparison")
                chart_df = df[["URL", "Mobile Score", "Desktop Score"]].set_index("URL")
                st.bar_chart(chart_df)

            # DOWNLOAD CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Audit Report (CSV)", data=csv, file_name="core_web_vitals_report.csv", mime="text/csv")


# ==================== TAB 2: GOOGLE SHEET SYNC ====================
with tab2:
    st.write("### Sync Audit Results with Google Sheets")
    st.caption("Automatically pulls URLs from Column A of your Google Sheet and updates Columns B through I.")

    c_sname, c_json = st.columns([2, 2])
    with c_sname:
        sheet_name_input = st.text_input("Google Sheet Name or URL", value="BPO Webpage", help="Exact name of your Google Sheet")
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
            st.error("⚠️ PageSpeed API Key missing. Please expand '⚙️ API Keys & Authentication Settings' above.")
        elif gc is None:
            st.error("⚠️ Service Account JSON key is missing. Please upload your `.json` key file above.")
        else:
            try:
                with st.spinner(f"Opening Google Sheet '{sheet_name_input}'..."):
                    sh = gc.open(sheet_name_input)
                    worksheet = sh.sheet1
                    urls = worksheet.col_values(1)[1:]

                st.info(f"Loaded **{len(urls)} URLs** from Google Sheet `{sheet_name_input}`. Starting audit...")

                headers = [
                    "Mobile Score", "Mobile LCP", "Mobile CLS", "Mobile INP / TBT",
                    "Desktop Score", "Desktop LCP", "Desktop CLS", "Desktop INP / TBT"
                ]
                worksheet.update(range_name='B1:I1', values=[headers])

                progress_bar = st.progress(0)
                status_text = st.empty()

                all_results = []
                display_rows = []

                for i, url in enumerate(urls):
                    url_str = url.strip()
                    progress = (i + 1) / len(urls)
                    progress_bar.progress(progress)

                    if not url_str or not url_str.startswith("http"):
                        all_results.append(["", "", "", "", "", "", "", ""])
                        continue

                    status_text.markdown(f"⏳ **Auditing ({i+1}/{len(urls)}):** `{url_str}`")

                    mob = get_metrics(url_str, "mobile", curr_key)
                    time.sleep(1.2)
                    desk = get_metrics(url_str, "desktop", curr_key)
                    time.sleep(1.2)

                    combined = mob + desk
                    all_results.append(combined)
                    display_rows.append([url_str] + combined)

                if all_results:
                    end_row = len(all_results) + 1
                    worksheet.update(range_name=f"B2:I{end_row}", values=all_results)
                    status_text.success(f"🎉 **Success!** Google Sheet `{sheet_name_input}` updated successfully!")

                    df_cols = ["URL"] + headers
                    df_sheet = pd.DataFrame(display_rows, columns=df_cols)
                    st.dataframe(
                        df_sheet,
                        use_container_width=True,
                        column_config={
                            "Mobile Score": st.column_config.ProgressColumn("Mobile Score", format="%d", min_value=0, max_value=100),
                            "Desktop Score": st.column_config.ProgressColumn("Desktop Score", format="%d", min_value=0, max_value=100),
                        }
                    )

                    csv = df_sheet.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Report (CSV)", data=csv, file_name="sheet_audit_report.csv", mime="text/csv")

            except Exception as e:
                st.error(f"❌ Google Sheet Error: {e}")
