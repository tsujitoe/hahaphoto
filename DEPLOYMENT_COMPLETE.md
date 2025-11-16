# 🎉 GCP 部署完成摘要

**部署完成時間**: 2025-11-16 20:20 (UTC+8)  
**狀態**: ✅ 成功

---

## 部署成果

### Cloud Run 服務
- **服務名稱**: `hahaphoto`
- **區域**: `asia-east1` (台灣)
- **服務 URL**: https://hahaphoto-mbuoqxoktq-de.a.run.app
- **修訂版本**: hahaphoto-00002-yut
- **流量分配**: 100% ✅
- **狀態**: 正在運作 ✅

### Cloud SQL 資料庫
- **實例名稱**: `hahaphoto-postgres`
- **資料庫版本**: PostgreSQL 14
- **機器類型**: db-f1-micro (共享核心)
- **區域**: `asia-east1`
- **資料庫**: `photoalbumdb`
- **使用者**: `postgres`
- **狀態**: 就緒 ✅

### Cloud Storage
- **Bucket 名稱**: `hahaphoto-prod-33000-hahaphoto-media`
- **位置**: `asia-east1`
- **用途**: 靜態檔案與上傳媒體
- **狀態**: 就緒 ✅

### Docker 容器
- **映像**: `gcr.io/hahaphoto-prod-33000/hahaphoto`
- **大小**: ~270MB
- **基礎映像**: Python 3.11-slim
- **應用伺服器**: gunicorn (2 workers, port 8080)
- **推送狀態**: 成功 ✅

### 服務帳戶與 IAM
- **服務帳戶**: `hahaphoto-sa@hahaphoto-prod-33000.iam.gserviceaccount.com`
- **配置角色**:
  - ✅ Cloud SQL Client
  - ✅ Storage Object Viewer
  - ✅ Storage Object Creator
  - ✅ Logging Writer

---

## 環境變數配置

部署時已設定的環境變數：
- `DJANGO_DEBUG=0` — 生產模式
- `DJANGO_SECRET_KEY` — 已生成
- `DJANGO_ALLOWED_HOSTS=hahaphoto.run.app` — 允許的主機
- `DATABASE_URL` — Cloud SQL 連線字串（含 Unix socket）
- `GS_BUCKET_NAME` — Cloud Storage bucket
- `GS_PROJECT_ID` — GCP 專案 ID

---

## 後續必要步驟

### 1️⃣ 執行資料庫遷移 ⚠️ **重要**

應用現在已上線，但資料庫表結構尚未建立。需要執行 Django migrations：

**方法 A：使用 Cloud SQL Auth Proxy（推薦本地執行）**

```powershell
# 下載 cloud_sql_proxy
Invoke-WebRequest -Uri "https://dl.google.com/cloudsql/cloud_sql_proxy.exe" -OutFile ".\cloud_sql_proxy.exe"

# 在新 PowerShell 視窗啟動代理
.\cloud_sql_proxy.exe -instances="hahaphoto-prod-33000:asia-east1:hahaphoto-postgres=tcp:5432"

# 在另一個視窗設定環境變數並執行遷移
$env:DATABASE_URL = "postgresql://postgres:YOUR_DB_PASSWORD@127.0.0.1:5432/photoalbumdb"
$env:DJANGO_DEBUG = "0"
$env:DJANGO_SECRET_KEY = "YOUR_SECRET_KEY"

cd "C:\Users\tsujitoe\Programe-tsujitoe\tsujitoe-lab\ai-test"
python manage.py migrate
python manage.py createsuperuser  # 建立 admin 使用者
python manage.py collectstatic    # 收集靜態檔案
```

**方法 B：使用 Cloud Run Job（推薦雲端執行）**

```powershell
# 建立 migration job
$PROJECT_ID = "hahaphoto-prod-33000"
$REGION = "asia-east1"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/hahaphoto"

gcloud run jobs create hahaphoto-migrate \
  --image=$IMAGE_NAME \
  --add-cloudsql-instances="hahaphoto-prod-33000:asia-east1:hahaphoto-postgres" \
  --set-env-vars="DATABASE_URL=...,DJANGO_SECRET_KEY=..." \
  --command="python,manage.py,migrate" \
  --region=$REGION

# 執行 job
gcloud run jobs execute hahaphoto-migrate --region=$REGION
```

### 2️⃣ 測試服務

在瀏覽器開啟：https://hahaphoto-mbuoqxoktq-de.a.run.app

預期會看到：
- Django 應用頁面，或
- 若未執行 migrations：資料庫錯誤（待修正後消失）

### 3️⃣ 檢查日誌（故障排除）

```powershell
# 查看最新日誌
gcloud run services describe hahaphoto --region=asia-east1 --format=json --project=hahaphoto-prod-33000

# 在 Cloud Console 查看詳細日誌
# https://console.cloud.google.com/logs
```

---

## 敏感資訊管理

⚠️ **安全提示**：

以下資訊已保存在本機臨時目錄，應立即妥善處理：
- Django SECRET_KEY：`$env:TEMP\django_secret_key.txt`
- DB Password：`$env:TEMP\db_password.txt`

**建議操作**：
1. 使用 GCP Secret Manager 安全存儲敏感資訊
2. 從臨時目錄刪除這些檔案
3. 本地 `.env` 檔案應添加到 `.gitignore`

```powershell
# 刪除臨時敏感檔案
Remove-Item "$env:TEMP\django_secret_key.txt"
Remove-Item "$env:TEMP\db_password.txt"
Remove-Item "$env:TEMP\db_password.txt"
```

---

## 成本預估（月度）

| 服務 | 預估成本 | 備註 |
|------|--------|------|
| Cloud Run | ¥0-100 | 免費配額 200k requests/月 |
| Cloud SQL db-f1-micro | ¥65-100 | 共享核心，最低層級 |
| Cloud Storage | ¥10-50 | 依存儲與流量 |
| **合計** | **¥75-250** | 初期使用量 |

*實際成本會根據流量、存儲量而定。建議在 GCP Console 設定預算告警。*

---

## 常用命令

```powershell
# 查看服務 URL
$PROJECT_ID = "hahaphoto-prod-33000"
$REGION = "asia-east1"
gcloud run services describe hahaphoto --region=$REGION --format='value(status.url)' --project=$PROJECT_ID

# 檢查 Cloud SQL 狀態
gcloud sql instances describe hahaphoto-postgres --project=$PROJECT_ID

# 查看 Cloud Storage 內容
gsutil ls -r gs://hahaphoto-prod-33000-hahaphoto-media/

# 重新部署（代碼變更後）
gcloud run deploy hahaphoto --image=gcr.io/$PROJECT_ID/hahaphoto --region=$REGION --project=$PROJECT_ID

# 查看環境變數
gcloud run services describe hahaphoto --region=$REGION --format='value(spec.template.spec.containers[0].env)' --project=$PROJECT_ID

# 清理：刪除所有資源（謹慎操作）
gcloud run services delete hahaphoto --region=$REGION --quiet
gcloud sql instances delete hahaphoto-postgres --quiet
gsutil -m rm -r gs://hahaphoto-prod-33000-hahaphoto-media/
```

---

## 部署流程回顧

| 步驟 | 狀態 | 時間 |
|-----|-----|-----|
| 1. GCP 專案建立 | ✅ | ~1 分鐘 |
| 2. 啟用 API | ✅ | ~2 分鐘 |
| 3. Cloud Storage 建立 | ✅ | ~1 分鐘 |
| 4. 服務帳戶設定 | ✅ | ~1 分鐘 |
| 5. Docker build & push | ✅ | ~5 分鐘 |
| 6. Cloud SQL 建立 | ✅ | ~8 分鐘 |
| 7. 資料庫初始化 | ✅ | ~2 分鐘 |
| 8. Cloud Run 部署 | ✅ | ~2 分鐘 |
| **總計** | **✅ 完成** | **~22 分鐘** |

---

## 相關檔案

- `GCP_DEPLOYMENT_GUIDE.md` — 詳細部署指南
- `DEPLOYMENT_PROGRESS.md` — 部署進度記錄
- `deploy_to_cloudrun.ps1` — 自動化部署腳本
- `Dockerfile` — 容器配置
- `entrypoint.sh` — 容器啟動腳本
- `requirements.txt` — Python 依賴（含生產包）
- `photoalbum/settings.py` — Django 配置（支援環境變數）

---

## GitHub 倉庫

所有檔案已上傳到：https://github.com/tsujitoe/hahaphoto

```
主分支：master
提交：
  - Prepare for GCP: add Dockerfile, entrypoint, update requirements and settings
  - Add complete Django project files and .gitignore
  - Add comprehensive GCP deployment guide
  - Add deployment automation script and progress report
```

---

## 故障排除

### Cloud Run 服務無法連接
- 檢查日誌：https://console.cloud.google.com/logs
- 確認 Cloud SQL 實例狀態為 RUNNABLE
- 驗證環境變數中的 DATABASE_URL 格式

### 資料庫遷移失敗
- 檢查 Cloud SQL 連線：使用 cloud_sql_proxy 測試
- 驗證 postgres 使用者密碼
- 確認 Django migrations 檔案存在

### 靜態檔案 404 錯誤
- 執行 `python manage.py collectstatic` 上傳到 GCS
- 確認 GS_BUCKET_NAME 環境變數設定正確
- 檢查 django-storages 配置

---

## 下一步建議

1. ✅ 部署完成 — 服務已上線
2. ⏳ 執行 migrations — 建立資料庫結構
3. 💾 建立 superuser — 存取管理後台
4. 🔒 配置 HTTPS（自動）— Cloud Run 預設啟用
5. 📊 設定監控告警 — 在 GCP Console
6. 🌐 設定自訂域名（可選） — 指向 Cloud Run
7. 🔄 設定 CI/CD（可選） — 自動部署
8. 📈 監控成本 — 設定預算告警

---

**祝部署順利！有任何問題可參考 GCP_DEPLOYMENT_GUIDE.md 或 GCP Console。**
