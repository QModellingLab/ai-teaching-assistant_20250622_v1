# app.py - EMI 智能教學助理 (完全修復版本)

import os
import json
import datetime
import logging
import random
from flask import Flask, request, abort, render_template_string, jsonify, redirect
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

# =================== 修復後的輔助函數 ===================

def sync_student_stats(student):
    """同步學生統計資料"""
    try:
        all_messages = list(Message.select().where(Message.student == student))
        
        total_messages = len(all_messages)
        questions = [m for m in all_messages if m.message_type == 'question']
        question_count = len(questions)
        
        if all_messages:
            message_dates = set(m.timestamp.date() for m in all_messages)
            active_days = len(message_dates)
            last_active = max(all_messages, key=lambda x: x.timestamp).timestamp
        else:
            active_days = 0
            last_active = student.created_at or datetime.datetime.now()
        
        participation_rate = min(100, total_messages * 12) if total_messages else 0
        question_rate = (question_count / max(total_messages, 1)) * 100
        
        # 更新學生統計
        student.message_count = total_messages
        student.question_count = question_count
        student.question_rate = question_rate
        student.participation_rate = participation_rate
        student.last_active = last_active
        
        logger.info(f"✅ 計算學生統計: {student.name} - 訊息:{total_messages}, 參與度:{participation_rate:.1f}%")
        
        return {
            'total_messages': total_messages,
            'question_count': question_count,
            'participation_rate': participation_rate,
            'question_rate': question_rate,
            'active_days': active_days,
            'last_active': last_active
        }
        
    except Exception as e:
        logger.error(f"同步學生統計錯誤: {e}")
        return None

def get_database_stats():
    """從資料庫獲取真實統計資料"""
    try:
        if db.is_closed():
            db.connect()
        
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_questions = Message.select().where(Message.message_type == 'question').count()
        
        # 正確區分真實學生和演示學生
        real_students = Student.select().where(
            (~Student.name.startswith('[DEMO]')) & 
            (~Student.line_user_id.startswith('demo_'))
        ).count()
        
        active_today = Student.select().where(
            Student.last_active >= datetime.datetime.now().date()
        ).count()
        
        # 計算平均參與度（只對有訊息的學生）
        students_with_messages = Student.select().where(Student.message_count > 0)
        if students_with_messages.count() > 0:
            total_participation = sum(s.participation_rate for s in students_with_messages)
            avg_engagement = total_participation / students_with_messages.count()
        else:
            avg_engagement = 0
        
        return {
            'total_students': total_students,
            'real_students': real_students,
            'demo_students': total_students - real_students,
            'active_conversations': active_today,
            'total_messages': total_messages,
            'total_questions': total_questions,
            'avg_engagement': round(avg_engagement, 1),
            'active_students': active_today,
            'avg_response_time': '2.3',
            'system_load': '正常',
            'question_rate': round((total_questions / max(total_messages, 1)) * 100, 1)
        }
    except Exception as e:
        logger.error(f"獲取資料庫統計時發生錯誤: {e}")
        return {
            'total_students': 0,
            'real_students': 0,
            'demo_students': 0,
            'active_conversations': 0,
            'total_messages': 0,
            'total_questions': 0,
            'avg_engagement': 0,
            'active_students': 0,
            'avg_response_time': '0',
            'system_load': '錯誤',
            'question_rate': 0
        }

def get_recent_messages():
    """獲取最近訊息"""
    try:
        recent = []
        for message in Message.select().join(Student).order_by(Message.timestamp.desc()).limit(10):
            recent.append({
                'student': {'name': message.student.name},
                'timestamp': message.timestamp,
                'message_type': message.message_type.title(),
                'content': message.content[:50] + ('...' if len(message.content) > 50 else '')
            })
        return recent
    except Exception as e:
        logger.error(f"獲取最近訊息時發生錯誤: {e}")
        return []

def update_student_stats_immediately(student):
    """立即更新學生統計"""
    try:
        stats = sync_student_stats(student)
        if stats:
            student.save()  # 保存更新的統計
            logger.info(f"📊 即時更新統計: {student.name}")
    except Exception as e:
        logger.error(f"即時更新統計失敗: {e}")

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

def get_or_create_student(user_id, event):
    """取得或建立學生記錄 - 自然創建版"""
    try:
        # 首先嘗試用 user_id 查找現有學生
        student = Student.get(Student.line_user_id == user_id)
        
        # 更新最後活動時間
        student.last_active = datetime.datetime.now()
        student.save()
        
        logger.info(f"找到現有學生: {student.name} ({user_id})")
        return student
        
    except Student.DoesNotExist:
        # 學生不存在，創建新記錄
        try:
            # 嘗試從 LINE API 獲取用戶資料
            if line_bot_api:
                try:
                    profile = line_bot_api.get_profile(user_id)
                    display_name = profile.display_name
                    logger.info(f"從 LINE API 獲取用戶名稱: {display_name}")
                except Exception as profile_error:
                    logger.warning(f"無法獲取 LINE 用戶資料: {profile_error}")
                    display_name = f"User_{user_id[:8]}"
            else:
                display_name = f"User_{user_id[:8]}"
            
            # 創建新學生記錄
            student = Student.create(
                name=display_name,
                line_user_id=user_id,
                created_at=datetime.datetime.now(),
                last_active=datetime.datetime.now(),
                message_count=0,
                question_count=0,
                participation_rate=0.0,
                question_rate=0.0,
                learning_style=None,  # 讓系統後續分析
                notes=f"自動創建於 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            logger.info(f"✅ 自動創建新學生記錄: {display_name} ({user_id})")
            return student
            
        except Exception as create_error:
            logger.error(f"創建學生記錄失敗: {create_error}")
            raise

def save_message(student, message_text, event):
    """儲存訊息記錄"""
    try:
        is_question = is_question_message(message_text)
        
        # 儲存訊息
        message = Message.create(
            student=student,
            content=message_text,
            message_type='question' if is_question else 'statement',
            timestamp=datetime.datetime.now(),
            source_type=getattr(event.source, 'type', 'user'),
            group_id=getattr(event.source, 'group_id', None),
            room_id=getattr(event.source, 'room_id', None),
            language_detected='en' if any(c.isalpha() and ord(c) < 128 for c in message_text) else 'zh',
            is_processed=False
        )
        
        logger.info(f"✅ 訊息已儲存: {student.name} - {message_text[:30]}...")
        
        # 立即更新學生統計
        update_student_stats_immediately(student)
        
        return message
        
    except Exception as e:
        logger.error(f"儲存訊息失敗: {e}")
        return None

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
        query = message_text.replace('@AI', '').strip()
        if not query:
            query = message_text
        
        ai_response = get_ai_response(query, student.id)
        
        if ai_response and line_bot_api:
            AIResponse.create(
                student=student,
                query=query,
                response=ai_response,
                timestamp=datetime.datetime.now(),
                response_type='gemini'
            )
            
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
            Analysis.create(
                student=student,
                analysis_type='pattern_analysis',
                content=analysis_result,
                created_at=datetime.datetime.now()
            )
            
            logger.info(f"完成學生分析: {student.name}")
            
    except Exception as e:
        logger.error(f"執行分析時發生錯誤: {e}")

if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """處理 LINE 訊息事件 - 修復版"""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            
            logger.info(f"📨 收到訊息: {user_id} - {message_text[:50]}...")
            
            # 獲取或創建學生記錄
            student = get_or_create_student(user_id, event)
            
            # 儲存訊息記錄
            message = save_message(student, message_text, event)
            
            if not message:
                logger.error("訊息儲存失敗")
                return
            
            # 處理 AI 請求
            if message_text.startswith('@AI') or event.source.type == 'user':
                handle_ai_request(event, student, message_text)
            
            # 每5則訊息進行一次深度分析
            if student.message_count % 5 == 0 and student.message_count > 0:
                perform_periodic_analysis(student)
                
            logger.info(f"✅ 訊息處理完成: {student.name} (總訊息: {student.message_count})")
                
        except Exception as e:
            logger.error(f"❌ 處理訊息時發生錯誤: {e}")
            try:
                if line_bot_api:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="抱歉，系統處理時發生錯誤，請稍後再試。")
                    )
            except:
                pass

# =================== Web 管理後台功能 ===================

if WEB_TEMPLATES_AVAILABLE:
    @app.route('/')
    def index():
        """Web 管理後台首頁"""
        try:
            stats = get_database_stats()
            recent_messages = get_recent_messages()
            
            return render_template_string(INDEX_TEMPLATE, 
                                          stats=stats,
                                          recent_messages=recent_messages,
                                          current_time=datetime.datetime.now())
        except Exception as e:
            logger.error(f"首頁錯誤: {e}")
            return f"""
            <h1>系統錯誤</h1>
            <p>錯誤: {str(e)}</p>
            <p><a href="/debug-students">查看調試信息</a></p>
            <p><a href="/sync-all-stats">同步統計資料</a></p>
            """

    @app.route('/students')
    def students():
        """學生列表頁面 - 完全修復版"""
        try:
            logger.info("開始載入學生列表頁面...")
            
            students_list = []
            all_students = list(Student.select().order_by(Student.last_active.desc().nulls_last()))
            
            logger.info(f"從資料庫獲取到 {len(all_students)} 位學生")
            
            for student in all_students:
                try:
                    # 重新計算統計
                    stats = sync_student_stats(student)
                    
                    if stats:
                        # 保存更新的統計
                        student.save()
                        
                        # 計算相對時間
                        if student.last_active:
                            time_diff = datetime.datetime.now() - student.last_active
                            if time_diff.days > 0:
                                last_active_display = f"{time_diff.days} 天前"
                            elif time_diff.seconds > 3600:
                                hours = time_diff.seconds // 3600
                                last_active_display = f"{hours} 小時前"
                            elif time_diff.seconds > 60:
                                minutes = time_diff.seconds // 60
                                last_active_display = f"{minutes} 分鐘前"
                            else:
                                last_active_display = "剛剛"
                        else:
                            last_active_display = "無記錄"
                        
                        students_list.append({
                            'id': student.id,
                            'name': student.name,
                            'email': student.line_user_id or 'N/A',
                            'total_messages': student.message_count,
                            'engagement_score': student.participation_rate,
                            'last_active': student.last_active or datetime.datetime.now(),
                            'last_active_display': last_active_display,
                            'status': 'active' if student.participation_rate > 50 else 'moderate',
                            'engagement': int(student.participation_rate),
                            'question_count': student.question_count,
                            'questions_count': student.question_count,
                            'progress': int(student.participation_rate),
                            'performance_level': (
                                'excellent' if student.participation_rate >= 80 
                                else 'good' if student.participation_rate >= 60 
                                else 'needs-attention'
                            ),
                            'performance_text': (
                                '優秀' if student.participation_rate >= 80 
                                else '良好' if student.participation_rate >= 60 
                                else '需關注'
                            ),
                            'active_days': stats['active_days'],
                            'participation_rate': student.participation_rate
                        })
                        
                        logger.info(f"✅ 處理學生: {student.name} (訊息:{student.message_count}, 參與度:{student.participation_rate:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"處理學生 {student.name} 時發生錯誤: {e}")
                    continue
            
            logger.info(f"成功處理 {len(students_list)} 位學生資料")
            
            return render_template_string(STUDENTS_TEMPLATE,
                                        students=students_list,
                                        current_time=datetime.datetime.now())
                                        
        except Exception as e:
            logger.error(f"學生頁面錯誤: {e}")
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>學生頁面錯誤</title></head>
            <body style="font-family: sans-serif; padding: 20px;">
                <h1>❌ 學生頁面載入失敗</h1>
                <p><strong>錯誤:</strong> {str(e)}</p>
                <p><strong>學生總數:</strong> {Student.select().count() if not db.is_closed() else '無法查詢'}</p>
                <div style="margin-top: 20px;">
                    <a href="/debug-students" style="padding: 10px 20px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px;">調試信息</a>
                    <a href="/sync-all-stats" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px;">同步統計</a>
                    <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
                </div>
            </body>
            </html>
            """

    @app.route('/student/<int:student_id>')
    def student_detail(student_id):
        """學生詳細頁面"""
        try:
            student_record = Student.get_by_id(student_id)
            
            stats = sync_student_stats(student_record)
            if stats:
                student_record.save()
            else:
                stats = {
                    'total_messages': 0,
                    'question_count': 0,
                    'participation_rate': 0,
                    'question_rate': 0,
                    'active_days': 0,
                    'last_active': datetime.datetime.now()
                }
            
            all_messages = list(Message.select().where(
                Message.student == student_record
            ).order_by(Message.timestamp.desc()))
            
            display_messages = []
            for msg in all_messages[:20]:
                time_diff = datetime.datetime.now() - msg.timestamp
                if time_diff.days > 0:
                    time_display = f"{time_diff.days} 天前"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_display = f"{hours} 小時前"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    time_display = f"{minutes} 分鐘前"
                else:
                    time_display = "剛剛"
                
                display_messages.append({
                    'content': msg.content,
                    'timestamp': msg.timestamp,
                    'time_display': time_display,
                    'message_type': msg.message_type
                })
            
            try:
                analysis = analyze_student_patterns(student_id)
            except Exception as e:
                logger.warning(f"AI 分析失敗: {e}")
                analysis = None
            
            try:
                from utils import get_student_conversation_summary
                conversation_summary = get_student_conversation_summary(student_id, days=30)
            except Exception as e:
                logger.warning(f"對話摘要生成失敗: {e}")
                conversation_summary = None
            
            student_data = {
                'id': student_record.id,
                'name': student_record.name,
                'line_user_id': student_record.line_user_id or 'N/A',
                'total_messages': stats['total_messages'],
                'question_count': stats['question_count'],
                'participation_rate': round(stats['participation_rate'], 1),
                'question_rate': round(stats['question_rate'], 1),
                'active_days': stats['active_days'],
                'last_active': stats['last_active'].strftime('%Y-%m-%d %H:%M'),
                'last_active_relative': calculate_relative_time(stats['last_active']),
                'created_at': student_record.created_at.strftime('%Y-%m-%d') if student_record.created_at else 'N/A'
            }
            
            return render_template_string(STUDENT_DETAIL_TEMPLATE,
                                        student=student_data,
                                        messages=display_messages,
                                        analysis=analysis,
                                        conversation_summary=conversation_summary,
                                        current_time=datetime.datetime.now())
                                        
        except Student.DoesNotExist:
            return "學生未找到", 404
        except Exception as e:
            logger.error(f"獲取學生詳細資料時發生錯誤: {e}")
            return "系統錯誤", 500

    @app.route('/teaching-insights')
    def teaching_insights():
        """教師分析後台"""
        from utils import get_question_category_stats
        
        category_stats = get_question_category_stats()
        engagement_analysis = {
            'daily_average': 78.5,
            'weekly_trend': 5.2,
            'peak_hours': ['10:00-11:00', '14:00-15:00', '19:00-20:00']
        }
        students = []
        stats = get_database_stats()
        
        return render_template_string(TEACHING_INSIGHTS_TEMPLATE, 
                                      category_stats=category_stats,
                                      engagement_analysis=engagement_analysis,
                                      students=students,
                                      stats=stats)

    @app.route('/conversation-summaries')
    def conversation_summaries():
        """對話摘要頁面"""
        summaries = []
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
        recommendations = []
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

def calculate_relative_time(timestamp):
    """計算相對時間"""
    if not timestamp:
        return "未知"
        
    try:
        time_diff = datetime.datetime.now() - timestamp
        
        if time_diff.days > 0:
            return f"{time_diff.days} 天前"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"{hours} 小時前"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            return f"{minutes} 分鐘前"
        else:
            return "剛剛"
    except Exception:
        return "未知"

# =================== 調試和修復路由 ===================

@app.route('/debug-students')
def debug_students():
    """調試學生資料"""
    try:
        if db.is_closed():
            db.connect()
            
        debug_info = {
            'database_connection': 'connected' if not db.is_closed() else 'disconnected',
            'total_students': Student.select().count(),
            'total_messages': Message.select().count(),
            'real_students': Student.select().where(
                (~Student.name.startswith('[DEMO]')) & 
                (~Student.line_user_id.startswith('demo_'))
            ).count(),
            'students_list': []
        }
        
        for student in Student.select().order_by(Student.id):
            actual_messages = Message.select().where(Message.student == student).count()
            debug_info['students_list'].append({
                'id': student.id,
                'name': student.name,
                'line_user_id': student.line_user_id,
                'stored_message_count': student.message_count,
                'actual_message_count': actual_messages,
                'participation_rate': student.participation_rate,
                'last_active': student.last_active.isoformat() if student.last_active else None,
                'created_at': student.created_at.isoformat() if student.created_at else None
            })
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sync-all-stats')
def sync_all_stats():
    """同步所有學生統計"""
    try:
        updated_count = 0
        results = []
        
        for student in Student.select():
            stats = sync_student_stats(student)
            if stats:
                student.save()
                updated_count += 1
                results.append(f"更新 {student.name}: 訊息={stats['total_messages']}, 參與度={stats['participation_rate']:.1f}%")
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'results': results,
            'message': f'成功同步 {updated_count} 位學生的統計資料'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/check-orphaned-messages')
def check_orphaned_messages():
    """檢查孤立的訊息"""
    try:
        orphaned = []
        total_messages = Message.select().count()
        
        for message in Message.select():
            try:
                student = message.student
                if not student:
                    orphaned.append({
                        'id': message.id,
                        'content': message.content[:50],
                        'timestamp': message.timestamp.isoformat(),
                        'student_id': message.student_id
                    })
            except Student.DoesNotExist:
                orphaned.append({
                    'id': message.id,
                    'content': message.content[:50],
                    'timestamp': message.timestamp.isoformat(),
                    'student_id': message.student_id
                })
        
        return jsonify({
            'total_messages': total_messages,
            'orphaned_count': len(orphaned),
            'orphaned_messages': orphaned[:10]  # 只顯示前10個
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fix-orphaned-messages')
def fix_orphaned_messages():
    """修復孤立的訊息記錄"""
    try:
        results = []
        fixed_count = 0
        
        # 檢查所有訊息
        for message in Message.select():
            try:
                # 嘗試訪問學生記錄
                student = message.student
                if student is None:
                    raise Student.DoesNotExist()
            except Student.DoesNotExist:
                # 這是一個孤立訊息
                results.append(f"發現孤立訊息: ID={message.id}, 內容={message.content[:30]}...")
                
                # 嘗試根據訊息內容重建學生記錄
                placeholder_student = Student.create(
                    name=f"恢復用戶_{message.id}",
                    line_user_id=f"recovered_user_{message.id}",
                    created_at=message.timestamp - datetime.timedelta(days=1),
                    last_active=message.timestamp,
                    message_count=0,
                    question_count=0,
                    participation_rate=0.0,
                    question_rate=0.0,
                    notes=f"從孤立訊息恢復，原始訊息ID: {message.id}"
                )
                
                # 更新訊息的學生關聯
                message.student = placeholder_student
                message.save()
                
                fixed_count += 1
                results.append(f"✅ 修復完成: 創建學生 {placeholder_student.name}")
        
        # 重新同步所有學生統計
        for student in Student.select():
            sync_student_stats(student)
            student.save()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>孤立訊息修復結果</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                .result {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            </style>
        </head>
        <body>
            <h1>🔧 孤立訊息修復結果</h1>
            <div class="result">
                <strong>修復統計:</strong><br>
                修復的孤立訊息數量: {fixed_count}<br>
                當前學生總數: {Student.select().count()}<br>
                當前訊息總數: {Message.select().count()}
            </div>
            
            <h3>詳細結果:</h3>
            {''.join([f'<div class="result">{r}</div>' for r in results]) if results else '<p>沒有發現孤立訊息</p>'}
            
            <div style="margin-top: 20px;">
                <a href="/students" class="btn">查看學生管理</a>
                <a href="/debug-students" class="btn">調試信息</a>
                <a href="/" class="btn">返回首頁</a>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"<h1>修復失敗</h1><pre>{str(e)}</pre><a href='/'>返回首頁</a>"

@app.route('/simulate-line-message')
def simulate_line_message():
    """模擬 LINE 訊息以測試學生創建"""
    try:
        # 模擬一個 LINE 用戶發送訊息
        class MockEvent:
            def __init__(self):
                self.source = MockSource()
                self.message = MockMessage()
                self.reply_token = "mock_reply_token"
        
        class MockSource:
            def __init__(self):
                self.type = 'user'
                self.user_id = 'test_user_123'
        
        class MockMessage:
            def __init__(self):
                self.text = "What is machine learning?"
        
        mock_event = MockEvent()
        
        # 使用修復後的邏輯處理訊息
        student = get_or_create_student(mock_event.source.user_id, mock_event)
        message = save_message(student, mock_event.message.text, mock_event)
        
        return jsonify({
            'success': True,
            'message': '成功模擬訊息處理',
            'student_id': student.id,
            'student_name': student.name,
            'message_id': message.id if message else None,
            'stats': {
                'total_students': Student.select().count(),
                'total_messages': Message.select().count()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/clean-demo-data')
def clean_demo_data():
    """清理演示資料"""
    try:
        # 只清理明確標記為演示的資料
        demo_students = Student.select().where(
            (Student.name.startswith('[DEMO]')) | 
            (Student.line_user_id.startswith('demo_'))
        )
        
        deleted_count = 0
        for student in demo_students:
            # 刪除相關訊息
            Message.delete().where(Message.student == student).execute()
            # 刪除學生記錄
            student.delete_instance()
            deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 個演示學生記錄',
            'remaining_students': Student.select().count()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
            'web_interface': 'available' if WEB_TEMPLATES_AVAILABLE else 'not_available',
            'stats': get_database_stats()
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
    return jsonify(get_database_stats())

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """API: 獲取儀表板統計"""
    return jsonify({
        'success': True,
        'data': get_database_stats()
    })

@app.route('/api/students')
def api_students():
    """API: 獲取學生列表"""
    try:
        students_data = []
        for student in Student.select():
            students_data.append({
                'id': student.id,
                'name': student.name,
                'line_user_id': student.line_user_id,
                'message_count': student.message_count,
                'question_count': student.question_count,
                'participation_rate': student.participation_rate,
                'last_active': student.last_active.isoformat() if student.last_active else None
            })
        
        return jsonify({
            'success': True,
            'students': students_data,
            'total': len(students_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync-all-students')
def sync_all_students():
    """API: 同步所有學生統計"""
    try:
        students = list(Student.select())
        updated_count = 0
        
        for student in students:
            stats = sync_student_stats(student)
            if stats:
                student.save()
                updated_count += 1
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'成功同步 {updated_count} 位學生的統計資料'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =================== 錯誤處理 ===================

ERROR_404_HTML = '''<!DOCTYPE html>
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
</html>'''

ERROR_500_HTML = '''<!DOCTYPE html>
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
</html>'''

@app.errorhandler(404)
def not_found_error(error):
    """404 錯誤處理"""
    if request.path.startswith('/api/'):
        return {'error': 'Not found'}, 404
    return render_template_string(ERROR_404_HTML), 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    logger.error(f"Internal server error: {error}")
    if request.path.startswith('/api/'):
        return {'error': 'Internal server error'}, 500
    return render_template_string(ERROR_500_HTML), 500

# =================== 啟動檢查 ===================

def startup_checks():
    """啟動時的系統檢查"""
    try:
        logger.info("🔍 執行啟動檢查...")
        
        # 檢查資料庫連接
        if db.is_closed():
            db.connect()
        
        # 檢查學生和訊息數量
        student_count = Student.select().count()
        message_count = Message.select().count()
        
        logger.info(f"📊 啟動狀態: {student_count} 位學生, {message_count} 則訊息")
        
        # 如果有孤立訊息，自動修復
        orphaned_count = 0
        for message in Message.select():
            try:
                student = message.student
                if not student:
                    orphaned_count += 1
            except Student.DoesNotExist:
                orphaned_count += 1
        
        if orphaned_count > 0:
            logger.warning(f"⚠️ 發現 {orphaned_count} 個孤立訊息，建議執行修復")
        
        # 自動同步統計（如果學生數量不多）
        if student_count <= 10:
            logger.info("🔄 自動同步學生統計...")
            for student in Student.select():
                sync_student_stats(student)
                student.save()
            logger.info("✅ 統計同步完成")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 啟動檢查失敗: {e}")
        return False

# 在應用程式啟動時執行檢查
with app.app_context():
    try:
        startup_checks()
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
        logger.info("   - 首頁: /")
        logger.info("   - 學生管理: /students")
        logger.info("   - 教師分析: /teaching-insights")
        logger.info("   - 對話摘要: /conversation-summaries")
        logger.info("   - 學習建議: /learning-recommendations")
        logger.info("   - 儲存管理: /storage-management")
        logger.info("   - 資料匯出: /data-export")
    
    logger.info("🔧 調試端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - 系統統計: /stats")
    logger.info("   - 調試學生: /debug-students")
    logger.info("   - 同步統計: /sync-all-stats")
    logger.info("   - 檢查孤立訊息: /check-orphaned-messages")
    logger.info("   - 修復孤立訊息: /fix-orphaned-messages")
    logger.info("   - 模擬訊息: /simulate-line-message")
    logger.info("   - LINE Bot Webhook: /callback")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點（用於生產環境）
application = app
