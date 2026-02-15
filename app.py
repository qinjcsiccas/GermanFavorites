import os
import json
import random
import time
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = Flask(__name__)

def get_worksheet():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON 缺失")
    info = json.loads(creds_json)
    # 处理 PEM 换行符
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
        # 强制清除表头两端的不可见字符
        df.columns = [c.strip() for c in df.columns]
        df['备注'] = df['备注'].fillna('')
        
        # 统一处理名称字段，防止因空格导致标星失效
        df['名称'] = df['名称'].astype(str).str.strip()
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        
        q = request.args.get('q', '').strip()
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        # 置顶区域
        starred = df[df['标星']].to_dict(orient='records')
        
        # 分类区域：现在保留所有资源，不再过滤已标星的
        categories = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]
        cat_data = {}
        for cat in categories:
            items = df[df['类型'] == cat].to_dict(orient='records')
            if items:
                cat_data[cat] = items
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, categories=categories)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/toggle/<name>')
def toggle(name):
    # 强制对传入的名称进行去空格处理
    target_name = name.strip()
    sheet = get_worksheet()
    data = sheet.get_all_records()
    
    for i, row in enumerate(data):
        # 解决 Slow German 等网站无法匹配的问题：两侧全部去空格对比
        if str(row.get('名称', '')).strip() == target_name:
            current = str(row.get('标星', '')).upper() in ['TRUE', '1', '是', 'YES']
            new_status = "TRUE" if not current else "FALSE"
            # 更新第 5 列 (E 列)
            sheet.update_cell(i + 2, 5, new_status)
            break
            
    return redirect(url_for('index', q=request.args.get('q', ''), _t=time.time()))

@app.route('/add', methods=['POST'])
def add():
    sheet = get_worksheet()
    new_row = [
        request.form.get('name').strip(),
        request.form.get('url').strip(),
        request.form.get('type'),
        request.form.get('note').strip(),
        "FALSE" 
    ]
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
