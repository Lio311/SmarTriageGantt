import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. הגדרות עמוד (רוחב מלא) ---
st.set_page_config(page_title="לוח גאנט", layout="wide")

# --- 2. הוספת פונט Open Sans Hebrew לכל האתר (בקשה 3) ---
# זהו "האק" CSS שמשנה את הפונט של כל רכיבי Streamlit
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300..800&display=swap');
    
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. פונקציה לטעינת וניקוי הנתונים ---
@st.cache_data
def load_data(excel_file):
    try:
        # קורא את קובץ האקסל, עם הכותרת בשורה 9 (אינדקס 8)
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

        # --- עיבוד הנתונים לפורמט של גאנט ---
        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj',
            'Category': 'Resource', 
            'Days': 'Duration'
        })

        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])
        
        # חישוב תאריך סיום (כאן נשאיר אותו כאובייקט תאריך)
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

# --- 4. טעינת הנתונים (בקשה 2) ---
FILE_PATH = 'GANTT_TAI.xlsx' # שם הקובץ עודכן
df_processed = load_data(FILE_PATH)

# --- 5. הצגת האפליקציה (בלי כותרת ראשית - בקשה 4) ---

if not df_processed.empty:
    
    # --- 6. חישוב טווחי תאריכים ---
    project_start_date = df_processed['Start'].min()
    project_start_month = project_start_date.replace(day=1) # תחילת חודש הפרויקט
    project_end_date = df_processed['Finish'].max()
    today_date = pd.to_datetime(datetime.today().date()) # התאריך של היום

    # --- 7. בורר טווחי תצוגה חדש (בקשות 5, 6) ---
    view_option = st.radio(
        "בחר תצוגת ציר זמן:",
        ('הכל', '3 חודשים', 'חודש', 'שבוע'), # האפשרויות
        index=0, # ברירת המחדל היא "הכל"
        horizontal=True, # מציג את הכפתורים בשורה אחת
    )

    # --- 8. יצירת הגרף ---
    
    # הפונקציה create_gantt דורשת תאריכים כטקסט (string)
    df_for_gantt = df_processed.copy()
    df_for_gantt['Start'] = df_for_gantt['Start'].dt.strftime('%Y-%m-%d')
    df_for_gantt['Finish'] = df_for_gantt['Finish'].dt.strftime('%Y-%m-%d')
    
    tasks_list = df_for_gantt.to_dict('records')
    
    # הגדרת צבעים
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

    # --- 9. עדכון פריסה (Layout) לפי בחירת המשתמש ---
    
    # הגדרת טווח התצוגה הדינמי
    if view_option == 'שבוע':
        start_range = today_date - timedelta(days=1) # מתחיל יום לפני היום
        end_range = today_date + timedelta(days=7) # ומציג 7 ימים קדימה
    elif view_option == 'חודש':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=30)
    elif view_option == '3 חודשים':
        start_range = today_date - timedelta(days=1)
        end_range = today_date + timedelta(days=90)
    else: # 'הכל' (ברירת מחדל)
        start_range = project_start_month - timedelta(days=7) # מתחיל שבוע לפני תחילת החודש
        end_range = project_end_date + timedelta(days=15) # נוסיף קצת "רווח" בסוף הגרף

    fig.update_layout(
        # title='Project Timeline', # הכותרת בתוך הגרף הוסרה
        xaxis_title='ציר זמן',
        yaxis_title='משימות',
        height=800,
        font=dict(family="Open Sans Hebrew, sans-serif", size=12),
        xaxis_range=[start_range, end_range] # הפקודה שקובעת את טווח ציר ה-X
    )

    # --- 10. הוספת קו "היום" (Today Line) ---
    fig.add_shape(
        type="line",
        x0=today_date, y0=0,
        x1=today_date, y1=1,
        yref="paper", # הקו נמתח מלמטה (0) עד למעלה (1)
        line=dict(color="Red", width=2, dash="dash")
    )
    fig.add_annotation(
        x=today_date,
        y=1.05, # מיקום קצת מעל הגרף
        yref="paper",
        text="היום",
        showarrow=False,
        font=dict(color="Red", family="Open Sans Hebrew, sans-serif")
    )

    # --- 11. הצגת הגרף ---
    st.plotly_chart(fig, use_container_width=True)
    
    # הוסר ה-st.expander שהציג את הטבלה (בקשה 1)

else:
    # הודעה למקרה שהקובץ נטען אך הוא ריק
    st.error("טעינת הנתונים נכשלה או שלא נמצאו משימות תקינות בקובץ.")
    st.info("אנא ודא שקובץ האקסל (GANTT_TAI.xlsx) תקין ומכיל את העמודות הנדרשות (שורה 9 היא הכותרת).")

