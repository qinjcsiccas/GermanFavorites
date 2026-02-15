import os
import json
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = Flask(__name__)

def get_worksheet():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("环境变量 GOOGLE_CREDS_JSON 缺失")
    
    info = json.loads(creds_json)
    
    # 【核心修正】强制处理换行符，防止 PEM 加载错误
    info['private_key'] = info['private_key'].replace('\\n', '\n') 
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 使用你提供的表格 ID
    sh = client.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
    return sh.get_worksheet(0)

@app.route('/')
def index():
    try:
        sheet = get_worksheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # 清洗：标星在前，分类在后
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        starred = df[df['标星']].to_dict(orient='records')
        others = df[~df['标星']].to_dict(orient='records')
        
        return render_template('index.html', starred=starred, others=others)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/toggle/<name>')
def toggle(name):
    sheet = get_worksheet()
    data = sheet.get_all_records()
    for i, row in enumerate(data):
        if str(row.get('名称')).strip() == name.strip():
            # 切换状态并更新到第 4 列（标星列）
            current = str(row.get('标星')).upper() in ['TRUE', '1', '是', 'YES']
            sheet.update_cell(i + 2, 4, "TRUE" if not current else "FALSE")
            break
    return redirect(url_for('index'))
