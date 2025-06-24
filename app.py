# app.py - 真實資料版本（移除演示資料功能）

import os
import json
import datetime
import logging
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
    get_question_category_stats,
    get_student_conversation_summary
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
    from templates_utils import get_template, ERROR_TEMPLATE, HEALTH_TEMPLATE
    from templates_main import INDEX_TEMPLATE, STUDENTS_TEMPLATE, STUDENT_DETAIL_TEMPLATE
    
    try:
        from templates_analysis_part1 import TEACHING_INSIGHTS_TEMPLATE
    except ImportError:
        TEACHING_INSIGHTS_TEMPLATE = ""
        
    try:
        from templates_analysis_part2 import CONVERSATION_SUMMARIES_TEMPLATE
    except ImportError:
        CONVERSATION_SUMMARIES_TEMPLATE = ""
        
    try:
        from templates_analysis_part3 import LEARNING_RECOMMENDATIONS_TEMPLATE
    except ImportError:
        LEARNING_RECOMMENDATIONS_TEMPLATE = ""
        
    try:
        from templates_management import STORAGE_MANAGEMENT_TEMPLATE
    except ImportError:
        STORAGE_MANAGEMENT_TEMPLATE = ""
    
    WEB_TEMPLATES_AVAILABLE = True
    logging.info("✅ Web management templates loaded successfully")
    
except ImportError as e:
    WEB_TEMPLATES_AVAILABLE = False
    logging.warning(f"⚠️ Web management templates load failed: {e}")
    
    # Create minimal fallbacks
    INDEX_TEMPLATE = STUDENTS_TEMPLATE = STUDENT_DETAIL_TEMPLATE = ""
    TEACHING_INSIGHTS_TEMPLATE = CONVERSATION_SUMMARIES_TEMPLATE = ""
    LEARNING_RECOMMENDATIONS_TEMPLATE = STORAGE_MANAGEMENT_TEMPLATE = ""
    ERROR_TEMPLATE = HEALTH_TEMPLATE = ""
    
    def get_template(name):
        return ""

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

# =================== 資料庫連接管理 ===================

def ensure_db_connection():
    """確保資料庫連接正常"""
    try:
        if db.is_closed():
            logger.info("🔄 資料庫連接已關閉，正在重新連接...")
            db.connect()
            logger.info("✅ 資料庫重新連接成功")
        
        # 測試連接
        db.execute_sql('SELECT 1')
        logger.info("✅ 資料庫連接測試通過")
        return True
        
    except Exception as e:
        logger.error(f"❌ 資料庫連接失敗: {e}")
        logger.error(f"❌ 連接錯誤類型: {type(e).__name__}")
        
        # 嘗試重新連接
        try:
            if not db.is_closed():
                db.close()
            db.connect()
            db.execute_sql('SELECT 1')
            logger.info("✅ 資料庫強制重連成功")
            return True
        except Exception as retry_error:
            logger.error(f"❌ 資料庫重連也失敗: {retry_error}")
            return False

def get_db_status():
    """取得資料庫狀態"""
    try:
        if db.is_closed():
            return "disconnected"
        
        # 測試查詢
        db.execute_sql('SELECT 1')
        return "connected"
        
    except Exception as e:
        logger.error(f"資料庫狀態檢查錯誤: {e}")
        return "error"

def initialize_db_with_retry(max_retries=3):
    """帶重試機制的資料庫初始化"""
    for attempt in range(max_retries):
        try:
            logger.info(f"📊 嘗試初始化資料庫 (第 {attempt + 1} 次)")
            
            # 原有的初始化邏輯
            initialize_db()
            
            # 確保連接
            if ensure_db_connection():
                logger.info("✅ 資料庫初始化完成")
                return True
            else:
                logger.warning(f"⚠️ 資料庫初始化嘗試 {attempt + 1} 失敗")
                
        except Exception as e:
            logger.error(f"❌ 資料庫初始化錯誤 (嘗試 {attempt + 1}): {e}")
            
        if attempt < max_retries - 1:
            import time
            time.sleep(2)  # 等待 2 秒後重試
    
    logger.error("💥 資料庫初始化完全失敗")
    return False

# =================== 資料庫清理功能 ===================

class DatabaseCleaner:
    """資料庫清理器 - 移除演示資料"""
    
    def __init__(self):
        self.cleanup_stats = {
            'students_deleted': 0,
            'messages_deleted': 0,
            'analyses_deleted': 0,
            'ai_responses_deleted': 0
        }
    
    def identify_demo_data(self):
        """識別演示資料"""
        try:
            # 演示學生
            demo_students = list(Student.select().where(
                (Student.name.startswith('[DEMO]')) |
                (Student.line_user_id.startswith('demo_'))
            ))
            
            # 演示訊息
            demo_messages = list(Message.select().where(
                Message.source_type == 'demo'
            ))
            
            # 演示學生相關的所有資料
            demo_student_ids = [s.id for s in demo_students]
            
            return {
                'demo_students': demo_students,
                'demo_messages': demo_messages,
                'demo_student_ids': demo_student_ids
            }
        except Exception as e:
            logger.error(f"識別演示資料錯誤: {e}")
            return {'demo_students': [], 'demo_messages': [], 'demo_student_ids': []}
    
    def clean_demo_data(self):
        """清理演示資料"""
        try:
            demo_data = self.identify_demo_data()
            
            if not demo_data['demo_students'] and not demo_data['demo_messages']:
                return {
                    'success': True,
                    'message': '沒有找到演示資料，資料庫已經是純淨狀態',
                    'stats': self.cleanup_stats
                }
            
            # 清理演示學生及其相關資料
            for student in demo_data['demo_students']:
                try:
                    # 刪除相關的 AI 回應
                    ai_responses_deleted = AIResponse.delete().where(
                        AIResponse.student == student
                    ).execute()
                    self.cleanup_stats['ai_responses_deleted'] += ai_responses_deleted
                    
                    # 刪除相關的分析記錄
                    analyses_deleted = Analysis.delete().where(
                        Analysis.student == student
                    ).execute()
                    self.cleanup_stats['analyses_deleted'] += analyses_deleted
                    
                    # 刪除相關的訊息
                    messages_deleted = Message.delete().where(
                        Message.student == student
                    ).execute()
                    self.cleanup_stats['messages_deleted'] += messages_deleted
                    
                    # 刪除學生記錄
                    student.delete_instance()
                    self.cleanup_stats['students_deleted'] += 1
                    
                    logger.info(f"已清理演示學生: {student.name}")
                    
                except Exception as e:
                    logger.error(f"清理演示學生 {student.name} 時發生錯誤: {e}")
            
            # 清理孤立的演示訊息
            for message in demo_data['demo_messages']:
                try:
                    message.delete_instance()
                    self.cleanup_stats['messages_deleted'] += 1
                except Exception as e:
                    logger.error(f"清理演示訊息時發生錯誤: {e}")
            
            # 清理包含演示關鍵字的分析記錄
            demo_analyses_deleted = Analysis.delete().where(
                (Analysis.analysis_data.contains('DEMO')) |
                (Analysis.analysis_data.contains('demo'))
            ).execute()
            self.cleanup_stats['analyses_deleted'] += demo_analyses_deleted
            
            return {
                'success': True,
                'message': f"成功清理演示資料：{self.cleanup_stats['students_deleted']} 位學生，{self.cleanup_stats['messages_deleted']} 則訊息",
                'stats': self.cleanup_stats
            }
            
        except Exception as e:
            logger.error(f"清理演示資料錯誤: {e}")
            return {
                'success': False,
                'message': f"清理過程發生錯誤: {str(e)}",
                'stats': self.cleanup_stats
            }
    
    def get_real_data_status(self):
        """取得真實資料狀態"""
        try:
            real_students = Student.select().where(
                (~Student.name.startswith('[DEMO]')) &
                (~Student.line_user_id.startswith('demo_'))
            ).count()
            
            real_messages = Message.select().join(Student).where(
                (~Student.name.startswith('[DEMO]')) &
                (~Student.line_user_id.startswith('demo_')) &
                (Message.source_type != 'demo')
            ).count()
            
            demo_students = Student.select().where(
                (Student.name.startswith('[DEMO]')) |
                (Student.line_user_id.startswith('demo_'))
            ).count()
            
            demo_messages = Message.select().where(
                Message.source_type == 'demo'
            ).count()
            
            return {
                'real_students': real_students,
                'real_messages': real_messages,
                'demo_students': demo_students,
                'demo_messages': demo_messages,
                'has_real_data': real_students > 0 and real_messages > 0,
                'has_demo_data': demo_students > 0 or demo_messages > 0
            }
            
        except Exception as e:
            logger.error(f"取得資料狀態錯誤: {e}")
            return {
                'real_students': 0,
                'real_messages': 0,
                'demo_students': 0,
                'demo_messages': 0,
                'has_real_data': False,
                'has_demo_data': False,
                'error': str(e)
            }

# 全域清理器實例
db_cleaner = DatabaseCleaner()

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
            data_status = db_cleaner.get_real_data_status()
            return render_template_string(
                INDEX_TEMPLATE,
                stats={
                    'total_students': data_status['real_students'], 
                    'real_students': data_status['real_students'], 
                    'total_messages': data_status['real_messages'], 
                    'avg_participation': 0
                },
                recent_messages=[],
                real_data_info={
                    'has_real_data': data_status['has_real_data'],
                    'data_status': 'ACTIVE' if data_status['has_real_data'] else 'WAITING_FOR_DATA',
                    'error': data_status.get('error')
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

# =================== 管理員功能路由 ===================

@app.route('/admin')
def admin_dashboard():
    """管理員儀表板"""
    try:
        data_status = db_cleaner.get_real_data_status()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>🔧 系統管理儀表板 - EMI 智能教學助理</title>
            <style>
                body {{ font-family: sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; min-height: 100vh; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
                .admin-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; padding: 30px; }}
                .admin-card {{ background: #f8f9fa; border: 2px solid #e9ecef; border-radius: 10px; padding: 25px; text-align: center; transition: all 0.3s ease; }}
                .admin-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.15); }}
                .admin-card.primary {{ border-color: #007bff; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); }}
                .admin-card.success {{ border-color: #28a745; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); }}
                .admin-card.warning {{ border-color: #ffc107; background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%); }}
                .admin-card.danger {{ border-color: #dc3545; background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); }}
                .card-icon {{ font-size: 3em; margin-bottom: 15px; }}
                .card-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 10px; color: #2c3e50; }}
                .card-description {{ color: #666; margin-bottom: 20px; line-height: 1.5; }}
                .card-button {{ background: #007bff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; display: inline-block; transition: all 0.3s ease; }}
                .card-button:hover {{ background: #0056b3; transform: scale(1.05); }}
                .status-bar {{ background: #f8f9fa; padding: 20px; border-bottom: 1px solid #dee2e6; }}
                .status-item {{ display: inline-block; margin: 0 20px; }}
                .status-number {{ font-size: 1.5em; font-weight: bold; color: #2c3e50; }}
                .status-label {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔧 系統管理儀表板</h1>
                    <p>EMI 智能教學助理 - 管理員控制台</p>
                </div>
                
                <div class="status-bar">
                    <div class="status-item">
                        <div class="status-number">{data_status['real_students']}</div>
                        <div class="status-label">真實學生</div>
                    </div>
                    <div class="status-item">
                        <div class="status-number">{data_status['real_messages']}</div>
                        <div class="status-label">真實訊息</div>
                    </div>
                    <div class="status-item">
                        <div class="status-number">{'✅' if data_status['has_real_data'] else '⏳'}</div>
                        <div class="status-label">系統狀態</div>
                    </div>
                    <div class="status-item">
                        <div class="status-number">{'🟢' if line_bot_api else '🔴'}</div>
                        <div class="status-label">LINE Bot</div>
                    </div>
                </div>
                
                <div class="admin-grid">
                    <div class="admin-card primary">
                        <div class="card-icon">👥</div>
                        <div class="card-title">更新學生暱稱</div>
                        <div class="card-description">
                            自動獲取並更新所有學生的 LINE 真實暱稱，讓系統顯示如 "York" 等真實名稱而不是自動生成的 ID
                        </div>
                        <a href="/admin/update-line-names" class="card-button">🔄 立即更新暱稱</a>
                    </div>
                    
                    <div class="admin-card success">
                        <div class="card-icon">🏥</div>
                        <div class="card-title">系統健康檢查</div>
                        <div class="card-description">
                            檢查資料庫連接、LINE Bot 配置、AI 服務狀態等系統核心功能是否正常運作
                        </div>
                        <a href="/health" class="card-button">🔍 健康檢查</a>
                    </div>
                    
                    <div class="admin-card warning">
                        <div class="card-icon">📊</div>
                        <div class="card-title">學生管理</div>
                        <div class="card-description">
                            查看和管理所有學生帳號，檢視學習進度和參與統計
                        </div>
                        <a href="/students" class="card-button">👥 學生列表</a>
                    </div>
                    
                    <div class="admin-card danger">
                        <div class="card-icon">🧹</div>
                        <div class="card-title">資料庫清理</div>
                        <div class="card-description">
                            清理演示資料以確保分析結果的準確性
                        </div>
                        <a href="/admin/cleanup" class="card-button">🗑️ 清理演示資料</a>
                    </div>
                </div>
                
                <div style="text-align: center; padding: 30px;">
                    <a href="/" style="background: #6c757d; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px;">🏠 返回首頁</a>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 管理儀表板載入失敗</h1>
            <p>錯誤: {str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """, 500

@app.route('/admin/update-line-names')
def update_line_names():
    """批量更新現有學生的 LINE 暱稱"""
    try:
        if not line_bot_api:
            return """
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ LINE Bot API 未配置</h1>
                <p>無法更新學生暱稱，請檢查 LINE Bot 配置</p>
                <a href="/admin" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回管理後台</a>
            </div>
            """
        
        updated_count = 0
        failed_count = 0
        update_details = []
        
        # 找到所有需要更新的學生（真實學生但名稱是自動生成的）
        students = Student.select().where(
            (Student.name.startswith('學生_') | 
             Student.name.startswith('LINE用戶_') | 
             Student.name.startswith('用戶_')) &
            (~Student.line_user_id.startswith('demo_'))
        )
        
        for student in students:
            try:
                # 獲取 LINE 用戶資料
                profile = line_bot_api.get_profile(student.line_user_id)
                old_name = student.name
                new_name = profile.display_name or f"用戶_{student.line_user_id[-6:]}"
                
                student.name = new_name
                student.save()
                
                update_details.append(f"{old_name} → {new_name}")
                logger.info(f"✅ 更新成功: {old_name} -> {new_name}")
                updated_count += 1
                
            except LineBotApiError as e:
                logger.warning(f"⚠️ LINE API 錯誤，更新失敗 {student.line_user_id}: {e}")
                failed_count += 1
            except Exception as e:
                logger.warning(f"⚠️ 更新失敗 {student.line_user_id}: {e}")
                failed_count += 1
        
        # 生成結果頁面
        details_html = ""
        if update_details:
            details_html = f"""
            <div style="background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; margin: 20px 0; max-height: 300px; overflow-y: auto;">
                <h4>更新詳情：</h4>
                <ul style="text-align: left; margin: 0; padding-left: 20px;">
                    {"".join([f"<li>{detail}</li>" for detail in update_details[:20]])}
                    {f"<li><em>... 還有 {len(update_details) - 20} 個更新</em></li>" if len(update_details) > 20 else ""}
                </ul>
            </div>
            """
        
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>✅ LINE 暱稱更新完成</h1>
            <div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>更新結果</h3>
                <p><strong>成功更新：</strong>{updated_count} 個學生</p>
                <p><strong>更新失敗：</strong>{failed_count} 個學生</p>
                {f"<p><em>失敗原因：可能是 LINE API 權限問題或用戶已刪除 Bot</em></p>" if failed_count > 0 else ""}
            </div>
            {details_html}
            <div style="margin-top: 20px;">
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">查看學生列表</a>
                <a href="/admin" style="padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">返回管理後台</a>
            </div>
        </div>
        """
        
    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 更新失敗</h1>
            <div style="background: #ffebee; border: 1px solid #f44336; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>錯誤詳情</h3>
                <p>{str(e)}</p>
            </div>
            <a href="/admin" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回管理後台</a>
        </div>
        """

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
    """處理 LINE 訊息 - 修復版本（支援暱稱獲取）"""
    if not line_bot_api:
        logger.error("❌ LINE Bot API 未初始化")
        return
    
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        logger.info(f"🔍 收到訊息: {user_id} -> {user_message[:50]}")
        
        # 確保不是演示用戶
        if user_id.startswith('demo_'):
            logger.warning(f"跳過演示用戶訊息: {user_id}")
            return
        
        # 確保資料庫連接
        try:
            if db.is_closed():
                logger.warning("⚠️ 資料庫連接已關閉，嘗試重新連接...")
                db.connect()
                logger.info("✅ 資料庫重新連接成功")
            
            db.execute_sql('SELECT 1')
            logger.info("✅ 資料庫連接測試通過")
            
        except Exception as db_error:
            logger.error(f"❌ 資料庫連接錯誤: {db_error}")
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="System is temporarily unavailable. Please try again later. 🔧")
                )
            except:
                pass
            return
        
        # 🔧 關鍵修復：取得或創建學生記錄（包含 LINE 暱稱獲取）
        student = None
        try:
            student, created = Student.get_or_create(
                line_user_id=user_id,
                defaults={'name': f'學生_{user_id[-4:]}'}  # 臨時名稱
            )
            
            # 如果是新學生或需要更新暱稱，獲取 LINE 用戶資料
            if created or student.name.startswith('學生_') or student.name.startswith('LINE用戶_'):
                try:
                    # ✅ 關鍵修復：獲取 LINE 用戶資料
                    profile = line_bot_api.get_profile(user_id)
                    display_name = profile.display_name or f"用戶_{user_id[-4:]}"
                    
                    # 更新學生名稱為真實暱稱
                    old_name = student.name
                    student.name = display_name
                    student.save()
                    
                    logger.info(f"✅ 成功獲取用戶暱稱: {old_name} -> {display_name}")
                    
                except LineBotApiError as profile_error:
                    logger.warning(f"⚠️ LINE API 錯誤，無法獲取用戶資料: {profile_error}")
                    # 如果無法獲取暱稱，使用較友善的備用名稱
                    if student.name.startswith('學生_'):
                        student.name = f"用戶_{user_id[-6:]}"
                        student.save()
                except Exception as profile_error:
                    logger.warning(f"⚠️ 無法獲取用戶資料: {profile_error}")
                    # 如果無法獲取暱稱，保持原名稱或使用備用名稱
                    if student.name.startswith('學生_'):
                        student.name = f"用戶_{user_id[-6:]}"
                        student.save()
            
            logger.info(f"👤 學生記錄: {student.name} ({'新建' if created else '既有'})")
            
            # 確保學生名稱不是演示格式
            if student.name.startswith('[DEMO]'):
                student.name = f'用戶_{user_id[-4:]}'
                student.save()
                logger.info(f"🔄 清理演示名稱: {student.name}")
                
        except Exception as student_error:
            logger.error(f"❌ 學生記錄處理錯誤: {student_error}")
            student = None

        # 儲存訊息
        try:
            if student:
                message_record = Message.create(
                    student=student,
                    content=user_message,
                    timestamp=datetime.datetime.now(),
                    message_type='text',
                    source_type='user'
                )
                logger.info(f"💾 訊息已儲存: ID {message_record.id}")
        except Exception as msg_error:
            logger.error(f"❌ 訊息儲存錯誤: {msg_error}")
        
        # 取得 AI 回應
        logger.info("🤖 開始生成 AI 回應...")
        ai_response = None
        
        try:
            if not GEMINI_API_KEY:
                logger.error("❌ GEMINI_API_KEY 未配置")
                ai_response = "Hello! I'm currently being set up. Please try again in a moment. 👋"
            else:
                ai_response = get_ai_response(student.id if student else None, user_message)
                logger.info(f"✅ AI 回應生成成功，長度: {len(ai_response)}")
                
        except Exception as ai_error:
            logger.error(f"❌ AI 回應生成失敗: {ai_error}")
            ai_response = "I'm sorry, I'm having trouble processing your message right now. Please try again in a moment. 🤖"
        
        # 確保有回應內容
        if not ai_response or len(ai_response.strip()) == 0:
            ai_response = "Hello! I received your message. How can I help you with your English learning today? 📚"
            logger.warning("⚠️ 使用預設回應")
        
        # 更新學生統計
        if student:
            try:
                student.last_active = datetime.datetime.now()
                student.message_count += 1
                student.save()
                logger.info("📊 學生統計已更新")
            except Exception as stats_error:
                logger.error(f"⚠️ 統計更新失敗: {stats_error}")
        
        # 發送回應
        logger.info("📤 準備發送 LINE 回應...")
        try:
            if len(ai_response) > 2000:
                ai_response = ai_response[:1900] + "... (message truncated)"
                logger.warning("⚠️ 回應內容過長，已截斷")
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=ai_response)
            )
            logger.info("✅ LINE 回應發送成功")
            
        except Exception as line_error:
            logger.error(f"❌ LINE 回應發送失敗: {line_error}")
        
        logger.info(f"🎉 訊息處理完成: {user_id} ({student.name if student else 'Unknown'})")
        
    except Exception as e:
        logger.error(f"💥 處理訊息時發生嚴重錯誤: {str(e)}")
        
        try:
            if line_bot_api and hasattr(event, 'reply_token'):
                emergency_response = "System error. Please try again. 🔧"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=emergency_response)
                )
                logger.info("🚨 緊急回應已發送")
        except:
            logger.error("💥 連緊急回應都無法發送")

# =================== 其他路由 ===================

@app.route('/students')
def students():
    """學生列表頁面 - 只顯示真實學生"""
    try:
        # 只取得真實學生
        real_students = list(Student.select().where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_'))
        ).order_by(Student.last_active.desc()))
        
        return render_template_string(STUDENTS_TEMPLATE, students=real_students)
    except Exception as e:
        app.logger.error(f"學生列表錯誤: {e}")
        return render_template_string(STUDENTS_TEMPLATE, students=[])

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細頁面 - 只處理真實學生"""
    try:
        student = Student.get_by_id(student_id)
        
        # 確保不是演示學生
        if student.name.startswith('[DEMO]') or student.line_user_id.startswith('demo_'):
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>⚠️ 演示學生</h1>
                <p>這是演示學生帳號，無法查看詳細資料</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """, 403
        
        # 取得學生訊息
        messages = list(Message.select().where(
            Message.student == student
        ).order_by(Message.timestamp.desc()).limit(20))
        
        # 學習分析
        analysis = analyze_student_patterns(student_id)
        
        # 對話摘要
        conversation_summary = get_student_conversation_summary(student_id)
        
        return render_template_string(
            STUDENT_DETAIL_TEMPLATE,
            student=student,
            messages=messages,
            analysis=analysis,
            conversation_summary=conversation_summary
        )
                                 
    except Exception as e:
        logger.error(f"學生詳細頁面錯誤: {e}")
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

# =================== 健康檢查和狀態路由 ===================

@app.route('/health')
def health_check():
    """健康檢查端點 - 修復版本"""
    try:
        db_connection_ok = ensure_db_connection()
        db_status = get_db_status()
        
        try:
            if db_connection_ok:
                data_status = db_cleaner.get_real_data_status()
                db_query_ok = True
            else:
                data_status = {
                    'real_students': 0,
                    'real_messages': 0,
                    'demo_students': 0,
                    'demo_messages': 0,
                    'has_real_data': False,
                    'has_demo_data': False
                }
                db_query_ok = False
        except Exception as query_error:
            logger.error(f"資料查詢錯誤: {query_error}")
            data_status = {
                'real_students': 0,
                'real_messages': 0,
                'demo_students': 0,
                'demo_messages': 0,
                'has_real_data': False,
                'has_demo_data': False,
                'error': str(query_error)
            }
            db_query_ok = False
        
        overall_status = 'healthy' if (db_connection_ok and db_query_ok) else 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.datetime.now().isoformat(),
            'database': db_status,
            'line_bot': 'configured' if line_bot_api else 'not_configured',
            'gemini_ai': 'configured' if GEMINI_API_KEY else 'not_configured',
            'real_data_stats': data_status,
            'has_real_data': data_status['has_real_data']
        }
    except Exception as e:
        logger.error(f"健康檢查嚴重錯誤: {e}")
        return {
            'status': 'critical_error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }, 500

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
            <a href="/admin" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🔧 管理後台</a>
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（修復版本）")
    
    # 系統組件檢查
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🌐 Web 管理後台: {'可用' if WEB_TEMPLATES_AVAILABLE else '不可用'}")
    logger.info(f"📊 改進分析系統: {'已載入' if IMPROVED_ANALYTICS_AVAILABLE else '未載入'}")
    
    # 強化資料庫初始化
    logger.info("📊 初始化資料庫連接...")
    try:
        if initialize_db_with_retry():
            logger.info("✅ 資料庫初始化成功")
        else:
            logger.error("❌ 資料庫初始化失敗，但繼續啟動")
    except Exception as db_init_error:
        logger.error(f"❌ 資料庫初始化異常: {db_init_error}")
        try:
            initialize_db()
            logger.info("✅ 使用原有方法初始化資料庫成功")
        except Exception as fallback_error:
            logger.error(f"❌ 所有資料庫初始化方法都失敗: {fallback_error}")
    
    # 最終連接狀態檢查
    try:
        db_status = get_db_status()
        logger.info(f"📊 資料庫最終狀態: {db_status}")
    except Exception as status_error:
        logger.error(f"❌ 無法檢查資料庫狀態: {status_error}")
    
    # LINE Bot 配置詳細檢查
    if line_bot_api and handler:
        logger.info("✅ LINE Bot 完全配置完成")
        logger.info("📞 Webhook URL: https://web-production-c8b8.up.railway.app/callback")
    else:
        logger.warning("⚠️ LINE Bot 配置不完整")
        if not CHANNEL_ACCESS_TOKEN:
            logger.error("❌ CHANNEL_ACCESS_TOKEN 未設定")
        if not CHANNEL_SECRET:
            logger.error("❌ CHANNEL_SECRET 未設定")
    
    # Gemini AI 配置詳細檢查
    if GEMINI_API_KEY:
        logger.info("✅ Gemini AI API 金鑰已設定")
        try:
            from utils import model
            if model:
                logger.info("✅ Gemini 模型初始化成功")
            else:
                logger.warning("⚠️ Gemini 模型初始化失敗，但 API 金鑰存在")
        except Exception as model_check_error:
            logger.error(f"❌ Gemini 模型檢查失敗: {model_check_error}")
    else:
        logger.error("❌ GEMINI_API_KEY 未設定")
    
    logger.info("🔧 主要 API 端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - LINE Bot Webhook: /callback")
    logger.info("   - 管理員後台: /admin")
    logger.info("   - 更新學生暱稱: /admin/update-line-names")
    
    logger.info("✅ 修復增強功能:")
    logger.info("   ✅ 修復語法錯誤和重複 try 區塊")
    logger.info("   ✅ 添加 LINE 用戶暱稱自動獲取功能")
    logger.info("   ✅ 管理員儀表板和批量更新功能")
    logger.info("   ✅ 強化錯誤處理和日誌記錄")
    logger.info("   ✅ 系統健康狀態監控")
    
    logger.info(f"🔗 啟動參數: Port={port}, Debug={debug}")
    logger.info("🎉 系統修復完成，準備處理請求...")
    
    try:
        app.run(
            debug=debug,
            host='0.0.0.0',
            port=port
        )
    except Exception as startup_error:
        logger.error(f"💥 應用程式啟動失敗: {startup_error}")
        raise

# WSGI 應用程式入口點（用於 Railway 生產環境）
application = app

# 生產環境啟動檢查（當由 Gunicorn 啟動時執行）
if __name__ != '__main__':
    logger.info("🚀 生產環境啟動檢查...")
    
    # 檢查關鍵環境變數
    config_issues = []
    if not CHANNEL_ACCESS_TOKEN:
        config_issues.append("CHANNEL_ACCESS_TOKEN 未設定")
    if not CHANNEL_SECRET:
        config_issues.append("CHANNEL_SECRET 未設定")
    if not GEMINI_API_KEY:
        config_issues.append("GEMINI_API_KEY 未設定")
    
    if config_issues:
        logger.error("❌ 生產環境配置問題:")
        for issue in config_issues:
            logger.error(f"   - {issue}")
    else:
        logger.info("✅ 生產環境配置檢查通過")
    
    # 生產環境資料庫初始化
    try:
        if not initialize_db_with_retry():
            logger.error("❌ 生產環境資料庫初始化失敗")
        else:
            logger.info("✅ 生產環境資料庫初始化成功")
    except Exception as prod_db_error:
        logger.error(f"❌ 生產環境資料庫初始化異常: {prod_db_error}")
    
    logger.info("🎯 生產環境準備完成")
