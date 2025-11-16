# GCP 部署進度報告

**部署時間**: 2025-11-16

## 已完成步驟

### ✅ 步驟 1：GCP 專案建立
- **專案 ID**: `hahaphoto-prod-33000`
- **區域**: `asia-east1`（台灣）
- **計費**: 已啟用

### ✅ 步驟 2：啟用 API
已啟用以下 API：
- Google Cloud APIs
- Cloud Run API
- Cloud Build API
- Cloud SQL Admin API
- Compute Engine API
- Cloud Storage API
- Cloud Resource Manager API
- Identity and Access Management API

### ✅ 步驟 3：建立 Cloud Storage Bucket
- **Bucket 名稱**: `hahaphoto-prod-33000-hahaphoto-media`
- **位置**: `asia-east1`
- **用途**: 存放靜態檔案與媒體上傳

### ✅ 步驟 4：建立服務帳戶與 IAM 權限
- **服務帳戶**: `hahaphoto-sa@hahaphoto-prod-33000.iam.gserviceaccount.com`
- **權限已設定**:
  - Cloud SQL Client（連接資料庫）
  - Storage Object Viewer（讀取靜態檔案）
  - Storage Object Creator（上傳媒體）
  - Logging Writer（寫入日誌）

### ✅ 步驟 5：構建 Docker Image
- **Image 名稱**: `gcr.io/hahaphoto-prod-33000/hahaphoto`
- **大小**: ~270MB
- **狀態**: 已推送到 Google Container Registry (GCR)
- **構建詳情**:
  - 基礎映像: Python 3.11-slim
  - 依賴: gunicorn, Django, psycopg2, django-storages, google-cloud-storage, whitenoise
  - 應用伺服器: gunicorn (2 workers, port 8080)

## 進行中

### ⏳ 步驟 6：建立 Cloud SQL Postgres
- **實例名稱**: `hahaphoto-postgres`
- **資料庫版本**: PostgreSQL 14
- **機器類型**: db-f1-micro (共享核心，最低成本)
- **區域**: `asia-east1`
- **狀態**: 建立中...（預計需要 3-5 分鐘）

正在執行自動化部署腳本 (`deploy_to_cloudrun.ps1`)，它將：
1. 等待 Cloud SQL 完成初始化
2. 設定 postgres 使用者密碼
3. 建立應用資料庫 (`photoalbumdb`)
4. 將應用部署到 Cloud Run
5. 設定環境變數與 Cloud SQL 連線

## 待執行步驟

### 步驟 7：部署到 Cloud Run
部署命令範例（自動執行中）：
```powershell
gcloud run deploy hahaphoto \
  --image=gcr.io/hahaphoto-prod-33000/hahaphoto \
  --platform=managed \
  --region=asia-east1 \
  --allow-unauthenticated \
  --memory=512Mi \
  --add-cloudsql-instances=hahaphoto-prod-33000:asia-east1:hahaphoto-postgres \
  --service-account=hahaphoto-sa@hahaphoto-prod-33000.iam.gserviceaccount.com
```

### 步驟 8：執行資料庫遷移
部署完成後，需要執行以下步驟（見 GCP_DEPLOYMENT_GUIDE.md 第 8 步）：

**方法 A：使用 Cloud SQL Auth Proxy**
```powershell
# 下載 cloud_sql_proxy
Invoke-WebRequest -Uri "https://dl.google.com/cloudsql/cloud_sql_proxy.exe" -OutFile ".\cloud_sql_proxy.exe"

# 在新視窗啟動代理
.\cloud_sql_proxy.exe -instances="hahaphoto-prod-33000:asia-east1:hahaphoto-postgres=tcp:5432"

# 在另一個視窗執行遷移
$env:DATABASE_URL = "postgresql://postgres:YOUR_DB_PASSWORD@127.0.0.1:5432/photoalbumdb"
python manage.py migrate
python manage.py createsuperuser  # 可選，用於管理後台
python manage.py collectstatic    # 收集靜態檔案
```

**方法 B：使用 Cloud Run Job（推薦）**
```powershell
# 執行一次性遷移 job
gcloud run jobs create hahaphoto-migrate \
  --image=gcr.io/hahaphoto-prod-33000/hahaphoto \
  --add-cloudsql-instances=hahaphoto-prod-33000:asia-east1:hahaphoto-postgres \
  --set-env-vars=DATABASE_URL="..." \
  --command=python,manage.py,migrate

# 執行 job
gcloud run jobs execute hahaphoto-migrate --region=asia-east1
```

## 生成的敏感資訊

以下密鑰已生成並保存在本機臨時目錄（部署完成後應移除）：

- **DJANGO_SECRET_KEY**: 已生成（儲存於 `$env:TEMP\django_secret_key.txt`）
- **DB_PASSWORD**: 已生成（儲存於 `$env:TEMP\db_password.txt`）
- **DATABASE_URL**: 格式 `postgresql+psycopg2://postgres:PASSWORD@/photoalbumdb?host=/cloudsql/PROJECT:REGION:INSTANCE`

**安全提示**：
- 這些密鑰不應被提交到 Git
- 應該在 GCP Cloud Run 的 Secret Manager 中安全存儲
- 臨時檔案應在部署完成後手動刪除

## 預期成本

| 項目 | 估計月費用 |
|------|----------|
| Cloud Run (按需付費) | ¥0-50 (免費配額 200k requests/月) |
| Cloud SQL db-f1-micro | ¥65-100 |
| Cloud Storage | ¥10-50 (依存儲與流量) |
| **總計** | **¥75-200** (初期用量) |

## 後續操作清單

- [ ] 等待 `deploy_to_cloudrun.ps1` 腳本完成
- [ ] 取得 Cloud Run 服務 URL
- [ ] 執行資料庫遷移 (migrate)
- [ ] 測試服務可訪問性
- [ ] 建立 Django admin 超級使用者
- [ ] 上傳靜態檔案到 Cloud Storage (或驗證 WhiteNoise)
- [ ] 設定自訂域名（可選）
- [ ] 啟用 HTTPS 與 HTTP2（已自動啟用）
- [ ] 配置 Cloud Logging 與 monitoring
- [ ] 清理臨時密鑰檔案

## 常用命令

```powershell
# 查看部署日誌
gcloud run services logs read hahaphoto --region=asia-east1 --limit=50

# 檢查服務狀態
gcloud run services describe hahaphoto --region=asia-east1

# 取得服務 URL
gcloud run services describe hahaphoto --region=asia-east1 --format='value(status.url)'

# 查看 Cloud SQL 狀態
gcloud sql instances describe hahaphoto-postgres

# 查看 Cloud Storage bucket 內容
gsutil ls -r gs://hahaphoto-prod-33000-hahaphoto-media/

# 刪除部署（若需要清理）
gcloud run services delete hahaphoto --region=asia-east1
gcloud sql instances delete hahaphoto-postgres
gsutil -m rm -r gs://hahaphoto-prod-33000-hahaphoto-media/
```

## 故障排除

### Cloud Run 容器啟動失敗
檢查日誌：
```powershell
gcloud run services logs read hahaphoto --region=asia-east1 --limit=100
```

常見原因：
- DATABASE_URL 格式錯誤
- Cloud SQL 未準備好
- 環境變數未設定

### 無法連接 Cloud SQL
檢查項目：
- Cloud SQL 實例狀態是否為 RUNNABLE
- 服務帳戶是否有 cloudsql.client 角色
- Cloud SQL Auth Proxy 是否正在運行

### 靜態檔案 404
檢查：
- GCS bucket 是否包含 static 檔案
- `DJANGO_ALLOWED_HOSTS` 是否正確
- `GS_BUCKET_NAME` 環境變數是否設定

---

**部署指南**: 詳見 `GCP_DEPLOYMENT_GUIDE.md`

**GitHub 倉庫**: https://github.com/tsujitoe/hahaphoto
