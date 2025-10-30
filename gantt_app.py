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
    /* Style all buttons to be full-width *within their column* */
    div[data-testid="stButton"] > button {
        width: 80%;
        height: 5px; 
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
            'Category': 'Resource', # 'Resource' is used for grouping
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
        
        # Append percentage to Task name
        df_gantt['Task'] = df_gantt['Task'] + " (" + df_gantt['Progress'].round(0).astype(int).astype(str) + "%)"
        
        # Clean up category names from potential newlines
        df_gantt['Resource'] = df_gantt['Resource'].str.replace('\n', ' ', regex=False).str.strip()
        
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

    # --- 9. Display Buttons (Centered) ---
    
    def set_view(view):
        """Callback function to set the view in session state"""
        st.session_state.view_option = view

    # --- THIS IS THE CHANGE ---
    # Create 7 columns: spacers on the sides, 5 for buttons in the center
    # The ratio [4.5, 1, 1, 1, 1, 1, 4.5] centers the buttons
    spacer1, col1, col2, col3, col4, col5, spacer2 = st.columns([1.5, 1, 1, 1, 1, 1, 1.5])
    
    with col1:
        st.button("All", on_click=set_view, args=('All',), use_container_width=True)
    with col2:
        st.button("3M", on_click=set_view, args=('3M',), use_container_width=True)
    with col3:
        st.button("1M", on_click=set_view, args=('1M',), use_container_width=True)
    with col4:
        st.button("1W", on_click=set_view, args=('1W',), use_container_width=True)
    with col5:
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

    # Define distinct colors for each CATEGORY
    categories = df_processed['Resource'].unique()
    # Using a predefined list of distinct colors
    color_palette = [
        'rgb(31, 119, 180)', 'rgb(255, 127, 14)', 'rgb(44, 160, 44)', 
        'rgb(214, 39, 40)', 'rgb(148, 103, 189)', 'rgb(140, 86, 75)', 
        'rgb(227, 119, 194)', 'rgb(127, 127, 127)', 'rgb(188, 189, 34)', 
        'rgb(23, 190, 207)'
    ]
    
    # Create the color map {CategoryName: color}
    color_map = {cat: color_palette[i % len(color_palette)] for i, cat in enumerate(categories)}

    # Create the figure
    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,          # Pass the category color dictionary
        index_col='Resource',      # Group by 'Resource' (Category)
        show_colorbar=True,      # Show the category legend on the right
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
    fig.layout.yaxis.title = 'Tasks (Grouped by Category)'
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
