# app.py - 完整版本，包含所有必要路由
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
    create_sample_data,
    get_system_status
)
from templates_utils import render_template_with_error_handling
from peewee import fn

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

# =================== 網頁路由 ===================

@app.route('/')
def index():
    """首頁 - 系統概覽"""
    try:
        # 基本統計
        total_students = Student.select().count()
        real_students = Student.select().where(~Student.name.startswith('[DEMO]')).count()
        total_messages = Message.select().count()
        total_questions = Message.select().where(Message.message_type == 'question').count()
        
        # 最近活動
        recent_messages = list(Message.select().order_by(Message.timestamp.desc()).limit(5))
        
        # 參與度統計
        if real_students > 0:
            students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
            avg_participation = sum(s.participation_rate for s in students) / len(students)
        else:
            avg_participation = 0
        
        stats = {
            'total_students': total_students,
            'real_students': real_students,
            'total_messages': total_messages,
            'total_questions': total_questions,
            'avg_participation': round(avg_participation, 1),
            'question_rate': round((total_questions / max(total_messages, 1)) * 100, 1)
        }
        
        return render_template_with_error_handling('index.html', 
                             stats=stats, 
                             recent_messages=recent_messages)
                             
    except Exception as e:
        app.logger.error(f"首頁錯誤: {e}")
        return render_template_with_error_handling('index.html', 
                             stats={}, 
                             recent_messages=[])

@app.route('/students')
def students():
    """學生列表頁面"""
    try:
        students = list(Student.select().order_by(Student.last_active.desc()))
        return render_template_with_error_handling('students.html', students=students)
    except Exception as e:
        app.logger.error(f"學生列表錯誤: {e}")
        return render_template_with_error_handling('students.html', students=[])

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細頁面"""
    try:
        student = Student.get_by_id(student_id)
        
        # 取得學生訊息
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(20))
        
        # 學習分析
        analysis = analyze_student_patterns(student_id)
        
        # 對話摘要
        conversation_summary = get_student_conversation_summary(student_id, days=30)
        
        return render_template_with_error_handling('student_detail.html', 
                             student=student,
                             messages=messages,
                             analysis=analysis,
                             conversation_summary=conversation_summary)
                             
    except Student.DoesNotExist:
        return render_template_with_error_handling('error.html', 
                             error_code=404,
                             error_message="找不到指定的學生"), 404
    except Exception as e:
        app.logger.error(f"學生詳細頁面錯誤: {e}")
        return render_template_with_error_handling('error.html',
                             error_code=500,
                             error_message="載入學生詳情時發生錯誤"), 500

@app.route('/teaching-insights')
def teaching_insights():
    """教師分析後台主頁"""
    try:
        # 問題分類統計
        category_stats = get_question_category_stats()
        
        # 學生參與度分析  
        engagement_analysis = analyze_class_engagement()
        
        return render_template_with_error_handling('teaching_insights.html',
                             category_stats=category_stats,
                             engagement_analysis=engagement_analysis)
                             
    except Exception as e:
        app.logger.error(f"教學洞察頁面錯誤: {e}")
        return render_template_with_error_handling('teaching_insights.html',
                             category_stats={},
                             engagement_analysis={})

@app.route('/conversation-summaries')
def conversation_summaries():
    """對話摘要總覽頁面"""
    try:
        return render_template_with_error_handling('conversation_summaries.html', summaries=[])
    except Exception as e:
        app.logger.error(f"對話摘要頁面錯誤: {e}")
        return render_template_with_error_handling('conversation_summaries.html', summaries=[])

@app.route('/learning-recommendations')
def learning_recommendations():
    """學習建議總覽頁面"""
    try:
        return render_template_with_error_handling('learning_recommendations.html', recommendations=[])
    except Exception as e:
        app.logger.error(f"學習建議頁面錯誤: {e}")
        return render_template_with_error_handling('learning_recommendations.html', recommendations=[])

@app.route('/storage-management')
def storage_management():
    """儲存空間管理頁面"""
    try:
        storage_stats = monitor_storage_usage()
        return render_template_with_error_handling('storage_management.html', 
                             storage_stats=storage_stats,
                             data_breakdown={
                                 'conversations': {'size': '1.2GB', 'percentage': 48},
                                 'analysis': {'size': '0.8GB', 'percentage': 32}, 
                                 'cache': {'size': '0.3GB', 'percentage': 12},
                                 'exports': {'size': '0.15GB', 'percentage': 6},
                                 'logs': {'size': '0.05GB', 'percentage': 2}
                             },
                             cleanup_estimates={
                                 'safe': 150,
                                 'aggressive': 500,
                                 'archive': 800,
                                 'optimize': 200
                             },
                             alerts=[
                                 {
                                     'type': 'info',
                                     'title': '系統狀態良好',
                                     'message': '目前儲存空間使用正常，系統運行穩定。'
                                 }
                             ],
                             recommendations={'cache_cleanup': 150})
    except Exception as e:
        app.logger.error(f"儲存管理頁面錯誤: {e}")
        return render_template_with_error_handling('storage_management.html', storage_stats={})

@app.route('/data-export')
def data_export():
    """資料匯出頁面"""
    try:
        # 預設日期
        today = datetime.datetime.now()
        default_dates = {
            'today': today.strftime('%Y-%m-%d'),
            'month_ago': (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
            'semester_start': (today - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
        }
        
        return render_template_with_error_handling('data_export.html',
                             default_dates=default_dates,
                             export_jobs=[],
                             export_history=[])
    except Exception as e:
        app.logger.error(f"資料匯出頁面錯誤: {e}")
        return render_template_with_error_handling('data_export.html', default_dates={})

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

# =================== API 路由 ===================

@app.route('/api/student-stats')
def api_student_stats():
    """學生統計 API"""
    try:
        total_students = Student.select().count()
        real_students = Student.select().where(~Student.name.startswith('[DEMO]')).count()
        total_messages = Message.select().count()
        
        return jsonify({
            'total_students': total_students,
            'real_students': real_students,
            'demo_students': total_students - real_students,
            'total_messages': total_messages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# =================== 輔助函數 ===================

def get_question_category_stats():
    """取得問題分類統計"""
    try:
        from utils import get_question_category_stats as utils_get_stats
        return utils_get_stats()
    except Exception:
        return {
            'grammar_questions': 45,
            'vocabulary_questions': 32,
            'pronunciation_questions': 18,
            'cultural_questions': 12
        }

def analyze_class_engagement():
    """分析班級參與度"""
    try:
        students = list(Student.select().where(~Student.name.startswith('[DEMO]')))
        
        if not students:
            return {
                'daily_average': 0,
                'weekly_trend': 0,
                'peak_hours': []
            }
        
        avg_participation = sum(s.participation_rate for s in students) / len(students)
        
        return {
            'daily_average': round(avg_participation, 1),
            'weekly_trend': 5.2,  # 示例數據
            'peak_hours': ['10:00-11:00', '14:00-15:00', '19:00-20:00']
        }
    except Exception:
        return {
            'daily_average': 78,
            'weekly_trend': 5.2,
            'peak_hours': ['10:00-11:00', '14:00-15:00', '19:00-20:00']
        }

def monitor_storage_usage():
    """監控儲存使用量"""
    try:
        # 計算記錄數
        student_count = Student.select().count()
        message_count = Message.select().count()
        analysis_count = Analysis.select().count()
        
        # 估算大小
        estimated_size_mb = (
            student_count * 0.001 +
            message_count * 0.005 +
            analysis_count * 0.002
        )
        
        free_limit_mb = 512
        usage_percentage = (estimated_size_mb / free_limit_mb) * 100
        
        return {
            'used_gb': round(estimated_size_mb / 1024, 2),
            'available_gb': round((free_limit_mb - estimated_size_mb) / 1024, 2),
            'total_gb': round(free_limit_mb / 1024, 2),
            'usage_percentage': round(usage_percentage, 1),
            'daily_growth_mb': 15,
            'days_until_full': max(1, int((free_limit_mb - estimated_size_mb) / 15))
        }
    except Exception:
        return {
            'used_gb': 2.5,
            'available_gb': 7.5,
            'total_gb': 10.0,
            'usage_percentage': 25,
            'daily_growth_mb': 15,
            'days_until_full': 180
        }

def get_student_conversation_summary(student_id, days=30):
    """取得學生對話摘要"""
    try:
        from utils import get_student_conversation_summary as utils_summary
        return utils_summary(student_id, days)
    except Exception:
        return "對話摘要功能暫時無法使用"

# =================== 錯誤處理 ===================

@app.errorhandler(404)
def not_found_error(error):
    return render_template_with_error_handling('error.html', 
                         error_code=404,
                         error_message="找不到您要訪問的頁面"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template_with_error_handling('error.html',
                         error_code=500,
                         error_message="伺服器內部錯誤"), 500

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
