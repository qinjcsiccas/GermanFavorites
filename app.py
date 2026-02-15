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
# 密钥建议从环境变量获取
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "german_study_2026_super_secret")

def slugify(text):
    if not text: return ""
    return re.sub(r'\W+', '', str(text)).lower()

app.jinja_env.filters['slugify'] = slugify

# 全局五大类
UI_CATEGORIES = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]

# 预设初始数据
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

# --- 新增功能：网址格式检测函数 ---
def is_valid_url(url):
    regex = re.compile(
        r'^https?://'  # http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' # domain...
        r'localhost|' # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password_raw = request.form.get('password')
        
        if not username or not password_raw:
            return "用户名和密码不能为空"

        try:
            gc = get_gc()
            sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
            user_sheet = sh.worksheet("Users")
            
            if any(str(u.get('username')).strip() == username for u in user_sheet.get_all_records()):
                return "用户名已存在"
                
            # 1. 记录账号
            password_hash = generate_password_hash(password_raw)
            user_sheet.append_row([username, password_hash])
            
            # 2. 创建子表并初始化数据 (改用更兼容的逻辑)
            new_ws = sh.add_worksheet(title=username, rows="100", cols="10")
            # 写入表头和预设内容
            combined_data = [["名称", "网址", "类型", "备注", "标星"]] + INITIAL_RESOURCES
            # 使用 update 来一次性写入，比多次 append 更快更稳
            new_ws.update('A1', combined_data)
            
            return redirect(url_for('login'))
        except Exception as e:
            return f"注册失败（可能是API限流或权限问题）: {str(e)}"
    return render_template('register.html')

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect(url_for('login'))
    
    url = request.form.get('url', '').strip()
    # 网址校验逻辑
    if not is_valid_url(url):
        return "⚠️ 网址格式不正确，必须以 http:// 或 https:// 开头！"

    sheet = get_user_sheet(session['user'])
    new_row = [
        request.form.get('name', '').strip(),
        url,
        request.form.get('type'),
        request.form.get('note', '').strip(),
        "FALSE" 
    ]
    sheet.append_row(new_row)
    return redirect(url_for('index'))

# index, login, logout, toggle, random 路由保持上一版完美逻辑即可
# 记得在 index 路由中传入 categories=UI_CATEGORIES
