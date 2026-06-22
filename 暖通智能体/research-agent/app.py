import html

from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ranker import rank_results
from search_engine import read_result_pages, search_web
from summarizer import build_summary


PAGE_TITLE = "\u7a7a\u8c03\u5efa\u7b51\u8282\u80fd\u7814\u7a76\u578b\u641c\u7d22\u667a\u80fd\u4f53"


def render_progress(slot, percent, title, detail=""):
    percent = max(0, min(100, int(round(percent))))
    safe_title = html.escape(title)
    safe_detail = html.escape(detail)
    detail_html = f'<div class="progress-detail">{safe_detail}</div>' if safe_detail else ""
    slot.markdown(
        f"""
        <div class="progress-panel">
            <div class="loading-row compact">
                <div class="loading-spinner"></div>
                <div>
                    <div class="progress-title">{safe_title}</div>
                    {detail_html}
                </div>
                <div class="progress-percent">{percent}%</div>
            </div>
            <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{percent}">
                <div class="progress-fill" style="width: {percent}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_style():
    st.markdown(
        """
        <style>
        :root {
            --ink: #0f172a;
            --muted: #64748b;
            --blue-900: #0b2a5b;
            --blue-700: #1d4ed8;
            --blue-500: #3b82f6;
            --blue-300: #93c5fd;
            --blue-100: #dbeafe;
            --glass: rgba(219, 234, 254, 0.58);
            --glass-strong: rgba(191, 219, 254, 0.72);
            --white-glass: rgba(255, 255, 255, 0.74);
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 8%, rgba(59, 130, 246, 0.22), transparent 30%),
                radial-gradient(circle at 78% 2%, rgba(14, 165, 233, 0.18), transparent 30%),
                linear-gradient(135deg, #f8fbff 0%, #eef6ff 44%, #f9fbff 100%);
            color: var(--ink);
            overflow-anchor: none;
        }

        html,
        body,
        .main,
        .block-container,
        div[data-testid="stAppViewContainer"],
        section[data-testid="stMain"] {
            overflow-anchor: none !important;
        }

        .block-container {
            max-width: 1120px;
            padding-top: 2.6rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            display: none;
        }

        .hero {
            text-align: center;
            padding: 2.2rem 1rem 0.8rem;
        }

        .hero-kicker {
            display: inline-block;
            padding: 0.38rem 0.78rem;
            border-radius: 999px;
            background: rgba(219, 234, 254, 0.7);
            color: #1e40af;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            box-shadow: 0 10px 30px rgba(37, 99, 235, 0.12);
        }

        .hero-title {
            margin: 1rem 0 0.5rem;
            font-size: clamp(2.15rem, 5vw, 4rem);
            line-height: 1.05;
            font-weight: 850;
            color: var(--blue-900);
        }

        .hero-subtitle {
            max-width: 760px;
            margin: 0 auto;
            color: var(--muted);
            font-size: 1.04rem;
            line-height: 1.8;
        }

        .glass-panel {
            border-radius: 22px;
            border: 1px solid rgba(147, 197, 253, 0.62);
            background:
                linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(219, 234, 254, 0.55)),
                linear-gradient(90deg, rgba(59, 130, 246, 0.16), rgba(125, 211, 252, 0.12));
            box-shadow:
                0 22px 55px rgba(30, 64, 175, 0.18),
                inset 0 1px 0 rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            padding: 1.25rem;
            margin: 1.1rem 0;
        }

        .search-shell {
            max-width: 850px;
            margin: 1.2rem auto 2rem;
        }

        div[data-testid="stForm"] {
            width: min(860px, calc(100vw - 3rem));
            max-width: 860px;
            margin: 1.6rem auto 2rem;
            border-radius: 22px;
            border: 1px solid rgba(147, 197, 253, 0.62);
            background:
                linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(219, 234, 254, 0.55)),
                linear-gradient(90deg, rgba(59, 130, 246, 0.16), rgba(125, 211, 252, 0.12));
            box-shadow:
                0 22px 55px rgba(30, 64, 175, 0.18),
                inset 0 1px 0 rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            padding: 1.25rem 1.35rem 1.35rem;
        }

        div[data-testid="stForm"] > div {
            width: 100%;
        }

        div[data-testid="stForm"] .stTextInput,
        div[data-testid="stForm"] .stNumberInput {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            min-width: 0;
        }

        div[data-testid="stForm"] .stTextInput > label,
        div[data-testid="stForm"] .stNumberInput > label {
            flex: 0 0 auto;
            margin: 0 !important;
            color: #1e3a8a !important;
            font-weight: 850 !important;
            white-space: nowrap;
        }

        div[data-testid="stForm"] .stNumberInput > label {
            width: 118px !important;
        }

        div[data-testid="stForm"] .stTextInput input,
        div[data-testid="stForm"] .stNumberInput input {
            min-height: 44px;
            border-radius: 12px !important;
            border: 1px solid rgba(147, 197, 253, 0.85) !important;
            background: #ffffff !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95);
            font-size: 0.98rem !important;
            color: #0f172a !important;
        }

        div[data-testid="stForm"] .stTextInput div[data-baseweb="input"] {
            border-radius: 12px !important;
            border-color: rgba(147, 197, 253, 0.85) !important;
            background: #ffffff !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
        }

        div[data-testid="stForm"] .stTextInput div[data-baseweb="input"]:focus,
        div[data-testid="stForm"] .stTextInput div[data-baseweb="input"]:focus-visible,
        div[data-testid="stForm"] .stTextInput div[data-baseweb="input"]:focus-within {
            outline: none !important;
            border-color: #93c5fd !important;
            box-shadow:
                inset 0 0 0 2px rgba(147, 197, 253, 0.72),
                inset 0 0 18px 5px rgba(191, 219, 254, 0.38),
                inset 0 12px 30px rgba(147, 197, 253, 0.18),
                inset 0 -1px 0 rgba(255, 255, 255, 0.95) !important;
            background:
                linear-gradient(#ffffff, #ffffff) padding-box,
                linear-gradient(135deg, #bfdbfe, #a5f3fc) border-box !important;
        }

        div[data-testid="stForm"] .stTextInput div[data-baseweb="input"][aria-invalid="true"],
        div[data-testid="stForm"] input[aria-invalid="true"],
        div[data-testid="stForm"] input:invalid {
            border-color: #93c5fd !important;
            outline: none !important;
            box-shadow:
                inset 0 0 0 2px rgba(147, 197, 253, 0.68),
                inset 0 0 18px 5px rgba(191, 219, 254, 0.34),
                inset 0 12px 30px rgba(147, 197, 253, 0.15) !important;
        }

        div[data-testid="stForm"] .stTextInput input:focus,
        div[data-testid="stForm"] .stNumberInput input:focus,
        div[data-testid="stForm"] .stTextInput input:focus-visible,
        div[data-testid="stForm"] .stNumberInput input:focus-visible {
            outline: none !important;
            border-color: #93c5fd !important;
            background: #ffffff !important;
            box-shadow:
                inset 0 0 0 2px rgba(147, 197, 253, 0.7),
                inset 0 0 18px 5px rgba(191, 219, 254, 0.36),
                inset 0 12px 30px rgba(147, 197, 253, 0.16),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
        }

        div[data-testid="stForm"] .stNumberInput input:focus,
        div[data-testid="stForm"] .stNumberInput input:focus-visible {
            box-shadow:
                inset 0 0 0 2px rgba(147, 197, 253, 0.62),
                inset 0 0 18px 5px rgba(219, 234, 254, 0.42),
                inset 0 10px 24px rgba(147, 197, 253, 0.14) !important;
        }

        div[data-testid="stForm"] .stTextInput input:active,
        div[data-testid="stForm"] .stNumberInput input:active {
            outline: none !important;
            border-color: #93c5fd !important;
        }

        div[data-testid="stForm"] *:focus,
        div[data-testid="stForm"] *:focus-visible {
            outline-color: transparent !important;
            outline-style: none !important;
        }

        div[data-testid="stForm"] * {
            --borderFocus: #93c5fd !important;
            --inputBorderFocus: #93c5fd !important;
        }

        div[data-testid="stForm"] .stTextInput input {
            width: 100% !important;
            min-width: 0 !important;
        }

        div[data-testid="stForm"] .stNumberInput input {
            width: 120px !important;
            min-width: 120px !important;
            max-width: 120px !important;
            text-align: center;
            border-radius: 12px !important;
            border: 1px solid rgba(147, 197, 253, 0.85) !important;
        }

        div[data-testid="stForm"] .stNumberInput > div {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
            height: auto !important;
            display: flex !important;
            align-items: center !important;
            overflow: visible !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stForm"] .stNumberInput > div:focus,
        div[data-testid="stForm"] .stNumberInput > div:focus-visible,
        div[data-testid="stForm"] .stNumberInput > div:focus-within {
            outline: none !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stForm"] .stNumberInput div[data-baseweb="input"] {
            width: 120px !important;
            min-width: 120px !important;
            max-width: 120px !important;
            border-radius: 12px !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stForm"] .stNumberInput div[data-baseweb="input"]:focus-within {
            outline: none !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stForm"] .stNumberInput button {
            width: 46px !important;
            min-width: 46px !important;
            height: 44px !important;
            border-radius: 0 !important;
            background: #ffffff !important;
            border: 1px solid rgba(147, 197, 253, 0.65) !important;
            color: #1e3a8a !important;
            box-shadow: none !important;
        }

        div[data-testid="stForm"] .stNumberInput button:nth-of-type(1) {
            margin-left: 8px !important;
            border-radius: 12px 0 0 12px !important;
            border-right: 1px solid rgba(147, 197, 253, 0.65) !important;
        }

        div[data-testid="stForm"] .stNumberInput button:last-child {
            border-radius: 0 12px 12px 0 !important;
            border-left: 0 !important;
        }

        div[data-testid="stForm"] .stNumberInput button:focus,
        div[data-testid="stForm"] .stNumberInput button:focus-visible,
        div[data-testid="stForm"] .stNumberInput button:hover {
            outline: none !important;
            background: linear-gradient(135deg, #eff6ff, #ffffff) !important;
            box-shadow: inset 0 0 12px rgba(191, 219, 254, 0.36) !important;
            color: #1d4ed8 !important;
        }

        div[data-testid="stForm"] input::placeholder {
            color: #a0aec0 !important;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            align-items: center;
            gap: 1.1rem;
            margin-bottom: 0.7rem;
        }

        .start-hint {
            position: fixed;
            left: 50%;
            bottom: 2.8rem;
            transform: translateX(-50%);
            width: min(720px, calc(100vw - 3rem));
            text-align: center;
            color: #475569;
            font-size: 1rem;
            margin: 0;
            z-index: 2;
        }

        div.stButton > button:first-child {
            width: 100%;
            min-height: 42px;
            border-radius: 999px;
            border: 0;
            background: linear-gradient(135deg, #2563eb, #06b6d4);
            color: white;
            font-weight: 800;
            box-shadow: 0 14px 34px rgba(37, 99, 235, 0.28);
        }

        div.stButton > button:first-child:hover {
            background: linear-gradient(135deg, #1d4ed8, #0891b2);
            color: white;
            transform: translateY(-1px);
        }

        div.stButton > button:first-child:active,
        div.stButton > button:first-child:focus,
        div.stButton > button:first-child:focus-visible {
            background: linear-gradient(135deg, #2563eb, #06b6d4) !important;
            color: #ffffff !important;
            outline: none !important;
            box-shadow:
                inset 0 0 16px rgba(191, 219, 254, 0.22),
                0 14px 34px rgba(37, 99, 235, 0.24) !important;
        }

        div.stButton > button:first-child * {
            color: #ffffff !important;
        }

        .loading-row {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.9rem;
            margin: 3.2rem auto 0;
            color: #0f172a;
            font-size: 1.08rem;
            font-weight: 650;
            text-align: center;
        }

        .loading-spinner {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            border: 4px solid rgba(148, 163, 184, 0.28);
            border-top-color: #38a5f8;
            animation: spin 0.9s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .progress-panel {
            width: min(760px, 100%);
            margin: 3rem auto 0;
            padding: 1rem 1.1rem 1.15rem;
            border-radius: 8px;
            border: 1px solid rgba(147, 197, 253, 0.68);
            background: rgba(255, 255, 255, 0.78);
            box-shadow: 0 16px 38px rgba(30, 64, 175, 0.14);
        }

        .loading-row.compact {
            justify-content: flex-start;
            margin: 0 0 0.85rem;
            text-align: left;
        }

        .loading-row.compact .loading-spinner {
            width: 30px;
            height: 30px;
            border-width: 3px;
            flex: 0 0 auto;
        }

        .progress-title {
            color: #0f172a;
            font-size: 1.02rem;
            font-weight: 800;
            line-height: 1.35;
        }

        .progress-detail {
            margin-top: 0.2rem;
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.45;
        }

        .progress-percent {
            margin-left: auto;
            color: #1d4ed8;
            font-size: 1rem;
            font-weight: 850;
            white-space: nowrap;
        }

        .progress-track {
            width: 100%;
            height: 12px;
            overflow: hidden;
            border-radius: 999px;
            background: #dbeafe;
            box-shadow: inset 0 1px 2px rgba(30, 64, 175, 0.12);
        }

        .progress-fill {
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #2563eb, #38a5f8);
            transition: width 0.22s ease;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 1rem 0 1.4rem;
        }

        .metric-card {
            border-radius: 18px;
            padding: 1rem;
            background: linear-gradient(145deg, rgba(219, 234, 254, 0.86), rgba(239, 246, 255, 0.6));
            border: 1px solid rgba(147, 197, 253, 0.72);
            box-shadow: 0 16px 36px rgba(30, 64, 175, 0.14);
        }

        .metric-label {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .metric-value {
            margin-top: 0.35rem;
            color: #0b2a5b;
            font-size: 1.25rem;
            font-weight: 850;
            word-break: break-word;
        }

        .section-title {
            margin: 2rem 0 0.9rem;
            color: #0b2a5b;
            font-size: 1.35rem;
            font-weight: 850;
        }

        .report-title {
            font-size: 1.75rem;
            line-height: 1.25;
        }

        div[data-testid="metric-container"] {
            border-radius: 18px;
            padding: 1rem;
            background: linear-gradient(145deg, rgba(219, 234, 254, 0.86), rgba(239, 246, 255, 0.6));
            border: 1px solid rgba(147, 197, 253, 0.72);
            box-shadow: 0 16px 36px rgba(30, 64, 175, 0.14);
        }

        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.28rem !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        div[data-testid="metric-container"] [data-testid="stMetricLabel"] {
            font-size: 0.86rem !important;
            color: #475569 !important;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(147, 197, 253, 0.65);
            box-shadow: 0 16px 36px rgba(30, 64, 175, 0.12);
        }

        .debug-table-compact {
            width: 100%;
            table-layout: fixed;
            border-collapse: separate;
            border-spacing: 0 0.42rem;
            font-size: 0.82rem;
        }

        .debug-table-compact th {
            text-align: left;
            color: #1e40af;
            padding: 0.48rem 0.55rem;
            font-weight: 850;
        }

        .debug-table-compact td {
            padding: 0.58rem 0.55rem;
            background: rgba(239, 246, 255, 0.82);
            border-top: 1px solid rgba(147, 197, 253, 0.45);
            border-bottom: 1px solid rgba(147, 197, 253, 0.45);
            color: #1f2937;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .debug-table-compact td:first-child {
            border-left: 1px solid rgba(147, 197, 253, 0.45);
            border-radius: 12px 0 0 12px;
            text-align: center;
            color: #1e3a8a;
            font-weight: 850;
            background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        }

        .debug-table-compact td:last-child {
            border-right: 1px solid rgba(147, 197, 253, 0.45);
            border-radius: 0 12px 12px 0;
        }

        .debug-table-compact .col-rank { width: 7%; }
        .debug-table-compact .col-title { width: 36%; }
        .debug-table-compact .col-hit { width: 22%; }
        .debug-table-compact .col-score { width: 8%; }
        .debug-table-compact .col-domain { width: 13%; }
        .debug-table-compact .col-read { width: 14%; }

        .report-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
        }

        .report-card, .result-card {
            border-radius: 20px;
            padding: 1.08rem 1.15rem;
            background:
                linear-gradient(145deg, rgba(219, 234, 254, 0.82), rgba(240, 249, 255, 0.58));
            border: 1px solid rgba(96, 165, 250, 0.65);
            box-shadow:
                0 18px 45px rgba(37, 99, 235, 0.16),
                inset 0 1px 0 rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }

        .report-card.wide {
            grid-column: 1 / -1;
        }

        .report-card h3 {
            margin: 0 0 0.65rem;
            color: #1d4ed8;
            font-size: 1.04rem;
            font-weight: 850;
        }

        .report-card p, .report-card li {
            color: #1f2937;
            line-height: 1.75;
            font-size: 0.98rem;
        }

        .result-card {
            margin-bottom: 0.85rem;
            background: linear-gradient(145deg, rgba(239, 246, 255, 0.86), rgba(219, 234, 254, 0.62));
        }

        .result-title {
            color: #1d4ed8;
            font-size: 1.05rem;
            font-weight: 850;
            text-decoration: none;
        }

        .result-url {
            margin: 0.35rem 0;
            color: #0f766e;
            font-size: 0.86rem;
            word-break: break-all;
        }

        .result-snippet {
            color: #334155;
            line-height: 1.72;
            font-size: 0.96rem;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.75rem;
        }

        .pill {
            border-radius: 999px;
            padding: 0.26rem 0.62rem;
            background: rgba(255, 255, 255, 0.7);
            color: #1e40af;
            border: 1px solid rgba(147, 197, 253, 0.7);
            font-size: 0.78rem;
            font-weight: 700;
        }

        .debug-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 0.55rem;
        }

        .debug-table th {
            color: #1e40af;
            text-align: left;
            font-size: 0.82rem;
            padding: 0.55rem 0.7rem;
        }

        .debug-table td {
            padding: 0.7rem;
            background: rgba(239, 246, 255, 0.78);
            border-top: 1px solid rgba(147, 197, 253, 0.45);
            border-bottom: 1px solid rgba(147, 197, 253, 0.45);
            color: #1f2937;
            font-size: 0.86rem;
        }

        .debug-table td:first-child {
            border-left: 1px solid rgba(147, 197, 253, 0.45);
            border-radius: 14px 0 0 14px;
            background: linear-gradient(135deg, #dbeafe, #bfdbfe);
            color: #1e3a8a;
            font-weight: 850;
        }

        .debug-table td:last-child {
            border-right: 1px solid rgba(147, 197, 253, 0.45);
            border-radius: 0 14px 14px 0;
        }

        .debug-score {
            color: #0369a1;
            font-weight: 850;
        }

        .debug-hit {
            color: #0f766e;
            font-weight: 700;
        }

        /* Research workbench overrides */
        :root {
            --ink: #111827;
            --muted: #4b5563;
            --line: #d1d5db;
            --line-soft: #e5e7eb;
            --surface: #ffffff;
            --surface-muted: #f3f4f6;
            --accent: #2563eb;
            --success: #047857;
            --warning: #a16207;
            --danger: #b91c1c;
        }

        .stApp {
            background: #f6f7f9;
            color: var(--ink);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 1.35rem;
        }

        .hero {
            text-align: left;
            padding: 0.65rem 0 0.45rem;
            border-bottom: 1px solid var(--line-soft);
        }

        .hero-kicker {
            padding: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            color: #374151;
            font-size: 0.84rem;
            font-weight: 700;
            letter-spacing: 0;
        }

        .hero-title {
            margin: 0.35rem 0 0.25rem;
            color: #111827;
            font-size: 1.9rem;
            line-height: 1.22;
            font-weight: 800;
            letter-spacing: 0;
        }

        .hero-subtitle {
            max-width: 860px;
            margin: 0;
            color: #4b5563;
            font-size: 0.98rem;
            line-height: 1.65;
        }

        div[data-testid="stForm"] {
            width: 100%;
            max-width: 100%;
            margin: 1rem 0 1.2rem;
            border-radius: 8px;
            border: 1px solid var(--line);
            background: var(--surface);
            box-shadow: none;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
            padding: 1rem;
        }

        div[data-testid="stForm"] .stTextInput > label,
        div[data-testid="stForm"] .stNumberInput > label {
            color: #1f2937 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stForm"] .stTextInput input,
        div[data-testid="stForm"] .stNumberInput input,
        div[data-testid="stForm"] .stTextInput div[data-baseweb="input"] {
            border-radius: 6px !important;
            border-color: var(--line) !important;
            box-shadow: none !important;
        }

        div.stButton > button:first-child,
        div[data-testid="stDownloadButton"] > button {
            min-height: 40px;
            border-radius: 6px;
            border: 1px solid #1d4ed8;
            background: #2563eb;
            color: #ffffff;
            font-weight: 700;
            box-shadow: none;
        }

        div.stButton > button:first-child:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            background: #1d4ed8;
            color: #ffffff;
            transform: none;
        }

        div[data-testid="metric-container"] {
            border-radius: 8px;
            padding: 0.85rem;
            background: var(--surface);
            border: 1px solid var(--line-soft);
            box-shadow: none;
        }

        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            color: #111827 !important;
            font-size: 1.08rem !important;
        }

        .section-title {
            margin: 1.3rem 0 0.65rem;
            color: #111827;
            font-size: 1.08rem;
            font-weight: 800;
        }

        .report-title {
            font-size: 1.2rem;
        }

        .workbench-toolbar {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface);
            padding: 0.85rem 1rem 0.2rem;
            margin: 0.8rem 0 1rem;
        }

        .workbench-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.35rem 0 0.75rem;
            color: #4b5563;
            font-size: 0.86rem;
        }

        .meta-chip {
            border: 1px solid var(--line-soft);
            border-radius: 999px;
            background: #f9fafb;
            padding: 0.22rem 0.55rem;
        }

        .report-card,
        .result-card {
            border-radius: 8px;
            padding: 1rem;
            background: var(--surface);
            border: 1px solid var(--line-soft);
            box-shadow: none;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
        }

        .result-card {
            margin-bottom: 0.7rem;
        }

        .result-title {
            color: #1d4ed8;
            font-size: 1rem;
            line-height: 1.45;
            font-weight: 750;
        }

        .result-url {
            color: #047857;
            font-size: 0.82rem;
        }

        .result-snippet {
            color: #374151;
            line-height: 1.65;
            font-size: 0.92rem;
        }

        .pill {
            border-radius: 999px;
            padding: 0.2rem 0.52rem;
            background: #f9fafb;
            color: #374151;
            border: 1px solid var(--line-soft);
            font-size: 0.76rem;
            font-weight: 650;
        }

        .trust-badge {
            font-weight: 800;
        }

        .trust-high {
            background: #ecfdf5;
            border-color: #a7f3d0;
            color: #047857;
        }

        .trust-medium {
            background: #eff6ff;
            border-color: #bfdbfe;
            color: #1d4ed8;
        }

        .trust-low {
            background: #fff7ed;
            border-color: #fed7aa;
            color: #c2410c;
        }

        .trust-unknown,
        .read-fallback {
            background: #f3f4f6;
            border-color: #d1d5db;
            color: #4b5563;
        }

        .read-ok {
            background: #ecfdf5;
            border-color: #a7f3d0;
            color: #047857;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 8px;
            border: 1px solid var(--line);
            box-shadow: none;
        }

        .start-hint {
            position: static;
            transform: none;
            width: auto;
            max-width: 760px;
            text-align: left;
            margin: 2rem 0 0;
            color: #4b5563;
            font-size: 0.98rem;
        }

        @media (max-width: 820px) {
            .metric-grid, .report-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 1.55rem;
            }
            div[data-testid="stForm"] .stTextInput,
            div[data-testid="stForm"] .stNumberInput {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def esc(value):
    return html.escape(str(value or ""))


def credibility_meta(result):
    score = float(result.source_reliability_score or 0)
    if score >= 8 or result.source_tier == 1:
        return "高可信", "trust-high"
    if score >= 5:
        return "中可信", "trust-medium"
    if score > 0:
        return "低可信", "trust-low"
    return "未知可信度", "trust-unknown"


def is_high_credibility(result):
    label, _ = credibility_meta(result)
    return label == "高可信"


def source_filter_options(results):
    labels = sorted({r.source_tier_label for r in results if r.source_tier_label})
    domains = sorted({r.domain for r in results if r.domain})
    return ["全部来源"] + labels + [f"域名：{domain}" for domain in domains]


def filter_results(results, source_choice, high_only, readable_only):
    filtered = list(results)
    if source_choice and source_choice != "全部来源":
        if source_choice.startswith("域名："):
            domain = source_choice.replace("域名：", "", 1)
            filtered = [r for r in filtered if r.domain == domain]
        else:
            filtered = [r for r in filtered if r.source_tier_label == source_choice]
    if high_only:
        filtered = [r for r in filtered if is_high_credibility(r)]
    if readable_only:
        filtered = [r for r in filtered if r.read_success]
    return filtered


def build_export_markdown(query, results):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = (
        build_summary(query, len(results), sum(1 for r in results if r.read_success), results)
        if results
        else "当前筛选条件下没有可导出的结果。"
    )
    lines = [
        f"# {query} 研究小报",
        "",
        f"- 生成时间：{generated_at}",
        f"- 当前导出结果数：{len(results)}",
        "",
        "## 总结",
        "",
        summary.strip() or "暂无总结。",
        "",
        "## 来源清单",
        "",
    ]
    for result in results:
        credibility, _ = credibility_meta(result)
        read_status = "成功读取正文" if result.read_success else "使用搜索摘要"
        snippet = result.snippet or result.content[:220]
        lines.extend([
            f"### {result.rank}. {result.title}",
            "",
            f"- 来源：{result.domain}",
            f"- 链接：{result.url}",
            f"- 主题相关度：{result.topic_relevance_score}/10",
            f"- 来源可信度：{credibility}（{result.source_reliability_score}/10，{result.source_tier_label}）",
            f"- 正文可读性：{result.content_readability_score}/10",
            f"- 时效性：{result.freshness_score}/10",
            f"- 正文读取：{read_status}",
            f"- 排名分：{result.score}/10",
            f"- 摘要：{snippet}",
            f"- 排名原因：{result.ranking_reason}",
            "",
        ])
    return "\n".join(lines)


def safe_export_filename(query):
    cleaned = "".join("_" if char in '<>:"/\\|?*' else char for char in query.strip())
    return f"{cleaned or '研究主题'}_研究小报.md"


def render_workbench_controls(results, query):
    st.markdown(
        '<div class="workbench-toolbar"><div class="workbench-meta">'
        '<span class="meta-chip">筛选作用于当前搜索结果</span>'
        '<span class="meta-chip">高可信为来源可信度 >= 8 或权威研究来源</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    col_source, col_high, col_read, col_export = st.columns([2.2, 1.2, 1.35, 1.25])
    with col_source:
        source_choice = st.selectbox("来源筛选器", source_filter_options(results), key="source_filter")
    with col_high:
        high_only = st.checkbox("只看高可信来源", key="high_only_filter")
    with col_read:
        readable_only = st.checkbox("只看成功读取正文", key="readable_only_filter")

    filtered = filter_results(results, source_choice, high_only, readable_only)
    export_markdown = build_export_markdown(query, filtered)
    with col_export:
        st.download_button(
            "导出当前小报",
            data=export_markdown,
            file_name=safe_export_filename(query),
            mime="text/markdown",
        )

    st.markdown(
        f"""
        <div class="workbench-meta">
            <span class="meta-chip">当前显示：{len(filtered)} / {len(results)}</span>
            <span class="meta-chip">高可信：{sum(1 for r in results if is_high_credibility(r))}</span>
            <span class="meta-chip">正文读取成功：{sum(1 for r in results if r.read_success)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return filtered


def render_metric_grid(query, raw_count, read_count, kept_count):
    cols = st.columns(5)
    cols[0].metric("\u5f53\u524d\u4e3b\u9898", query)
    cols[1].metric("\u641c\u7d22\u7ed3\u679c\u6570\u91cf", raw_count)
    cols[2].metric("\u6210\u529f\u8bfb\u53d6\u6b63\u6587", read_count)
    cols[3].metric("\u6700\u7ec8\u4fdd\u7559\u7ed3\u679c", kept_count)
    cols[4].metric("\u641c\u7d22\u5f15\u64ce", "\u516c\u5f00\u641c\u7d22\u9875")


def split_summary(summary):
    sections = []
    current_title = ""
    current_lines = []
    for line in summary.splitlines():
        if line.startswith("### "):
            if current_title:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.replace("### ", "", 1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def markdownish_to_html(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    html_lines = []
    list_items = []
    for line in lines:
        if line.startswith(("- ", "1. ", "2. ", "3. ", "4. ", "5. ")):
            item = line[2:].strip() if line.startswith("- ") else line[3:].strip()
            list_items.append(f"<li>{esc(item)}</li>")
        else:
            if list_items:
                html_lines.append("<ol>" + "".join(list_items) + "</ol>")
                list_items = []
            html_lines.append(f"<p>{esc(line)}</p>")
    if list_items:
        html_lines.append("<ol>" + "".join(list_items) + "</ol>")
    return "".join(html_lines)


def render_report(summary):
    for title, body in split_summary(summary):
        st.markdown(f"#### {title}")
        st.markdown(body)


def render_results(results):
    for result in results:
        read_status = "\u6210\u529f" if result.read_success else "\u4f7f\u7528\u641c\u7d22\u6458\u8981"
        read_class = "read-ok" if result.read_success else "read-fallback"
        credibility_label, credibility_class = credibility_meta(result)
        snippet = result.snippet or result.content[:220]
        reason_label = "\u4e3a\u4ec0\u4e48\u6392\u7b2c\u4e00" if result.rank == 1 else "\u6392\u540d\u539f\u56e0"
        st.markdown(
            f"""
            <div class="result-card">
                <a class="result-title" href="{esc(result.url)}" target="_blank">
                    {esc(result.rank)}. {esc(result.title)}
                </a>
                <div class="result-url">{esc(result.domain)} · {esc(result.url)}</div>
                <div class="result-snippet">{esc(snippet)}</div>
                <div class="pill-row">
                    <span class="pill trust-badge {credibility_class}">来源可信度：{esc(credibility_label)}</span>
                    <span class="pill {read_class}">正文读取：{esc(read_status)}</span>
                    <span class="pill">\u4e3b\u9898\u76f8\u5173\u5ea6\uff1a{esc(result.topic_relevance_score)}/10</span>
                    <span class="pill">\u6765\u6e90\u5c42\u7ea7\uff1a{esc(result.source_tier_label)}</span>
                    <span class="pill">\u53ef\u4fe1\u5ea6\uff1a{esc(result.source_reliability_score)}/10</span>
                    <span class="pill">\u6b63\u6587\u53ef\u8bfb\u6027\uff1a{esc(result.content_readability_score)}/10</span>
                    <span class="pill">\u65f6\u6548\u6027\uff1a{esc(result.freshness_score)}/10</span>
                    <span class="pill">\u6700\u7ec8\u6392\u540d\u5206\uff1a{esc(result.score)}/10</span>
                </div>
                <div class="result-snippet"><strong>{esc(reason_label)}：</strong>{esc(result.ranking_reason)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_debug_table(results):
    rows = []
    for result in results:
        matched_terms = "\u3001".join(result.matched_terms)
        read_status = result.read_error or result.read_status or "\u6210\u529f"
        rows.append({
            "\u6392\u5e8f": result.rank,
            "\u6807\u9898": result.title,
            "\u547d\u4e2d\u8bcd": matched_terms,
            "\u4e3b\u9898\u76f8\u5173\u5ea6": result.topic_relevance_score,
            "\u6765\u6e90\u5c42\u7ea7": result.source_tier_label,
            "\u53ef\u4fe1\u5ea6": result.source_reliability_score,
            "\u6b63\u6587\u53ef\u8bfb\u6027": result.content_readability_score,
            "\u65f6\u6548\u6027": result.freshness_score,
            "\u6700\u7ec8\u6392\u540d\u5206": result.score,
            "\u6392\u540d\u539f\u56e0": result.ranking_reason,
            "\u5f52\u7c7b\u539f\u56e0": result.source_reason,
            "\u57df\u540d": result.domain,
            "\u8bfb\u53d6\u60c5\u51b5": read_status,
            "\u6b63\u6587\u957f\u5ea6": result.content_length,
            "\u53d1\u5e03\u65f6\u95f4": result.published_at,
            "\u4f5c\u8005": result.author,
        })
    df = pd.DataFrame(
        rows,
        columns=[
            "\u6392\u5e8f",
            "\u6807\u9898",
            "\u547d\u4e2d\u8bcd",
            "\u4e3b\u9898\u76f8\u5173\u5ea6",
            "\u6765\u6e90\u5c42\u7ea7",
            "\u53ef\u4fe1\u5ea6",
            "\u6b63\u6587\u53ef\u8bfb\u6027",
            "\u65f6\u6548\u6027",
            "\u6700\u7ec8\u6392\u540d\u5206",
            "\u6392\u540d\u539f\u56e0",
            "\u5f52\u7c7b\u539f\u56e0",
            "\u57df\u540d",
            "\u8bfb\u53d6\u60c5\u51b5",
            "\u6b63\u6587\u957f\u5ea6",
            "\u53d1\u5e03\u65f6\u95f4",
            "\u4f5c\u8005",
        ],
    )
    st.dataframe(df, width=1180, height=min(380, 58 + max(len(df), 1) * 38))


def install_enter_search_handler():
    components.html(
        """
        <script>
        (() => {
            const scrollTop = () => {
                const doc = window.parent.document;
                if ('scrollRestoration' in window.parent.history) {
                    window.parent.history.scrollRestoration = 'manual';
                }
                const anchor = doc.getElementById('page-top-anchor');
                if (anchor) {
                    anchor.scrollIntoView({ block: 'start', behavior: 'auto' });
                }
                window.parent.scrollTo({ top: 0, left: 0, behavior: 'auto' });
                doc.documentElement.scrollTop = 0;
                doc.body.scrollTop = 0;
                Array.from(doc.querySelectorAll('*')).forEach((node) => {
                    if (node.scrollTop && node.scrollTop > 0) {
                        node.scrollTop = 0;
                    }
                    if (node.scrollLeft && node.scrollLeft > 0) {
                        node.scrollLeft = 0;
                    }
                });
            };
            const runPendingTopScroll = () => {
                if (window.parent.sessionStorage.getItem('searchShouldReturnTop') !== '1') {
                    return;
                }
                let userMoved = false;
                const stopForUser = () => { userMoved = true; };
                window.parent.addEventListener('wheel', stopForUser, { once: true, passive: true });
                window.parent.addEventListener('touchstart', stopForUser, { once: true, passive: true });
                window.parent.addEventListener('pointerdown', stopForUser, { once: true, passive: true });
                window.parent.addEventListener('mousedown', stopForUser, { once: true, passive: true });

                let elapsed = 0;
                scrollTop();
                window.requestAnimationFrame(scrollTop);
                const timer = window.setInterval(() => {
                    if (userMoved || elapsed >= 8000) {
                        window.clearInterval(timer);
                        window.parent.sessionStorage.removeItem('searchShouldReturnTop');
                        return;
                    }
                    scrollTop();
                    elapsed += 250;
                }, 250);
            };
            runPendingTopScroll();

            const bindSearchEnter = () => {
                const doc = window.parent.document;
                const searchInput = Array.from(doc.querySelectorAll('input'))
                    .find((input) => input.type === 'text' && input.placeholder);
                const searchButton = Array.from(doc.querySelectorAll('button'))
                    .find((button) => button.innerText.trim() === '\\u641c\\u7d22');

                if (!searchInput || !searchButton || searchInput.dataset.enterSearchBound) {
                    return;
                }

                searchInput.dataset.enterSearchBound = '1';
                const markSearchStarted = () => {
                    window.parent.sessionStorage.setItem('searchShouldReturnTop', '1');
                    scrollTop();
                };
                let enterSubmitPending = false;
                const submitByEnter = (event) => {
                    if (event.key !== 'Enter' || event.isComposing) {
                        return;
                    }
                    if (doc.activeElement !== searchInput) {
                        return;
                    }
                    if (enterSubmitPending) {
                        return;
                    }
                    enterSubmitPending = true;
                    event.preventDefault();
                    markSearchStarted();
                    window.setTimeout(() => {
                        searchButton.click();
                        enterSubmitPending = false;
                    }, 40);
                };
                searchButton.addEventListener('click', markSearchStarted);
                searchInput.addEventListener('keydown', submitByEnter, true);
                searchInput.addEventListener('keyup', submitByEnter, true);
                doc.addEventListener('keydown', submitByEnter, true);
                doc.addEventListener('keyup', submitByEnter, true);
            };

            bindSearchEnter();
            let tries = 0;
            const bindTimer = window.setInterval(() => {
                bindSearchEnter();
                tries += 1;
                if (tries >= 40) {
                    window.clearInterval(bindTimer);
                }
            }, 250);
        })();
        </script>
        """,
        height=0,
    )


st.set_page_config(page_title=PAGE_TITLE, layout="wide")
inject_style()
st.markdown('<div id="page-top-anchor"></div>', unsafe_allow_html=True)
if st.session_state.pop("return_top_after_search", False):
    components.html(
        """
        <script>
        window.parent.sessionStorage.setItem('searchShouldReturnTop', '1');
        </script>
        """,
        height=0,
    )
install_enter_search_handler()

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">\u771f\u5b9e\u8054\u7f51 · \u7b5b\u9009\u6392\u5e8f · \u603b\u7ed3\u5c0f\u62a5</div>
        <div class="hero-title">{PAGE_TITLE}</div>
        <div class="hero-subtitle">
            \u9762\u5411\u6696\u901a\u7a7a\u8c03\u4e0e\u5efa\u7b51\u8282\u80fd\u8bfe\u9898\uff0c\u8f93\u5165\u5173\u952e\u8bcd\u540e\u81ea\u52a8\u641c\u7d22\u3001\u8bfb\u53d6\u3001\u6392\u5e8f\u5e76\u751f\u6210\u53ef\u6f14\u793a\u7684\u7ed3\u6784\u5316\u5c0f\u62a5\u3002
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ui_version = st.session_state.get("ui_version", 0)
if not st.session_state.get("search_top_n_default_upgraded_v1"):
    if st.session_state.get("last_search_top_n", 0) < 40:
        st.session_state["last_search_top_n"] = 40
    st.session_state["search_top_n_default_upgraded_v1"] = True
if not st.session_state.get("read_top_k_default_upgraded_v2"):
    if st.session_state.get("last_read_top_k", 0) < 16:
        st.session_state["last_read_top_k"] = 16
    st.session_state["read_top_k_default_upgraded_v2"] = True

with st.form(f"search_form_{ui_version}"):
    col_q, col_c = st.columns([5.2, 1.35])
    with col_q:
        query = st.text_input(
            "\u641c\u7d22\u4e3b\u9898",
            value=st.session_state.get("last_query", ""),
            placeholder="\u4f8b\u5982\uff1aHVAC AI\u9884\u6d4b\u63a7\u5236\u4ea7\u54c1 2024",
            key=f"query_input_{ui_version}",
        )
    with col_c:
        submitted = st.form_submit_button("\u641c\u7d22")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        search_top_n = st.number_input(
            "\u641c\u7d22\u7ed3\u679c\u6570\u91cf",
            min_value=5,
            max_value=50,
            value=st.session_state.get("last_search_top_n", 40),
            step=1,
            key=f"search_top_n_{ui_version}",
        )
    with col_b:
        read_top_k = st.number_input(
            "\u8bfb\u53d6\u6b63\u6587\u6570\u91cf",
            min_value=0,
            max_value=20,
            value=st.session_state.get("last_read_top_k", 16),
            step=1,
            key=f"read_top_k_{ui_version}",
        )

if submitted:
    if not query.strip():
        query = "\u70ed\u6cf5"
    st.session_state["last_query"] = query
    st.session_state["last_search_top_n"] = search_top_n
    st.session_state["last_read_top_k"] = read_top_k
    loading_slot = st.empty()
    progress_state = {"raw_count": 0}

    def update_progress(phase, completed, total, count):
        total = max(total, 1)
        if phase == "search_start":
            percent = 3 + (3 * completed / total)
            render_progress(
                loading_slot,
                percent,
                f"\u6b63\u5728\u542f\u52a8\u5173\u952e\u8bcd\u641c\u7d22 {completed}/{total}",
                f"\u5df2\u542f\u52a8 {count} \u4e2a\u641c\u7d22\u8bf7\u6c42\uff0c\u6b63\u5728\u7b49\u5f85\u641c\u7d22\u7f51\u7ad9\u8fd4\u56de",
            )
        elif phase == "search":
            percent = 6 + (44 * completed / total)
            render_progress(
                loading_slot,
                percent,
                f"\u6b63\u5728\u771f\u5b9e\u8054\u7f51\u641c\u7d22 {completed}/{total} \u7ec4\u5173\u952e\u8bcd",
                f"\u5df2\u641c\u7d22 {count} \u4e2a\u7f51\u7ad9",
            )
        elif phase == "search_done":
            progress_state["raw_count"] = count
            render_progress(
                loading_slot,
                52,
                "\u8054\u7f51\u641c\u7d22\u5b8c\u6210",
                f"\u5df2\u641c\u7d22 {count} \u4e2a\u7f51\u7ad9\uff0c\u6b63\u5728\u51c6\u5907\u8bfb\u53d6\u6b63\u6587",
            )
        elif phase == "read":
            percent = 55 + (30 * completed / total)
            render_progress(
                loading_slot,
                percent,
                f"\u6b63\u5728\u8bfb\u53d6\u7f51\u9875\u6b63\u6587 {completed}/{total}",
                (
                    f"\u5df2\u641c\u7d22 {progress_state['raw_count']} \u4e2a\u7f51\u7ad9\uff0c"
                    f"\u6210\u529f\u8bfb\u53d6 {count} \u4e2a\u7f51\u9875\u6b63\u6587"
                ),
            )

    render_progress(
        loading_slot,
        3,
        "\u6b63\u5728\u51c6\u5907\u771f\u5b9e\u8054\u7f51\u641c\u7d22",
        "\u8fdb\u5ea6\u4f1a\u968f\u641c\u7d22\u8bf7\u6c42\u548c\u7f51\u9875\u8bfb\u53d6\u5b8c\u6210\u800c\u66f4\u65b0",
    )
    raw_results = search_web(query, search_top_n, update_progress)
    progress_state["raw_count"] = len(raw_results)
    read_result_pages(raw_results, read_top_k, update_progress)
    read_count = sum(1 for r in raw_results if r.read_success)
    render_progress(
        loading_slot,
        88,
        "\u6b63\u5728\u7b5b\u9009\u548c\u6392\u5e8f\u7ed3\u679c",
        f"\u5df2\u641c\u7d22 {len(raw_results)} \u4e2a\u7f51\u7ad9\uff0c\u6210\u529f\u8bfb\u53d6 {read_count} \u4e2a\u7f51\u9875\u6b63\u6587",
    )
    ranked = rank_results(raw_results, query)
    render_progress(
        loading_slot,
        94,
        "\u6b63\u5728\u751f\u6210\u5c0f\u62a5",
        f"\u5df2\u4fdd\u7559 {len(ranked)} \u4e2a\u9ad8\u76f8\u5173\u6765\u6e90",
    )
    summary = build_summary(query, len(raw_results), read_count, ranked)
    render_progress(loading_slot, 100, "\u5c0f\u62a5\u751f\u6210\u5b8c\u6210", "\u6b63\u5728\u6253\u5f00\u7814\u7a76\u5de5\u4f5c\u53f0")
    loading_slot.empty()
    st.session_state["search_payload"] = {
        "query": query,
        "raw_count": len(raw_results),
        "read_count": read_count,
        "ranked": ranked,
        "summary": summary,
    }
    st.session_state["return_top_after_search"] = True
    st.session_state["ui_version"] = ui_version + 1
    st.experimental_rerun()

payload = st.session_state.get("search_payload")

if payload:
    st.markdown('<div class="section-title">\u7814\u7a76\u5de5\u4f5c\u53f0</div>', unsafe_allow_html=True)
    filtered_results = render_workbench_controls(payload["ranked"], payload["query"])

    st.markdown('<div class="section-title">\u641c\u7d22\u72b6\u6001</div>', unsafe_allow_html=True)
    render_metric_grid(payload["query"], payload["raw_count"], payload["read_count"], len(filtered_results))

    st.markdown('<div class="section-title">\u641c\u7d22\u7ed3\u679c</div>', unsafe_allow_html=True)
    if filtered_results:
        render_results(filtered_results)
    else:
        st.info("当前筛选条件下没有结果。可以放宽来源、可信度或正文读取条件。")

    with st.expander("\u8c03\u8bd5\u4fe1\u606f", expanded=False):
        render_debug_table(filtered_results)

    st.markdown('<div class="section-title report-title">\u603b\u7ed3\u5c0f\u62a5</div>', unsafe_allow_html=True)
    render_report(payload["summary"])
else:
    st.markdown(
        """
        <p class="start-hint">
            \u8f93\u5165\u641c\u7d22\u4e3b\u9898\u5e76\u8bbe\u7f6e\u7ed3\u679c\u6570\u91cf\u540e\uff0c\u70b9\u51fb\u641c\u7d22\u5f00\u59cb\u751f\u6210\u7814\u7a76\u5c0f\u62a5\u3002
        </p>
        """,
        unsafe_allow_html=True,
    )
