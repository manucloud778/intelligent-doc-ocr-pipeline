📄 Intelligent Document OCR & Expense Analytics PipelineA production-grade, end-to-end data engineering pipeline that ingests unstructured invoice documents, extracts core financial metrics via rule-based NLP and regular expressions, and loads relational data into DuckDB for high-speed OLAP analytics and automated fraud/anomaly detection.

📌 Executive SummaryModern enterprise financial auditing requires high-throughput processing of semi-structured and unstructured invoice documents. This project bridges raw document parsing with analytical data warehousing by providing an end-to-end pipeline that:Parses unstructured invoice text into structured data using deterministic regex rules.Stores historical transactions in an ACID-compliant, high-performance embedded OLAP database (DuckDB).Runs automated audit checks to detect duplicate billing and anomalous spend spikes.Visualizes expenditure patterns through an interactive BI dashboard built with Streamlit and Plotly.🏗️ System Architecture
┌──────────────────────────┐
│   Unstructured Invoices  │
│  (.txt / Raw OCR Text)   │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Entity Extraction Engine │  <-- Deterministic Regex / Rule-Based NLP
│ (Vendor, Date, Amount)   │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Embedded OLAP Warehouse  │  <-- DuckDB Relational Engine
│  (ACID-Compliant Tables) │
└────────────┬─────────────┘
             │
    ┌────────┴────────────────────────┐
    ▼                                 ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│ Anomaly & Fraud Engine   │   │ BI Analytics Dashboard   │
│  - Duplicate Checks      │   │  - Spend Trends          │
│  - 1.8x Spike Alerts     │   │  - Vendor Share          │
└──────────────────────────┘   └──────────────────────────┘
✨ Key Features & Technical Highlights1. Robust Document Parsing (Regex Engine)Extracts critical financial attributes: Vendor Name, Invoice ID, Transaction Date, Tax Amount, and Gross Total Amount.Handles complex edge cases including varied currency formatting, multi-line structural layouts, and missing field fallbacks.2. High-Performance OLAP Storage (DuckDB)Utilizes DuckDB for zero-latency, local analytical querying over structured invoice datasets.Schema enforcement ensures transactional integrity and high-speed columnar aggregation.3. Automated Fraud & Anomaly Detection LogicDuplicate Invoice Identification: Uses SQL HAVING COUNT(*) > 1 grouping logic to flag redundant invoice submissions prior to payment release.Spend Spike Engine: Employs Common Table Expressions (CTEs) to flag individual transaction totals exceeding $1.8 \times$ the vendor's historical average:$$\text{Threshold} = 1.8 \times \text{AVG}(\text{Historical Spend}_{\text{Vendor}})$$4. Interactive BI & SQL Exploration InterfaceMarket Share Distribution: Interactive Plotly pie and bar charts detailing expenditure by vendor.Monthly Spend Velocity: Time-series tracking of total outflow across billing cycles.Embedded SQL Query Runner: Live, custom SQL terminal for ad-hoc querying directly against DuckDB.🛠️ Tech StackCore Language: Python 3.10+Database / Engine: DuckDB (OLAP Analytics)Data Manipulation & Analysis: Pandas, NumPyDashboard & UI: StreamlitData Visualization: Plotly ExpressParsing Engine: Regular Expressions (re)📂 Project Structureintelligent-doc-ocr-pipeline/
│
├── app.py                  # Main Streamlit Dashboard & Pipeline Engine
├── sample_invoice_1.txt    # Sample invoice document 1
├── sample_invoice_2.txt    # Sample invoice document 2
├── .gitignore              # Ignored files (DuckDB binaries, cache, venv)
└── README.md               # Project documentation
🚀 Getting Started1. PrerequisitesEnsure you have Python 3.10 or higher installed.python --version
2. InstallationClone the repository and install the required dependencies:# Clone the repository
git clone https://github.com/manucloud778/intelligent-doc-ocr-pipeline.git
cd intelligent-doc-ocr-pipeline

# Install required Python packages
pip install streamlit duckdb pandas numpy plotly
3. Run the ApplicationLaunch the interactive Streamlit dashboard:streamlit run app.py
📊 Analytical SQL Patterns DemonstrationPrice Spike Detection QueryWITH VendorStats AS (
    SELECT 
        vendor_name,
        AVG(total_amount) AS avg_spend
    FROM invoices
    GROUP BY vendor_name
)
SELECT 
    i.invoice_id,
    i.vendor_name,
    i.total_amount,
    v.avg_spend,
    ROUND(i.total_amount / v.avg_spend, 2) AS spike_factor
FROM invoices i
JOIN VendorStats v ON i.vendor_name = v.vendor_name
WHERE i.total_amount > (1.8 * v.avg_spend);
📜 LicenseDistributed under the MIT License.
