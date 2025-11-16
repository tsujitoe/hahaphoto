# GCP 部署指南 - hahaphoto Django 應用

本指南逐步說明如何將 Django hahaphoto 應用部署到 Google Cloud Platform (GCP) 的 Cloud Run。

## 前置條件

1. 安裝 Google Cloud SDK (`gcloud` CLI)
   - 下載：https://cloud.google.com/sdk/docs/install
   - 驗證安裝：`gcloud --version`

2. 安裝 Docker Desktop（或容器引擎）
   - https://www.docker.com/products/docker-desktop

3. 在 GCP 建立一個專案（或使用現有專案）

## 第 1 步：初始化 GCP 環境

### 1.1 登入 GCP 並設定專案

```powershell
# 登入 Google 帳號
gcloud auth login

# 列出所有專案 ID
gcloud projects list

# 設定預設專案（將 YOUR_PROJECT_ID 換成你的專案 ID）
gcloud config set project YOUR_PROJECT_ID

# 驗證專案設定
gcloud config list
```

### 1.2 設定環境變數（供後續步驟使用）

在 PowerShell 中執行（請根據你的需求修改這些值）：

```powershell
# 設定基本變數
$PROJECT_ID = "YOUR_PROJECT_ID"
$REGION = "asia-east1"  # 台灣推薦用 asia-east1；其他選項: us-central1, europe-west1
$APP_NAME = "hahaphoto"
$SERVICE_NAME = "hahaphoto"
$DB_INSTANCE = "hahaphoto-postgres"
$DB_NAME = "photoalbumdb"
$DB_USER = "postgres"
$BUCKET_NAME = "$PROJECT_ID-hahaphoto-media"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$APP_NAME"

# 驗證變數（可選）
Write-Output "PROJECT_ID: $PROJECT_ID"
Write-Output "REGION: $REGION"
Write-Output "IMAGE_NAME: $IMAGE_NAME"
```

### 1.3 啟用必要的 GCP API

```powershell
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  compute.googleapis.com \
  storage-api.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com
```

---

## 第 2 步：建立 Cloud SQL (Postgres) 資料庫

### 2.1 建立 Cloud SQL 實例

```powershell
# 建立 Cloud SQL Postgres 實例
# 注意：db-f1-micro 為最低成本選項；如需更好效能可改用 db-g1-small 或更高
gcloud sql instances create $DB_INSTANCE `
  --database-version=POSTGRES_15 `
  --tier=db-f1-micro `
  --region=$REGION `
  --availability-type=zonal `
  --enable-bin-log=false `
  --backup-start-time=03:00 `
  --retained-backups-count=7 `
  --transaction-log-retention-days=1

# 等待實例建立完成（通常需要 3-5 分鐘）
# 檢查實例狀態
gcloud sql instances describe $DB_INSTANCE --region=$REGION
```

### 2.2 建立資料庫與使用者

```powershell
# 設定 postgres 使用者的密碼
$DB_PASSWORD = Read-Host "請輸入 postgres 密碼 (需要複雜)" -AsSecureString
$DB_PASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($DB_PASSWORD))

# 設定 postgres 密碼
gcloud sql users set-password postgres --instance=$DB_INSTANCE --password=$DB_PASSWORD_PLAIN

# 建立應用用的資料庫
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE

# 驗證資料庫與使用者
gcloud sql databases list --instance=$DB_INSTANCE
gcloud sql users list --instance=$DB_INSTANCE
```

### 2.3 配置 Cloud SQL 連線權限

```powershell
# 允許所有 IP 連接（用於開發；生產應限制 IP）
gcloud sql instances patch $DB_INSTANCE --allowed-networks=0.0.0.0/0

# 取得 Cloud SQL 連線名稱（供後續 Cloud Run 使用）
$SQL_CONNECTION_NAME = (gcloud sql instances describe $DB_INSTANCE --format='value(connectionName)')
Write-Output "SQL Connection Name: $SQL_CONNECTION_NAME"
```

---

## 第 3 步：建立 Google Cloud Storage Bucket（存放靜態與媒體檔案）

### 3.1 建立 bucket

```powershell
# 建立 GCS bucket（若已存在會報錯，可忽略）
gsutil mb -l $REGION gs://$BUCKET_NAME

# 檢查 bucket 是否存在
gsutil ls
```

### 3.2 設定 bucket 權限與 CORS（選用，若需跨域存取）

```powershell
# 建立簡單的 CORS 設定檔
$corsJson = @"
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
"@

# 將 CORS 設定寫入臨時檔案
$corsJson | Out-File -FilePath cors.json -Encoding UTF8

# 套用 CORS 設定到 bucket
gsutil cors set cors.json gs://$BUCKET_NAME

# 清理臨時檔案
Remove-Item cors.json
```

---

## 第 4 步：設定服務帳戶與 IAM 權限

### 4.1 建立服務帳戶

```powershell
$SA_NAME = "hahaphoto-sa"
$SA_EMAIL = "$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# 建立服務帳戶
gcloud iam service-accounts create $SA_NAME `
  --display-name="hahaphoto Cloud Run Service Account"

# 驗證服務帳戶
gcloud iam service-accounts list --filter="email:$SA_EMAIL"
```

### 4.2 授予服務帳戶權限

```powershell
# Cloud SQL Client（允許 Cloud Run 連接 Cloud SQL）
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/cloudsql.client"

# Storage Object Viewer & Creator（允許讀寫 GCS bucket）
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/storage.objectCreator"

# Logs Writer（允許寫入 Cloud Logging）
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/logging.logWriter"
```

---

## 第 5 步：準備與推送 Docker Image

### 5.1 在本地構建 Docker image

```powershell
# 切換到專案目錄
cd "C:\Users\tsujitoe\Programe-tsujitoe\tsujitoe-lab\ai-test"

# 建構 Docker image（標籤為 GCR 格式）
docker build -t $IMAGE_NAME .

# 驗證 image 已建立
docker images | grep hahaphoto
```

### 5.2 將 image 推送到 Google Container Registry (GCR)

```powershell
# 配置 Docker 用來認證 GCR
gcloud auth configure-docker

# 推送 image 到 GCR
docker push $IMAGE_NAME

# 驗證 image 已上傳
gcloud container images list
gcloud container images list-tags $IMAGE_NAME
```

---

## 第 6 步：在本地準備環境變數檔案（用於測試或參考）

建立一份 `.env.production` 檔案（不要 commit 到 Git，僅供參考）：

```
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=hahaphoto.run.app,yourdomain.com
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@/photoalbumdb?host=/cloudsql/YOUR_PROJECT_ID:asia-east1:hahaphoto-postgres
GS_BUCKET_NAME=YOUR_PROJECT_ID-hahaphoto-media
GS_PROJECT_ID=YOUR_PROJECT_ID
```

> **重要**：不要把真實密碼與 secret key 推送到 GitHub！改用 Cloud Run 的 environment variables 或 Secret Manager。

---

## 第 7 步：部署到 Cloud Run

### 7.1 產生強密碼和 Django SECRET_KEY

```powershell
# 產生 Django SECRET_KEY（PowerShell）
$SECRET_KEY = -join ((65..90) + (97..122) | Get-Random -Count 50 | ForEach-Object {[char]$_})
Write-Output "Generated SECRET_KEY: $SECRET_KEY"

# 產生資料庫密碼（若尚未產生）
$NEW_DB_PASSWORD = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 20 | ForEach-Object {[char]$_})
Write-Output "Generated DB Password: $NEW_DB_PASSWORD"
```

### 7.2 部署到 Cloud Run

```powershell
# 部署應用
gcloud run deploy $SERVICE_NAME `
  --image=$IMAGE_NAME `
  --platform=managed `
  --region=$REGION `
  --allow-unauthenticated `
  --memory=512Mi `
  --timeout=3600 `
  --set-env-vars=`
DJANGO_DEBUG=0,`
DJANGO_SECRET_KEY=$SECRET_KEY,`
DJANGO_ALLOWED_HOSTS=hahaphoto.run.app,`
DATABASE_URL="postgresql+psycopg2://postgres:$DB_PASSWORD_PLAIN@/photoalbumdb?host=/cloudsql/$SQL_CONNECTION_NAME",`
GS_BUCKET_NAME=$BUCKET_NAME,`
GS_PROJECT_ID=$PROJECT_ID `
  --add-cloudsql-instances=$SQL_CONNECTION_NAME `
  --service-account=$SA_EMAIL `
  --no-gen2

# 部署完成後，gcloud 會顯示服務 URL
# 例如：https://hahaphoto-xxxxxx.run.app
```

### 7.3 驗證部署

```powershell
# 檢查 Cloud Run 服務狀態
gcloud run services describe $SERVICE_NAME --region=$REGION

# 查看實時日誌
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50

# 取得服務 URL
$SERVICE_URL = (gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')
Write-Output "Service URL: $SERVICE_URL"

# 在瀏覽器開啟（或用 curl 測試）
Start-Process $SERVICE_URL
```

---

## 第 8 步：資料庫初始化與遷移

### 8.1 下載 Cloud SQL Auth Proxy（用於本地連接遠端資料庫）

```powershell
# 下載 cloud_sql_proxy（Windows 版本）
$proxyUrl = "https://dl.google.com/cloudsql/cloud_sql_proxy.exe"
$proxyPath = ".\cloud_sql_proxy.exe"
Invoke-WebRequest -Uri $proxyUrl -OutFile $proxyPath

# 驗證下載成功
if (Test-Path $proxyPath) {
    Write-Output "cloud_sql_proxy downloaded successfully"
} else {
    Write-Output "Failed to download cloud_sql_proxy"
}
```

### 8.2 啟動 Cloud SQL Auth Proxy

在新的 PowerShell 視窗執行：

```powershell
# 啟動代理（連接到遠端 Cloud SQL）
.\cloud_sql_proxy.exe -instances="$SQL_CONNECTION_NAME=tcp:5432"

# 這個視窗會持續運行，顯示連接狀態
# 保持此視窗開啟，並在另一個 PowerShell 視窗執行後續步驟
```

### 8.3 在另一個視窗執行遷移

```powershell
# 切換到專案目錄
cd "C:\Users\tsujitoe\Programe-tsujitoe\tsujitoe-lab\ai-test"

# 設定本地 DATABASE_URL（連接至代理）
$env:DATABASE_URL = "postgresql://postgres:$DB_PASSWORD_PLAIN@127.0.0.1:5432/photoalbumdb"
$env:DJANGO_DEBUG = "0"
$env:DJANGO_SECRET_KEY = $SECRET_KEY

# 執行 migrations
python manage.py migrate

# 建立 superuser（可選，用於管理後台）
python manage.py createsuperuser

# 收集靜態檔案到 GCS bucket（若配置 django-storages）
# （此步驟在 entrypoint.sh 中會自動執行，但可在本地先測試）
# python manage.py collectstatic --noinput
```

### 8.4 驗證資料庫連接

```powershell
# 從本地連接遠端資料庫檢查（可選）
# 需要安裝 psql（PostgreSQL client）或用 Python
python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('Database OK')"
```

---

## 第 9 步：設定自訂域名（可選）

若要使用自訂域名（如 hahaphoto.yourdomain.com）：

### 9.1 在 GCP 中設定對應

```powershell
# 添加域名對應（需在 Cloud Run 服務中設定）
gcloud run services update-traffic $SERVICE_NAME `
  --to-revisions LATEST=100 `
  --region=$REGION

# 在 Cloud Console 中，進入 Cloud Run > hahaphoto > Manage Custom Domains
# 按照步驟驗證域名並添加
```

### 9.2 更新 ALLOWED_HOSTS

更新環境變數中的 `DJANGO_ALLOWED_HOSTS`：

```powershell
gcloud run services update $SERVICE_NAME `
  --region=$REGION `
  --update-env-vars=DJANGO_ALLOWED_HOSTS="hahaphoto.run.app,yourdomain.com,www.yourdomain.com"
```

---

## 第 10 步：監控與日誌

### 10.1 實時日誌查看

```powershell
# 查看最後 50 行日誌
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50

# 實時監控日誌（使用 Cloud Logging）
# https://console.cloud.google.com/logs

# 或用 gcloud 持續觀看
gcloud run services logs read $SERVICE_NAME --region=$REGION --follow
```

### 10.2 設定告警（可選）

建議在 Cloud Console 設定以下告警：
- Error rate（錯誤率）
- Request latency（請求延遲）
- Memory usage（記憶體使用率）

---

## 故障排除

### 問題 1：部署失敗 - "Image not found"
**解決**：確認 Docker image 已推送到 GCR。執行 `gcloud container images list-tags $IMAGE_NAME`

### 問題 2：資料庫連接失敗
**解決**：
- 檢查 `DATABASE_URL` 格式是否正確
- 確認 Cloud SQL 實例狀態：`gcloud sql instances describe $DB_INSTANCE`
- 確認服務帳戶有 `cloudsql.client` 角色

### 問題 3：靜態檔案未加載（404 錯誤）
**解決**：
- 確認 `GS_BUCKET_NAME` 已設定
- 確認 django-storages 已安裝（在 requirements.txt）
- 在本地執行 `python manage.py collectstatic` 測試
- 檢查 bucket 中是否存在 static 檔案：`gsutil ls gs://$BUCKET_NAME/static/`

### 問題 4：ALLOWED_HOSTS 錯誤
**解決**：更新環境變數 `DJANGO_ALLOWED_HOSTS` 包含正確的域名

### 問題 5：容器啟動超時
**解決**：
- 檢查 entrypoint.sh 的 migrate 步驟（可在 Cloud SQL 代理未就緒時失敗）
- 增加 Cloud Run timeout（默認 5 分鐘，可改為 60 秒以上）
- 檢查日誌找出具體原因：`gcloud run services logs read $SERVICE_NAME`

---

## 清理資源（若要停止服務）

```powershell
# 刪除 Cloud Run 服務
gcloud run services delete $SERVICE_NAME --region=$REGION --quiet

# 刪除 Cloud SQL 實例
gcloud sql instances delete $DB_INSTANCE --quiet

# 刪除 GCS bucket（會刪除所有檔案）
gsutil -m rm -r gs://$BUCKET_NAME

# 刪除服務帳戶
gcloud iam service-accounts delete $SA_EMAIL --quiet

# 刪除 Container Registry 中的 image
gcloud container images delete $IMAGE_NAME --quiet
```

---

## 成本預估（大致）

（以 asia-east1 為例）
- Cloud Run：¥0.0000025 per request + ¥0.00001667 per GB-second（免費配額：200k requests/月）
- Cloud SQL db-f1-micro：約 ¥65/月
- Cloud Storage：¥0.0176/GB/月（存儲）+ ¥0.123/GB（上傳流量）
- 預估最低成本：¥100-150/月（初期用量少）

---

## 參考連結

- [GCP Cloud Run 文件](https://cloud.google.com/run/docs)
- [Cloud SQL Postgres 指南](https://cloud.google.com/sql/docs/postgres)
- [Django Storages 文件](https://django-storages.readthedocs.io/)
- [gcloud CLI 參考](https://cloud.google.com/cli/gcloud-cli)

---

**祝部署順利！有任何問題可參考上述故障排除部分或查看官方文件。**
