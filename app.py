"""
app.py - Dashboard End-of-Line QC & Defect Rate Tracker
PT. Ardiva Clothing (Divisi Busana Muslim)

Aplikasi web untuk pemantauan kualitas akhir lini garmen, perhitungan otomatis
defect rate, dan rekomendasi keputusan operasional shopfloor secara real-time.
"""

from datetime import datetime
import json
import pandas as pd
import streamlit as st
from qc_logic import evaluate_batch

try:
    import requests
except ImportError:
    requests = None


def sync_to_gsheets(webhook_url: str, payload: dict) -> tuple[bool, str]:
    """
    Kirim data ke Google Sheets melalui Apps Script Webhook.
    """
    if not requests:
        return False, "Library requests belum terpasang."
    clean_url = webhook_url.strip() if webhook_url else ""
    if not clean_url or not clean_url.startswith("https://script.google.com"):
        return False, "URL Webhook Google Apps Script tidak valid."

    try:
        resp = requests.post(
            clean_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=12,
        )
        if resp.status_code in [200, 302]:
            return True, "Berhasil disinkronkan ke Google Sheets."
        return False, f"Server Google merespons status: {resp.status_code}"
    except Exception as e:
        return False, f"Gagal terhubung: {str(e)}"


def render_html(html_str: str) -> None:
    """
    Render HTML secara aman di Streamlit tanpa memicu aturan 'Indented Code Block'
    pada Markdown (menghilangkan baris kosong dan spasi indentasi berlebih).
    """
    clean_lines = [line.strip() for line in html_str.splitlines() if line.strip()]
    st.markdown("\n".join(clean_lines), unsafe_allow_html=True)


def generate_qc_table_html(df: pd.DataFrame) -> str:
    """
    Menghasilkan tabel HTML responsif berdesain modern dengan pewarnaan baris,
    status badge, dan indikator visual mutu yang ramah pengguna.
    """
    rows_html = []
    for _, row in df.iterrows():
        status = str(row.get("Status QC", ""))
        line = str(row.get("Lini Produksi", ""))
        batch_code = str(row.get("Kode Batch", ""))
        time_str = str(row.get("Waktu Pengecekan", ""))
        inspected = row.get("Total Periksa (pcs)", 0)
        defects = row.get("Total Cacat (pcs)", 0)
        rate_str = str(row.get("Defect Rate (%)", "0.00%"))
        breakdown = str(row.get("Rincian Cacat (Loncat/Noda/Ukuran)", "0 / 0 / 0"))
        recom = str(row.get("Rekomendasi", ""))

        # Klasifikasi status
        if "LOLOS" in status:
            row_cls = "tw-row-pass"
            status_badge = '<span class="tbl-status-badge status-pass">Lolos QC (PASS)</span>'
            rate_badge = f'<span class="tbl-rate-badge rate-pass">{rate_str}</span>'
            recom_style = "color: #15803D;"
            defect_color = "#059669"
        elif "PERINGATAN" in status:
            row_cls = "tw-row-warn"
            status_badge = '<span class="tbl-status-badge status-warn">Peringatan (WARN)</span>'
            rate_badge = f'<span class="tbl-rate-badge rate-warn">{rate_str}</span>'
            recom_style = "color: #92400E; font-weight: 600;"
            defect_color = "#D97706"
        else:
            row_cls = "tw-row-hold"
            status_badge = '<span class="tbl-status-badge status-hold">Tahan (HOLD)</span>'
            rate_badge = f'<span class="tbl-rate-badge rate-hold">{rate_str}</span>'
            recom_style = "color: #BE123C; font-weight: 700;"
            defect_color = "#E11D48"

        # Klasifikasi badge lini produksi
        if "Line 1" in line:
            line_badge = f'<span class="tbl-line-badge line-gamis">{line}</span>'
        elif "Line 2" in line:
            line_badge = f'<span class="tbl-line-badge line-tunik">{line}</span>'
        elif "Line 3" in line:
            line_badge = f'<span class="tbl-line-badge line-hijab">{line}</span>'
        else:
            line_badge = f'<span class="tbl-line-badge line-mukena">{line}</span>'

        # Defect breakdown formatting
        breakdown_cls = "tbl-breakdown-warn" if defects > 0 else "tbl-breakdown-pill"
        breakdown_badge = f'<span class="{breakdown_cls}">{breakdown}</span>'

        row_html = f"""
        <tr class="{row_cls}">
            <td style="color: #64748B; font-size: 0.75rem;">{time_str}</td>
            <td>{line_badge}</td>
            <td><span class="tbl-batch-code">{batch_code}</span></td>
            <td style="text-align: right; font-weight: 600;">{inspected:,} <span style="font-size: 0.7rem; color: #64748B;">pcs</span></td>
            <td style="text-align: right; font-weight: 700; color: {defect_color};">{defects} <span style="font-size: 0.7rem; color: #64748B;">pcs</span></td>
            <td style="text-align: center;">{rate_badge}</td>
            <td style="text-align: center;">{status_badge}</td>
            <td>{breakdown_badge}</td>
            <td style="font-size: 0.8rem; {recom_style}">{recom}</td>
        </tr>
        """
        rows_html.append(row_html.strip())

    table_body = "\n".join(rows_html)
    return f"""
    <div class="tw-table-wrapper">
        <div class="tw-table-container">
            <table class="tw-qc-table">
                <thead>
                    <tr>
                        <th style="width: 135px;">Waktu</th>
                        <th style="width: 175px;">Lini Produksi</th>
                        <th style="width: 135px;">Kode Batch</th>
                        <th style="width: 95px; text-align: right;">Periksa</th>
                        <th style="width: 85px; text-align: right;">Cacat</th>
                        <th style="width: 110px; text-align: center;">Defect Rate</th>
                        <th style="width: 145px; text-align: center;">Status Mutu</th>
                        <th style="width: 155px;">Rincian (J/N/U)</th>
                        <th style="min-width: 230px;">Rekomendasi Operasional</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body}
                </tbody>
            </table>
        </div>
    </div>
    """


# 1. Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="QC Tracker - PT. Ardiva Clothing",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Injeksi Styling Desain Elegan & Profesional
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet">

    <style>
    /* Global Typography & Font Family */
    html, body, .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stMarkdown, .stText, p, h1, h2, h3, h4, label, input, select, button {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Pastikan icon bawaan Streamlit / Material Symbols tidak tertimpa font teks */
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-symbols-outlined,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapsedControl"] span,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        font-style: normal;
        font-feature-settings: 'liga' 1;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
    }

    /* Styling tombol toggle sidebar saat di-minimize */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 0.5rem !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
    }
    [data-testid="stSidebarCollapsedControl"]:hover {
        background-color: #EFF6FF !important;
        border-color: #BFDBFE !important;
    }

    /* Background & Container Reset */
    .stApp {
        background-color: #F8FAFC !important; /* Tailwind slate-50 */
    }
    
    .block-container {
        padding-top: 1.75rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1380px !important;
    }

    /* Container Card Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 0.875rem !important;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04) !important;
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
    }

    .tw-card {
        background: #FFFFFF;
        border-radius: 0.875rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04);
        padding: 1.25rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 1rem;
    }

    /* Header & Navigation Bar */
    .tw-header-bar {
        background: #FFFFFF;
        border-radius: 1rem;
        border: 1px solid #E2E8F0;
        padding: 1.35rem 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }

    .tw-badge-brand {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        background-color: #F1F5F9;
        color: #334155;
        border: 1px solid #E2E8F0;
        font-size: 0.725rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        width: fit-content;
    }

    .tw-status-dot {
        width: 0.45rem;
        height: 0.45rem;
        border-radius: 9999px;
        background-color: #10B981;
        display: inline-block;
    }

    .tw-title,
    .tw-header-bar h1,
    h1.tw-title,
    [data-testid="stMarkdownContainer"] .tw-title,
    [data-testid="stMarkdownContainer"] h1.tw-title {
        font-size: 1.65rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        -webkit-text-fill-color: #0F172A !important;
        letter-spacing: -0.025em !important;
        line-height: 1.2 !important;
        margin: 0 !important;
    }

    .tw-subtitle,
    [data-testid="stMarkdownContainer"] .tw-subtitle {
        font-size: 0.925rem !important;
        color: #475569 !important;
        -webkit-text-fill-color: #475569 !important;
        margin: 0 !important;
        line-height: 1.4 !important;
    }

    /* KPI Metric Cards (Tremor / Modern Clean Style) */
    .tw-metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1.25rem;
    }

    .tw-metric-box {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 0.875rem !important;
        padding: 1.15rem 1rem !important;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .tw-metric-box:hover {
        box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.08) !important;
    }

    .tw-metric-box.active-blue {
        border-top: 4px solid #2563EB !important;
    }
    .tw-metric-box.active-indigo {
        border-top: 4px solid #4F46E5 !important;
    }
    .tw-metric-box.active-amber {
        border-top: 4px solid #D97706 !important;
    }
    .tw-metric-box.active-emerald {
        border-top: 4px solid #059669 !important;
    }
    .tw-metric-box.active-rose {
        border-top: 4px solid #E11D48 !important;
    }

    .tw-metric-label {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        margin-bottom: 0.2rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    .tw-metric-value {
        font-size: 1.75rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }

    .tw-metric-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        width: fit-content;
        margin-top: 0.35rem;
    }
    .tw-metric-pill.pill-pass {
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .tw-metric-pill.pill-warn {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .tw-metric-pill.pill-hold {
        background-color: #FFF1F2;
        color: #BE123C;
        border: 1px solid #FECDD3;
    }

    /* Gauge / Progress Indicator Bar */
    .tw-gauge-wrapper {
        background: #F1F5F9;
        border-radius: 9999px;
        height: 0.5rem;
        overflow: hidden;
        margin: 0.65rem 0 0.4rem 0;
        display: flex;
        position: relative;
    }
    .tw-gauge-fill {
        height: 100%;
        border-radius: 9999px;
        transition: width 0.4s ease-in-out;
    }

    /* Alert Decision Card */
    .tw-alert-banner {
        border-radius: 0.75rem;
        padding: 1.15rem;
        display: flex;
        gap: 0.875rem;
        align-items: flex-start;
        margin-top: 1rem;
    }
    .tw-alert-pass {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        color: #14532D;
    }
    .tw-alert-warn {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        color: #78350F;
    }
    .tw-alert-hold {
        background-color: #FFF1F2;
        border: 1px solid #FECDD3;
        color: #881337;
    }

    .tw-alert-tag {
        font-size: 0.725rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.2rem 0.55rem;
        border-radius: 0.375rem;
        display: inline-block;
        margin-bottom: 0.35rem;
    }
    .tw-alert-tag.tag-pass {
        background: #DCFCE7;
        color: #15803D;
        border: 1px solid #BBF7D0;
    }
    .tw-alert-tag.tag-warn {
        background: #FEF3C7;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .tw-alert-tag.tag-hold {
        background: #FFE4E6;
        color: #BE123C;
        border: 1px solid #FECDD3;
    }

    .tw-alert-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .tw-alert-desc {
        font-size: 0.875rem;
        line-height: 1.45;
        opacity: 0.95;
    }

    /* Section Headers */
    .tw-section-heading {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.65rem;
    }
    .tw-section-badge {
        font-size: 0.725rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 0.375rem;
        background: #F1F5F9;
        color: #475569;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    div[data-testid="stSidebarUserContent"] {
        padding: 1.25rem 1rem 2rem 1rem !important;
    }

    div[data-testid="stSidebarUserContent"] [data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
    }

    .sb-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 0.75rem;
        padding: 1rem;
        box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
        margin-bottom: 0.875rem;
    }

    .sb-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
    }

    .sb-threshold-item {
        border-radius: 0.5rem;
        padding: 0.65rem 0.75rem;
        margin-bottom: 0.5rem;
        border: 1px solid transparent;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }
    .sb-threshold-item:last-child {
        margin-bottom: 0;
    }

    .sb-item-pass {
        background-color: #F0FDF4;
        border-color: #BBF7D0;
    }
    .sb-item-warn {
        background-color: #FFFBEB;
        border-color: #FDE68A;
    }
    .sb-item-hold {
        background-color: #FFF1F2;
        border-color: #FECDD3;
    }

    .sb-threshold-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 700;
        font-size: 0.825rem;
    }
    .sb-item-pass .sb-threshold-header { color: #166534; }
    .sb-item-warn .sb-threshold-header { color: #92400E; }
    .sb-item-hold .sb-threshold-header { color: #9F1239; }

    .sb-badge-rate {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.1rem 0.45rem;
        border-radius: 9999px;
    }
    .sb-item-pass .sb-badge-rate { background: #DCFCE7; color: #15803D; }
    .sb-item-warn .sb-badge-rate { background: #FEF3C7; color: #B45309; }
    .sb-item-hold .sb-badge-rate { background: #FFE4E6; color: #BE123C; }

    .sb-threshold-sub {
        font-size: 0.75rem;
        line-height: 1.35;
    }
    .sb-item-pass .sb-threshold-sub { color: #15803D; }
    .sb-item-warn .sb-threshold-sub { color: #B45309; }
    .sb-item-hold .sb-threshold-sub { color: #BE123C; }

    .sb-guide-item {
        padding: 0.5rem 0;
        border-bottom: 1px solid #F1F5F9;
    }
    .sb-guide-item:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }
    .sb-guide-name {
        font-size: 0.8rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.15rem;
    }
    .sb-guide-desc {
        font-size: 0.725rem;
        color: #64748B;
        line-height: 1.35;
    }

    /* Streamlit Native Input Polish */
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input {
        border-radius: 0.5rem !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        font-weight: 500 !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stTextInput"] input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }

    /* Streamlit Primary Button */
    div.stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        border: 1px solid #1D4ED8 !important;
        border-radius: 0.5rem !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.25rem !important;
        box-shadow: 0 1px 2px 0 rgba(16, 24, 40, 0.05) !important;
        transition: all 0.15s ease-in-out !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2) !important;
    }
    div.stButton > button[kind="primary"]:active {
        transform: scale(0.99) !important;
    }

    /* Secondary / Preset Buttons */
    div.stButton > button[kind="secondary"] {
        border-radius: 0.5rem !important;
        border: 1px solid #E2E8F0 !important;
        background: #FFFFFF !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.15s ease-in-out !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }

    /* Toast Notification */
    div[data-testid="stToast"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.1) !important;
        border-radius: 0.5rem !important;
    }

    /* KPI Grid & Responsiveness */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin-bottom: 1.25rem;
    }

    @media (max-width: 640px) {
        .tw-metric-container {
            grid-template-columns: repeat(1, minmax(0, 1fr)) !important;
            gap: 0.65rem !important;
        }
        .kpi-grid {
            grid-template-columns: repeat(1, minmax(0, 1fr)) !important;
            gap: 0.65rem !important;
        }
        .tw-header-bar {
            padding: 1rem 1.15rem !important;
        }
        .tw-title {
            font-size: 1.3rem !important;
        }
        .tw-subtitle {
            font-size: 0.8rem !important;
        }
    }

    @media (min-width: 641px) and (max-width: 1024px) {
        .tw-metric-container {
            grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        }
        .kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        }
    }

    /* Modern Table Styling (Color Coded, High Contrast & Friendly) */
    .tw-table-wrapper {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 0.875rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        overflow: hidden;
        margin-bottom: 1rem;
    }

    .tw-table-container {
        overflow-x: auto;
        max-height: 540px;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
    }

    .tw-table-container::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    .tw-table-container::-webkit-scrollbar-track {
        background: #F1F5F9;
    }
    .tw-table-container::-webkit-scrollbar-thumb {
        background: #CBD5E1;
        border-radius: 9999px;
    }
    .tw-table-container::-webkit-scrollbar-thumb:hover {
        background: #94A3B8;
    }

    .tw-qc-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.825rem;
        text-align: left;
        min-width: 960px;
    }

    .tw-qc-table th {
        background-color: #F8FAFC;
        color: #475569;
        font-weight: 700;
        font-size: 0.725rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.85rem 0.9rem;
        border-bottom: 2px solid #E2E8F0;
        position: sticky;
        top: 0;
        z-index: 10;
        white-space: nowrap;
    }

    .tw-qc-table td {
        padding: 0.75rem 0.9rem;
        border-bottom: 1px solid #F1F5F9;
        color: #1E293B;
        vertical-align: middle;
        white-space: nowrap;
        transition: background-color 0.15s ease;
    }

    /* Baris Tabel Berwarna Berdasarkan Status QC */
    .tw-row-pass {
        border-left: 4px solid #10B981 !important;
        background-color: #FFFFFF;
    }
    .tw-row-pass:hover td {
        background-color: #F0FDF4 !important;
    }

    .tw-row-warn {
        border-left: 4px solid #F59E0B !important;
        background-color: #FFFDF5;
    }
    .tw-row-warn td {
        background-color: #FFFDF5;
    }
    .tw-row-warn:hover td {
        background-color: #FEF3C7 !important;
    }

    .tw-row-hold {
        border-left: 4px solid #EF4444 !important;
        background-color: #FFF8F8;
    }
    .tw-row-hold td {
        background-color: #FFF8F8;
    }
    .tw-row-hold:hover td {
        background-color: #FFE4E6 !important;
    }

    /* Line Badges */
    .tbl-line-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.55rem;
        border-radius: 0.375rem;
        font-size: 0.75rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .line-gamis {
        background: #EEF2FF;
        color: #4338CA;
        border: 1px solid #C7D2FE;
    }
    .line-tunik {
        background: #F0F9FF;
        color: #0369A1;
        border: 1px solid #BAE6FD;
    }
    .line-hijab {
        background: #F0FDFA;
        color: #0F766E;
        border: 1px solid #99F6E4;
    }
    .line-mukena {
        background: #FAF5FF;
        color: #7E22CE;
        border: 1px solid #E9D5FF;
    }

    /* Monospace Batch Code */
    .tbl-batch-code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.75rem;
        font-weight: 700;
        background: #F1F5F9;
        color: #0F172A;
        border: 1px solid #CBD5E1;
        padding: 0.18rem 0.45rem;
        border-radius: 0.35rem;
        display: inline-block;
    }

    /* Defect Rate Badges */
    .tbl-rate-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-weight: 800;
        font-size: 0.775rem;
        min-width: 3.75rem;
    }
    .rate-pass {
        background: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .rate-warn {
        background: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .rate-hold {
        background: #FFE4E6;
        color: #BE123C;
        border: 1px solid #FECDD3;
    }

    /* Status QC Badges */
    .tbl-status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.22rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }
    .status-pass {
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .status-warn {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .status-hold {
        background-color: #FFE4E6;
        color: #BE123C;
        border: 1px solid #FECDD3;
    }

    .tbl-breakdown-pill {
        display: inline-flex;
        align-items: center;
        font-size: 0.725rem;
        padding: 0.18rem 0.55rem;
        border-radius: 9999px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        color: #475569;
        font-weight: 500;
    }
    .tbl-breakdown-warn {
        display: inline-flex;
        align-items: center;
        font-size: 0.725rem;
        padding: 0.18rem 0.55rem;
        border-radius: 9999px;
        background: #FEF3C7;
        border: 1px solid #FDE68A;
        color: #92400E;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def get_initial_qc_history():
    """
    Menghasilkan data riwayat inspeksi harian realistis untuk PT. Ardiva Clothing
    (32 batch pemeriksaan seimbang di 4 lini produksi busana muslim).
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_samples = [
        ("17:10:00", "Line 3 - Hijab & Khimar", "BATCH-HJB-0332", 100, 1, 0, 0),
        ("17:02:15", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0431", 120, 1, 1, 0),
        ("16:45:10", "Line 1 - Gamis & Abaya", "BATCH-GMS-0130", 100, 1, 1, 0),
        ("16:22:35", "Line 3 - Hijab & Khimar", "BATCH-HJB-0329", 150, 2, 1, 0),
        ("16:04:12", "Line 2 - Tunik & Blouse", "BATCH-TNK-0228", 100, 3, 1, 0),
        ("15:42:50", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0427", 80, 1, 0, 0),
        ("15:25:15", "Line 1 - Gamis & Abaya", "BATCH-GMS-0126", 120, 2, 1, 0),
        ("15:05:40", "Line 2 - Tunik & Blouse", "BATCH-TNK-0225", 100, 4, 2, 1),
        ("14:48:20", "Line 3 - Hijab & Khimar", "BATCH-HJB-0324", 150, 1, 0, 1),
        ("14:30:10", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0423", 100, 2, 1, 0),
        ("14:12:55", "Line 1 - Gamis & Abaya", "BATCH-GMS-0122", 100, 0, 1, 0),
        ("13:55:30", "Line 2 - Tunik & Blouse", "BATCH-TNK-0221", 100, 2, 2, 0),
        ("13:38:15", "Line 3 - Hijab & Khimar", "BATCH-HJB-0320", 200, 3, 1, 1),
        ("13:15:40", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0419", 100, 1, 1, 0),
        ("12:50:20", "Line 1 - Gamis & Abaya", "BATCH-GMS-0118", 150, 2, 1, 0),
        ("12:25:10", "Line 2 - Tunik & Blouse", "BATCH-TNK-0217", 80, 1, 0, 0),
        ("11:58:45", "Line 3 - Hijab & Khimar", "BATCH-HJB-0316", 100, 4, 1, 1),
        ("11:42:15", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0415", 120, 2, 1, 1),
        ("11:24:30", "Line 1 - Gamis & Abaya", "BATCH-GMS-0114", 100, 1, 0, 0),
        ("11:05:10", "Line 2 - Tunik & Blouse", "BATCH-TNK-0213", 100, 2, 1, 0),
        ("10:48:50", "Line 3 - Hijab & Khimar", "BATCH-HJB-0312", 150, 2, 0, 0),
        ("10:32:15", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0411", 100, 1, 1, 0),
        ("10:15:40", "Line 1 - Gamis & Abaya", "BATCH-GMS-0110", 80, 0, 0, 0),
        ("09:58:25", "Line 2 - Tunik & Blouse", "BATCH-TNK-0209", 100, 3, 1, 0),
        ("09:41:10", "Line 3 - Hijab & Khimar", "BATCH-HJB-0308", 120, 1, 1, 0),
        ("09:22:35", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0407", 100, 2, 0, 0),
        ("09:05:50", "Line 1 - Gamis & Abaya", "BATCH-GMS-0106", 100, 5, 2, 1),
        ("08:50:15", "Line 2 - Tunik & Blouse", "BATCH-TNK-0205", 150, 2, 1, 0),
        ("08:35:40", "Line 3 - Hijab & Khimar", "BATCH-HJB-0304", 100, 1, 1, 0),
        ("08:22:10", "Line 4 - Mukena & Perlengkapan Shalat", "BATCH-MKN-0403", 100, 1, 0, 0),
        ("08:12:30", "Line 1 - Gamis & Abaya", "BATCH-GMS-0102", 120, 2, 1, 0),
        ("08:02:15", "Line 2 - Tunik & Blouse", "BATCH-TNK-0201", 100, 2, 2, 0),
    ]
    history = []
    for time_str, line, code, inspected, skip, stain, size in raw_samples:
        res = evaluate_batch(inspected, skip, stain, size)
        history.append({
            "Waktu Pengecekan": f"{today_str} {time_str}",
            "Lini Produksi": line,
            "Kode Batch": code,
            "Total Periksa (pcs)": res["total_inspected"],
            "Total Cacat (pcs)": res["total_defects"],
            "Defect Rate (%)": f"{res['defect_rate']:.2f}%",
            "Status QC": res["status"],
            "Rincian Cacat (Loncat/Noda/Ukuran)": f"{skip} / {stain} / {size}",
            "Rekomendasi": res["recommendation"],
        })
    return history


# 3. Inisialisasi Session State
if "user_cleared_history" not in st.session_state:
    st.session_state.user_cleared_history = False

if "qc_history" not in st.session_state or (not st.session_state.user_cleared_history and not st.session_state.qc_history):
    st.session_state.qc_history = get_initial_qc_history()

# Inisialisasi URL Google Sheets Webhook
default_webhook = "https://script.google.com/macros/s/AKfycbxAuO7zmm2eUA1urRbpxhfcZ8MwAK3Up6UHlkWWNpeSphnMJtyHP2mNicorUA_R9UhD/exec"
try:
    if "GSHEETS_WEBHOOK_URL" in st.secrets:
        default_webhook = st.secrets["GSHEETS_WEBHOOK_URL"]
except Exception:
    pass

if "gsheets_webhook_url" not in st.session_state:
    st.session_state.gsheets_webhook_url = default_webhook

# State untuk Quick-Fill Presets
if "preset_data" not in st.session_state:
    st.session_state.preset_data = {
        "line": "Line 1 - Gamis & Abaya",
        "code": "BATCH-GMS-001",
        "inspected": 100,
        "skip": 1,
        "stain": 1,
        "size": 0,
    }


def apply_preset(line: str, code: str, inspected: int, skip: int, stain: int, size: int) -> None:
    """Callback untuk mengisi cepat form uji coba."""
    st.session_state.preset_data = {
        "line": line,
        "code": code,
        "inspected": inspected,
        "skip": skip,
        "stain": stain,
        "size": size,
    }


# 4. Sidebar: Standar Toleransi QC & Identitas Pabrik
with st.sidebar:
    # Card 1: Identitas Pabrik & Stasiun
    render_html(
        """
        <div class="sb-card" style="border-top: 3px solid #2563EB;">
            <div style="display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.5rem;">
                <div style="background: #1E293B; color: #FFFFFF; font-weight: 800; width: 2.25rem; height: 2.25rem; border-radius: 0.5rem; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; letter-spacing: 0.05em; flex-shrink: 0;">
                    AC
                </div>
                <div>
                    <div style="font-size: 0.95rem; font-weight: 800; color: #0F172A; line-height: 1.2;">PT. Ardiva Clothing</div>
                    <div style="font-size: 0.725rem; color: #64748B;">Divisi IT Manufaktur (Busana Muslim)</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.725rem; background: #F1F5F9; color: #334155; padding: 0.25rem 0.55rem; border-radius: 9999px; font-weight: 600; width: fit-content; border: 1px solid #E2E8F0;">
                <span class="tw-status-dot"></span>
                <span>Meja Inspeksi Akhir (Line 1 - 4)</span>
            </div>
        </div>
        """
    )

    # Card 2: Standar Batas Toleransi Mutu (AQL)
    render_html(
        """
        <div class="sb-card">
            <div class="sb-title">Ambang Batas Toleransi Mutu (AQL)</div>
            <div class="sb-threshold-item sb-item-pass">
                <div class="sb-threshold-header">
                    <span>Lolos (PASS)</span>
                    <span class="sb-badge-rate">≤ 3.0%</span>
                </div>
                <div class="sb-threshold-sub">Kualitas prima. Lanjut packing & gudang jadi.</div>
            </div>
            <div class="sb-threshold-item sb-item-warn">
                <div class="sb-threshold-header">
                    <span>Peringatan (WARN)</span>
                    <span class="sb-badge-rate">3.1% - 5.0%</span>
                </div>
                <div class="sb-threshold-sub">Karantina batch. Evaluasi & rework pakaian cacat.</div>
            </div>
            <div class="sb-threshold-item sb-item-hold">
                <div class="sb-threshold-header">
                    <span>Tahan (HOLD)</span>
                    <span class="sb-badge-rate">> 5.0%</span>
                </div>
                <div class="sb-threshold-sub">Stop kirim! Investigasi mesin & operator jahit.</div>
            </div>
        </div>
        """
    )

    # Card 3: Kamus Singkat Kategori Cacat
    render_html(
        """
        <div class="sb-card">
            <div class="sb-title">Kategori Cacat Inspeksi</div>
            <div class="sb-guide-item">
                <div class="sb-guide-name">Jahitan Loncat</div>
                <div class="sb-guide-desc">Skip stitch, benang putus, atau kerutan sambungan.</div>
            </div>
            <div class="sb-guide-item">
                <div class="sb-guide-name">Noda Kain / Oli</div>
                <div class="sb-guide-desc">Cipratan oli mesin jahit, debu, atau cacat pewarnaan kain.</div>
            </div>
            <div class="sb-guide-item">
                <div class="sb-guide-name">Ukuran Meleset</div>
                <div class="sb-guide-desc">Dimensi pola di luar batas toleransi size chart.</div>
            </div>
        </div>
        """
    )

    # Card 4: Integrasi Google Spreadsheet (Live Cloud Sync)
    is_connected = bool(
        st.session_state.gsheets_webhook_url
        and st.session_state.gsheets_webhook_url.strip().startswith("https://script.google.com")
    )
    status_label = "Terhubung" if is_connected else "Belum Terhubung"
    status_color = "#047857" if is_connected else "#64748B"
    status_bg = "#ECFDF5" if is_connected else "#F1F5F9"
    status_border = "#A7F3D0" if is_connected else "#E2E8F0"
    dot_color = "#10B981" if is_connected else "#94A3B8"
    card_border = "#10B981" if is_connected else "#2563EB"

    render_html(
        f"""
        <div class="sb-card" style="border-top: 3px solid {card_border};">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <div class="sb-title" style="margin: 0;">Sinkronisasi Google Sheets</div>
                <div style="display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.7rem; font-weight: 700; color: {status_color}; background: {status_bg}; padding: 0.15rem 0.55rem; border-radius: 9999px; border: 1px solid {status_border};">
                    <span style="width: 0.4rem; height: 0.4rem; border-radius: 9999px; background-color: {dot_color}; display: inline-block;"></span>
                    <span>{status_label}</span>
                </div>
            </div>
            <div style="font-size: 0.725rem; color: #64748B; margin-bottom: 0.5rem; line-height: 1.35;">
                Data inspeksi dapat otomatis tersimpan langsung ke Google Spreadsheet online secara real-time.
            </div>
        </div>
        """
    )

    with st.expander("Pengaturan Google Spreadsheet", expanded=not is_connected):
        webhook_input = st.text_input(
            "URL Web App Apps Script:",
            value=st.session_state.gsheets_webhook_url,
            placeholder="https://script.google.com/macros/s/.../exec",
            help="Tempelkan URL Web App dari Google Apps Script Spreadsheet Anda",
            key="input_gsheets_webhook",
        )
        if webhook_input != st.session_state.gsheets_webhook_url:
            st.session_state.gsheets_webhook_url = webhook_input
            st.rerun()

        if is_connected:
            if st.button("Kirim 32 Data ke Spreadsheet", type="secondary", use_container_width=True, help="Kirim seluruh riwayat 32 batch saat ini ke Google Sheets"):
                with st.spinner("Mengirim data ke Google Sheets..."):
                    ok, msg = sync_to_gsheets(
                        st.session_state.gsheets_webhook_url,
                        {"action": "bulk", "rows": st.session_state.qc_history}
                    )
                    if ok:
                        st.toast("Semua data riwayat berhasil dikirim ke Google Sheets!")
                    else:
                        st.error(f"Gagal mengirim: {msg}")



# 5. Top Header Banner
render_html(
    """
    <div class="tw-header-bar">
        <div class="tw-badge-brand">
            <span class="tw-status-dot"></span>
            <span>SHOPFLOOR QUALITY ASSURANCE SYSTEM</span>
        </div>
        <h1 class="tw-title">End-of-Line QC & Defect Rate Tracker</h1>
        <p class="tw-subtitle">
            Sistem otomasi kalkulasi defect rate dan rekomendasi keputusan operasional batch garmen (Busana Muslim).
        </p>
    </div>
    """
)

# 6. Bar Tombol Uji Cepat (Presets)
render_html(
    """
    <div style="font-size: 0.75rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">
        Preset Simulasi Cepat:
    </div>
    """
)

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    if st.button(
        "Batch 1: Lolos (2.0%)",
        use_container_width=True,
        type="secondary",
        help="Simulasi batch gamis dengan 2% cacat (memenuhi standar)",
    ):
        apply_preset("Line 1 - Gamis & Abaya", "BATCH-GMS-001", 100, 1, 1, 0)
        st.rerun()

with col_p2:
    if st.button(
        "Batch 2: Peringatan (4.0%)",
        use_container_width=True,
        type="secondary",
        help="Simulasi batch tunik dengan 4% cacat (perlu rework)",
    ):
        apply_preset("Line 2 - Tunik & Blouse", "BATCH-TNK-002", 100, 2, 2, 0)
        st.rerun()

with col_p3:
    if st.button(
        "Batch 3: Tahan (7.0%)",
        use_container_width=True,
        type="secondary",
        help="Simulasi batch hijab dengan 7% cacat (melebihi ambang batas toleransi)",
    ):
        apply_preset("Line 3 - Hijab & Khimar", "BATCH-HJB-003", 100, 4, 2, 1)
        st.rerun()

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

# 7. Area Kerja Utama: Dua Kolom (Input Form & Real-time Analytics)
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    render_html(
        """
        <div class="tw-section-heading">
            <span>Input Pemeriksaan Batch</span>
            <span class="tw-section-badge">Form Meja QC</span>
        </div>
        """
    )

    with st.container(border=True):
        line_options = [
            "Line 1 - Gamis & Abaya",
            "Line 2 - Tunik & Blouse",
            "Line 3 - Hijab & Khimar",
            "Line 4 - Mukena & Perlengkapan Shalat",
        ]
        default_line_idx = (
            line_options.index(st.session_state.preset_data["line"])
            if st.session_state.preset_data["line"] in line_options
            else 0
        )

        production_line = st.selectbox(
            "Lini Produksi:",
            options=line_options,
            index=default_line_idx,
            help="Pilih lini manufaktur tempat batch pakaian diproduksi",
        )

        batch_code = st.text_input(
            "Kode / Nama Batch:",
            value=st.session_state.preset_data["code"],
            help="Nomor Work Order (WO) atau Surat Perintah Kerja (SPK)",
        )

        total_inspected = st.number_input(
            "Total Pakaian Diperiksa (pcs):",
            min_value=1,
            value=int(st.session_state.preset_data["inspected"]),
            step=1,
            help="Jumlah sampel pakaian yang diambil di meja inspeksi akhir",
        )

        render_html(
            """
            <div style="font-size: 0.85rem; font-weight: 700; color: #334155; margin: 1rem 0 0.5rem 0;">
                Rincian Temuan Cacat (Defects Breakdown):
            </div>
            """
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            skip_stitch = st.number_input(
                "Jahitan Loncat (pcs):",
                min_value=0,
                value=int(st.session_state.preset_data["skip"]),
                step=1,
                help="Skip stitch, benang putus, atau jahitan kerut",
            )
        with c2:
            stain = st.number_input(
                "Noda / Oli (pcs):",
                min_value=0,
                value=int(st.session_state.preset_data["stain"]),
                step=1,
                help="Noda oli mesin jahit, noda debu, atau cacat kain",
            )
        with c3:
            size_mismatch = st.number_input(
                "Ukuran Meleset (pcs):",
                min_value=0,
                value=int(st.session_state.preset_data["size"]),
                step=1,
                help="Ukuran pola di luar batas toleransi spesifikasi",
            )

with col_right:
    render_html(
        """
        <div class="tw-section-heading">
            <span>Hasil Evaluasi Real-Time</span>
            <span class="tw-section-badge">Automated Decision</span>
        </div>
        """
    )

    evaluation_error = None
    batch_result = None

    try:
        batch_result = evaluate_batch(
            total_inspected=int(total_inspected),
            skip_stitch=int(skip_stitch),
            stain=int(stain),
            size_mismatch=int(size_mismatch),
        )
    except ValueError as e:
        evaluation_error = str(e)

    with st.container(border=True):
        if evaluation_error:
            render_html(
                f"""
                <div class="tw-alert-banner tw-alert-hold">
                    <div>
                        <div class="tw-alert-title">Kesalahan Validasi Data</div>
                        <div class="tw-alert-desc">
                            {evaluation_error}<br>
                            Pastikan jumlah total cacat tidak melebihi total pakaian yang diperiksa.
                        </div>
                    </div>
                </div>
                """
            )
        elif batch_result:
            defect_pct = batch_result["defect_rate"]
            status_color = batch_result["color"]

            if status_color == "green":
                box_class = "active-emerald"
                pill_class = "pill-pass"
                pill_text = "Lolos (≤ 3.0%)"
                alert_class = "tw-alert-pass"
                tag_class = "tag-pass"
                tag_text = "STATUS: PASS"
                bar_color = "#059669"
            elif status_color == "orange":
                box_class = "active-amber"
                pill_class = "pill-warn"
                pill_text = "Peringatan (3.1% - 5.0%)"
                alert_class = "tw-alert-warn"
                tag_class = "tag-warn"
                tag_text = "STATUS: WARNING"
                bar_color = "#D97706"
            else:
                box_class = "active-rose"
                pill_class = "pill-hold"
                pill_text = "Tahan (> 5.0%)"
                alert_class = "tw-alert-hold"
                tag_class = "tag-hold"
                tag_text = "STATUS: HOLD"
                bar_color = "#E11D48"

            # 3 Tremor Metric Cards
            render_html(
                f"""
                <div class="tw-metric-container">
                    <div class="tw-metric-box active-blue">
                        <span class="tw-metric-label">Pakaian Diperiksa</span>
                        <span class="tw-metric-value">{batch_result['total_inspected']:,} <span style="font-size: 0.85rem; font-weight: 500; color: #64748B;">pcs</span></span>
                        <span class="tw-metric-pill" style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1;">Sampel Inspeksi</span>
                    </div>
                    <div class="tw-metric-box active-amber">
                        <span class="tw-metric-label">Total Cacat</span>
                        <span class="tw-metric-value">{batch_result['total_defects']:,} <span style="font-size: 0.85rem; font-weight: 500; color: #64748B;">pcs</span></span>
                        <span class="tw-metric-pill" style="background:#FEF3C7; color:#92400E; border:1px solid #FDE68A;">
                            {skip_stitch} loncat / {stain} noda / {size_mismatch} ukuran
                        </span>
                    </div>
                    <div class="tw-metric-box {box_class}">
                        <span class="tw-metric-label">Defect Rate</span>
                        <span class="tw-metric-value">{defect_pct:.2f}%</span>
                        <span class="tw-metric-pill {pill_class}">{pill_text}</span>
                    </div>
                </div>
                """
            )

            # Defect Rate Meter / Visual Gauge Bar
            normalized_pct = min(max(defect_pct, 0.0), 10.0)
            fill_width = (normalized_pct / 10.0) * 100

            render_html(
                f"""
                <div style="margin: 0.5rem 0 1rem 0;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.725rem; font-weight: 600; color: #64748B;">
                        <span>0% (Sempurna)</span>
                        <span style="color: #059669;">3.0% (Batas Aman)</span>
                        <span style="color: #D97706;">5.0% (Toleransi Maks)</span>
                        <span style="color: #E11D48;">10%+ (Kritis)</span>
                    </div>
                    <div class="tw-gauge-wrapper">
                        <div class="tw-gauge-fill" style="width: {fill_width}%; background-color: {bar_color};"></div>
                    </div>
                </div>
                """
            )

            # Alert Banner & Recommendation
            render_html(
                f"""
                <div class="tw-alert-banner {alert_class}">
                    <div style="flex: 1;">
                        <span class="tw-alert-tag {tag_class}">{tag_text}</span>
                        <div class="tw-alert-title">{batch_result['status']}</div>
                        <div class="tw-alert-desc">
                            <strong>Rekomendasi Operasional:</strong> {batch_result['recommendation']}
                        </div>
                    </div>
                </div>
                """
            )

            st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

            # Tombol Simpan ke Riwayat
            if st.button(
                "Simpan ke Riwayat Pemeriksaan",
                type="primary",
                use_container_width=True,
                help="Catat hasil evaluasi batch ini ke tabel rekap harian pabrik",
            ):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_entry = {
                    "Waktu Pengecekan": now_str,
                    "Lini Produksi": production_line,
                    "Kode Batch": batch_code,
                    "Total Periksa (pcs)": batch_result["total_inspected"],
                    "Total Cacat (pcs)": batch_result["total_defects"],
                    "Defect Rate (%)": f"{batch_result['defect_rate']:.2f}%",
                    "Status QC": batch_result["status"],
                    "Rincian Cacat (Loncat/Noda/Ukuran)": f"{skip_stitch} / {stain} / {size_mismatch}",
                    "Rekomendasi": batch_result["recommendation"],
                }
                st.session_state.qc_history.insert(0, new_entry)

                # Sinkronisasi otomatis ke Google Sheets jika terhubung
                if st.session_state.get("gsheets_webhook_url"):
                    ok, msg = sync_to_gsheets(
                        st.session_state.gsheets_webhook_url,
                        {"action": "append", "data": new_entry}
                    )
                    if ok:
                        st.toast(f"Batch {batch_code} tersimpan ke Riwayat & Google Sheets!")
                    else:
                        st.toast(f"Tersimpan di riwayat (Gagal sync Google Sheets: {msg})")
                else:
                    st.toast(f"Batch {batch_code} berhasil disimpan ke riwayat.")

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

# 8. Bagian Bawah: Rekapitulasi Riwayat Pemeriksaan
render_html(
    """
    <div class="tw-section-heading">
        <span>Rekapitulasi Riwayat Pemeriksaan</span>
        <span class="tw-section-badge">Daily Log Summary</span>
    </div>
    """
)

if st.session_state.qc_history:
    df_history = pd.DataFrame(st.session_state.qc_history)

    # 1. Ringkasan KPI Riwayat (Tremor Style dengan Top Colored Borders & Badge Pills)
    total_batch_count = len(df_history)
    total_inspected_sum = df_history["Total Periksa (pcs)"].sum()
    total_defects_sum = df_history["Total Cacat (pcs)"].sum()
    pass_count = sum(1 for s in df_history["Status QC"] if "LOLOS" in str(s))
    pass_ratio = (pass_count / total_batch_count) * 100 if total_batch_count > 0 else 0.0

    render_html(
        f"""
        <div class="kpi-grid">
            <div class="tw-metric-box active-blue">
                <span class="tw-metric-label">TOTAL BATCH TERCATAT</span>
                <span class="tw-metric-value">{total_batch_count} <span style="font-size: 0.85rem; font-weight: 500; color: #64748B;">batch</span></span>
                <span class="tw-metric-pill" style="background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;">Log Operasional</span>
            </div>
            <div class="tw-metric-box active-indigo">
                <span class="tw-metric-label">TOTAL GARMENT DIPERIKSA</span>
                <span class="tw-metric-value">{total_inspected_sum:,} <span style="font-size: 0.85rem; font-weight: 500; color: #64748B;">pcs</span></span>
                <span class="tw-metric-pill" style="background:#EEF2FF; color:#4338CA; border:1px solid #C7D2FE;">Akumulasi 4 Lini</span>
            </div>
            <div class="tw-metric-box active-rose">
                <span class="tw-metric-label">TOTAL DEFECT TERDETEKSI</span>
                <span class="tw-metric-value" style="color: #E11D48;">{total_defects_sum:,} <span style="font-size: 0.85rem; font-weight: 500; color: #64748B;">pcs</span></span>
                <span class="tw-metric-pill pill-hold">{total_defects_sum} pcs Perlu Rework</span>
            </div>
            <div class="tw-metric-box active-emerald">
                <span class="tw-metric-label">TINGKAT KELULUSAN (PASS)</span>
                <span class="tw-metric-value" style="color: #059669;">{pass_ratio:.1f}% <span style="font-size: 0.85rem; font-weight: 500; color: #64748B;">({pass_count}/{total_batch_count})</span></span>
                <span class="tw-metric-pill pill-pass">Target Mutu ≥ 70%</span>
            </div>
        </div>
        """
    )

    # 2. Filter & Pencarian Cepat (Friendly UX agar User Tidak Pusing)
    render_html(
        """
        <div style="font-size: 0.725rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;">
            Filter & Navigasi Cepat Tabel:
        </div>
        """
    )
    col_f1, col_f2, col_f3 = st.columns([1.5, 1.3, 1.4], gap="medium")
    with col_f1:
        filter_line = st.selectbox(
            "Filter Lini Produksi:",
            [
                "Semua Lini Produksi (32 Batch)",
                "Line 1 - Gamis & Abaya",
                "Line 2 - Tunik & Blouse",
                "Line 3 - Hijab & Khimar",
                "Line 4 - Mukena & Perlengkapan Shalat",
            ],
            index=0,
            key="sb_filter_line",
        )
    with col_f2:
        filter_status = st.selectbox(
            "Filter Status Mutu:",
            [
                "Semua Status QC",
                "LOLOS QC (PASS)",
                "PERINGATAN (WARNING)",
                "TAHAN BATCH (HOLD / REJECT)",
            ],
            index=0,
            key="sb_filter_status",
        )
    with col_f3:
        search_kw = st.text_input(
            "Cari Batch / Keyword:",
            placeholder="Ketik BATCH-GMS, noda, rework...",
            key="ti_search_kw",
        )

    # Filter DataFrame
    df_filtered = df_history.copy()
    if filter_line != "Semua Lini Produksi (32 Batch)":
        df_filtered = df_filtered[df_filtered["Lini Produksi"] == filter_line]
    if filter_status != "Semua Status QC":
        df_filtered = df_filtered[df_filtered["Status QC"] == filter_status]
    if search_kw.strip():
        kw = search_kw.strip().lower()
        mask = (
            df_filtered["Kode Batch"].str.lower().str.contains(kw)
            | df_filtered["Rekomendasi"].str.lower().str.contains(kw)
            | df_filtered["Lini Produksi"].str.lower().str.contains(kw)
            | df_filtered["Waktu Pengecekan"].str.lower().str.contains(kw)
        )
        df_filtered = df_filtered[mask]

    is_filtered = (
        (filter_line != "Semua Lini Produksi (32 Batch)")
        or (filter_status != "Semua Status QC")
        or bool(search_kw.strip())
    )
    filter_hint = (
        f"Menampilkan <strong>{len(df_filtered)}</strong> dari <strong>{len(df_history)}</strong> batch pemeriksaan"
        + (" <em>(Filter Aktif)</em>" if is_filtered else "")
    )

    render_html(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin: 0.5rem 0 0.75rem 0; font-size: 0.8rem; color: #475569; flex-wrap: wrap; gap: 0.5rem;">
            <div>{filter_hint}</div>
            <div style="font-size: 0.725rem; color: #64748B;">
                Indikator Baris: <span style="color:#059669; font-weight:700;">Hijau</span> = Lolos &nbsp;|&nbsp; <span style="color:#D97706; font-weight:700;">Kuning</span> = Peringatan &nbsp;|&nbsp; <span style="color:#E11D48; font-weight:700;">Merah</span> = Tahan Batch
            </div>
        </div>
        """
    )

    # 3. Tampilan Tabel: Tab Berwarna (Visual) & Tab Spreadsheet
    tab_visual, tab_grid = st.tabs([
        "Tampilan Berwarna (Visual Friendly)",
        "Tampilan Spreadsheet (Grid Data)",
    ])

    with tab_visual:
        if not df_filtered.empty:
            render_html(generate_qc_table_html(df_filtered))
        else:
            render_html(
                """
                <div class="tw-card" style="text-align: center; padding: 2rem 1rem; color: #64748B;">
                    Tidak ada batch pemeriksaan yang cocok dengan filter yang dipilih.
                </div>
                """
            )

    with tab_grid:
        if not df_filtered.empty:
            st.dataframe(
                df_filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Waktu Pengecekan": st.column_config.TextColumn("Waktu", width="small"),
                    "Lini Produksi": st.column_config.TextColumn("Lini Produksi", width="medium"),
                    "Kode Batch": st.column_config.TextColumn("Kode Batch", width="small"),
                    "Total Periksa (pcs)": st.column_config.NumberColumn("Periksa", format="%d pcs", width="small"),
                    "Total Cacat (pcs)": st.column_config.NumberColumn("Cacat", format="%d pcs", width="small"),
                    "Defect Rate (%)": st.column_config.TextColumn("Defect Rate", width="small"),
                    "Status QC": st.column_config.TextColumn("Status Mutu", width="medium"),
                    "Rincian Cacat (Loncat/Noda/Ukuran)": st.column_config.TextColumn("Rincian Cacat", width="medium"),
                    "Rekomendasi": st.column_config.TextColumn("Rekomendasi Operasional", width="large"),
                },
            )
        else:
            st.info("Tidak ada batch pemeriksaan yang cocok dengan filter yang dipilih.")

    # 4. Bar Tombol Ekspor, Muat Ulang Sampel & Reset
    col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.5, 1.2])
    with col_btn1:
        csv_data = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"Unduh Rekap CSV ({len(df_filtered)} Baris)",
            data=csv_data,
            file_name=f"Rekap_QC_ArdivaClothing_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download data riwayat yang sedang tampil ke format spreadsheet CSV",
        )
    with col_btn2:
        if st.button(
            "Muat Ulang Sampel (32 Batch)",
            type="secondary",
            use_container_width=True,
            help="Kembalikan riwayat ke 32 data sampel simulasi pabrik",
        ):
            st.session_state.user_cleared_history = False
            st.session_state.qc_history = get_initial_qc_history()
            st.rerun()
    with col_btn3:
        if st.button(
            "Reset Riwayat",
            type="secondary",
            use_container_width=True,
            help="Kosongkan seluruh riwayat pemeriksaan",
        ):
            st.session_state.user_cleared_history = True
            st.session_state.qc_history = []
            st.rerun()

else:
    render_html(
        """
        <div class="tw-card" style="text-align: center; padding: 2.25rem 1.5rem 1.75rem 1.5rem;">
            <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin-bottom: 0.35rem;">
                Belum Ada Riwayat Pemeriksaan Hari Ini
            </div>
            <div style="font-size: 0.85rem; color: #64748B; max-width: 520px; margin: 0 auto 1.25rem auto; line-height: 1.5;">
                Tabel rekapitulasi sedang kosong. Anda dapat menginput batch baru melalui form meja QC di atas, atau klik tombol di bawah untuk memuat 32 data sampel pemeriksaan operasional.
            </div>
        </div>
        """
    )
    col_empty_left, col_empty_mid, col_empty_right = st.columns([1, 1.2, 1])
    with col_empty_mid:
        if st.button("Muat Data Sampel (32 Batch)", type="primary", use_container_width=True):
            st.session_state.user_cleared_history = False
            st.session_state.qc_history = get_initial_qc_history()
            st.rerun()
