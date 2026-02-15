from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = Flask(__name__)

# 配置 Google Sheets 连接
def get_worksheet():
    # 填入你提供的 Service Account 信息
    creds_dict = {
        "type": "service_account",
        "project_id": "german-favorites",
        "private_key_id": "3b9117b68783d43ccc41650a1d70ccc47daf7453",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCwLirSYsyFIWLs\nl2kYaWPcEHQj4RJ4EoJhjUyOEofescs208NKScLlSdToDd8M+ns/mVaejculYIjW\neXNfNKt/9IpKqgguZox7ESV2OPz2Tm8+Iv2gXsl+GRbVVwfumswirmyT00xFLn6P\nOjkWUk7l3VkDTUjwTs/L+qMYXAjzaDzHnfWSUFquIYEqSkZj5QK03wdzgvKyVPeN\nFHn42tCOX0GQj1F1gVzIFfUSynW7HMxarVwTxTEwun79w/JJH9V0LOmqB2dgb3Lv\n3wVA2+HgXc6dnetgvFA1EpP6yDFEuzgetnadE1/WLdJ2gbP5ZMiDqa08KMZk7cVo\nOwyc/i+7AgMBAAECggEATR6QaRKNYxNHubfXbbOoXiqnpBMAIiY8A1a2NZR//CfI\nhAHzQOAD25lThJaZ1hUJAUBuba40//m/PF7idUDZd4PES0Wdmi4SfUZ2pwbwGCMi\nR8lKSzpiqftyhsV3d+czx1Shu52pC7l79dcvKQmzdqRLNApPDL368NeQL/gNhPoY\nf4nR9BU81w6zkS84j2Qu8CKAs4I1/QlNBBtUl/Vx26QozbtH01zcRASacg9LmdiY\n/CMcipHI0WKQCCY/BntH6KZF4lIECqZX1Yt20OqAS/8HhRo/TWEdDpCHw3gILRQP\nVi5TecaBqhWGQ/9ri9MFSC9FKrAtHalo6u1bEBfqpQKBgQDU8u12H0sIv5RdhBft\nBxQJdzCj8cwyZZETf/TAtFBVJQlPcRHMYjE1RHAm8zEwyIqzW3sV2/6eUy5opROi\nAu8xt5uLXc4u86os2o9g3xjlcpSh51NMHDsDBmoNtyCRlWTsDWfz1UKFhGNCxiEr\nst77ArmuCCau1iiHz5H6v3koZQKBgQDTzExcLvre+3/S6+pT6eKbwwij9ntdGMlH\nwdJ+7RjIIxeglnO4liR6+qkQCqzB4hmjMmQcoIvmq9jz5h0/p/gfPMc1oH7t80U1\njrYozEgXPF4gD72h2rb95cuNPPoogLjHxn409uyo5P7mgOIb9PRd9Z6WPOpcbsB4\nXFQ5DxGlnwKBgGfO9Mt8fcuJ+P2Ng0xdAvuKSv/gw7ZdpNdorRuzyuV25I8Bg7eq\ntmpNLo8ORpCNcm/0zI/fasQrsJf6wRNdctU9uGm8FOL2jaLH+NU0bKKNtL8oUYbs\nzCexXMnK1+mgdk5MSrym3YLRAsJua4Ut8V1T+shH2POqGp/6JCOka5+xAoGBAIWy\nXzmJxn9fz0678Y3LBGtC8H9gJnucG+MaLOBGlvAvhsiucJpC3QBsnrArrOYu7fQg\n6SVRCz8vl6JOzoPSakR9v1rQ148pk7S9Q6v5WECisOAYT6KOSBl6J8YeieNrbjld\nyWlxve7Xrziefx0awe9WDyfTiDWVDBZuYhQquP8NAoGBAL7PEoJqCSS6dirc4kk9\n2viWGwcpsHl3+34jdWfYca7Bmo18/29b8iNIrumvj6xKMBGndQOkGsfoT/WDt4oI\nfNJLGyINK8M4wsQ8u3l022zvGUouVvTc7Na+Re4+I/N8Ol63eA5IuNoBBgXlrM9y\nw8cw0lroZyF39eVtKWUI00jZ\n-----END PRIVATE KEY-----\n",
        "client_email": "german-favorites@german-favorites.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    # 通过你提供的 URL 直接打开
    sh = client.open_by_url("https://docs.google.com/spreadsheets/d/1jsbu9uX51m02v_H1xNuTF3bukOZg-4phJecreh3dECs/edit")
    return sh.get_worksheet(0)

@app.route('/')
def index():
    sheet = get_worksheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # 清洗标星逻辑：强制转换为布尔值
    df['标星'] = df['标星'].apply(lambda x: str(x).upper() in ['TRUE', '1', '是', 'YES'])
    
    # 资源分组：置顶与其他
    starred = df[df['标星'] == True].to_dict(orient='records')
    others = df[df['标星'] == False].to_dict(orient='records')
    
    return render_template('index.html', starred=starred, others=others)

@app.route('/toggle/<name>')
def toggle(name):
    sheet = get_worksheet()
    data = sheet.get_all_records()
    # 查找对应行并取反
    for i, row in enumerate(data):
        if row['名称'] == name:
            new_val = not (str(row['标星']).upper() in ['TRUE', '1', '是', 'YES'])
            sheet.update_cell(i + 2, 5, "TRUE" if new_val else "FALSE") # 假设第5列是“标星”
            break
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run()
