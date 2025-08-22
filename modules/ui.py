import streamlit as st

def hero(title: str, subtitle: str, badge: str=None):
    st.markdown(f"<div class='vg-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='vg-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
    if badge:
        st.markdown(f"<span class='badge'>{badge}</span>", unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)

def kpi_card(label: str, value: str, container=None):
    target = container if container is not None else st
    target.markdown(f\"\"\"
    <div class="vg-card">
      <div style="font-size:12px;opacity:.8;margin-bottom:6px;">{label}</div>
      <div style="font-size:28px;font-weight:700;">{value}</div>
    </div>
    \"\"\", unsafe_allow_html=True)

def scope_badge(scope: str):
    st.markdown(f"<span class='badge'>{scope}</span>", unsafe_allow_html=True)

def section_title(text: str):
    st.markdown(f"### {text}")

def success_toast(msg: str):
    st.toast(msg)

def warn_toast(msg: str):
    st.toast(msg)
