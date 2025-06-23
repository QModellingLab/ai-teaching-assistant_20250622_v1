# app.py - 修正匯入錯誤版

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

# 導入改進的真實資料分析模組
try:
    from improved_real_analytics import (
        has_real_student_data,
        get_improved_teaching_insights,
        get_improved_conversation_summaries,
        get_improved_student_recommendations,
        get_improved_storage_management,
        improved_analytics
    )
    IMPROVED_ANALYTICS_AVAILABLE = True
    logging.info("✅ Improved real data analytics module loaded successfully")
except ImportError as e:
    IMPROVED_ANALYTICS_AVAILABLE = False
    logging.error(f"❌ Failed to load improved analytics module: {e}")

# 導入 Web 管理後台模板
try:
    from templates_main import INDEX_TEMPLATE, STUDENTS_TEMPLATE, STUDENT_DETAIL_TEMPLATE
    from templates_analysis_part1 import TEACHING_INSIGHTS_TEMPLATE
    from templates_analysis_part2 import CONVERSATION_SUMMARIES_TEMPLATE
    from templates_analysis_part3 import LEARNING_RECOMMENDATIONS_TEMPLATE
    from templates_management import STORAGE_MANAGEMENT_TEMPLATE
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

# =================== 主要路由 ===================

@app.route('/')
def index():
    """首頁 - 支援等待狀態和真實資料檢測"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            # 檢查是否有真實學生資料
            has_real_data = has_real_student_data()
            insights_data = get_improved_teaching_insights()
            
            # 設定資料狀態
            data_status = 'ACTIVE' if has_real_data else 'WAITING_FOR_DATA'
            
            return render_template_string(
                INDEX_TEMPLATE,
                stats=insights_data['stats'],
                recent_messages=insights_data.get('recent_messages', []),
                real_data_info={
                    'has_real_data': has_real_data,
                    'data_status': data_status,
                    'last_updated': insights_data.get('timestamp'),
                    'total_real_students': insights_data['stats'].get('real_students', 0)
                }
            )
        else:
            # 如果改進分析模組不可用，使用基本狀態
            return render_template_string(
                INDEX_TEMPLATE,
                stats={'total_students': 0, 'real_students': 0, 'total_messages': 0, 'avg_participation': 0},
                recent_messages=[],
                real_data_info={
                    'has_real_data': False,
                    'data_status': 'WAITING_FOR_DATA',
                    'error': 'Analytics module not available'
                }
            )
    except Exception as e:
        app.logger.error(f"首頁錯誤: {e}")
        return render_template_string(
            INDEX_TEMPLATE,
            stats={'total_students': 0, 'real_students': 0, 'total_messages': 0, 'avg_participation': 0},
            recent_messages=[],
            real_data_info={
                'has_real_data': False,
                'data_status': 'ERROR',
                'error': str(e)
            }
        )

@app.route('/teaching-insights')
def teaching_insights():
    """教師分析後台 - 使用改進的真實資料分析"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            insights_data = get_improved_teaching_insights()
            
            # 檢查是否有真實資料
            if not insights_data.get('has_real_data', False):
                # 顯示等待狀態頁面
                no_data_message = f"""
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; margin: 20px 0; border-radius: 10px; text-align: center;">
                    <h3>📊 等待真實教學資料</h3>
                    <p><strong>系統目前沒有真實學生對話資料。</strong></p>
                    <p>要查看真實的教學分析，請：</p>
                    <ol style="text-align: left; max-width: 500px; margin: 15px auto;">
                        <li>確認 LINE Bot 已正確設定並運作</li>
                        <li>分享 LINE Bot 連結給學生</li>
                        <li>鼓勵學生開始用英文提問或討論</li>
                        <li>系統會即時分析每則對話並更新此頁面</li>
                    </ol>
                    <p style="margin-top: 15px;">
                        <button onclick="window.location.reload()" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                            🔄 重新檢查資料
                        </button>
                        <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                            🏠 返回首頁
                        </a>
                    </p>
                </div>
                """
                insights_data['no_real_data_message'] = no_data_message
            
            return render_template_string(
                TEACHING_INSIGHTS_TEMPLATE,
                category_stats=insights_data['category_stats'],
                engagement_analysis=insights_data['engagement_analysis'],
                students=insights_data['students'],
                stats=insights_data['stats'],
                real_data_info=insights_data,
                current_time=datetime.datetime.now()
            )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 改進分析模組未載入</h1>
                <p>教師分析後台需要改進的真實資料分析模組</p>
                <p>請檢查 improved_real_analytics.py 檔案是否存在</p>
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
                    <li>improved_real_analytics.py 檔案遺失或語法錯誤</li>
                    <li>資料庫連接問題</li>
                    <li>模板檔案載入失敗</li>
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
    """對話摘要頁面"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            summaries_data = get_improved_conversation_summaries()
            
            return render_template_string(
                CONVERSATION_SUMMARIES_TEMPLATE,
                summaries=summaries_data['summaries'],
                insights=summaries_data['insights'],
                real_data_message=summaries_data.get('message', ''),
                current_time=datetime.datetime.now()
            )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 改進分析模組未載入</h1>
                <p>對話摘要需要改進的真實資料分析模組</p>
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
    """學習建議頁面"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            recommendations_data = get_improved_student_recommendations()
            
            return render_template_string(
                LEARNING_RECOMMENDATIONS_TEMPLATE,
                recommendations=recommendations_data['recommendations'],
                overview=recommendations_data['overview'],
                real_data_message=recommendations_data.get('message', ''),
                current_time=datetime.datetime.now()
            )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 改進分析模組未載入</h1>
                <p>學習建議需要改進的真實資料分析模組</p>
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
            storage_info = get_improved_storage_management()
            return render_template_string(
                STORAGE_MANAGEMENT_TEMPLATE,
                storage_stats=storage_info,
                real_data_info=storage_info
            )
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 改進分析模組未載入</h1>
                <p>儲存管理需要改進的真實資料分析模組</p>
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

# =================== API 路由 ===================

@app.route('/api/dashboard-stats')
def dashboard_stats_api():
    """儀表板統計 API - 支援真實資料檢測"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            insights_data = get_improved_teaching_insights()
            return jsonify({
                'success': True,
                'stats': insights_data['stats'],
                'has_real_data': insights_data.get('has_real_data', False),
                'last_updated': insights_data.get('timestamp'),
                'data_source': 'improved_real_analytics'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Improved analytics not available',
                'stats': {
                    'total_students': Student.select().count(),
                    'real_students': 0,
                    'total_messages': 0,
                    'avg_participation': 0
                },
                'has_real_data': False
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'has_real_data': False
        }), 500

@app.route('/api/student-analysis/<int:student_id>')
def student_analysis_api(student_id):
    """學生分析 API"""
    try:
        analysis = analyze_student_patterns(student_id)
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/class-statistics')
def class_statistics_api():
    """班級統計 API"""
    try:
        stats = {
            'total_students': Student.select().count(),
            'total_messages': Message.select().count(),
            'active_students_today': Student.select().where(
                Student.last_active >= datetime.datetime.now().date()
            ).count(),
            'avg_messages_per_student': 0,
            'common_question_types': ['文法', '詞彙', '發音']
        }
        
        if stats['total_students'] > 0:
            stats['avg_messages_per_student'] = stats['total_messages'] / stats['total_students']
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =================== 匯出相關 API 路由 ===================

@app.route('/api/export/<export_type>')
def export_data_api(export_type):
    """資料匯出 API"""
    try:
        export_format = request.args.get('format', 'json')
        date_range = request.args.get('date_range', None)
        
        # 簡化的匯出功能
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{export_type}_{timestamp}.{export_format}'
        
        # 模擬匯出資料
        export_data = {
            'export_info': {
                'type': export_type,
                'timestamp': timestamp,
                'format': export_format
            },
            'data': f'Export data for {export_type}'
        }
        
        if export_format == 'json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        
        return jsonify({
            'success': True,
            'download_url': f"/download/{filename}",
            'filename': filename,
            'size': file_size,
            'export_type': export_type,
            'format': export_format
        })
        
    except Exception as e:
        app.logger.error(f"匯出API錯誤: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """檔案下載端點"""
    try:
        if not os.path.exists(filename) or '..' in filename:
            return "File not found", 404
        
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
        update_student_stats(student.id)
        
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
            'improved_analytics': 'available' if IMPROVED_ANALYTICS_AVAILABLE else 'not_available',
            'basic_stats': {
                'total_students': student_count,
                'real_students': real_student_count,
                'demo_students': student_count - real_student_count,
                'messages': message_count
            },
            'has_real_data': real_student_count > 0 and message_count > 0
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }, 500

@app.route('/real-data-status')
def real_data_status():
    """真實資料狀態檢查"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            has_data = has_real_student_data()
            insights_data = get_improved_teaching_insights()
            
            return render_template_string(f"""
            <div style="font-family: sans-serif; padding: 20px;">
                <h1>📊 真實資料狀態報告</h1>
                <div style="background: {'#e7f3ff' if has_data else '#fff3cd'}; padding: 15px; margin: 15px 0; border-radius: 5px;">
                    <h3>{'✅' if has_data else '⏳'} 資料狀態：{'有真實資料' if has_data else '等待真實資料'}</h3>
                    <p><strong>真實學生數：</strong>{insights_data['stats']['real_students']}</p>
                    <p><strong>總訊息數：</strong>{insights_data['stats']['total_messages']}</p>
                    <p><strong>最後更新：</strong>{insights_data.get('timestamp', 'N/A')}</p>
                </div>
                {f'<div style="background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 5px;"><p>系統正在等待學生使用 LINE Bot。請確認學生已開始與 AI 對話。</p></div>' if not has_data else ''}
                <a href="/teaching-insights">返回分析後台</a>
            </div>
            """)
        else:
            return """
            <div style="font-family: sans-serif; padding: 20px;">
                <h1>❌ 改進分析模組未載入</h1>
                <p>請檢查 improved_real_analytics.py 檔案是否存在並正確配置。</p>
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

# =================== 測試和開發路由 ===================

@app.route('/create-sample-data')
def create_sample_data_route():
    """創建樣本資料（僅供開發測試使用）"""
    try:
        create_sample_data()
        return jsonify({
            'success': True,
            'message': '樣本資料創建成功'
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
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（改進版）")
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🌐 Web 管理後台: {'可用' if WEB_TEMPLATES_AVAILABLE else '不可用'}")
    logger.info(f"📊 改進分析系統: {'已載入' if IMPROVED_ANALYTICS_AVAILABLE else '未載入'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🔗 Port: {port}, Debug: {debug}")
    
    if WEB_TEMPLATES_AVAILABLE:
        logger.info("📊 Web 管理後台路由:")
        logger.info("   - 首頁: / （支援等待狀態）")
        logger.info("   - 學生管理: /students")
        logger.info("   - 教師洞察: /teaching-insights （真實資料分析）")
        logger.info("   - 對話摘要: /conversation-summaries")
        logger.info("   - 學習建議: /learning-recommendations")
        logger.info("   - 儲存管理: /storage-management")
    
    logger.info("🔧 API 端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - 真實資料狀態: /real-data-status")
    logger.info("   - 儀表板統計: /api/dashboard-stats （支援真實資料檢測）")
    logger.info("   - 資料匯出: /api/export/<type>")
    logger.info("   - 檔案下載: /download/<filename>")
    logger.info("   - 學生分析: /api/student-analysis/<id>")
    logger.info("   - 班級統計: /api/class-statistics")
    logger.info("   - LINE Bot Webhook: /callback")
    
    if IMPROVED_ANALYTICS_AVAILABLE:
        logger.info("✅ 重要功能：")
        logger.info("   ✅ 智能等待狀態：無真實資料時顯示專業等待介面")
        logger.info("   ✅ 真實資料檢測：自動檢測學生使用 LINE Bot")
        logger.info("   ✅ 即時狀態切換：有資料時自動切換到分析模式")
        logger.info("   ✅ 改進分析系統：只使用真實資料庫資料")
        logger.info("   ✅ 等待狀態指引：提供清楚的設定步驟")
    else:
        logger.warning("⚠️ 改進分析模組未載入，部分功能可能不可用")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點
application = app
