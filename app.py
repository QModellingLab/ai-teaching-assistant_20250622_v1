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

@app.route('/teaching-insights')
def teaching_insights():
    """教師分析後台 - 使用改進的真實資料分析"""
    try:
        if IMPROVED_ANALYTICS_AVAILABLE:
            insights_data = get_improved_teaching_insights()
            
            # 檢查是否有真實資料
            if not insights_data.get('has_real_data', False):
                # 顯示等待狀態頁面
                return render_template_string(
                    TEACHING_INSIGHTS_TEMPLATE,
                    category_stats={'total_questions': 0},
                    engagement_analysis={'total_real_students': 0, 'status': 'waiting_for_data'},
                    students=[],
                    stats=insights_data['stats'],
                    real_data_info={'has_real_data': False},
                    current_time=datetime.datetime.now()
                )
            
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
            # 基本的真實資料檢查
            data_status = db_cleaner.get_real_data_status()
            if not data_status['has_real_data']:
                return f"""
                <div style="font-family: sans-serif; padding: 40px; text-align: center; background: #f8f9fa;">
                    <h1>📊 教師分析後台</h1>
                    <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 30px; margin: 30px 0; border-radius: 10px;">
                        <h3>⏳ 等待真實學生資料</h3>
                        <p>目前有 <strong>{data_status['real_students']}</strong> 位真實學生，<strong>{data_status['real_messages']}</strong> 則真實對話</p>
                        <p>當學生開始使用 LINE Bot 對話時，分析功能將自動啟用</p>
                        <div style="margin-top: 20px;">
                            <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">返回首頁</a>
                            <a href="/admin/cleanup" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">清理演示資料</a>
                        </div>
                    </div>
                </div>
                """
            
            return f"""
            <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>❌ 改進分析模組未載入</h1>
                <p>教師分析後台需要改進的真實資料分析模組</p>
                <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
            </div>
            """
            
    except Exception as e:
        logger.error(f"Teaching insights error: {e}")
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ 教師分析後台載入失敗</h1>
            <p>錯誤: {str(e)}</p>
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

# =================== 管理員功能路由 ===================

@app.route('/admin/cleanup')
def admin_cleanup_page():
    """管理員清理頁面"""
    try:
        data_status = db_cleaner.get_real_data_status()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>🧹 資料庫清理 - EMI 管理後台</title>
            <style>
                body {{ font-family: sans-serif; background: #f8f9fa; margin: 0; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .status-card {{ background: #e3f2fd; border: 1px solid #2196f3; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .danger-zone {{ background: #ffebee; border: 1px solid #f44336; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .btn {{ padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }}
                .btn-danger {{ background: #f44336; color: white; }}
                .btn-primary {{ background: #2196f3; color: white; }}
                .btn-success {{ background: #4caf50; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🧹 資料庫清理管理</h1>
                
                <div class="status-card">
                    <h3>📊 當前資料狀態</h3>
                    <p><strong>真實學生:</strong> {data_status['real_students']} 位</p>
                    <p><strong>真實訊息:</strong> {data_status['real_messages']} 則</p>
                    <p><strong>演示學生:</strong> {data_status['demo_students']} 位</p>
                    <p><strong>演示訊息:</strong> {data_status['demo_messages']} 則</p>
                </div>
                
                {'<div class="danger-zone"><h3>⚠️ 發現演示資料</h3><p>資料庫中仍有演示資料，建議清理以確保分析結果的準確性。</p></div>' if data_status['has_demo_data'] else '<div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; border-radius: 8px; margin: 20px 0;"><h3>✅ 資料庫已清潔</h3><p>沒有發現演示資料，資料庫處於純淨狀態。</p></div>'}
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/admin/cleanup/execute" class="btn btn-danger" onclick="return confirm('確定要清理所有演示資料嗎？此操作無法復原！')">
                        🗑️ 清理演示資料
                    </a>
                    <a href="/admin/data-status" class="btn btn-primary">
                        📊 查看詳細狀態
                    </a>
                    <a href="/" class="btn btn-success">
                        🏠 返回首頁
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"清理頁面載入錯誤: {str(e)}", 500

@app.route('/admin/cleanup/execute')
def admin_cleanup_execute():
    """執行清理操作"""
    try:
        result = db_cleaner.clean_demo_data()
        
        if result['success']:
            return f"""
            <div style="font-family: sans-serif; padding: 40px; text-align: center; background: #f8f9fa;">
                <h1>✅ 清理完成</h1>
                <div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>清理結果</h3>
                    <p>{result['message']}</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>刪除學生: {result['stats']['students_deleted']} 位</li>
                        <li>刪除訊息: {result['stats']['messages_deleted']} 則</li>
                        <li>刪除分析: {result['stats']['analyses_deleted']} 個</li>
                        <li>刪除AI回應: {result['stats']['ai_responses_deleted']} 個</li>
                    </ul>
                </div>
                <div style="margin-top: 30px;">
                    <a href="/" style="background: #4caf50; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
                    <a href="/health" style="background: #2196f3; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">🔧 檢查系統狀態</a>
                </div>
            </div>
            """
        else:
            return f"""
            <div style="font-family: sans-serif; padding: 40px; text-align: center; background: #f8f9fa;">
                <h1>❌ 清理失敗</h1>
                <div style="background: #ffebee; border: 1px solid #f44336; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>錯誤詳情</h3>
                    <p>{result['message']}</p>
                </div>
                <div style="margin-top: 30px;">
                    <a href="/admin/cleanup" style="background: #f44336; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">🔄 重試清理</a>
                    <a href="/" style="background: #2196f3; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">🏠 返回首頁</a>
                </div>
            </div>
            """
    except Exception as e:
        logger.error(f"執行清理錯誤: {e}")
        return f"清理執行錯誤: {str(e)}", 500

@app.route('/admin/data-status')
def admin_data_status():
    """資料狀態詳情"""
    try:
        data_status = db_cleaner.get_real_data_status()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>📊 資料狀態 - EMI 管理後台</title>
            <style>
                body {{ font-family: sans-serif; background: #f8f9fa; margin: 0; padding: 20px; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .status-card {{ background: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; border-radius: 8px; text-align: center; }}
                .status-number {{ font-size: 2em; font-weight: bold; color: #2196f3; }}
                .status-label {{ color: #666; margin-top: 5px; }}
                .real-data {{ border-left: 4px solid #4caf50; }}
                .demo-data {{ border-left: 4px solid #f44336; }}
                .btn {{ padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }}
                .btn-primary {{ background: #2196f3; color: white; }}
                .btn-success {{ background: #4caf50; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 資料庫狀態詳情</h1>
                
                <h3>🎯 真實資料統計</h3>
                <div class="status-grid">
                    <div class="status-card real-data">
                        <div class="status-number">{data_status['real_students']}</div>
                        <div class="status-label">真實學生</div>
                    </div>
                    <div class="status-card real-data">
                        <div class="status-number">{data_status['real_messages']}</div>
                        <div class="status-label">真實訊息</div>
                    </div>
                </div>
                
                <h3>🧹 演示資料統計</h3>
                <div class="status-grid">
                    <div class="status-card demo-data">
                        <div class="status-number">{data_status['demo_students']}</div>
                        <div class="status-label">演示學生</div>
                    </div>
                    <div class="status-card demo-data">
                        <div class="status-number">{data_status['demo_messages']}</div>
                        <div class="status-label">演示訊息</div>
                    </div>
                </div>
                
                <h3>🎯 系統狀態</h3>
                <div style="background: {'#e8f5e8' if data_status['has_real_data'] else '#fff3cd'}; border: 1px solid {'#4caf50' if data_status['has_real_data'] else '#ffc107'}; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>資料可用性:</strong> {'✅ 有真實資料可供分析' if data_status['has_real_data'] else '⏳ 等待真實學生開始使用'}</p>
                    <p><strong>清理需求:</strong> {'⚠️ 建議清理演示資料' if data_status['has_demo_data'] else '✅ 資料庫已清潔'}</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/admin/cleanup" class="btn btn-primary">🧹 資料清理</a>
                    <a href="/" class="btn btn-success">🏠 返回首頁</a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"狀態頁面載入錯誤: {str(e)}", 500

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
            data_status = db_cleaner.get_real_data_status()
            return jsonify({
                'success': True,
                'stats': {
                    'total_students': data_status['real_students'],
                    'real_students': data_status['real_students'],
                    'total_messages': data_status['real_messages'],
                    'avg_participation': 0
                },
                'has_real_data': data_status['has_real_data'],
                'data_source': 'basic_real_data_check'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'has_real_data': False
        }), 500

@app.route('/api/student-analysis/<int:student_id>')
def student_analysis_api(student_id):
    """學生分析 API - 只分析真實學生"""
    try:
        student = Student.get_by_id(student_id)
        
        # 確保不是演示學生
        if student.name.startswith('[DEMO]') or student.line_user_id.startswith('demo_'):
            return jsonify({
                'success': False, 
                'error': 'Demo student analysis not available'
            }), 403
        
        analysis = analyze_student_patterns(student_id)
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/class-statistics')
def class_statistics_api():
    """班級統計 API - 只統計真實學生"""
    try:
        data_status = db_cleaner.get_real_data_status()
        
        stats = {
            'total_students': data_status['real_students'],
            'total_messages': data_status['real_messages'],
            'active_students_today': 0,  # 可以加入更詳細的計算
            'avg_messages_per_student': 0,
            'common_question_types': ['文法', '詞彙', '發音']
        }
        
        if stats['total_students'] > 0:
            stats['avg_messages_per_student'] = stats['total_messages'] / stats['total_students']
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cleanup/status')
def cleanup_status_api():
    """清理狀態 API"""
    try:
        data_status = db_cleaner.get_real_data_status()
        return jsonify({
            'success': True,
            'data_status': data_status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cleanup/execute', methods=['POST'])
def cleanup_execute_api():
    """執行清理 API"""
    try:
        result = db_cleaner.clean_demo_data()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =================== 匯出相關 API 路由 ===================

@app.route('/api/export/<export_type>')
def export_data_api(export_type):
    """資料匯出 API - 只匯出真實資料"""
    try:
        export_format = request.args.get('format', 'json')
        date_range = request.args.get('date_range', None)
        
        # 只匯出真實學生資料
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{export_type}_real_data_{timestamp}.{export_format}'
        
        # 收集真實資料
        real_students = list(Student.select().where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_'))
        ))
        
        real_messages = list(Message.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_')) &
            (Message.source_type != 'demo')
        ))
        
        export_data = {
            'export_info': {
                'type': export_type,
                'timestamp': timestamp,
                'format': export_format,
                'real_data_only': True
            },
            'students': len(real_students),
            'messages': len(real_messages),
            'data': f'Real data export for {export_type}'
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
            'format': export_format,
            'real_data_only': True
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
    """處理 LINE 訊息 - 只處理真實學生"""
    if not line_bot_api:
        return
    
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        
        # 確保不是演示用戶
        if user_id.startswith('demo_'):
            logger.warning(f"跳過演示用戶訊息: {user_id}")
            return
        
        # 取得或創建學生記錄
        student, created = Student.get_or_create(
            line_user_id=user_id,
            defaults={'name': f'學生_{user_id[-4:]}'}
        )
        
        # 確保學生名稱不是演示格式
        if student.name.startswith('[DEMO]'):
            student.name = f'學生_{user_id[-4:]}'
            student.save()
        
        # 儲存訊息
        message_record = Message.create(
            student=student,
            content=user_message,
            timestamp=datetime.datetime.now(),
            message_type='text',
            source_type='user'  # 確保不是 'demo'
        )
        
        # 取得 AI 回應
        ai_response = get_ai_response(user_message, student.id)
        
        # 更新學生統計
        update_student_stats(student.id)
        
        # 發送回應
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
        logger.info(f"處理真實學生訊息成功: {user_id} -> {user_message[:50]}")
        
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
    """健康檢查端點 - 真實資料版本"""
    try:
        db_status = 'connected' if not db.is_closed() else 'disconnected'
        
        try:
            data_status = db_cleaner.get_real_data_status()
            db_query_ok = True
        except Exception:
            data_status = {
                'real_students': 0,
                'real_messages': 0,
                'demo_students': 0,
                'demo_messages': 0,
                'has_real_data': False,
                'has_demo_data': False
            }
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
            'real_data_stats': data_status,
            'has_real_data': data_status['has_real_data'],
            'data_cleanliness': 'clean' if not data_status['has_demo_data'] else 'has_demo_data'
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
                <div style="margin-top: 20px;">
                    <a href="/teaching-insights" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">返回分析後台</a>
                    <a href="/admin/cleanup" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">清理演示資料</a>
                </div>
            </div>
            """)
        else:
            data_status = db_cleaner.get_real_data_status()
            return f"""
            <div style="font-family: sans-serif; padding: 20px;">
                <h1>📊 真實資料狀態報告</h1>
                <div style="background: {'#e7f3ff' if data_status['has_real_data'] else '#fff3cd'}; padding: 15px; margin: 15px 0; border-radius: 5px;">
                    <h3>{'✅' if data_status['has_real_data'] else '⏳'} 資料狀態：{'有真實資料' if data_status['has_real_data'] else '等待真實資料'}</h3>
                    <p><strong>真實學生數：</strong>{data_status['real_students']}</p>
                    <p><strong>真實訊息數：</strong>{data_status['real_messages']}</p>
                    <p><strong>演示學生數：</strong>{data_status['demo_students']}</p>
                    <p><strong>演示訊息數：</strong>{data_status['demo_messages']}</p>
                </div>
                <div style="margin-top: 20px;">
                    <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">返回首頁</a>
                    <a href="/admin/cleanup" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">清理演示資料</a>
                </div>
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
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（真實資料版）")
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🌐 Web 管理後台: {'可用' if WEB_TEMPLATES_AVAILABLE else '不可用'}")
    logger.info(f"📊 改進分析系統: {'已載入' if IMPROVED_ANALYTICS_AVAILABLE else '未載入'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🎯 資料處理: 只分析真實學生資料")
    logger.info(f"🔗 Port: {port}, Debug: {debug}")
    
    if WEB_TEMPLATES_AVAILABLE:
        logger.info("📊 Web 管理後台路由:")
        logger.info("   - 首頁: / （支援等待狀態）")
        logger.info("   - 學生管理: /students （只顯示真實學生）")
        logger.info("   - 教師洞察: /teaching-insights （真實資料分析）")
        logger.info("   - 對話摘要: /conversation-summaries")
        logger.info("   - 學習建議: /learning-recommendations")
        logger.info("   - 儲存管理: /storage-management")
    
    logger.info("🔧 API 端點:")
    logger.info("   - 健康檢查: /health")
    logger.info("   - 真實資料狀態: /real-data-status")
    logger.info("   - 儀表板統計: /api/dashboard-stats （支援真實資料檢測）")
    logger.info("   - 資料匯出: /api/export/<type> （只匯出真實資料）")
    logger.info("   - 檔案下載: /download/<filename>")
    logger.info("   - 學生分析: /api/student-analysis/<id> （只分析真實學生）")
    logger.info("   - 班級統計: /api/class-statistics （只統計真實學生）")
    logger.info("   - LINE Bot Webhook: /callback")
    
    logger.info("🧹 管理功能:")
    logger.info("   - 清理頁面: /admin/cleanup")
    logger.info("   - 執行清理: /admin/cleanup/execute")
    logger.info("   - 資料狀態: /admin/data-status")
    logger.info("   - 清理狀態API: /api/cleanup/status")
    logger.info("   - 執行清理API: /api/cleanup/execute")
    
    logger.info("✅ 重要改進：")
    logger.info("   ✅ 移除演示資料：系統只處理真實學生資料")
    logger.info("   ✅ 增強對話記憶：30輪對話，24小時記憶")
    logger.info("   ✅ 資料庫清理：提供完整的演示資料清理功能")
    logger.info("   ✅ 管理後台：新增管理員清理介面")
    logger.info("   ✅ 真實資料檢測：自動檢測並顯示適當介面")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )

# WSGI 應用程式入口點
application = app
