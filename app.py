# app.py - EMI智能記憶系統優化版本
# 將對話記憶從3次提升到8次，新增學習檔案系統功能

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
        if student.language_preference:
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
        if student.learning_style:
            context_parts.append(f"Learning style: {student.learning_style}")
        
        # 興趣領域
        if student.interest_areas:
            context_parts.append(f"Interests: {student.interest_areas[:100]}")
        
        return "; ".join(context_parts)
        
    except Exception as e:
        logger.error(f"❌ 獲取學生學習背景錯誤: {e}")
        return ""

# =================== 學習檔案系統功能 ===================

def generate_student_learning_summary(student_id, conversation_limit=None):
    """
    即時生成學生學習摘要
    根據對話數量動態調整摘要長度
    """
    try:
        student = Student.get_by_id(student_id)
        
        # 獲取所有對話記錄
        messages_query = Message.select().where(Message.student_id == student_id).order_by(Message.timestamp.desc())
        
        if conversation_limit:
            messages = list(messages_query.limit(conversation_limit))
        else:
            messages = list(messages_query)
        
        message_count = len(messages)
        
        if message_count == 0:
            return {
                'summary': '此學生尚未開始對話。',
                'message_count': 0,
                'summary_length': '無資料',
                'topics': [],
                'generated_at': datetime.datetime.now().isoformat()
            }
        
        # 根據對話數量決定摘要長度
        if message_count <= 10:
            target_length = 50  # 1-10則: 50字
            summary_type = "簡要摘要"
        elif message_count <= 30:
            target_length = 100  # 11-30則: 100字
            summary_type = "詳細摘要"
        else:
            target_length = 150  # 31則+: 150字
            summary_type = "完整摘要"
        
        # 分析對話內容
        questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content]
        statements = [msg for msg in messages if msg.message_type != 'question' and '?' not in msg.content]
        
        # 識別主要話題（簡易版本）
        topics = []
        content_text = " ".join([msg.content.lower() for msg in messages[-20:]])  # 分析最近20條
        
        # 常見EMI課程主題檢測
        topic_keywords = {
            "Industry 4.0": ["industry", "4.0", "automation", "smart manufacturing", "iot"],
            "Smart Home": ["smart home", "home automation", "iot", "connected devices"],
            "AI Healthcare": ["healthcare", "medical", "ai in medicine", "health technology"],
            "Big Data": ["big data", "data analysis", "analytics", "database"],
            "Machine Learning": ["machine learning", "ml", "algorithm", "model"],
            "文法問題": ["grammar", "tense", "verb", "sentence structure"],
            "詞彙學習": ["vocabulary", "word", "meaning", "definition"],
            "發音指導": ["pronunciation", "speak", "sound", "accent"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_text for keyword in keywords):
                topics.append(topic)
        
        # 生成摘要文字
        summary_parts = []
        
        # 基本參與資訊
        if message_count >= 20:
            summary_parts.append(f"{student.name}是一位積極參與的學生")
        elif message_count >= 10:
            summary_parts.append(f"{student.name}展現良好的學習參與度")
        else:
            summary_parts.append(f"{student.name}正在開始參與課程討論")
        
        # 問答比例
        if questions:
            question_ratio = len(questions) / message_count * 100
            if question_ratio > 40:
                summary_parts.append("表現出強烈的求知慾，經常主動提問")
            elif question_ratio > 20:
                summary_parts.append("會適度提出問題，學習態度積極")
            else:
                summary_parts.append("較多以陳述為主，偶爾提出疑問")
        
        # 主要興趣話題
        if topics:
            summary_parts.append(f"主要關注議題包括：{', '.join(topics[:3])}")
        
        # 學習模式
        if student.participation_rate > 70:
            summary_parts.append("學習互動頻繁，參與度高")
        elif student.participation_rate > 30:
            summary_parts.append("學習互動適中，持續參與")
        
        # 組合摘要並控制長度
        full_summary = "，".join(summary_parts) + "。"
        
        # 如果超過目標長度，進行適當截取
        if len(full_summary) > target_length:
            full_summary = full_summary[:target_length-3] + "..."
        
        return {
            'summary': full_summary,
            'message_count': message_count,
            'question_count': len(questions),
            'statement_count': len(statements),
            'summary_type': summary_type,
            'target_length': target_length,
            'actual_length': len(full_summary),
            'topics': topics[:5],  # 最多顯示5個主題
            'participation_rate': student.participation_rate,
            'generated_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 生成學習摘要錯誤: {e}")
        return {
            'summary': f'摘要生成失敗：{str(e)}',
            'message_count': 0,
            'error': str(e),
            'generated_at': datetime.datetime.now().isoformat()
        }

# =================== 新增的網頁後台路由 ===================

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
                .search-box { padding: 10px; border: 1px solid #ddd; border-radius: 4px; width: 300px; }
                .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 0 5px; }
                .btn:hover { background: #0056b3; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .stat-card { background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center; }
                .student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
                .student-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white; }
                .student-name { font-weight: bold; font-size: 1.1em; margin-bottom: 8px; }
                .student-info { color: #666; font-size: 0.9em; margin: 4px 0; }
                .status-active { color: #28a745; font-weight: bold; }
                .status-inactive { color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 EMI智能教學助理 - 學生列表</h1>
                    <div>
                        <a href="/admin" class="btn">返回管理後台</a>
                        <a href="/students/export" class="btn">匯出資料</a>
                    </div>
                </div>
                
                <div class="stats-grid">
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
                
                <form method="GET" style="margin-bottom: 20px;">
                    <input type="text" name="search" value="{{ search }}" placeholder="搜尋學生姓名、LINE ID或學號..." class="search-box">
                    <button type="submit" class="btn">搜尋</button>
                    {% if search %}
                    <a href="/students" class="btn" style="background: #6c757d;">清除搜尋</a>
                    {% endif %}
                </form>
                
                <div class="student-grid">
                    {% for item in student_stats %}
                    <div class="student-card">
                        <div class="student-name">{{ item.student.name }}</div>
                        <div class="student-info">LINE ID: {{ item.student.line_user_id[:20] }}...</div>
                        {% if item.student.student_id %}
                        <div class="student-info">學號: {{ item.student.student_id }}</div>
                        {% endif %}
                        <div class="student-info">對話數: {{ item.message_count }}</div>
                        <div class="student-info">參與度: {{ "%.1f"|format(item.student.participation_rate) }}%</div>
                        {% if item.last_message_time %}
                        <div class="student-info">最後活動: {{ item.last_message_time.strftime('%m-%d %H:%M') }}</div>
                        {% endif %}
                        <div class="student-info {{ 'status-active' if item.activity_status == '活躍' else 'status-inactive' }}">
                            {{ item.activity_status }}
                        </div>
                        <div style="margin-top: 10px;">
                            <a href="/students/{{ item.student.id }}" class="btn" style="font-size: 0.8em;">查看詳情</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                {% if not student_stats %}
                <div style="text-align: center; color: #666; margin: 40px 0;">
                    {% if search %}
                    找不到符合「{{ search }}」的學生。
                    {% else %}
                    目前還沒有學生資料。
                    {% endif %}
                </div>
                {% endif %}
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

@app.route('/students/<int:student_id>')
def student_profile_detail(student_id):
    """學生詳情頁面"""
    try:
        student = Student.get_by_id(student_id)
        
        # 獲取所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(50))
        
        # 即時生成學習摘要
        learning_summary = generate_student_learning_summary(student_id)
        
        # 分析學習模式
        analysis = analyze_student_patterns(student_id)
        
        # 使用基本HTML模板
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ student.name }} - 學習檔案</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 0 5px; font-size: 0.9em; }
                .btn:hover { background: #0056b3; }
                .btn-export { background: #28a745; }
                .btn-export:hover { background: #1e7e34; }
                .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .info-card { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }
                .summary-section { background: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .messages-section { background: #f8f9fa; padding: 20px; border-radius: 8px; }
                .message-item { background: white; padding: 10px; margin: 8px 0; border-radius: 4px; border-left: 3px solid #ddd; }
                .message-question { border-left-color: #28a745; }
                .message-timestamp { color: #666; font-size: 0.8em; }
                .topic-tag { display: inline-block; background: #e3f2fd; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; margin: 2px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👤 {{ student.name }} - 學習檔案</h1>
                    <div>
                        <a href="/students/{{ student.id }}/export" class="btn btn-export">匯出檔案</a>
                        <a href="/students" class="btn">返回列表</a>
                    </div>
                </div>
                
                <div class="info-grid">
                    <div class="info-card">
                        <h4>基本資訊</h4>
                        <p><strong>姓名:</strong> {{ student.name }}</p>
                        <p><strong>LINE ID:</strong> {{ student.line_user_id[:15] }}...</p>
                        {% if student.student_id %}
                        <p><strong>學號:</strong> {{ student.student_id }}</p>
                        {% endif %}
                    </div>
                    
                    <div class="info-card">
                        <h4>學習統計</h4>
                        <p><strong>總對話數:</strong> {{ learning_summary.message_count }}</p>
                        <p><strong>提問數:</strong> {{ learning_summary.question_count }}</p>
                        <p><strong>參與度:</strong> {{ "%.1f"|format(student.participation_rate) }}%</p>
                    </div>
                    
                    <div class="info-card">
                        <h4>活動狀態</h4>
                        {% if student.last_active %}
                        <p><strong>最後活動:</strong> {{ student.last_active.strftime('%Y-%m-%d %H:%M') }}</p>
                        {% endif %}
                        <p><strong>註冊時間:</strong> {{ student.created_at.strftime('%Y-%m-%d') }}</p>
                    </div>
                    
                    <div class="info-card">
                        <h4>學習偏好</h4>
                        <p><strong>語言偏好:</strong> 
                        {% if student.language_preference == 'english' %}英文為主
                        {% elif student.language_preference == 'chinese' %}中文為主
                        {% else %}中英混合{% endif %}</p>
                        {% if student.learning_style %}
                        <p><strong>學習風格:</strong> {{ student.learning_style }}</p>
                        {% endif %}
                    </div>
                </div>
                
                <div class="summary-section">
                    <h3>📝 學習摘要 <span style="font-size: 0.7em; color: #666;">{{ learning_summary.summary_type }} ({{ learning_summary.actual_length }}/{{ learning_summary.target_length }}字)</span></h3>
                    <p>{{ learning_summary.summary }}</p>
                    
                    {% if learning_summary.topics %}
                    <div style="margin-top: 15px;">
                        <strong>主要學習主題:</strong><br>
                        {% for topic in learning_summary.topics %}
                        <span class="topic-tag">{{ topic }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}
                    
                    <div style="margin-top: 10px; font-size: 0.8em; color: #666;">
                        摘要生成時間: {{ learning_summary.generated_at[:19].replace('T', ' ') }}
                    </div>
                </div>
                
                <div class="messages-section">
                    <h3>💬 最近對話記錄 (最多50條)</h3>
                    {% if messages %}
                    {% for message in messages %}
                    <div class="message-item {{ 'message-question' if message.message_type == 'question' or '?' in message.content }}">
                        <div class="message-timestamp">
                            {{ message.timestamp.strftime('%m-%d %H:%M') }} 
                            {% if message.message_type == 'question' or '?' in message.content %}❓ 問題{% else %}💬 陳述{% endif %}
                        </div>
                        <div>{{ message.content }}</div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p style="color: #666; text-align: center; margin: 20px 0;">尚無對話記錄</p>
                    {% endif %}
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
        return f"學生詳情載入失敗: {str(e)}", 500

@app.route('/students/<int:student_id>/export')
def export_student_profile(student_id):
    """匯出學生學習檔案"""
    try:
        student = Student.get_by_id(student_id)
        
        # 獲取所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.asc()))
        
        # 生成學習摘要
        learning_summary = generate_student_learning_summary(student_id)
        
        # 準備匯出內容
        export_content = []
        export_content.append("EMI智能教學助理 - 學生學習檔案")
        export_content.append("=" * 50)
        export_content.append(f"學生姓名: {student.name}")
        export_content.append(f"LINE ID: {student.line_user_id}")
        if student.student_id:
            export_content.append(f"學號: {student.student_id}")
        export_content.append(f"總對話數: {learning_summary['message_count']}")
        export_content.append(f"提問數: {learning_summary['question_count']}")
        export_content.append(f"參與度: {student.participation_rate:.1f}%")
        if student.last_active:
            export_content.append(f"最後活動: {student.last_active.strftime('%Y-%m-%d %H:%M:%S')}")
        export_content.append(f"匯出時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_content.append("")
        
        # 學習摘要
        export_content.append("學習摘要:")
        export_content.append("-" * 30)
        export_content.append(learning_summary['summary'])
        if learning_summary.get('topics'):
            export_content.append(f"主要學習主題: {', '.join(learning_summary['topics'])}")
        export_content.append("")
        
        # 對話記錄
        export_content.append("完整對話記錄:")
        export_content.append("-" * 30)
        
        for i, message in enumerate(messages, 1):
            timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if message.timestamp else '未知時間'
            msg_type = '❓ 問題' if (message.message_type == 'question' or '?' in message.content) else '💬 陳述'
            export_content.append(f"{i:3d}. [{timestamp}] {msg_type}")
            export_content.append(f"     {message.content}")
            export_content.append("")
        
        # 生成檔案
        output = StringIO()
        output.write('\n'.join(export_content))
        output.seek(0)
        
        # 建立檔案名稱
        filename = f"{student.name}_學習檔案_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return send_file(
            BytesIO(output.getvalue().encode('utf-8-sig')),  # 加上BOM以支援中文
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain; charset=utf-8'
        )
        
    except Exception as e:
        logger.error(f"❌ 匯出學生檔案錯誤: {e}")
        return f"匯出失敗: {str(e)}", 500

@app.route('/students/export')
def export_all_students():
    """匯出所有學生資料（TSV格式）"""
    try:
        students = list(Student.select().order_by(Student.created_at.desc()))
        
        # 準備CSV資料
        output = StringIO()
        writer = csv.writer(output, delimiter='\t')  # TSV格式
        
        # 寫入標題行
        headers = [
            '學生姓名', 'LINE_ID', '學號', '總對話數', '提問數', '參與度(%)', 
            '最後活動時間', '註冊時間', '語言偏好', '學習風格', '活動狀態'
        ]
        writer.writerow(headers)
        
        # 寫入學生資料
        for student in students:
            # 計算統計資料
            message_count = Message.select().where(Message.student_id == student.id).count()
            question_count = Message.select().where(
                (Message.student_id == student.id) & 
                ((Message.message_type == 'question') | (Message.content.contains('?')))
            ).count()
            
            # 判斷活動狀態
            if student.last_active:
                days_inactive = (datetime.datetime.now() - student.last_active).days
                activity_status = '活躍' if days_inactive < 7 else '較少活動'
            else:
                activity_status = '尚未活動'
            
            # 語言偏好顯示
            lang_pref = '中英混合'
            if student.language_preference == 'english':
                lang_pref = '英文為主'
            elif student.language_preference == 'chinese':
                lang_pref = '中文為主'
            
            row = [
                student.name,
                student.line_user_id,
                student.student_id or '',
                message_count,
                question_count,
                f"{student.participation_rate:.1f}",
                student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else '',
                student.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                lang_pref,
                student.learning_style or '',
                activity_status
            ]
            writer.writerow(row)
        
        output.seek(0)
        
        # 生成檔案名稱
        filename = f"EMI學生清單_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv"
        
        return send_file(
            BytesIO(output.getvalue().encode('utf-8-sig')),
            as_attachment=True,
            download_name=filename,
            mimetype='text/tab-separated-values; charset=utf-8'
        )
        
    except Exception as e:
        logger.error(f"❌ 匯出學生清單錯誤: {e}")
        return f"匯出失敗: {str(e)}", 500

# =================== 修改原有的訊息處理函數 ===================

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
        if db.is_closed():
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
            
            # 如果是新學生或需要更新暱稱，獲取 LINE 用戶資料
            if created or student.name.startswith('學生_') or student.name.startswith('LINE用戶_'):
                try:
                    profile = line_bot_api.get_profile(user_id)
                    display_name = profile.display_name or f"用戶_{user_id[-4:]}"
                    
                    old_name = student.name
                    student.name = display_name
                    student.save()
                    
                    logger.info(f"✅ 成功獲取用戶暱稱: {old_name} -> {display_name}")
                    
                except LineBotApiError as profile_error:
                    logger.warning(f"⚠️ LINE API 錯誤，無法獲取用戶資料: {profile_error}")
                    if student.name.startswith('學生_'):
                        student.name = f"用戶_{user_id[-6:]}"
                        student.save()
                except Exception as profile_error:
                    logger.warning(f"⚠️ 無法獲取用戶資料: {profile_error}")
                    if student.name.startswith('學生_'):
                        student.name = f"用戶_{user_id[-6:]}"
                        student.save()
            
            logger.info(f"👤 學生記錄: {student.name} ({'新建' if created else '既有'})")
                
        except Exception as student_error:
            logger.error(f"❌ 學生記錄處理錯誤: {student_error}")
            student = None

        # 儲存訊息
        try:
            if student:
                # 判斷訊息類型
                message_type = 'question' if '?' in user_message else 'statement'
                
                message_record = Message.create(
                    student=student,
                    content=user_message,
                    timestamp=datetime.datetime.now(),
                    message_type=message_type,
                    source_type='user'
                )
                logger.info(f"💾 訊息已儲存: ID {message_record.id}, 類型: {message_type}")
        except Exception as msg_error:
            logger.error(f"❌ 訊息儲存錯誤: {msg_error}")
        
        # 🔥 關鍵改進：使用增強的8次對話記憶
        logger.info("🧠 開始獲取增強對話上下文...")
        conversation_context = ""
        student_context = ""
        
        if student:
            try:
                # 獲取8次對話記憶
                conversation_context = get_enhanced_conversation_context(student.id, limit=8)
                logger.info(f"✅ 已獲取8次對話記憶，長度: {len(conversation_context)} 字符")
                
                # 獲取學生學習背景
                student_context = get_student_learning_context(student.id)
                logger.info(f"✅ 已獲取學生學習背景，長度: {len(student_context)} 字符")
                
            except Exception as context_error:
                logger.error(f"❌ 獲取對話上下文錯誤: {context_error}")
                conversation_context = ""
                student_context = ""
        
        # 取得 AI 回應
        logger.info("🤖 開始生成 AI 回應...")
        ai_response = None
        
        try:
            if not GEMINI_API_KEY:
                logger.error("❌ GEMINI_API_KEY 未配置")
                ai_response = "Hello! I'm currently being set up. Please try again in a moment. 👋"
            else:
                # 使用增強的上下文生成AI回應
                ai_response = get_ai_response(
                    student.id if student else None, 
                    user_message,
                    conversation_context=conversation_context,
                    student_context=student_context
                )
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
                
                # 更新參與度（簡易計算）
                total_days = (datetime.datetime.now() - student.created_at).days + 1
                student.participation_rate = min(100, (student.message_count / total_days) * 10)
                
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
        except:
            pass

# =================== 其他原有路由保持不變 ===================

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
        </div>
        <div style="margin-top: 20px; color: #666;">
            <p>✨ 新功能：8次對話記憶 | 即時學習摘要 | 完整檔案匯出</p>
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
                <h4>🧠 系統改進摘要：</h4>
                <ul>
                    <li>✅ 對話記憶從3次提升到8次</li>
                    <li>✅ 新增即時學習摘要生成</li>
                    <li>✅ 摘要長度自動調整 (1-10則:50字，11-30則:100字，31則+:150字)</li>
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

@app.route('/health')
def health_check():
    """系統健康檢查"""
    try:
        # 資料庫連接檢查
        db_status = "正常" if not db.is_closed() else "未連接"
        
        # LINE Bot API 檢查
        line_status = "已配置" if line_bot_api else "未配置"
        
        # Gemini AI 檢查
        ai_status = "已配置" if GEMINI_API_KEY else "未配置"
        
        return f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h1>🏥 系統健康檢查</h1>
            
            <div style="margin: 20px 0;">
                <h3>📊 系統狀態</h3>
                <p>🗄️ 資料庫: <span style="color: {'green' if db_status == '正常' else 'red'};">{db_status}</span></p>
                <p>📱 LINE Bot: <span style="color: {'green' if line_status == '已配置' else 'red'};">{line_status}</span></p>
                <p>🤖 Gemini AI: <span style="color: {'green' if ai_status == '已配置' else 'red'};">{ai_status}</span></p>
            </div>
            
            <div style="margin: 20px 0;">
                <h3>🧠 記憶系統狀態</h3>
                <p>✅ 對話記憶: 8次記憶 (已優化)</p>
                <p>✅ 學習檔案: 即時生成摘要</p>
                <p>✅ 匯出功能: TSV/TXT格式支援</p>
            </div>
            
            <div style="margin-top: 20px;">
                <a href="/admin" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回管理後台</a>
            </div>
        </div>
        """
        
    except Exception as e:
        return f"健康檢查失敗: {str(e)}", 500

# =================== 程式進入點 ===================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 啟動 EMI 智能教學助理（增強記憶版本）")
    
    # 系統組件檢查
    logger.info(f"📱 LINE Bot: {'已配置' if line_bot_api else '未配置'}")
    logger.info(f"🤖 Gemini AI: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"🧠 記憶系統: 8次對話記憶已啟用")
    logger.info(f"📁 學習檔案: 即時摘要生成已啟用")
    
    # 資料庫初始化
    logger.info("📊 初始化資料庫連接...")
    try:
        initialize_db()
        logger.info("✅ 資料庫初始化成功")
    except Exception as db_init_error:
        logger.error(f"❌ 資料庫初始化失敗: {db_init_error}")
    
    # 啟動應用
    app.run(host='0.0.0.0', port=port, debug=debug)
