@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # 提前初始化变量，防止渲染时找不到定义
    starred = []
    cat_data = {}
    q = request.args.get('q', '').strip()
    
    try:
        sheet = get_user_sheet(session['user'])
        if not sheet:
            return "用户数据表丢失，请联系管理员。"
            
        data = sheet.get_all_records()
        if not data:
            # 如果是新用户，数据为空，直接返回空页面
            return render_template('index.html', starred=[], cat_data={}, q=q, user=session['user'])
            
        df = pd.DataFrame(data)
        df.columns = [c.strip() for c in df.columns]
        df['备注'] = df['备注'].fillna('')
        df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
        
        if q:
            df = df[df['名称'].str.contains(q, case=False)]

        # 核心逻辑
        starred = df[df['标星']].to_dict(orient='records')
        categories = ["影音视听", "系统学习", "词典工具", "移动应用", "其他"]
        for cat in categories:
            items = df[df['类型'] == cat].to_dict(orient='records')
            if items:
                cat_data[cat] = items
        
        return render_template('index.html', starred=starred, cat_data=cat_data, q=q, user=session['user'])
    except Exception as e:
        # 打印具体错误到日志，方便调试
        print(f"Error details: {e}")
        return f"数据读取失败: {str(e)}"
