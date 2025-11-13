import pandas as pd

# For checking the version of pandas installed
print("Pandas version:", pd.__version__)


# -----------------------------------------------
# Data Ingestion (Reading Multiple CSV Files)
# -----------------------------------------------
def load_data():
    sales = pd.read_csv('data/sales.csv')
    inventory = pd.read_csv('data/inventory.csv')
    products = pd.read_csv('data/products.csv')
    suppliers = pd.read_csv('data/suppliers.csv')
    
    return (sales, inventory, products, suppliers)


sales, inventory, products, suppliers = load_data()

# -----------------------------------------------
# Data Cleaning and Preparation
# -----------------------------------------------
for df in [sales, inventory, products, suppliers]:
    df.columns = df.columns.str.strip().str.lower()
    
# ensure date column exists
# date_col = "date_of_sale"
date_col = "date_of_sale" if "date_of_sale" in sales.columns else "date"
if date_col not in sales.columns:
    print("Date should be recorded")
    exit()
    
# convert to datetime (with coercing invalid values)
sales[date_col] = pd.to_datetime(sales[date_col], errors='coerce', dayfirst=True)

# drop roww with invalid or missing dates
sales.dropna(subset=[date_col], inplace=True)

# standarize medicin names (important fro merging)
sales['medicine'] = sales['medicine'].astype(str).str.strip().str.title()
products['medicine'] = products['medicine'].astype(str).str.strip().str.title()
products['sales'] = sales['medicine'].astype(str).str.strip().str.title()

# remove duplicates
sales.drop_duplicates(inplace=True)

# Flat file format
# Merge all dataset - pandas relations joins
merged = sales.merge(products, on='medicine', how='left')
merged = merged.merge(inventory, on='medicine', how='left')
merged = merged.merge(suppliers, on='supplier_id', how='left')

print(merged.head())

