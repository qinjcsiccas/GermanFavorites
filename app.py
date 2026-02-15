import os
import json
import random
import time
import re
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = Flask(__name__)

# 预处理：移除所有空白、转小写、移除特殊字符，生成纯净ID
def slugify(text):
    if not text: return ""
    return re.sub(r'\W+', '', str(text)).lower()

def get_worksheet():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON 缺失")
    info = json.loads(creds_json)
    info['private_key'] = info['private_key'].replace('\\n', '\n')
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
    return sh.get_worksheet(0)

@app.route('/')
def index():
    try:
        sheet = get_worksheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [c.strip() for c in df.columns]
        df['备注'] = df['备注'].fillna('')
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        
        # 为前端生成一个“脱水ID”，用于安全传输和匹配
        df['clean_id'] = df['名称'].apply(slugify)
        
        q = request.args.get('q', '').strip()
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        starred = df[df['标星']].to_dict(orient='records')
        categories = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]
        cat_data = {cat: df[df['类型'] == cat].to_dict(orient='records') for cat in categories if not df[df['类型'] == cat].empty}
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/toggle/<clean_id>')
def toggle(clean_id):
    sheet = get_worksheet()
    data = sheet.get_all_records()
    
    # 在后端遍历，通过影子索引匹配
    for i, row in enumerate(data):
        row_name = str(row.get('名称', ''))
        if slugify(row_name) == clean_id:
            # 找到目标行，切换标星状态
            current = str(row.get('标星', '')).upper() in ['TRUE', '1', '是', 'YES']
            new_status = "TRUE" if not current else "FALSE"
            # 锁定第 5 列 (E列) 更新
            sheet.update_cell(i + 2, 5, new_status)
            break
            
    return redirect(url_for('index', q=request.args.get('q', ''), _t=time.time()))

@app.route('/add', methods=['POST'])
def add():
    sheet = get_worksheet()
    new_row = [request.form.get('name').strip(), request.form.get('url').strip(), 
               request.form.get('type'), request.form.get('note').strip(), "FALSE"]
    sheet.append_row(new_row)
    return redirect(url_for('index'))

@app.route('/random')
def random_res():
    sheet = get_worksheet()
    data = sheet.get_all_records()
    if data:
        res = random.choice(data)
        return redirect(res['网址'])
    return redirect(url_for('index'))
