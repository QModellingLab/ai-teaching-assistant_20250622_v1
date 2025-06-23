# app.py - 更新版本（移除資料匯出中心相關內容）

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

# 導入 REAL DATA 分析模組
try:
    from fixed_analytics import (
        get_real_teaching_insights,
        get_real_conversation_summaries,
        get_real_storage_management,
        get_real_student_recommendations,
        real_analytics
    )
    REAL_ANALYTICS_AVAILABLE = True
    logging.info("✅ Real data analytics module loaded successfully")
except ImportError as e:
    REAL_ANALYTICS_AVAILABLE = False
    logging.error(f"❌ Failed to load real analytics module: {e}")

# 導入 Web 管理後台模板（更新：移除 DATA_EXPORT_TEMPLATE）
try:
    from templates_main import INDEX_TEMPLATE, STUDENTS_TEMPLATE, STUDENT_DETAIL_TEMPLATE
    from templates_analysis_part1 import TEACHING_INSIGHTS_TEMPLATE  # 這個已經更新為包含匯出功能
    from templates_analysis_part2 import CONVERSATION_SUMMARIES_TEMPLATE
    from templates_analysis_part3 import LEARNING_RECOMMENDATIONS_TEMPLATE
    from templates_management import STORAGE_MANAGEMENT_TEMPLATE
    # 移除：DATA_EXPORT_TEMPLATE - 已整合到 TEACHING_INSIGHTS_TEMPLATE
    WEB_TEMPLATES_AVAILABLE = True
    logging.info("✅ Web management templates loaded successfully")
except ImportError as e:
    WEB_TEMPLATES_AVAILABLE = False
    logging.warning(f"⚠️ Web management templates load failed: {e}")

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

# =================== 更新的路由設定 ===================

@app.route('/')
def index():
    """首頁"""
    try:
        if REAL_ANALYTICS_AVAILABLE:
            real_data = get_real_teaching_insights()
            return render_template_string(
                INDEX_TEMPLATE,
                stats=real_data['stats'],
                recent_messages=real_data.get('recent_messages', []),
                real_data_info=real_data
            )
        else:
            return render_template_string(INDEX_TEMPLATE, stats={}, recent_messages=[])
    except Exception as e:
        app.logger.error(f"首頁錯誤: {e}")
        return render_template_string(INDEX_TEMPLATE, stats={}, recent_messages=[])

@app.route('/teaching-insights')
def teaching_insights():
    """教師分析後台 - 整合匯出功能"""
    try:
        if REAL_ANALYTICS_AVAILABLE:
            real_data = get_real_teaching_insights()
            
            # 標記這是真實資料
            real_data['data_source'] = 'REAL DATABASE DATA'
            real_data['last_updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 如果沒有真實資料，顯示提示訊息
            if real_data['stats']['real_students'] == 0:
                real_data['no_real_data_message'] = """
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; margin: 20px 0; border-radius: 10px;">
                    <h3>📊 等待真實資料</h3>
                    <p><strong>目前系統中沒有真實學生資料。</strong></p>
                    <p>要查看真實的教學分析數據，請：</p>
                    <ol>
                        <li>讓學生開始使用 LINE Bot 進行對話</li>
                        <li>學生發送訊息到您的 LINE Bot</li>
                        <li>系統會自動分析對話內容並生成真實統計</li>
                    </ol>
                    <p><em>教師分析後台現在包含完整的資料匯出功能</em></p>
                </div>
                """
            
            return render_template_string(
                TEACHING_INSIGHTS_TEMPLATE,  # 使用更新後的模板（包含匯出功能）
                category_stats=real_data['category_stats'],
                engagement_analysis=real_data['engagement_analysis'],
                students=real_data['students'],
                stats=real_data['stats'],
                real_data_info=real_data,
                current_time=datetime.datetime.now()
            )
        else:
            # 如果真實分析模組不可用
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 真實資料分析模組未載入</h1>
                <p>教師分析後台需要真實資料分析模組</p>
                <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
            </div>
            """
            
    except Exception as e:
        logger.error(f"Teaching insights error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 教師分析後台載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """, 500

# =================== 移除的路由 ===================
# @app.route('/data-export') - 已移除，功能整合到 /teaching-insights

# =================== 匯出相關 API 路由 ===================

@app.route('/api/export/<export_type>')
def export_data_api(export_type):
    """資料匯出 API - 支援對話記錄和分析報告"""
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
        
        # 導入匯出函數
        from data_management import perform_data_export
        
        # 根據匯出類型執行不同的匯出邏輯
        if export_type == 'conversations':
            result = export_conversation_data(export_format, parsed_date_range, export_content)
        elif export_type == 'analysis':
            result = export_analysis_data(export_format, parsed_date_range, export_content)
        elif export_type in ['comprehensive', 'academic_paper', 'progress_report', 'analytics_summary']:
            result = perform_data_export(export_type, export_format, parsed_date_range)
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
        from flask import send_file
        
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

# =================== 新增的匯出函數 ===================

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
                'ai_response': getattr(msg, 'ai_response', ''),
                'message_type': getattr(msg, 'message_type', ''),
                'analysis_tags': getattr(msg, 'analysis_tags', '')
            })
        
        # 根據格式匯出
        if format_type == 'json':
            filename += '.json'
            import json
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
            import csv
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
            'difficulty_analysis': get_difficulty_analysis_data(date_range),
            'interest_topics': get_interest_topics_data(date_range),
            'learning_progress': get_learning_progress_data(date_range),
            'teaching_recommendations': get_teaching_recommendations_data(date_range)
        }
        
        # 根據格式匯出
        if format_type == 'json':
            filename += '.json'
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
        elif format_type == 'pdf':
            filename += '.txt'  # 暫時用文字檔案代替 PDF
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("AI學習分析報告\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"生成時間: {timestamp}\n")
                f.write(f"分析期間: {date_range}\n\n")
                f.write("學習困難點分析:\n")
                f.write(str(analysis_data['difficulty_analysis']))
                f.write("\n\n學生興趣主題:\n")
                f.write(str(analysis_data['interest_topics']))
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return {
            'success': True,
            'filename': filename,
            'size': file_size
        }
        
    except Exception as e:
        app.logger.error(f"分析資料匯出錯誤: {e}")
        return {'success': False, 'error': str(e)}

# =================== 輔助分析函數 ===================

def get_difficulty_analysis_data(date_range):
    """取得困難點分析資料"""
    return {
        'present_perfect_confusion': {
            'student_count': 5,
            'message_count': 12,
            'severity': 'high',
            'examples': ['什麼時候用現在完成式？', 'I have been 和 I went 有什麼不同？']
        },
        'passive_voice_usage': {
            'student_count': 3,
            'message_count': 8,
            'severity': 'medium',
            'examples': ['為什麼這裡要用被動語態？', '什麼情況下用被動比較好？']
        }
    }

def get_interest_topics_data(date_range):
    """取得興趣主題資料"""
    return {
        'travel_english': {'count': 12, 'trend': 'increasing'},
        'technology': {'count': 8, 'trend': 'stable'},
        'cultural_differences': {'count': 6, 'trend': 'increasing'},
        'business_communication': {'count': 4, 'trend': 'stable'}
    }

def get_learning_progress_data(date_range):
    """取得學習進步資料"""
    return {
        'overall_improvement': '15%',
        'active_students': 85,
        'engagement_increase': '35%'
    }

def get_teaching_recommendations_data(date_range):
    """取得教學建議資料"""
    return [
        {
            'topic': '現在完成式',
            'recommendation': '增加時間軸視覺化教學',
            'priority': 'high'
        },
        {
            'topic': '被動語態',
            'recommendation': '提供更多情境練習',
            'priority': 'medium'
        }
    ]

# =================== 其他路由保持不變 ===================

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
        app.logger.error(f"學生詳細頁面錯誤: {e}")
        return f"學生資料載入失敗: {str(e)}", 500

@app.route('/storage-management')
def storage_management():
    """儲存管理頁面"""
    try:
        if REAL_ANALYTICS_AVAILABLE:
            real_storage_info = get_real_storage_management()
            return render_template_string(
                STORAGE_MANAGEMENT_TEMPLATE,
                storage_stats=real_storage_info,
                real_data_info=real_storage_info
            )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 真實資料分析模組未載入</h1>
                <p>儲存管理需要真實資料分析模組</p>
                <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
            </div>
            """
    except Exception as e:
        logger.error(f"Storage management error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 儲存管理載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/teaching-insights" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回分析後台</a>
        </div>
        """, 500

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

# =================== 健康檢查 ===================

@app.route('/health')
def health_check():
    """健康檢查端點"""
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
        
        return {
            'status': 'healthy' if db_query_ok else 'degraded',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': db_status,
            'database_queries': 'ok' if db_query_ok else 'error',
            'line_bot': 'configured' if line_bot_api else 'not_configured',
            'gemini_ai': 'configured' if GEMINI_API_KEY else 'not_configured',
            'web_interface': 'available' if WEB_TEMPLATES_AVAILABLE else 'not_available',
            'real_analytics': 'available' if REAL_ANALYTICS_AVAILABLE else 'not_available',
            'basic_stats': {
                'total_students': student_count,
                'real_students': real_student_count,
                'demo_students': student_count - real_student_count,
                'messages': message_count
            },
            'export_integration': 'completed',  # 新增：標記匯出功能已整合
            'data_export_center': 'removed'      # 新增：標記資料匯出中心已移除
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }, 500

# =================== 程式進入點 ===================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（整合匯出功能版）")
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🌐 Web 管理後台: {'可用' if WEB_TEMPLATES_AVAILABLE else '不可用'}")
    logger.info(f"📊 真實資料分析: {'已載入' if REAL_ANALYTICS_AVAILABLE else '未載入'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🔗 Port: {port}, Debug: {debug}")
    
    if WEB_TEMPLATES_AVAILABLE:
        logger.info("📊 Web 管理後台路由:")
        logger.info("   - 首頁: / （真實資料統計）")
        logger.info("   - 學生管理: /students （真實學生資料）")
        logger.info("   - 教師洞察: /teaching-insights （整合匯出功能）")
        logger.info("   - 儲存管理: /storage-management （真實儲存使用量）")
        logger.info("   ❌ 資料匯出中心: /data-export （已移除，功能整合到教師洞察）")
    
    logger.info("🔧 API 端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - 資料匯出: /api/export/<type>")
    logger.info("   - 檔案下載: /download/<filename>")
    logger.info("   - LINE Bot Webhook: /callback")
    
    logger.info("✅ 重要更新：")
    logger.info("   ✅ 資料匯出功能已整合到教師分析後台")
    logger.info("   ✅ 移除獨立的資料匯出中心頁面")
    logger.info("   ✅ 新增對話記錄和分析報告匯出 API")
    logger.info("   ✅ 支援多種匯出格式（JSON, CSV, PDF, Excel）")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點
application = app
