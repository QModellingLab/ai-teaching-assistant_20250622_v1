# gunicorn.conf.py - Gunicorn 配置檔案

import os
import multiprocessing

# 服務器設定
bind = f"0.0.0.0:{os.getenv('PORT', 5000)}"
workers = int(os.getenv('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# 超時設定
timeout = 120
keepalive = 2
graceful_timeout = 30

# 記憶體管理
preload_app = True
max_worker_memory = 200  # MB

# 日誌設定
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 安全設定
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# 進程管理
user = None
group = None
tmp_upload_dir = "/tmp"

# 開發/生產環境區分
if os.getenv('FLASK_ENV') == 'development':
    # 開發環境設定
    reload = True
    workers = 1
    timeout = 0
    loglevel = 'debug'
else:
    # 生產環境設定
    reload = False
    preload_app = True
    
# Heroku/Railway 特殊設定
if os.getenv('DYNO'):  # Heroku
    workers = int(os.getenv('WEB_CONCURRENCY', 2))
    max_requests = 1200
    
if os.getenv('RAILWAY_ENVIRONMENT'):  # Railway
    workers = int(os.getenv('WEB_CONCURRENCY', 2))
    timeout = 60

# 統計和監控
statsd_host = os.getenv('STATSD_HOST')
if statsd_host:
    statsd_prefix = 'ai-teaching-assistant'

# Worker 啟動和關閉事件
def when_ready(server):
    """當服務器啟動完成時執行"""
    server.log.info("🚀 AI Teaching Assistant 服務器已啟動")
    server.log.info(f"📊 Workers: {workers}")
    server.log.info(f"🌐 綁定地址: {bind}")

def worker_int(worker):
    """Worker 收到中斷信號時執行"""
    worker.log.info("👋 Worker 正在優雅地關閉...")

def post_fork(server, worker):
    """Worker 進程分叉後執行"""
    server.log.info(f"🔧 Worker {worker.pid} 已啟動")

def pre_fork(server, worker):
    """Worker 進程分叉前執行"""
    pass

def worker_exit(server, worker):
    """Worker 退出時執行"""
    server.log.info(f"🔻 Worker {worker.pid} 已退出")

# 健康檢查和資源清理
def on_exit(server):
    """服務器退出時執行清理"""
    server.log.info("🧹 執行資源清理...")
    
    # 關閉資料庫連接
    try:
        from models import db
        if not db.is_closed():
            db.close()
            server.log.info("📊 資料庫連接已關閉")
    except Exception as e:
        server.log.error(f"❌ 資料庫關閉錯誤: {e}")
    
    server.log.info("✅ AI Teaching Assistant 服務器已安全關閉")

# 錯誤處理
def worker_abort(worker):
    """Worker 異常終止時執行"""
    worker.log.error(f"💥 Worker {worker.pid} 異常終止")

# 自定義配置驗證
def validate_config():
    """驗證配置參數"""
    errors = []
    
    if workers < 1:
        errors.append("Workers 數量必須大於 0")
    
    if timeout < 10:
        errors.append("Timeout 不應少於 10 秒")
        
    if errors:
        raise ValueError(f"配置錯誤: {', '.join(errors)}")

# 執行配置驗證
validate_config()

# 環境變數日誌
print(f"""
🎓 AI Teaching Assistant - Gunicorn 配置
{'='*50}
📍 綁定地址: {bind}
👥 Worker 數量: {workers}
⏱️  超時時間: {timeout}s
📝 日誌級別: {loglevel}
🔄 預加載應用: {preload_app}
🛠️  環境: {os.getenv('FLASK_ENV', 'production')}
{'='*50}
""")
