import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# 1. Page Configuration (wide layout)
st.set_page_config(page_title="לוח גאנט", layout="wide")

# 2. Add Open Sans Hebrew font for the entire site (request 3)
# This is a CSS "hack" that changes the font for all Streamlit elements
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300..800&display=swap');
    
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Function to load and clean data
@st.cache_data
def load_data(excel_file):
    try:
        # Reads the Excel file, with the header at row 9 (index 8)
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days', 'Progress']
        if not all(col in df.columns for col in relevant_cols):
            st.error("שגיאה: חסרות עמודות חיוניות (Milestone description, Category, Start, Days, Progress) בקובץ האקסל.")
            return pd.DataFrame()
            
        df = df[relevant_cols]
        df = df.dropna(subset=['Start', 'Days'])
        
        if df.empty:
            st.warning("לא נמצאו משימות עם תאריך התחלה ומשך בקובץ.")
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
        
        # Calculate finish date (here we leave it as a date object)
        df_gantt['Finish'] = df_gantt.apply(
            lambda row: row['Start'] + timedelta(days=row['Duration']), 
            axis=1
        )
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"הקובץ '{excel_file}' לא נמצא במאגר. ודא שהשם תקין (GANTT_TAI.xlsx).")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"אירעה שגיאה בקריאת קובץ האקסל: {e}")
        return pd.DataFrame()

# 4. Load data (request 2)
FILE_PATH = 'GANTT_TAI.xlsx' # File name updated
df_processed = load_data(FILE_PATH)

# 5. Display the application (without main title request 4)

if not df_processed.empty:
    
    # 6. Calculate date ranges
    project_start_date = df_processed['Start'].min()
    project_start_month = project_start_date.replace(day=1) # First month of the project
    project_end_date = df_processed['Finish'].max()
    today_date = pd.to_datetime(datetime.today().date()) # Today's date

    # 7. New display range selector (requests 5, 6)
    view_option = st.radio(
        "בחר תצוגת ציר זמן:",
        ('הכל', '3 חודשים', 'חודש', 'שבוע'), # The options
        index=0, # Default is "All"
        horizontal=True, # Displays the buttons in one line
    )

    # 8. Create the graph
    
    # The create_gantt function requires dates as text (string)
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-%m-%d')
    
    tasks_list = df_for_gantt.to_dict('records')
    
    # Define colors
    categories = df_processed['Resource'].unique()
    custom_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA', '#F08A5D', '#B2CC83', '#6E5773']
    color_map = {cat: color for cat, color in zip(categories, custom_colors)}

    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True
    )

    # 9. Update layout based on user selection
    
    # Define the dynamic display range
    if view_option == 'שבוע':
        start_range = today_date - timedelta(days=1) # Starts one day before today
        end_range = today_date + timedelta(days=7) # And displays 7 days forward
    elif view_option == 'חודש':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=30)
    elif view_option == '3 חודשים':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=90)
    else: # 'All' (default)
        start_range = project_start_month - timedelta(days=7) # Starts one week before the beginning of the month
        end_range = project_end_date + timedelta(days=15) # We'll add some "padding" at the end of the graph

    # --- THIS IS THE FIX ---
    # The fig.update_layout() command caused the ValueError crash.
    # This direct assignment method avoids the crash.
    
    fig.layout.xaxis.title = 'ציר זמן'
    fig.layout.yaxis.title = 'משימות'
    fig.layout.height = 800
    fig.layout.font = dict(family="Open Sans Hebrew, sans-serif", size=12)
    fig.layout.xaxis.range = [start_range, end_range] # The command that sets the X axis range

    # 10. Add "Today" Line
    fig.add_shape(
        type="line",
        x0=today_date, y0=0,
        x1=today_date, y1=1,
        yref="paper", # The line stretches from bottom (0) to top (1)
        line=dict(color="Red", width=2, dash="dash")
    )
    fig.add_annotation(
        x=today_date,
        y=1.05, # Positioned slightly above the graph
        yref="paper",
        text="היום",
        showarrow=False,
        font=dict(color="Red", family="Open Sans Hebrew, sans-serif")
    )

    # 11. Display the graph
    st.plotly_chart(fig, use_container_width=True)
    
    # The st.expander that showed the table was removed (request 1)

else:
    # Message in case the file was loaded but is empty
    st.error("טעינת הנתונים נכשלה או שלא נמצאו משימות תקינות בקובץ.")
    st.info("אנא ודא שקובץ האקסל (GANTT_TAI.xlsx) תקין ומכיל את העמודות הנדרשות (שורה 9 היא הכותרת).")
