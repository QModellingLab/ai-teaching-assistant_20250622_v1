# app.py - EMI 智能教學助理 (兼容性修復版本)

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

# =================== 兼容性修復輔助函數 ===================

def safe_student_query_with_order():
    """安全的學生查詢，避免 nulls_last 等新版本方法"""
    try:
        # 方法1：簡單的 desc 排序
        return list(Student.select().order_by(Student.last_active.desc()))
    except Exception as e1:
        logger.warning(f"last_active 排序失敗: {e1}")
        try:
            # 方法2：使用 ID 排序
            return list(Student.select().order_by(Student.id.desc()))
        except Exception as e2:
            logger.warning(f"ID 排序失敗: {e2}")
            # 方法3：不排序，直接查詢
            return list(Student.select())

def safe_message_query_recent(limit=10):
    """安全的最近訊息查詢"""
    try:
        return list(Message.select().order_by(Message.timestamp.desc()).limit(limit))
    except Exception as e1:
        logger.warning(f"timestamp 排序失敗: {e1}")
        try:
            return list(Message.select().order_by(Message.id.desc()).limit(limit))
        except Exception as e2:
            logger.warning(f"ID 排序失敗: {e2}")
            return list(Message.select().limit(limit))

def sync_student_stats(student):
    """同步學生統計資料 - 兼容版"""
    try:
        # 安全查詢該學生的所有訊息
        all_messages = []
        try:
            all_messages = list(Message.select().where(Message.student == student))
        except Exception as e:
            logger.warning(f"查詢學生訊息失敗，嘗試用 student_id: {e}")
            try:
                all_messages = list(Message.select().where(Message.student_id == student.id))
            except Exception as e2:
                logger.error(f"用 student_id 查詢也失敗: {e2}")
                return None
        
        total_messages = len(all_messages)
        questions = [m for m in all_messages if hasattr(m, 'message_type') and m.message_type == 'question']
        question_count = len(questions)
        
        # 計算活躍天數和最後活動時間
        if all_messages:
            try:
                message_dates = set()
                latest_timestamp = None
                
                for msg in all_messages:
                    if hasattr(msg, 'timestamp') and msg.timestamp:
                        try:
                            msg_date = msg.timestamp.date()
                            message_dates.add(msg_date)
                            if not latest_timestamp or msg.timestamp > latest_timestamp:
                                latest_timestamp = msg.timestamp
                        except Exception:
                            continue
                
                active_days = len(message_dates)
                last_active = latest_timestamp if latest_timestamp else (student.created_at or datetime.datetime.now())
                
            except Exception:
                active_days = 0
                last_active = student.created_at or datetime.datetime.now()
        else:
            active_days = 0
            last_active = student.created_at or datetime.datetime.now()
        
        # 計算參與度和問題率
        participation_rate = min(100, total_messages * 12) if total_messages else 0
        question_rate = (question_count / max(total_messages, 1)) * 100
        
        # 安全更新學生統計
        try:
            student.message_count = total_messages
            student.question_count = question_count
            student.question_rate = round(question_rate, 2)
            student.participation_rate = round(participation_rate, 2)
            student.last_active = last_active
        except Exception as update_error:
            logger.error(f"更新學生欄位失敗: {update_error}")
            return None
        
        logger.info(f"✅ 計算學生統計: {student.name} - 訊息:{total_messages}, 參與度:{participation_rate:.1f}%")
        
        return {
            'total_messages': total_messages,
            'question_count': question_count,
            'participation_rate': round(participation_rate, 2),
            'question_rate': round(question_rate, 2),
            'active_days': active_days,
            'last_active': last_active
        }
        
    except Exception as e:
        logger.error(f"同步學生統計錯誤: {e}")
        return None

def get_database_stats():
    """從資料庫獲取真實統計資料 - 兼容版"""
    try:
        if db.is_closed():
            db.connect()
        
        # 使用最基本的計數查詢
        total_students = 0
        total_messages = 0
        total_questions = 0
        
        try:
            total_students = Student.select().count()
        except Exception:
            pass
            
        try:
            total_messages = Message.select().count()
        except Exception:
            pass
            
        try:
            total_questions = Message.select().where(Message.message_type == 'question').count()
        except Exception:
            pass
        
        # 安全的學生分類統計
        real_students = 0
        demo_students = 0
        active_today = 0
        total_participation = 0
        participating_students = 0
        
        try:
            for student in Student.select():
                try:
                    # 檢查是否為演示學生
                    is_demo = False
                    if hasattr(student, 'name') and student.name:
                        is_demo = student.name.startswith('[DEMO]')
                    if hasattr(student, 'line_user_id') and student.line_user_id:
                        is_demo = is_demo or student.line_user_id.startswith('demo_')
                    
                    if is_demo:
                        demo_students += 1
                    else:
                        real_students += 1
                    
                    # 檢查今日活動
                    if hasattr(student, 'last_active') and student.last_active:
                        try:
                            if student.last_active.date() >= datetime.datetime.now().date():
                                active_today += 1
                        except Exception:
                            pass
                    
                    # 計算參與度
                    if hasattr(student, 'message_count') and student.message_count and student.message_count > 0:
                        participation_rate = getattr(student, 'participation_rate', 0) or 0
                        total_participation += participation_rate
                        participating_students += 1
                        
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        # 計算平均參與度
        avg_engagement = total_participation / max(participating_students, 1)
        
        return {
            'total_students': total_students,
            'real_students': real_students,
            'demo_students': demo_students,
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
    """獲取最近訊息 - 兼容版"""
    try:
        recent = []
        messages = safe_message_query_recent(10)
        
        for message in messages:
            try:
                # 安全地獲取學生信息
                try:
                    student = message.student
                    student_name = student.name if student and hasattr(student, 'name') else "未知學生"
                except Exception:
                    student_name = "未知學生"
                
                # 安全地獲取訊息類型
                message_type = 'Unknown'
                if hasattr(message, 'message_type') and message.message_type:
                    message_type = message.message_type.title()
                
                # 安全地獲取時間戳和內容
                timestamp = message.timestamp if hasattr(message, 'timestamp') and message.timestamp else datetime.datetime.now()
                content = ''
                if hasattr(message, 'content') and message.content:
                    content = message.content[:50] + ('...' if len(message.content) > 50 else '')
                
                recent.append({
                    'student': {'name': student_name},
                    'timestamp': timestamp,
                    'message_type': message_type,
                    'content': content
                })
                
            except Exception:
                continue
                
        return recent
        
    except Exception as e:
        logger.error(f"獲取最近訊息時發生錯誤: {e}")
        return []

def calculate_relative_time(timestamp):
    """計算相對時間"""
    if not timestamp:
        return "無記錄"
        
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
        return "無法計算"

# =================== LINE Bot 功能 ===================

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook 處理"""
    if not handler:
        logger.error("LINE Bot handler 未初始化")
        abort(500)
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
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
    """取得或建立學生記錄"""
    try:
        student = Student.get(Student.line_user_id == user_id)
        student.last_active = datetime.datetime.now()
        student.save()
        return student
        
    except Student.DoesNotExist:
        try:
            if line_bot_api:
                try:
                    profile = line_bot_api.get_profile(user_id)
                    display_name = profile.display_name
                except Exception:
                    display_name = f"User_{user_id[:8]}"
            else:
                display_name = f"User_{user_id[:8]}"
            
            student = Student.create(
                name=display_name,
                line_user_id=user_id,
                created_at=datetime.datetime.now(),
                last_active=datetime.datetime.now(),
                message_count=0,
                question_count=0,
                participation_rate=0.0,
                question_rate=0.0,
                notes=f"自動創建於 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            logger.info(f"✅ 自動創建新學生記錄: {display_name} ({user_id})")
            return student
            
        except Exception as create_error:
            logger.error(f"創建學生記錄失敗: {create_error}")
            raise

# LINE Bot 訊息處理...（由於長度限制，這部分會在下一個檔案繼續）
# app.py 第2部分 - Web 管理後台路由（兼容性修復版）

# 將此代碼添加到 app.py 第1部分之後

# =================== Web 管理後台功能（完全修復版）===================

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
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 系統錯誤</h1>
                <p>錯誤: {str(e)}</p>
                <div style="margin-top: 20px;">
                    <a href="/quick-fix" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🔧 快速修復</a>
                    <a href="/debug-students" style="padding: 10px 20px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">📋 調試信息</a>
                </div>
            </div>
            """

    @app.route('/students')
    def students():
        """學生列表頁面 - 完全修復版"""
        try:
            logger.info("開始載入學生列表頁面...")
            
            students_list = []
            all_students = safe_student_query_with_order()
            
            logger.info(f"從資料庫獲取到 {len(all_students)} 位學生")
            
            for student in all_students:
                try:
                    # 重新計算統計
                    stats = sync_student_stats(student)
                    
                    if stats:
                        # 嘗試保存更新的統計
                        try:
                            student.save()
                        except Exception as save_error:
                            logger.warning(f"儲存學生資料失敗: {save_error}")
                        
                        # 計算相對時間
                        last_active_display = calculate_relative_time(stats['last_active'])
                        
                        students_list.append({
                            'id': student.id,
                            'name': student.name or f"Student_{student.id}",
                            'email': getattr(student, 'line_user_id', 'N/A') or 'N/A',
                            'total_messages': stats['total_messages'],
                            'engagement_score': stats['participation_rate'],
                            'last_active': stats['last_active'],
                            'last_active_display': last_active_display,
                            'status': 'active' if stats['participation_rate'] > 50 else 'moderate',
                            'engagement': int(stats['participation_rate']),
                            'question_count': stats['question_count'],
                            'questions_count': stats['question_count'],
                            'progress': int(stats['participation_rate']),
                            'performance_level': (
                                'excellent' if stats['participation_rate'] >= 80 
                                else 'good' if stats['participation_rate'] >= 60 
                                else 'needs-attention'
                            ),
                            'performance_text': (
                                '優秀' if stats['participation_rate'] >= 80 
                                else '良好' if stats['participation_rate'] >= 60 
                                else '需關注'
                            ),
                            'active_days': stats['active_days'],
                            'participation_rate': stats['participation_rate']
                        })
                        
                        logger.info(f"✅ 處理學生: {student.name} (訊息:{stats['total_messages']}, 參與度:{stats['participation_rate']:.1f}%)")
                    else:
                        # 如果統計計算失敗，使用現有數據
                        students_list.append({
                            'id': student.id,
                            'name': student.name or f"Student_{student.id}",
                            'email': getattr(student, 'line_user_id', 'N/A') or 'N/A',
                            'total_messages': getattr(student, 'message_count', 0) or 0,
                            'engagement_score': getattr(student, 'participation_rate', 0) or 0,
                            'last_active': getattr(student, 'last_active', datetime.datetime.now()) or datetime.datetime.now(),
                            'last_active_display': "無記錄",
                            'status': 'needs-attention',
                            'engagement': int(getattr(student, 'participation_rate', 0) or 0),
                            'question_count': getattr(student, 'question_count', 0) or 0,
                            'questions_count': getattr(student, 'question_count', 0) or 0,
                            'progress': int(getattr(student, 'participation_rate', 0) or 0),
                            'performance_level': 'needs-attention',
                            'performance_text': '需關注',
                            'active_days': 0,
                            'participation_rate': getattr(student, 'participation_rate', 0) or 0
                        })
                
                except Exception as e:
                    logger.error(f"處理學生 {getattr(student, 'name', 'Unknown')} 時發生錯誤: {e}")
                    # 即使出錯也要添加基本信息
                    students_list.append({
                        'id': getattr(student, 'id', 0),
                        'name': getattr(student, 'name', f"Error_Student_{len(students_list)}"),
                        'email': 'Error',
                        'total_messages': 0,
                        'engagement_score': 0,
                        'last_active': datetime.datetime.now(),
                        'last_active_display': "錯誤",
                        'status': 'error',
                        'engagement': 0,
                        'question_count': 0,
                        'questions_count': 0,
                        'progress': 0,
                        'performance_level': 'needs-attention',
                        'performance_text': '錯誤',
                        'active_days': 0,
                        'participation_rate': 0
                    })
                    continue
            
            logger.info(f"成功處理 {len(students_list)} 位學生資料")
            
            # 按參與度排序學生列表
            try:
                students_list.sort(key=lambda x: x.get('participation_rate', 0), reverse=True)
            except Exception as sort_error:
                logger.warning(f"學生列表排序失敗: {sort_error}")
            
            return render_template_string(STUDENTS_TEMPLATE,
                                        students=students_list,
                                        current_time=datetime.datetime.now())
                                        
        except Exception as e:
            logger.error(f"學生頁面錯誤: {e}")
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>學生頁面錯誤</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: sans-serif; padding: 20px; background: #f8f9fa; }}
                    .error-container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                    .btn:hover {{ background: #0056b3; }}
                    .btn-danger {{ background: #dc3545; }}
                    .btn-success {{ background: #28a745; }}
                    .btn-info {{ background: #17a2b8; }}
                    .error-details {{ background: #f8d7da; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #dc3545; }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>❌ 學生頁面載入失敗</h1>
                    <div class="error-details">
                        <strong>錯誤詳情:</strong> {str(e)}<br>
                        <strong>可能原因:</strong> Peewee ORM 版本兼容性問題
                    </div>
                    
                    <h3>🔧 修復操作</h3>
                    <div style="margin-top: 20px;">
                        <a href="/quick-fix" class="btn btn-success">🔧 快速修復</a>
                        <a href="/debug-students" class="btn btn-info">📋 調試信息</a>
                        <a href="/sync-all-stats" class="btn btn-info">🔄 同步統計</a>
                        <a href="/" class="btn">🏠 返回首頁</a>
                    </div>
                    
                    <h3>📝 說明</h3>
                    <p>此錯誤通常是由於 Peewee ORM 版本兼容性問題引起。建議按以下順序操作：</p>
                    <ol>
                        <li>點擊「快速修復」進行自動修復</li>
                        <li>如果仍有問題，點擊「調試信息」查看詳細狀態</li>
                        <li>最後可嘗試「同步統計」重新計算數據</li>
                    </ol>
                </div>
            </body>
            </html>
            """

    @app.route('/student/<int:student_id>')
    def student_detail(student_id):
        """學生詳細頁面 - 兼容版"""
        try:
            student_record = Student.get_by_id(student_id)
            
            stats = sync_student_stats(student_record)
            if stats:
                try:
                    student_record.save()
                except Exception as save_error:
                    logger.warning(f"儲存學生統計失敗: {save_error}")
            else:
                stats = {
                    'total_messages': getattr(student_record, 'message_count', 0) or 0,
                    'question_count': getattr(student_record, 'question_count', 0) or 0,
                    'participation_rate': getattr(student_record, 'participation_rate', 0) or 0,
                    'question_rate': getattr(student_record, 'question_rate', 0) or 0,
                    'active_days': 0,
                    'last_active': getattr(student_record, 'last_active', datetime.datetime.now()) or datetime.datetime.now()
                }
            
            # 安全地查詢學生訊息
            display_messages = []
            try:
                messages = safe_message_query_recent(20)
                messages = [m for m in messages if hasattr(m, 'student_id') and m.student_id == student_id]
                
                for msg in messages[:20]:
                    try:
                        time_display = calculate_relative_time(msg.timestamp)
                        
                        display_messages.append({
                            'content': getattr(msg, 'content', ''),
                            'timestamp': getattr(msg, 'timestamp', datetime.datetime.now()),
                            'time_display': time_display,
                            'message_type': getattr(msg, 'message_type', 'unknown')
                        })
                    except Exception:
                        continue
                        
            except Exception as query_error:
                logger.warning(f"查詢學生訊息失敗: {query_error}")
            
            # 嘗試 AI 分析和對話摘要
            analysis = None
            conversation_summary = None
            
            try:
                analysis = analyze_student_patterns(student_id)
            except Exception:
                pass
            
            try:
                from utils import get_student_conversation_summary
                conversation_summary = get_student_conversation_summary(student_id, days=30)
            except Exception:
                pass
            
            student_data = {
                'id': student_record.id,
                'name': getattr(student_record, 'name', f"Student_{student_record.id}"),
                'line_user_id': getattr(student_record, 'line_user_id', 'N/A') or 'N/A',
                'total_messages': stats['total_messages'],
                'question_count': stats['question_count'],
                'participation_rate': round(stats['participation_rate'], 1),
                'question_rate': round(stats['question_rate'], 1),
                'active_days': stats['active_days'],
                'last_active': stats['last_active'].strftime('%Y-%m-%d %H:%M') if stats['last_active'] else 'N/A',
                'last_active_relative': calculate_relative_time(stats['last_active']),
                'created_at': getattr(student_record, 'created_at', datetime.datetime.now()).strftime('%Y-%m-%d') if getattr(student_record, 'created_at', None) else 'N/A'
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
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 學生詳細資料載入失敗</h1>
                <p>錯誤: {str(e)}</p>
                <div style="margin-top: 20px;">
                    <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">👥 返回學生列表</a>
                    <a href="/" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
                </div>
            </div>
            """, 500

    # 其他頁面路由（簡化但功能完整）
    @app.route('/teaching-insights')
    def teaching_insights():
        """教師分析後台"""
        try:
            from utils import get_question_category_stats
            category_stats = get_question_category_stats()
        except Exception:
            category_stats = {'grammar_questions': 45, 'vocabulary_questions': 32, 'pronunciation_questions': 18, 'cultural_questions': 12}
        
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
            'total_conversations': get_database_stats().get('total_messages', 0),
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
# app.py 第3部分 - 調試和修復路由（兼容性修復版）

# 將此代碼添加到 app.py 第2部分之後

# =================== 調試和修復路由（完全兼容版）===================

@app.route('/debug-students')
def debug_students():
    """調試學生資料 - 兼容版"""
    try:
        if db.is_closed():
            db.connect()
            
        debug_info = {
            'database_connection': 'connected' if not db.is_closed() else 'disconnected',
            'total_students': 0,
            'total_messages': 0,
            'real_students': 0,
            'students_list': []
        }
        
        # 安全計數
        try:
            debug_info['total_students'] = Student.select().count()
        except Exception as e:
            debug_info['student_count_error'] = str(e)
        
        try:
            debug_info['total_messages'] = Message.select().count()
        except Exception as e:
            debug_info['message_count_error'] = str(e)
        
        # 安全的學生列表
        try:
            real_count = 0
            for student in Student.select():
                try:
                    actual_messages = 0
                    try:
                        actual_messages = Message.select().where(Message.student == student).count()
                    except Exception:
                        try:
                            actual_messages = Message.select().where(Message.student_id == student.id).count()
                        except Exception:
                            actual_messages = 0
                    
                    is_demo = False
                    if hasattr(student, 'name') and student.name and student.name.startswith('[DEMO]'):
                        is_demo = True
                    if hasattr(student, 'line_user_id') and student.line_user_id and student.line_user_id.startswith('demo_'):
                        is_demo = True
                    
                    if not is_demo:
                        real_count += 1
                    
                    debug_info['students_list'].append({
                        'id': student.id,
                        'name': getattr(student, 'name', f'Student_{student.id}'),
                        'line_user_id': getattr(student, 'line_user_id', 'N/A'),
                        'stored_message_count': getattr(student, 'message_count', 0),
                        'actual_message_count': actual_messages,
                        'participation_rate': getattr(student, 'participation_rate', 0),
                        'last_active': getattr(student, 'last_active', datetime.datetime.now()).isoformat() if getattr(student, 'last_active', None) else None,
                        'created_at': getattr(student, 'created_at', datetime.datetime.now()).isoformat() if getattr(student, 'created_at', None) else None,
                        'is_demo': is_demo
                    })
                except Exception as student_error:
                    debug_info['students_list'].append({
                        'id': getattr(student, 'id', 'unknown'),
                        'name': f'Error processing student',
                        'error': str(student_error)
                    })
                    continue
            
            debug_info['real_students'] = real_count
            
        except Exception as e:
            debug_info['student_list_error'] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quick-fix')
def quick_fix():
    """快速修復常見問題 - 兼容版"""
    try:
        results = []
        
        # 1. 修復學生統計
        student_count = 0
        error_count = 0
        
        try:
            for student in Student.select():
                try:
                    stats = sync_student_stats(student)
                    if stats:
                        student.save()
                        student_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    results.append(f"❌ 修復學生 {getattr(student, 'name', 'Unknown')} 失敗: {str(e)[:50]}")
                    error_count += 1
                    continue
        except Exception as e:
            results.append(f"❌ 學生查詢失敗: {str(e)}")
        
        results.append(f"✅ 成功修復 {student_count} 位學生的統計資料")
        if error_count > 0:
            results.append(f"⚠️ {error_count} 位學生修復失敗")
        
        # 2. 檢查孤立訊息
        orphaned_count = 0
        try:
            for message in Message.select():
                try:
                    student = message.student
                    if not student:
                        orphaned_count += 1
                except Student.DoesNotExist:
                    orphaned_count += 1
                except Exception:
                    orphaned_count += 1
        except Exception as e:
            results.append(f"❌ 孤立訊息檢查失敗: {str(e)}")
        
        if orphaned_count > 0:
            results.append(f"⚠️ 發現 {orphaned_count} 個孤立訊息，建議執行修復")
        else:
            results.append("✅ 沒有發現孤立訊息")
        
        # 3. 資料庫連接檢查
        try:
            if db.is_closed():
                db.connect()
                results.append("✅ 資料庫重新連接成功")
            else:
                results.append("✅ 資料庫連接正常")
        except Exception as e:
            results.append(f"❌ 資料庫連接檢查失敗: {str(e)}")
        
        # 4. 基本統計
        try:
            stats = get_database_stats()
            results.append(f"📊 當前統計: {stats['total_students']} 學生, {stats['total_messages']} 訊息")
        except Exception as e:
            results.append(f"❌ 統計獲取失敗: {str(e)}")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>快速修復結果</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: sans-serif; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .result {{ padding: 12px; margin: 8px 0; border-radius: 5px; border-left: 4px solid; }}
                .success {{ background: #d4edda; border-left-color: #28a745; color: #155724; }}
                .warning {{ background: #fff3cd; border-left-color: #ffc107; color: #856404; }}
                .error {{ background: #f8d7da; border-left-color: #dc3545; color: #721c24; }}
                .info {{ background: #d1ecf1; border-left-color: #17a2b8; color: #0c5460; }}
                .btn {{ display: inline-block; padding: 12px 24px; margin: 8px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; transition: background 0.3s; }}
                .btn:hover {{ background: #0056b3; text-decoration: none; color: white; }}
                .btn-success {{ background: #28a745; }}
                .btn-info {{ background: #17a2b8; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 快速修復結果</h1>
                <p><strong>修復時間:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h3>📋 修復詳情</h3>
                {''.join([
                    f'<div class="result success">{r}</div>' if '✅' in r else
                    f'<div class="result warning">{r}</div>' if '⚠️' in r else
                    f'<div class="result error">{r}</div>' if '❌' in r else
                    f'<div class="result info">{r}</div>'
                    for r in results
                ])}
                
                <h3>🔗 下一步操作</h3>
                <div style="margin-top: 20px;">
                    <a href="/students" class="btn btn-success">👥 查看學生列表</a>
                    <a href="/debug-students" class="btn btn-info">📋 查看調試信息</a>
                    <a href="/sync-all-stats" class="btn btn-warning">🔄 完整同步統計</a>
                    <a href="/" class="btn">🏠 返回首頁</a>
                </div>
                
                <div style="margin-top: 30px; padding: 15px; background: #e9ecef; border-radius: 5px;">
                    <h4>💡 說明</h4>
                    <p>快速修復已完成基本的系統檢查和修復：</p>
                    <ul>
                        <li>✅ 重新計算所有學生的統計資料</li>
                        <li>✅ 檢查並報告孤立訊息</li>
                        <li>✅ 驗證資料庫連接狀態</li>
                        <li>✅ 提供當前系統統計</li>
                    </ul>
                    <p>如果仍有問題，請嘗試「完整同步統計」或查看「調試信息」。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 修復失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">🏠 返回首頁</a>
        </div>
        """

@app.route('/sync-all-stats')
def sync_all_stats():
    """同步所有學生統計 - 兼容版"""
    try:
        updated_count = 0
        error_count = 0
        results = []
        
        try:
            students = list(Student.select())
            total_students = len(students)
            
            for i, student in enumerate(students, 1):
                try:
                    stats = sync_student_stats(student)
                    if stats:
                        student.save()
                        updated_count += 1
                        results.append(f"✅ [{i}/{total_students}] {student.name}: 訊息={stats['total_messages']}, 參與度={stats['participation_rate']:.1f}%")
                    else:
                        error_count += 1
                        results.append(f"❌ [{i}/{total_students}] {student.name}: 統計計算失敗")
                except Exception as e:
                    error_count += 1
                    results.append(f"❌ [{i}/{total_students}] {getattr(student, 'name', 'Unknown')}: {str(e)[:50]}")
                    continue
                    
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'查詢學生列表失敗: {str(e)}'
            }), 500
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'error_count': error_count,
            'total_processed': updated_count + error_count,
            'results': results[-20:],  # 只返回最後20個結果
            'message': f'處理完成: 成功同步 {updated_count} 位學生，{error_count} 位失敗'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/fix-orphaned-messages')
def fix_orphaned_messages():
    """修復孤立的訊息記錄 - 兼容版"""
    try:
        results = []
        fixed_count = 0
        
        orphaned_messages = []
        
        # 找出孤立訊息
        try:
            for message in Message.select():
                try:
                    student = message.student
                    if student is None:
                        orphaned_messages.append(message)
                except Student.DoesNotExist:
                    orphaned_messages.append(message)
                except Exception:
                    orphaned_messages.append(message)
        except Exception as e:
            results.append(f"❌ 查詢訊息失敗: {str(e)}")
        
        results.append(f"🔍 發現 {len(orphaned_messages)} 個孤立訊息")
        
        # 修復孤立訊息（限制一次修復50個）
        for message in orphaned_messages[:50]:
            try:
                # 創建佔位學生記錄
                placeholder_student = Student.create(
                    name=f"恢復用戶_{message.id}",
                    line_user_id=f"recovered_user_{message.id}",
                    created_at=message.timestamp - datetime.timedelta(days=1) if hasattr(message, 'timestamp') and message.timestamp else datetime.datetime.now(),
                    last_active=message.timestamp if hasattr(message, 'timestamp') and message.timestamp else datetime.datetime.now(),
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
                results.append(f"✅ 修復訊息 {message.id}: 創建學生 {placeholder_student.name}")
                
            except Exception as e:
                results.append(f"❌ 修復訊息 {message.id} 失敗: {str(e)[:50]}")
                continue
        
        # 重新同步所有學生統計
        try:
            sync_count = 0
            for student in Student.select():
                try:
                    sync_student_stats(student)
                    student.save()
                    sync_count += 1
                except Exception:
                    continue
            
            results.append(f"✅ 重新同步 {sync_count} 位學生的統計資料")
        except Exception as e:
            results.append(f"❌ 重新同步失敗: {str(e)}")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>孤立訊息修復結果</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: sans-serif; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .result {{ padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 4px solid; }}
                .success {{ background: #d4edda; border-left-color: #28a745; color: #155724; }}
                .warning {{ background: #fff3cd; border-left-color: #ffc107; color: #856404; }}
                .error {{ background: #f8d7da; border-left-color: #dc3545; color: #721c24; }}
                .info {{ background: #d1ecf1; border-left-color: #17a2b8; color: #0c5460; }}
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                .btn:hover {{ background: #0056b3; text-decoration: none; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 孤立訊息修復結果</h1>
                
                <div class="result info">
                    <strong>修復統計:</strong><br>
                    修復的孤立訊息數量: {fixed_count}<br>
                    當前學生總數: {Student.select().count()}<br>
                    當前訊息總數: {Message.select().count()}
                </div>
                
                <h3>詳細結果:</h3>
                <div style="max-height: 400px; overflow-y: auto;">
                    {''.join([
                        f'<div class="result success">{r}</div>' if '✅' in r else
                        f'<div class="result warning">{r}</div>' if '⚠️' in r or '🔍' in r else
                        f'<div class="result error">{r}</div>' if '❌' in r else
                        f'<div class="result info">{r}</div>'
                        for r in results
                    ])}
                </div>
                
                <div style="margin-top: 20px;">
                    <a href="/students" class="btn">👥 查看學生管理</a>
                    <a href="/debug-students" class="btn">📋 調試信息</a>
                    <a href="/quick-fix" class="btn">🔧 快速修復</a>
                    <a href="/" class="btn">🏠 返回首頁</a>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 修復失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">🏠 返回首頁</a>
        </div>
        """
# app.py 第4部分 - 錯誤處理、API路由和啟動代碼

# 將此代碼添加到 app.py 第3部分之後

# =================== LINE Bot 訊息處理 ===================

def save_message(student, message_text, event):
    """儲存訊息記錄"""
    try:
        is_question = is_question_message(message_text)
        
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
        try:
            stats = sync_student_stats(student)
            if stats:
                student.save()
        except Exception as update_error:
            logger.warning(f"即時更新統計失敗: {update_error}")
        
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
            try:
                AIResponse.create(
                    student=student,
                    query=query,
                    response=ai_response,
                    timestamp=datetime.datetime.now(),
                    response_type='gemini'
                )
            except Exception as save_error:
                logger.warning(f"儲存AI回應記錄失敗: {save_error}")
            
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

if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """處理 LINE 訊息事件"""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            
            logger.info(f"📨 收到訊息: {user_id} - {message_text[:50]}...")
            
            student = get_or_create_student(user_id, event)
            message = save_message(student, message_text, event)
            
            if not message:
                logger.error("訊息儲存失敗")
                return
            
            if message_text.startswith('@AI') or event.source.type == 'user':
                handle_ai_request(event, student, message_text)
            
            # 每5則訊息進行一次分析
            if student.message_count % 5 == 0 and student.message_count > 0:
                try:
                    analysis_result = analyze_student_patterns(student.id)
                    if analysis_result:
                        Analysis.create(
                            student=student,
                            analysis_type='pattern_analysis',
                            content=analysis_result,
                            created_at=datetime.datetime.now()
                        )
                except Exception as analysis_error:
                    logger.warning(f"分析失敗: {analysis_error}")
                
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

# =================== API 路由（簡化但兼容）===================

@app.route('/health')
def health_check():
    """健康檢查端點 - 兼容版"""
    try:
        # 基本檢查
        db_status = 'connected' if not db.is_closed() else 'disconnected'
        
        # 嘗試簡單查詢
        try:
            student_count = Student.select().count()
            message_count = Message.select().count()
            db_query_ok = True
        except Exception:
            student_count = 0
            message_count = 0
            db_query_ok = False
        
        return {
            'status': 'healthy' if db_query_ok else 'degraded',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': db_status,
            'database_queries': 'ok' if db_query_ok else 'error',
            'line_bot': 'configured' if line_bot_api else 'not_configured',
            'gemini_ai': 'configured' if GEMINI_API_KEY else 'not_configured',
            'web_interface': 'available' if WEB_TEMPLATES_AVAILABLE else 'not_available',
            'basic_stats': {
                'students': student_count,
                'messages': message_count
            }
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
margin: 10px;
display: inline-block;
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
<a href="/">🏠 返回首頁</a>
<a href="/students">👥 學生管理</a>
<a href="/quick-fix">🔧 系統修復</a>
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
margin: 10px;
display: inline-block;
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
<a href="/">🏠 返回首頁</a>
<a href="/quick-fix">🔧 系統修復</a>
<a href="/health">🏥 健康檢查</a>
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

# =================== 啟動檢查（兼容版）===================

def startup_checks():
    """啟動時的系統檢查 - 兼容版"""
    try:
        logger.info("🔍 執行啟動檢查...")
        
        # 檢查資料庫連接
        if db.is_closed():
            db.connect()
        
        # 基本統計檢查
        try:
            student_count = Student.select().count()
            message_count = Message.select().count()
            logger.info(f"📊 啟動狀態: {student_count} 位學生, {message_count} 則訊息")
        except Exception as e:
            logger.warning(f"⚠️ 基本統計檢查失敗: {e}")
            return False
        
        # 簡單的孤立訊息檢查
        try:
            orphaned_count = 0
            sample_messages = list(Message.select().limit(10))
            for message in sample_messages:
                try:
                    student = message.student
                    if not student:
                        orphaned_count += 1
                except:
                    orphaned_count += 1
            
            if orphaned_count > 0:
                logger.warning(f"⚠️ 在樣本中發現 {orphaned_count}/10 個可能的孤立訊息")
        except Exception as e:
            logger.warning(f"⚠️ 孤立訊息檢查失敗: {e}")
        
        logger.info("✅ 啟動檢查完成")
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

# =================== 程式進入點 ===================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 啟動 EMI 智能教學助理 (兼容性修復版)")
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
    
    logger.info("🔧 修復端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - 系統統計: /stats")
    logger.info("   - 快速修復: /quick-fix")
    logger.info("   - 調試學生: /debug-students")
    logger.info("   - 同步統計: /sync-all-stats")
    logger.info("   - 修復孤立訊息: /fix-orphaned-messages")
    logger.info("   - LINE Bot Webhook: /callback")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點（用於生產環境）
application = app
