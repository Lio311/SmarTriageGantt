import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. Page Configuration ---
st.set_page_config(layout="wide", page_title="SmarTriage Gantt")

# --- 2. Custom CSS Injection ---
st.markdown("""
    <style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300..800&display=swap');
    
    /* Apply font to all elements */
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    
    /* Style for filter buttons: smaller and closer */
    div[data-testid="stButton"] > button {
        width: 60px;
        height: 25px;
        font-size: 8px;
        padding: 0px;
        min-width: auto;
        margin: 0 1px;
    }
    
    /* CSS fix to hide the Plotly modebar */
    div[data-testid="stPlotlyChart"] .modebar {
        display: none !important;
    }
    
    /* Hide Plotly's default rangeselector */
    .plotly .rangeselector {
        display: none !important;
    }
    
    /* Hide Streamlit's header and small text elements */
    small, .stApp > header, [class*="stMarkdown"] small {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Page Title ---
st.markdown("<h1 style='text-align: center; font-size: 40px;'>SmarTriage Gantt</h1>", unsafe_allow_html=True)

# --- 4. Helper Functions ---

def calculate_progress(row, today):
    """Calculates the progress percentage of a task based on today's date."""
    start_date = row['Start']
    duration = row['Duration']
    if today < start_date:
        return 0.0
    if duration <= 0:
        return 0.0
    
    days_passed = (today - start_date).days + 1
    progress = (days_passed / duration)
    # Cap progress at 100%
    return min(progress, 1.0) * 100

@st.cache_data
def load_data(excel_file):
    """
    Loads and processes the Gantt chart data from the specified Excel file.
    """
    try:
        # Read the Excel file, skipping the first 8 rows
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        # Clean up the DataFrame
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        
        # Check for essential columns
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days']
        if not all(col in df.columns for col in relevant_cols):
            st.error("Error: Missing essential columns (Milestone description, Category, Start, Days) in the Excel file.")
            return pd.DataFrame()
        
        df = df[relevant_cols]
        df = df.dropna(subset=['Start', 'Days'])
        
        if df.empty:
            st.warning("No tasks with valid Start date and Days duration found in the file.")
            return pd.DataFrame()

        # Rename columns for use with ff.create_gantt
        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj',
            'Category': 'Resource',
            'Days': 'Duration'
        })

        # Fill missing 'Resource' (Category) to prevent 'undefined' in the chart
        df_gantt['Resource'] = df_gantt['Resource'].fillna('Uncategorized')

        # Convert data types for processing
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])
        df_gantt['Finish'] = df_gantt.apply(lambda row: row['Start'] + timedelta(days=row['Duration']), axis=1)

        # Calculate progress and append it to the task name
        today = pd.to_datetime(datetime.today().date())
        df_gantt['Progress'] = df_gantt.apply(lambda row: calculate_progress(row, today), axis=1)
        df_gantt['Task'] = df_gantt['Task'] + " (" + df_gantt['Progress'].round(0).astype(int).astype(str) + "%)"
        
        # Clean up resource names
        df_gantt['Resource'] = df_gantt['Resource'].str.replace('\n', ' ', regex=False).str.strip()
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"Error: The file '{excel_file}' was not found.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while reading the Excel file: {e}")
        return pd.DataFrame()

# --- 5. Data Loading and Session State ---
FILE_PATH = 'GANTT_TAI.xlsx'  
df_processed = load_data(FILE_PATH)

# Initialize session state for view options
if 'view_option' not in st.session_state:
    st.session_state.view_option = 'All'
if 'chart_key' not in st.session_state:
    st.session_state.chart_key = 0

# --- 6. Main App Logic ---
if not df_processed.empty:
    # Calculate project boundaries
    project_start_date = df_processed['Start'].min()
    project_start_month = project_start_date.replace(day=1)
    project_end_date = df_processed['Finish'].max()
    today_date = pd.to_datetime(datetime.today().date())

    # --- 6a. Button Click Handlers ---
    def set_view(view):
        st.session_state.view_option = view

    def restart_chart():
        st.session_state.view_option = 'All'
        st.session_state.chart_key += 1 # Force re-render

    # --- 6b. Filter Buttons ---
    # Centered buttons with spacers and compact layout
    spacer1, col1, col2, col3, col4, col5, spacer2 = st.columns([4, 0.5, 0.5, 0.5, 0.5, 0.5, 4])
    with col1:
        st.button("All", on_click=restart_chart, use_container_width=True)
    with col2:
        st.button("3M", on_click=set_view, args=('3M',), use_container_width=True)
    with col3:
        st.button("1M", on_click=set_view, args=('1M',), use_container_width=True)
    with col4:
        st.button("1W", on_click=set_view, args=('1W',), use_container_width=True)
    with col5:
        st.button("Restart", on_click=restart_chart, use_container_width=True)

    # --- 6c. Chart Preparation ---
    view_option = st.session_state.view_option
    
    # Format dates as strings for Plotly
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-%m-%d')
    tasks_list = df_for_gantt.to_dict('records')

    # Define color map for categories
    color_map = {
        'Planning & Preparation': '#009C7C',
        'Development & Implementation': '#A3D65C',
        'Documentation': '#4E76E0',
        'Evaluation & Visual Interface': '#C40C0C',
        'Progress Monitoring & Mentorship': '#FFCA28',
        'Bureaucracy & Procurement': '#20C4F4',
        'Uncategorized': '#808080' # Color for the fallback category
    }

    # Dynamically add colors for any new, undefined categories
    categories_in_data = df_processed['Resource'].unique()
    fallback_colors = ['#808080', '#A4D65E', '#FFE000']
    color_index = 0
    for cat in categories_in_data:
        if cat not in color_map:
            color_map[cat] = fallback_colors[color_index % len(fallback_colors)]
            color_index += 1

    # --- 6d. Gantt Figure Creation ---
    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True
    )
    
    # Hide the default Plotly title
    fig.update_layout(title="")

    # Hide the rangeselector completely
    fig.update_xaxes(rangeselector=dict(visible=False))

    # Apply date range based on the selected view option
    if view_option == '1W':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=7)
    elif view_option == '1M':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=30)
    elif view_option == '3M':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=90)
    else: # 'All'
        start_range = project_start_month - timedelta(days=7)
        end_range = project_end_date + timedelta(days=15)

    # Apply final layout adjustments
    fig.layout.xaxis.title = 'Timeline'
    fig.layout.yaxis.title = 'Tasks (Grouped by Category)'
    fig.layout.height = 800
    fig.layout.font = dict(family="Open Sans Hebrew, sans-serif", size=12)
    fig.layout.xaxis.range = [start_range, end_range]

    # Add the "Today" line
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

    # --- 6e. Display Chart ---
    # Use a dynamic key to force re-render on 'Restart'
    chart_key = f"gantt_chart_{st.session_state.chart_key}"
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key)

else:
    # Fallback message if data loading fails
    st.error("Data loading failed or no valid tasks were found.")
    st.info("Please ensure the Excel file (GANTT_TAI.xlsx) is correct and headers are on row 9.")
