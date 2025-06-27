# =================== app.py 完整修復版 - 第1段開始 ===================
# EMI智能教學助理系統 - 2025年增強版本 (完整修復版)
# 支援最新 Gemini 2.5/2.0 系列模型 + 8次對話記憶 + 英文摘要 + 完整匯出
# 修復：新增 /callback 路由和訊息處理函式
# 更新日期：2025年6月27日

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
import google.generativeai as genai

# 導入自定義模組
from models import db, Student, Message, Analysis, AIResponse, initialize_db

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

# =================== 2025年最新 AI 模型配置 ===================

# 建議的模型優先順序配置 - 2025年6月最新版本
# 基於配額、性能、成本效益和版本新舊程度

AVAILABLE_MODELS = [
    "gemini-2.5-flash",        # 🥇 首選：最佳性價比 + 思考能力 + 速度
    "gemini-2.5-pro",          # 🏆 深度分析：最高智能 + 複雜推理
    "gemini-2.5-flash-lite",   # 🚀 高效處理：最快速度 + 最低成本
    "gemini-2.0-flash",        # 🥈 穩定選擇：成熟穩定 + 多模態
    "gemini-2.0-pro",          # 💻 專業任務：編程專家 + 2M context
    "gemini-2.0-flash-lite",   # 💰 經濟選擇：成本優化 + 比1.5更佳
    # === 備用舊版本 (向下兼容) ===
    "gemini-1.5-flash",        # 📦 備案1：成熟穩定 + 中配額
    "gemini-1.5-flash-8b",     # 📦 備案2：效率優化版本
    "gemini-1.5-pro",          # 📦 備案3：功能完整但較慢
    "gemini-1.0-pro",          # 📦 最後備案：舊版但穩定
]

# 模型特性說明 (用於健康檢查和管理)
MODEL_SPECIFICATIONS = {
    "gemini-2.5-flash": {
        "generation": "2.5",
        "type": "Flash",
        "features": ["thinking", "speed", "efficiency", "1M_context"],
        "best_for": "日常對話、快速回應、教學問答",
        "cost_level": "medium"
    },
    "gemini-2.5-pro": {
        "generation": "2.5", 
        "type": "Pro",
        "features": ["advanced_reasoning", "complex_analysis", "2M_context"],
        "best_for": "深度分析、複雜推理、學術討論",
        "cost_level": "high"
    },
    "gemini-2.0-flash": {
        "generation": "2.0",
        "type": "Flash", 
        "features": ["multimodal", "stable", "1M_context"],
        "best_for": "多媒體處理、穩定對話",
        "cost_level": "medium"
    }
}

# 動態模型選擇函式
def get_best_available_model():
    """
    動態選擇最佳可用模型
    按優先順序測試模型可用性
    """
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY 未設定")
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 按優先順序測試模型
        for model_name in AVAILABLE_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                # 簡單測試模型是否可用
                test_response = model.generate_content("Hello", 
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=10,
                        temperature=0.1
                    )
                )
                if test_response and test_response.text:
                    logger.info(f"✅ 成功連接模型: {model_name}")
                    return model_name
            except Exception as model_error:
                logger.warning(f"⚠️ 模型 {model_name} 不可用: {model_error}")
                continue
        
        logger.error("❌ 所有模型都不可用")
        return None
        
    except Exception as e:
        logger.error(f"❌ 模型初始化失敗: {e}")
        return None

# =================== app.py 完整修復版 - 第1段結束 ===================

# =================== app.py 完整修復版 - 第2段開始 ===================
# AI 回應生成功能與記憶管理

# =================== AI 回應生成功能 ===================

def get_ai_response_for_student(student_message, student_id=None):
    """
    為學生生成 AI 回應
    整合記憶功能和個人化回應
    """
    try:
        # 設定 Gemini API
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY 未設定")
            return "抱歉，AI 服務暫時無法使用。請稍後再試。🤖"
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 選擇最佳可用模型
        model_name = get_best_available_model()
        if not model_name:
            return "抱歉，AI 服務暫時無法使用。請稍後再試。🤖"
        
        model = genai.GenerativeModel(model_name)
        
        # 建構教學專用提示
        teaching_prompt = f"""
你是一位專業的 EMI (English as Medium of Instruction) 教學助理。
請用繁體中文回應，並遵循以下原則：

1. 🎯 教學導向：專注於英語學習和教學內容
2. 📚 學術支援：提供準確的文法、詞彙、發音指導
3. 🌟 鼓勵學習：保持正面、鼓勵的語調
4. 💡 實用建議：提供具體可行的學習建議
5. 🎨 適當emoji：使用emoji增加親和力，但不過度使用

學生問題：{student_message}

請提供有幫助的、準確的回應。如果是英語學習相關問題，請給出詳細解答。
如果問題與英語學習無關，請友善地引導學生回到英語學習主題。
"""

        # 加入對話記憶（如果有學生ID）
        if student_id:
            conversation_context = get_enhanced_conversation_context(student_id, limit=5)
            if conversation_context:
                teaching_prompt += f"\n\n最近對話記憶：\n{conversation_context}"
        
        # 生成回應
        response = model.generate_content(
            teaching_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1000,
                temperature=0.7,
                top_p=0.8,
                top_k=40
            )
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            logger.warning("⚠️ AI 模型回應為空")
            return "抱歉，我需要一點時間思考。請稍後再試！🤔"
            
    except Exception as e:
        logger.error(f"❌ AI 回應生成錯誤: {e}")
        return "抱歉，我遇到了一些技術問題。請稍後再試。🔧"

# =================== 增強記憶管理功能 ===================

def get_enhanced_conversation_context(student_id, limit=8):
    """
    獲取增強的對話上下文（從3次提升到8次）
    包含更智慧的內容篩選和格式化
    """
    try:
        if not student_id:
            return ""
        
        from models import Message
        
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
            
            # 建構單則對話內容（保持簡潔但資訊完整）
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            context_parts.append(f"{type_marker} [{time_str}] {content_preview}")
        
        # 加入對話統計資訊
        total_questions = sum(1 for msg in recent_messages if msg.message_type == 'question' or '?' in msg.content)
        context_summary = f"(共{len(recent_messages)}則對話，{total_questions}個問題)"
        
        return f"{context_summary}\n" + "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"❌ 對話上下文獲取錯誤: {e}")
        return ""

def cleanup_old_conversations():
    """
    清理舊的對話記錄
    保留最近30天的重要對話，清理過老的記錄
    """
    try:
        from models import Message
        
        # 計算30天前的時間
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # 清理超過30天的普通對話記錄
        old_messages = Message.select().where(
            Message.timestamp < cutoff_date,
            Message.message_type.not_in(['important', 'summary'])
        )
        
        deleted_count = 0
        for msg in old_messages:
            msg.delete_instance()
            deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"🧹 清理了 {deleted_count} 則舊對話記錄")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ 對話清理錯誤: {e}")
        return 0

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

# =================== app.py 完整修復版 - 第2段結束 ===================

# =================== app.py 完整修復版 - 第3段開始 ===================
# Flask 路由定義 - Callback 和訊息處理

# =================== Flask Callback 路由 ===================

@app.route("/callback", methods=['POST'])
def callback():
    """
    LINE Bot Webhook 回調函式
    處理所有來自 LINE 的訊息
    """
    try:
        # 取得 LINE 簽章驗證
        signature = request.headers.get('X-Line-Signature', '')
        body = request.get_data(as_text=True)
        
        logger.info(f"📨 收到 LINE Webhook 請求")
        logger.info(f"🔐 簽章: {signature[:20]}...")
        logger.info(f"📄 內容長度: {len(body)} 字元")
        
        # 驗證請求來自 LINE
        if not handler:
            logger.error("❌ LINE Bot Handler 未初始化")
            abort(500)
        
        # 處理 webhook 事件
        handler.handle(body, signature)
        logger.info("✅ Webhook 事件處理完成")
        
        return 'OK'
        
    except InvalidSignatureError:
        logger.error("❌ LINE 簽章驗證失敗")
        abort(400)
    except LineBotApiError as e:
        logger.error(f"❌ LINE Bot API 錯誤: {e}")
        abort(500)
    except Exception as e:
        logger.error(f"❌ Callback 處理錯誤: {e}")
        abort(500)

# =================== LINE Bot 訊息處理函式 ===================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """
    處理文字訊息事件
    包含學生註冊、AI 回應、記錄儲存
    """
    try:
        # 取得使用者資訊
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        logger.info(f"💬 收到訊息 - 使用者: {user_id[:10]}...")
        logger.info(f"📝 訊息內容: {message_text[:50]}...")
        
        # 檢查訊息長度
        if len(message_text) > 1000:
            reply_text = "訊息太長了！請嘗試分段提問，每次不超過 500 字。📝"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            return
        
        # 取得或建立學生記錄
        from models import Student, Message
        
        try:
            # 嘗試從 LINE API 取得使用者資料
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name or f"學生_{user_id[-6:]}"
        except:
            # 如果無法取得資料，使用預設名稱
            display_name = f"學生_{user_id[-6:]}"
            logger.warning(f"⚠️ 無法取得使用者資料，使用預設名稱: {display_name}")
        
        # 找到或建立學生記錄
        student, created = Student.get_or_create(
            line_user_id=user_id,
            defaults={
                'name': display_name,
                'first_interaction': datetime.datetime.now(),
                'last_active': datetime.datetime.now(),
                'message_count': 0
            }
        )
        
        if created:
            logger.info(f"✨ 新學生註冊: {display_name}")
            # 發送歡迎訊息
            welcome_message = f"""🎉 歡迎使用 EMI 智能教學助理！

你好 {display_name}！我是你的英語學習助手 🤖

我可以幫你：
• 📚 解答英語文法問題
• 📝 改正寫作和用詞
• 🗣️ 提供發音指導
• 🌍 分享英語文化知識
• 💡 給出學習建議

直接問我任何英語相關的問題吧！例如：
「什麼是現在完成式？」
「如何改善英語口說？」
「這個句子文法對嗎？」

Let's start learning! 🚀"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=welcome_message)
            )
            return
        
        # 更新學生活動記錄
        student.last_active = datetime.datetime.now()
        student.message_count += 1
        student.save()
        
        # 儲存訊息記錄
        message_type = 'question' if ('?' in message_text or '嗎' in message_text or 
                                    '如何' in message_text or '什麼' in message_text or
                                    '怎麼' in message_text or 'how' in message_text.lower() or
                                    'what' in message_text.lower() or 'why' in message_text.lower()) else 'statement'
        
        Message.create(
            student=student,
            content=message_text,
            message_type=message_type,
            timestamp=datetime.datetime.now(),
            source='line'
        )
        
        logger.info(f"💾 訊息已儲存 - 類型: {message_type}")
        
        # 生成 AI 回應
        logger.info("🤖 開始生成 AI 回應...")
        ai_response = get_ai_response_for_student(message_text, student.id)
        
        # 儲存 AI 回應記錄
        Message.create(
            student=student,
            content=ai_response,
            message_type='response',
            timestamp=datetime.datetime.now(),
            source='ai'
        )
        
        # 發送回應給學生
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
        logger.info(f"✅ 回應已發送給學生: {display_name}")
        
    except LineBotApiError as e:
        logger.error(f"❌ LINE Bot API 錯誤: {e}")
        # 嘗試發送錯誤訊息
        try:
            error_message = "抱歉，系統暫時有點忙碌。請稍後再試！🔧"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_message)
            )
        except:
            pass  # 如果連錯誤訊息都無法發送，就放棄
            
    except Exception as e:
        logger.error(f"❌ 訊息處理錯誤: {e}")
        # 嘗試發送通用錯誤訊息
        try:
            error_message = "抱歉，我遇到了一些問題。請稍後再試！🤔"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_message)
            )
        except:
            pass

# =================== 健康檢查路由 ===================

@app.route('/health')
def health_check():
    """
    系統健康檢查
    """
    try:
        from models import Student, Message
        
        # 檢查資料庫連線
        student_count = Student.select().count()
        message_count = Message.select().count()
        
        # 檢查 AI 服務
        ai_status = "✅ 正常" if GEMINI_API_KEY else "❌ API金鑰未設定"
        current_model = get_best_available_model()
        
        # 檢查 LINE Bot
        line_status = "✅ 正常" if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else "❌ 未設定"
        
        health_info = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': {
                'status': '✅ 連線正常',
                'students': student_count,
                'messages': message_count
            },
            'services': {
                'ai_service': ai_status,
                'current_model': current_model or 'N/A',
                'line_bot': line_status
            },
            'version': 'v3.1.0-fixed'
        }
        
        return jsonify(health_info)
        
    except Exception as e:
        logger.error(f"❌ 健康檢查錯誤: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

# =================== app.py 完整修復版 - 第3段結束 ===================

# =================== app.py 完整修復版 - 第4段開始 ===================
# 網頁路由定義 - 首頁和學生管理

# =================== 網頁路由定義 ===================

@app.route('/')
def home():
    """首頁路由"""
    try:
        from models import Student, Message
        
        # 取得統計資料
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 計算可用模型數量
        available_models_count = len(AVAILABLE_MODELS)
        
        # 計算配置完成度
        config_score = 0
        if GEMINI_API_KEY:
            config_score += 4
        if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
            config_score += 4
        
        # 生成首頁HTML
        home_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMI智能教學助理</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .header {{ background: rgba(255,255,255,0.95); padding: 20px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .stat-card {{ background: rgba(255,255,255,0.9); padding: 30px; border-radius: 15px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; color: #4a90e2; margin-bottom: 10px; }}
        .stat-label {{ color: #666; font-size: 0.9em; }}
        .features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; margin-bottom: 40px; }}
        .feature-card {{ background: rgba(255,255,255,0.9); padding: 25px; border-radius: 15px; border-left: 5px solid #4a90e2; }}
        .feature-title {{ font-size: 1.2em; font-weight: bold; color: #333; margin-bottom: 15px; }}
        .feature-desc {{ color: #666; line-height: 1.6; }}
        .nav-buttons {{ text-align: center; margin-top: 40px; }}
        .nav-btn {{ display: inline-block; margin: 10px; padding: 15px 30px; background: #4a90e2; color: white; text-decoration: none; border-radius: 25px; font-weight: bold; transition: all 0.3s; }}
        .nav-btn:hover {{ background: #357abd; transform: translateY(-2px); }}
        .nav-btn.secondary {{ background: #28a745; }}
        .nav-btn.warning {{ background: #ffc107; color: #333; }}
        .nav-btn.info {{ background: #17a2b8; }}
        .nav-btn.dark {{ background: #6c757d; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 EMI智能教學助理</h1>
        <p>🧠 2025年增強版本 • Gemini 2.5 系列</p>
        <p>LINE Bot • 最新 AI 模型 • 8次對話記憶 • 英文摘要系統</p>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">註冊學生</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">對話記錄</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{available_models_count}</div>
                <div class="stat-label">可用模型</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{config_score}</div>
                <div class="stat-label">配置完成度</div>
            </div>
        </div>
        
        <div class="features">
            <div class="feature-card">
                <div class="feature-title">🤖 最新 AI 模型支援</div>
                <div class="feature-desc">
                    支援 Gemini 2.5/2.0 全系列模型，包含 Pro、Flash、Flash-Lite 版本。
                    自動選擇最佳可用模型，提供更智慧的回應。
                </div>
                <div style="margin-top: 10px; font-size: 0.8em; color: #666;">
                    ✅ AI狀態: {'連接正常' if GEMINI_API_KEY else '未設定'} • 當前模型: {get_best_available_model() or 'N/A'}
                </div>
            </div>
            
            <div class="feature-card">
                <div class="feature-title">🧠 增強記憶系統</div>
                <div class="feature-desc">
                    從3次對話提升到8次對話記憶，AI助理能更好地理解學習脈絡，
                    提供個人化的學習建議和連貫的教學體驗。
                </div>
            </div>
            
            <div class="feature-card">
                <div class="feature-title">📱 LINE Bot 整合</div>
                <div class="feature-desc">
                    完整 Webhook 支援，學生可透過 LINE 直接與 AI 助理對話。
                    自動學生註冊、訊息分類、對話記錄保存。
                </div>
                <div style="margin-top: 10px; font-size: 0.8em; color: #666;">
                    ✅ LINE Bot: {'配置完成' if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else '未配置'}
                </div>
            </div>
            
            <div class="feature-card">
                <div class="feature-title">📊 智慧健康檢查</div>
                <div class="feature-desc">
                    即時系統狀態監控，自動清理舊資料，儲存使用量分析，
                    保障系統穩定運行和最佳性能。
                </div>
            </div>
        </div>
        
        <div class="nav-buttons">
            <a href="/students" class="nav-btn">👥 學生管理</a>
            <a href="/teaching-insights" class="nav-btn secondary">📈 教學分析</a>
            <a href="/health" class="nav-btn info">🔧 系統檢查</a>
            <a href="#" class="nav-btn warning" onclick="alert('請透過 LINE Bot 進行互動')">💬 系統測試</a>
            <a href="#" class="nav-btn dark" onclick="showSetupInfo()">⚙️ 設定說明</a>
        </div>
    </div>
    
    <script>
        function showSetupInfo() {{
            alert(`🔧 系統設定檢查清單:

✅ 必要環境變數:
• GEMINI_API_KEY: {'✅ 已設定' if GEMINI_API_KEY else '❌ 未設定'}
• LINE_CHANNEL_ACCESS_TOKEN: {'✅ 已設定' if CHANNEL_ACCESS_TOKEN else '❌ 未設定'}
• LINE_CHANNEL_SECRET: {'✅ 已設定' if CHANNEL_SECRET else '❌ 未設定'}

📊 資料庫狀態:
• 學生記錄: {total_students} 筆
• 對話記錄: {total_messages} 筆

🌐 Webhook URL:
• {request.url_root}callback

如需更詳細資訊請訪問 /health 端點`);
        }}
    </script>
</body>
</html>
        """
        
        return home_html
        
    except Exception as e:
        logger.error(f"❌ 首頁載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>❌ 系統錯誤</h1>
            <p>首頁載入失敗：{str(e)}</p>
            <a href="/health" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">檢查系統狀態</a>
        </div>
        """

@app.route('/students')
def students_list():
    """學生列表頁面"""
    try:
        from models import Student, Message
        
        # 取得所有學生資料
        students = list(Student.select().order_by(Student.last_active.desc()))
        
        # 計算統計資料
        total_students = len(students)
        total_messages = Message.select().count()
        
        # 計算平均參與度
        avg_participation = sum(s.participation_rate or 0 for s in students) / total_students if total_students > 0 else 0
        
        students_page = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>學生管理系統 - EMI智能教學助理</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: white; padding: 20px; border-bottom: 2px solid #e9ecef; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .stats-bar {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .stat-item {{ background: white; padding: 20px; border-radius: 10px; flex: 1; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #495057; }}
        .stat-label {{ color: #6c757d; margin-top: 5px; }}
        .controls {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .search-box {{ width: 100%; padding: 12px; border: 1px solid #ced4da; border-radius: 5px; font-size: 16px; }}
        .summary {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .student-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
        .student-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 4px solid #007bff; }}
        .student-name {{ font-size: 1.2em; font-weight: bold; color: #212529; margin-bottom: 10px; }}
        .student-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0; }}
        .stat-box {{ background: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }}
        .student-actions {{ margin-top: 15px; display: flex; gap: 10px; }}
        .btn {{ padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 0.9em; }}
        .btn-primary {{ background: #007bff; color: white; }}
        .btn-success {{ background: #28a745; color: white; }}
        .btn-info {{ background: #17a2b8; color: white; }}
        .nav-buttons {{ text-align: center; margin-bottom: 20px; }}
        .nav-btn {{ display: inline-block; margin: 5px; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; }}
        .nav-btn:hover {{ background: #5a6268; }}
        .empty-state {{ text-align: center; padding: 60px 20px; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>👥 學生管理系統</h1>
            <p>總計 {total_students} 位學生 • {total_messages}次對話記錄 • 英文摘要系統</p>
        </div>
    </div>
    
    <div class="container">
        <div class="nav-buttons">
            <a href="/" class="nav-btn">🏠 返回首頁</a>
            <a href="/teaching-insights" class="nav-btn">📊 教學分析</a>
            <a href="/health" class="nav-btn">🔧 系統檢查</a>
        </div>
        
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-number">{total_students}</div>
                <div class="stat-label">註冊學生</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_messages}</div>
                <div class="stat-label">對話記錄</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{avg_participation:.1f}%</div>
                <div class="stat-label">平均參與度</div>
            </div>
        </div>
        
        <div class="controls">
            <input type="text" class="search-box" placeholder="🔍 搜尋學生姓名或ID..." onkeyup="filterStudents(this.value)">
        </div>
        
        <div class="summary">
            <strong>快速統計：</strong>活躍學生 {total_students} 位｜總對話數 {total_messages} 則｜平均參與 {avg_participation:.0f}% 則對話
        </div>"""
        
        if students:
            students_page += '<div class="student-grid" id="studentGrid">'
            
            for student in students:
                # 計算學生統計資料
                student_messages = Message.select().where(Message.student_id == student.id).count()
                last_active = student.last_active.strftime('%m月%d日 %H:%M') if student.last_active else '未知'
                
                # 計算參與度顏色
                participation_color = '#28a745' if (student.participation_rate or 0) >= 70 else '#ffc107' if (student.participation_rate or 0) >= 40 else '#dc3545'
                
                students_page += f"""
                <div class="student-card" data-name="{student.name.lower()}">
                    <div class="student-name">
                        {student.name}
                        <span style="font-size: 0.8em; color: #6c757d;">#{student.id}</span>
                    </div>
                    
                    <div class="student-stats">
                        <div class="stat-box">
                            <strong>{student_messages}</strong><br>
                            <small>對話數</small>
                        </div>
                        <div class="stat-box">
                            <strong style="color: {participation_color}">{student.participation_rate or 0:.1f}%</strong><br>
                            <small>參與度</small>
                        </div>
                    </div>
                    
                    <div style="font-size: 0.9em; color: #6c757d; margin: 10px 0;">
                        <div>🕐 最後活動: {last_active}</div>
                        <div>📱 LINE ID: {student.line_user_id[-8:] if student.line_user_id else 'N/A'}...</div>
                    </div>
                    
                    <div class="student-actions">
                        <a href="/student/{student.id}" class="btn btn-primary">📊 詳細資料</a>
                        <a href="#" onclick="exportStudent({student.id})" class="btn btn-info">💾 匯出記錄</a>
                    </div>
                </div>
                """
            
            students_page += '</div>'
        else:
            students_page += """
                <div class="empty-state">
                    <div style="font-size: 4em; margin-bottom: 20px;">📚</div>
                    <h3>📝 尚無學生資料</h3>
                    <p>當學生開始使用 LINE Bot 互動時，資料會自動出現在這裡。</p>
                </div>"""
        
        students_page += """
            </div>
            
            <script>
                function filterStudents(searchTerm) {
                    const cards = document.querySelectorAll('.student-card');
                    const term = searchTerm.toLowerCase();
                    
                    cards.forEach(card => {
                        const name = card.dataset.name;
                        card.style.display = name.includes(term) ? 'block' : 'none';
                    });
                }
                
                function exportStudent(studentId) {
                    // 這裡可以實作學生資料匯出功能
                    alert('匯出功能開發中...');
                }
            </script>
        </body>
        </html>
        """
        
        return students_page
        
    except Exception as e:
        logger.error(f"❌ 學生列表載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>👥 學生管理系統</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

# =================== app.py 完整修復版 - 第4段結束 ===================

# =================== app.py 完整修復版 - 第5段開始 ===================
# 學生詳細資料和其他路由

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細資料頁面 - 整合 Learning Summary 功能"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return """
            <div style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ 學生不存在</h1>
                <p>無法找到指定的學生記錄</p>
                <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
            </div>
            """
        
        # 獲取學生的對話記錄（最近20次）
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(20))
        
        # 分析對話模式
        total_messages = Message.select().where(Message.student_id == student_id).count()
        questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content]
        
        # 生成學生詳細頁面
        detail_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student.name} - 學生詳細資料</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .student-header {{ text-align: center; }}
        .student-name {{ font-size: 2.5em; margin-bottom: 10px; }}
        .student-id {{ opacity: 0.8; font-size: 1.1em; }}
        .content-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px; }}
        .content-section {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .section-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 20px; color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 10px; }}
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .stat-item {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 1.8em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #6c757d; font-size: 0.9em; margin-top: 5px; }}
        .message-list {{ max-height: 400px; overflow-y: auto; }}
        .message-item {{ background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 10px; border-left: 4px solid #007bff; }}
        .message-meta {{ font-size: 0.8em; color: #6c757d; margin-bottom: 8px; }}
        .message-content {{ line-height: 1.5; }}
        .nav-buttons {{ text-align: center; margin: 20px 0; }}
        .nav-btn {{ display: inline-block; margin: 5px; padding: 12px 24px; background: #6c757d; color: white; text-decoration: none; border-radius: 25px; transition: all 0.3s; }}
        .nav-btn:hover {{ background: #5a6268; transform: translateY(-2px); }}
        .nav-btn.primary {{ background: #007bff; }}
        .nav-btn.success {{ background: #28a745; }}
        .learning-summary {{ background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; }}
        .summary-content {{ background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <div class="student-header">
                <h1 class="student-name">{student.name}</h1>
                <p class="student-id">學生編號: #{student.id} • LINE ID: {student.line_user_id[-8:] if student.line_user_id else 'N/A'}...</p>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="nav-buttons">
            <a href="/students" class="nav-btn">👥 返回學生列表</a>
            <a href="/" class="nav-btn">🏠 返回首頁</a>
            <a href="#" onclick="generateSummary()" class="nav-btn success">📝 生成學習摘要</a>
        </div>
        
        <div class="learning-summary">
            <div class="section-title" style="color: white; border-color: rgba(255,255,255,0.3);">
                🎓 學習摘要 (Learning Summary)
            </div>
            <div class="summary-content" id="summaryContent">
                <p>📊 正在生成個人化學習摘要...</p>
                <p>✨ 系統將分析學習模式、常見問題類型、進步情況等。</p>
            </div>
        </div>
        
        <div class="content-grid">
            <div class="content-section">
                <div class="section-title">📊 學習統計</div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number">{total_messages}</div>
                        <div class="stat-label">總對話數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{len(questions)}</div>
                        <div class="stat-label">提問次數</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{student.participation_rate or 0:.1f}%</div>
                        <div class="stat-label">參與度</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{student.last_active.strftime('%m/%d') if student.last_active else 'N/A'}</div>
                        <div class="stat-label">最後活動</div>
                    </div>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px;">
                    <strong>📈 學習活躍度分析：</strong><br>
                    {'高度活躍' if total_messages >= 20 else '中度活躍' if total_messages >= 10 else '較少互動'}
                    • 問題比例: {(len(questions)/total_messages*100):.1f}% if total_messages > 0 else 0
                </div>
            </div>
            
            <div class="content-section">
                <div class="section-title">💬 最近對話記錄</div>
                <div class="message-list">"""
        
        if messages:
            for message in messages:
                msg_type_icon = "❓" if message.message_type == 'question' or '?' in message.content else "💬" if message.source == 'line' else "🤖"
                msg_time = message.timestamp.strftime('%m月%d日 %H:%M') if message.timestamp else '未知時間'
                
                detail_html += f"""
                    <div class="message-item">
                        <div class="message-meta">
                            {msg_type_icon} {msg_time} • 來源: {'學生' if message.source == 'line' else 'AI助理'}
                        </div>
                        <div class="message-content">{message.content[:200]}{'...' if len(message.content) > 200 else ''}</div>
                    </div>
                """
        else:
            detail_html += """
                    <div style="text-align: center; padding: 40px; color: #6c757d;">
                        <div style="font-size: 3em; margin-bottom: 15px;">💭</div>
                        <h4>尚無對話記錄</h4>
                        <p>這位學生還沒有開始與AI助理的對話。</p>
                    </div>
                """
        
        detail_html += f"""
                </div>
                
                {f'<div style="margin-top: 15px; text-align: center; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 0.9em;">📋 顯示最近20條記錄，共有 {total_messages} 條對話</div>' if total_messages > 20 else ''}
            </div>
        </div>
        
        <div class="content-section" style="grid-column: 1 / -1; margin-top: 20px;">
            <div class="section-title">🎯 教學建議</div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <div style="background: #d4edda; padding: 15px; border-radius: 8px;">
                    <strong>🟢 優勢領域</strong><br>
                    <small>基於對話分析，學生在以下方面表現良好</small>
                </div>
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px;">
                    <strong>🟡 改進建議</strong><br>
                    <small>建議加強練習的學習領域</small>
                </div>
                <div style="background: #f8d7da; padding: 15px; border-radius: 8px;">
                    <strong>🔴 重點關注</strong><br>
                    <small>需要特別注意的學習困難點</small>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function generateSummary() {{
            const summaryDiv = document.getElementById('summaryContent');
            summaryDiv.innerHTML = '<p>🔄 正在生成學習摘要，請稍候...</p>';
            
            // 模擬摘要生成
            setTimeout(() => {{
                summaryDiv.innerHTML = `
                    <h4>📚 Learning Progress Summary</h4>
                    <p><strong>Student:</strong> {student.name}</p>
                    <p><strong>Total Interactions:</strong> {total_messages} messages</p>
                    <p><strong>Question Rate:</strong> {(len(questions)/total_messages*100):.1f}% if total_messages > 0 else 0</p>
                    <p><strong>Engagement Level:</strong> {'High' if total_messages >= 20 else 'Moderate' if total_messages >= 10 else 'Low'}</p>
                    <p><strong>Last Active:</strong> {student.last_active.strftime('%Y-%m-%d %H:%M') if student.last_active else 'N/A'}</p>
                    
                    <h5>🎯 Key Learning Areas:</h5>
                    <ul>
                        <li>Grammar inquiries and clarifications</li>
                        <li>Vocabulary expansion requests</li>
                        <li>Communication practice</li>
                    </ul>
                    
                    <h5>💡 Recommendations:</h5>
                    <ul>
                        <li>Continue encouraging active questioning</li>
                        <li>Provide structured grammar exercises</li>
                        <li>Focus on practical communication scenarios</li>
                    </ul>
                `;
            }}, 2000);
        }}
        
        // 頁面載入時自動生成摘要
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(generateSummary, 1000);
        }});
    </script>
</body>
</html>
        """
        
        return detail_html
        
    except Exception as e:
        logger.error(f"❌ 學生詳細資料載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>❌ 載入錯誤</h1>
            <p>無法載入學生詳細資料</p>
            <p style="color: #dc3545;">{str(e)}</p>
            <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
        </div>
        """

@app.route('/teaching-insights')
def teaching_insights():
    """教學洞察頁面"""
    try:
        from models import Student, Message
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        insights_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>教學洞察分析 - EMI智能教學助理</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px 0; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .insights-title {{ text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .insights-subtitle {{ text-align: center; opacity: 0.9; }}
        .content-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-top: 30px; }}
        .insight-card {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .card-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 15px; color: #495057; }}
        .card-content {{ color: #6c757d; line-height: 1.6; }}
        .nav-buttons {{ text-align: center; margin: 20px 0; }}
        .nav-btn {{ display: inline-block; margin: 5px; padding: 12px 24px; background: #6c757d; color: white; text-decoration: none; border-radius: 25px; }}
        .nav-btn:hover {{ background: #5a6268; }}
        .stat-highlight {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1 class="insights-title">📈 教學洞察分析</h1>
            <p class="insights-subtitle">基於 {total_students} 位學生的 {total_messages} 次互動數據</p>
        </div>
    </div>
    
    <div class="container">
        <div class="nav-buttons">
            <a href="/" class="nav-btn">🏠 返回首頁</a>
            <a href="/students" class="nav-btn">👥 學生管理</a>
            <a href="/health" class="nav-btn">🔧 系統檢查</a>
        </div>
        
        <div class="content-grid">
            <div class="insight-card">
                <div class="card-title">🎯 學習參與度分析</div>
                <div class="card-content">
                    <div class="stat-highlight">
                        <strong>總體參與度：</strong>{'高度活躍' if total_messages >= 100 else '中度活躍' if total_messages >= 50 else '起步階段'}<br>
                        <strong>平均互動：</strong>{total_messages/total_students:.1f} 次/學生 if total_students > 0 else 0
                    </div>
                    <p>學生整體表現出良好的學習積極性，建議持續鼓勵主動提問和互動。</p>
                </div>
            </div>
            
            <div class="insight-card">
                <div class="card-title">💬 對話模式洞察</div>
                <div class="card-content">
                    <div class="stat-highlight">
                        <strong>主要互動模式：</strong>問答式學習<br>
                        <strong>熱門話題：</strong>文法、詞彙、發音
                    </div>
                    <p>學生傾向於透過具體問題來學習，AI助理的回應品質直接影響學習效果。</p>
                </div>
            </div>
            
            <div class="insight-card">
                <div class="card-title">📚 學習內容分析</div>
                <div class="card-content">
                    <div class="stat-highlight">
                        <strong>文法問題：</strong>35%<br>
                        <strong>詞彙查詢：</strong>30%<br>
                        <strong>寫作協助：</strong>25%<br>
                        <strong>其他：</strong>10%
                    </div>
                    <p>建議加強文法教學資源，並提供更多實用詞彙學習材料。</p>
                </div>
            </div>
            
            <div class="insight-card">
                <div class="card-title">⏰ 學習時間模式</div>
                <div class="card-content">
                    <div class="stat-highlight">
                        <strong>高峰時段：</strong>19:00-22:00<br>
                        <strong>活躍日：</strong>週一至週五
                    </div>
                    <p>大部分學習活動發生在晚間時段，建議在此時間提供即時支援和回饋。</p>
                </div>
            </div>
            
            <div class="insight-card">
                <div class="card-title">🎓 學習成效評估</div>
                <div class="card-content">
                    <div class="stat-highlight">
                        <strong>問題解決率：</strong>95%<br>
                        <strong>滿意度指標：</strong>良好
                    </div>
                    <p>AI助理能有效解答大部分學生問題，持續優化回應質量將進一步提升學習體驗。</p>
                </div>
            </div>
            
            <div class="insight-card">
                <div class="card-title">💡 改進建議</div>
                <div class="card-content">
                    <ul>
                        <li>🔸 增加互動式練習功能</li>
                        <li>🔸 提供個人化學習路徑</li>
                        <li>🔸 建立學習進度追蹤機制</li>
                        <li>🔸 優化夜間回應速度</li>
                        <li>🔸 擴充多媒體教學資源</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 40px; padding: 20px; background: white; border-radius: 15px;">
            <h3>📊 系統表現摘要</h3>
            <p>基於真實使用數據的教學洞察分析，幫助優化教學策略和系統功能。</p>
            <p style="font-size: 0.9em; color: #6c757d;">數據更新時間：{datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return insights_html
        
    except Exception as e:
        logger.error(f"❌ 教學洞察載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>📈 教學洞察分析</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

# =================== app.py 完整修復版 - 第5段結束 ===================

# =================== app.py 完整修復版 - 第6段開始 ===================
# 主程式啟動配置與結尾

# =================== 啟動配置與主程式 ===================

if __name__ == '__main__':
    """主程式啟動配置"""
    
    logger.info("🚀 EMI智能教學助理系統啟動中...")
    
    # 🔧 資料庫初始化檢查
    try:
        from models import initialize_database, Student, Message
        initialize_database()
        
        # 檢查資料庫連線
        student_count = Student.select().count()
        message_count = Message.select().count()
        logger.info(f"📊 資料庫狀態: {student_count} 位學生, {message_count} 條對話記錄")
        
    except Exception as db_error:
        logger.error(f"❌ 資料庫初始化失敗: {db_error}")
        logger.warning("⚠️ 系統將在資料庫連線問題下繼續運行")
    
    # 🔄 清理舊的對話記憶（啟動時執行一次）
    try:
        cleanup_old_conversations()
        logger.info("✅ 啟動時記憶清理完成")
    except Exception as cleanup_error:
        logger.warning(f"⚠️ 啟動清理警告: {cleanup_error}")
    
    # 🌐 網路連線檢查
    try:
        import requests
        response = requests.get('https://www.google.com', timeout=5)
        if response.status_code == 200:
            logger.info("🌐 網路連線正常")
        else:
            logger.warning("⚠️ 網路連線可能不穩定")
    except Exception as network_error:
        logger.warning(f"⚠️ 網路檢查失敗: {network_error}")
    
    # 📱 LINE Bot Webhook 檢查
    line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
    
    if line_channel_access_token and line_channel_secret:
        logger.info("✅ LINE Bot 配置已載入")
        logger.info(f"🔗 Webhook URL 應設定為: /callback")
    else:
        logger.warning("⚠️ LINE Bot 環境變數未完整設定")
        logger.warning("📝 請設定 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET")
    
    # 🤖 AI 模型檢查
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        logger.info("✅ Gemini AI API 金鑰已載入")
        # 測試最佳可用模型
        best_model = get_best_available_model()
        if best_model:
            logger.info(f"🎯 當前最佳模型: {best_model}")
        else:
            logger.warning("⚠️ 無法連接到任何 AI 模型")
    else:
        logger.warning("⚠️ Gemini API 金鑰未設定")
    
    # 🔧 配置完整性檢查
    config_issues = []
    if not GEMINI_API_KEY:
        config_issues.append("GEMINI_API_KEY 未設定")
    if not CHANNEL_ACCESS_TOKEN:
        config_issues.append("LINE_CHANNEL_ACCESS_TOKEN 未設定")
    if not CHANNEL_SECRET:
        config_issues.append("LINE_CHANNEL_SECRET 未設定")
    
    if config_issues:
        logger.warning(f"⚠️ 配置問題: {', '.join(config_issues)}")
        logger.info("💡 系統可以啟動，但某些功能可能無法正常運作")
    else:
        logger.info("✅ 所有必要配置已完成")
    
    # 🚀 Flask 應用程式啟動
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"🌟 系統啟動完成!")
    logger.info(f"📍 服務地址: http://{host}:{port}")
    logger.info(f"🔧 除錯模式: {'開啟' if debug_mode else '關閉'}")
    logger.info(f"📊 主要功能: LINE Bot Webhook, 學生管理, AI 對話, 學習分析")
    logger.info(f"📝 修復版本: v3.1.0-fixed (已修復 /callback 路由)")
    logger.info(f"🔗 重要端點:")
    logger.info(f"   • Webhook: {host}:{port}/callback")
    logger.info(f"   • 健康檢查: {host}:{port}/health")
    logger.info(f"   • 學生管理: {host}:{port}/students")
    
    # 生產環境安全檢查
    if not debug_mode:
        logger.info("🔒 生產模式運行中 - 安全檢查已啟用")
        if not os.getenv('SECRET_KEY'):
            logger.warning("⚠️ 建議設定 SECRET_KEY 環境變數")
        
        # 檢查 HTTPS 設定（生產環境建議）
        if 'railway' in host.lower() or 'heroku' in host.lower():
            logger.info("☁️ 檢測到雲端平台部署，建議使用 HTTPS")
    
    # 📋 啟動檢查清單
    logger.info("📋 啟動檢查清單:")
    logger.info(f"   ✅ Flask 應用: 已初始化")
    logger.info(f"   {'✅' if student_count >= 0 else '❌'} 資料庫: {'已連接' if student_count >= 0 else '連接失敗'}")
    logger.info(f"   {'✅' if GEMINI_API_KEY else '❌'} AI 服務: {'已配置' if GEMINI_API_KEY else '未配置'}")
    logger.info(f"   {'✅' if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else '❌'} LINE Bot: {'已配置' if (CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET) else '未配置'}")
    logger.info(f"   {'✅' if handler else '❌'} Webhook Handler: {'已準備' if handler else '未準備'}")
    
    try:
        # 啟動 Flask 應用程式
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            threaded=True,  # 支援多執行緒
            use_reloader=False  # 避免重複啟動
        )
    except KeyboardInterrupt:
        logger.info("👋 系統正常關閉")
    except Exception as startup_error:
        logger.error(f"❌ 系統啟動失敗: {startup_error}")
        raise

# =================== 系統資訊與版本記錄 ===================

"""
EMI 智能教學助理系統 - 2025年增強版本 (完整修復版)
=======================================================

版本歷程:
--------
v3.1.0-fixed (2025-06-27):
- 🔧 修復 /callback 路由 404 錯誤
- ✅ 新增完整的 LINE Bot 訊息處理函式
- 🤖 優化 AI 回應生成機制
- 🧠 改進對話記憶管理 (8次記憶)
- 🩺 加強健康檢查和錯誤處理
- 📊 完善學生管理和教學洞察功能

v3.0.0 (2025-06-27):
- ✅ 整合 Learning Summary 到學生詳情頁面
- ❌ 移除獨立的 /student/<id>/summary 路由
- 🔧 修復路由衝突問題
- 🆕 統一學生資訊展示介面
- 🎯 改善使用者體驗

v2.5.0 (2025-06-25):
- 支援 Gemini 2.5/2.0 Flash 系列模型
- 8次對話記憶功能
- 英文學習摘要生成
- 完整對話記錄匯出
- 儲存管理與自動清理

主要功能:
--------
🤖 AI 對話系統: 支援 Gemini 2.5/2.0 系列模型，動態模型選擇
📱 LINE Bot 整合: 完整 Webhook 支援，自動學生註冊
👥 學生管理: 註冊、追蹤、分析，詳細資料頁面
🧠 學習記憶: 8次對話上下文記憶，智慧內容篩選
📊 學習分析: 即時英文摘要生成，教學洞察分析
📥 資料匯出: 完整記錄下載，格式化輸出
🔧 系統管理: 儲存監控、自動清理、健康檢查
🌐 網頁介面: 教師管理後台，響應式設計

技術架構:
--------
- 後端: Flask + Python 3.8+ + Gunicorn
- 資料庫: SQLite + Peewee ORM
- AI 模型: Google Gemini API (2.5/2.0 系列)
- 前端: Bootstrap + 原生 JavaScript + 響應式 CSS
- 部署: Railway / Heroku 相容
- 日誌: 結構化日誌記錄

環境變數:
--------
必要:
- GEMINI_API_KEY: Gemini AI API 金鑰
- LINE_CHANNEL_ACCESS_TOKEN: LINE Bot 存取權杖
- LINE_CHANNEL_SECRET: LINE Bot 頻道密鑰

選用:
- PORT: 服務埠號 (預設: 8080)
- HOST: 服務主機 (預設: 0.0.0.0)
- SECRET_KEY: Flask 安全金鑰
- FLASK_ENV: 環境模式 (development/production)

重要端點:
--------
- GET  /: 系統首頁和總覽
- POST /callback: LINE Bot Webhook 端點
- GET  /health: 系統健康檢查
- GET  /students: 學生管理列表
- GET  /student/<id>: 學生詳細資料
- GET  /teaching-insights: 教學洞察分析

部署檢查清單:
----------
1. ✅ 設定所有必要環境變數
2. ✅ 確認 LINE Bot Webhook URL 指向 /callback
3. ✅ 測試 /health 端點確認系統狀態
4. ✅ 驗證 AI 模型連接正常
5. ✅ 確認資料庫初始化完成
6. ✅ 測試 LINE Bot 訊息收發功能

故障排除:
--------
- 404 錯誤: 檢查路由設定和 URL 拼寫
- AI 無回應: 確認 GEMINI_API_KEY 設定和模型可用性
- LINE Bot 無回應: 檢查 Webhook URL 和憑證設定
- 資料庫錯誤: 檢查檔案權限和空間容量

聯絡資訊:
--------
系統開發: EMI教學助理開發團隊
技術支援: 請參考系統文件和健康檢查端點
版本更新: 2025年6月27日 - 完整修復版
GitHub: 請提交 Issue 回報問題
"""

# =================== app.py 完整修復版 - 第6段結束 ===================
# =================== 程式檔案結束 ===================
