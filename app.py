import os
import json
import random
import time
import re
from flask import Flask, render_template, request, redirect, url_for, session
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "german_study_2026_secret")

# 影子索引函数：彻底移除空白进行匹配
def slugify(text):
    if not text: return ""
    return re.sub(r'\W+', '', str(text)).lower()

app.jinja_env.filters['slugify'] = slugify

# 定义全局五大类
UI_CATEGORIES = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]

# 定义初始化数据：注册成功后自动填入
INITIAL_RESOURCES = [
    ["DW Learn German", "https://learngerman.dw.com/", "系统学习", "官方分级课程 (A1-C1)", "FALSE"],
    ["Dict.cc", "https://www.dict.cc/", "词典工具", "经典德英词典", "FALSE"],
    ["Duolingo", "https://www.duolingo.com/", "移动应用", "多邻国趣味打卡", "FALSE"],
    ["YourGermanTeacher", "https://www.youtube.com/@YourGermanTeacher", "影音视听", "详尽语法讲解", "FALSE"]
]

def get_gc():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    info = json.loads(creds_json)
    info['private_key'] = info['private_key'].replace('\\n', '\n')
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

def get_user_sheet(username=None):
    gc = get_gc()
    sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
    target = username if username else "Users"
    try:
        return sh.worksheet(target)
    except gspread.exceptions.WorksheetNotFound:
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password_raw = request.form.get('password')
        
        gc = get_gc()
        sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
        user_sheet = sh.worksheet("Users")
        
        if any(str(u.get('username')).strip() == username for u in user_sheet.get_all_records()):
            return "用户名已存在"
            
        # 1. 记录账号
        password_hash = generate_password_hash(password_raw)
        user_sheet.append_row([username, password_hash])
        
        # 2. 创建子表并初始化
        new_ws = sh.add_worksheet(title=username, rows="100", cols="10")
        # 写入表头
        new_ws.append_row(["名称", "网址", "类型", "备注", "标星"])
        # 批量写入初始内容
        new_ws.append_rows(INITIAL_RESOURCES)
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    starred = []
    cat_data = {}
    q = request.args.get('q', '').strip()
    
    try:
        sheet = get_user_sheet(session['user'])
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [c.strip() for c in df.columns]
        df['备注'] = df['备注'].fillna('')
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        starred = df[df['标星']].to_dict(orient='records')
        # 严格按照 UI_CATEGORIES 展示
        for cat in UI_CATEGORIES:
            items = df[df['类型'] == cat].to_dict(orient='records')
            if items:
                cat_data[cat] = items
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, user=session['user'], categories=UI_CATEGORIES)
    except Exception as e:
        return f"系统繁忙，请刷新重试。{str(e)}"

# 确保 add 路由中也使用这个分类列表
@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect(url_for('login'))
    sheet = get_user_sheet(session['user'])
    new_row = [
        request.form.get('name').strip(),
        request.form.get('url').strip(),
        request.form.get('type'), # 来自下拉菜单
        request.form.get('note').strip(),
        "FALSE" 
    ]
    sheet.append_row(new_row)
    return redirect(url_for('index'))

# ... 其他路由 (login, logout, toggle, random) 保持之前的完美版逻辑 ...
