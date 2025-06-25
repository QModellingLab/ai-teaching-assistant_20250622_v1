# app.py - EMI智能記憶系統優化版本（英文摘要+完整顯示+增強健康檢查）
# 將對話記憶從3次提升到8次，新增學習檔案系統功能

import os
import json
import datetime
import logging
import csv
import zipfile
import time
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
    get_student_conversation_summary,
    AVAILABLE_MODELS,
    get_quota_status,
    test_ai_connection,
    model_usage_stats
)

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

# =================== 增強記憶管理功能 ===================

def get_enhanced_conversation_context(student_id, limit=8):
    """
    獲取增強的對話上下文（從3次提升到8次）
    包含更智慧的內容篩選和格式化
    """
    try:
        if not student_id:
            return ""
        
        # 獲取最近8次對話記錄
        recent_messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(limit))
        
        if not recent_messages:
            return ""
        
        # 反轉順序以時間正序排列
        recent_messages.reverse()
        
        # 構建上下文字串，包含更多元資訊
        context_parts = []
        for i, msg in enumerate(recent_messages, 1):
            # 格式化時間
            time_str = msg.timestamp.strftime("%H:%M") if msg.timestamp else ""
            
            # 判斷訊息類型並加上標記
            if msg.message_type == 'question':
                type_marker = "❓"
            elif '?' in msg.content:
                type_marker = "❓" 
            else:
                type_marker = "💬"
            
            # 限制單條訊息長度以控制token用量
            content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            
            context_parts.append(f"{type_marker} [{time_str}] {content}")
        
        # 組合上下文，包含統計資訊
        context_header = f"Recent conversation history ({len(recent_messages)} messages):"
        context_body = "\n".join(context_parts)
        
        full_context = f"{context_header}\n{context_body}"
        
        # 確保總長度合理（約1000字符以內）
        if len(full_context) > 1000:
            # 如果太長，保留最近的5條
            recent_5 = context_parts[-5:]
            full_context = f"Recent conversation history (5 most recent):\n" + "\n".join(recent_5)
        
        logger.info(f"📝 已獲取學生 {student_id} 的對話上下文，共 {len(recent_messages)} 條記錄")
        return full_context
        
    except Exception as e:
        logger.error(f"❌ 獲取對話上下文錯誤: {e}")
        return ""

def get_student_learning_context(student_id):
    """
    獲取學生學習背景資訊，增強AI回應的個人化程度
    """
    try:
        student = Student.get_by_id(student_id)
        
        # 基本資訊
        context_parts = [f"Student: {student.name}"]
        
        # 學習偏好
        if hasattr(student, 'language_preference') and student.language_preference:
            if student.language_preference == 'english':
                context_parts.append("Prefers English responses")
            elif student.language_preference == 'chinese':
                context_parts.append("Prefers Chinese explanations")
            else:
                context_parts.append("Uses mixed language (English/Chinese)")
        
        # 參與度資訊
        if student.participation_rate > 80:
            context_parts.append("Highly engaged student")
        elif student.participation_rate > 50:
            context_parts.append("Moderately active student")
        else:
            context_parts.append("Developing engagement")
        
        # 學習風格
        if hasattr(student, 'learning_style') and student.learning_style:
            context_parts.append(f"Learning style: {student.learning_style}")
        
        # 興趣領域
        if hasattr(student, 'interest_areas') and student.interest_areas:
            context_parts.append(f"Interests: {student.interest_areas[:100]}")
        
        return "; ".join(context_parts)
        
    except Exception as e:
        logger.error(f"❌ 獲取學生學習背景錯誤: {e}")
        return ""

# =================== 學習檔案系統功能（修改為英文生成） ===================

def generate_student_learning_summary(student_id, conversation_level='standard', target_length=500):
    """
    生成學生學習摘要 - 修改為英文生成版本
    解決簡體中文問題，直接用英文提供學術標準的摘要
    完全移除截斷限制，確保完整內容顯示
    """
    try:
        student = Student.get_by_id(student_id)
        
        # 獲取學生所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.asc()))
        
        if not messages:
            return {
                'summary': 'No conversation data available for analysis.',
                'message_count': 0,
                'error': 'No data',
                'generated_at': datetime.datetime.now().isoformat(),
                'language': 'english'
            }
        
        message_count = len(messages)
        
        # 分類訊息類型
        questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content]
        statements = [msg for msg in messages if msg not in questions]
        
        # 提取學習主題（分析訊息內容中的關鍵詞）
        topics = []
        for msg in messages[-10:]:  # 分析最近10則訊息
            content_lower = msg.content.lower()
            # 英語學習相關主題識別
            if any(word in content_lower for word in ['grammar', 'tense', 'verb', 'noun', 'adjective']):
                topics.append('Grammar')
            if any(word in content_lower for word in ['vocabulary', 'word', 'meaning', 'definition']):
                topics.append('Vocabulary')
            if any(word in content_lower for word in ['pronunciation', 'sound', 'accent', 'speak']):
                topics.append('Pronunciation')
            if any(word in content_lower for word in ['writing', 'essay', 'paragraph', 'composition']):
                topics.append('Writing')
            if any(word in content_lower for word in ['reading', 'comprehension', 'text', 'article']):
                topics.append('Reading')
            if any(word in content_lower for word in ['conversation', 'dialogue', 'speaking', 'communication']):
                topics.append('Conversation')
        
        topics = list(set(topics))  # 去除重複
        
        # 構建英文摘要 prompt - 改為完全使用英文
        summary_type = 'comprehensive' if conversation_level == 'detailed' else 'standard'
        
        # 修改：prompt 改為英文，確保 AI 用英文回應
        summary_prompt = f"""As an EMI (English-Medium Instruction) educational analyst, please generate a comprehensive learning summary for this student in English.

Student Information:
- Name: {student.name}
- Total Messages: {message_count}
- Questions Asked: {len(questions)}
- Statements Made: {len(statements)}
- Participation Rate: {student.participation_rate}%
- Learning Topics Identified: {', '.join(topics) if topics else 'General English learning'}

Please provide an English learning summary that includes:

**🎯 Learning Focus Areas:**
[Key subjects and skills the student has been working on]

**📈 Progress Assessment:**
[Student's current level and improvement areas observed]

**💡 Learning Patterns:**
[How this student typically engages with language learning]

**🔍 Recommendations:**
[Specific suggestions for continued learning and growth]

**📊 Engagement Summary:**
[Overall participation and interaction quality]

Please write in clear, professional English suitable for EMI instructors. Provide a comprehensive analysis without length restrictions - include all relevant insights and observations about this student's learning journey."""

        # 使用 AI 生成英文摘要
        try:
            ai_response = get_ai_response(student_id, summary_prompt, "", "")
            
            # 處理 AI 回應
            if ai_response and len(ai_response.strip()) > 50:
                full_summary = ai_response.strip()
            else:
                raise Exception("AI response was insufficient")
                
        except Exception as ai_error:
            logger.warning(f"⚠️ AI 摘要生成失敗，使用備用摘要: {ai_error}")
            
            # 如果 AI 回應失敗，提供英文備用摘要
            full_summary = f"""**Learning Summary for {student.name}**

**🎯 Learning Focus Areas:**
This student has engaged in {message_count} interactions, with {len(questions)} questions and {len(statements)} statements. Primary focus areas include: {', '.join(topics) if topics else 'general English communication skills'}.

**📈 Progress Assessment:**
The student shows a participation rate of {student.participation_rate}%, indicating {'high engagement' if student.participation_rate > 70 else 'moderate engagement' if student.participation_rate > 40 else 'developing engagement'} with the learning process.

**💡 Learning Patterns:**
{'Question-oriented learning style' if len(questions) > len(statements) else 'Statement-based communication style'}, showing {'active inquiry' if len(questions) > 5 else 'steady participation'} in educational interactions.

**🔍 Recommendations:**
Continue encouraging {'this questioning approach' if len(questions) > len(statements) else 'more interactive questioning'} to enhance learning outcomes. Focus on {'maintaining current engagement levels' if student.participation_rate > 70 else 'increasing participation frequency'}.

**📊 Engagement Summary:**
Overall learning engagement is {'excellent' if student.participation_rate > 80 else 'good' if student.participation_rate > 60 else 'satisfactory'} with consistent interaction patterns over the learning period."""
        
        # 完全移除截斷邏輯，返回完整摘要
        return {
            'summary': full_summary,  # 完整摘要，絕不截斷
            'message_count': message_count,
            'question_count': len(questions),
            'statement_count': len(statements),
            'summary_type': summary_type,
            'actual_length': len(full_summary),
            'topics': topics[:5],  # 最多顯示5個主題
            'participation_rate': student.participation_rate,
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',  # 標記為英文摘要
            'truncated': False,  # 明確標記未被截斷
            'complete': True  # 標記為完整摘要
        }
        
    except Exception as e:
        logger.error(f"❌ 生成英文學習摘要錯誤: {e}")
        return {
            'summary': f'Error generating learning summary: {str(e)}',
            'message_count': 0,
            'error': str(e),
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english'
        }

# =================== 網頁後台路由 ===================

@app.route('/')
def home():
    """首頁"""
    return """
    <div style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>📚 EMI智能教學助理</h1>
        <h2>🧠 增強記憶系統 (8次對話記憶)</h2>
        <p>LINE Bot + Gemini AI + 智能學習檔案系統</p>
        <div style="margin-top: 30px;">
            <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">👥 學生列表</a>
            <a href="/admin" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">⚙️ 管理後台</a>
            <a href="/health" style="padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏥 系統檢查</a>
        </div>
        <div style="margin-top: 20px; color: #666;">
            <p>✨ 新功能：8次對話記憶 | 英文學習摘要 | 完整檔案匯出 | 增強健康檢查</p>
        </div>
    </div>
    """

@app.route('/admin')
def admin():
    """管理後台"""
    try:
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        active_students = Student.select().where(
            Student.last_active > (datetime.datetime.now() - datetime.timedelta(days=7))
        ).count()
        
        return f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h1>⚙️ EMI智能教學助理 - 管理後台</h1>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center;">
                    <h2>{total_students}</h2>
                    <p>總學生數</p>
                </div>
                <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; text-align: center;">
                    <h2>{active_students}</h2>
                    <p>活躍學生</p>
                </div>
                <div style="background: #fff3e0; padding: 20px; border-radius: 8px; text-align: center;">
                    <h2>{total_messages}</h2>
                    <p>總對話數</p>
                </div>
            </div>
            
            <div style="margin: 20px 0;">
                <h3>📋 管理功能</h3>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">👥 學生列表</a>
                <a href="/students/export" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">📊 匯出資料</a>
                <a href="/health" style="padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">🏥 系統檢查</a>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px;">
                <h4>✨ 系統功能摘要：</h4>
                <ul>
                    <li>✅ 對話記憶從3次提升到8次</li>
                    <li>✅ 學習摘要改為專業英文生成</li>
                    <li>✅ 完整摘要顯示，移除截斷限制</li>
                    <li>✅ 增強系統健康檢查與AI模型監控</li>
                    <li>✅ 學生列表頁面與搜尋功能</li>
                    <li>✅ 個人學習檔案詳情頁</li>
                    <li>✅ TSV/TXT格式匯出功能</li>
                    <li>✅ 智能話題識別與分類</li>
                </ul>
            </div>
        </div>
        """
        
    except Exception as e:
        return f"管理後台載入失敗: {str(e)}", 500

# =================== 增強的系統健康檢查 ===================

@app.route('/health')
def health_check():
    """增強的系統健康檢查 - 包含 AI 模型詳細狀態"""
    try:
        # 計算系統運行時間
        try:
            import psutil
            boot_time = psutil.boot_time()
            current_time = time.time()
            uptime_seconds = current_time - boot_time
            uptime_hours = int(uptime_seconds // 3600)
        except ImportError:
            # 如果 psutil 不可用，使用簡單估算
            uptime_hours = "N/A"
        
        # 基本系統檢查
        try:
            # 測試資料庫連接
            if hasattr(db, 'connect'):
                db.connect(reuse_if_open=True)
            student_count = Student.select().count()
            message_count = Message.select().count()
            db_status = "正常"
        except Exception as db_error:
            db_status = f"錯誤: {str(db_error)[:50]}"
            student_count = 0
            message_count = 0
        
        # LINE Bot 狀態檢查
        line_status = "已配置" if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else "未配置"
        
        # AI 連接測試
        ai_connection_ok, ai_connection_msg = test_ai_connection()
        ai_status = "已配置" if GEMINI_API_KEY else "未配置"
        
        # 獲取模型配額狀態
        quota_status = get_quota_status()
        
        # 計算總 API 調用次數和成功率
        total_calls = sum(stats['calls'] for stats in model_usage_stats.values())
        total_errors = sum(stats['errors'] for stats in model_usage_stats.values())
        success_rate = ((total_calls - total_errors) / max(total_calls, 1)) * 100
        
        # 獲取最後模型切換時間
        last_switch_times = [stats['last_used'] for stats in model_usage_stats.values() if stats['last_used']]
        last_switch_time = max(last_switch_times) if last_switch_times else None
        last_switch_str = datetime.datetime.fromtimestamp(last_switch_time).strftime('%Y-%m-%d %H:%M') if last_switch_time else "從未切換"
        
        # 嘗試從 teaching_analytics 獲取狀態
        try:
            from teaching_analytics import get_analytics_status
            analytics_status = get_analytics_status()
        except ImportError:
            analytics_status = {
                'current_model': 'N/A',
                'model_switches': 0,
                'system_status': 'unknown'
            }
        
        # 生成詳細的健康檢查報告 HTML
        health_html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>EMI 智能教學助理 - 系統健康檢查</title>
            <style>
                body {{ 
                    font-family: 'Microsoft JhengHei', sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{ 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 12px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
                    overflow: hidden;
                }}
                .header {{ 
                    background: #2c3e50; 
                    color: white; 
                    padding: 30px; 
                    text-align: center;
                }}
                .header h1 {{ 
                    margin: 0 0 10px 0; 
                    font-size: 2.5em; 
                    font-weight: 300;
                }}
                .header p {{ 
                    margin: 0; 
                    opacity: 0.9;
                }}
                .nav-bar {{
                    background: #34495e;
                    padding: 15px 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .nav-links a {{
                    color: white;
                    text-decoration: none;
                    margin-right: 20px;
                    padding: 8px 16px;
                    border-radius: 4px;
                    transition: background-color 0.3s;
                }}
                .nav-links a:hover {{
                    background-color: rgba(255,255,255,0.1);
                }}
                .content {{ 
                    padding: 30px; 
                }}
                .status-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                    gap: 20px; 
                    margin: 20px 0;
                }}
                .status-card {{ 
                    background: #f8f9fa; 
                    border-radius: 8px; 
                    padding: 20px; 
                    border-left: 4px solid #3498db;
                }}
                .status-card.success {{ border-left-color: #27ae60; }}
                .status-card.warning {{ border-left-color: #f39c12; }}
                .status-card.error {{ border-left-color: #e74c3c; }}
                .status-title {{ 
                    font-size: 1.2em; 
                    font-weight: bold; 
                    margin-bottom: 10px; 
                    color: #2c3e50;
                }}
                .status-item {{ 
                    margin: 8px 0; 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center;
                }}
                .status-value {{ 
                    font-weight: bold; 
                }}
                .status-value.ok {{ color: #27ae60; }}
                .status-value.warning {{ color: #f39c12; }}
                .status-value.error {{ color: #e74c3c; }}
                .model-list {{ 
                    background: #f8f9fa; 
                    border-radius: 8px; 
                    padding: 20px; 
                    margin: 20px 0;
                    border: 1px solid #e9ecef;
                }}
                .model-item {{ 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    padding: 12px 0; 
                    border-bottom: 1px solid #e9ecef;
                }}
                .model-item:last-child {{ border-bottom: none; }}
                .model-name {{ 
                    font-weight: bold; 
                    color: #2c3e50;
                }}
                .model-status {{ 
                    display: flex; 
                    align-items: center; 
                    gap: 10px;
                }}
                .badge {{ 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    font-size: 0.8em; 
                    font-weight: bold;
                }}
                .badge.available {{ background: #d4edda; color: #155724; }}
                .badge.warning {{ background: #fff3cd; color: #856404; }}
                .badge.unavailable {{ background: #f8d7da; color: #721c24; }}
                .badge.current {{ background: #cce5ff; color: #004085; }}
                .progress-bar {{ 
                    width: 100px; 
                    height: 8px; 
                    background: #e9ecef; 
                    border-radius: 4px; 
                    overflow: hidden;
                }}
                .progress-fill {{ 
                    height: 100%; 
                    transition: width 0.3s ease;
                }}
                .progress-fill.low {{ background: #28a745; }}
                .progress-fill.medium {{ background: #ffc107; }}
                .progress-fill.high {{ background: #dc3545; }}
                .refresh-btn {{
                    background: #007bff;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                    transition: background-color 0.3s;
                    display: inline-block;
                    margin-top: 20px;
                }}
                .refresh-btn:hover {{
                    background: #0056b3;
                }}
                .timestamp {{
                    text-align: center;
                    color: #6c757d;
                    font-size: 0.9em;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e9ecef;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- 頁面標題 -->
                <div class="header">
                    <h1>🏥 系統健康檢查</h1>
                    <p>EMI 智能教學助理 - 系統狀態監控儀表板</p>
                </div>
                
                <!-- 導航欄 -->
                <div class="nav-bar">
                    <div class="nav-links">
                        <a href="/">🏠 首頁</a>
                        <a href="/students">👥 學生列表</a>
                        <a href="/admin">⚙️ 管理後台</a>
                    </div>
                    <a href="/health" class="refresh-btn">🔄 重新整理</a>
                </div>
                
                <div class="content">
                    <!-- 基本系統狀態 -->
                    <h2>📊 基本系統狀態</h2>
                    <div class="status-grid">
                        <div class="status-card {'success' if db_status == '正常' else 'error'}">
                            <div class="status-title">🗄️ 資料庫連接</div>
                            <div class="status-item">
                                <span>狀態:</span>
                                <span class="status-value {'ok' if db_status == '正常' else 'error'}">{db_status} {'✅' if db_status == '正常' else '❌'}</span>
                            </div>
                            <div class="status-item">
                                <span>學生總數:</span>
                                <span class="status-value">{student_count:,}</span>
                            </div>
                            <div class="status-item">
                                <span>訊息總數:</span>
                                <span class="status-value">{message_count:,}</span>
                            </div>
                        </div>
                        
                        <div class="status-card {'success' if line_status == '已配置' else 'warning'}">
                            <div class="status-title">📱 LINE Bot API</div>
                            <div class="status-item">
                                <span>配置狀態:</span>
                                <span class="status-value {'ok' if line_status == '已配置' else 'warning'}">{line_status} {'✅' if line_status == '已配置' else '⚠️'}</span>
                            </div>
                            <div class="status-item">
                                <span>Access Token:</span>
                                <span class="status-value">{'已設定' if CHANNEL_ACCESS_TOKEN else '未設定'}</span>
                            </div>
                            <div class="status-item">
                                <span>Channel Secret:</span>
                                <span class="status-value">{'已設定' if CHANNEL_SECRET else '未設定'}</span>
                            </div>
                        </div>
                        
                        <div class="status-card {'success' if ai_connection_ok else 'error'}">
                            <div class="status-title">⚙️ 系統運行</div>
                            <div class="status-item">
                                <span>系統運行時間:</span>
                                <span class="status-value">{uptime_hours} 小時</span>
                            </div>
                            <div class="status-item">
                                <span>記憶系統:</span>
                                <span class="status-value ok">8次對話記憶 ✅</span>
                            </div>
                            <div class="status-item">
                                <span>學習摘要:</span>
                                <span class="status-value ok">英文生成 ✅</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- AI 模型狀態 -->
                    <h2>🤖 AI 模型狀態</h2>
                    <div class="status-grid">
                        <div class="status-card {'success' if ai_connection_ok else 'error'}">
                            <div class="status-title">🧠 主要 AI 系統</div>
                            <div class="status-item">
                                <span>當前模型:</span>
                                <span class="status-value {'ok' if ai_connection_ok else 'error'}">{quota_status['current_model']} {'✅' if ai_connection_ok else '❌'}</span>
                            </div>
                            <div class="status-item">
                                <span>連接狀態:</span>
                                <span class="status-value {'ok' if ai_connection_ok else 'error'}">{ai_connection_msg}</span>
                            </div>
                            <div class="status-item">
                                <span>API 密鑰:</span>
                                <span class="status-value {'ok' if GEMINI_API_KEY else 'error'}">{'已配置' if GEMINI_API_KEY else '未配置'}</span>
                            </div>
                        </div>
                        
                        <div class="status-card success">
                            <div class="status-title">📈 使用統計</div>
                            <div class="status-item">
                                <span>總 API 調用:</span>
                                <span class="status-value">{total_calls:,} 次</span>
                            </div>
                            <div class="status-item">
                                <span>成功率:</span>
                                <span class="status-value {'ok' if success_rate > 90 else 'warning' if success_rate > 70 else 'error'}">{success_rate:.1f}%</span>
                            </div>
                            <div class="status-item">
                                <span>模型切換次數:</span>
                                <span class="status-value">{analytics_status.get('model_switches', 0)} 次</span>
                            </div>
                        </div>
                        
                        <div class="status-card success">
                            <div class="status-title">🔬 教學分析系統</div>
                            <div class="status-item">
                                <span>分析模型:</span>
                                <span class="status-value ok">{analytics_status.get('current_model', 'N/A')} ✅</span>
                            </div>
                            <div class="status-item">
                                <span>系統狀態:</span>
                                <span class="status-value {'ok' if analytics_status.get('system_status') == 'ready' else 'warning'}">{analytics_status.get('system_status', 'unknown').title()}</span>
                            </div>
                            <div class="status-item">
                                <span>最後切換:</span>
                                <span class="status-value">{last_switch_str}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 可用模型清單 -->
                    <h2>🔄 可用模型清單</h2>
                    <div class="model-list">"""
        
        # 生成每個模型的狀態
        for i, model_name in enumerate(AVAILABLE_MODELS):
            model_info = quota_status['models'].get(model_name, {})
            usage_percent = model_info.get('usage_percent', 0)
            calls = model_info.get('calls', 0)
            errors = model_info.get('errors', 0)
            
            # 判斷狀態
            if model_name == quota_status['current_model']:
                status_badge = '<span class="badge current">當前使用</span>'
                status_icon = "🎯"
            elif usage_percent >= 100:
                status_badge = '<span class="badge unavailable">配額已用完</span>'
                status_icon = "❌"
            elif usage_percent >= 80:
                status_badge = '<span class="badge warning">配額不足</span>'
                status_icon = "⚠️"
            else:
                status_badge = '<span class="badge available">可用</span>'
                status_icon = "✅"
            
            # 設定進度條顏色
            if usage_percent < 50:
                progress_class = "low"
            elif usage_percent < 80:
                progress_class = "medium"
            else:
                progress_class = "high"
            
            priority_order = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅"]
            priority = priority_order[i] if i < len(priority_order) else "🏅"
            
            health_html += f"""
                        <div class="model-item">
                            <div>
                                <span class="model-name">{priority} {model_name}</span>
                                <div style="font-size: 0.8em; color: #6c757d; margin-top: 4px;">
                                    調用次數: {calls}, 錯誤: {errors}
                                </div>
                            </div>
                            <div class="model-status">
                                <div class="progress-bar">
                                    <div class="progress-fill {progress_class}" style="width: {min(usage_percent, 100)}%"></div>
                                </div>
                                <span style="font-size: 0.8em; margin: 0 8px;">{usage_percent:.0f}% 已用</span>
                                {status_icon} {status_badge}
                            </div>
                        </div>"""
        
        health_html += f"""
                    </div>
                    
                    <!-- 系統建議 -->
                    <h2>💡 系統建議</h2>
                    <div class="status-card">
                        <div class="status-title">🎯 優化建議</div>"""
        
        # 生成建議
        if not ai_connection_ok:
            health_html += '<div class="status-item"><span style="color: #e74c3c;">⚠️ AI 連接異常，請檢查 GEMINI_API_KEY 設定</span></div>'
        
        if success_rate < 90:
            health_html += '<div class="status-item"><span style="color: #f39c12;">⚠️ API 成功率偏低，建議檢查網路連接或模型配額</span></div>'
        
        available_models = [name for name, info in quota_status['models'].items() if info.get('usage_percent', 0) < 100]
        if len(available_models) <= 1:
            health_html += '<div class="status-item"><span style="color: #f39c12;">⚠️ 可用模型數量較少，建議升級 API 方案或等待配額重置</span></div>'
        
        if line_status != "已配置":
            health_html += '<div class="status-item"><span style="color: #f39c12;">⚠️ LINE Bot 未完全配置，學生無法使用聊天功能</span></div>'
        
        if not any([ai_connection_ok == False, success_rate < 90, len(available_models) <= 1, line_status != "已配置"]):
            health_html += '<div class="status-item"><span style="color: #27ae60;">✅ 系統運行正常，所有功能都已就緒</span></div>'
        
        health_html += f"""
                    </div>
                    
                    <!-- 時間戳記 -->
                    <div class="timestamp">
                        <p>🕐 檢查時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (台北時間)</p>
                        <p>💾 資料更新頻率: 即時 | 🔄 建議每 5 分鐘重新整理一次</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return health_html
        
    except Exception as e:
        # 簡化版錯誤回應
        return f"""
        <div style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1 style="color: #e74c3c;">🚨 系統健康檢查失敗</h1>
            <p>錯誤詳情: {str(e)}</p>
            <a href="/admin" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回管理後台</a>
        </div>
        """, 500

# =================== 學生管理路由 ===================

@app.route('/students')
def student_profiles():
    """學生清單頁面"""
    try:
        # 搜尋參數
        search = request.args.get('search', '').strip()
        
        # 查詢學生
        query = Student.select()
        if search:
            query = query.where(
                (Student.name.contains(search)) |
                (Student.line_user_id.contains(search)) |
                (Student.student_id.contains(search))
            )
        
        students = list(query.order_by(Student.last_active.desc()))
        
        # 為每個學生獲取基本統計
        student_stats = []
        for student in students:
            message_count = Message.select().where(Message.student_id == student.id).count()
            last_message = Message.select().where(Message.student_id == student.id).order_by(Message.timestamp.desc()).first()
            
            student_stats.append({
                'student': student,
                'message_count': message_count,
                'last_message_time': last_message.timestamp if last_message else None,
                'activity_status': '活躍' if student.last_active and 
                    (datetime.datetime.now() - student.last_active).days < 7 else '較少活動'
            })
        
        # 使用基本HTML模板
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>EMI智能教學助理 - 學生列表</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .search-box { padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 300px; }
                .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 0 5px; }
                .btn:hover { background: #0056b3; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
                .stat-card { background: #f8f9fa; padding: 15px; text-align: center; border-radius: 6px; }
                .student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .student-card { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }
                .student-name { font-weight: bold; font-size: 1.1em; margin-bottom: 8px; }
                .student-info { color: #666; font-size: 0.9em; margin: 4px 0; }
                .activity-active { color: #28a745; font-weight: bold; }
                .activity-inactive { color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>👥 學生列表</h1>
                        <p>EMI智能教學助理 - 學生管理系統</p>
                    </div>
                    <div>
                        <a href="/" class="btn">🏠 首頁</a>
                        <a href="/admin" class="btn">⚙️ 管理後台</a>
                        <a href="/students/export" class="btn">📊 匯出資料</a>
                    </div>
                </div>
                
                <div style="margin: 20px 0;">
                    <form method="GET" style="display: inline-block;">
                        <input type="text" name="search" placeholder="搜尋學生姓名或ID..." 
                               value="{{ search }}" class="search-box">
                        <input type="submit" value="🔍 搜尋" class="btn">
                    </form>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3>{{ total_students }}</h3>
                        <p>總學生數</p>
                    </div>
                    <div class="stat-card">
                        <h3>{{ active_students }}</h3>
                        <p>活躍學生</p>
                    </div>
                    <div class="stat-card">
                        <h3>{{ total_messages }}</h3>
                        <p>總對話數</p>
                    </div>
                </div>
                
                <div class="student-grid">
                    {% if student_stats %}
                    {% for stat in student_stats %}
                    <div class="student-card">
                        <div class="student-name">
                            <a href="/students/{{ stat.student.id }}" style="text-decoration: none; color: #007bff;">
                                {{ stat.student.name }}
                            </a>
                        </div>
                        <div class="student-info">📱 LINE ID: {{ stat.student.line_user_id[-8:] }}...</div>
                        <div class="student-info">💬 對話數: {{ stat.message_count }}</div>
                        <div class="student-info">📊 參與度: {{ "%.1f"|format(stat.student.participation_rate) }}%</div>
                        <div class="student-info">
                            ⏰ 最後活動: 
                            {% if stat.last_message_time %}
                                {{ stat.last_message_time.strftime('%m-%d %H:%M') }}
                            {% else %}
                                無記錄
                            {% endif %}
                        </div>
                        <div class="student-info">
                            📈 狀態: 
                            <span class="{{ 'activity-active' if stat.activity_status == '活躍' else 'activity-inactive' }}">
                                {{ stat.activity_status }}
                            </span>
                        </div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <div style="text-align: center; color: #666; padding: 40px;">
                        目前還沒有學生資料。
                    </div>
                    {% endif %}
                </div>
            </div>
        </body>
        </html>
        """
        
        # 計算統計數據
        total_students = len(students)
        active_students = len([s for s in student_stats if s['activity_status'] == '活躍'])
        total_messages = sum([s['message_count'] for s in student_stats])
        
        return render_template_string(html_template,
                                    student_stats=student_stats,
                                    search=search,
                                    total_students=total_students,
                                    active_students=active_students,
                                    total_messages=total_messages)
        
    except Exception as e:
        logger.error(f"❌ 學生列表頁面錯誤: {e}")
        return f"學生列表載入失敗: {str(e)}", 500

@app.route('/students/export')
def export_all_students():
    """匯出所有學生資料"""
    try:
        students = list(Student.select().order_by(Student.created_at.asc()))
        
        # 準備TSV格式的匯出內容
        output = StringIO()
        writer = csv.writer(output, delimiter='\t')
        
        # 寫入標題行
        writer.writerow([
            'Student Name', 'LINE User ID', 'Student ID', 'Total Messages', 
            'Question Count', 'Participation Rate', 'Last Active', 'Created At'
        ])
        
        # 寫入學生資料
        for student in students:
            message_count = Message.select().where(Message.student_id == student.id).count()
            
            writer.writerow([
                student.name,
                student.line_user_id,
                getattr(student, 'student_id', '') or '',
                message_count,
                student.question_count,
                f"{student.participation_rate:.1f}%",
                student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else '',
                student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else ''
            ])
        
        # 創建檔案
        output.seek(0)
        content = output.getvalue()
        output.close()
        
        # 準備回應
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"EMI_All_Students_{timestamp}.tsv"
        
        response_output = BytesIO()
        response_output.write(content.encode('utf-8'))
        response_output.seek(0)
        
        return send_file(
            response_output,
            as_attachment=True,
            download_name=filename,
            mimetype='text/tab-separated-values; charset=utf-8'
        )
        
    except Exception as e:
        logger.error(f"❌ 匯出學生清單錯誤: {e}")
        return f"匯出失敗: {str(e)}", 500

@app.route('/students/<int:student_id>')
def student_detail(student_id):
    """學生詳情頁面 - 修改為支援完整英文摘要顯示"""
    try:
        student = Student.get_by_id(student_id)
        
        # 獲取所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()))
        
        # 生成完整學習摘要（英文版本，不截斷）
        learning_summary = generate_student_learning_summary(student_id)
        
        # 獲取分析記錄
        analysis = Analysis.select().where(Analysis.student_id == student_id).first()
        
        # 修改 HTML 模板以支援英文內容和完整顯示
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>EMI Teaching Assistant - Student Profile: {{ student.name }}</title>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f8f9fa; 
                    line-height: 1.6;
                }
                .container { 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 12px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
                    overflow: hidden;
                }
                .header { 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 30px; 
                    text-align: center;
                }
                .header h1 { 
                    margin: 0 0 10px 0; 
                    font-size: 2.5em; 
                    font-weight: 300;
                }
                .header p { 
                    margin: 0; 
                    opacity: 0.9; 
                    font-size: 1.1em;
                }
                .nav-bar {
                    background: #2c3e50;
                    padding: 15px 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .nav-links a {
                    color: white;
                    text-decoration: none;
                    margin-right: 20px;
                    padding: 8px 16px;
                    border-radius: 4px;
                    transition: background-color 0.3s;
                }
                .nav-links a:hover {
                    background-color: rgba(255,255,255,0.1);
                }
                .export-btn {
                    background: #27ae60;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                    transition: background-color 0.3s;
                }
                .export-btn:hover {
                    background: #2ecc71;
                }
                .content { 
                    padding: 30px; 
                }
                .stats-grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; 
                    margin-bottom: 30px;
                }
                .stat-card { 
                    background: #f8f9fa; 
                    padding: 20px; 
                    text-align: center; 
                    border-radius: 8px; 
                    border-left: 4px solid #667eea;
                }
                .stat-value { 
                    font-size: 2em; 
                    font-weight: bold; 
                    color: #2c3e50; 
                    margin-bottom: 5px;
                }
                .stat-label { 
                    color: #7f8c8d; 
                    font-size: 0.9em; 
                    text-transform: uppercase; 
                    letter-spacing: 1px;
                }
                .section { 
                    margin-bottom: 30px; 
                    background: white; 
                    border-radius: 8px; 
                    overflow: hidden;
                    border: 1px solid #e9ecef;
                }
                .section-header { 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-bottom: 1px solid #e9ecef;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .section-title { 
                    margin: 0; 
                    font-size: 1.3em; 
                    color: #2c3e50;
                    font-weight: 600;
                }
                .section-content { 
                    padding: 25px; 
                }
                /* 修改：支援完整摘要顯示的樣式 */
                .learning-summary { 
                    background: #f8f9fa; 
                    padding: 25px; 
                    border-radius: 8px; 
                    border-left: 4px solid #27ae60;
                    white-space: pre-wrap; /* 保持換行格式 */
                    word-wrap: break-word; /* 支援長文本換行 */
                    max-height: none; /* 移除高度限制 */
                    overflow: visible; /* 移除滾動條限制 */
                    line-height: 1.7;
                    font-size: 1.05em;
                }
                .summary-meta {
                    background: #e8f5e8;
                    padding: 15px;
                    border-radius: 6px;
                    margin-bottom: 20px;
                    font-size: 0.95em;
                    color: #2d5a2d;
                }
                .conversation-history { 
                    max-height: 500px; 
                    overflow-y: auto; 
                    border: 1px solid #e9ecef; 
                    border-radius: 6px;
                }
                .message { 
                    padding: 15px; 
                    border-bottom: 1px solid #f8f9fa; 
                    transition: background-color 0.3s;
                }
                .message:hover { 
                    background-color: #f8f9fa; 
                }
                .message-timestamp { 
                    font-size: 0.8em; 
                    color: #7f8c8d; 
                    margin-bottom: 8px;
                    font-weight: 500;
                }
                .message-content {
                    color: #2c3e50;
                    line-height: 1.5;
                }
                .no-data {
                    text-align: center;
                    color: #7f8c8d;
                    font-style: italic;
                    padding: 40px;
                }
                .language-indicator {
                    background: #3498db;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <!-- 頁面標題 -->
                <div class="header">
                    <h1>📚 Student Learning Profile</h1>
                    <p>EMI Teaching Assistant - Comprehensive Learning Analytics</p>
                </div>
                
                <!-- 導航欄 -->
                <div class="nav-bar">
                    <div class="nav-links">
                        <a href="/">🏠 Home</a>
                        <a href="/students">👥 All Students</a>
                        <a href="/admin">⚙️ Admin Panel</a>
                    </div>
                    <a href="/students/{{ student.id }}/export" class="export-btn">
                        📥 Export Profile
                    </a>
                </div>
                
                <!-- 學生基本資訊 -->
                <div class="content">
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">
                        👤 {{ student.name }}
                        {% if learning_summary.get('language') == 'english' %}
                            <span class="language-indicator">EN</span>
                        {% endif %}
                    </h2>
                    
                    <!-- 統計數據 -->
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{{ learning_summary.message_count }}</div>
                            <div class="stat-label">Total Messages</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ learning_summary.question_count }}</div>
                            <div class="stat-label">Questions Asked</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ "%.1f"|format(student.participation_rate) }}%</div>
                            <div class="stat-label">Participation Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ learning_summary.get('topics', [])|length }}</div>
                            <div class="stat-label">Learning Topics</div>
                        </div>
                    </div>
                    
                    <!-- 完整學習摘要 -->
                    <div class="section">
                        <div class="section-header">
                            <h3 class="section-title">📈 Learning Summary (English)</h3>
                            <small style="color: #7f8c8d;">Generated: {{ learning_summary.generated_at[:19] if learning_summary.generated_at else 'Unknown' }}</small>
                        </div>
                        <div class="section-content">
                            {% if learning_summary.summary %}
                                <div class="summary-meta">
                                    <strong>📊 Summary Statistics:</strong>
                                    Length: {{ learning_summary.actual_length or 'N/A' }} characters | 
                                    Complete: {{ '✅ Full Summary' if not learning_summary.get('truncated', True) else '⚠️ Truncated' }} |
                                    Language: {{ '🇺🇸 English' if learning_summary.get('language') == 'english' else '🇹🇼 Traditional Chinese' }}
                                    {% if learning_summary.get('topics') %}
                                        <br><strong>🎯 Key Topics:</strong> {{ learning_summary.topics | join(', ') }}
                                    {% endif %}
                                </div>
                                <div class="learning-summary">{{ learning_summary.summary }}</div>
                            {% else %}
                                <div class="no-data">
                                    📝 Learning summary will be generated automatically as the student continues to interact with the system.
                                </div>
                            {% endif %}
                        </div>
                    </div>
                    
                    <!-- 對話歷史 -->
                    <div class="section">
                        <div class="section-header">
                            <h3 class="section-title">💬 Recent Conversations</h3>
                            <small style="color: #7f8c8d;">Last {{ messages|length }} messages</small>
                        </div>
                        <div class="section-content">
                            {% if messages %}
                                <div class="conversation-history">
                                    {% for message in messages %}
                                    <div class="message" title="Full message: {{ message.content }}">
                                        <div class="message-timestamp">
                                            {{ message.timestamp.strftime('%Y-%m-%d %H:%M') if message.timestamp else 'Unknown time' }} 
                                            {% if message.message_type == 'question' or '?' in message.content %}
                                                ❓ Question
                                            {% else %}
                                                💬 Statement
                                            {% endif %}
                                        </div>
                                        <div class="message-content">{{ message.content }}</div>
                                    </div>
                                    {% endfor %}
                                </div>
                            {% else %}
                                <div class="no-data">
                                    💭 No conversation records available yet.
                                </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(html_template,
                                    student=student,
                                    messages=messages,
                                    learning_summary=learning_summary,
                                    analysis=analysis)
        
    except Exception as e:
        logger.error(f"❌ 學生詳情頁面錯誤: {e}")
        return f"Student profile loading failed: {str(e)}", 500

@app.route('/students/<int:student_id>/export')
def export_student_profile(student_id):
    """匯出學生學習檔案 - 修改為支援完整英文摘要匯出"""
    try:
        student = Student.get_by_id(student_id)
        
        # 獲取所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.asc()))
        
        # 生成完整學習摘要（英文版本，不截斷）
        learning_summary = generate_student_learning_summary(student_id)
        
        # 準備匯出內容 - 改為英文格式
        export_content = []
        export_content.append("EMI Teaching Assistant - Student Learning Profile")
        export_content.append("=" * 60)
        export_content.append(f"Student Name: {student.name}")
        export_content.append(f"LINE User ID: {student.line_user_id}")
        if hasattr(student, 'student_id') and student.student_id:
            export_content.append(f"Student ID: {student.student_id}")
        export_content.append(f"Total Messages: {learning_summary['message_count']}")
        export_content.append(f"Questions Asked: {learning_summary['question_count']}")
        export_content.append(f"Participation Rate: {student.participation_rate:.1f}%")
        if student.last_active:
            export_content.append(f"Last Active: {student.last_active.strftime('%Y-%m-%d %H:%M:%S')}")
        export_content.append(f"Export Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_content.append(f"Summary Language: {learning_summary.get('language', 'english').title()}")
        export_content.append("")
        
        # 完整學習摘要（英文版本）
        export_content.append("COMPREHENSIVE LEARNING SUMMARY:")
        export_content.append("-" * 40)
        # 不截斷摘要內容，完整匯出
        export_content.append(learning_summary['summary'])
        
        if learning_summary.get('topics'):
            export_content.append("")
            export_content.append(f"Key Learning Topics: {', '.join(learning_summary['topics'])}")
        
        export_content.append("")
        export_content.append(f"Summary Statistics:")
        export_content.append(f"- Total Characters: {learning_summary.get('actual_length', 'N/A')}")
        export_content.append(f"- Complete Summary: {'Yes' if not learning_summary.get('truncated', True) else 'No (truncated)'}")
        export_content.append(f"- Generated At: {learning_summary.get('generated_at', 'Unknown')}")
        export_content.append("")
        
        # 完整對話記錄
        export_content.append("COMPLETE CONVERSATION HISTORY:")
        export_content.append("-" * 40)
        
        for i, message in enumerate(messages, 1):
            timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if message.timestamp else 'Unknown time'
            msg_type = '❓ Question' if (message.message_type == 'question' or '?' in message.content) else '💬 Statement'
            
            export_content.append(f"{i:3d}. [{timestamp}] {msg_type}")
            export_content.append(f"     {message.content}")
            export_content.append("")
        
        if not messages:
            export_content.append("No conversation records available.")
        
        export_content.append("")
        export_content.append("=" * 60)
        export_content.append("End of Student Learning Profile")
        
        # 創建匯出檔案
        export_text = '\n'.join(export_content)
        
        # 使用學生姓名和時間戳記創建檔名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"EMI_Student_Profile_{student.name}_{timestamp}.txt"
        
        # 創建檔案內容
        output = BytesIO()
        output.write(export_text.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain; charset=utf-8'
        )
        
    except Exception as e:
        logger.error(f"❌ 匯出學生檔案錯誤: {e}")
        return f"Export failed: {str(e)}", 500

# =================== LINE Bot 訊息處理 ===================

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
    """處理 LINE 訊息 - 增強記憶版本"""
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
        if hasattr(db, 'is_closed') and db.is_closed():
            logger.warning("⚠️ 資料庫連接已關閉，嘗試重新連接...")
            db.connect()
            logger.info("✅ 資料庫重新連接成功")
        
        # 獲取或創建學生記錄
        student = None
        try:
            student, created = Student.get_or_create(
                line_user_id=user_id,
                defaults={'name': f'學生_{user_id[-4:]}'}
            )
            
            if created:
                logger.info(f"🆕 創建新學生記錄: {student.name}")
            
            # 更新最後活動時間
            student.last_active = datetime.datetime.now()
            student.save()
            
        except Exception as student_error:
            logger.error(f"❌ 學生記錄處理錯誤: {student_error}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="系統忙碌中，請稍後再試。System busy, please try again later.")
            )
            return
        
        # 儲存訊息記錄
        try:
            # 判斷訊息類型
            message_type = 'question' if '?' in user_message or user_message.endswith('？') else 'statement'
            
            Message.create(
                student_id=student.id,
                content=user_message,
                message_type=message_type,
                timestamp=datetime.datetime.now()
            )
            
            logger.info(f"💾 已儲存訊息記錄: {message_type}")
            
        except Exception as message_error:
            logger.error(f"❌ 訊息儲存錯誤: {message_error}")
        
        # 獲取增強的對話上下文（8次記憶）
        conversation_context = get_enhanced_conversation_context(student.id, limit=8)
        student_context = get_student_learning_context(student.id)
        
        # 生成AI回應
        try:
            ai_response = get_ai_response(
                student.id,
                user_message,
                conversation_context,
                student_context
            )
            
            if ai_response:
                # 回覆訊息
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=ai_response)
                )
                
                # 儲存AI回應記錄
                try:
                    AIResponse.create(
                        student_id=student.id,
                        user_message=user_message,
                        ai_response=ai_response,
                        timestamp=datetime.datetime.now()
                    )
                except Exception as ai_save_error:
                    logger.error(f"❌ AI回應儲存錯誤: {ai_save_error}")
                
                # 更新學生統計
                try:
                    update_student_stats(student.id)
                except Exception as stats_error:
                    logger.error(f"❌ 統計更新錯誤: {stats_error}")
                
                logger.info(f"✅ 成功處理訊息並回覆")
                
            else:
                # AI回應失敗的備用回應
                fallback_response = "I'm having some technical difficulties right now. Please try again in a moment! 🤖"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=fallback_response)
                )
                logger.warning("⚠️ AI回應失敗，使用備用回應")
                
        except Exception as ai_error:
            logger.error(f"❌ AI處理錯誤: {ai_error}")
            # 緊急備用回應
            emergency_response = "Sorry, I'm experiencing technical issues. Please try again later. 🔧"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=emergency_response)
                )
            except:
                pass
        
    except Exception as e:
        logger.error(f"❌ 訊息處理全域錯誤: {e}")
        try:
            emergency_response = "System error occurred. Please try again. 🔧"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=emergency_response)
            )
        except:
            pass

# =================== 程式進入點 ===================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（增強版本）")
    
    # 系統組件檢查
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🧠 記憶系統: 8次對話記憶已啟用")
    logger.info(f"📁 學習檔案: 英文摘要生成已啟用")
    logger.info(f"🏥 健康檢查: 增強AI模型監控已啟用")
    
    # 資料庫初始化
    logger.info("📊 初始化資料庫連接...")
    try:
        initialize_db()
        logger.info("✅ 資料庫初始化成功")
    except Exception as db_init_error:
        logger.error(f"❌ 資料庫初始化失敗: {db_init_error}")
    
    # 啟動應用
    app.run(host='0.0.0.0', port=port, debug=debug)
