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

# 影子索引函数：移除所有空白、转小写、移除特殊字符
def slugify(text):
    if not text: return ""
    # 彻底脱水：只保留字母和数字
    return re.sub(r'\W+', '', str(text)).lower()

# 注册为 Jinja2 过滤器，解决报错的核心步骤
app.jinja_env.filters['slugify'] = slugify

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
        
        q = request.args.get('q', '').strip()
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        starred = df[df['标星']].to_dict(orient='records')
        
        # 保持分类全量展示，置顶不消失
        categories = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]
        cat_data = {cat: df[df['类型'] == cat].to_dict(orient='records') for cat in categories if not df[df['类型'] == cat].empty}
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, categories=categories)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/toggle/<clean_id>')
def toggle(clean_id):
    sheet = get_worksheet()
    data = sheet.get_all_records()
    for i, row in enumerate(data):
        # 后端同样使用 slugify 进行影子匹配，无视任何空格
        if slugify(row.get('名称', '')) == clean_id:
            current = str(row.get('标星', '')).upper() in ['TRUE', '1', '是', 'YES']
            new_status = "TRUE" if not current else "FALSE"
            sheet.update_cell(i + 2, 5, new_status) # 假设标星在 E 列
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
