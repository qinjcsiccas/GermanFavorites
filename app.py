import os
import json
import random
import time
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "german_study_secure_2026")

def slugify(text):
    if not text: return ""
    return re.sub(r'\W+', '', str(text)).lower()

app.jinja_env.filters['slugify'] = slugify

UI_CATEGORIES = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]

# 初始数据内容
INITIAL_RESOURCES = [
    ["DW Learn German", "https://learngerman.dw.com/", "系统学习", "官方分级课程 (A1-C1)", "FALSE"],
    ["Dict.cc", "https://www.dict.cc/", "词典工具", "经典德英词典", "FALSE"],
    ["Duolingo", "https://www.duolingo.com/", "移动应用", "多邻国趣味打卡", "FALSE"],
    ["YourGermanTeacher", "https://www.youtube.com/@YourGermanTeacher", "影音视听", "详尽语法讲解", "FALSE"]
]

# 网址格式检测
def is_valid_url(url):
    regex = re.compile(r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', re.IGNORECASE)
    return re.match(regex, url) is not None

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
    except:
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password_raw = request.form.get('password')
        if not username or not password_raw:
            flash("请完整填写用户名和密码")
            return redirect(url_for('register'))

        try:
            gc = get_gc()
            sh = gc.open_by_key("1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs")
            user_sheet = sh.worksheet("Users")
            
            # 1. 检查 Users 账号表是否存在同名
            if any(str(u.get('username')).strip() == username for u in user_sheet.get_all_records()):
                flash("注册失败：用户名已存在")
                return redirect(url_for('register'))
            
            # 2. 检查 Google Sheets 是否已存在同名标签页（防止 400 错误）
            existing_sheets = [s.title for s in sh.worksheets()]
            if username in existing_sheets:
                flash("注册失败：系统资源冲突，请尝试其他用户名")
                return redirect(url_for('register'))
            
            # 记录账号并初始化子表
            user_sheet.append_row([username, generate_password_hash(password_raw)])
            new_ws = sh.add_worksheet(title=username, rows="100", cols="10")
            header_and_data = [["名称", "网址", "类型", "备注", "标星"]] + INITIAL_RESOURCES
            new_ws.update('A1', header_and_data)
            
            flash("注册成功！请登录")
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f"系统繁忙: {str(e)}")
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect(url_for('login'))
    url = request.form.get('url', '').strip()
    if not is_valid_url(url):
        return "⚠️ 网址格式错误！必须以 http:// 或 https:// 开头"
    
    sheet = get_user_sheet(session['user'])
    sheet.append_row([request.form.get('name').strip(), url, request.form.get('type'), request.form.get('note').strip(), "FALSE"])
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        un = request.form.get('username', '').strip()
        pw = request.form.get('password', '')
        
        try:
            u_sheet = get_user_sheet("Users")
            if not u_sheet:
                flash("系统错误：找不到用户表")
                return redirect(url_for('login'))
                
            users = u_sheet.get_all_records()
            for u in users:
                # 统一转字符串对比，防止 Excel 格式干扰
                if str(u.get('username', '')).strip() == un:
                    if check_password_hash(str(u.get('password', '')), pw):
                        session['user'] = un
                        return redirect(url_for('index'))
                    else:
                        flash("密码错误，请重试")
                        return redirect(url_for('login'))
            
            flash("用户名不存在")
            return redirect(url_for('login'))
            
        except Exception as e:
            # 如果是 API 超时或权限问题，捕获它而不是直接报 500
            print(f"Login Error: {e}")
            flash("登录服务暂时不可用，请稍后再试")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    new_pw = request.form.get('new_password')
    # 简单的安全性长度检查
    if not new_pw or len(new_pw) < 6:
        flash("密码太短啦，至少需要6位哦")
        return redirect(url_for('index'))

    try:
        user_sheet = get_user_sheet("Users")
        data = user_sheet.get_all_records()
        for i, row in enumerate(data):
            # 精确匹配当前用户名
            if str(row.get('username')).strip() == session['user']:
                new_hash = generate_password_hash(new_pw)
                # 更新 Users 表的第二列 (B列)
                user_sheet.update_cell(i + 2, 2, new_hash) 
                flash("密码修改成功！下次请用新密码登录")
                break
    except Exception as e:
        flash(f"修改失败: {str(e)}")
        
    return redirect(url_for('index'))

@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    starred, cat_data, q = [], {}, request.args.get('q', '').strip()
    try:
        sheet = get_user_sheet(session['user'])
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = [c.strip() for c in df.columns]
        df['备注'] = df['备注'].fillna('')
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        if q: df = df[df['名称'].str.contains(q, case=False)]
        starred = df[df['标星']].to_dict(orient='records')
        for cat in UI_CATEGORIES:
            items = df[df['类型'] == cat].to_dict(orient='records')
            if items: cat_data[cat] = items
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, user=session['user'], categories=UI_CATEGORIES)
    except:
        return render_template('index.html', starred=[], cat_data={}, q=q, user=session['user'], categories=UI_CATEGORIES)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/toggle/<cid>')
def toggle(cid):
    s = get_user_sheet(session['user'])
    d = s.get_all_records()
    for i, r in enumerate(d):
        if slugify(r.get('名称', '')) == cid:
            curr = str(r.get('标星', '')).upper() in ['TRUE', '1', '是', 'YES']
            s.update_cell(i + 2, 5, "TRUE" if not curr else "FALSE")
            break
    return redirect(url_for('index', q=request.args.get('q', '')))

@app.route('/random')
def random_res():
    d = get_user_sheet(session['user']).get_all_records()
    return redirect(random.choice(d)['网址']) if d else redirect(url_for('index'))

@app.route('/admin/reset', methods=['GET', 'POST'])
def admin_reset():
    # 简单安全校验：只有你自己的账号名（假设是 Jincheng）能进
    if session.get('user') != 'Jincheng': 
        return "权限不足", 403

    if request.method == 'POST':
        target_user = request.form.get('target_username').strip()
        new_pw_raw = request.form.get('new_password')
        
        user_sheet = get_user_sheet("Users")
        data = user_sheet.get_all_records()
        
        found = False
        for i, row in enumerate(data):
            if str(row.get('username')).strip() == target_user:
                # 生成新哈希并直接覆盖 Google Sheet 对应行的密码列（B列）
                new_hash = generate_password_hash(new_pw_raw)
                user_sheet.update_cell(i + 2, 2, new_hash) 
                found = True
                break
        
        if found:
            flash(f"用户 {target_user} 的密码已重置为 {new_pw_raw}")
        else:
            flash("未找到该用户")
        return redirect(url_for('admin_reset'))

    return render_template('admin_reset.html')
