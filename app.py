import os
import json
import random
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
        
        # 搜索过滤
        q = request.args.get('q', '').strip()
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        # 数据分类
        starred = df[df['标星']].to_dict(orient='records')
        
        # 分类展示逻辑
        categories = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]
        cat_data = {}
        for cat in categories:
            # 下方列表只显示未标星的
            items = df[(df['类型'] == cat) & (~df['标星'])].to_dict(orient='records')
            if items:
                cat_data[cat] = items
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, categories=categories)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/toggle/<name>')
def toggle(name):
    sheet = get_worksheet()
    data = sheet.get_all_records()
    for i, row in enumerate(data):
        if str(row.get('名称')).strip() == name.strip():
            current = str(row.get('标星')).upper() in ['TRUE', '1', '是', 'YES']
            sheet.update_cell(i + 2, 5, "TRUE" if not current else "FALSE") # 标星在第5列
            break
    return redirect(url_for('index', q=request.args.get('q', '')))

@app.route('/add', methods=['POST'])
def add():
    sheet = get_worksheet()
    new_row = [
        request.form.get('name'),
        request.form.get('url'),
        request.form.get('type'),
        request.form.get('note'),
        "FALSE" # 默认不标星
    ]
    sheet.append_row(new_row)
    return redirect(url_for('index'))

@app.route('/random')
def random_res():
    sheet = get_worksheet()
    data = sheet.get_all_records()
    res = random.choice(data)
    return redirect(res['网址'])

if __name__ == "__main__":
    app.run()
