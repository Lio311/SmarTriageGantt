import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# --- 1. הגדרות עמוד ---
st.set_page_config(page_title="פרויקט Triage AI - DEBUG", layout="wide")

# ----------------------------------------------------
st.title("🐞 מצב ניפוי באגים (Debug Mode) 🐞")
st.warning("האפליקציה כרגע במצב ניפוי באגים. יוצגו נתונים גולמיים.")
# ----------------------------------------------------

# פונקציה לטעינה ועיבוד הנתונים
def load_and_process_data(excel_file):
    try:
        st.subheader("שלב 1: טעינת קובץ האקסל")
        # אנו מוסיפים sheet_name=None כדי לטעון את *כל* הגיליונות, ואז נבדוק
        # אם יש יותר מגיליון אחד. 'header=8' אומר ששורה 9 היא הכותרת.
        df = pd.read_excel(excel_file, header=8, engine='openpyxl')
        
        st.write(f"קובץ האקסל '{excel_file}' נטען בהצלחה.")
        st.write("5 השורות הראשונות כפי שנקראו מהקובץ (נתונים גולמיים):")
        st.dataframe(df.head())

        st.subheader("שלב 2: ניקוי שורות וטורים ריקים")
        df = df.dropna(how='all').dropna(axis=1, how='all')
        st.write(f"לאחר ניקוי שורות/טורים ריקים, נשארו {len(df)} שורות.")
        st.dataframe(df.head())

        st.subheader("שלב 3: בחירת עמודות רלוונטיות")
        # מנקה רווחים מיותרים משמות העמודות
        df.columns = df.columns.str.strip()
        st.write("שמות העמודות שנמצאו בקובץ (אחרי ניקוי רווחים):")
        st.write(df.columns.tolist())
        
        relevant_cols = ['Milestone description', 'Category', 'Start', 'Days', 'Progress']
        st.write(f"הקוד מחפש את העמודות הבאות: {relevant_cols}")
        
        # בודק אם כל העמודות קיימות לפני שמנסה לגשת אליהן
        missing_cols = [col for col in relevant_cols if col not in df.columns]
        if missing_cols:
            st.error(f"שגיאה קריטית: העמודות הבאות חסרות בקובץ האקסל שלך (או ששמן שונה): {missing_cols}")
            return pd.DataFrame() # מחזיר טבלה ריקה

        df = df[relevant_cols]
        st.write("לאחר בחירת עמודות רלוונטיות:")
        st.dataframe(df.head())

        st.subheader("שלב 4: סינון שורות ללא תאריך ('Start') או משך ('Days')")
        st.write(f"מספר שורות לפני סינון 'Start'/'Days': {len(df)}")
        df_before_drop = df.copy() # שומר עותק לבדיקה
        
        df = df.dropna(subset=['Start', 'Days'])
        
        st.write(f"מספר שורות אחרי סינון 'Start'/'Days': {len(df)}")
        
        if df.empty and not df_before_drop.empty:
            st.error("זו הבעיה! כל השורות נמחקו בשלב 4.")
            st.write("זה אומר שכל השורות היו חסרות ערך (NaN) בעמודות 'Start' או 'Days'.")
            st.write("הנה הנתונים כפי שנראו *לפני* הסינון (שים לב לעמודות 'Start' ו-'Days'):")
            st.dataframe(df_before_drop)
            return pd.DataFrame() # מחזיר טבלה ריקה

        st.success("הנתונים עברו את כל שלבי הסינון! ממשיכים לעיבוד...")

        # --- 3. עיבוד הנתונים לפורמט של גאנט ---
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
        df_gantt['Start'] = df_gantt['Start'].dt.strftime('%Y-%m-%d')
        df_gantt['Finish'] = df_gantt['Finish'].dt.strftime('%Y-%m-%d')
        
        return df_gantt

    except FileNotFoundError:
        st.error(f"הקובץ '{excel_file}' לא נמצא. ודא שהוא במאגר ה-GitHub.")
        return pd.DataFrame()
    except KeyError as e:
        st.error(f"שגיאת 'KeyError'. זה אומר שחסרה עמודה: {e}")
        st.write("בדוק ששמות העמודות בקובץ האקסל (בשורה 9) תואמים בדיוק.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"אירעה שגיאה בלתי צפויה בקריאת הקובץ: {e}")
        st.write("ייתכן שקובץ האקסל פגום או שהגדרת 'header=8' שגויה.")
        return pd.DataFrame()

# --- טעינת הנתונים ---
# ❗️ ודא ששם הקובץ הזה תואם בדיוק למה שנמצא ב-GitHub
FILE_PATH = 'GANTT_TAI.xlsx - Light.csv' 
df_processed = load_and_process_data(FILE_PATH)

# --- 5. הצגת הגרף ---
st.header("--- הצגת התרשים ---")
if not df_processed.empty:
    st.write("מייצר את תרשים הגאנט...")
    
    # הגדרת מפת צבעים מותאמת אישית לכל קטגוריה
    categories = df_processed['Resource'].unique()
    custom_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA', '#F08A5D', '#B2CC83', '#6E5773']
    color_map = {cat: color for cat, color in zip(categories, custom_colors)}

    tasks_list = df_processed.to_dict('records')

    fig = ff.create_gantt(
        tasks_list,
        colors=color_map,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True
    )

    fig.update_layout(
        title='GANTT Chart: Smart Triage with AI Project',
        xaxis_title='Timeline',
        yaxis_title='Tasks',
        height=800,
        font=dict(family="Arial, sans-serif", size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("הצג את טבלת הנתונים המעובדת (Data Table)"):
        st.dataframe(df_processed[['Task', 'Resource', 'Start', 'Finish', 'Duration', 'Progress']])

else:
    st.error("לא ניתן להציג תרשים גאנט מכיוון שהטבלה המעובדת ריקה.")
    st.write("גלול למעלה ובדוק את הפלט של מצב ניפוי הבאגים כדי לראות איפה הנתונים נמחקו.")
