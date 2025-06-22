# app.py - 修復版本
import os
import json
import datetime
import logging
from flask import Flask, request, abort, render_template_string, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 導入自定義模組
from models import db, Student, Message, Analysis, AIResponse, initialize_db
from utils import (
    get_ai_response, 
    analyze_student_patterns, 
    update_student_stats,
    create_sample_data
)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 應用初始化
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# 環境變數設定
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN') or os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET') or os.getenv('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 詳細的環境變數檢查
logger.info("=== 環境變數檢查 ===")
logger.info(f"CHANNEL_ACCESS_TOKEN: {'已設定' if CHANNEL_ACCESS_TOKEN else '❌ 未設定'}")
logger.info(f"CHANNEL_SECRET: {'已設定' if CHANNEL_SECRET else '❌ 未設定'}")
logger.info(f"GEMINI_API_KEY: {'已設定' if GEMINI_API_KEY else '❌ 未設定'}")

# LINE Bot API 初始化
line_bot_api = None
handler = None

if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(CHANNEL_SECRET)
        logger.info("✅ LINE Bot API 初始化成功")
    except Exception as e:
        logger.error(f"❌ LINE Bot API 初始化失敗: {e}")
        line_bot_api = None
        handler = None
else:
    logger.error("❌ LINE Bot 環境變數缺失")

# =================== LINE Bot 功能 ===================

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook 處理 - 修復版本"""
    logger.info("收到 LINE Webhook 請求")
    
    # 檢查 LINE Bot 是否初始化
    if not handler or not line_bot_api:
        logger.error("LINE Bot 未正確初始化")
        return "LINE Bot not configured", 500
    
    # 取得請求內容
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    logger.info(f"Signature: {signature[:20]}...")
    logger.info(f"Body length: {len(body)}")
    
    # 驗證簽名
    try:
        handler.handle(body, signature)
        logger.info("✅ Webhook 處理成功")
        return 'OK'
    except InvalidSignatureError:
        logger.error("❌ 無效的簽名")
        abort(400)
    except Exception as e:
        logger.error(f"❌ Webhook 處理錯誤: {e}")
        return str(e), 500

# 測試用的 GET 端點
@app.route("/callback", methods=['GET'])
def callback_test():
    """測試 Callback 端點是否運作"""
    return {
        'status': 'Callback endpoint is working',
        'line_bot_configured': line_bot_api is not None,
        'handler_configured': handler is not None,
        'webhook_url': 'https://web-production-c8b8.up.railway.app/callback'
    }

# 註冊訊息處理器
if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """處理 LINE 訊息事件 - 增強版本"""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            
            logger.info(f"📨 收到訊息: {user_id[:8]}... - {message_text[:50]}...")
            
            # 取得或建立學生記錄
            student = get_or_create_student(user_id, event)
            logger.info(f"👤 學生: {student.name}")
            
            # 記錄訊息
            save_message(student, message_text, event)
            
            # 更新學生統計
            update_student_stats(student.id)
            
            # 處理回應
            if message_text.strip():
                # 取得 AI 回應
                ai_response = get_ai_response(message_text, student.id)
                
                if ai_response and line_bot_api:
                    # 回傳給用戶
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=ai_response)
                    )
                    logger.info(f"✅ AI 回應已發送")
                else:
                    # 備用回應
                    if line_bot_api:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Hello! I'm your EMI teaching assistant. How can I help you today?")
                        )
                        logger.info("✅ 備用回應已發送")
            
        except Exception as e:
            logger.error(f"❌ 處理訊息錯誤: {e}")
            # 發送錯誤回應
            try:
                if line_bot_api:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="Sorry, I'm having some technical difficulties. Please try again later.")
                    )
            except Exception as reply_error:
                logger.error(f"❌ 發送錯誤回應失敗: {reply_error}")

def get_or_create_student(user_id, event):
    """取得或建立學生記錄"""
    try:
        student = Student.get(Student.line_user_id == user_id)
        # 更新最後活動時間
        student.last_active = datetime.datetime.now()
        student.save()
        return student
    except Student.DoesNotExist:
        # 嘗試取得用戶資料
        try:
            if line_bot_api:
                profile = line_bot_api.get_profile(user_id)
                display_name = profile.display_name
            else:
                display_name = f"User_{user_id[:8]}"
        except Exception as e:
            logger.warning(f"無法取得用戶資料: {e}")
            display_name = f"User_{user_id[:8]}"
        
        # 建立新學生記錄
        student = Student.create(
            name=display_name,
            line_user_id=user_id,
            created_at=datetime.datetime.now(),
            last_active=datetime.datetime.now(),
            message_count=0,
            question_count=0,
            participation_rate=0.0,
            question_rate=0.0
        )
        
        logger.info(f"✅ 建立新學生記錄: {display_name}")
        return student

def save_message(student, message_text, event):
    """儲存訊息記錄"""
    # 判斷訊息類型
    is_question = is_question_message(message_text)
    
    # 儲存訊息
    message = Message.create(
        student=student,
        content=message_text,
        message_type='question' if is_question else 'statement',
        timestamp=datetime.datetime.now(),
        source_type=getattr(event.source, 'type', 'unknown'),
        group_id=getattr(event.source, 'group_id', None),
        room_id=getattr(event.source, 'room_id', None)
    )
    
    logger.info(f"✅ 訊息已儲存: {message_text[:30]}...")
    return message

def is_question_message(text):
    """判斷是否為問題"""
    question_indicators = [
        '?', '？', '嗎', '呢', '如何', '怎麼', '為什麼', '什麼是',
        'how', 'what', 'why', 'when', 'where', 'which', 'who',
        'can you', 'could you', 'would you', 'is it', 'are you',
        'do you', 'does', 'did', 'will', 'shall'
    ]
    
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in question_indicators)

# =================== 健康檢查 ===================

@app.route('/health')
def health_check():
    """詳細的健康檢查"""
    try:
        # 資料庫檢查
        db_status = 'connected' if not db.is_closed() else 'disconnected'
        
        # LINE Bot 檢查
        line_status = 'configured' if (line_bot_api and handler) else 'not_configured'
        
        # 環境變數檢查
        env_status = {
            'CHANNEL_ACCESS_TOKEN': bool(CHANNEL_ACCESS_TOKEN),
            'CHANNEL_SECRET': bool(CHANNEL_SECRET),
            'GEMINI_API_KEY': bool(GEMINI_API_KEY)
        }
        
        # 系統統計
        try:
            stats = {
                'total_students': Student.select().count(),
                'total_messages': Message.select().count(),
                'real_students': Student.select().where(~Student.name.startswith('[DEMO]')).count()
            }
        except Exception:
            stats = {'error': 'Database query failed'}
        
        health_info = {
            'status': 'healthy' if (db_status == 'connected' and line_status == 'configured') else 'degraded',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': db_status,
            'line_bot': line_status,
            'environment_variables': env_status,
            'webhook_url': 'https://web-production-c8b8.up.railway.app/callback',
            'stats': stats,
            'version': '2.0.0'
        }
        
        return jsonify(health_info)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

# =================== 其他路由 ===================

@app.route('/')
def index():
    """首頁"""
    return {
        'message': '🎓 EMI 智能教學助理',
        'status': 'running',
        'webhook_url': 'https://web-production-c8b8.up.railway.app/callback',
        'health_check': 'https://web-production-c8b8.up.railway.app/health',
        'line_bot_configured': line_bot_api is not None
    }

# =================== 錯誤處理 ===================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found', 'webhook_url': '/callback'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# =================== 初始化 ===================

def initialize_app():
    """初始化應用程式"""
    try:
        # 初始化資料庫
        initialize_db()
        logger.info("✅ 資料庫初始化完成")
        
        # 建立範例資料（如果需要）
        try:
            if Student.select().count() == 0:
                create_sample_data()
                logger.info("✅ 範例資料建立完成")
        except Exception as e:
            logger.warning(f"範例資料建立警告: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 應用程式初始化失敗: {e}")
        return False

# 初始化應用程式
if __name__ == "__main__":
    logger.info("🚀 啟動 EMI 智能教學助理")
    
    # 初始化
    init_success = initialize_app()
    
    # 環境檢查報告
    logger.info("=== 系統狀態報告 ===")
    logger.info(f"📱 LINE Bot: {'✅ 已配置' if line_bot_api else '❌ 未配置'}")
    logger.info(f"🤖 Gemini AI: {'✅ 已配置' if GEMINI_API_KEY else '❌ 未配置'}")
    logger.info(f"💾 資料庫: {'✅ 已初始化' if init_success else '❌ 初始化失敗'}")
    logger.info(f"🌐 Webhook URL: https://web-production-c8b8.up.railway.app/callback")
    
    # 啟動伺服器
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
else:
    # 生產環境初始化
    initialize_app()

# WSGI 應用程式入口點
application = app
