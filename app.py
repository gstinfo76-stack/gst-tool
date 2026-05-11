import streamlit as st
import pandas as pd
import io
import plotly.express as px

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="GST Reconciliation Pro",
    layout="wide"
)

# =====================================
# LOGIN SYSTEM
# =====================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():

    st.markdown("""
    <h1 style='text-align:center;color:#1E3A8A;'>
    🔐 GST Reconciliation Login
    </h1>
    """, unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.rerun()

        else:
            st.error("Invalid Username or Password")

if not st.session_state.logged_in:
    login()
    st.stop()

# =====================================
# SIDEBAR
# =====================================
st.sidebar.success("✅ Logged In")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.title("📌 GST Tool")

# =====================================
# TITLE
# =====================================
st.markdown("""
<h1 style='text-align:center;color:#0F172A;'>
📊 GST Reconciliation CFO Dashboard
</h1>
""", unsafe_allow_html=True)

# =====================================
# FILE UPLOAD
# =====================================
file = st.file_uploader(
    "📤 Upload GST Excel File",
    type=["xlsx"]
)

if file is not None:

    # =====================================
    # LOAD DATA
    # =====================================
    books = pd.read_excel(file, sheet_name="purchase")
    gst2b = pd.read_excel(file, sheet_name="2b")

    # =====================================
    # CLEANING
    # =====================================
    for df in [books, gst2b]:

        df['Invoice_No'] = (
            df['Invoice_No']
            .astype(str)
            .str.upper()
            .str.replace("-", "", regex=False)
            .str.replace("/", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.strip()
        )

        df['Supplier_GSTIN'] = (
            df['Supplier_GSTIN']
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df['GST_Amount'] = pd.to_numeric(
            df['GST_Amount'],
            errors='coerce'
        ).fillna(0)

    # =====================================
    # MERGE
    # =====================================
    recon = pd.merge(
        books,
        gst2b,
        on=['Supplier_GSTIN', 'Invoice_No'],
        how='outer',
        suffixes=('_Books', '_2B')
    )

    # =====================================
    # GST DIFFERENCE
    # =====================================
    recon['GST_Diff'] = (
        recon['GST_Amount_Books'].fillna(0)
        - recon['GST_Amount_2B'].fillna(0)
    )

    # =====================================
    # MATCH STATUS
    # =====================================
    def get_status(row):

        if pd.isna(row.get('GST_Amount_2B')):
            return "Unmatched"

        elif pd.isna(row.get('GST_Amount_Books')):
            return "Unmatched"

        elif (
            abs(row['GST_Diff']) < 1
            and row['Invoice_Date_Books']
            == row['Invoice_Date_2B']
        ):
            return "Exact Match"

        elif (
            abs(row['GST_Diff']) < 1
            and row['Invoice_Date_Books']
            != row['Invoice_Date_2B']
        ):
            return "Partial Match"

        else:
            return "Partial Match"

    recon['Match_Status'] = recon.apply(
        get_status,
        axis=1
    )

    # =====================================
    # DIFFERENCE REASON
    # =====================================
    def get_reason(row):

        if pd.isna(row.get('GST_Amount_2B')):
            return "Missing in 2B"

        elif pd.isna(row.get('GST_Amount_Books')):
            return "Missing in Books"

        elif (
            abs(row['GST_Diff']) < 1
            and row['Invoice_Date_Books']
            != row['Invoice_Date_2B']
        ):
            return "Date Difference"

        elif abs(row['GST_Diff']) < 1:
            return "All Fields Match"

        else:
            return "GST Difference"

    recon['Difference_Reason'] = recon.apply(
        get_reason,
        axis=1
    )

    # =====================================
    # RECOMMENDED ITC
    # =====================================
    recon['Recommended_ITC'] = recon[
        'Match_Status'
    ].apply(
        lambda x: "YES"
        if x == "Exact Match"
        else "REVIEW"
    )

    # =====================================
    # KPI CALCULATIONS
    # =====================================
    total_books_itc = books['GST_Amount'].sum()

    total_2b_itc = gst2b['GST_Amount'].sum()

    recommended_itc = recon[
        recon['Match_Status']
        == 'Exact Match'
    ]['GST_Amount_Books'].sum()

    itc_risk = recon[
        recon['Match_Status']
        != 'Exact Match'
    ]['GST_Amount_Books'].fillna(0).sum()

    total_books_invoice = len(books)

    total_2b_invoice = len(gst2b)

    invoice_difference = abs(
        total_books_invoice
        - total_2b_invoice
    )

    review_required = len(
        recon[
            recon['Match_Status']
            != 'Exact Match'
        ]
    )

    # =====================================
    # KPI DASHBOARD
    # =====================================
    st.subheader("📌 CFO Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#2563EB,#1D4ED8);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>📘 Total ITC Booked</h4>
        <h2>₹ {total_books_itc:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#059669,#10B981);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>📥 ITC in 2B</h4>
        <h2>₹ {total_2b_itc:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#16A34A,#22C55E);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>✅ Recommended ITC</h4>
        <h2>₹ {recommended_itc:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#DC2626,#EF4444);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>🚨 ITC at Risk</h4>
        <h2>₹ {itc_risk:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    c5, c6, c7, c8 = st.columns(4)

    with c5:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#7C3AED,#8B5CF6);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>📑 Invoices in Books</h4>
        <h2>{total_books_invoice}</h2>
        </div>
        """, unsafe_allow_html=True)

    with c6:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#0891B2,#06B6D4);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>📄 Invoices in 2B</h4>
        <h2>{total_2b_invoice}</h2>
        </div>
        """, unsafe_allow_html=True)

    with c7:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#D97706,#F59E0B);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>⚠ Invoice Difference</h4>
        <h2>{invoice_difference}</h2>
        </div>
        """, unsafe_allow_html=True)

    with c8:
        st.markdown(f"""
        <div style="
        background:linear-gradient(135deg,#BE123C,#E11D48);
        padding:25px;
        border-radius:18px;
        color:white;
        text-align:center;
        ">
        <h4>🔍 Review Required</h4>
        <h2>{review_required}</h2>
        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # CHART
    # =====================================
    st.subheader("📊 Match Summary")

    chart_data = (
        recon['Match_Status']
        .value_counts()
        .reset_index()
    )

    chart_data.columns = ['Status', 'Count']

    fig = px.pie(
        chart_data,
        values='Count',
        names='Status',
        hole=0.5
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================
    # FILTER
    # =====================================
    st.subheader("🔍 Filter Data")

    status_filter = st.selectbox(
        "Select Match Status",
        ["All"] + list(
            recon['Match_Status']
            .dropna()
            .unique()
        )
    )

    if status_filter != "All":

        filtered_data = recon[
            recon['Match_Status']
            == status_filter
        ]

    else:
        filtered_data = recon

    # =====================================
    # SHOW DATA
    # =====================================
    st.subheader("📄 Reconciliation Data")

    st.dataframe(
        filtered_data,
        use_container_width=True
    )

    # =====================================
    # EXCEL EXPORT
    # =====================================
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine='xlsxwriter'
    ) as writer:

        books.to_excel(
            writer,
            sheet_name='Books',
            index=False
        )

        gst2b.to_excel(
            writer,
            sheet_name='2B',
            index=False
        )

        recon.to_excel(
            writer,
            sheet_name='Reconciliation',
            index=False
        )

        exact_match = recon[
            recon['Match_Status']
            == 'Exact Match'
        ]

        partial_match = recon[
            recon['Match_Status']
            == 'Partial Match'
        ]

        unmatched = recon[
            recon['Match_Status']
            == 'Unmatched'
        ]

        exact_match.to_excel(
            writer,
            sheet_name='Exact_Match',
            index=False
        )

        partial_match.to_excel(
            writer,
            sheet_name='Partial_Match',
            index=False
        )

        unmatched.to_excel(
            writer,
            sheet_name='Unmatched',
            index=False
        )

        # =====================================
        # WORKBOOK
        # =====================================
        workbook = writer.book

        dashboard = workbook.add_worksheet(
            'CFO_Dashboard'
        )

        # =====================================
        # FORMATS
        # =====================================
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 22,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#1E3A8A'
        })

        green_box = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#16A34A',
            'border': 1
        })

        blue_box = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#2563EB',
            'border': 1
        })

        red_box = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#DC2626',
            'border': 1
        })

        orange_box = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D97706',
            'border': 1
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EAF7',
            'border': 1
        })

        green_fill = workbook.add_format({
            'bg_color': '#C6EFCE'
        })

        yellow_fill = workbook.add_format({
            'bg_color': '#FFEB9C'
        })

        red_fill = workbook.add_format({
            'bg_color': '#FFC7CE'
        })

        # =====================================
        # DASHBOARD TITLE
        # =====================================
        dashboard.merge_range(
            'A1:H2',
            'GST CFO DASHBOARD',
            title_format
        )

        dashboard.set_column('A:H', 25)

        # =====================================
        # KPI BOXES
        # =====================================
        dashboard.merge_range(
            'A4:B5',
            f'Total ITC Booked\n₹ {total_books_itc:,.2f}',
            blue_box
        )

        dashboard.merge_range(
            'C4:D5',
            f'ITC in 2B\n₹ {total_2b_itc:,.2f}',
            green_box
        )

        dashboard.merge_range(
            'E4:F5',
            f'Recommended ITC\n₹ {recommended_itc:,.2f}',
            green_box
        )

        dashboard.merge_range(
            'G4:H5',
            f'ITC at Risk\n₹ {itc_risk:,.2f}',
            red_box
        )

        dashboard.merge_range(
            'A7:B8',
            f'Invoices in Books\n{total_books_invoice}',
            blue_box
        )

        dashboard.merge_range(
            'C7:D8',
            f'Invoices in 2B\n{total_2b_invoice}',
            green_box
        )

        dashboard.merge_range(
            'E7:F8',
            f'Invoice Difference\n{invoice_difference}',
            orange_box
        )

        dashboard.merge_range(
            'G7:H8',
            f'Review Required\n{review_required}',
            red_box
        )

        # =====================================
        # FORMAT SHEETS
        # =====================================
        sheets = [
            'Books',
            '2B',
            'Reconciliation',
            'Exact_Match',
            'Partial_Match',
            'Unmatched'
        ]

        for sheet in sheets:

            ws = writer.sheets[sheet]

            ws.set_column('A:Z', 20)

            ws.freeze_panes(1, 0)

            for col_num, value in enumerate(
                recon.columns.values
            ):
                try:
                    ws.write(
                        0,
                        col_num,
                        value,
                        header_format
                    )
                except:
                    pass

        # =====================================
        # CONDITIONAL FORMATTING
        # =====================================
        ws = writer.sheets['Reconciliation']

        rows = len(recon)

        ws.conditional_format(
            f'A2:Z{rows+1}',
            {
                'type': 'formula',
                'criteria': '=$L2="Exact Match"',
                'format': green_fill
            }
        )

        ws.conditional_format(
            f'A2:Z{rows+1}',
            {
                'type': 'formula',
                'criteria': '=$L2="Partial Match"',
                'format': yellow_fill
            }
        )

        ws.conditional_format(
            f'A2:Z{rows+1}',
            {
                'type': 'formula',
                'criteria': '=$L2="Unmatched"',
                'format': red_fill
            }
        )

    # =====================================
    # DOWNLOAD BUTTON
    # =====================================
    st.download_button(
        label="⬇️ Download Professional GST Report",
        data=output.getvalue(),
        file_name="GST_Professional_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:

    st.info("👆 Upload your GST Excel file")
