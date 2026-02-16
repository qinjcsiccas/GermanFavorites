# 🇩🇪 GermanFavorites | 德语资源库

一个专为德语学习者设计的轻量级、响应式资源管理系统。通过 Flask 驱动，并利用 Google Sheets 实现数据的实时云同步。

---

## ✨ 核心功能

* **智能联想搜索**：前端实时过滤，自动匹配资源名称、备注及分类，并智能展开相关文件夹。
* **动态资源管理**：支持在线新增、编辑、删除及星标置顶，数据直接持久化至 Google Sheets。
* **抽奖式随机跳转**：通过“手气不错”功能，配合震动与旋转动画，仪式感满满地随机抽取学习内容。
* **多端自适应 UI**：采用 Tailwind CSS 打造的德式美学界面，完美适配手机浏览器。
* **安全与持久化**：
    * 基于 `werkzeug` 的哈希密码加密，保护账户安全。
    * 支持“记住我”功能，利用持久化 Session 实现 7 天免登录。
* **数据导出**：支持一键将个人收藏导出为 UTF-8 编码的 CSV 备份文件。

---

## 🛠️ 技术栈

* **Backend**: Python / Flask
* **Database**: Google Sheets API (via gspread & oauth2)
* **Frontend**: HTML5 / Tailwind CSS / JavaScript (ES6)
* **Deployment**: Vercel

---

## 🚀 快速开始 (本地开发)

1.  **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```
2.  **配置环境变量**：
    * `GOOGLE_CREDS_JSON`: Google 服务账号的 JSON 凭据字符串。
    * `FLASK_SECRET_KEY`: 用于 Session 加密的自定义密钥。
3.  **启动应用**：
    * 运行 `python app.py` 或直接双击 `run_local.bat`。

---

## 🛡️ 管理员工具

* 访问 `/admin/reset` 路由可以为特定用户手动重置密码。
* 仅限管理员账号拥有访问权限。

---

## 👤 作者

**Jincheng Qin** | Materials Science & AI  
Email: 1419629781@qq.com | qinjccas@gmail.com
