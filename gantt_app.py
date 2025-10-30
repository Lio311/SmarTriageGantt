import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 0. Clear Cache on Every Run ---
st.cache_data.clear()

# --- 1. Page Configuration (wide layout) ---
st.set_page_config(page_title="Gantt Chart", layout="wide")

# --- 2. Font Styling ---
# This CSS applies the font globally
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300..800&display=swap');
    
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    /* Style all buttons to be full-width */
    div[data-testid="stButton"] > button {
        width: 100%;
        height: 40px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Helper Functions for Progress Calculation ---

def calculate_progress(row, today):
    """
    Calculates the progress percentage (0-100).
    Logic: (days_passed / duration)
    """
    start_date = row['Start']
    duration = row['Duration']
    
    if today < start_date:
        return 0.0
    if duration <= 0:
        return 0.0

    # Calculate days passed (+1 to include the start day)
    days_passed = (today - start_date).days + 1
    
    progress = (days_passed / duration)
    
    # Cap at 1.0 (100%) and convert to 0-100 scale
    return min(progress, 1.0) * 100

def get_progress_color_name(p):
    """
    Returns a color string (name) based on the progress percentage.
    """
    if p < 25:
        return 'Red (0-24%)'
    if p < 50:
        return 'Yellow (25-49%)'
    if p < 75:
        return 'Orange (50-74%)'
    return 'Green (75-100%)'

# --- 4. Function to load and clean data ---
@st.cache_data
def load_data(excel_file):
    """
    Loads, cleans, and processes data from the Excel file.
    """
    try:
        # Reads the Excel file, with the header at row 9 (index 8)
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days']
        # Check for essential columns
        if not all(col in df.columns for col in relevant_cols):
            st.error("Error: Missing essential columns (Milestone description, Category, Start, Days) in the Excel file.")
            return pd.DataFrame()
            
        df = df[relevant_cols]
        df = df.dropna(subset=['Start', 'Days'])
        
        if df.empty:
            st.warning("No tasks with valid Start date and Days duration found in the file.")
            return pd.DataFrame()

        # Process data into Gantt format
        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj',
            'Category': 'Resource', 
            'Days': 'Duration'
        })

        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])
        
        # Calculate finish date
        df_gantt['Finish'] = df_gantt.apply(
            lambda row: row['Start'] + timedelta(days=row['Duration']), 
            axis=1
        )
        
        # --- Apply Progress Logic ---
        today = pd.to_datetime(datetime.today().date())
        
        # Create 'Progress' column (0-100) for the shading
        df_gantt['Progress'] = df_gantt.apply(lambda row: calculate_progress(row, today), axis=1)
        
        # Create 'Color' column for grouping
        df_gantt['Color'] = df_gantt['Progress'].apply(get_progress_color_name)
        
        # Append percentage to Task name
        df_gantt['Task'] = df_gantt['Task'] + " (" + df_gantt['Progress'].round(0).astype(int).astype(str) + "%)"
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"Error: The file '{excel_file}' was not found. Please check the file name.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while reading the Excel file: {e}")
        return pd.DataFrame()

# --- 5. Load data ---
FILE_PATH = 'GANTT_TAI.xlsx' 
df_processed = load_data(FILE_PATH)

# --- 6. Initialize Session State for View Selector ---
if 'view_option' not in st.session_state:
    st.session_state.view_option = 'All' # Default view

# --- 7. Display the application ---
if not df_processed.empty:
    
    # --- 8. Calculate date ranges ---
    project_start_date = df_processed['Start'].min()
    project_start_month = project_start_date.replace(day=1) 
    project_end_date = df_processed['Finish'].max()
    today_date = pd.to_datetime(datetime.today().date()) 

    # --- 9. Display Buttons (Replaces Radio Buttons) ---
    
    def set_view(view):
        """Callback function to set the view in session state"""
        st.session_state.view_option = view

    # Create 5 columns for the 5 buttons
    cols = st.columns(5)
    
    with cols[0]:
        st.button("All", on_click=set_view, args=('All',), use_container_width=True)
    with cols[1]:
        st.button("3M", on_click=set_view, args=('3M',), use_container_width=True)
    with cols[2]:
        st.button("1M", on_click=set_view, args=('1M',), use_container_width=True)
    with cols[3]:
        st.button("1W", on_click=set_view, args=('1W',), use_container_width=True)
    with cols[4]:
        # Restart button also sets the view to 'All'
        st.button("Restart", on_click=set_view, args=('All',), use_container_width=True)

    # Read the current view option from session state
    view_option = st.session_state.view_option

    # --- 10. Create the graph ---
    # Prepare data for Plotly (dates as strings)
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-%m-%d')
    
    tasks_list = df_for_gantt.to_dict('records')

    # --- THIS IS THE FIX ---
    # We must use explicit RGB strings instead of simple names like 'red'
    # to avoid the TypeError in Plotly's color parser.
    color_map = {
        'Red (0-24%)': 'rgb(239, 83, 80)',      # Red
        'Yellow (25-49%)': 'rgb(255, 241, 118)', # Yellow
        'Orange (50-74%)': 'rgb(255, 167, 38)', # Orange
        'Green (75-100%)': 'rgb(102, 187, 106)' # Green
    }

    # Create the figure
    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,          # Pass the color dictionary
        index_col='Color',         # Group by the 'Color' column
        show_colorbar=True,      # ⭐️ This shows the legend on the right ⭐️
        group_tasks=True,          # This will create the groups
        showgrid_x=True,
        showgrid_y=True
    )

    # --- 11. Update layout based on user selection ---
    if view_option == '1W':
        start_range = today_date - timedelta(days=1) 
        end_range = today_date + timedelta(days=7) 
    elif view_option == '1M':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=30)
    elif view_option == '3M':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=90) 
    else: # 'All' (default)
        start_range = project_start_month - timedelta(days=7) 
        end_range = project_end_date + timedelta(days=15) 

    # --- 12. Apply Layout Updates (The Safe Way) ---
    # This direct assignment avoids the ValueError
    
    fig.layout.xaxis.title = 'Timeline'
    fig.layout.yaxis.title = 'Tasks (Grouped by Progress)'
    fig.layout.height = 800
    fig.layout.font = dict(family="Open Sans Hebrew, sans-serif", size=12)
    fig.layout.xaxis.range = [start_range, end_range] # Set the X-axis range

    # --- 13. Add "Today" Line ---
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

    # --- 14. Display the graph ---
    # config={'displayModeBar': False} hides the Plotly toolbar
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    # Message in case the file was loaded but is empty
    st.error("Data loading failed or no valid tasks were found.")
    st.info("Please ensure the Excel file (GANTT_TAI.xlsx) is correct and headers are on row 9.")
