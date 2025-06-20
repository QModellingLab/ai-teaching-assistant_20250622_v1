import os
import json
import datetime
import logging
from flask import Flask, request, abort
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
from routes import init_routes

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 應用初始化
app = Flask(__name__)

# 環境變數設定 - 修復變數名稱
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN') or os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET') or os.getenv('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    logger.error("Missing LINE Bot credentials")
    logger.info("請檢查環境變數: CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET")
    # 不要拋出錯誤，允許系統啟動以便檢查
else:
    logger.info("LINE Bot 憑證已載入")

if not GEMINI_API_KEY:
    logger.error("Missing Gemini API key")
    logger.info("請檢查環境變數: GEMINI_API_KEY")
else:
    logger.info("Gemini API 金鑰已載入")

# LINE Bot API 初始化
if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(CHANNEL_SECRET)
    logger.info("LINE Bot API 初始化成功")
else:
    line_bot_api = None
    handler = None
    logger.warning("LINE Bot API 未初始化")

# 初始化資料庫
try:
    initialize_db()
    logger.info("資料庫初始化成功")
except Exception as e:
    logger.error(f"資料庫初始化失敗: {e}")

# 初始化路由
init_routes(app)

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook 處理"""
    if not handler:
        logger.error("LINE Bot handler 未初始化")
        abort(500)
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    logger.info(f"Request body: {body}")
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    except Exception as e:
        logger.error(f"處理 webhook 時發生錯誤: {e}")
        abort(500)
    
    return 'OK'

if handler:  # 只有在 handler 存在時才註冊事件處理器
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """處理 LINE 訊息事件"""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            
            logger.info(f"收到訊息: {user_id} - {message_text}")
            
            # 取得或建立學生記錄
            student = get_or_create_student(user_id, event)
            
            # 記錄訊息
            save_message(student, message_text, event)
            
            # 更新學生統計
            update_student_stats(student.id)
            
            # 處理 AI 回應
            if message_text.startswith('@AI') or event.source.type == 'user':
                handle_ai_request(event, student, message_text)
            
            # 進行週期性分析
            if student.message_count % 5 == 0:  # 每5則訊息分析一次
                perform_periodic_analysis(student)
                
        except Exception as e:
            logger.error(f"處理訊息時發生錯誤: {e}")
            # 回傳錯誤訊息給用戶
            try:
                if line_bot_api:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="抱歉，系統處理時發生錯誤，請稍後再試。")
                    )
            except:
                pass

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
        except:
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
        
        logger.info(f"建立新學生記錄: {display_name} ({user_id})")
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
    
    logger.info(f"訊息已儲存: {student.name} - {message_text[:50]}...")
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

def handle_ai_request(event, student, message_text):
    """處理 AI 請求"""
    try:
        # 移除 @AI 前綴（如果有的話）
        query = message_text.replace('@AI', '').strip()
        if not query:
            query = message_text
        
        # 取得 AI 回應
        ai_response = get_ai_response(query, student.id)
        
        if ai_response and line_bot_api:
            # 儲存 AI 回應記錄
            AIResponse.create(
                student=student,
                query=query,
                response=ai_response,
                timestamp=datetime.datetime.now(),
                response_type='gemini'
            )
            
            # 回傳給用戶
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=ai_response)
            )
            
            logger.info(f"AI 回應已發送給 {student.name}")
        else:
            if line_bot_api:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="抱歉，我現在無法回應您的問題，請稍後再試。")
                )
            
    except Exception as e:
        logger.error(f"處理 AI 請求時發生錯誤: {e}")
        try:
            if line_bot_api:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="系統處理中發生問題，請稍後再試。")
                )
        except:
            pass

def perform_periodic_analysis(student):
    """執行週期性分析"""
    try:
        analysis_result = analyze_student_patterns(student.id)
        if analysis_result:
            # 儲存分析結果
            Analysis.create(
                student=student,
                analysis_type='pattern_analysis',
                content=analysis_result,
                created_at=datetime.datetime.now()
            )
            
            logger.info(f"完成學生分析: {student.name}")
            
    except Exception as e:
        logger.error(f"執行分析時發生錯誤: {e}")

@app.route('/health')
def health_check():
    """健康檢查端點"""
    try:
        return {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'connected' if not db.is_closed() else 'disconnected',
            'line_bot': 'configured' if line_bot_api else 'not_configured',
            'gemini_ai': 'configured' if GEMINI_API_KEY else 'not_configured'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }, 500

@app.route('/stats')
def get_stats():
    """取得系統統計資料"""
    try:
        stats = {
            'total_students': Student.select().count(),
            'total_messages': Message.select().count(),
            'total_questions': Message.select().where(Message.message_type == 'question').count(),
            'total_ai_responses': AIResponse.select().count(),
            'active_today': Student.select().where(
                Student.last_active >= datetime.datetime.now().date()
            ).count()
        }
        return stats
    except Exception as e:
        logger.error(f"取得統計資料時發生錯誤: {e}")
        return {'error': 'Unable to fetch stats'}, 500

# 錯誤處理
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return {'error': 'Internal server error'}, 500

# 初始化範例資料的函數 - 移除過時的裝飾器
def initialize_sample_data():
    """初始化範例資料"""
    try:
        # 檢查是否已有資料
        if Student.select().count() == 0:
            logger.info("建立範例資料...")
            create_sample_data()
            logger.info("範例資料建立完成")
    except Exception as e:
        logger.error(f"建立範例資料時發生錯誤: {e}")

# 在應用程式啟動時初始化資料
with app.app_context():
    try:
        initialize_sample_data()
    except Exception as e:
        logger.error(f"應用程式初始化錯誤: {e}")

# 程式進入點
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"啟動應用程式 - Port: {port}, Debug: {debug}")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點（用於生產環境）
application = app
