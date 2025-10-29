import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. Page Configuration ---
# Set the page to wide layout
st.set_page_config(page_title="Gantt Chart", layout="wide")

# --- 2. Font Styling ---
# Load and apply the Open Sans Hebrew font to the app.
# This font will be used even for English text.
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300..800&display=swap');
    
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    .plotly .rangeselector .period-label {
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
        # Read the Excel file, assuming row 9 (index 8) is the header
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        # Clean up data
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        
        # Check for essential columns
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days', 'Progress']
        if not all(col in df.columns for col in relevant_cols):
            st.error("Error: Missing essential columns (Milestone description, Category, Start, Days, Progress) in the Excel file.")
            return pd.DataFrame()
            
        df = df[relevant_cols]
        
        # Drop rows without a start date or duration
        df = df.dropna(subset=['Start', 'Days'])
        
        if df.empty:
            st.warning("No tasks with valid Start date and Days duration found in the file.")
            return pd.DataFrame()

        # Rename columns for Plotly Gantt chart
        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj', # Rename to avoid confusion
            'Category': 'Resource', 
            'Days': 'Duration'
        })

        # Convert data types
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])
        
        # Calculate the finish date
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
    
    today_date = pd.to_datetime(datetime.today().date())

    # --- 6. Prepare Data for Gantt ---
    # Create a copy for Plotly, which requires date strings
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-m-%d')
    
    tasks_list = df_for_gantt.to_dict('records')
    
    # Define colors for categories
    categories = df_processed['Resource'].unique()
    custom_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA', '#F08A5D', '#B2CC83', '#6E5773']
    color_map = {cat: color for cat, color in zip(categories, custom_colors)}

    # --- 7. Create Gantt Chart ---
    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True
    )

    # --- 8. Update Figure Layout (This is the corrected part) ---
    # We modify the 'fig.layout' object properties directly
    # to avoid the 'ValueError' validation conflict.
    
    fig.layout.yaxis.title = 'Tasks'
    fig.layout.height = 800
    fig.layout.font = dict(family="Open Sans Hebrew, sans-serif", size=12)
    fig.layout.xaxis.title = 'Timeline'
    
    # Add the range selector buttons to the xaxis
    fig.layout.xaxis.rangeselector = dict(
        buttons=list([
            dict(count=1,
                 label="1W",
                 step="week",
                 stepmode="backward"),
            dict(count=1,
                 label="1M",
                 step="month",
                 stepmode="backward"),
            dict(count=3,
                 label="3M",
                 step="month",
                 stepmode="backward"),
            dict(step="all",
                 label="All")
        ]),
        font=dict(family="Open Sans Hebrew, sans-serif", size=12),
        bgcolor="#f0f2f6",
        bordercolor="#d1d1d1",
        borderwidth=1,
        activecolor="#e0e0e0"
    )

    # --- 9. Add "Today" Line ---
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

    # --- 10. Display Chart ---
    st.plotly_chart(fig, use_container_width=True)

else:
    # This message shows if data loading failed or returned empty
    st.error("Data could not be loaded or no valid tasks were found.")
    st.info("Please ensure the Excel file (GANTT_TAI.xlsx) is correct and headers are on row 9.")
