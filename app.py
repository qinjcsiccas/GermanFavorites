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
# 建议在 Vercel 环境变量中设置 FLASK_SECRET_KEY
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "german_study_secret_2026")

def slugify(text):
    if not text: return ""
    return re.sub(r'\W+', '', str(text)).lower()

app.jinja_env.filters['slugify'] = slugify

def get_gc():
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("环境变量 GOOGLE_CREDS_JSON 缺失")
    info = json.loads(creds_json)
    info['private_key'] = info['private_key'].replace('\\n', '\n')
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

def get_user_sheet(username=None):
    gc = get_gc()
    # 你的 Spreadsheet ID
    sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
    target = username if username else "Users"
    try:
        return sh.worksheet(target)
    except gspread.exceptions.WorksheetNotFound:
        return None

# --- 路由逻辑 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user_sheet = get_user_sheet("Users")
        if not user_sheet:
            return "系统错误：未找到 Users 认证表，请检查 Google Sheets。"
            
        users = user_sheet.get_all_records()
        for u in users:
            # 确保列名一致
            if str(u.get('username')).strip() == username and check_password_hash(u.get('password'), password):
                session['user'] = username
                return redirect(url_for('index'))
        return "用户名或密码错误"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password_raw = request.form.get('password')
        
        if not username or not password_raw:
            return "请完整填写用户名和密码"

        gc = get_gc()
        sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
        user_sheet = sh.worksheet("Users")
        
        # 检查重复
        if any(str(u.get('username')).strip() == username for u in user_sheet.get_all_records()):
            return "用户名已存在"
            
        # 写入新用户
        password_hash = generate_password_hash(password_raw)
        user_sheet.append_row([username, password_hash])
        
        # 创建专属子表并初始化
        try:
            new_ws = sh.add_worksheet(title=username, rows="100", cols="10")
            new_ws.append_row(["名称", "网址", "类型", "备注", "标星"])
        except Exception as e:
            return f"账号创建成功，但初始化个人表失败（可能是权限问题）: {e}"
            
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
        if not sheet:
            return f"未找到用户 {session['user']} 的资源表。"
            
        data = sheet.get_all_records()
        if not data:
            return render_template('index.html', starred=[], cat_data={}, q=q, user=session['user'])
            
        df = pd.DataFrame(data)
        df.columns = [c.strip() for c in df.columns]
        df['备注'] = df['备注'].fillna('')
        # 修正标星逻辑兼容性
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        starred = df[df['标星']].to_dict(orient='records')
        categories = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]
        for cat in categories:
            items = df[df['类型'] == cat].to_dict(orient='records')
            if items:
                cat_data[cat] = items
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, user=session['user'])
    except Exception as e:
        return f"系统繁忙，请刷新重试。错误: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 其余 toggle, add, random 路由中一律使用 get_user_sheet(session['user'])
