# ⚡ Core Web Vitals Dual-Audit Streamlit App

A password-protected Streamlit web application to audit Core Web Vitals (Mobile + Desktop) via Google PageSpeed Insights API and sync results directly back to Google Sheets.

---

## 🛠️ How to Test Locally

1. Open your terminal in this directory:
   ```bash
   cd C:\Users\Admin\.gemini\antigravity\scratch\core-web-vitals-streamlit
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

4. The app will open in your browser at `http://localhost:8501`.
   * **Default Password:** `Damco2026!`

---

## 🚀 How to Deploy on Streamlit Cloud

1. Create a GitHub repository and push `app.py` and `requirements.txt`.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
3. Click **"New app"** and select your GitHub repository.
4. Set the main file path as `app.py` and choose your desired domain name (e.g. `core-web-vital-score.streamlit.app`).
5. Open **Settings > Secrets** in Streamlit Cloud and paste your secrets following `.streamlit/secrets.toml.template`.
6. Click **Deploy**! Your app will be live and password-protected.
