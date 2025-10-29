import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. הגדרות עמוד ---
# מגדיר את העמוד לשימוש ברוחב מלא ונותן לו כותרת
st.set_page_config(page_title="פרויקט Triage AI", layout="wide")

# --- 2. פונקציה לטעינת וניקוי הנתונים ---
@st.cache_data  # שומר את הנתונים בזיכרון מטמון לביצועים מהירים
def load_data(csv_file):
    try:
        # טוען את ה-CSV. הכותרת האמיתית נמצאת בשורה 9 (אינדקס 8)
        df = pd.read_csv(csv_file, header=8, encoding='cp1255')
        
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
            'Start': 'Start_Date_Str',
            'Category': 'Resource', # 'Resource' ישמש לקביעת הצבע
            'Days': 'Duration'
        })

        # המרת עמודת התאריך (שהיא טקסט) לאובייקט תאריך
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start_Date_Str'], format='%Y-%m-%d')
        
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
        st.error(f"הקובץ {csv_file} לא נמצא. ודא שהוא באותה תיקייה.")
        return pd.DataFrame()

# --- 4. טעינת הנתונים ---
FILE_PATH = 'GANTT_TAI.xlsx'
df_processed = load_data(FILE_PATH)

if not df_processed.empty:
    
    # --- 5. יצירת הגרף האינטראקטיבי ---
    
    # הגדרת מפת צבעים מותאמת אישית לכל קטגוריה
    categories = df_processed['Resource'].unique()
    # ניתן להוסיף עוד צבעים אם יש יותר קטגוריות
    custom_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA', '#F08A5D', '#B2CC83', '#6E5773']
    
    color_map = {cat: color for cat, color in zip(categories, custom_colors)}

    # הופך את הדאטהפריים לרשימה של מילונים, הפורמט ש-create_gantt דורש
    tasks_list = df_processed.to_dict('records')

    # יצירת הגרף!
    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,          # שימוש בצבעים שהגדרנו
        index_col='Resource',      # העמודה שלפיה יתבצע הקיבוץ והצביעה (הקטגוריה)
        show_colorbar=True,        # מציג מקרא צבעים
        group_tasks=True,          # מקבץ משימות תחת אותה קטגוריה
        showgrid_x=True,           # מציג רשת אנכית
        showgrid_y=True            # מציג רשת אופקית
    )

    # עדכון עיצוב הגרף (גובה, פונטים וכו')
    fig.update_layout(
        title='Gantt Chart: Smart Triage with AI Project',
        xaxis_title='Timeline',
        yaxis_title='Tasks',
        height=800,
        font=dict(family="Arial, sans-serif", size=12)
    )

    # --- 6. הצגת האפליקציה ---
    st.title("📊 לוח גאנט אינטראקטיבי - פרויקט Smart Triage with AI")
    st.write("אפליקציה זו מציגה באופן דינמי את התקדמות הפרויקט על בסיס קובץ ה-CSV.")
    
    # הצגת הגרף של Plotly
    st.plotly_chart(fig, use_container_width=True)
    
    # בונוס: הצגת טבלת הנתונים המעובדת
    with st.expander("הצג את טבלת הנתונים (Data Table)"):
        st.dataframe(df_processed[['Task', 'Resource', 'Start', 'Finish', 'Duration', 'Progress']])
