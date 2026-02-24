import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# ────────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ────────────────────────────────────────────────
# Uses [connections.supabase] from Streamlit Secrets
conn = st.connection("supabase", type=SupabaseConnection)

@st.cache_data(ttl=60)
def load_supabase_data():
    try:
        # Fetch all rows from the 'cylinders' table
        response = conn.table("cylinders").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Data Cleaning
            df["Location_PIN"] = df["Location_PIN"].astype(str).str.strip()
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
        overdue_count = df["Overdue"].sum() if "Overdue" in df.columns else 0
        col2.metric("Overdue (Test)", overdue_count)
        col3.metric("Empty Stock", len(df[df["Status"] == "Empty"]))
        
        st.subheader("Full Inventory Overview")
        st.dataframe(df.sort_values("Next_Test_Due"), use_container_width=True)
    else:
        st.warning("No data found. Please add a cylinder to begin.")

# ────────────────────────────────────────────────
# 4. ADVANCED CYLINDER FINDER
# ────────────────────────────────────────────────
elif page == "Cylinder Finder":
    st.title("🔍 Advanced Cylinder Search")
    
    colA, colB, colC = st.columns(3)
    with colA:
        s_id = st.text_input("Search ID", placeholder="LEO-XXX")
    with colB:
        s_name = st.text_input("Search Customer", placeholder="e.g. Hyderabad Gas")
    with colC:
        s_status = st.selectbox("Filter Status", ["All", "Full", "Empty", "Damaged"])

    # Filtering Logic
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
            condition = st.selectbox("Condition", ["Good", "Dented", "Leaking", "Valve Damage"])
            if st.form_submit_button("Submit Return"):
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
                    st.error(f"Update failed: {e}")

# ────────────────────────────────────────────────
# 6. ADD NEW CYLINDER (With Decimals)
# ────────────────────────────────────────────────
elif page == "Add New Cylinder":
    st.title("Register New Stock")
    with st.form("new_entry_form"):
        c_id = st.text_input("New Cylinder ID")
        cust = st.text_input("Customer Name")
        pin = st.text_input("Location PIN (Numbers Only)", max_chars=6)
        
        # Capacity Dropdown using decimals from LeoGas product list
        cap_val = st.selectbox(
            "Cylinder Capacity (kg)", 
            options=[5.0, 10.0, 14.2, 19.0, 47.5],
            index=2, # Defaults to 14.2
            format_func=lambda x: f"{x} kg"
        )
        
        if st.form_submit_button("Add Cylinder"):
            if not c_id:
                st.error("Please enter a Cylinder ID.")
            else:
                today = datetime.now().date()
                next_due = today + pd.Timedelta(days=1825) # 5 years
                
                # Payload including decimals
                payload = {
                    "Cylinder_ID": str(c_id),
                    "Customer_Name": str(cust),
                    "Location_PIN": int(pin) if pin.isdigit() else 0,
                    "Capacity_kg": float(cap_val), # This sends 14.2 as a float
                    "Fill_Percent": 100,
                    "Status": "Full",
                    "Last_Fill_Date": str(today),
                    "Last_Test_Date": str(today),
                    "Next_Test_Due": str(next_due),
                    "Overdue": False
                }
                
                try:
                    conn.table("cylinders").insert(payload).execute()
                    st.success(f"Cylinder {c_id} ({cap_val}kg) registered!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}. (Tip: Ensure 'Capacity_kg' in Supabase is set to 'numeric' or 'float8')")

