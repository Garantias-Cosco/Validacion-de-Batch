import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Validador de Pagos", layout="wide")
st.title("📊 Validador de Pagos - Comparación de Archivos Excel")
st.markdown("### 1. Carga de archivos")

# Carga de archivos
batch_file = st.file_uploader("Archivo base: Batch.xlsx", type=["xlsx"])
deposit_file = st.file_uploader("Archivo: Deposit MGT.xls", type=["xls"])
fund_file = st.file_uploader("Archivo: Fund reason out confirm.xls", type=["xls"])
customer_file = st.file_uploader("Archivo: Customer refund application query.xls", type=["xls"])
payment_file = st.file_uploader("Archivo: Payment request mgt.xls", type=["xls"])
fund_register_file = st.file_uploader("Archivo: Fund register query.xls", type=["xls"])

# Funciones de validación
def validar_longitud(valor, longitud_esperada):
    if pd.isna(valor) or str(valor).strip() == "":
        return "VACIO"
    valor_str = str(valor).strip()
    if len(valor_str) > longitud_esperada:
        return f"LEN: {len(valor_str)}"
    return "OK"

def validar_bl_multiple(bl_value, bl_no_column):
    if pd.isna(bl_value):
        return "VACIO"
    try:
        bls = [str(int(b.strip())) for b in str(bl_value).split(",") if b.strip().isdigit()]
        bl_no_values = bl_no_column.dropna().astype(int).astype(str).values
        return "OK" if all(bl in bl_no_values for bl in bls) else "ERROR"
    except:
        return "ERROR"
def detectar_duplicados(df, columnas):
    duplicados = []
    for i, row in df.iterrows():
        duplicadas = []
        for col in columnas:
            if df[col].duplicated(keep=False)[i]:
                duplicadas.append(col)
        duplicados.append(", ".join(duplicadas) if duplicadas else "OK")
    return duplicados

def validar_bl_ref1(bl_value, ref1_column):
    try:
        primer_bl = str(bl_value).split(",")[0].strip()
        primer_bl_num = int(primer_bl)
        return "OK" if primer_bl_num in ref1_column.dropna().astype(int).values else "ERROR"
    except:
        return "ERROR"

def validar_bl_doc_text(bl_value, doc_text_column):
    try:
        bls = [b.strip() for b in str(bl_value).split(",")]
        if len(bls) <= 1:
            return ""
        adicionales = bls[1:]
        doc_text_values = doc_text_column.dropna().astype(str).apply(lambda x: [s for s in x.split() if s.isdigit()])
        encontrados = []
        for bl in adicionales:
            if any(bl == val for sublist in doc_text_values for val in sublist):
                encontrados.append(True)
            else:
                encontrados.append(False)
        return "OK" if all(encontrados) else "ERROR"
    except:
        return "ERROR"

def validar_bank_account(fund_registro, df_fund_register):
    try:
        fund_registro = str(fund_registro).strip()
        df_fund_register["Fund Registration"] = df_fund_register["Fund Registration"].astype(str).str.strip()
        df_fund_register["Bank Account"] = df_fund_register["Bank Account"].astype(str).str.strip()
        filtro = df_fund_register[df_fund_register["Fund Registration"] == fund_registro]
        if filtro.empty:
            return "ERROR"
        cuenta = filtro["Bank Account"].values[0]
        if cuenta in ["124180002356385257", "124180002356380294"]:
            return "GUARANTEE"
        elif cuenta == "110180000776468582":
            return "LC"
        elif cuenta == "124180002356385095":
            return "DND"
        elif cuenta == "880285643":
            return "OFT"
        else:
            return "ERROR"
    except Exception:
        return "ERROR"

def validar_cantidad(row, payment_request):
    try:
        filtro = payment_request[payment_request["Application  Number"] == row["Payment Request"]]
        if filtro.empty:
            return "ERROR"
        monto = filtro["Refund Amount"].values[0]
        if row["MXN"] > 0:
            return "OK" if row["MXN"] == monto else "ERROR"
        elif row["USD"] > 0:
            return "OK" if row["USD"] == monto else "ERROR"
        else:
            return "ERROR"
    except:
        return "ERROR"

def validar_divisa(row, payment_request):
    try:
        filtro = payment_request[payment_request["Application  Number"] == row["Payment Request"]]
        if filtro.empty:
            return "ERROR"
        moneda = filtro["Application Currency"].values[0]
        if row["MXN"] > 0:
            return "OK" if moneda == "MXN" else "ERROR"
        elif row["USD"] > 0:
            return "OK" if moneda == "USD" else "ERROR"
        else:
            return "ERROR"
    except:
        return "ERROR"

# Validación principal
if st.button("🔍 Validar archivos"):
    archivos = {
        "Batch": batch_file,
        "Deposit": deposit_file,
        "Fund Reason": fund_file,
        "Customer Refund": customer_file,
        "Payment Request": payment_file,
        "Fund Register": fund_register_file
    }

    faltantes = [nombre for nombre, archivo in archivos.items() if archivo is None]
    if faltantes:
        st.warning(f"⚠️ Faltan los siguientes archivos: {', '.join(faltantes)}")
    else:
        batch = pd.read_excel(batch_file, engine="openpyxl")
        deposit = pd.read_excel(deposit_file, engine="xlrd")
        fund_reason = pd.read_excel(fund_file, engine="xlrd")
        customer_refund = pd.read_excel(customer_file, engine="xlrd")
        payment_request = pd.read_excel(payment_file, engine="xlrd")
        fund_register = pd.read_excel(fund_register_file, engine="xlrd", dtype=str)

        columnas_duplicadas = ["BL", "Fund Registration", "REASON OUT", "Payment Request"]
        for col in columnas_duplicadas:
            batch[col] = batch[col].astype(str)

        batch["Duplicados"] = detectar_duplicados(batch, columnas_duplicadas)
        batch["Valida BL"] = batch["BL"].apply(lambda x: validar_longitud(x, 10))
        batch["Valida FR"] = batch["Fund Registration"].apply(lambda x: validar_longitud(x, 19))
        batch["Valida RSO"] = batch["REASON OUT"].apply(lambda x: validar_longitud(x, 15))
        batch["Valida PR"] = batch["Payment Request"].apply(lambda x: validar_longitud(x, 14))
        batch["Existe BL"] = batch["BL"].apply(lambda x: validar_bl_multiple(x, deposit["B/L No"]))
        batch["Description"] = batch.apply(lambda row: "GUA" if row["Existe BL"] == "OK" and row["Fund Registration"] in deposit["Fund Registration"].values else "WP", axis=1)
        batch["Coincide RSO"] = batch.apply(lambda row: "OK" if str(row["REASON OUT"]).strip() in fund_reason["Reason Out No."].astype(str).str.strip().values else "ERROR", axis=1)
        batch["Coincide FR"] = batch.apply(lambda row: "OK" if row["Fund Registration"] in fund_reason["Fund Registration"].values else "ERROR", axis=1)
        batch["FR y Ref 3"] = batch.apply(lambda row: "OK" if row["Fund Registration"] in fund_reason["Ref 3"].astype(str).values else "ERROR", axis=1)
        batch["BL y Ref 1"] = batch["BL"].apply(lambda x: validar_bl_ref1(x, fund_reason["Ref 1"]))
        batch["BL y Doc Text"] = batch["BL"].apply(lambda x: validar_bl_doc_text(x, fund_reason["Document Text"]))
        batch["CR existe"] = batch["Payment Request"].apply(lambda x: "OK" if x in customer_refund["Payment Request No."].values else "ERROR")
        batch["CR y FR"] = batch.apply(lambda row: "OK" if any(fr.strip() in customer_refund["Fund Registration"].values for fr in str(row["Fund Registration"]).split(",")) else "ERROR", axis=1)
        batch["CR Y RSO"] = batch.apply(lambda row: "OK" if any(rso.strip() in customer_refund["Reason No."].values for rso in str(row["REASON OUT"]).split()) else "ERROR", axis=1)
        batch["Cantidad"] = batch.apply(lambda row: validar_cantidad(row, payment_request), axis=1)
        batch["Divisa"] = batch.apply(lambda row: validar_divisa(row, payment_request), axis=1)
        batch["Error Cantidad"] = batch.apply(lambda row: "ERROR" if ((pd.isna(row["MXN"]) and pd.isna(row["USD"])) or (row["MXN"] > 0 and row["USD"] > 0)) else "", axis=1)
        batch["Tipo Cuenta"] = batch["Fund Registration"].apply(lambda x: validar_bank_account(x, fund_register))

        st.success("✅ Validación completada")
        st.dataframe(batch)

        output = BytesIO()
        batch.to_excel(output, index=False, engine="openpyxl")
        st.download_button(
            label="📥 Descargar archivo validado",
            data=output.getvalue(),
            file_name="Validación de Batch.xlsx"
        )
