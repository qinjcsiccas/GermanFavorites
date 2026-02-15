import os
import json
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = Flask(__name__)

def get_worksheet():
    # 从环境变量读取私钥信息，解决安全隐患
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("未在 Vercel 环境变量中找到 GOOGLE_CREDS_JSON")
    
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 你的 Spreadsheet ID
    sh = client.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
    return sh.get_worksheet(0)

@app.route('/')
def index():
    try:
        sheet = get_worksheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # 强制格式化列名，防止空格导致匹配失败
        df.columns = [c.strip() for c in df.columns]
        
        # 标星逻辑兼容
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        
        # 排序：标星的在前，未标星的在后
        starred = df[df['标星'] == True].to_dict(orient='records')
        others = df[df['标星'] == False].to_dict(orient='records')
        
        return render_template('index.html', starred=starred, others=others)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/toggle/<name>')
def toggle(name):
    sheet = get_worksheet()
    data = sheet.get_all_records()
    for i, row in enumerate(data):
        if str(row.get('名称')).strip() == name.strip():
            # 切换布尔值并写回第 4 列 (D列) 或第 5 列 (E列)，请根据你表格实际情况调整
            # 假设“标星”在第 4 列
            current_star = str(row.get('标星')).upper() in ['TRUE', '1', '是', 'YES']
            new_val = "TRUE" if not current_star else "FALSE"
            sheet.update_cell(i + 2, 4, new_val) 
            break
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run()
