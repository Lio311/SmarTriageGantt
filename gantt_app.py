import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. הגדרות עמוד (רוחב מלא) ---
st.set_page_config(page_title="לוח גאנט", layout="wide")

# --- 2. הוספת פונט Open Sans Hebrew לכל האתר ---
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

# --- 3. פונקציה לטעינת וניקוי הנתונים ---
@st.cache_data
def load_data(excel_file):
    try:
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
        st.error(f"הקובץ '{excel_file}' לא נמצא במאגר. ודא שהשם תקין (GANTT_TAI.xlsx).")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"אירעה שגיאה בקריאת קובץ האקסל: {e}")
        return pd.DataFrame()

# --- 4. טעינת הנתונים ---
FILE_PATH = 'GANTT_TAI.xlsx' 
df_processed = load_data(FILE_PATH)

# --- 5. הצגת האפליקציה ---

if not df_processed.empty:
    
    today_date = pd.to_datetime(datetime.today().date())

    # --- 7. יצירת הגרף ---
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-m-%d')
    
    tasks_list = df_for_gantt.to_dict('records')
    
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

    # --- 8. עדכון פריסה (Layout) - ⭐️ כאן התיקון ⭐️ ---
    fig.update_layout(
        # xaxis_title הוסר מכאן
        yaxis_title='משימות',
        height=800,
        font=dict(family="Open Sans Hebrew, sans-serif", size=12),
        
        # כל ההגדרות של ציר X נמצאות עכשיו בתוך אותו מילון
        xaxis=dict(
            title='ציר זמן', # <-- xaxis_title הועבר לכאן
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1W", # שבוע אחורה מהיום
                         step="week",
                         stepmode="backward"),
                    dict(count=1,
                         label="1M", # חודש אחורה מהיום
                         step="month",
                         stepmode="backward"),
                    dict(count=3,
                         label="3M", # 3 חודשים אחורה מהיום
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
            ),
            type="date"
        )
    )

    # --- 9. הוספת קו "היום" (Today Line) ---
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
        text="היום",
        showarrow=False,
        font=dict(color="Red", family="Open Sans Hebrew, sans-serif")
    )

    # --- 10. הצגת הגרף ---
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("טעינת הנתונים נכשלה או שלא נמצאו משימות תקינות בקובץ.")
    st.info("אנא ודא שקובץ האקסל (GANTT_TAI.xlsx) תקין ומכיל את העמודות הנדרשות (שורה 9 היא הכותרת).")
