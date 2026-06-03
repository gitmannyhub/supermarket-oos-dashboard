# ============================================================
# Focal Systems OOS Dashboard
# Author: Mani
# Database: interview_db (MySQL local)
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Focal Systems OOS Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# DATABASE CONNECTION
# ============================================================
@st.cache_resource
def get_engine():
    return create_engine("mysql+pymysql://root@127.0.0.1/interview_db")

@st.cache_data
def run_query(sql):
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn)

# ============================================================
# SQL QUERIES
# ============================================================

SQL_EXECUTIVE_SUMMARY = """
WITH OOS_DATA AS (
    SELECT
        product_id,
        COUNT(DISTINCT oos_id)                                           AS total_oos_events,
        COUNT(DISTINCT date)                                             AS distinct_oos_days,
        ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 1)      AS avg_duration_mins,
        ROUND(SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60, 1) AS total_oos_hours
    FROM out_of_stocks
    WHERE stage = 'valid'
    GROUP BY product_id
),
REV_DATA AS (
    SELECT
        product_id,
        ROUND(AVG(price * sales_volume), 2)      AS avg_daily_revenue,
        ROUND(AVG(price * sales_volume) / 15, 2) AS avg_hourly_revenue
    FROM product_sales_records
    GROUP BY product_id
),
RESOLUTION_DATA AS (
    SELECT
        o.product_id,
        ROUND(SUM(CASE WHEN at.action_taken = 'FILLED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)                         AS fill_rate_pct,
        ROUND(SUM(CASE WHEN at.action_taken = 'FILLED' AND at.is_algo_fill = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS human_fill_pct,
        ROUND(SUM(CASE WHEN at.action_taken = 'CYCLE_COUNT' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)                   AS cycle_count_pct
    FROM action_tasks at
    JOIN out_of_stocks o ON at.oos_id = o.oos_id
    WHERE o.stage = 'valid'
    GROUP BY o.product_id
)
SELECT
    o.product_id,
    o.total_oos_events,
    o.distinct_oos_days,
    o.avg_duration_mins,
    o.total_oos_hours,
    r.avg_daily_revenue,
    ROUND(r.avg_hourly_revenue * o.total_oos_hours, 2) AS estimated_lost_revenue,
    res.fill_rate_pct,
    res.human_fill_pct,
    res.cycle_count_pct,
    CASE
        WHEN ROUND(r.avg_hourly_revenue * o.total_oos_hours, 2) > 1000 THEN 'HIGH RISK'
        WHEN ROUND(r.avg_hourly_revenue * o.total_oos_hours, 2) >= 200 THEN 'MEDIUM RISK'
        ELSE 'LOW RISK'
    END AS risk_flag
FROM OOS_DATA o
JOIN REV_DATA r ON o.product_id = r.product_id
JOIN RESOLUTION_DATA res ON o.product_id = res.product_id
ORDER BY estimated_lost_revenue DESC
"""

SQL_OOS_DURATION = """
SELECT
    product_id,
    COUNT(*) AS total_oos_events,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 1) AS avg_duration_mins,
    MAX(TIMESTAMPDIFF(MINUTE, start_time, end_time)) AS max_duration_mins,
    MIN(TIMESTAMPDIFF(MINUTE, start_time, end_time)) AS min_duration_mins
FROM out_of_stocks
WHERE stage = 'valid'
GROUP BY product_id
HAVING COUNT(*) > 5
ORDER BY avg_duration_mins DESC
"""

SQL_RESOLUTION = """
SELECT
    CASE
        WHEN is_algo_fill = 1 THEN 'Algo Fill'
        WHEN action_taken = 'FILLED' THEN 'Human Fill'
        ELSE 'Cycle Count'
    END AS resolution_type,
    COUNT(DISTINCT oos.oos_id) AS total_events,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 1) AS avg_duration_mins,
    ROUND(SUM(CASE WHEN action_taken = 'FILLED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_resolved,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, actioned_at)), 1) AS avg_response_mins
FROM action_tasks act
JOIN out_of_stocks oos ON oos.oos_id = act.oos_id
WHERE oos.stage = 'valid'
GROUP BY resolution_type
ORDER BY total_events DESC
"""

SQL_USER_PERFORMANCE = """
SELECT
    user_id,
    COUNT(*) AS total_tasks,
    SUM(CASE WHEN action_taken = 'FILLED' THEN 1 ELSE 0 END) AS filled_count,
    SUM(CASE WHEN action_taken = 'CYCLE_COUNT' THEN 1 ELSE 0 END) AS cycle_count_count,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, actioned_at)), 1) AS avg_response_mins
FROM action_tasks acts
JOIN out_of_stocks oos ON acts.oos_id = oos.oos_id
WHERE stage = 'valid'
AND is_algo_fill = 0
AND user_id IS NOT NULL
GROUP BY user_id
ORDER BY avg_response_mins
"""

SQL_CYCLE_COUNT_RATE = """
SELECT
    product_id,
    SUM(CASE WHEN action_taken = 'FILLED' THEN 1 ELSE 0 END) AS filled_count,
    SUM(CASE WHEN action_taken = 'CYCLE_COUNT' THEN 1 ELSE 0 END) AS cycle_count,
    ROUND(SUM(CASE WHEN action_taken = 'CYCLE_COUNT' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS cycle_count_pct
FROM action_tasks acts
JOIN out_of_stocks oos ON acts.oos_id = oos.oos_id
WHERE stage = 'valid'
AND is_algo_fill = 0
GROUP BY product_id
HAVING cycle_count > 0
ORDER BY cycle_count_pct DESC
LIMIT 10
"""

SQL_DAY_OF_WEEK = """
SELECT
    DAYNAME(CONVERT_TZ(start_time, 'UTC', 'US/Eastern')) AS day_of_week,
    COUNT(*) AS total_oos_events,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 1) AS avg_duration_mins
FROM out_of_stocks
WHERE stage = 'valid'
GROUP BY day_of_week
ORDER BY FIELD(day_of_week, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
"""

SQL_INVENTORY_AT_OOS = """
WITH oos_data AS (
    SELECT oos_id, product_id, date AS oos_date,
    CONVERT_TZ(start_time, 'UTC', 'US/Eastern') AS oos_start_local,
    start_time
    FROM out_of_stocks WHERE stage = 'valid'
),
last_inv_before_oos AS (
    SELECT o.oos_id, o.product_id, MAX(pih.created_at) AS last_inv_time
    FROM oos_data o
    JOIN product_inventory_levels pil ON o.product_id = pil.product_id
    JOIN product_inventory_history pih ON pil.inventory_level_id = pih.inventory_level_id
    WHERE pih.created_at < o.start_time
    GROUP BY o.oos_id, o.product_id
)
SELECT
    o.oos_id,
    o.product_id,
    o.oos_date,
    o.oos_start_local,
    pih.inventory_level AS inventory_level_before_oos
FROM last_inv_before_oos li
JOIN oos_data o ON li.oos_id = o.oos_id
JOIN product_inventory_levels pil ON li.product_id = pil.product_id
JOIN product_inventory_history pih
    ON pil.inventory_level_id = pih.inventory_level_id
    AND pih.created_at = li.last_inv_time
ORDER BY o.oos_date
LIMIT 20
"""

SQL_LOST_REVENUE = """
WITH OOS_DATA AS (
    SELECT product_id,
    COUNT(*) AS total_oos_events,
    ROUND(SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60, 1) AS total_oos_hours
    FROM out_of_stocks WHERE stage = 'valid'
    GROUP BY product_id
),
REV_DATA AS (
    SELECT product_id,
    ROUND(AVG(price * sales_volume), 2) AS avg_daily_revenue,
    ROUND(AVG(price * sales_volume) / 15, 2) AS avg_hourly_revenue
    FROM product_sales_records
    GROUP BY product_id
)
SELECT
    o.product_id,
    o.total_oos_events,
    o.total_oos_hours,
    r.avg_daily_revenue,
    r.avg_hourly_revenue,
    ROUND(r.avg_hourly_revenue * o.total_oos_hours, 2) AS estimated_lost_revenue
FROM OOS_DATA o
JOIN REV_DATA r ON o.product_id = r.product_id
ORDER BY estimated_lost_revenue DESC
"""

SQL_CHRONIC_OOS = """
WITH OOS_DATA AS (
    SELECT product_id,
    COUNT(DISTINCT date)                                             AS distinct_oos_days,
    COUNT(DISTINCT oos_id)                                          AS total_oos_events,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 1)     AS avg_duration_mins,
    ROUND(SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60, 1) AS total_oos_hours
    FROM out_of_stocks WHERE stage = 'valid'
    GROUP BY product_id
    HAVING COUNT(DISTINCT date) > 30
),
REV_DATA AS (
    SELECT product_id,
    ROUND(AVG(price * sales_volume) / 15, 2) AS avg_hourly_revenue
    FROM product_sales_records
    GROUP BY product_id
)
SELECT
    o.product_id,
    o.distinct_oos_days,
    o.total_oos_events,
    o.avg_duration_mins,
    ROUND(r.avg_hourly_revenue * o.total_oos_hours, 2) AS estimated_lost_revenue
FROM OOS_DATA o
JOIN REV_DATA r ON o.product_id = r.product_id
ORDER BY distinct_oos_days DESC
"""

# ============================================================
# APP HEADER
# ============================================================
st.title("📊 Focal Systems -- OOS Analytics Dashboard")
st.markdown("**Store 101 | US/Eastern | Data: May 2025 -- Apr 2026**")
st.divider()

# ============================================================
# TABS
# ============================================================
tabs = st.tabs([
    "📋 Executive Summary",
    "⏱ OOS Duration",
    "🔄 Resolution Analysis",
    "👤 User Performance",
    "🔁 Cycle Count Rate",
    "📅 OOS by Day",
    "📦 Inventory at OOS",
    "💰 Lost Revenue",
    "🚨 Chronic OOS"
])

# ============================================================
# TAB 1 -- EXECUTIVE SUMMARY
# ============================================================
with tabs[0]:
    st.header("📋 Executive Summary")

    st.info("""
    **Key Findings:**
    - Product **10140** is the highest risk -- 324 OOS events, £17,319 estimated lost revenue
    - Product **10031** is 2nd highest -- 314 OOS events, £6,181 estimated lost revenue
    - Products flagged as **HIGH RISK** have lost over £1,000 in estimated revenue
    - The top 5 chronic OOS products account for the majority of total revenue loss
    """)

    df = run_query(SQL_EXECUTIVE_SUMMARY)

    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products with OOS", len(df))
    col2.metric("High Risk Products", len(df[df['risk_flag'] == 'HIGH RISK']))
    col3.metric("Total Est. Lost Revenue", f"£{df['estimated_lost_revenue'].sum():,.0f}")
    col4.metric("Avg Fill Rate", f"{df['fill_rate_pct'].mean():.1f}%")

    st.divider()

    # Risk flag filter
    risk_filter = st.selectbox("Filter by Risk", ["All", "HIGH RISK", "MEDIUM RISK", "LOW RISK"])
    if risk_filter != "All":
        df = df[df['risk_flag'] == risk_filter]

    # Chart
    fig = px.bar(
        df.head(15),
        x='product_id',
        y='estimated_lost_revenue',
        color='risk_flag',
        color_discrete_map={
            'HIGH RISK': '#e74c3c',
            'MEDIUM RISK': '#f39c12',
            'LOW RISK': '#2ecc71'
        },
        title="Top 15 Products by Estimated Lost Revenue",
        labels={'estimated_lost_revenue': 'Est. Lost Revenue (£)', 'product_id': 'Product ID'}
    )
    fig.update_layout(xaxis_type='category')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_EXECUTIVE_SUMMARY, language='sql')

# ============================================================
# TAB 2 -- OOS DURATION
# ============================================================
with tabs[1]:
    st.header("⏱ OOS Duration by Product")

    st.info("""
    **Key Findings:**
    - Product **10091** has the worst avg OOS duration at **192.6 mins** (over 3 hours!)
    - Product **10076** averages **165 mins** per OOS event
    - Product **10140** has a **negative min duration (-12 mins)** -- data quality issue worth investigating
    - Only products with more than 5 OOS events are included
    """)

    df = run_query(SQL_OOS_DURATION)

    fig = px.bar(
        df.head(15),
        x='product_id',
        y='avg_duration_mins',
        title="Top 15 Products by Avg OOS Duration (mins)",
        labels={'avg_duration_mins': 'Avg Duration (mins)', 'product_id': 'Product ID'},
        color='avg_duration_mins',
        color_continuous_scale='Reds'
    )
    fig.update_layout(xaxis_type='category')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_OOS_DURATION, language='sql')

# ============================================================
# TAB 3 -- RESOLUTION ANALYSIS
# ============================================================
with tabs[2]:
    st.header("🔄 Resolution Analysis")

    st.info("""
    **Key Findings:**
    - **68.7%** of OOS events resolved by human FILLED
    - **20.8%** resolved algorithmically (algo fill) -- no human intervention
    - **10.5%** ended in CYCLE_COUNT -- no stock found anywhere
    - Algo fills paradoxically take **longer (192.2 mins)** vs human fills (117.8 mins)
      because algo detection waits for natural shelf recovery
    - CYCLE_COUNT has **0% resolution** -- stock could not be found
    """)

    df = run_query(SQL_RESOLUTION)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            df,
            values='total_events',
            names='resolution_type',
            title="OOS Events by Resolution Type",
            color_discrete_sequence=['#2ecc71', '#3498db', '#e74c3c']
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df,
            x='resolution_type',
            y='avg_duration_mins',
            title="Avg OOS Duration by Resolution Type (mins)",
            labels={'avg_duration_mins': 'Avg Duration (mins)', 'resolution_type': 'Resolution Type'},
            color='resolution_type',
            color_discrete_sequence=['#2ecc71', '#3498db', '#e74c3c']
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_RESOLUTION, language='sql')

# ============================================================
# TAB 4 -- USER PERFORMANCE
# ============================================================
with tabs[3]:
    st.header("👤 User Performance")

    st.info("""
    **Key Findings:**
    - **User 502** is the fastest responder at **114 mins avg** with 399 tasks
    - **User 503** is the slowest at **127.3 mins avg**
    - All 4 users handle similar workloads (370-399 tasks each)
    - **User 501** has the highest FILLED count (348) -- most successful at finding stock
    - Only human tasks included (algo fills excluded)
    """)

    df = run_query(SQL_USER_PERFORMANCE)
    df['user_id'] = df['user_id'].astype(str)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df,
            x='user_id',
            y='avg_response_mins',
            title="Avg Response Time by User (mins)",
            labels={'avg_response_mins': 'Avg Response (mins)', 'user_id': 'User ID'},
            color='avg_response_mins',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df,
            x='user_id',
            y=['filled_count', 'cycle_count_count'],
            title="Filled vs Cycle Count by User",
            labels={'value': 'Count', 'user_id': 'User ID'},
            barmode='group',
            color_discrete_map={
                'filled_count': '#2ecc71',
                'cycle_count_count': '#e74c3c'
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_USER_PERFORMANCE, language='sql')

# ============================================================
# TAB 5 -- CYCLE COUNT RATE
# ============================================================
with tabs[4]:
    st.header("🔁 Products with Highest Cycle Count Rate")

    st.info("""
    **Key Findings:**
    - **Product 10033** was cycle counted **66.7%** of the time -- most problematic product
    - **Products 10096 and 10028** at 50% cycle count rate
    - A high cycle count rate suggests **systemic inventory issues** for these products
    - Stock is consistently unavailable even in back rooms or alternate locations
    - Only top 10 products shown
    """)

    df = run_query(SQL_CYCLE_COUNT_RATE)
    df['product_id'] = df['product_id'].astype(str)

    fig = px.bar(
        df,
        x='product_id',
        y='cycle_count_pct',
        title="Top 10 Products by Cycle Count Rate (%)",
        labels={'cycle_count_pct': 'Cycle Count Rate (%)', 'product_id': 'Product ID'},
        color='cycle_count_pct',
        color_continuous_scale='Oranges'
    )
    fig.update_layout(xaxis_type='category')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_CYCLE_COUNT_RATE, language='sql')

# ============================================================
# TAB 6 -- OOS BY DAY OF WEEK
# ============================================================
with tabs[5]:
    st.header("📅 OOS Events by Day of Week")

    st.info("""
    **Key Findings:**
    - **Tuesday** has the most OOS events (315) -- busiest day for stock issues
    - **Saturday** is the slowest to resolve (170.6 mins avg) -- likely weekend staffing levels
    - **Thursday** is the fastest to resolve (144.4 mins avg)
    - Distribution is fairly even across all days (272-315 events per day)
    - All times converted to US/Eastern local time
    """)

    df = run_query(SQL_DAY_OF_WEEK)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df,
            x='day_of_week',
            y='total_oos_events',
            title="Total OOS Events by Day of Week",
            labels={'total_oos_events': 'Total OOS Events', 'day_of_week': 'Day'},
            color='total_oos_events',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df,
            x='day_of_week',
            y='avg_duration_mins',
            title="Avg OOS Duration by Day of Week (mins)",
            labels={'avg_duration_mins': 'Avg Duration (mins)', 'day_of_week': 'Day'},
            color='avg_duration_mins',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_DAY_OF_WEEK, language='sql')

# ============================================================
# TAB 7 -- INVENTORY AT OOS
# ============================================================
with tabs[6]:
    st.header("📦 Inventory Level at Time of OOS")

    st.info("""
    **Key Findings:**
    - Many products go OOS with **0 inventory** -- expected behaviour
    - **Product 10127** shows **negative inventory (-2)** before OOS detected -- data quality issue
    - Camera detection sometimes **lags behind** actual stock depletion
    - Some products show inventory > 0 when OOS triggered -- suggests misplaced stock
    - Limited to 20 most recent OOS events for performance
    """)

    df = run_query(SQL_INVENTORY_AT_OOS)

    fig = px.bar(
        df,
        x='oos_id',
        y='inventory_level_before_oos',
        color='inventory_level_before_oos',
        title="Inventory Level Before OOS Event",
        labels={
            'inventory_level_before_oos': 'Inventory Level',
            'oos_id': 'OOS Event ID'
        },
        color_continuous_scale='RdYlGn'
    )
    fig.update_layout(xaxis_type='category')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_INVENTORY_AT_OOS, language='sql')

# ============================================================
# TAB 8 -- LOST REVENUE
# ============================================================
with tabs[7]:
    st.header("💰 Estimated Lost Revenue Due to OOS")

    st.info("""
    **Key Findings:**
    - **Product 10140** leads with **£17,319** estimated lost revenue across 857 OOS hours
    - **Product 10031** second at **£6,181** across 883 OOS hours
    - Top 5 products account for over **£30,000** in combined lost revenue
    - Lost revenue = avg hourly revenue × total OOS hours (store open 15 hrs/day)
    - This is a conservative estimate -- actual impact may be higher due to customer churn
    """)

    df = run_query(SQL_LOST_REVENUE)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Est. Lost Revenue", f"£{df['estimated_lost_revenue'].sum():,.0f}")
    col2.metric("Most Affected Product", str(df.iloc[0]['product_id']))
    col3.metric("Max Single Product Loss", f"£{df.iloc[0]['estimated_lost_revenue']:,.0f}")

    st.divider()

    fig = px.bar(
        df.head(15),
        x='product_id',
        y='estimated_lost_revenue',
        title="Top 15 Products by Estimated Lost Revenue (£)",
        labels={
            'estimated_lost_revenue': 'Est. Lost Revenue (£)',
            'product_id': 'Product ID'
        },
        color='estimated_lost_revenue',
        color_continuous_scale='Reds'
    )
    fig.update_layout(xaxis_type='category')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_LOST_REVENUE, language='sql')

# ============================================================
# TAB 9 -- CHRONIC OOS
# ============================================================
with tabs[8]:
    st.header("🚨 Chronic OOS Products")

    st.info("""
    **Key Findings:**
    - Only **12 products** went OOS on more than 30 distinct days -- these are chronic offenders
    - **Product 10140** went OOS on the most distinct days with highest lost revenue
    - **Product 10031** has the most total OOS events (314) across distinct days
    - Chronic OOS suggests deeper supply chain or inventory management issues
    - These products should be prioritised for operational review
    """)

    df = run_query(SQL_CHRONIC_OOS)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df,
            x='product_id',
            y='distinct_oos_days',
            title="Distinct OOS Days per Product",
            labels={'distinct_oos_days': 'Distinct OOS Days', 'product_id': 'Product ID'},
            color='distinct_oos_days',
            color_continuous_scale='Oranges'
        )
        fig.update_layout(xaxis_type='category')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            df,
            x='distinct_oos_days',
            y='estimated_lost_revenue',
            size='total_oos_events',
            text='product_id',
            title="OOS Days vs Lost Revenue (bubble = total events)",
            labels={
                'distinct_oos_days': 'Distinct OOS Days',
                'estimated_lost_revenue': 'Est. Lost Revenue (£)'
            },
            color='estimated_lost_revenue',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 View SQL Query"):
        st.code(SQL_CHRONIC_OOS, language='sql')

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.markdown("""
<div style='text-align: center; color: grey;'>
    Focal Systems OOS Dashboard | Built with Streamlit + MySQL | Mani
</div>
""", unsafe_allow_html=True)