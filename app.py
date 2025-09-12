import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Validador de Pagos", layout="wide")
st.title("📊 Validador de Pagos - Comparación de Archivos Excel")

st.markdown("### 1. Carga de archivos")
batch_file = st.file_uploader("Archivo base: Batch.xlsx", type=["xlsx"])
deposit_file = st.file_uploader("Archivo: Deposit MGT.xls", type=["xls"])
fund_file = st.file_uploader("Archivo: Fund reason out confirm.xls", type=["xls"])
customer_file = st.file_uploader("Archivo: Customer refund application query.xls", type=["xls"])
payment_file = st.file_uploader("Archivo: Payment request mgt.xls", type=["xls"])

if st.button("🔍 Validar archivos") and all([batch_file, deposit_file, fund_file, customer_file, payment_file]):
    batch = pd.read_excel(batch_file, engine="openpyxl")
    deposit = pd.read_excel(deposit_file, engine="xlrd")
    fund_reason = pd.read_excel(fund_file, engine="xlrd")
    customer_refund = pd.read_excel(customer_file, engine="xlrd")
    payment_request = pd.read_excel(payment_file, engine="xlrd")

    # Validación de duplicados
    columnas_duplicadas = ["BL", "Fund Registration", "REASON OUT", "Payment Request"]
    for col in columnas_duplicadas:
        batch[col] = batch[col].astype(str)

    def detectar_duplicados(df, columnas):
        duplicados = []
        for i, row in df.iterrows():
            duplicadas = []
            for col in columnas:
                if df[col].duplicated(keep=False)[i]:
                    duplicadas.append(col)
            duplicados.append(", ".join(duplicadas))
        return duplicados

    batch["Duplicados"] = detectar_duplicados(batch, columnas_duplicadas)

    # Convertir BL y Ref 1 a formato numérico para evitar errores de comparación
    batch["BL"] = pd.to_numeric(batch["BL"], errors="coerce")
    deposit["B/L No"] = pd.to_numeric(deposit["B/L No"], errors="coerce")
    fund_reason["Ref 1"] = pd.to_numeric(fund_reason["Ref 1"], errors="coerce")

    def validar_bl(bl_value, bl_no_column):
        if pd.isna(bl_value):
            return "NO"
        try:
            bl_int = int(bl_value)
            if bl_int in bl_no_column.dropna().astype(int).values:
                return "OK"
            else:
                return "NO"
        except:
            return "NO"

    batch["Existe BL"] = batch["BL"].apply(lambda x: validar_bl(x, deposit["B/L No"]))
    batch["Description"] = batch.apply(lambda row: "GUA" if row["Existe BL"] == "OK" and row["Fund Registration"] in deposit["Fund Registration"].values else "WP", axis=1)

    batch["Coincide RSO"] = batch.apply(lambda row: "OK" if str(row["REASON OUT"]).strip() in fund_reason["Reason Out No."].astype(str).str.strip().values else "NO", axis=1)
    batch["Coincide FR"] = batch.apply(lambda row: "OK" if row["Fund Registration"] in fund_reason["Fund Registration"].values else "NO", axis=1)
    batch["FR y Ref 3"] = batch.apply(lambda row: "OK" if row["Fund Registration"] in fund_reason["Ref 3"].astype(str).values else "NO", axis=1)
    batch["BL y Ref 1"] = batch.apply(lambda row: "OK" if pd.to_numeric(row["BL"], errors="coerce") in fund_reason["Ref 1"].dropna().values else "NO", axis=1)
    batch["BL y Doc Text"] = batch.apply(lambda row: "OK" if len(str(row["BL"]).split()) > 1 and str(row["BL"]).split()[1] in fund_reason["Document Text"].astype(str).values else "", axis=1)

    batch["CR existe"] = batch["Payment Request"].apply(lambda x: "OK" if x in customer_refund["Payment Request No."].values else "NO")
    batch["CR y FR"] = batch.apply(lambda row: "OK" if any(fr.strip() in customer_refund["Fund Registration"].values for fr in str(row["Fund Registration"]).split(",")) else "NO", axis=1)
    batch["CR Y RSO"] = batch.apply(lambda row: "OK" if any(rso.strip() in customer_refund["Reason No."].values for rso in str(row["REASON OUT"]).split()) else "NO", axis=1)

    batch["Cantidad"] = batch.apply(lambda row: "OK" if ((row["MXN"] == payment_request.loc[payment_request["Application  Number"] == row["Payment Request"], "Refund Amount"].values[0]) if row["MXN"] > 0 else (row["USD"] == payment_request.loc[payment_request["Application  Number"] == row["Payment Request"], "Refund Amount"].values[0])) else "NO", axis=1)
    batch["Divisa"] = batch.apply(lambda row: "OK" if ((row["MXN"] > 0 and payment_request.loc[payment_request["Application  Number"] == row["Payment Request"], "Application Currency"].values[0] == "MXN") or (row["USD"] > 0 and payment_request.loc[payment_request["Application  Number"] == row["Payment Request"], "Application Currency"].values[0] == "USD")) else "NO", axis=1)
    batch["Error Cantidad"] = batch.apply(lambda row: "NO" if (row["MXN"] > 0 and row["USD"] > 0) or (row["MXN"] == 0 and row["USD"] == 0) else "", axis=1)

    st.success("✅ Validación completada")
    st.dataframe(batch)

    output = BytesIO()
    batch.to_excel(output, index=False, engine="openpyxl")
    st.download_button(
        label="📥 Descargar archivo validado",
        data=output.getvalue(),
        file_name="Validación de Batch.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Por favor, sube todos los archivos antes de validar.")
