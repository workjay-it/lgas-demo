import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# ────────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ────────────────────────────────────────────────
# This automatically uses the 'url' and 'key' from your Streamlit Secrets
conn = st.connection("supabase", type=SupabaseConnection)

@st.cache_data(ttl=60)  # Cache for 1 minute to save on API calls
def load_supabase_data():
    try:
        # Fetch all rows from the 'cylinders' table
        response = conn.table("cylinders").select("*").execute()
        df = pd.DataFrame(response.data)
        
        # Data Cleaning
        if not df.empty:
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
        colA, colB, colC = st.columns(3)
        colA.metric("Total Cylinders", len(df))
        colB.metric("Overdue for Test", df["Overdue"].sum())
        colC.metric("Active Units", len(df[df["Status"] == "In Use"]))
        
        st.subheader("Cylinder Inventory")
        st.dataframe(df.sort_values("Next_Test_Due"), use_container_width=True)
    else:
        st.warning("No data found in Supabase. Please add your first cylinder.")

# ────────────────────────────────────────────────
# 4. RETURN & PENALTY LOG (The "Moving On" Logic)
# ────────────────────────────────────────────────
elif page == "Return & Penalty Log":
    st.title("Cylinder Return Portal")
    
    return_id = st.selectbox("Scan/Select Cylinder ID", options=df["Cylinder_ID"].unique())
    
    if return_id:
        row = df[df["Cylinder_ID"] == return_id].iloc[0]
        st.info(f"Customer: {row['Customer_Name']} | Due Date: {row['Next_Test_Due'].date()}")

        with st.form("audit_form"):
            condition = st.selectbox("Return Condition", ["Good", "Dented", "Valve Damaged", "Leaking"])
            
            # Auto-calculate Penalty
            fine = 0
            if condition != "Good": fine += 500
            if row["Overdue"]: fine += 1000
            
            st.warning(f"Total Calculated Penalty: ₹{fine}")
            
            if st.form_submit_button("Confirm Return & Update Cloud"):
                # UPDATE SUPABASE: Change status to Empty/Damaged
                new_status = "Empty" if condition == "Good" else "Damaged"
                conn.table("cylinders").update({"Status": new_status, "Fill_Percent": 0}).eq("Cylinder_ID", return_id).execute()
                
                st.success(f"Cylinder {return_id} updated in Supabase!")
                st.cache_data.clear()
                st.rerun()

# ────────────────────────────────────────────────
# 5. ADD NEW CYLINDER
# ────────────────────────────────────────────────
elif page == "Add New Cylinder":
    st.title("Register New Stock")
    with st.form("new_entry"):
        c_id = st.text_input("Cylinder ID (Unique)")
        cust = st.text_input("Customer Name")
        pin = st.text_input("Location PIN", max_chars=6)
        
        if st.form_submit_button("Push to Database"):
            if c_id in df["Cylinder_ID"].values:
                st.error("This ID already exists!")
            else:
                new_row = {
                    "Cylinder_ID": c_id,
                    "Customer_Name": cust,
                    "Location_PIN": pin,
                    "Status": "Full",
                    "Next_Test_Due": (datetime.now() + pd.Timedelta(days=1825)).strftime("%Y-%m-%d"),
                    "Overdue": False
                }
                # INSERT INTO SUPABASE
                conn.table("cylinders").insert(new_row).execute()
                st.success("Cylinder saved to cloud!")
                st.cache_data.clear()
                st.rerun()
st.markdown("---")

st.caption("Cylinder Tracking Demo • Hyderabad • February 2026 • Built with Streamlit")
