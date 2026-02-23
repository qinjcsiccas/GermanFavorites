import os
import json
import random
import time
import re
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import gspread
from google.oauth2.service_account import Credentials
# import pandas as pd
import csv
from io import StringIO
from flask import make_response

# 简单的内存缓存
cache = {}
CACHE_TIMEOUT = 300  # 5分钟缓存

def get_cached(key, timeout=CACHE_TIMEOUT):
    """获取缓存数据"""
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < timeout:
            return data
        else:
            del cache[key]
    return None

def set_cached(key, data):
    """设置缓存数据"""
    cache[key] = (data, time.time())

def clear_cache():
    """清空缓存"""
    cache.clear()

# 错误处理装饰器
def handle_errors(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            flash(f"Google Sheets 服务繁忙，请稍后重试")
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            flash(f"系统开小差了，请稍后再试")
            return redirect(url_for('index'))
    return decorated_function

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "german_study_secure_2026")

def slugify(text):
    if not text: return "item"
    # 增加对 unicode 字符的更广泛兼容
    cleaned = re.sub(r'[^\w\u4e00-\u9fa5]', '', str(text))
    return cleaned.lower() if cleaned else "item"

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
    name = request.form.get('name', '').strip()

    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not is_valid_url(url):
        flash("网址格式有误，请重试 ⚠️")
        return redirect(url_for('index'))
    
    # --- 新增：处理自定义分类 ---
    resource_type = request.form.get('type')
    if resource_type == '__custom__':
        resource_type = request.form.get('custom_type', '').strip() or '其他'
        
    sheet = get_user_sheet(session['user'])
    # 注意：这里存入的分类改成了 resource_type
    sheet.append_row([name, url, resource_type, request.form.get('note').strip(), "FALSE"])
    
    # 清空用户缓存
    cache_key = f"user_data_{session['user']}"
    if cache_key in cache:
        del cache[cache_key]
    
    flash(f"手摘星辰，点亮{name[:4]} ") 
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        un = request.form.get('username', '').strip()
        pw = request.form.get('password', '')
        remember = request.form.get('remember')  # 获取勾选框状态

        try:
            u_sheet = get_user_sheet("Users")
            users = u_sheet.get_all_records()
            for u in users:
                if str(u.get('username', '')).strip() == un:
                    if check_password_hash(str(u.get('password', '')), pw):
                        # 核心逻辑：根据勾选状态决定是否持久化
                        if remember:
                            session.permanent = True  # 启用长效 Session
                            app.permanent_session_lifetime = timedelta(days=7) # 设置为 7 天
                        else:
                            session.permanent = False # 浏览器关闭即失效
                            
                        session['user'] = un
                        return redirect(url_for('index'))
                    else:
                        flash("密码错误，请重试")
                        return redirect(url_for('login'))
            
            flash("用户名不存在")
            return redirect(url_for('login'))
        except Exception as e:
            flash("登录服务繁忙，请稍后再试")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/edit_resource', methods=['POST'])
def edit_resource():
    if 'user' not in session: return redirect(url_for('login'))
    
    # 获取前端传回的原始数据，用于匹配定位
    old_name = request.form.get('old_name')
    old_url = request.form.get('old_url')
    
    # 获取新数据
    name = request.form.get('name', '').strip()
    raw_url = request.form.get('url', '').strip()
    if raw_url and not raw_url.startswith(('http://', 'https://')):
        raw_url = 'https://' + raw_url
    
    # --- 新增：处理自定义分类 ---
    resource_type = request.form.get('type')
    if resource_type == '__custom__':
        resource_type = request.form.get('custom_type', '').strip() or '其他'
    
    updated_row = [
        name,
        raw_url,
        resource_type, # 这里换成了动态的 resource_type
        request.form.get('note')
    ]
    
    try:
        user_ws = get_user_sheet(session['user'])
        records = user_ws.get_all_records()
        
        found = False
        # 遍历所有行，寻找 名称 和 网址 同时匹配的行
        for i, row in enumerate(records):
            if str(row.get('名称')) == old_name and str(row.get('网址')) == old_url:
                # 找到了原始行：i 是索引，+2 是 Sheet 实际行号
                user_ws.update(f'A{i + 2}:D{i + 2}', [updated_row])
                found = True
                break
        
        if found:
            cache_key = f"user_data_{session['user']}"
            if cache_key in cache:
                del cache[cache_key]
            flash("✨ 资源已更新 ✨")
        else:
            flash("未找到原始资源，无法修改 ⚠️")
            
    except Exception as e:
        flash(f"更新失败: {str(e)}")
        
    return redirect(url_for('index'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session: return redirect(url_for('login'))
    
    old_pw = request.form.get('old_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if new_pw != confirm_pw:
        flash("两次输入的新密码不一致 ❌")
        return redirect(url_for('index'))
    
    if len(new_pw) < 6:
        flash("新密码至少需要 6 位 🔒")
        return redirect(url_for('index'))

    try:
        user_sheet = get_user_sheet("Users")
        users = user_sheet.get_all_records()
        for i, row in enumerate(users):
            if str(row.get('username')).strip() == session['user']:
                # 校验旧密码
                if check_password_hash(str(row.get('password')), old_pw):
                    new_hash = generate_password_hash(new_pw)
                    user_sheet.update_cell(i + 2, 2, new_hash)
                    flash("密码修改成功！下次登录生效 ✨")
                    return redirect(url_for('index'))
                else:
                    flash("旧密码输入错误 🛡️")
                    return redirect(url_for('index'))
    except Exception as e:
        flash(f"系统错误: {str(e)}")
    return redirect(url_for('index'))

@app.route('/')
@handle_errors  # 添加错误处理装饰器
def index():
    if 'user' not in session: return redirect(url_for('login'))
    
    starred = []
    cat_data = {}
    q = request.args.get('q', '').strip().lower()
    
    # 1. 尝试从缓存获取数据
    cache_key = f"user_data_{session['user']}"
    cached_data = get_cached(cache_key)
    
    # 2. 如果有缓存且没有搜索关键词，直接使用缓存数据
    if cached_data and not q:
        # 兼容处理：确保从缓存中解包出 dynamic_categories
        if len(cached_data) == 3:
            starred, cat_data, dynamic_categories = cached_data
        else:
            starred, cat_data = cached_data
            dynamic_categories = UI_CATEGORIES.copy()
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, user=session['user'], categories=dynamic_categories)
    
    # 3. 没有缓存或正在搜索，从Google Sheets获取数据
    try:
        sheet = get_user_sheet(session['user'])
        if not sheet:
            return render_template('index.html', starred=[], cat_data={}, q=q, user=session['user'], categories=UI_CATEGORIES)
            
        records = sheet.get_all_records()
        if not records:
            return render_template('index.html', starred=[], cat_data={}, q=q, user=session['user'], categories=UI_CATEGORIES)

        # 4. 数据处理与分类收集
        all_items = []
        all_types = set() # 新增：收集表格中出现的所有分类
        
        for r in records:
            item = {str(k).strip(): (v if v is not None else "") for k, v in r.items()}
            is_star = str(item.get('标星', '')).upper() in ['TRUE', '1', '是', 'YES']
            item['标星'] = is_star
            
            # 记录有效的分类
            cat_val = str(item.get('类型', '')).strip()
            if cat_val: 
                all_types.add(cat_val)
            
            if q:
                if q in str(item.get('名称', '')).lower() or q in str(item.get('备注', '')).lower():
                    all_items.append(item)
            else:
                all_items.append(item)

        # 5. 处理星选资源
        starred = [i for i in all_items if i['标星']]
        starred.sort(key=lambda x: str(x.get('名称', '')).lower())

        # --- 新增：动态生成分类列表，强制把“其他”垫底 ---
        base_cats = ["影音视听", "系统学习", "词典工具", "移动应用"]
        # custom_cats: 从所有类型中剔除基础分类和"其他"，剩下的就是用户自定义的
        custom_cats = sorted(list(all_types - set(base_cats) - {"其他"}))
        # 组装最终呈现的分类顺序
        dynamic_categories = base_cats + custom_cats + ["其他"]

        # 6. 按动态分类整理
        for cat in dynamic_categories:
            cat_list = [i for i in all_items if str(i.get('类型', '')).strip() == cat]
            if cat_list:
                cat_list.sort(key=lambda x: str(x.get('名称', '')).lower())
                cat_data[cat] = cat_list
        
        # 7. 只有在没有搜索关键词时才缓存数据
        if not q:
            set_cached(cache_key, (starred, cat_data, dynamic_categories))
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, user=session['user'], categories=dynamic_categories)
    
    except Exception as e:
        print(f"Server Logic Error: {str(e)}") 
        # 8. 出错时返回空数据
        return render_template('index.html', starred=[], cat_data={}, q=q, user=session['user'], categories=UI_CATEGORIES)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/toggle/<cid>')
@handle_errors
def toggle(cid):
    if 'user' not in session: 
        return redirect(url_for('login'))
    
    # 获取用户工作表
    s = get_user_sheet(session['user'])
    d = s.get_all_records()
    
    # 查找并更新标星状态
    for i, r in enumerate(d):
        if slugify(r.get('名称', '')) == cid:
            curr = str(r.get('标星', '')).upper() in ['TRUE', '1', '是', 'YES']
            # 更新单元格
            s.update_cell(i + 2, 5, "TRUE" if not curr else "FALSE")
            break
    
    # 关键：清空该用户的缓存
    cache_key = f"user_data_{session['user']}"
    if cache_key in cache:
        del cache[cache_key]
        print(f"已清除缓存 for {session['user']}")  # 调试用
    
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

@app.route('/export_csv')
def export_csv():
    if 'user' not in session: return redirect(url_for('login'))
    
    try:
        sheet = get_user_sheet(session['user'])
        data = sheet.get_all_records()
        
        # 创建内存中的 CSV 文件
        si = StringIO()
        cw = csv.DictWriter(si, fieldnames=["名称", "网址", "类型", "备注", "标星"])
        cw.writeheader()
        cw.writerows(data)
        
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename={session['user']}_german_links.csv"
        output.headers["Content-type"] = "text/csv; charset=utf-8-sig" # 确保中文不乱码
        return output
    except Exception as e:
        flash(f"导出失败: {e}")
        return redirect(url_for('index'))

@app.route('/delete_resource', methods=['POST'])
def delete_resource():
    if 'user' not in session: return redirect(url_for('login'))
    
    name_to_delete = request.form.get('name')
    url_to_delete = request.form.get('url')

    try:
        user_ws = get_user_sheet(session['user'])
        records = user_ws.get_all_records()
        
        # 寻找匹配的行（Google Sheets 索引从1开始，且有标题行，故 +2）
        for i, row in enumerate(records):
            if str(row.get('名称')) == name_to_delete and str(row.get('网址')) == url_to_delete:
                user_ws.delete_rows(i + 2)
                flash(f"已删除：{name_to_delete}")
                break
    except Exception as e:
        flash(f"删除失败: {str(e)}")
        
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    flash('系统开小差了，请稍后再试')
    return redirect(url_for('index'))
