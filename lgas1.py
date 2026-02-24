import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# ────────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ────────────────────────────────────────────────
# Ensure Secrets has SUPABASE_URL and SUPABASE_KEY (All Caps)
conn = st.connection("supabase", type=SupabaseConnection)

@st.cache_data(ttl=60)
def load_supabase_data():
    try:
        # Fetch all rows from the 'cylinders' table
        response = conn.table("cylinders").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Convert date columns for calculation
            for col in ["Last_Fill_Date", "Last_Test_Date", "Next_Test_Due"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

df = load_supabase_data()

# ────────────────────────────────────────────────
# 2. SIDEBAR NAVIGATION
# ────────────────────────────────────────────────
st.sidebar.title("LeoGas Management 2026")
page = st.sidebar.selectbox(
    "Select Page",
    ["Dashboard", "Cylinder Finder", "Return & Penalty Log", "Add New Cylinder"]
)

# ────────────────────────────────────────────────
# 3. DASHBOARD PAGE
# ────────────────────────────────────────────────
if page == "Dashboard":
    st.title("Live Fleet Dashboard")
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Units", len(df))
        col2.metric("Overdue", df["Overdue"].sum() if "Overdue" in df.columns else 0)
        col3.metric("Empty", len(df[df["Status"] == "Empty"]))
        
        st.subheader("Inventory Overview")
        st.dataframe(df, use_container_width=True)

# ────────────────────────────────────────────────
# 4. CYLINDER FINDER
# ────────────────────────────────────────────────
elif page == "Cylinder Finder":
    st.title("Search Database")
    search_id = st.text_input("Enter Cylinder ID")
    if search_id:
        result = df[df["Cylinder_ID"].str.contains(search_id, case=False, na=False)]
        st.dataframe(result)

# ────────────────────────────────────────────────
# 5. RETURN & PENALTY LOG
# ────────────────────────────────────────────────
elif page == "Return & Penalty Log":
    st.title("Cylinder Audit")
    return_id = st.selectbox("Select ID", options=df["Cylinder_ID"].unique() if not df.empty else [])
    
    if return_id:
        row = df[df["Cylinder_ID"] == return_id].iloc[0]
