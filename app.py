# app.py - 更新版本（整合改進的真實資料分析系統）

import os
import json
import datetime
import logging
import random
import csv
import zipfile
from io import StringIO, BytesIO
from flask import Flask, request, abort, render_template_string, jsonify, redirect, send_file
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

# 導入改進的 REAL DATA 分析模組（優先使用）
try:
    from improved_real_analytics import (
        get_improved_teaching_insights,
        get_improved_conversation_summaries,
        get_improved_storage_management,
        get_improved_student_recommendations,
        has_real_student_data,
        improved_analytics
    )
    IMPROVED_ANALYTICS_AVAILABLE = True
    logging.info("✅ 改進的真實資料分析模組已載入")
except ImportError as e:
    IMPROVED_ANALYTICS_AVAILABLE = False
    logging.error(f"❌ 改進分析模組載入失敗: {e}")
    
    # 回退到原有的分析模組
    try:
        from fixed_analytics import (
            get_real_teaching_insights,
            get_real_conversation_summaries,
            get_real_storage_management,
            get_real_student_recommendations,
            real_analytics
        )
        REAL_ANALYTICS_AVAILABLE = True
        logging.info("✅ 回退到原有真實資料分析模組")
    except ImportError as e:
        REAL_ANALYTICS_AVAILABLE = False
        logging.error(f"❌ 所有分析模組載入失敗: {e}")

# 導入 Web 管理後台模板
try:
    from templates_main import INDEX_TEMPLATE, STUDENTS_TEMPLATE, STUDENT_DETAIL_TEMPLATE
    from templates_analysis_part1 import TEACHING_INSIGHTS_TEMPLATE
    from templates_analysis_part2 import CONVERSATION_SUMMARIES_TEMPLATE
    from templates_analysis_part3 import LEARNING_RECOMMENDATIONS_TEMPLATE
    from templates_management import STORAGE_MANAGEMENT_TEMPLATE
    from templates_utils import EMPTY_STATE_TEMPLATE
    WEB_TEMPLATES_AVAILABLE = True
    logging.info("✅ Web 管理模板已載入（包含空狀態模板）")
except ImportError as e:
    WEB_TEMPLATES_AVAILABLE = False
    logging.warning(f"⚠️ Web 管理模板載入失敗: {e}")

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
    logger.info("✅ LINE Bot API 初始化成功")
else:
    line_bot_api = None
    handler = None
    logger.warning("⚠️ LINE Bot API 未配置")

# 資料庫初始化
initialize_db()

# =================== 主要路由 ===================

@app.route('/')
def index():
    """首頁 - 支援等待狀態"""
    try:
        # 檢查是否有真實學生資料
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_real_data = has_real_student_data()
            if not has_real_data:
                # 顯示等待狀態
                return render_template_string(
                    INDEX_TEMPLATE,
                    data_status='WAITING_FOR_DATA',
                    waiting_message='等待學生開始使用 LINE Bot 進行對話',
                    stats={
                        'real_students': 0,
                        'total_students': Student.select().count(),
                        'total_messages': 0,
                        'avg_participation': 0
                    },
                    recent_messages=[]
                )
            else:
                # 顯示真實資料分析
                real_data = get_improved_teaching_insights()
                return render_template_string(
                    INDEX_TEMPLATE,
                    data_status='HAS_DATA',
                    stats=real_data['stats'],
                    recent_messages=real_data.get('recent_messages', []),
                    real_data_info=real_data
                )
        else:
            # 無分析模組時的基本顯示
            return render_template_string(
                INDEX_TEMPLATE,
                data_status='WAITING_FOR_DATA',
                stats={},
                recent_messages=[]
            )
    except Exception as e:
        app.logger.error(f"首頁錯誤: {e}")
        return render_template_string(
            INDEX_TEMPLATE,
            data_status='ERROR',
            stats={},
            recent_messages=[],
            error_message=str(e)
        )

@app.route('/teaching-insights')
def teaching_insights():
    """教師分析後台 - 支援等待狀態"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            # 檢查是否有真實資料
            has_real_data = has_real_student_data()
            
            if not has_real_data:
                # 顯示等待狀態的分析後台
                return render_template_string(
                    EMPTY_STATE_TEMPLATE,
                    page_title="教師分析後台",
                    main_message="等待學生開始對話",
                    sub_message="系統已準備就緒，等待學生使用 LINE Bot 開始學習對話",
                    setup_instructions=[
                        "確保 LINE Bot 已正確設定並可接收訊息",
                        "將 Bot 連結分享給學生或在課堂上展示 QR Code",
                        "鼓勵學生開始提問或進行英語對話練習",
                        "學生開始對話後，真實的教學分析將自動顯示"
                    ],
                    redirect_actions=[
                        {"text": "檢查系統狀態", "url": "/health", "icon": "🔧"},
                        {"text": "查看儲存管理", "url": "/storage-management", "icon": "💾"},
                        {"text": "學生管理頁面", "url": "/students", "icon": "👥"}
                    ],
                    tips=[
                        "💡 學生每發送一則訊息，系統就會即時進行 AI 分析",
                        "📊 困難點和興趣主題會自動識別並更新",
                        "🔄 頁面會自動檢測到新資料並提示重新整理"
                    ]
                )
            else:
                # 顯示真實資料分析
                real_data = get_improved_teaching_insights()
                return render_template_string(
                    TEACHING_INSIGHTS_TEMPLATE,
                    category_stats=real_data['category_stats'],
                    engagement_analysis=real_data['engagement_analysis'],
                    students=real_data['students'],
                    stats=real_data['stats'],
                    real_data_info=real_data,
                    current_time=datetime.datetime.now()
                )
        else:
            # 分析模組不可用
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 分析模組未載入</h1>
                <p>請檢查 improved_real_analytics.py 或 fixed_analytics.py 是否存在</p>
                <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
            </div>
            """
            
    except Exception as e:
        logger.error(f"Teaching insights error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 教師分析後台載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <div style="background: #f8d7da; padding: 15px; margin: 20px 0; border-radius: 5px;">
                <strong>可能原因：</strong>
                <ul style="text-align: left; max-width: 500px; margin: 0 auto;">
                    <li>資料庫連接問題</li>
                    <li>分析模組載入失敗</li>
                    <li>查詢權限不足</li>
                </ul>
            </div>
            <div style="margin-top: 20px;">
                <a href="/health" style="padding: 10px 20px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏥 系統健康檢查</a>
                <a href="/" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
            </div>
        </div>
        """, 500

@app.route('/conversation-summaries')
def conversation_summaries():
    """對話摘要頁面 - 支援等待狀態"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_real_data = has_real_student_data()
            
            if not has_real_data:
                # 顯示等待狀態
                return render_template_string(
                    EMPTY_STATE_TEMPLATE,
                    page_title="智能對話摘要",
                    main_message="等待對話資料",
                    sub_message="需要學生開始與 LINE Bot 對話後才能生成智能摘要",
                    setup_instructions=[
                        "學生需要與 LINE Bot 進行至少 3-5 輪對話",
                        "AI 會自動分析對話內容並提取教學重點",
                        "摘要會根據學習困難點和興趣主題分類",
                        "每次新對話都會更新和優化摘要內容"
                    ],
                    redirect_actions=[
                        {"text": "返回分析後台", "url": "/teaching-insights", "icon": "📊"},
                        {"text": "檢查系統狀態", "url": "/health", "icon": "🔧"}
                    ]
                )
            else:
                # 顯示真實對話摘要
                real_data = get_improved_conversation_summaries()
                return render_template_string(
                    CONVERSATION_SUMMARIES_TEMPLATE,
                    summaries=real_data['summaries'],
                    insights=real_data['insights'],
                    real_data_message=real_data.get('message', ''),
                    current_time=datetime.datetime.now()
                )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 分析模組未載入</h1>
                <p>對話摘要需要分析模組支援</p>
                <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
            </div>
            """
            
    except Exception as e:
        logger.error(f"Conversation summaries error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 對話摘要載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
        </div>
        """, 500

@app.route('/learning-recommendations')
def learning_recommendations():
    """學習建議頁面 - 支援等待狀態"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_real_data = has_real_student_data()
            
            if not has_real_data:
                # 顯示等待狀態
                return render_template_string(
                    EMPTY_STATE_TEMPLATE,
                    page_title="個人化學習建議",
                    main_message="等待學習資料",
                    sub_message="需要收集學生學習資料後才能生成個人化建議",
                    setup_instructions=[
                        "系統需要分析學生的提問模式和學習行為",
                        "基於真實對話內容識別個別學習需求",
                        "AI 會為每位學生量身定制學習建議",
                        "建議會根據學習進度動態調整和更新"
                    ],
                    redirect_actions=[
                        {"text": "返回分析後台", "url": "/teaching-insights", "icon": "📊"},
                        {"text": "學生管理", "url": "/students", "icon": "👥"}
                    ]
                )
            else:
                # 顯示真實學習建議
                real_data = get_improved_student_recommendations()
                return render_template_string(
                    LEARNING_RECOMMENDATIONS_TEMPLATE,
                    recommendations=real_data['recommendations'],
                    overview=real_data['overview'],
                    real_data_message=real_data.get('message', ''),
                    current_time=datetime.datetime.now()
                )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 分析模組未載入</h1>
                <p>學習建議需要分析模組支援</p>
                <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
            </div>
            """
            
    except Exception as e:
        logger.error(f"Learning recommendations error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 學習建議載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
        </div>
        """, 500

@app.route('/students')
def students():
    """學生列表頁面"""
    try:
        students = list(Student.select().order_by(Student.last_active.desc()))
        return render_template_string(STUDENTS_TEMPLATE, students=students)
    except Exception as e:
        app.logger.error(f"學生列表錯誤: {e}")
        return render_template_string(STUDENTS_TEMPLATE, students=[])

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細頁面"""
    try:
        student = Student.get_by_id(student_id)
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(20))
        
        analysis = analyze_student_patterns(student_id)
        
        return render_template_string(
            STUDENT_DETAIL_TEMPLATE,
            student=student,
            messages=messages,
            analysis=analysis
        )
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

@app.route('/storage-management')
def storage_management():
    """儲存管理頁面"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            real_storage_info = get_improved_storage_management()
        elif REAL_ANALYTICS_AVAILABLE:
            real_storage_info = get_real_storage_management()
        else:
            real_storage_info = {
                'total_size_mb': 0,
                'usage_percentage': 0,
                'record_counts': {'students': 0, 'messages': 0, 'analyses': 0, 'real_students': 0}
            }
            
        return render_template_string(
            STORAGE_MANAGEMENT_TEMPLATE,
            storage_stats=real_storage_info,
            real_data_info=real_storage_info
        )
    except Exception as e:
        logger.error(f"Storage management error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 儲存管理載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
        </div>
        """, 500

# =================== API 路由 ===================

@app.route('/api/real-data-status')
def real_data_status_api():
    """真實資料狀態檢查 API"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_data = has_real_student_data()
            real_student_count = Student.select().where(~Student.name.startswith('[DEMO]')).count()
            total_messages = Message.select().count()
            
            return jsonify({
                'has_real_data': has_data,
                'real_student_count': real_student_count,
                'total_messages': total_messages,
                'status': 'ready' if has_data else 'waiting',
                'message': '有真實學生資料' if has_data else '等待學生開始對話',
                'last_check': datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                'has_real_data': False,
                'error': 'Analytics module not available',
                'status': 'error'
            }), 503
    except Exception as e:
        return jsonify({
            'has_real_data': False,
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/student-analysis/<int:student_id>')
def student_analysis_api(student_id):
    """學生分析 API"""
    try:
        analysis = analyze_student_patterns(student_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard-stats')
def dashboard_stats_api():
    """儀表板統計 API"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_data = has_real_student_data()
            if has_data:
                real_data = get_improved_teaching_insights()
                return jsonify({
                    'success': True,
                    'has_real_data': True,
                    'stats': real_data['stats'],
                    'last_updated': datetime.datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': True,
                    'has_real_data': False,
                    'message': 'Waiting for real student data',
                    'stats': {
                        'real_students': 0,
                        'total_students': Student.select().count(),
                        'total_messages': 0,
                        'avg_participation': 0
                    }
                })
        else:
            return jsonify({'error': 'Analytics not available'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/class-statistics')
def class_statistics_api():
    """班級統計 API"""
    try:
        stats = {
            'total_students': Student.select().count(),
            'real_students': Student.select().where(~Student.name.startswith('[DEMO]')).count(),
            'total_messages': Message.select().count(),
            'active_students_today': Student.select().where(
                Student.last_active >= datetime.datetime.now().date()
            ).count(),
            'avg_messages_per_student': 0,
            'common_question_types': ['文法', '詞彙', '發音']
        }
        
        if stats['total_students'] > 0:
            stats['avg_messages_per_student'] = stats['total_messages'] / stats['total_students']
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================== 匯出相關 API 路由 ===================

@app.route('/api/export/<export_type>')
def export_data_api(export_type):
    """資料匯出 API"""
    try:
        export_format = request.args.get('format', 'json')
        date_range = request.args.get('date_range', None)
        export_content = request.args.get('content', 'all')
        
        # 解析日期範圍
        parsed_date_range = None
        if date_range:
            try:
                start_date, end_date = date_range.split(',')
                parsed_date_range = (start_date.strip(), end_date.strip())
            except:
                parsed_date_range = None
        
        # 根據匯出類型執行不同的匯出邏輯
        if export_type == 'conversations':
            result = export_conversation_data(export_format, parsed_date_range, export_content)
        elif export_type == 'analysis':
            result = export_analysis_data(export_format, parsed_date_range, export_content)
        elif export_type in ['comprehensive', 'academic_paper', 'progress_report', 'analytics_summary']:
            result = export_comprehensive_data(export_format, parsed_date_range, export_content)
        else:
            return jsonify({'error': 'Unknown export type'}), 400
        
        if result['success']:
            return jsonify({
                'success': True,
                'download_url': f"/download/{result['filename']}",
                'filename': result['filename'],
                'size': result['size'],
                'export_type': export_type,
                'format': export_format
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        app.logger.error(f"匯出API錯誤: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """檔案下載端點"""
    try:
        # 安全檢查
        allowed_extensions = {'.json', '.csv', '.xlsx', '.pdf', '.zip', '.txt'}
        file_ext = os.path.splitext(filename)[1].lower()
        
        if not os.path.exists(filename) or '..' in filename or file_ext not in allowed_extensions:
            app.logger.warning(f"非法檔案下載請求: {filename}")
            return "File not found or not allowed", 404
        
        return send_file(filename, as_attachment=True)
        
    except Exception as e:
        app.logger.error(f"檔案下載錯誤: {e}")
        return "Download failed", 500

# =================== LINE Bot Webhook ===================

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot webhook 處理"""
    if not line_bot_api or not handler:
        abort(400)
    
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature")
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理 LINE 訊息"""
    if not line_bot_api:
        return
    
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        
        # 取得或創建學生記錄
        student, created = Student.get_or_create(
            line_user_id=user_id,
            defaults={'name': f'學生_{user_id[-4:]}'}
        )
        
        # 儲存訊息
        message_record = Message.create(
            student=student,
            content=user_message,
            timestamp=datetime.datetime.now(),
            message_type='text'
        )
        
        # 取得 AI 回應
        ai_response = get_ai_response(user_message)
        
        # 更新學生統計
        update_student_stats(student.id, user_message, ai_response)
        
        # 發送回應
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
        logger.info(f"處理訊息成功: {user_id} -> {user_message[:50]}")
        
    except Exception as e:
        logger.error(f"處理訊息錯誤: {e}")
        if line_bot_api:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，系統暫時無法處理您的訊息，請稍後再試。")
            )

# =================== 健康檢查和狀態路由 ===================

@app.route('/health')
def health_check():
    """健康檢查端點 - 更新版"""
    try:
        db_status = 'connected' if not db.is_closed() else 'disconnected'
        
        try:
            student_count = Student.select().count()
            message_count = Message.select().count()
            real_student_count = Student.select().where(~Student.name.startswith('[DEMO]')).count()
            db_query_ok = True
        except Exception:
            student_count = 0
            message_count = 0
            real_student_count = 0
            db_query_ok = False
        
        # 檢查是否有真實資料
        has_real_data = False
        analytics_status = 'not_available'
        
        if IMPROVED_ANALYTICS_AVAILABLE:
            try:
                has_real_data = has_real_student_data()
                analytics_status = 'improved_available'
            except:
                analytics_status = 'improved_error'
        elif REAL_ANALYTICS_AVAILABLE:
            analytics_status = 'basic_available'
            has_real_data = real_student_count > 0
        
        return {
            'status': 'healthy' if db_query_ok else 'degraded',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': db_status,
            'database_queries': 'ok' if db_query_ok else 'error',
            'line_bot': 'configured' if line_bot_api else 'not_configured',
            'gemini_ai': 'configured' if GEMINI_API_KEY else 'not_configured',
            'web_interface': 'available' if WEB_TEMPLATES_AVAILABLE else 'not_available',
            'analytics_module': analytics_status,
            'has_real_data': has_real_data,
            'basic_stats': {
                'total_students': student_count,
                'real_students': real_student_count,
                'demo_students': student_count - real_student_count,
                'messages': message_count
            },
            'data_analysis_features': {
                'improved_analytics': IMPROVED_ANALYTICS_AVAILABLE,
                'basic_analytics': REAL_ANALYTICS_AVAILABLE,
                'empty_state_support': True,
                'real_time_detection': True
            },
            'recommendations': {
                'next_steps': [
                    'Invite students to use LINE Bot' if not has_real_data else 'Continue collecting data',
                    'Check LINE Bot configuration' if not line_bot_api else 'LINE Bot ready',
                    'Monitor real-time analytics' if has_real_data else 'Wait for first conversations'
                ]
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }, 500

@app.route('/real-data-status')
def real_data_status():
    """真實資料狀態檢查頁面"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_data = has_real_student_data()
            real_student_count = Student.select().where(~Student.name.startswith('[DEMO]')).count()
            total_messages = Message.select().count()
            
            return render_template_string(f"""
            <div style="font-family: sans-serif; padding: 20px;">
                <h1>📊 真實資料狀態報告</h1>
                <div style="background: {'#e7f3ff' if has_data else '#fff3cd'}; padding: 15px; margin: 15px 0; border-radius: 5px;">
                    <h3>{'✅' if has_data else '⏳'} 資料分析狀態：{'已就緒' if has_data else '等待中'}</h3>
                    <p><strong>真實學生數：</strong>{real_student_count}</p>
                    <p><strong>總訊息數：</strong>{total_messages}</p>
                    <p><strong>分析模組：</strong>改進版已載入</p>
                    <p><strong>最後檢查：</strong>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                {'<div style="background: #d4edda; padding: 15px; margin: 15px 0; border-radius: 5px;"><h4>🎉 系統已有真實資料</h4><p>教學分析功能已啟用，可以查看真實的學習洞察。</p></div>' if has_data else '<div style="background: #f8d7da; padding: 15px; margin: 15px 0; border-radius: 5px;"><h4>📱 等待學生開始對話</h4><p>請邀請學生使用 LINE Bot 開始對話，系統會自動分析並生成教學洞察。</p></div>'}
                <div style="margin-top: 20px;">
                    <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">📊 分析後台</a>
                    <a href="/" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
                </div>
            </div>
            """)
        else:
            return """
            <div style="font-family: sans-serif; padding: 20px;">
                <h1>❌ 改進的分析模組未載入</h1>
                <p>請確認 improved_real_analytics.py 檔案已正確放置並可正常載入。</p>
                <a href="/">返回首頁</a>
            </div>
            """
    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h1>❌ 真實資料狀態檢查失敗</h1>
            <p>錯誤：{str(e)}</p>
            <a href="/">返回首頁</a>
        </div>
        """, 500

# =================== 匯出功能函數 ===================

def export_conversation_data(format_type, date_range, content_type):
    """匯出對話記錄資料"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'conversation_data_{timestamp}'
        
        # 建構查詢
        query = Message.select().join(Student)
        
        # 應用日期篩選
        if date_range:
            start_date, end_date = date_range
            query = query.where(Message.timestamp.between(start_date, end_date))
        
        # 根據內容類型篩選
        if content_type == 'difficulties_only':
            query = query.where(Message.content.contains('困難'))
        elif content_type == 'interests_only':
            query = query.where(Message.content.contains('興趣'))
        
        messages = list(query.order_by(Message.timestamp.desc()))
        
        # 準備資料
        export_data = []
        for msg in messages:
            export_data.append({
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else '',
                'student_name': msg.student.name if msg.student else '',
                'message_content': msg.content or '',
                'message_type': getattr(msg, 'message_type', ''),
                'analysis_tags': getattr(msg, 'analysis_tags', '')
            })
        
        # 根據格式匯出
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_info': {
                        'type': 'conversation_data',
                        'timestamp': timestamp,
                        'record_count': len(export_data),
                        'date_range': date_range,
                        'content_type': content_type
                    },
                    'conversations': export_data
                }, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'csv':
            filename += '.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if export_data:
                    writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
                    writer.writeheader()
                    writer.writerows(export_data)
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'record_count': len(export_data)
        }
        
    except Exception as e:
        app.logger.error(f"對話資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

def export_analysis_data(format_type, date_range, content_type):
    """匯出分析報告資料"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'analysis_report_{timestamp}'
        
        # 收集分析資料
        analysis_data = {
            'export_info': {
                'type': 'analysis_report',
                'timestamp': timestamp,
                'date_range': date_range,
                'content_type': content_type
            },
            'has_real_data': False,
            'real_student_count': 0,
            'total_messages': 0
        }
        
        # 如果有改進的分析模組，取得真實資料
        if IMPROVED_ANALYTICS_AVAILABLE:
            try:
                has_data = has_real_student_data()
                analysis_data['has_real_data'] = has_data
                
                if has_data:
                    insights = get_improved_teaching_insights()
                    analysis_data.update({
                        'teaching_insights': insights,
                        'real_student_count': insights['stats']['real_students'],
                        'total_messages': insights['stats']['total_messages']
                    })
                else:
                    analysis_data['message'] = '等待真實學生資料'
            except Exception as e:
                analysis_data['error'] = str(e)
        
        # 根據格式匯出
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'pdf':
            filename += '.txt'  # 暫時用文字檔案代替 PDF
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("EMI 智能教學助理 - 分析報告\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"生成時間: {timestamp}\n")
                f.write(f"分析期間: {date_range}\n")
                f.write(f"有真實資料: {'是' if analysis_data['has_real_data'] else '否'}\n")
                f.write(f"真實學生數: {analysis_data['real_student_count']}\n")
                f.write(f"總訊息數: {analysis_data['total_messages']}\n\n")
                
                if analysis_data['has_real_data']:
                    f.write("真實教學洞察已包含在 JSON 格式中\n")
                else:
                    f.write("等待學生開始使用 LINE Bot 進行對話\n")
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size
        }
        
    except Exception as e:
        app.logger.error(f"分析資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

def export_comprehensive_data(format_type, date_range, content_type):
    """匯出綜合資料"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'comprehensive_data_{timestamp}'
        
        # 收集所有資料
        all_data = {
            'export_info': {
                'type': 'comprehensive_data',
                'timestamp': timestamp,
                'date_range': date_range,
                'content_type': content_type,
                'system_version': 'improved_analytics_v2'
            },
            'has_real_data': False,
            'conversations': [],
            'analysis': {},
            'statistics': {}
        }
        
        # 檢查並收集真實資料
        if IMPROVED_ANALYTICS_AVAILABLE:
            try:
                has_data = has_real_student_data()
                all_data['has_real_data'] = has_data
                
                if has_data:
                    # 收集對話資料
                    conversation_result = export_conversation_data('dict', date_range, content_type)
                    if conversation_result.get('success'):
                        all_data['conversations'] = conversation_result.get('data', [])
                    
                    # 收集分析資料
                    insights = get_improved_teaching_insights()
                    all_data['analysis'] = insights
                    all_data['statistics'] = insights['stats']
                else:
                    all_data['message'] = '系統等待真實學生資料中'
            except Exception as e:
                all_data['error'] = str(e)
        
        # 根據格式匯出
        if format_type == 'json':
            filename += '.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
        elif format_type == 'zip':
            filename += '.zip'
            with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加 JSON 資料
                json_content = json.dumps(all_data, ensure_ascii=False, indent=2)
                zipf.writestr('comprehensive_data.json', json_content)
                
                # 添加說明文件
                readme_content = f"""
EMI 智能教學助理 - 綜合資料匯出
====================================

匯出時間: {timestamp}
系統版本: improved_analytics_v2
真實資料: {'是' if all_data['has_real_data'] else '否'}

檔案說明:
- comprehensive_data.json: 完整的系統資料
- README.txt: 本說明文件

如果「真實資料」為「否」，表示系統正在等待學生開始使用 LINE Bot。
請邀請學生開始對話後重新匯出以取得真實的教學分析資料。
                """
                zipf.writestr('README.txt', readme_content)
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size,
            'has_real_data': all_data['has_real_data']
        }
        
    except Exception as e:
        app.logger.error(f"綜合資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

# =================== 測試和開發路由 ===================

@app.route('/create-sample-data')
def create_sample_data_route():
    """創建樣本資料（僅供開發測試使用）"""
    try:
        result = create_sample_data()
        return jsonify({
            'success': True,
            'message': '樣本資料創建成功',
            'created': result,
            'note': '注意：這些是演示資料，不會影響真實資料分析'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =================== 錯誤處理 ===================

@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return f"""
    <div style="font-family: sans-serif; padding: 20px; text-align: center;">
        <h1>🔍 頁面不存在</h1>
        <p>您要訪問的頁面不存在。</p>
        <div style="margin-top: 20px;">
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
            <a href="/teaching-insights" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">📊 分析後台</a>
        </div>
    </div>
    """, 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    return f"""
    <div style="font-family: sans-serif; padding: 20px; text-align: center;">
        <h1>⚠️ 伺服器錯誤</h1>
        <p>系統遇到內部錯誤，請稍後再試。</p>
        <div style="margin-top: 20px;">
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
            <a href="/health" style="padding: 10px 20px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏥 系統檢查</a>
        </div>
    </div>
    """, 500

# =================== 程式進入點 ===================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（改進真實資料分析版）")
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🌐 Web 管理後台: {'可用' if WEB_TEMPLATES_AVAILABLE else '不可用'}")
    logger.info(f"📊 改進分析模組: {'已載入' if IMPROVED_ANALYTICS_AVAILABLE else '未載入'}")
    logger.info(f"📊 基本分析模組: {'已載入' if REAL_ANALYTICS_AVAILABLE else '未載入'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🔗 Port: {port}, Debug: {debug}")
    
    if WEB_TEMPLATES_AVAILABLE:
        logger.info("📊 Web 管理後台路由:")
        logger.info("   - 首頁: / （支援等待狀態）")
        logger.info("   - 學生管理: /students")
        logger.info("   - 教師分析: /teaching-insights （支援等待狀態）")
        logger.info("   - 對話摘要: /conversation-summaries （支援等待狀態）")
        logger.info("   - 學習建議: /learning-recommendations （支援等待狀態）")
        logger.info("   - 儲存管理: /storage-management")
    
    logger.info("🔧 API 端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - 真實資料狀態: /real-data-status")
    logger.info("   - 真實資料狀態 API: /api/real-data-status")
    logger.info("   - 資料匯出: /api/export/<type>")
    logger.info("   - 檔案下載: /download/<filename>")
    logger.info("   - 學生分析: /api/student-analysis/<id>")
    logger.info("   - 儀表板統計: /api/dashboard-stats")
    logger.info("   - 班級統計: /api/class-statistics")
    logger.info("   - LINE Bot Webhook: /callback")
    
    logger.info("✅ 重要更新：")
    logger.info("   ✅ 新增改進的真實資料分析系統")
    logger.info("   ✅ 支援無資料時的專業等待狀態")
    logger.info("   ✅ 自動檢測真實學生資料並切換顯示模式")
    logger.info("   ✅ 保留完整的匯出功能和 API")
    logger.info("   ✅ 向後相容原有分析模組")
    logger.info("   ✅ 即時資料狀態檢查和更新")
    
    if IMPROVED_ANALYTICS_AVAILABLE:
        try:
            has_initial_data = has_real_student_data()
            logger.info(f"📈 初始資料狀態: {'有真實資料' if has_initial_data else '等待學生對話'}")
        except:
            logger.info("📈 初始資料狀態: 檢查中...")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點
application = app
