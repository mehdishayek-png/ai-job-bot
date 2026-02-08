import streamlit as st
import json
import os
import re
import uuid
import time
import io
import zipfile
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ============================================
# PAGE CONFIG — MUST BE FIRST
# ============================================

st.set_page_config(
    page_title="JobBot · AI-Powered Job Matching",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS — 2026 Glassmorphism + Modern Design
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ============ GLOBAL ============ */
* { margin: 0; padding: 0; box-sizing: border-box; }

.stApp {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #f8f9fc;
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: #1a1a2e !important;
}

p, li, span, div { color: #3d3d56; }

code, .stCode, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ============ HERO ============ */
.hero {
    background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 60%, #74b9ff 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(108, 92, 231, 0.2);
}

.hero::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -15%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    filter: blur(40px);
}

.hero-content { position: relative; z-index: 1; }

.hero h1 {
    color: #ffffff !important;
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.4rem 0 !important;
    line-height: 1.1;
}

.hero-subtitle {
    color: rgba(255,255,255,0.85);
    font-size: 1.05rem;
    margin: 0 0 1.2rem 0;
    font-weight: 400;
    line-height: 1.5;
}

.hero-tags {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}

.hero-tag {
    background: rgba(255,255,255,0.2);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.3);
    color: #fff;
    padding: 0.4rem 0.85rem;
    border-radius: 10px;
    font-size: 0.8rem;
    font-weight: 600;
}

/* ============ STEPPER ============ */
.stepper {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.75rem;
    margin: 1.5rem 0 2rem;
    padding: 1rem;
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.step {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6c6c8a;
}

.step-icon {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}

.step.done { color: #059669; }
.step.done .step-icon {
    background: #059669;
    color: #fff;
    box-shadow: 0 2px 8px rgba(5,150,105,0.25);
}

.step.active {
    color: #6c5ce7;
    background: #f0edff;
}
.step.active .step-icon {
    background: #6c5ce7;
    color: #fff;
    box-shadow: 0 2px 8px rgba(108,92,231,0.3);
    animation: pulse 2s ease-in-out infinite;
}

.step.pending { color: #c0c0d0; }
.step.pending .step-icon {
    background: #f0f0f5;
    border: 2px dashed #d0d0dd;
}

.step-connector {
    width: 40px; height: 2px;
    background: #e0e0ea;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

/* ============ CARDS ============ */
.glass-card {
    background: #ffffff;
    border: 1px solid #e8e8f0;
    border-radius: 16px;
    padding: 1.75rem;
    margin-bottom: 1.25rem;
    transition: all 0.2s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.glass-card:hover {
    border-color: #d0cfe8;
    box-shadow: 0 4px 16px rgba(108,92,231,0.08);
}

.card-header {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin-bottom: 1.25rem;
}

.card-icon {
    width: 42px; height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    background: #f0edff;
    border: 1px solid #e0dcf5;
}

.card-title {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    color: #1a1a2e !important;
    margin: 0 !important;
}

/* ============ SKILL CHIPS ============ */
.skills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: 1rem;
    padding: 0.75rem 0;
}

.skill-chip {
    padding: 0.5rem 1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
    backdrop-filter: blur(10px);
    border: 1px solid;
    transition: all 0.3s ease;
    white-space: nowrap;
}

/* Color variation for skills - rotate through different colors */
.skill-chip:nth-child(4n+1) {
    background: rgba(108, 92, 231, 0.12);
    color: #5a4b9a;
    border-color: rgba(108, 92, 231, 0.3);
}

.skill-chip:nth-child(4n+2) {
    background: rgba(5, 150, 105, 0.12);
    color: #047857;
    border-color: rgba(5, 150, 105, 0.3);
}

.skill-chip:nth-child(4n+3) {
    background: rgba(217, 119, 6, 0.12);
    color: #b45309;
    border-color: rgba(217, 119, 6, 0.3);
}

.skill-chip:nth-child(4n+4) {
    background: rgba(30, 58, 138, 0.12);
    color: #1e3a8a;
    border-color: rgba(30, 58, 138, 0.3);
}

.skill-chip:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(108, 92, 231, 0.15);
}

/* ============ STATS ============ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1.25rem;
    margin: 2rem 0;
    padding: 0.5rem 0;
}

.stat-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(249,248,255,0.95) 100%);
    border: 1.5px solid rgba(224, 220, 245, 0.6);
    border-radius: 16px;
    padding: 1.5rem 1.25rem;
    text-align: center;
    box-shadow: 0 4px 16px rgba(108,92,231,0.08);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.stat-card:hover {
    border-color: #d0cfe8;
    box-shadow: 0 8px 24px rgba(108,92,231,0.12);
    transform: translateY(-2px);
}

.stat-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: #6c5ce7;
    line-height: 1;
    margin-bottom: 0.5rem;
}

.stat-label {
    color: #8888a0;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ============ SCORE BADGES ============ */
.score-badge {
    display: inline-block;
    padding: 0.4rem 1rem;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 700;
    text-align: center;
}

.score-excellent {
    background: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
}
.score-good {
    background: #fffbeb;
    color: #d97706;
    border: 1px solid #fde68a;
}
.score-fair {
    background: #f0edff;
    color: #6c5ce7;
    border: 1px solid #e0dcf5;
}

/* ============ SOURCE BADGES ============ */
.source-badge, .src-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: #eef2ff;
    color: #6366f1;
    border: 1px solid #ddd6fe;
}

/* ============ TIMESTAMP BADGES ============ */
.ts-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 600;
}
.ts-fresh {
    background: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
}
.ts-recent {
    background: #fed7aa;
    color: #ea580c;
    border: 1px solid #fdba74;
}
.ts-old {
    background: #f3f4f6;
    color: #6b7280;
    border: 1px solid #e5e7eb;
}

/* ============ PIN BADGE ============ */
.pin-badge {
    display: inline-flex;
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 700;
    background: #fecaca;
    color: #ef4444;
    border: 1px solid #fca5a5;
}

/* ============ BUTTONS ============ */
.stButton > button {
    background: #6c5ce7 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.25rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(108,92,231,0.2) !important;
}

.stButton > button:hover {
    background: #5b4bd5 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(108,92,231,0.3) !important;
}

/* VIBRANT Apply Now Button - Stand out in job cards */
/* Target link_button specifically */
div[data-testid="baseButton-secondary"] a {
    background: linear-gradient(135deg, #ff6b35 0%, #ff8555 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 16px rgba(255, 107, 53, 0.3) !important;
    text-decoration: none !important;
    display: inline-block !important;
    width: 100% !important;
    text-align: center !important;
}

div[data-testid="baseButton-secondary"] a:hover {
    background: linear-gradient(135deg, #ff5920 0%, #ff7a45 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255, 107, 53, 0.4) !important;
}

/* ============ EXPANDERS (job cards) ============ */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #ffffff 0%, #f9f8ff 100%) !important;
    border: 1.5px solid #e0dcf5 !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    color: #1a1a2e !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.5rem !important;
    transition: all 0.3s ease !important;
}

.streamlit-expanderHeader:hover {
    border-color: #d0cfe8 !important;
    box-shadow: 0 4px 16px rgba(108,92,231,0.1) !important;
}

/* When expander is open, ensure content has proper spacing */
div[data-testid="stExpander"] {
    margin-bottom: 1.5rem !important;
}

div[data-testid="stExpander"] > div:last-child {
    padding: 1.25rem 1.5rem !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(249,248,255,0.95) 100%) !important;
    border: 1px solid #e8e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
    backdrop-filter: blur(10px) !important;
}

/* Input elements within expanders */
div[data-testid="stExpander"] .stTextInput > div > div > input,
div[data-testid="stExpander"] .stTextArea > div > div > textarea,
div[data-testid="stExpander"] .stSelectbox > div > div {
    background: rgba(255, 255, 255, 0.92) !important;
    color: #1a1a2e !important;
}

/* Focus state within expanders */
div[data-testid="stExpander"] .stTextInput > div > div > input:focus,
div[data-testid="stExpander"] .stTextArea > div > div > textarea:focus,
div[data-testid="stExpander"] .stSelectbox > div > div:focus {
    background: rgba(255, 255, 255, 0.99) !important;
    color: #1a1a2e !important;
}

/* ============ INPUTS ============ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(255, 255, 255, 0.85) !important;
    backdrop-filter: blur(10px) !important;
    border: 1.5px solid rgba(224, 224, 234, 0.8) !important;
    border-radius: 12px !important;
    color: #1a1a2e !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 1rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
}

/* Focus state - subtle, clean appearance */
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox > div > div:focus,
.stMultiSelect > div > div:focus {
    border-color: #6c5ce7 !important;
    box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.12), 0 2px 12px rgba(108, 92, 231, 0.1) !important;
    background: rgba(255, 255, 255, 0.98) !important;
    color: #1a1a2e !important;
    outline: none !important;
}

/* Prevent black text appearance on selection */
.stTextInput > div > div > input::selection,
.stTextArea > div > div > textarea::selection {
    background: rgba(108, 92, 231, 0.2) !important;
    color: #1a1a2e !important;
}

/* Selectbox dropdown styling */
.stSelectbox > div > div > div,
.stMultiSelect > div > div > div {
    background: rgba(255, 255, 255, 0.95) !important;
    color: #1a1a2e !important;
}

/* Selectbox custom select element styling */
select, 
div[data-baseweb="select"] {
    background: rgba(255, 255, 255, 0.85) !important;
    color: #1a1a2e !important;
    border-color: rgba(224, 224, 234, 0.8) !important;
}

select:focus, 
div[data-baseweb="select"]:focus {
    background: rgba(255, 255, 255, 0.98) !important;
    border-color: #6c5ce7 !important;
    color: #1a1a2e !important;
}

.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: #b0b0c0 !important;
}

/* Enhance label styling */
.stTextInput > label,
.stTextArea > label,
.stSelectbox > label,
.stMultiSelect > label {
    font-weight: 600 !important;
    color: #3d3d56 !important;
    margin-bottom: 0.5rem !important;
}

/* ============ DIVIDER ============ */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, #e0e0ea 50%, transparent 100%);
    margin: 2rem 0;
}

/* ============ COVER LETTER ============ */
.cover-letter-box {
    background: linear-gradient(135deg, rgba(248, 248, 252, 0.8) 0%, rgba(240, 237, 255, 0.8) 100%);
    backdrop-filter: blur(10px);
    border: 1.5px solid rgba(224, 220, 245, 0.6);
    border-radius: 14px;
    padding: 1.5rem;
    margin-top: 1rem;
    color: #3d3d56;
    line-height: 1.8;
    font-size: 0.95rem;
    box-shadow: 0 8px 32px rgba(108, 92, 231, 0.08);
}

.cover-letter-label {
    color: #6c5ce7;
    font-weight: 700;
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

/* ============ COLUMNS & LAYOUT IMPROVEMENTS ============ */
/* Ensure column spacing and proper alignment */
div[data-testid="column"] {
    padding: 0.5rem !important;
    gap: 1rem !important;
}

/* Improve job card layout - right column spacing */
div[data-testid="column"]:last-child {
    min-width: 140px !important;
}

/* Ensure buttons in columns are readable */
div[data-testid="column"] .stButton > button {
    width: 100% !important;
    margin-bottom: 0.75rem !important;
}

/* Markdown text readability in columns */
div[data-testid="column"] .stMarkdown {
    color: #1a1a2e !important;
    line-height: 1.6 !important;
}

/* ============ SCROLLBAR ============ */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #f0f0f5; }
::-webkit-scrollbar-thumb { background: #d0cfe8; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #b0afd0; }

/* ============ FOOTER ============ */
.footer {
    text-align: center;
    padding: 1.5rem 1rem;
    margin-top: 3rem;
    color: #999;
    font-size: 0.8rem;
    border-top: 1px solid #e8e8f0;
}
.footer a { color: #6c5ce7; text-decoration: none; font-weight: 600; }
.footer a:hover { color: #5b4bd5; }

/* ============ SIDEBAR ============ */
section[data-testid="stSidebar"] {
    background: #fff;
    border-right: 1px solid #e8e8f0;
}
section[data-testid="stSidebar"] * { color: #3d3d56; }
/* ============ FILE UPLOADER - GLASSMORPHISM ============ */
.stFileUploader {
    margin-bottom: 1.5rem !important;
}

.stFileUploader section {
    padding: 1.5rem !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(249,248,255,0.7) 100%) !important;
    border: 2px dashed rgba(108, 92, 231, 0.3) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 16px rgba(108, 92, 231, 0.06) !important;
}

.stFileUploader section:hover {
    border-color: rgba(108, 92, 231, 0.5) !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.85) 0%, rgba(249,248,255,0.85) 100%) !important;
    box-shadow: 0 8px 24px rgba(108, 92, 231, 0.12) !important;
}

.stFileUploader section > div {
    color: #3d3d56 !important;
}

.stFileUploader span {
    color: #6c5ce7 !important;
    font-weight: 600 !important;
}

/* Uploaded file name - make it readable */
.stFileUploader [data-testid="stFileUploadDropzone"] > div > div {
    color: #1a1a2e !important;
}

div[data-testid="stFileUploadDropzone"] button {
    background: linear-gradient(135deg, #6c5ce7 0%, #7d6cdc 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.3s ease !important;
}

div[data-testid="stFileUploadDropzone"] button:hover {
    background: linear-gradient(135deg, #5b4bd5 0%, #6c5cce 100%) !important;
    transform: translateY(-1px) !important;
}

/* ============ PROFILE DISPLAY SECTION ============ */
.profile-box {
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(249,248,255,0.95) 100%);
    backdrop-filter: blur(10px);
    border: 1.5px solid rgba(108, 92, 231, 0.2);
    border-radius: 16px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 8px 32px rgba(108, 92, 231, 0.1);
}

.profile-name {
    font-size: 1.5rem !important;
    font-weight: 800 !important;
    color: #1a1a2e !important;
    margin-bottom: 0.5rem !important;
}

.profile-headline {
    font-size: 1rem !important;
    color: #6c5ce7 !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
}

.profile-location {
    font-size: 0.95rem !important;
    color: #3d3d56 !important;
    margin-top: 0.75rem !important;
}

.skills-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 2px solid rgba(108, 92, 231, 0.1);
}

.sc {
    display: inline-block;
    padding: 0.55rem 1.1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    backdrop-filter: blur(10px);
    border: 1px solid;
    transition: all 0.3s ease;
}

.sc:nth-child(4n+1) {
    background: rgba(108, 92, 231, 0.12);
    color: #5a4b9a;
    border-color: rgba(108, 92, 231, 0.3);
}

.sc:nth-child(4n+2) {
    background: rgba(5, 150, 105, 0.12);
    color: #047857;
    border-color: rgba(5, 150, 105, 0.3);
}

.sc:nth-child(4n+3) {
    background: rgba(217, 119, 6, 0.12);
    color: #b45309;
    border-color: rgba(217, 119, 6, 0.3);
}

.sc:nth-child(4n+4) {
    background: rgba(30, 58, 138, 0.12);
    color: #1e3a8a;
    border-color: rgba(30, 58, 138, 0.3);
}

.sc:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(108, 92, 231, 0.2);
}

/* ============ STREAMLIT OVERRIDES ============ */
/* Fix text colors in expanders, markdown, captions */
.stMarkdown, .stMarkdown p, .stCaption, .stText { color: #3d3d56 !important; }
.stAlert p { color: inherit !important; }
label, .stSelectbox label, .stTextInput label, .stTextArea label { color: #3d3d56 !important; }

/* Expander content readability */
div[data-testid="stExpander"] details summary span { color: #1a1a2e !important; }
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p { color: #3d3d56 !important; }

/* ============ CODE BLOCKS & PROGRESS - IMPROVED ============ */
/* Light gradient background instead of dark/black */
.stCodeBlock, pre, code { 
    background: linear-gradient(135deg, #f0edff 0%, #eef2ff 100%) !important; 
    color: #3d3d56 !important;
    border: 1.5px solid rgba(224, 220, 245, 0.6) !important;
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important;
    padding: 1rem 1.25rem !important;
    backdrop-filter: blur(10px) !important;
}

/* Progress bar with gradient matching hero */
.stProgress > div > div > div { 
    background: linear-gradient(135deg, #6c5ce7 0%, #74b9ff 100%) !important; 
    border-radius: 10px !important;
}

/* Container for progress and status messages */
.stSpinner,
div[class*="Progress"],
div[class*="progress"] {
    margin-bottom: 1.5rem !important;
}

/* Ensure proper spacing for overlapping elements */
.element-container {
    margin-bottom: 1rem !important;
}

/* Links */
a { color: #6c5ce7; text-decoration: none; }
a:hover { color: #5b4bd5; text-decoration: underline; }

/* Info/Warning/Error boxes - match theme */
.stAlert {
    border-radius: 12px !important;
    border-left: 4px solid #6c5ce7 !important;
    font-family: 'DM Sans', sans-serif !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(249,248,255,0.95) 100%) !important;
    backdrop-filter: blur(10px) !important;
    padding: 1.25rem 1.5rem !important;
    margin-bottom: 1.5rem !important;
    box-shadow: 0 4px 16px rgba(108, 92, 231, 0.08) !important;
}

.stAlert p {
    color: #3d3d56 !important;
    line-height: 1.6 !important;
}

/* ENSURE DM SANS EVERYWHERE - override Streamlit defaults */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stTextInput, .stTextArea, .stSelectbox, .stMultiSelect, .stNumberInput,
div[data-testid="stMarkdownContainer"],
div[data-testid="stMarkdownContainer"] *,
.stCaption, .element-container * {
    font-family: 'DM Sans', sans-serif !important;
}

/* Input wrapper elements - prevent dark backgrounds */
.stTextInput > div,
.stTextArea > div,
.stSelectbox > div,
.stMultiSelect > div {
    background: transparent !important;
}

/* Input inner wrappers */
.stTextInput > div > div,
.stTextArea > div > div,
.stSelectbox > div > div {
    background: transparent !important;
}

/* Override Streamlit's input wrapper defaults */
div[data-testid="stTextInput"],
div[data-testid="stTextArea"],
div[data-testid="stSelectbox"] {
    background: transparent !important;
}

/* Captions - consistent styling */
.stCaption {
    color: #8888a0 !important;
    font-size: 0.85rem !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# IMPORTS
# ============================================
load_dotenv()
import importlib, sys
for _m in ["location_utils","job_fetcher","resume_parser","run_auto_apply","cover_letter_generator"]:
    if _m in sys.modules:
        try: importlib.reload(sys.modules[_m])
        except: sys.modules.pop(_m, None)
try:
    from job_fetcher import fetch_all
    from resume_parser import build_profile
    from run_auto_apply import run_auto_apply_pipeline
    from cover_letter_generator import generate_cover_letter
    from location_utils import get_all_regions, get_region_display_name
except (ImportError, KeyError) as e:
    st.error(f"Missing module: {e}"); st.stop()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]
SID = st.session_state["session_id"]
DD = f"data/session_{SID}"
os.makedirs(DD, exist_ok=True)
PF = os.path.join(DD,"profile.json"); JF = os.path.join(DD,"jobs.json")
MF = os.path.join(DD,"matches.json"); CF = os.path.join(DD,"semantic_cache.json")
LF = os.path.join(DD,"pipeline.log"); LD = os.path.join(DD,"cover_letters")

COUNTRIES = ["India","United States","United Kingdom","Canada","Germany","Australia","UAE",
    "Saudi Arabia","Singapore","Netherlands","France","Ireland","Israel","Brazil",
    "Japan","South Korea","Philippines","Indonesia","Malaysia","Mexico","Remote Only"]
STATES = {
    "India":["Any","Karnataka (Bangalore)","Maharashtra (Mumbai/Pune)","Delhi NCR","Telangana (Hyderabad)","Tamil Nadu (Chennai)","West Bengal (Kolkata)","Gujarat (Ahmedabad)","Rajasthan (Jaipur)","Uttar Pradesh (Noida/Lucknow)","Kerala (Kochi)","Haryana (Gurgaon)"],
    "United States":["Any","California","New York","Texas","Washington","Massachusetts","Illinois","Florida","Georgia","Colorado"],
    "United Kingdom":["Any","London","Manchester","Edinburgh","Birmingham"],
    "Canada":["Any","Ontario (Toronto)","British Columbia (Vancouver)","Quebec (Montreal)","Alberta (Calgary)"],
    "Germany":["Any","Berlin","Munich","Hamburg","Frankfurt"],
    "Australia":["Any","New South Wales (Sydney)","Victoria (Melbourne)","Queensland (Brisbane)"],
    "UAE":["Any","Dubai","Abu Dhabi"],"Saudi Arabia":["Any","Riyadh","Jeddah"],
    "Singapore":["Any"],"Netherlands":["Any","Amsterdam"],"France":["Any","Paris"],
    "Ireland":["Any","Dublin"],"Israel":["Any","Tel Aviv"],"Brazil":["Any","Sao Paulo"],
    "Japan":["Any","Tokyo"],"South Korea":["Any","Seoul"],"Philippines":["Any","Metro Manila"],
    "Indonesia":["Any","Jakarta"],"Malaysia":["Any","Kuala Lumpur"],"Mexico":["Any","Mexico City"],
    "Remote Only":["Any"],
}

def load_j(fp):
    if not os.path.exists(fp): return None
    try:
        with open(fp,"r",encoding="utf-8") as f: return json.load(f)
    except: return None
def save_j(fp, d):
    os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
    with open(fp,"w",encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)
def strip_html(t):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+',' ',t)).strip() if t else ""
def mk_zip(d):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(d):
            if f.endswith(".txt"): z.write(os.path.join(d,f),f)
    b.seek(0); return b.getvalue()
def find_cl(company, title):
    if not os.path.exists(LD): return None,None
    cc=re.sub(r'[^a-zA-Z0-9_\-]','',company.replace(' ','_')).lower()
    tc=re.sub(r'[^a-zA-Z0-9_\-]','',title.replace(' ','_')).lower()
    for fn in os.listdir(LD):
        if fn.endswith(".txt") and (cc in fn.lower() or tc in fn.lower()):
            try:
                with open(os.path.join(LD,fn),"r",encoding="utf-8") as f: return f.read(),fn
            except: pass
    return None,None

def parse_ts(job):
    """Extract a datetime from job's posted_date or summary text."""
    p = job.get("posted_date") or ""
    if p:
        try: return datetime.fromisoformat(p.replace("Z","+00:00"))
        except: pass
    c = f"{job.get('summary','')} {job.get('title','')}".lower()
    if "just posted" in c or "just now" in c: return datetime.now()
    m = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', c)
    if m:
        n,u = int(m.group(1)), m.group(2)
        deltas = {"hour":timedelta(hours=n),"day":timedelta(days=n),"week":timedelta(weeks=n),"month":timedelta(days=n*30)}
        return datetime.now() - deltas.get(u, timedelta())
    return None

def fmt_ts(dt):
    """Format datetime into relative string + CSS class."""
    if not dt: return None, None, "ts-old"
    diff = datetime.now() - dt
    s = diff.total_seconds()
    if s < 3600: return "Just now", dt.strftime("%b %d, %Y"), "ts-fresh"
    if s < 86400: return f"{int(s//3600)}h ago", dt.strftime("%b %d, %Y"), "ts-fresh"
    if diff.days < 3: return f"{diff.days}d ago", dt.strftime("%b %d, %Y"), "ts-fresh"
    if diff.days < 7: return f"{diff.days}d ago", dt.strftime("%b %d, %Y"), "ts-recent"
    if diff.days < 30: return f"{diff.days//7}w ago", dt.strftime("%b %d, %Y"), "ts-recent"
    return f"{diff.days//30}mo ago", dt.strftime("%b %d, %Y"), "ts-old"

def get_pinned(): return st.session_state.get("_pins", set())
def toggle_pin(k):
    p = st.session_state.get("_pins", set())
    p.symmetric_difference_update({k})
    st.session_state["_pins"] = p
def jkey(j): return f"{j.get('company','')}__{j.get('title','')}__{j.get('apply_url','')[:50]}"

# Load profile and matches early for sidebar display
profile = load_j(PF)
matches = load_j(MF)

# ============================================
# SIDEBAR
# ============================================
# SIDEBAR - SESSION INFO & DEBUGGING
# ============================================
with st.sidebar:
    st.markdown("### 🔍 Session Info")
    st.code(f"Session ID: {SID}", language=None)
    st.caption("💡 **For Support:** Share this Session ID if you encounter issues")
    
    # Log file location info
    log_path = os.path.join(DD, "pipeline.log")
    st.caption(f"📁 **Logs:** `{log_path}`")
    
    if st.button("🔄 Start Fresh Session", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🎯 How It Works")
    st.markdown("""
    **1.** Upload resume → Extract skills  
    **2.** Scan 300+ jobs from 6 sources  
    **3.** AI ranks by match quality  
    **4.** Generate cover letters on demand
    """)
    
    st.markdown("---")
    st.markdown("### 📊 Job Sources")
    sources_info = [
        ("🌐 Google Jobs", "via Serper.dev"),
        ("💼 LinkedIn, Indeed", "Local + Remote"),
        ("🇮🇳 Naukri, Glassdoor", "India-focused"),
        ("🏢 Lever", "50+ tech companies"),
        ("🌍 Remotive", "Curated remote"),
        ("💻 WeWorkRemotely", "Remote-first")
    ]
    for name, desc in sources_info:
        st.caption(f"{name} · *{desc}*")
    
    st.markdown("---")
    st.markdown("### 🐛 Debug Info")
    st.caption(f"**Data Directory:** `{DD}`")
    st.caption(f"**Profile:** {'✅ Loaded' if profile else '❌ Missing'}")
    st.caption(f"**Matches:** {len(matches) if matches else 0} found")
    if os.path.exists(log_path):
        st.caption(f"**Log Size:** {os.path.getsize(log_path) // 1024}KB")


# ============================================
# HERO
# ============================================
st.markdown("""
<div class="hero"><div class="hero-content">
    <h1>JobBot</h1>
    <p class="hero-sub">Upload your resume, get matched with the right opportunities, and generate tailored cover letters.</p>
    <div class="hero-tags">
        <span class="hero-tag">AI Matching</span>
        <span class="hero-tag">6+ Sources</span>
        <span class="hero-tag">Local + Remote</span>
        <span class="hero-tag">Cover Letters</span>
    </div>
</div></div>
""", unsafe_allow_html=True)

# ============================================
# STEPPER (numbers only, no icons/emojis)
# ============================================
profile = load_j(PF); matches = load_j(MF)
s1 = "done" if profile and profile.get("skills") else "active"
s2 = "done" if matches else ("active" if s1=="done" else "pending")
s3 = "done" if os.path.exists(LD) and os.listdir(LD) else ("active" if s2=="done" else "pending")
st.markdown(f"""
<div class="stepper">
    <div class="step {s1}"><div class="step-num">1</div><span>Profile</span></div>
    <div class="step-conn"></div>
    <div class="step {s2}"><div class="step-num">2</div><span>Find Jobs</span></div>
    <div class="step-conn"></div>
    <div class="step {s3}"><div class="step-num">3</div><span>Apply</span></div>
</div>
""", unsafe_allow_html=True)

# ============================================
# STEP 1: PROFILE
# ============================================
st.subheader("Step 1: Your Profile")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader("Upload your resume (PDF)", type=["pdf"], key="resume_upload")
with col2:
    if uploaded:
        if st.button("Parse Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing..."):
                try:
                    rp = os.path.join(DD,"resume.pdf")
                    with open(rp,"wb") as f: f.write(uploaded.getbuffer())
                    ex = load_j(PF)
                    profile = build_profile(rp, PF)
                    if ex:
                        for fld in ["country","state","experience","job_preference"]:
                            if fld not in profile and fld in ex: profile[fld]=ex[fld]
                    profile.setdefault("country",""); profile.setdefault("state","Any")
                    profile.setdefault("experience","3-6 years"); profile.setdefault("job_preference","Both (local + remote)")
                    save_j(PF, profile); st.success("Resume parsed!"); time.sleep(0.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

profile = load_j(PF)
if profile and profile.get("skills"):
    st.markdown("---")
    st.markdown(f"**{profile.get('name','Candidate')}**")
    if profile.get('headline'): st.caption(profile['headline'])
    skills = profile.get("skills",[])
    if skills:
        chips = "".join(f'<span class="sc">{s}</span>' for s in skills)
        st.markdown(f'<div class="skills-wrap">{chips}</div>', unsafe_allow_html=True)
        st.caption(f"{len(skills)} skills detected")
    cn = profile.get("country",""); sn = profile.get("state","")
    if cn and cn != "Remote Only":
        st.caption(f"Location: {cn}" + (f" / {sn}" if sn and sn != "Any" else ""))
    elif cn == "Remote Only": st.caption("Remote Only")
else:
    st.info("Upload your resume above, or create a profile manually below.")

# Manual edit — plain text label, NO emojis
with st.expander("Edit Profile Manually" if profile else "Create Profile Manually"):
    nm = st.text_input("Full Name", value=profile.get("name","") if profile else "", placeholder="e.g. Jane Doe")
    hl = st.text_input("Headline", value=profile.get("headline","") if profile else "", placeholder="e.g. Financial Analyst")
    sk = st.text_area("Skills (one per line)", value="\n".join(profile.get("skills",[])) if profile else "", height=150, placeholder="financial analysis\nM&A\nPower BI")

    lc1, lc2 = st.columns(2)
    with lc1:
        cc = profile.get("country","") if profile else ""
        co = list(COUNTRIES)
        if cc and cc not in co: co.append(cc)
        ci = st.selectbox("Country", options=["-- Select --"]+co,
            index=(co.index(cc)+1) if cc in co else 0)
        if ci == "-- Select --": ci = ""
    with lc2:
        sl = STATES.get(ci, ["Any"]); cs = profile.get("state","Any") if profile else "Any"
        if cs not in sl: cs = "Any"
        si = st.selectbox("State / City", options=sl, index=sl.index(cs) if cs in sl else 0)

    ec1, ec2 = st.columns(2)
    with ec1:
        EXP = ["0-1 years","1-3 years","3-6 years","6-10 years","10+ years"]
        ce = profile.get("experience","3-6 years") if profile else "3-6 years"
        if ce not in EXP: ce = "3-6 years"
        ei = st.selectbox("Experience", options=EXP, index=EXP.index(ce))
    with ec2:
        PREFS = ["Local jobs in my city","Remote jobs","Both (local + remote)"]
        cp = profile.get("job_preference","Both (local + remote)") if profile else "Both (local + remote)"
        if cp not in PREFS: cp = "Both (local + remote)"
        pi = st.selectbox("Job Preference", options=PREFS, index=PREFS.index(cp))

    if st.button("Save Profile", use_container_width=True):
        sklist = [s.strip() for s in sk.split("\n") if s.strip()]
        if not sklist and not nm: st.error("Enter at least a name or skills")
        else:
            ex = load_j(PF) or {}
            save_j(PF, {"name":nm or "Candidate","headline":hl,"skills":sklist,
                "country":ci,"state":si,"experience":ei,"job_preference":pi,
                "industry":ex.get("industry",""),"search_terms":ex.get("search_terms",[])})
            st.success("Profile saved!"); time.sleep(0.5); st.rerun()

# ============================================
# STEP 2: JOB MATCHING
# ============================================
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 2: Find Your Matches")

profile = load_j(PF)
ok = bool(profile and profile.get("skills"))

if not ok:
    st.warning("Complete your profile above to unlock job matching.")
else:
    # Use st.expander with plain text — NO emojis, NO special chars
    with st.expander("How does matching work?"):
        st.markdown("**3-phase pipeline:** Keyword Extraction, Local Scoring, then AI Ranking (Gemini 2.5 Flash)\n\n**Sources:** Google Jobs (Indeed, Naukri, Glassdoor, LinkedIn), Lever, Remotive, WeWorkRemotely, RemoteOK, Jobicy")

    with st.expander("Upload Custom Jobs (Optional)"):
        ju = st.file_uploader("Upload jobs.json", type=["json"], help="Use your own jobs file")
        if ju:
            try: jd=json.loads(ju.getvalue()); save_j(JF,jd); st.success(f"Loaded {len(jd)} jobs")
            except Exception as e: st.error(f"Invalid JSON: {e}")

    if st.session_state.get("_done"):
        st.success("Matching complete! Scroll down for results.")
        mdc = load_j(MF); mc = len(mdc) if isinstance(mdc,list) else 0
        us = profile.get("state","Any"); uc = profile.get("country","")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Re-run (Fresh)", use_container_width=True):
                st.session_state.pop("_done",None); st.session_state.pop("_pins",None)
                for fp in [JF,MF,CF]:
                    if os.path.exists(fp): os.remove(fp)
                if os.path.exists(LD):
                    for lf in os.listdir(LD): os.remove(os.path.join(LD,lf))
                st.rerun()
        with c2:
            if mc < 5 and us != "Any" and uc:
                if st.button(f"Expand to all of {uc}", type="primary", use_container_width=True):
                    pd = load_j(PF)
                    if pd: pd["state"]="Any"; save_j(PF,pd)
                    st.session_state.pop("_done",None)
                    for fp in [JF,MF,CF]:
                        if os.path.exists(fp): os.remove(fp)
                    st.rerun()
    elif st.session_state.get("_running"):
        st.warning("Matching in progress... usually 30-60 seconds.")
    else:
        country = profile.get("country",""); state = profile.get("state","")
        if country and country != "Remote Only":
            loc = f"**{state+', ' if state and state!='Any' else ''}{country}**"
        elif country == "Remote Only": loc = "**remote opportunities worldwide**"
        else: loc = "**relevant regions**"
        st.markdown(f"Scanning **6+ sources** (Google Jobs, Indeed, Naukri, Glassdoor, Lever, Remotive) focused on {loc}. All qualifying matches will be shown.")

        if st.button("Start Job Matching", type="primary", use_container_width=True):
            st.session_state["_running"] = True
            status = st.empty(); bar = st.progress(0, text="Starting..."); detail = st.empty(); logs = []
            stages = {"Starting":0,"Fetching":5,"Serper":20,"Remotive":25,"Lever":35,"Google":40,"SerpAPI":40,"Loaded":50,"Location":55,"Matching":60,"Phase 1":65,"Batch 1":70,"Batch 2":78,"Batch 3":85,"Threshold":95,"Done":100}
            def cb(msg):
                logs.append(msg); detail.code("\n".join(logs[-8:]),language=None)
                pct = max((p for k,p in stages.items() if k.lower() in msg.lower()), default=0)
                pct = max(pct, getattr(cb,'_mx',0)); cb._mx = pct
                bar.progress(min(pct,100)/100, text=msg[:80])
            cb._mx = 0
            try:
                status.info("Scanning sources and running AI matching...")
                result = run_auto_apply_pipeline(profile_file=PF,jobs_file=JF,matches_file=MF,cache_file=CF,log_file=LF,letters_dir=None,progress_callback=cb)
                bar.progress(1.0, text="Complete!")
                st.session_state["_done"] = True; st.session_state.pop("_running",None)
                if result and result.get("status")=="success": status.success(f"Found {result['matches']} matches from {result['total_scored']} jobs!")
                elif result and result.get("status")=="no_matches": status.warning("No strong matches. Try broadening skills.")
                else: status.error(f"Pipeline error: {result}")
                time.sleep(1); st.rerun()
            except Exception as e:
                st.session_state.pop("_running",None); bar.progress(1.0,text="Error")
                status.error(f"Error: {e}"); st.exception(e)

# ============================================
# STEP 3: RESULTS — all matches, sorted by recency, with pin + posted date
# ============================================
md = load_j(MF)

if isinstance(md, list) and md:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Parse timestamps
    for j in md:
        j["_ts"] = parse_ts(j)

    pinned = get_pinned()
    def sk(j):
        ts = j.get("_ts")
        return (0, -ts.timestamp()) if ts else (1, -j.get("match_score",0))
    pj = sorted([j for j in md if jkey(j) in pinned], key=sk)
    uj = sorted([j for j in md if jkey(j) not in pinned], key=sk)
    all_sorted = pj + uj

    scores = [j.get("match_score",0) for j in md]
    avg = sum(scores)/len(scores) if scores else 0
    letters = [f for f in os.listdir(LD) if f.endswith(".txt")] if os.path.exists(LD) else []

    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-val purple">{len(md)}</div><div class="stat-lbl">Matches</div></div>
        <div class="stat-card"><div class="stat-val coral">{avg:.0f}%</div><div class="stat-lbl">Avg Score</div></div>
        <div class="stat-card"><div class="stat-val emerald">{max(scores)}%</div><div class="stat-lbl">Top Score</div></div>
        <div class="stat-card"><div class="stat-val amber">{len(letters)}</div><div class="stat-lbl">Letters</div></div>
    </div>
    """, unsafe_allow_html=True)

    if letters:
        zc1,zc2 = st.columns([3,1])
        with zc1: st.subheader(f"All {len(md)} Matches")
        with zc2:
            st.download_button(f"Download {len(letters)} Letters", data=mk_zip(LD),
                file_name="jobbot_letters.zip", mime="application/zip", use_container_width=True)
    else:
        st.subheader(f"All {len(md)} Matches")
        st.caption("Click 'Generate Letter' on any job to create a cover letter.")

    if pinned:
        st.caption(f"{len(pj)} pinned at top | Sorted newest to oldest")
    else:
        st.caption("Sorted newest to oldest | Pin jobs to keep them at top")

    # ---- Job Cards ----
    for i, j in enumerate(all_sorted, 1):
        sc = j.get("match_score", 0)
        co = j.get("company", "Unknown")
        ti = j.get("title", "Unknown")
        src = j.get("source", "")
        sm = strip_html(j.get("summary",""))[:400]
        jk = jkey(j)
        ip = jk in pinned
        ts_rel, ts_full, ts_cls = fmt_ts(j.get("_ts"))

        # Build label — PLAIN TEXT ONLY (no emojis, no unicode arrows)
        parts = [f"#{i}"]
        if ip: parts.append("[PINNED]")
        parts.append(f"{co} -- {ti} ({sc}%)")
        if ts_rel: parts.append(f"| {ts_rel}")
        label = "  ".join(parts)

        with st.expander(label):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{ti}**")

                # Company + source badge + timestamp badge (HTML)
                info = f"**{co}**"
                if src: info += f' &nbsp; <span class="src-badge">{src}</span>'
                if ts_rel: info += f' &nbsp; <span class="ts-badge {ts_cls}">{ts_rel}</span>'
                if ip: info += ' &nbsp; <span class="pin-badge">PINNED</span>'
                st.markdown(info, unsafe_allow_html=True)

                # Posted date — ALWAYS show if available
                if ts_full:
                    st.caption(f"Posted: {ts_full}")

                # Location + experience
                jl = j.get("location","")
                if not jl:
                    for t in j.get("location_tags",[]):
                        if t: jl = t; break
                meta = []
                if jl: meta.append(f"Location: {jl}")
                em = re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?', j.get("summary","").lower())
                if em: meta.append(f"Exp: {em.group(0).strip()}")
                if meta: st.caption(" | ".join(meta))

                if sm: st.write(sm)

            with c2:
                bc = "score-excellent" if sc >= 75 else ("score-good" if sc >= 60 else "score-fair")
                st.markdown(f'<div style="text-align:center;margin-bottom:.5rem"><span class="score-badge {bc}">{sc}%</span></div>', unsafe_allow_html=True)
                if j.get("apply_url"):
                    st.link_button("Apply Now", j["apply_url"], use_container_width=True)
                if st.button("Unpin" if ip else "Pin to Top", key=f"p_{i}", use_container_width=True):
                    toggle_pin(jk); st.rerun()
                cl, cn = find_cl(co, ti)
                if not cl:
                    if st.button("Generate Letter", key=f"g_{i}", use_container_width=True):
                        with st.spinner("Writing..."):
                            try:
                                os.makedirs(LD, exist_ok=True)
                                generate_cover_letter(j, load_j(PF), LD)
                                st.rerun()
                            except Exception as e: st.error(f"Failed: {e}")

            cl, cn = find_cl(co, ti)
            if cl:
                st.markdown("---")
                st.markdown('<p class="cover-letter-label">Tailored Cover Letter</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="cover-letter-box">{cl}</div>', unsafe_allow_html=True)
                st.download_button("Download Letter", data=cl, file_name=cn or f"letter_{i}.txt",
                    mime="text/plain", key=f"d_{i}", use_container_width=True)

# ============================================
# FOOTER
# ============================================
st.markdown('<div class="footer">Built with Streamlit and Gemini 2.5 Flash | <a href="https://github.com" target="_blank">GitHub</a></div>', unsafe_allow_html=True)
