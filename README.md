# 🇩🇪 德语星 (German Favorites / DE favs)

**每一个德语学习者，都是一位摘星人。**
* “德语星”原名“德语资源收藏夹”，英文名保留为 **German Favorites**。在我看来，每一个优秀的学习资源都如同一颗璀璨的星辰。通过“标星”功能，学习者可以在浩瀚的资料烟海中，亲手点亮属于自己的那片星海。
* 这是一款专为德语学习者设计的轻量化 Web 应用，集资源收藏、智能搜索、随机发现于一体，支持多用户独立管理及全设备移动端适配。

🔗 **在线演示**: [https://german-favorites-x247.vercel.app/](https://german-favorites-x247.vercel.app/)  
📱 **安卓支持**: 本仓库提供 **APK 安装包** 下载。

---

## ✨ 核心功能

* **多维资源管理**：支持对德语网站、词典、影音及移动应用进行在线新增、编辑与分类存储。
* **万象星选 (Starred)**：一键收藏高频资源，实现首页置顶显示。
* **流光碎影 (History)**：本地化存储最近 10 条浏览记录，快速回访历史足迹。
* **毫秒级搜索**：支持按名称、备注或分类进行实时联想过滤。
* **随机抽卡 (Surprise)**：🎲 按钮为你从星海中随机挑选学习资源，解决选择困难。
* **安全与隐私**：
    * 账号密码采用 **Werkzeug Hash 加密** 存储。
    * 支持**一键导出 CSV** 备份个人收藏数据。
    * 提供 **7 天免登录** 持久化选项。

## 🛠️ 技术架构

* **后端**: Python / Flask
* **前端**: HTML5 / Tailwind CSS / JavaScript
* **数据库**: Google Sheets API (实现轻量化、零成本云端数据管理)
* **部署**: Vercel

## 🚀 快速开始

### 本地部署
* 1. 安装依赖
```bash
pip install -r requirements.txt
```

* 2. 环境配置
在部署环境（如 Vercel）中设置以下环境变量即可运行：
* `GOOGLE_CREDS_JSON`: Google Cloud 服务账号密钥 JSON 字符串。
* `FLASK_SECRET_KEY`: 用于 Session 加密的私钥。

* 3. 运行应用
```bash
python app.py
```

## 🔐 演示账号

若不想注册，可使用公共账号体验：
* **用户名**: `Public`
* **密码**: `public`

---

**Built with ❤️ by Jincheng Qin**
*如果您有任何建议，欢迎通过应用内的邮件功能进行反馈。*
