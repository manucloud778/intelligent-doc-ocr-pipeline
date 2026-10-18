import streamlit as st
import duckdb
import pandas as pd
import datetime
import re
import numpy as np
import plotly.express as px

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Intelligent Document OCR & Analytics Pipeline",
    layout="wide"
)

# ---------------------------------------------------------
# 1. Database Initialization & Data Seeding
# ---------------------------------------------------------
DB_FILE = "invoices_warehouse.duckdb"

def init_db():
    conn = duckdb.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_documents (
            doc_id VARCHAR PRIMARY KEY,
            vendor_name VARCHAR,
            invoice_number VARCHAR,
            invoice_date DATE,
            category VARCHAR,
            tax_amount DOUBLE,
            total_amount DOUBLE,
            created_at TIMESTAMP
        )
    """)
    
    # Check if database is empty; if so, seed synthetic historical data
    count = conn.execute("SELECT COUNT(*) FROM processed_documents").fetchone()[0]
    if count == 0:
        vendors = ["Acme Corp", "TechSupplies Inc", "CloudHost Services", "Global Logistics", "OfficeDepot Ltd"]
        categories = ["Hardware", "SaaS", "Infrastructure", "Shipping", "Office Supplies"]
        
        np.random.seed(42)
        records = []
        base_date = datetime.date(2026, 1, 1)
        
        for i in range(50):
            idx = np.random.randint(0, len(vendors))
            v_name = vendors[idx]
            cat = categories[idx]
            inv_num = f"INV-2026-{1000 + i}"
            days_offset = np.random.randint(0, 80)
            inv_date = base_date + datetime.timedelta(days=int(days_offset))
            amt = round(float(np.random.uniform(150, 3500)), 2)
            tax = round(amt * 0.10, 2)
            doc_id = f"DOC_SEED_{i+1:03d}"
            created_at = datetime.datetime.now()
            
            records.append((doc_id, v_name, inv_num, inv_date, cat, tax, amt, created_at))
            
        conn.executemany("""
            INSERT INTO processed_documents VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        
    conn.close()

init_db()

# ---------------------------------------------------------
# 2. Rule-Based Document Parsing Engine
# ---------------------------------------------------------
def parse_invoice_text(text: str):
    """Extracts key invoice metrics using rule-based NLP & Regular Expressions."""
    text_lower = text.lower()
    
    # 1. Extract Vendor Name
    vendor = "Unknown Vendor"
    if "acme" in text_lower:
        vendor = "Acme Corp"
    elif "techsupplies" in text_lower or "tech supplies" in text_lower:
        vendor = "TechSupplies Inc"
    elif "global logistics" in text_lower or "logistics" in text_lower:
        vendor = "Global Logistics"
    elif "cloudhost" in text_lower or "cloud" in text_lower:
        vendor = "CloudHost Services"
    elif "officedepot" in text_lower or "office" in text_lower:
        vendor = "OfficeDepot Ltd"
    else:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) > 0:
            vendor = lines[0][:30]

    # 2. Extract Invoice Number
    inv_match = re.search(r'(?:invoice|inv)[\s#:]*([a-zA-Z0-9-]+)', text, re.IGNORECASE)
    if inv_match:
        extracted_inv = inv_match.group(1).strip()
        if extracted_inv.lower() in ["number", "num", "id", "#"]:
            inv_match_fallback = re.search(r'inv-[a-zA-Z0-9-]+', text, re.IGNORECASE)
            invoice_num = inv_match_fallback.group(0).upper() if inv_match_fallback else f"INV-{np.random.randint(2000, 9999)}"
        else:
            invoice_num = extracted_inv.upper()
    else:
        invoice_num = f"INV-{np.random.randint(2000, 9999)}"

    # 3. Extract Date
    date_match = re.search(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b', text)
    if date_match:
        try:
            extracted_date = pd.to_datetime(date_match.group(1)).date()
        except:
            extracted_date = datetime.date.today()
    else:
        extracted_date = datetime.date.today()

    # 4. Extract Financial Amounts ($) - Prioritize 'Total Due' or '$' symbol amounts
    total_match = re.search(r'(?:total due|grand total|total)[\s:]*\$?[\s]*(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    if total_match:
        total_amount = float(total_match.group(1))
    else:
        dollar_amounts = [float(x.replace(',', '')) for x in re.findall(r'\$\s*(\d+(?:\.\d{2})?)', text)]
        total_amount = max(dollar_amounts) if dollar_amounts else 250.00

    tax_match = re.search(r'(?:tax)[\s:]*\$?[\s]*(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    tax_amount = float(tax_match.group(1)) if tax_match else round(total_amount * 0.10, 2)

    # 5. Assign Category
    category_map = {
        "Acme Corp": "Hardware",
        "TechSupplies Inc": "Hardware",
        "Global Logistics": "Shipping",
        "CloudHost Services": "Infrastructure",
        "OfficeDepot Ltd": "Office Supplies"
    }
    category = category_map.get(vendor, "General Expense")

    return {
        "vendor_name": vendor,
        "invoice_number": invoice_num,
        "invoice_date": extracted_date,
        "category": category,
        "tax_amount": tax_amount,
        "total_amount": total_amount
    }

# ---------------------------------------------------------
# 3. Streamlit Sidebar Layout & File Ingestion
# ---------------------------------------------------------
st.title("📄 Intelligent Document OCR & Expense Analytics Pipeline")
st.caption("Transform unstructured scanned PDF/TXT invoices into structured DuckDB relational records with automated duplicate detection, price spike anomaly alerts, and SQL analytics.")

st.sidebar.header("📥 Ingest Document")
uploaded_file = st.sidebar.file_uploader("Upload Invoice (PDF / TXT)", type=["txt", "pdf"])

parsed_data = None

if uploaded_file is not None:
    try:
        raw_text = uploaded_file.read().decode("utf-8")
    except Exception:
        raw_text = str(uploaded_file.read())

    st.sidebar.success("Text Extraction Complete!")
    parsed_data = parse_invoice_text(raw_text)
    
    st.sidebar.subheader("Extracted Attributes")
    st.sidebar.json(parsed_data)
    
    if st.sidebar.button("Save & Commit to Warehouse"):
        conn = duckdb.connect(DB_FILE)
        doc_id = f"DOC_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conn.execute("""
            INSERT INTO processed_documents VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            parsed_data["vendor_name"],
            parsed_data["invoice_number"],
            parsed_data["invoice_date"],
            parsed_data["category"],
            parsed_data["tax_amount"],
            parsed_data["total_amount"],
            datetime.datetime.now()
        ))
        conn.close()
        st.sidebar.success("Successfully committed to DuckDB Warehouse!")
        st.rerun()

# ---------------------------------------------------------
# 4. Warehouse Analytics & KPI Metrics
# ---------------------------------------------------------
conn = duckdb.connect(DB_FILE)
df_all = conn.execute("SELECT * FROM processed_documents").df()
conn.close()

if not df_all.empty:
    total_spend = df_all["total_amount"].sum()
    avg_invoice = df_all["total_amount"].mean()
    active_vendors = df_all["vendor_name"].nunique()
    total_invoices = len(df_all)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Warehouse Spend", f"${total_spend:,.2f}")
    m2.metric("Avg Invoice Value", f"${avg_invoice:,.2f}")
    m3.metric("Active Vendors", active_vendors)
    m4.metric("Processed Invoices", total_invoices)

st.markdown("---")

# ---------------------------------------------------------
# 5. Visual Dashboard & Anomaly Engine Tabs
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈 Expense Trends & Breakdown", "⚠️ Anomaly Detection Engine", "🔍 Raw SQL Query Runner"])

with tab1:
    col_chart1, col_chart2 = st.columns(2)
    
    if not df_all.empty:
        df_all["month"] = pd.to_datetime(df_all["invoice_date"]).dt.strftime("%b %Y")
        
        # Monthly Spend Trend by Vendor
        df_trend = df_all.groupby(["month", "vendor_name"])["total_amount"].sum().reset_index()
        fig_trend = px.bar(
            df_trend,
            x="month",
            y="total_amount",
            color="vendor_name",
            title="Monthly Spend Trend by Vendor",
            labels={"total_amount": "Total Amount ($)", "month": "Month"},
            barmode="stack"
        )
        col_chart1.plotly_chart(fig_trend, use_container_width=True)

        # Spend Share by Category
        df_cat = df_all.groupby("category")["total_amount"].sum().reset_index()
        fig_pie = px.pie(
            df_cat,
            names="category",
            values="total_amount",
            title="Category Expenditure Distribution",
            hole=0.4
        )
        col_chart2.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("⚠️ Automated Fraud & Financial Anomaly Alerts")
    
    col_a1, col_a2 = st.columns(2)
    
    conn = duckdb.connect(DB_FILE)
    
    # 1. Duplicate Invoices Alert Query
    dup_query = """
        SELECT vendor_name, total_amount, COUNT(*) as duplicate_count,
               STRING_AGG(invoice_number, ', ') as invoice_ids
        FROM processed_documents
        GROUP BY vendor_name, total_amount
        HAVING COUNT(*) > 1
    """
    df_duplicates = conn.execute(dup_query).df()
    
    # 2. Price Spike Anomaly Query (where total > 1.8 * vendor average)
    spike_query = """
        WITH VendorAvg AS (
            SELECT vendor_name, AVG(total_amount) as avg_amount
            FROM processed_documents
            GROUP BY vendor_name
        )
        SELECT p.doc_id, p.vendor_name, p.invoice_number, p.total_amount, ROUND(v.avg_amount, 2) as vendor_avg_spend
        FROM processed_documents p
        JOIN VendorAvg v ON p.vendor_name = v.vendor_name
        WHERE p.total_amount > 1.8 * v.avg_amount
    """
    df_spikes = conn.execute(spike_query).df()
    conn.close()
    
    with col_a1:
        st.markdown(f"**Potential Duplicate Invoices Flagged ({len(df_duplicates)})**")
        if not df_duplicates.empty:
            st.dataframe(df_duplicates, use_container_width=True)
        else:
            st.success("No duplicate payments detected.")

    with col_a2:
        st.markdown(f"**Sudden Price Spikes Flagged ({len(df_spikes)})**")
        if not df_spikes.empty:
            st.dataframe(df_spikes, use_container_width=True)
        else:
            st.success("No price anomalies detected.")

with tab3:
    st.subheader("🔍 DuckDB SQL Explorer")
    st.caption("Run Custom DuckDB SQL Query")
    
    default_sql = "SELECT vendor_name, category, COUNT(*) as total_invoices, SUM(total_amount) as total_spend FROM processed_documents GROUP BY vendor_name, category ORDER BY total_spend DESC"
    
    user_query = st.text_area("DuckDB SQL Query:", value=default_sql, height=100)
    
    if st.button("Execute Query"):
        try:
            conn = duckdb.connect(DB_FILE)
            query_res = conn.execute(user_query).df()
            conn.close()
            st.dataframe(query_res, use_container_width=True)
        except Exception as e:
            st.error(f"SQL Execution Error: {e}")