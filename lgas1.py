import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# ────────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ────────────────────────────────────────────────
# Connect using SUPABASE_URL and SUPABASE_KEY from secrets.toml or Streamlit Cloud
conn = st.connection("supabase", type=SupabaseConnection)

@st.cache_data(ttl=60)
def load_supabase_data():
    try:
        # Fetch all rows from your 'cylinders' table
        response = conn.table("cylinders").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Data Cleaning & Type Conversion
            # Keep PIN as string for display, but it's stored as BigInt in DB
            df["Location_PIN"] = df["Location_PIN"].astype(str)
            for col in ["Last_Fill_Date", "Last_Test_Date", "Next_Test_Due"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return pd.DataFrame()

df = load_supabase_data()

# ────────────────────────────────────────────────
# 2. SIDEBAR NAVIGATION
# ────────────────────────────────────────────────
st.sidebar.title("LeoGas Management 2026")
st.sidebar.info("Operational Hub - Hyderabad")
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
        # Counts rows where 'Overdue' column is True
        overdue_count = df["Overdue"].sum() if "Overdue" in df.columns else 0
        col2.metric("Overdue (Test)", overdue_count)
        col3.metric("Empty Stock", len(df[df["Status"] == "Empty"]))
        
        st.subheader("Inventory Overview")
        st.dataframe(df.sort_values("Next_Test_Due"), use_container_width=True)
    else:
        st.warning("No data found in Supabase.")

# ────────────────────────────────────────────────
# 4. MODIFIED CYLINDER FINDER (New Features)
# ────────────────────────────────────────────────
elif page == "Cylinder Finder":
    st.title("🔍 Advanced Cylinder Search")
    
    # Search bars in three columns
    colA, colB, colC = st.columns(3)
    with colA:
        s_id = st.text_input("Search Cylinder ID", placeholder="LEO-XXX")
    with colB:
        s_name = st.text_input("Search Customer Name", placeholder="e.g. Ali Khan")
    with colC:
        s_status = st.selectbox("Filter Status", ["All", "Full", "Empty", "Damaged"])

    # Filtering Logic (Fuzzy search)
    f_df = df.copy()
    if s_id:
        f_df = f_df[f_df["Cylinder_ID"].str.contains(s_id, case=False, na=False)]
    if s_name:
        f_df = f_df[f_df["Customer_Name"].str.contains(s_name, case=False, na=False)]
    if s_status != "All":
        f_df = f_df[f_df["Status"] == s_status]

    st.subheader(f"Results Found: {len(f_df)}")
    st.dataframe(f_df, use_container_width=True)

# ────────────────────────────────────────────────
# 5. RETURN & PENALTY LOG
# ────────────────────────────────────────────────
elif page == "Return & Penalty Log":
    st.title("Cylinder Return Audit")
    
    if not df.empty:
        target_id = st.selectbox("Select ID for Return", options=df["Cylinder_ID"].unique())
        
        with st.form("audit_form"):
            condition = st.selectbox("Physical Condition", ["Good", "Dented", "Leaking", "Broken Valve"])
            if st.form_submit_button("Update Status"):
                # If damaged, set status to 'Damaged', else 'Empty'
                new_status = "Empty" if condition == "Good" else "Damaged"
                
                try:
                    conn.table("cylinders").update({
                        "Status": new_status, 
                        "Fill_Percent": 0
                    }).eq("Cylinder_ID", target_id).execute()
                    
                    st.success(f"Cylinder {target_id} updated successfully!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Update Failed: {e}")

# ────────────────────────────────────────────────
# 6. ADD NEW CYLINDER
# ────────────────────────────────────────────────
elif page == "Add New Cylinder":
    st.title("Register New Stock")
    with st.form("new_entry_form"):
        c_id = st.text_input("New Cylinder ID")
        cust = st.text_input("Customer Name")
        pin = st.text_input("Location PIN (Numbers Only)", max_chars=6)
        cap = st.number_input("Capacity (kg)", value=14.2)
        
        if st.form_submit_button("Add to Cloud"):
            if not c_id:
                st.error("Please provide a Cylinder ID.")
            else:
                today = datetime.now().date()
                next_due = today + pd.Timedelta(days=1825) # 5-year test cycle
                
                # Payload matches your exact SQL Table Schema
                payload = {
                    "Cylinder_ID": str(c_id),
                    "Customer_Name": str(cust),
                    "Location_PIN": int(pin) if pin.isdigit() else 0, # Force BigInt compliance
                    "Capacity_kg": float(cap),
                    "Fill_Percent": 100,
                    "Status": "Full",
                    "Last_Fill_Date": str(today),
                    "Last_Test_Date": str(today),
                    "Next_Test_Due": str(next_due),
                    "Overdue": False
                }
                
                try:
                    conn.table("cylinders").insert(payload).execute()
                    st.success(f"Cylinder {c_id} registered!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")
