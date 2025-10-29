import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# ... (הקוד של st.set_page_config נשאר אותו הדבר) ...

# --- 2. פונקציה לטעינת וניקוי הנתונים ---
@st.cache_data  # שומר את הנתונים בזיכרון מטמון לביצועים מהירים
def load_data(excel_file): # שיניתי את שם המשתנה לבהירות
    try:
        # אנחנו קוראים קובץ אקסל, לא CSV.
        # אנחנו משתמשים ב-engine='openpyxl' שדורש את הספרייה שהוספנו
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        # --- שאר הקוד נשאר כמעט זהה ---
        
        # מנקה שורות וטורים ריקים
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # מנקה רווחים מיותרים משמות העמודות
        df.columns = df.columns.str.strip()
        
        # בוחר רק את העמודות הרלוונטיות
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days', 'Progress']
        df = df[relevant_cols]
        
        # מסיר שורות שבהן חסר תאריך התחלה או משך
        df = df.dropna(subset=['Start', 'Days'])
        
        # --- 3. עיבוד הנתונים לפורמט של גאנט ---
        
        # שינוי שמות עמודות לפורמט ש-Plotly דורש
        df_gantt = df.rename(columns={
            'Milestone description': 'Task',
            'Start': 'Start_Date_Obj', # שיניתי שם כדי למנוע בלבול
            'Category': 'Resource', 
            'Days': 'Duration'
        })

        # עכשיו 'Start' כבר מגיע כאובייקט תאריך מאקסל, 
        # אבל נוודא שזה כך למקרה שזה מגיע כטקסט
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Obj'])
        
        # המרת עמודת המשך (Duration) למספר
        df_gantt['Duration'] = pd.to_numeric(df_gantt['Duration'])

        # חישוב תאריך סיום
        df_gantt['Finish'] = df_gantt.apply(
            lambda row: row['Start'] + timedelta(days=row['Duration']), 
            axis=1
        )
        
        # המרת התאריכים בחזרה למחרוזת (טקסט) - דרישה של Plotly
        df_gantt['Start'] = df_gantt['Start'].dt.strftime('%Y-%m-%d')
        df_gantt['Finish'] = df_gantt['Finish'].dt.strftime('%Y-%m-%d')
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"הקובץ {excel_file} לא נמצא. ודא שהוא באותה תיקייה.")
        return pd.DataFrame()
    except Exception as e:
        # תופס שגיאות כלליות יותר, כולל בעיות עם openpyxl
        st.error(f"אירעה שגיאה בקריאת קובץ האקסל: {e}")
        return pd.DataFrame()

# --- 4. טעינת הנתונים ---
# ⭐️ ודא ששם הקובץ הזה תואם בדיוק למה שנמצא ב-GitHub ⭐️
FILE_PATH = 'GANTT_TAI.xlsx' 
df_processed = load_data(FILE_PATH)

# ... (שאר הקוד להצגת הגרף נשאר זהה) ...
