import pandas as pd
import numpy as np

# ── Read source files ──────────────────────────────────────────────
xls = pd.ExcelFile("business case copia.xlsx")
transactions_raw = pd.read_excel(xls, "transactions")
products_raw = pd.read_excel(xls, "products")
portfolios_raw = pd.read_excel(xls, "portfolios")
fx_raw = pd.read_csv("fx copia.csv")
prices_raw = pd.read_csv("prices.csv", sep=";")

summary = []

# ── 1. clean_transactions ──────────────────────────────────────────
df = transactions_raw.copy()
input_rows = len(df)

df["transaction-code"] = df["transaction-code"].astype(str).str.strip().str.upper()
df["portfolio-code"] = df["portfolio-code"].astype(str).str.strip().str.upper()
df["product-code"] = df["product-code"].astype(str).str.strip().str.upper()
df["transaction-quantity"] = pd.to_numeric(df["transaction-quantity"], errors="coerce")
df["transaction-price"] = pd.to_numeric(df["transaction-price"], errors="coerce")
df["transaction-date"] = pd.to_datetime(df["transaction-date"], errors="coerce")

# Replace transaction-price null or 0 with 1
df["transaction-price"] = df["transaction-price"].replace(0, np.nan).fillna(1)

# Derived columns
df["transaction-direction"] = np.where(
    df["transaction-quantity"] > 0, "BUY",
    np.where(df["transaction-quantity"] < 0, "SELL", "NEUTRAL")
)
df["source-system"] = np.where(
    df["transaction-code"].str.startswith("TR-"), "CURRENT", "LEGACY"
)

# Replace stringified 'NAN' back to real NaN for null check
for col in ["transaction-code", "portfolio-code", "product-code"]:
    df[col] = df[col].replace("NAN", np.nan)

df = df.dropna(subset=["transaction-code", "portfolio-code", "product-code", "transaction-date"])

df.to_csv("clean_transactions.csv", index=False)
summary.append(("transactions", input_rows, len(df), list(df.columns)))

# ── 2. clean_products ─────────────────────────────────────────────
df = products_raw.copy()
input_rows = len(df)

text_cols = ["product-code", "product-type", "product-currency", "product-issuer-code"]
for col in text_cols:
    df[col] = df[col].astype(str).str.strip().str.upper()
    df[col] = df[col].replace("NAN", np.nan)

df["loan-property-value-ratio"] = pd.to_numeric(df["loan-property-value-ratio"], errors="coerce")

df = df.dropna(subset=["product-code", "product-type", "product-issuer-code"])
df = df.drop_duplicates(subset="product-code", keep="first")

df.to_csv("clean_products.csv", index=False)
summary.append(("products", input_rows, len(df), list(df.columns)))

# ── 3. clean_portfolios ───────────────────────────────────────────
df = portfolios_raw.copy()
input_rows = len(df)

df["portfolio-code"] = df["portfolio-code"].astype(str).str.strip().str.upper()
df["portfolio-currency"] = df["portfolio-currency"].astype(str).str.strip().str.upper()

for col in df.columns:
    df[col] = df[col].replace("NAN", np.nan)

df = df.dropna()
df = df.drop_duplicates(subset="portfolio-code", keep="first")

df.to_csv("clean_portfolios.csv", index=False)
summary.append(("portfolios", input_rows, len(df), list(df.columns)))

# ── 4. clean_fx ────────────────────────────────────────────────────
df = fx_raw.copy()
input_rows = len(df)

df["price-date"] = pd.to_datetime(df["price-date"], format="%d.%m.%Y", errors="coerce")
df["EURUSD"] = pd.to_numeric(df["EURUSD"], errors="coerce")

# Fill down null EURUSD values
df["EURUSD"] = df["EURUSD"].ffill()

df = df.dropna(subset=["price-date", "EURUSD"])
df = df.drop_duplicates(subset="price-date", keep="first")

df.to_csv("clean_fx.csv", index=False)
summary.append(("fx", input_rows, len(df), list(df.columns)))

# ── 5. clean_prices ────────────────────────────────────────────────
df = prices_raw.copy()
input_rows = len(df)

df["price-date"] = pd.to_datetime(df["price-date"], format="%d.%m.%Y", errors="coerce")
df["P1-EUR"] = pd.to_numeric(df["P1-EUR"], errors="coerce")
df["P2-USD"] = pd.to_numeric(df["P2-USD"], errors="coerce")

# Replace P2-USD zero with null
df["P2-USD"] = df["P2-USD"].replace(0, np.nan)

df = df.dropna(subset=["price-date", "P1-EUR"])
df = df.drop_duplicates(subset="price-date", keep="first")

df.to_csv("clean_prices.csv", index=False)
summary.append(("prices", input_rows, len(df), list(df.columns)))

# ── Summary ─────────────────────────────────────────────────────────
print(f"\n{'Table':<22} {'Input':>8} {'Output':>8}  Columns")
print("-" * 80)
for name, inp, out, cols in summary:
    print(f"{name:<22} {inp:>8} {out:>8}  {', '.join(cols)}")
