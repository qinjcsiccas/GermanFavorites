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
app.secret_key = "your_very_secret_key_here" # 必须设置，用于加密 Session

# 影子索引函数
def slugify(text):
    if not text: return ""
    return re.sub(r'\W+', '', str(text)).lower()

app.jinja_env.filters['slugify'] = slugify

def get_gc():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    info = json.loads(creds_json)
    info['private_key'] = info['private_key'].replace('\\n', '\n')
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

def get_user_sheet(username=None):
    gc = get_gc()
    sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
    
    # 如果未指定用户，则默认读取名为 "Users" 的主表进行登录校验
    target = username if username else "Users"
    try:
        return sh.worksheet(target)
    except gspread.exceptions.WorksheetNotFound:
        return None

# --- 路由：登录与注册 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user_sheet = get_user_sheet("Users") # 存储用户凭证的表
        users = user_sheet.get_all_records()
        
        for u in users:
            if u['username'] == username and check_password_hash(u['password'], password):
                session['user'] = username
                return redirect(url_for('index'))
        return "用户名或密码错误"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = generate_password_hash(request.form.get('password'))
        
        gc = get_gc()
        sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
        
        # 1. 在 Users 表记录账号
        user_sheet = sh.worksheet("Users")
        if any(u['username'] == username for u in user_sheet.get_all_records()):
            return "用户名已存在"
        user_sheet.append_row([username, password])
        
        # 2. 创建用户专属数据表并初始化表头
        new_ws = sh.add_worksheet(title=username, rows="100", cols="20")
        new_ws.append_row(["名称", "网址", "类型", "备注", "标星"])
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- 修改后的主逻辑 ---

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        sheet = get_user_sheet(session['user']) # 只读当前用户的子表
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        # ... (后续逻辑与你之前的完美版一致)
        return render_template('index.html', starred=starred, cat_data=cat_data, user=session['user'])
    except Exception as e:
        return f"数据初始化中，请稍后刷新。{str(e)}"

# toggle, add, random 路由中，全部将 get_worksheet() 替换为 get_user_sheet(session['user'])
