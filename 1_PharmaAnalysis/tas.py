# ============================================================
# 📊 The Aesthetic Syndicate (TAS) Monthly Operating Report Dashboard
# ============================================================
# This Streamlit app analyzes TAS financial and operational metrics
# from the TAS_MOR.csv file, providing interactive visualizations
# and insights similar to the pharma dashboard structure.

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import re

# ------------------------------------------------------------
# 1️⃣ Streamlit Page Configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="TAS Monthly Operating Report Dashboard",
    page_icon="📊",
    layout="wide"
)
st.title("📊 The Aesthetic Syndicate - Monthly Operating Report Dashboard")
st.markdown("Analyze financial performance, operational metrics, and trends from the monthly operating report.")

# ------------------------------------------------------------
# 2️⃣ Data Ingestion & Parsing
# ------------------------------------------------------------
@st.cache_data
def load_tas_data():
    """
    Load and parse the TAS_MOR.csv file which has a complex structure
    with headers, financial metrics, and trended monthly data.
    """
    # Read the CSV file
    df_raw = pd.read_csv("data/TAS_MOR.csv", header=None)
    
    # Extract header row (row 6, index 6)
    header_row = df_raw.iloc[6].values
    
    # Find the column indices for key columns
    metric_col_idx = 2  # Metric column
    actual_col_idx = 3  # Actual (Sep-25)
    budget_col_idx = 4  # Budget
    prior_year_col_idx = 5  # Prior Year (Sep-24)
    delta_col_idx = 6  # % Delta vs Budget
    yoy_col_idx = 7  # YoY % Change
    
    # Extract trended data columns (starting from column 11, index 11)
    trended_start_idx = 11
    month_columns = header_row[trended_start_idx:].tolist()
    
    # Parse financial metrics (rows 9-25, index 9-25)
    financial_data = []
    kpi_data = []
    
    for idx in range(9, len(df_raw)):
        row = df_raw.iloc[idx]
        metric_name = str(row.iloc[metric_col_idx]).strip()
        
        # Skip empty rows or section headers
        if pd.isna(row.iloc[metric_col_idx]) or metric_name == '' or metric_name == 'nan':
            continue
        
        # Check if it's a section header
        if metric_name in ['Financials', 'KPIs * Note - "GAAP" Visits post Zenoti implementation.']:
            continue
        
        # Extract values
        actual_val = str(row.iloc[actual_col_idx]).strip() if pd.notna(row.iloc[actual_col_idx]) else None
        budget_val = str(row.iloc[budget_col_idx]).strip() if pd.notna(row.iloc[budget_col_idx]) else None
        prior_year_val = str(row.iloc[prior_year_col_idx]).strip() if pd.notna(row.iloc[prior_year_col_idx]) else None
        delta_val = str(row.iloc[delta_col_idx]).strip() if pd.notna(row.iloc[delta_col_idx]) else None
        yoy_val = str(row.iloc[yoy_col_idx]).strip() if pd.notna(row.iloc[yoy_col_idx]) else None
        
        # Extract trended data
        trended_values = []
        for col_idx in range(trended_start_idx, len(row)):
            val = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else None
            trended_values.append(val)
        
        # Determine if it's a KPI (rows 28-30)
        is_kpi = idx >= 27
        
        data_entry = {
            'metric': metric_name,
            'actual': actual_val,
            'budget': budget_val,
            'prior_year': prior_year_val,
            'delta_vs_budget': delta_val,
            'yoy_change': yoy_val,
            'is_kpi': is_kpi,
            'trended_data': trended_values
        }
        
        if is_kpi:
            kpi_data.append(data_entry)
        else:
            financial_data.append(data_entry)
    
    # Create DataFrames
    financial_df = pd.DataFrame(financial_data)
    kpi_df = pd.DataFrame(kpi_data)
    
    # Parse trended data into a separate DataFrame
    trended_df_list = []
    for idx, entry in enumerate(financial_data + kpi_data):
        metric = entry['metric']
        trended_values = entry['trended_data']
        
        for month_idx, month_name in enumerate(month_columns):
            if month_idx < len(trended_values) and trended_values[month_idx] and trended_values[month_idx] != 'nan':
                trended_df_list.append({
                    'metric': metric,
                    'month': month_name,
                    'value': trended_values[month_idx],
                    'is_kpi': entry['is_kpi']
                })
    
    trended_df = pd.DataFrame(trended_df_list)
    
    return financial_df, kpi_df, trended_df, month_columns

# Load data
financial_df, kpi_df, trended_df, month_columns = load_tas_data()

# Helper function to clean numeric values
def clean_numeric(value):
    """Remove $, commas, parentheses, and convert to float"""
    if pd.isna(value) or value == 'N/A' or value == 'nan':
        return None
    
    value_str = str(value).strip()
    # Remove $, commas, spaces
    value_str = value_str.replace('$', '').replace(',', '').replace(' ', '')
    
    # Handle negative values in parentheses
    is_negative = '(' in value_str and ')' in value_str
    value_str = value_str.replace('(', '').replace(')', '')
    
    # Remove % sign for percentage values
    is_percentage = '%' in value_str
    value_str = value_str.replace('%', '')
    
    try:
        num_val = float(value_str)
        if is_negative:
            num_val = -num_val
        if is_percentage:
            return num_val / 100 if num_val != 0 else 0
        return num_val
    except:
        return None

# Clean the financial and KPI dataframes
for col in ['actual', 'budget', 'prior_year']:
    financial_df[col + '_numeric'] = financial_df[col].apply(clean_numeric)
    kpi_df[col + '_numeric'] = kpi_df[col].apply(clean_numeric)

# Clean trended values
trended_df['value_numeric'] = trended_df['value'].apply(clean_numeric)

# ------------------------------------------------------------
# 3️⃣ Sidebar Filters
# ------------------------------------------------------------
st.sidebar.header("🔍 Filter Your View")

# Metric type filter
metric_type = st.sidebar.radio(
    "Select Metric Type",
    options=["All Metrics", "Financial Metrics", "KPIs Only"]
)

# Metric selector
if metric_type == "Financial Metrics":
    available_metrics = financial_df['metric'].unique().tolist()
elif metric_type == "KPIs Only":
    available_metrics = kpi_df['metric'].unique().tolist()
else:
    available_metrics = list(financial_df['metric'].unique()) + list(kpi_df['metric'].unique())

# Ensure selected metric is valid for current filter
metric_options = ["All"] + sorted(available_metrics)

# Use session state to maintain selection across filter changes
if 'selected_metric_state' not in st.session_state:
    st.session_state.selected_metric_state = "All"

# Check if current selection is still valid
if st.session_state.selected_metric_state not in metric_options:
    st.session_state.selected_metric_state = "All"

selected_metric = st.sidebar.selectbox(
    "Select Specific Metric",
    options=metric_options,
    index=metric_options.index(st.session_state.selected_metric_state) if st.session_state.selected_metric_state in metric_options else 0,
    key="metric_selectbox"
)

# Update session state
st.session_state.selected_metric_state = selected_metric

# Month filter for trended data
if len(month_columns) > 0:
    available_months = [m for m in month_columns if pd.notna(m) and str(m).strip() != '']
    selected_months = st.sidebar.multiselect(
        "Select Months for Trend Analysis",
        options=available_months,
        default=available_months
    )
else:
    selected_months = []

# ------------------------------------------------------------
# 4️⃣ Key Performance Indicators (KPIs)
# ------------------------------------------------------------
st.subheader("📊 Key Performance Indicators")

# Show active filters
filter_info = []
if metric_type != "All Metrics":
    filter_info.append(f"Type: {metric_type}")
if selected_metric != "All":
    filter_info.append(f"Metric: {selected_metric}")
if len(selected_months) < len(available_months) if len(available_months) > 0 else False:
    filter_info.append(f"Months: {len(selected_months)} selected")

if filter_info:
    st.info("🔍 Active Filters: " + " | ".join(filter_info))

# Filter data based on selections
display_financial = financial_df.copy()
display_kpi = kpi_df.copy()
display_trended = trended_df.copy()

# Apply metric type filter
if metric_type == "Financial Metrics":
    display_kpi = kpi_df.iloc[0:0].copy() if len(kpi_df) > 0 else pd.DataFrame(columns=kpi_df.columns)  # Empty but with same structure
elif metric_type == "KPIs Only":
    display_financial = financial_df.iloc[0:0].copy() if len(financial_df) > 0 else pd.DataFrame(columns=financial_df.columns)  # Empty but with same structure
# If "All Metrics", keep both

# Apply specific metric filter
if selected_metric != "All":
    if len(display_financial) > 0 and 'metric' in display_financial.columns:
        display_financial = display_financial[display_financial['metric'] == selected_metric]
    if len(display_kpi) > 0 and 'metric' in display_kpi.columns:
        display_kpi = display_kpi[display_kpi['metric'] == selected_metric]
    if len(display_trended) > 0 and 'metric' in display_trended.columns:
        display_trended = display_trended[display_trended['metric'] == selected_metric]

# Apply month filter
if len(selected_months) > 0 and len(display_trended) > 0 and 'month' in display_trended.columns:
    display_trended = display_trended[display_trended['month'].isin(selected_months)]

# Display key financial metrics (only if not filtering by specific metric or showing all)
if selected_metric == "All" and metric_type != "KPIs Only" and len(display_financial) > 0 and 'metric' in display_financial.columns:
    key_metrics = ['Net Revenue', 'Gross Profit', 'Clinic EBITDA', 'Net Income']
    key_metrics_data = display_financial[display_financial['metric'].isin(key_metrics)]
else:
    # Show selected metric(s) instead
    key_metrics_data = display_financial.copy() if len(display_financial) > 0 else pd.DataFrame()

if len(key_metrics_data) > 0:
    num_cols = min(len(key_metrics_data), 4)
    cols = st.columns(num_cols)
    
    for idx, (_, row) in enumerate(key_metrics_data.iterrows()):
        if idx >= num_cols:
            break
        metric_name = row['metric']
        actual = row['actual_numeric']
        delta = row['delta_vs_budget']
        
        with cols[idx]:
            if actual is not None:
                delta_display = f" ({delta})" if delta and delta != 'nan' else ""
                if 'Revenue' in metric_name or 'Profit' in metric_name or 'EBITDA' in metric_name or 'Income' in metric_name:
                    st.metric(metric_name, f"${actual:,.0f}", delta_display)
                else:
                    st.metric(metric_name, f"{actual:.2f}", delta_display)

# Display KPI metrics
if len(display_kpi) > 0 and 'metric' in display_kpi.columns:
    st.subheader("📈 Operational KPIs")
    kpi_cols = st.columns(len(display_kpi))
    
    for idx, (_, row) in enumerate(display_kpi.iterrows()):
        metric_name = row['metric']
        actual = row['actual_numeric']
        yoy = row['yoy_change']
        
        with kpi_cols[idx]:
            if actual is not None:
                yoy_display = f" ({yoy})" if yoy and yoy != 'nan' else ""
                if 'Revenue' in metric_name or 'Visit' in metric_name:
                    st.metric(metric_name, f"${actual:,.2f}", yoy_display)
                else:
                    st.metric(metric_name, f"{actual:,.0f}", yoy_display)

# ------------------------------------------------------------
# 5️⃣ Visualizations
# ------------------------------------------------------------
st.subheader("📈 Financial Analytics")

# Actual vs Budget vs Prior Year Comparison
if len(display_financial) > 0 and 'metric' in display_financial.columns:
    comparison_data = []
    for _, row in display_financial.iterrows():
        metric = row['metric']
        if row['actual_numeric'] is not None:
            comparison_data.append({'Metric': metric, 'Type': 'Actual', 'Value': row['actual_numeric']})
        if row['budget_numeric'] is not None:
            comparison_data.append({'Metric': metric, 'Type': 'Budget', 'Value': row['budget_numeric']})
        if row['prior_year_numeric'] is not None:
            comparison_data.append({'Metric': metric, 'Type': 'Prior Year', 'Value': row['prior_year_numeric']})
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Use filtered metrics instead of hardcoded list
        # Only filter out percentage metrics and very large outliers for better visualization
        if selected_metric == "All":
            # When showing all, filter to key metrics for clarity
            key_metrics_for_chart = ['Net Revenue', 'Gross Profit', 'Clinic EBITDA', 'Corporate OpEx']
            comparison_df_filtered = comparison_df[comparison_df['Metric'].isin(key_metrics_for_chart)]
        else:
            # When showing specific metric, show it
            comparison_df_filtered = comparison_df
        
        if len(comparison_df_filtered) > 0:
            fig1 = px.bar(
                comparison_df_filtered,
                x='Metric',
                y='Value',
                color='Type',
                barmode='group',
                title="Actual vs Budget vs Prior Year Comparison",
                labels={'Value': 'Amount ($)', 'Metric': 'Financial Metric'}
            )
            st.plotly_chart(fig1, use_container_width=True)

# Trended Data Visualization
if len(display_trended) > 0 and 'metric' in display_trended.columns:
    if len(selected_months) > 0:
        st.subheader("📅 Trended Data Over Time")
        
        # Filter trended data for selected metrics
        trend_metrics = display_trended['metric'].unique()
        
        # Show all filtered metrics (or limit if too many)
        max_metrics_to_show = 10 if selected_metric == "All" else len(trend_metrics)
        metrics_to_show = list(trend_metrics)[:max_metrics_to_show]
        
        # Create line chart for each metric
        for metric in metrics_to_show:
            metric_trend = display_trended[
                (display_trended['metric'] == metric) & 
                (display_trended['value_numeric'].notna())
            ].copy()
            
            if len(metric_trend) > 0:
                # Sort by month order
                month_order = {month: idx for idx, month in enumerate(available_months)}
                metric_trend['month_order'] = metric_trend['month'].map(month_order)
                metric_trend = metric_trend.sort_values('month_order')
                
                fig_trend = px.line(
                    metric_trend,
                    x='month',
                    y='value_numeric',
                    title=f"{metric} Trend Over Time",
                    markers=True
                )
                fig_trend.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Value"
                )
                st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("👆 Please select at least one month from the sidebar to view trended data.")

# Percentage Metrics Visualization
if len(display_financial) > 0 and 'metric' in display_financial.columns:
    percentage_metrics = display_financial[
        display_financial['metric'].str.contains('%', na=False)
    ]
else:
    percentage_metrics = pd.DataFrame()

if len(percentage_metrics) > 0:
    st.subheader("📊 Percentage Metrics")
    
    percentage_data = []
    for _, row in percentage_metrics.iterrows():
        if row['actual_numeric'] is not None:
            percentage_data.append({
                'Metric': row['metric'],
                'Actual (%)': row['actual_numeric'] * 100 if row['actual_numeric'] < 1 else row['actual_numeric']
            })
    
    if percentage_data:
        percentage_df = pd.DataFrame(percentage_data)
        fig_pct = px.bar(
            percentage_df,
            x='Metric',
            y='Actual (%)',
            title="Percentage Metrics (Actual)",
            labels={'Actual (%)': 'Percentage (%)'}
        )
        st.plotly_chart(fig_pct, use_container_width=True)

# ------------------------------------------------------------
# 6️⃣ Data Tables
# ------------------------------------------------------------
st.subheader("📋 Detailed Financial Metrics")

# Financial Metrics Table
if len(display_financial) > 0 and 'metric' in display_financial.columns:
    table_cols = ['metric', 'actual', 'budget', 'prior_year', 'delta_vs_budget', 'yoy_change']
    # Check if all columns exist
    existing_cols = [col for col in table_cols if col in display_financial.columns]
    if existing_cols:
        financial_table = display_financial[existing_cols].copy()
        financial_table.columns = ['Metric', 'Actual (Sep-25)', 'Budget', 'Prior Year (Sep-24)', 'Delta vs Budget', 'YoY Change'][:len(existing_cols)]
        st.dataframe(financial_table, use_container_width=True, hide_index=True)
elif metric_type != "KPIs Only":
    st.info("No financial metrics match the selected filters. Try adjusting your filter selections.")

# KPI Table
if len(display_kpi) > 0 and 'metric' in display_kpi.columns:
    st.subheader("📋 Operational KPIs")
    kpi_cols = ['metric', 'actual', 'prior_year', 'yoy_change']
    existing_kpi_cols = [col for col in kpi_cols if col in display_kpi.columns]
    if existing_kpi_cols:
        kpi_table = display_kpi[existing_kpi_cols].copy()
        kpi_table.columns = ['Metric', 'Actual (Sep-25)', 'Prior Year (Sep-24)', 'YoY Change'][:len(existing_kpi_cols)]
        st.dataframe(kpi_table, use_container_width=True, hide_index=True)
elif metric_type != "Financial Metrics":
    st.info("No KPIs match the selected filters. Try adjusting your filter selections.")

# Trended Data Table
if len(display_trended) > 0:
    st.subheader("📅 Monthly Trended Data")
    trended_table = display_trended[display_trended['value_numeric'].notna()].copy()
    if len(trended_table) > 0:
        pivot_trended = trended_table.pivot_table(
            index='metric',
            columns='month',
            values='value_numeric',
            aggfunc='first'
        )
        st.dataframe(pivot_trended, use_container_width=True)
    else:
        st.info("No trended data available for the selected filters.")
else:
    if selected_metric != "All" or metric_type != "All Metrics":
        st.info("No trended data available for the selected filters.")

