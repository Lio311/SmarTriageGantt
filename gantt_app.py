import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. הגדרות עמוד ---
st.set_page_config(page_title="פרויקט Triage AI", layout="wide")

# --- 2. פונקציה לטעינת וניקוי הנתונים (הגרסה הנקייה) ---
@st.cache_data
def load_data(excel_file):
    try:
        # קורא את קובץ האקסל, עם הכותרת בשורה 9 (אינדקס 8)
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        # מנקה שורות וטורים ריקים
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # מנקה רווחים מיותרים משמות העמודות
        df.columns = df.columns.str.strip()
        
        # בודק אם העמודות החיוניות קיימות
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days', 'Progress']
        if not all(col in df.columns for col in relevant_cols):
            st.error("שגיאה: חסרות עמודות חיוניות (Milestone description, Category, Start, Days, Progress) בקובץ האקסל.")
            return pd.DataFrame()
            
        df = df[relevant_cols]
        
        # מסיר שורות שבהן חסר תאריך התחלה או משך
        df = df.dropna(subset=['Start', 'Days'])
        
        if df.empty:
            st.warning("לא נמצאו משימות עם תאריך התחלה ומשך בקובץ.")
            return pd.DataFrame()

        # --- 3. עיבוד הנתונים לפורמט של גאנט ---
        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj', # משנה שם כדי למנוע בלבול
            'Category': 'Resource', 
            'Days': 'Duration'
        })

        # המרת עמודות לתאריכים ומספרים
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])
        
        # חישוב תאריך סיום (כאן נשאיר אותו כאובייקט תאריך)
        df_gantt['Finish'] = df_gantt.apply(
            lambda row: row['Start'] + timedelta(days=row['Duration']), 
            axis=1
        )
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"הקובץ '{excel_file}' לא נמצא במאגר.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"אירעה שגיאה בקריאת קובץ האקסל: {e}")
        return pd.DataFrame()

# --- 4. טעינת הנתונים ---
FILE_PATH = 'GANTT_TAI.xlsx' 
df_processed = load_data(FILE_PATH)

# --- 5. הצגת האפליקציה ---
st.title("📊 לוח גאנט אינטראקטיבי - פרויקט Smart Triage with AI")

if not df_processed.empty:
    
    # --- 6. חישוב טווחי תאריכים ---
    project_start_date = df_processed['Start'].min()
    # בהתאם לבקשתך: נחשב את היום הראשון בחודש של תחילת הפרויקט
    project_start_month = project_start_date.replace(day=1)
    
    project_end_date = df_processed['Finish'].max()
    today_date = pd.to_datetime(datetime.today().date()) # התאריך של היום, בלי שעה

    # --- 7. הוספת בורר תצוגה ---
    view_option = st.radio(
        "בחר תצוגת ציר זמן:",
        ('הצג מתחילת הפרויקט', 'הצג מהיום'), # האפשרויות
        horizontal=True, # מציג את הכפתורים בשורה אחת
    )

    # --- 8. יצירת הגרף ---
    
    # הפונקציה create_gantt דורשת תאריכים כטקסט (string)
    # ניצור עותק זמני עם הפורמט הנכון
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
    if view_option == 'הצג מהיום':
        start_range = today_date - timedelta(days=7) # מתחיל שבוע לפני היום
    else: # 'הצג מתחילת הפרויקט'
        start_range = project_start_month - timedelta(days=7) # מתחיל שבוע לפני תחילת החודש

    # נוסיף קצת "רווח" בסוף הגרף
    end_range = project_end_date + timedelta(days=15)

    fig.update_layout(
        title='Project Timeline',
        xaxis_title='Timeline',
        yaxis_title='Tasks',
        height=800,
        font=dict(family="Arial, sans-serif", size=12),
        # הפקודה שקובעת את טווח ציר ה-X
        xaxis_range=[start_range, end_range] 
    )

    # --- 10. הוספת קו "היום" (Today Line) ---
    fig.add_shape(
        type="line",
        x0=today_date, y0=0,
        x1=today_date, y1=1,
        yref="paper", # הקו נמתח מלמטה (0) עד למעלה (1)
        line=dict(color="Red", width=2, dash="dash")
    )
    # הוספת טקסט מעל הקו
    fig.add_annotation(
        x=today_date,
        y=1.05, # מיקום קצת מעל הגרף
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="Red")
    )

    # --- 11. הצגת הגרף והטבלה ---
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("הצג את טבלת הנתונים המלאה (Data Table)"):
        # מציג את הטבלה עם עמודות התאריך כפי שחושבו
        st.dataframe(df_processed[['Task', 'Resource', 'Start', 'Finish', 'Duration', 'Progress']])

else:
    # הודעה למקרה שהקובץ נטען אך הוא ריק
    st.error("טעינת הנתונים נכשלה או שלא נמצאו משימות תקינות בקובץ.")
    st.info("אנא ודא שקובץ האקסל תקין ומכיל את העמודות הנדרשות (שורה 9 היא הכותרת).")
