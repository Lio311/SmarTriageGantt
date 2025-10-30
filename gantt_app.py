import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. Page Configuration ---
st.set_page_config(page_title="Gantt Chart", layout="wide")

# --- 2. Font Styling ---
# Load and apply the Open Sans Hebrew font
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300..800&display=swap');
    
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Data Loading Function ---
@st.cache_data
def load_data(excel_file):
    """
    Loads and processes data from the specified Excel file.
    """
    try:
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days', 'Progress']
        if not all(col in df.columns for col in relevant_cols):
            st.error("Error: Missing essential columns (Milestone description, Category, Start, Days, Progress) in the Excel file.")
            return pd.DataFrame()
            
        df = df[relevant_cols]
        df = df.dropna(subset=['Start', 'Days'])
        
        if df.empty:
            st.warning("No tasks with valid Start date and Days duration found in the file.")
            return pd.DataFrame()

        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj',
            'Category': 'Resource', 
            'Days': 'Duration'
        })

        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])
        
        df_gantt['Finish'] = df_gantt.apply(
            lambda row: row['Start'] + timedelta(days=row['Duration']), 
            axis=1
        )
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"Error: The file '{excel_file}' was not found. Please check the file name.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while reading the Excel file: {e}")
        return pd.DataFrame()

# --- 4. Load Data ---
FILE_PATH = 'GANTT_TAI.xlsx' 
df_processed = load_data(FILE_PATH)

# --- 5. Main Application Logic ---
if not df_processed.empty:
    
    # --- 6. Calculate Date Ranges ---
    today_date = pd.to_datetime(datetime.today().date())
    project_start_date = df_processed['Start'].min()
    project_start_month = project_start_date.replace(day=1) # First day of the project's start month
    project_end_date = df_processed['Finish'].max()

    # --- 7. Add Streamlit View Selector (The Button Bar) ---
    # This replaces the Plotly rangeselector
    view_option = st.radio(
        "Select Timeline View:",
        ('All', '3 Months', 'Month', 'Week'), # Options
        index=0, # Default to 'All'
        horizontal=True, # This makes it look like a button bar
    )

    # --- 8. Set Date Range Based on Selection ---
    if view_option == 'Week':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=7)
    elif view_option == 'Month':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=30)
    elif view_option == '3 Months':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=90)
    else: # 'All'
        start_range = project_start_month - timedelta(days=7) # Add padding
        end_range = project_end_date + timedelta(days=15) # Add padding

    # --- 9. Prepare Data for Gantt ---
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-m-%d')
    
    tasks_list = df_for_gantt.to_dict('records')
    
    categories = df_processed['Resource'].unique()
    custom_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA', '#F08A5D', '#B2CC83', '#6E5773']
    color_map = {cat: color for cat, color in zip(categories, custom_colors)}

    # --- 10. Create Gantt Chart ---
    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True
    )

    # --- 11. Update Figure Layout (Simplified) ---
    # This is now safe as we removed the conflicting rangeselector
    fig.update_layout(
        yaxis_title='Tasks',
        xaxis_title='Timeline',
        height=800,
        font=dict(family="Open Sans Hebrew, sans-serif", size=12),
        # Apply the dynamic date range from the st.radio buttons
        xaxis_range=[start_range, end_range]
    )

    # --- 12. Add "Today" Line ---
    fig.add_shape(
        type="line",
        x0=today_date, y0=0,
        x1=today_date, y1=1,
        yref="paper", 
        line=dict(color="Red", width=2, dash="dash")
    )
    
    fig.add_annotation(
        x=today_date,
        y=1.05, 
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="Red", family="Open Sans Hebrew, sans-serif")
    )

    # --- 13. Display Chart ---
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Data could not be loaded or no valid tasks were found.")
    st.info("Please ensure the Excel file (GANTT_TAI.xlsx) is correct and headers are on row 9.")
