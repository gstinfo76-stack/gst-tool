import streamlit as st
import pandas as pd
import io

# ================================
# TITLE
# ================================
st.title("📊 GST Reconciliation Tool (Pro)")

# ================================
# FILE UPLOAD
# ================================
file = st.file_uploader("Upload GST Excel File", type=["xlsx"])

if file is not None:

    # ================================
    # LOAD DATA
    # ================================
    books = pd.read_excel(file, sheet_name="purchase")
    gst2b = pd.read_excel(file, sheet_name="2b")

    # ================================
    # CLEANING
    # ================================
    for df in [books, gst2b]:
        df['Invoice_No'] = df['Invoice_No'].astype(str).str.strip()
        df['Supplier_GSTIN'] = df['Supplier_GSTIN'].astype(str).str.strip()
        df['GST_Amount'] = pd.to_numeric(df['GST_Amount'], errors='coerce').fillna(0)

    # ================================
    # MERGE
    # ================================
    recon = pd.merge(
        books,
        gst2b,
        on='Invoice_No',
        how='outer',
        suffixes=('_Books', '_2B')
    )

    # ================================
    # CALCULATIONS
    # ================================
    recon['GST_Diff'] = recon['GST_Amount_Books'].fillna(0) - recon['GST_Amount_2B'].fillna(0)

    # STATUS
    def get_status(row):
        if pd.isna(row.get('Supplier_GSTIN_2B')):
            return 'Missing in 2B'
        elif pd.isna(row.get('Supplier_GSTIN_Books')):
            return 'Missing in Books'
        elif abs(row['GST_Diff']) < 1:
            return 'Match'
        else:
            return 'Mismatch'

    recon['Status'] = recon.apply(get_status, axis=1)

    # ================================
    # EMAIL DRAFT
    # ================================
    def make_email(row):
        if row['Status'] == 'Missing in 2B':
            return f"""Subject: Invoice Missing in GSTR-2B

Dear Sir,

As per our records, below invoice is not reflecting in GSTR-2B:

Invoice No: {row['Invoice_No']}

Kindly upload the same in your GSTR-1.

Regards,
Accounts Team"""
        return ""

    recon['Email_Draft'] = recon.apply(make_email, axis=1)

    # ================================
    # KPI DASHBOARD
    # ================================
    st.subheader("📌 Summary")

    total_books = books['GST_Amount'].sum()
    total_2b = gst2b['GST_Amount'].sum()
    diff = total_books - total_2b

    col1, col2, col3 = st.columns(3)
    col1.metric("Books GST", f"{total_books:,.2f}")
    col2.metric("2B GST", f"{total_2b:,.2f}")
    col3.metric("Difference", f"{diff:,.2f}")

    # ================================
    # FILTER
    # ================================
    st.subheader("🔍 Filter Data")

    status_filter = st.selectbox("Select Status", ["All"] + list(recon['Status'].dropna().unique()))

    if status_filter != "All":
        filtered_data = recon[recon['Status'] == status_filter]
    else:
        filtered_data = recon

    # ================================
    # SHOW DATA
    # ================================
    st.subheader("📄 Reconciliation Data")
    st.dataframe(filtered_data, use_container_width=True)

    # ================================
    # MISSING IN 2B
    # ================================
    st.subheader("⚠️ Missing in 2B")
    missing_2b = recon[recon['Status'] == 'Missing in 2B']
    st.dataframe(missing_2b, use_container_width=True)

    # ================================
    # EXCEL EXPORT (PRO FORMAT)
    # ================================
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        # Write sheets
        books.to_excel(writer, sheet_name='Books', index=False)
        gst2b.to_excel(writer, sheet_name='2B', index=False)
        recon.to_excel(writer, sheet_name='Reconciliation', index=False)
        missing_2b.to_excel(writer, sheet_name='Missing_in_2B', index=False)

        email_sheet = missing_2b[['Supplier_GSTIN_Books','Invoice_No','GST_Amount_Books','Email_Draft']]
        email_sheet.to_excel(writer, sheet_name='Email_Followup', index=False)

        summary = pd.DataFrame({
            'Metric': ['Books GST', '2B GST', 'Difference'],
            'Value': [total_books, total_2b, diff]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

        workbook = writer.book

        # Formats
        header = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})
        green = workbook.add_format({'bg_color': '#C6EFCE'})
        red = workbook.add_format({'bg_color': '#FFC7CE'})
        yellow = workbook.add_format({'bg_color': '#FFEB9C'})
        orange = workbook.add_format({'bg_color': '#F4B084'})
        wrap = workbook.add_format({'text_wrap': True})

        # Format Books & 2B
        ws_books = writer.sheets['Books']
        ws_2b = writer.sheets['2B']
        ws_books.set_column('A:Z', 15)
        ws_2b.set_column('A:Z', 15)

        # Format Reconciliation
        ws_recon = writer.sheets['Reconciliation']
        ws_recon.set_column('A:Z', 18)

        status_col = recon.columns.get_loc('Status')
        col_letter = chr(65 + status_col)
        rows = len(recon)

        rng = f'A2:Z{rows+1}'

        ws_recon.conditional_format(rng, {'type':'formula','criteria':f'=${col_letter}2="Match"','format':green})
        ws_recon.conditional_format(rng, {'type':'formula','criteria':f'=ISNUMBER(SEARCH("Mismatch",${col_letter}2))','format':red})
        ws_recon.conditional_format(rng, {'type':'formula','criteria':f'=ISNUMBER(SEARCH("Missing",${col_letter}2))','format':yellow})

        # Format Missing
        ws_miss = writer.sheets['Missing_in_2B']
        ws_miss.set_column('A:Z', 18)
        ws_miss.conditional_format(f'A2:Z{len(missing_2b)+1}', {'type':'no_errors','format':orange})

        # Email sheet formatting
        ws_email = writer.sheets['Email_Followup']
        ws_email.set_column('A:C', 20)
        ws_email.set_column('D:D', 60, wrap)

    # Download button
    st.download_button(
        label="⬇️ Download Full GST Report (Excel)",
        data=output.getvalue(),
        file_name="GST_Professional_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👆 Upload your GST Excel file to start")