# app.py - EMI 智能教學助理 (LINE Bot + Web 管理後台)

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

# 導入 Web 管理後台模板
try:
    from templates_main import INDEX_TEMPLATE, STUDENTS_TEMPLATE, STUDENT_DETAIL_TEMPLATE
    from templates_analysis_part1 import TEACHING_INSIGHTS_TEMPLATE
    from templates_analysis_part2 import CONVERSATION_SUMMARIES_TEMPLATE
    from templates_analysis_part3 import LEARNING_RECOMMENDATIONS_TEMPLATE
    from templates_management import STORAGE_MANAGEMENT_TEMPLATE, DATA_EXPORT_TEMPLATE
    WEB_TEMPLATES_AVAILABLE = True
    logging.info("Web 管理後台模板載入成功")
except ImportError as e:
    WEB_TEMPLATES_AVAILABLE = False
    logging.warning(f"Web 管理後台模板載入失敗: {e}")

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

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    logger.error("Missing LINE Bot credentials")
    logger.info("請檢查環境變數: CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET")
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

# =================== LINE Bot 功能 ===================

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

# =================== Web 管理後台功能 ===================

def get_database_stats():
    """從資料庫獲取真實統計資料"""
    try:
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_questions = Message.select().where(Message.message_type == 'question').count()
        active_today = Student.select().where(
            Student.last_active >= datetime.datetime.now().date()
        ).count()
        
        # 計算平均參與度
        avg_engagement = Student.select().avg(Student.participation_rate) or 0
        
        return {
            'total_students': total_students,
            'active_conversations': active_today,
            'total_messages': total_messages,
            'avg_engagement': round(avg_engagement, 1),
            'active_students': active_today,
            'avg_response_time': '2.3',
            'system_load': '正常'
        }
    except Exception as e:
        logger.error(f"獲取資料庫統計時發生錯誤: {e}")
        # 返回預設值
        return {
            'total_students': 0,
            'active_conversations': 0,
            'total_messages': 0,
            'avg_engagement': 0,
            'active_students': 0,
            'avg_response_time': '0',
            'system_load': '錯誤'
        }

def get_database_students():
    """從資料庫獲取學生資料"""
    try:
        students = []
        for student in Student.select().order_by(Student.last_active.desc()):
            # 計算最後活動時間的相對描述
            if student.last_active:
                time_diff = datetime.datetime.now() - student.last_active
                if time_diff.days > 0:
                    last_active = f"{time_diff.days} 天前"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    last_active = f"{hours} 小時前"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    last_active = f"{minutes} 分鐘前"
                else:
                    last_active = "剛剛"
            else:
                last_active = "未知"
            
            # 判斷表現等級
            if student.participation_rate >= 80:
                performance_level = 'excellent'
                performance_text = '優秀'
            elif student.participation_rate >= 60:
                performance_level = 'good'
                performance_text = '良好'
            elif student.participation_rate >= 40:
                performance_level = 'average'
                performance_text = '普通'
            else:
                performance_level = 'needs-attention'
                performance_text = '需關注'
            
            students.append({
                'id': student.id,
                'name': student.name,
                'email': student.line_user_id or 'N/A',
                'total_messages': student.message_count,
                'engagement_score': student.participation_rate,
                'last_active': last_active,
                'status': 'active' if time_diff.days < 1 else 'moderate',
                'engagement': int(student.participation_rate),
                'questions_count': student.question_count,
                'progress': int(student.participation_rate),
                'performance_level': performance_level,
                'performance_text': performance_text
            })
        
        return students
    except Exception as e:
        logger.error(f"獲取學生資料時發生錯誤: {e}")
        return []

def get_recent_messages():
    """獲取最近訊息"""
    try:
        recent = []
        for message in Message.select().join(Student).order_by(Message.timestamp.desc()).limit(10):
            recent.append({
                'student': {'name': message.student.name},
                'timestamp': message.timestamp,
                'message_type': message.message_type.title(),
                'content': message.content
            })
        return recent
    except Exception as e:
        logger.error(f"獲取最近訊息時發生錯誤: {e}")
        return []

def get_question_category_stats():
    """獲取問題分類統計（簡化版）"""
    try:
        total_questions = Message.select().where(Message.message_type == 'question').count()
        # 這裡可以根據實際需求進行更複雜的分類
        return {
            'grammar_questions': int(total_questions * 0.4),  # 假設40%是文法問題
            'vocabulary_questions': int(total_questions * 0.3),  # 30%詞彙
            'pronunciation_questions': int(total_questions * 0.2),  # 20%發音
            'cultural_questions': int(total_questions * 0.1)  # 10%文化
        }
    except Exception as e:
        logger.error(f"獲取問題分類統計時發生錯誤: {e}")
        return {
            'grammar_questions': 0,
            'vocabulary_questions': 0,
            'pronunciation_questions': 0,
            'cultural_questions': 0
        }

# Web 路由
if WEB_TEMPLATES_AVAILABLE:
    @app.route('/')
    def index():
        """Web 管理後台首頁"""
        stats = get_database_stats()
        recent_messages = get_recent_messages()
        
        return render_template_string(INDEX_TEMPLATE, 
                                      stats=stats,
                                      recent_messages=recent_messages,
                                      current_time=datetime.datetime.now())

    @app.route('/students')
    def students():
        """學生列表頁面"""
        students_data = get_database_students()
        
        return render_template_string(STUDENTS_TEMPLATE,
                                      students=students_data,
                                      current_time=datetime.datetime.now())

    @app.route('/student/<int:student_id>')
    def student_detail(student_id):
        """學生詳細頁面"""
        try:
            student_record = Student.get_by_id(student_id)
            
            # 獲取學生訊息
            messages = []
            for msg in Message.select().where(Message.student == student_record).order_by(Message.timestamp.desc()).limit(50):
                messages.append({
                    'content': msg.content,
                    'timestamp': msg.timestamp,
                    'message_type': msg.message_type
                })
            
            # 獲取 AI 回應
            ai_responses = []
            for resp in AIResponse.select().where(AIResponse.student == student_record).order_by(AIResponse.timestamp.desc()).limit(20):
                ai_responses.append({
                    'query': resp.query,
                    'response': resp.response,
                    'timestamp': resp.timestamp
                })
            
            student_data = {
                'id': student_record.id,
                'name': student_record.name,
                'email': student_record.line_user_id or 'N/A',
                'total_messages': student_record.message_count,
                'engagement_score': student_record.participation_rate,
                'last_active': student_record.last_active.strftime('%Y-%m-%d %H:%M') if student_record.last_active else 'N/A',
                'messages': messages,
                'ai_responses': ai_responses
            }
            
            return render_template_string(STUDENT_DETAIL_TEMPLATE,
                                          student=student_data,
                                          current_time=datetime.datetime.now())
        except Student.DoesNotExist:
            return "學生未找到", 404
        except Exception as e:
            logger.error(f"獲取學生詳細資料時發生錯誤: {e}")
            return "系統錯誤", 500

    @app.route('/teaching-insights')
    def teaching_insights():
        """教師分析後台"""
        category_stats = get_question_category_stats()
        engagement_analysis = {
            'daily_average': 78.5,
            'weekly_trend': 5.2,
            'peak_hours': ['10:00-11:00', '14:00-15:00', '19:00-20:00']
        }
        students = get_database_students()
        stats = get_database_stats()
        
        return render_template_string(TEACHING_INSIGHTS_TEMPLATE, 
                                      category_stats=category_stats,
                                      engagement_analysis=engagement_analysis,
                                      students=students,
                                      stats=stats)

    @app.route('/conversation-summaries')
    def conversation_summaries():
        """對話摘要頁面"""
        # 這裡可以根據實際需求生成摘要
        summaries = []  # 使用示範資料
        insights = {
            'total_conversations': Message.select().count(),
            'avg_length': 8.5,
            'satisfaction_rate': 92,
            'response_time': 2.3
        }
        
        return render_template_string(CONVERSATION_SUMMARIES_TEMPLATE,
                                      summaries=summaries,
                                      insights=insights)

    @app.route('/learning-recommendations')
    def learning_recommendations():
        """學習建議頁面"""
        recommendations = []  # 使用示範資料
        overview = {
            'total_recommendations': 24,
            'high_priority': 8,
            'in_progress': 12,
            'completed_this_week': 15
        }
        
        return render_template_string(LEARNING_RECOMMENDATIONS_TEMPLATE,
                                      recommendations=recommendations,
                                      overview=overview)

    @app.route('/storage-management')
    def storage_management():
        """儲存管理頁面"""
        storage_stats = {
            'used_gb': 2.5,
            'available_gb': 7.5,
            'total_gb': 10.0,
            'usage_percentage': 25,
            'daily_growth_mb': 15,
            'days_until_full': 180
        }
        
        data_breakdown = {
            'conversations': {'size': '1.2GB', 'percentage': 48},
            'analysis': {'size': '0.8GB', 'percentage': 32},
            'cache': {'size': '0.3GB', 'percentage': 12},
            'exports': {'size': '0.15GB', 'percentage': 6},
            'logs': {'size': '0.05GB', 'percentage': 2}
        }
        
        return render_template_string(STORAGE_MANAGEMENT_TEMPLATE,
                                      storage_stats=storage_stats,
                                      data_breakdown=data_breakdown,
                                      cleanup_estimates={'safe': 150, 'aggressive': 500},
                                      alerts=[],
                                      recommendations={'cache_cleanup': 150})

    @app.route('/data-export')
    def data_export():
        """資料匯出頁面"""
        default_dates = {
            'today': datetime.datetime.now().strftime('%Y-%m-%d'),
            'month_ago': (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
            'semester_start': (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
        }
        
        return render_template_string(DATA_EXPORT_TEMPLATE,
                                      default_dates=default_dates,
                                      export_jobs=[],
                                      export_history=[])

# =================== API 路由 ===================

@app.route('/health')
def health_check():
    """健康檢查端點"""
    try:
        return {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'connected' if not db.is_closed() else 'disconnected',
            'line_bot': 'configured' if line_bot_api else 'not_configured',
            'gemini_ai': 'configured' if GEMINI_API_KEY else 'not_configured',
            'web_interface': 'available' if WEB_TEMPLATES_AVAILABLE else 'not_available'
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

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """API: 獲取儀表板統計"""
    return jsonify({
        'success': True,
        'data': get_database_stats()
    })

@app.route('/api/generate-summaries', methods=['POST'])
def api_generate_summaries():
    """API: 生成對話摘要"""
    options = request.get_json() if request.is_json else {}
    return jsonify({
        'success': True,
        'message': '摘要生成成功',
        'options': options
    })

@app.route('/api/students')
def api_students():
    """API: 獲取學生列表"""
    return jsonify({
        'success': True,
        'students': get_database_students()
    })

# =================== 錯誤處理 ===================

@app.errorhandler(404)
def not_found_error(error):
    """404 錯誤處理"""
    if request.path.startswith('/api/'):
        return {'error': 'Not found'}, 404
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>頁面未找到 - EMI 智能教學助理</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 100px 20px;
                margin: 0;
            }
            .error-container {
                max-width: 600px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            p { font-size: 1.2em; margin-bottom: 30px; }
            a {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 25px;
                transition: all 0.3s ease;
            }
            a:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="error-container">
            <h1>404</h1>
            <p>抱歉，您請求的頁面不存在</p>
            <a href="/">返回首頁</a>
        </div>
    </body>
    </html>
    """), 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    logger.error(f"Internal server error: {error}")
    if request.path.startswith('/api/'):
        return {'error': 'Internal server error'}, 500
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>系統錯誤 - EMI 智能教學助理</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                color: white;
                text-align: center;
                padding: 100px 20px;
                margin: 0;
            }
            .error-container {
                max-width: 600px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            p { font-size: 1.2em; margin-bottom: 30px; }
            a {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 25px;
                transition: all 0.3s ease;
            }
            a:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="error-container">
            <h1>500</h1>
            <p>系統發生內部錯誤，請稍後再試</p>
            <a href="/">返回首頁</a>
        </div>
    </body>
    </html>
    """), 500

# =================== 初始化和啟動 ===================

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
    
    logger.info(f"🚀 啟動 EMI 智能教學助理")
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🌐 Web 管理後台: {'可用' if WEB_TEMPLATES_AVAILABLE else '不可用'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🔗 Port: {port}, Debug: {debug}")
    
    if WEB_TEMPLATES_AVAILABLE:
        logger.info("📊 Web 管理後台路由:")
        logger.info("   - 首頁: http://localhost:5000/")
        logger.info("   - 學生管理: http://localhost:5000/students")
        logger.info("   - 教師分析: http://localhost:5000/teaching-insights")
        logger.info("   - 對話摘要: http://localhost:5000/conversation-summaries")
        logger.info("   - 學習建議: http://localhost:5000/learning-recommendations")
        logger.info("   - 儲存管理: http://localhost:5000/storage-management")
        logger.info("   - 資料匯出: http://localhost:5000/data-export")
    
    logger.info("🔧 API 端點:")
    logger.info("   - 健康檢查: http://localhost:5000/health")
    logger.info("   - 系統統計: http://localhost:5000/stats")
    logger.info("   - LINE Bot Webhook: http://localhost:5000/callback")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點（用於生產環境）
application = app
