# ============================================================
# 💊 Pharma Retail Sales & Inventory Intelligence Dashboard
# ============================================================
# This Streamlit app demonstrates a realistic, end-to-end
# data analysis project combining Pandas (backend data logic)
# and Streamlit (interactive frontend).
#
# It’s written to be used in a LIVE CODING classroom setting.
# Each section is annotated with instructor comments explaining:
#   ✅ Common debugging issues
#   ✅ Key syntax insights
#   ✅ Data transformation logic

# Synthetic Data - .csv files
# sales.csv: ['sale_id', 'date_of_sale', 'Medicine', 'quantity_sold', 'unit_price', 'BRANCH', 'total']

# ============================================================

import pandas as pd
import streamlit as st
import plotly.express as px

# ------------------------------------------------------------
# 1️⃣ Streamlit Page Configuration
# ------------------------------------------------------------
# https://emojicombos.com/capsule
st.set_page_config(
    page_title="Pharma Retail Sales Dashboard",
    page_icon="💊",
    layout="wide"
)
st.title("💊 Pharma Retail Sales & Inventory Intelligence Dashboard")
st.markdown("Analyze sales performance, **inventory levels,** and supplier reliability in retail pharmacy chains.**")

# ------------------------------------------------------------
# 2️⃣ Data Ingestion (Reading Multiple CSVs)
# ------------------------------------------------------------
# We cache data loading so the app doesn’t reload files on every UI change.
@st.cache_data
def load_data():
    sales = pd.read_csv("data/sales.csv")
    products = pd.read_csv("data/products.csv")
    inventory = pd.read_csv("data/inventory.csv")
    suppliers = pd.read_csv("data/suppliers.csv")

    return sales, products, inventory, suppliers

# from csv to python dataframe objects
sales, products, inventory, suppliers = load_data()

# print("\n******************** Origianl data files: sales, products, inventroy, suppliers")
# print(sales.head())
# print(products.head())
# print(inventory.head())
# print(suppliers.head())

# ------------------------------------------------------------
# 3️⃣ Data Cleaning & Preparation
# ------------------------------------------------------------
# 🧠 Debugging Lesson: In real projects, column names are often inconsistent.
#   Example: “Date”, “date_of_sale”, “ Date ” → all mean the same thing.
#   We fix that by standardizing column names to lowercase and stripping spaces.

for df in [sales, products, inventory, suppliers]:
    df.columns = df.columns.str.strip().str.lower()

print(sales.columns)

# 🧩 Detect date column dynamically
date_col = "date_of_sale" if "date_of_sale" in sales.columns else "date"
if date_col not in sales.columns:
    st.error("⚠️ Date column not found in sales.csv! Please verify your CSV headers.")
    st.stop()

# Convert to datetime (with coercion of invalid values)
sales[date_col] = pd.to_datetime(sales[date_col], errors="coerce", dayfirst=True) # dayfirst=False (the default)

# Drop rows with invalid or missing dates
sales.dropna(subset=[date_col], inplace=True)

# Standardize medicine names (important for merging)
sales["medicine"] = sales["medicine"].astype(str).str.strip().str.title()
products["medicine"] = products["medicine"].astype(str).str.strip().str.title()

# Remove duplicates (another real-world data issue)
sales.drop_duplicates(inplace=True)

# Flat File Format [300 rows x 19 columns]
# Merge all datasets — this demonstrates Pandas relational joins
merged = sales.merge(products, on="medicine", how="left") #  7 + 6 - 1 = 12 columns
# print(merged.columns)
merged = merged.merge(inventory, on="medicine", how="left") # 12 + 5 - 1= 16 columns
# print(merged.columns)
merged = merged.merge(suppliers, on="supplier_id", how="left") # 16 + 4 - 1 = 19 columns
# print(merged.columns)

# print("\n******************** merged: sales + products + inventroy + suppilers")
# print(merged.head())

# Compute derived business metrics - 19 + 3 = 22 columns
merged["total_sale"] = merged["quantity_sold"] * merged["unit_price"]
merged["profit"] = merged["total_sale"] - (merged["cost_price"] * merged["quantity_sold"])
merged["stock_turnover"] = merged["quantity_sold"] / merged["stock_on_hand"].replace(0, pd.NA)

# Rename for consistency
merged.rename(columns={date_col: "date"}, inplace=True)

# Flat File Format [300 rows x 22 columns]
print("\n********************* Final merged - new columns: total_sale, profit, stock_turnover")
print(merged.columns)
print(merged.head())

# ------------------------------------------------------------
# 4️⃣ Sidebar Filters — Adding Interactivity
# ------------------------------------------------------------
# https://emojicombos.com/search
st.sidebar.header("🔍 Filter Your View")

# 🔧 Debugging Tip: Streamlit sliders don’t accept Pandas Timestamps.
#   They need Python’s datetime.date objects. We fix this by converting.

min_date = merged["date"].min().date()
max_date = merged["date"].max().date()

# Date range selector
date_range = st.sidebar.slider(
    "Select Date Range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date)
)

# Filter by date range
filtered = merged[
    (merged["date"].dt.date >= date_range[0]) &
    (merged["date"].dt.date <= date_range[1])
]

# print("\n********************* Filtered by date_range ", date_range)
# print(filtered.head())

# Category filter
catOptions=["All"] + sorted(filtered["category"].dropna().unique().tolist())

category = st.sidebar.selectbox(
    "Select Medicine Category",
    options=catOptions
)

if category != "All":
    filtered = filtered[filtered["category"] == category]

# print("\n********************* Filtered by category ", category)
# print(filtered.head())

# Branch filter
brOptions = ["All"] + sorted(filtered["branch"].dropna().unique().tolist())

branch = st.sidebar.selectbox(
    "Select Branch",
    options=brOptions
)

if branch != "All":
    filtered = filtered[filtered["branch"] == branch]

# print("\n********************* Filtered by branch ", branch)
# print(filtered.head())

# ------------------------------------------------------------
# 5️⃣ Key Performance Indicators (KPIs)
# ------------------------------------------------------------
# KPIs summarize business performance and are easy to explain visually.
total_sales = filtered["total_sale"].sum()
total_profit = filtered["profit"].sum()
avg_turnover = filtered["stock_turnover"].mean(skipna=True)
low_stock = (filtered["stock_on_hand"] < 50).sum()
#  default date format for Pandas when converting strings to datetime objects using pd.to_datetime()  is ISO format, which is YYYY-MM-DD.
# If your date strings are in a different format, such as DD/MM/YYYY, you need to explicitly specify the format argument in pd.to_datetime() to ensure correct parsing.
expiring = filtered[
    filtered["expiry_date"].notna() &
    (pd.to_datetime(filtered["expiry_date"], format='%d/%m/%Y') < pd.Timestamp.today() + pd.Timedelta(days=30))
].shape[0]

print("\n********************* KPIs from Filtered data : counters : total_sales, total_profit, avg_turnover, low_stock, expiring")
print( total_sales, total_profit, avg_turnover, low_stock, expiring)
print()

# https://emojicombos.com/dashboard
st.subheader("📊 Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Sales", f"${total_sales:,.0f}")
col2.metric("Total Profit", f"${total_profit:,.0f}")
col3.metric("Avg. Stock Turnover", f"{avg_turnover:.2f}")
col4.metric("Low Stock Items", f"{low_stock}")
col5.metric("Expiring Batches", f"{expiring}")

# ------------------------------------------------------------
# 6️⃣ Visualizations — Data Storytelling
# ------------------------------------------------------------
# https://emojicombos.com/dashboard
st.subheader("📈 Sales Analytics")

# Sales Trend Over Time (Line Chart)
sales_trend = filtered.groupby("date")["total_sale"].sum().reset_index()

fig1 = px.line(
    sales_trend,
    x="date",
    y="total_sale",
    title="Daily Sales Trend",
    markers=True
)

# st.plotly_chart(fig1, width='content')
st.plotly_chart(fig1, use_container_width=True)

# Top 10 Medicines by Sales (Bar Chart)
top_meds = (
    filtered.groupby("medicine")["total_sale"]
    .sum()
    .nlargest(10)
    .reset_index()
)
fig2 = px.bar(top_meds, x="medicine", y="total_sale", title="Top 10 Medicines by Sales")
st.plotly_chart(fig2, use_container_width=True)

# Sales Distribution by Category (Pie Chart)
category_sales = filtered.groupby("category")["total_sale"].sum().reset_index()
fig3 = px.pie(
    category_sales,
    names="category",
    values="total_sale",
    title="Sales Distribution by Category",
    hole=0.4
)
st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------------------
# 7️⃣ Tables & Alerts — Actionable Insights
# ------------------------------------------------------------
# https://emojicombos.com/inventory
st.subheader("📦 Inventory & Expiry Alerts")

# Low Stock Table
low_stock_df = filtered[filtered["stock_on_hand"] < 50][
    ["medicine", "category", "stock_on_hand", "supplier_name", "branch"]
]
st.write("### 🧾 Low Stock Medicines (Reorder Soon)") # https://emojicombos.com/out-of-stock
st.dataframe(low_stock_df, use_container_width=True)

# Expiring Soon Table
expiring_soon_df = filtered[
    filtered["expiry_date"].notna() &
    (pd.to_datetime(filtered["expiry_date"], format='%d/%m/%Y') < pd.Timestamp.today() + pd.Timedelta(days=30))
   
][["medicine", "category", "expiry_date", "supplier_name", "branch"]]
st.write("### ⚠️ Expiring Soon (Next 30 Days)") # https://emojicombos.com/warning
st.dataframe(expiring_soon_df, use_container_width=True)