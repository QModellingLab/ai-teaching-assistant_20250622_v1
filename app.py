# =================== app.py 修改版 - 第 1 段開始 ===================
# EMI智能教學助理系統 - 2025年增強版本
# 支援最新 Gemini 2.5/2.0 系列模型 + 8次對話記憶 + 英文摘要 + 完整匯出
# 修改：整合Learning Summary到學生詳情頁面，移除重複路由
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
        "cost_tier": "balanced",
        "free_limit": "high",
        "best_for": "日常教學、快速回應、平衡任務"
    },
    "gemini-2.5-pro": {
        "generation": "2.5",
        "type": "Pro",
        "features": ["thinking", "coding", "complex_reasoning", "1M_context"],
        "cost_tier": "premium",
        "free_limit": "moderate",
        "best_for": "複雜分析、高級編程、深度思考任務"
    },
    "gemini-2.5-flash-lite": {
        "generation": "2.5",
        "type": "Flash-Lite",
        "features": ["ultra_fast", "ultra_cheap", "high_throughput", "thinking"],
        "cost_tier": "economy",
        "free_limit": "very_high",
        "best_for": "大量請求、分類、摘要任務"
    },
    "gemini-2.0-flash": {
        "generation": "2.0",
        "type": "Flash",
        "features": ["agentic", "multimodal", "low_latency", "stable"],
        "cost_tier": "standard",
        "free_limit": "high",
        "best_for": "代理任務、即時互動、穩定服務"
    },
    "gemini-2.0-pro": {
        "generation": "2.0",
        "type": "Pro",
        "features": ["experimental", "coding_expert", "2M_context", "tools"],
        "cost_tier": "premium",
        "free_limit": "limited",
        "best_for": "實驗性編程、大型文檔分析"
    },
    "gemini-2.0-flash-lite": {
        "generation": "2.0",
        "type": "Flash-Lite",
        "features": ["cost_efficient", "improved_quality", "1M_context"],
        "cost_tier": "economy",
        "free_limit": "very_high",
        "best_for": "成本敏感任務、高頻使用"
    },
    # 備用模型
    "gemini-1.5-flash": {
        "generation": "1.5",
        "type": "Flash",
        "features": ["mature", "stable", "reliable"],
        "cost_tier": "standard",
        "free_limit": "moderate",
        "best_for": "穩定生產環境"
    },
    "gemini-1.5-flash-8b": {
        "generation": "1.5",
        "type": "Flash-8B",
        "features": ["optimized", "efficient"],
        "cost_tier": "economy",
        "free_limit": "moderate",
        "best_for": "效率優化場景"
    },
    "gemini-1.5-pro": {
        "generation": "1.5",
        "type": "Pro",
        "features": ["comprehensive", "slower"],
        "cost_tier": "premium",
        "free_limit": "limited",
        "best_for": "完整功能需求"
    },
    "gemini-1.0-pro": {
        "generation": "1.0",
        "type": "Pro",
        "features": ["legacy", "stable"],
        "cost_tier": "standard",
        "free_limit": "basic",
        "best_for": "最後備用方案"
    }
}

# 模型使用統計 - 更新為包含新模型
model_usage_stats = {
    model: {
        'calls': 0, 
        'errors': 0, 
        'last_used': None, 
        'generation': MODEL_SPECIFICATIONS[model]['generation'],
        'success_rate': 0.0
    } for model in AVAILABLE_MODELS
}

# =================== AI 模型初始化和管理 ===================

import google.generativeai as genai

# 初始化 AI 模型
model = None
current_model_name = "gemini-2.5-flash"  # 預設使用最新的 2.5 Flash
model_rotation_index = 0

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 現在預設使用最新的 2.5 Flash（最佳性價比）
        model = genai.GenerativeModel(current_model_name)
        logger.info(f"✅ Gemini AI 初始化成功 - 使用最新模型: {current_model_name}")
    except Exception as e:
        logger.warning(f"⚠️ 最新模型初始化失敗，嘗試備用模型: {e}")
        # 如果最新模型失敗，按優先順序嘗試其他模型
        for backup_model in AVAILABLE_MODELS[1:]:
            try:
                model = genai.GenerativeModel(backup_model)
                current_model_name = backup_model
                logger.info(f"✅ 成功切換到備用模型: {backup_model}")
                break
            except Exception as backup_error:
                logger.warning(f"⚠️ 備用模型 {backup_model} 也失敗: {backup_error}")
                continue
        else:
            logger.error("❌ 所有模型都無法初始化")
            model = None
else:
    logger.warning("⚠️ GEMINI_API_KEY 未設定")

# =================== 增強的模型管理函數 ===================

def get_model_generation(model_name: str) -> str:
    """取得模型世代資訊"""
    return MODEL_SPECIFICATIONS.get(model_name, {}).get('generation', 'unknown')

def get_model_best_use_case(model_name: str) -> str:
    """取得模型最佳使用場景"""
    return MODEL_SPECIFICATIONS.get(model_name, {}).get('best_for', '一般用途')

def get_recommended_model_for_task(task_type: str) -> str:
    """根據任務類型推薦最佳模型"""
    recommendations = {
        'complex_analysis': 'gemini-2.5-pro',
        'daily_teaching': 'gemini-2.5-flash',
        'bulk_requests': 'gemini-2.5-flash-lite',
        'coding': 'gemini-2.0-pro',
        'real_time': 'gemini-2.0-flash',
        'cost_sensitive': 'gemini-2.5-flash-lite',
        'stable_production': 'gemini-1.5-flash',
        'fallback': 'gemini-1.0-pro'
    }
    return recommendations.get(task_type, 'gemini-2.5-flash')

def record_model_usage(model_name: str, success: bool = True):
    """記錄模型使用統計 - 增強版"""
    if model_name in model_usage_stats:
        model_usage_stats[model_name]['calls'] += 1
        model_usage_stats[model_name]['last_used'] = time.time()
        if not success:
            model_usage_stats[model_name]['errors'] += 1
        
        # 計算成功率
        total_calls = model_usage_stats[model_name]['calls']
        errors = model_usage_stats[model_name]['errors']
        model_usage_stats[model_name]['success_rate'] = ((total_calls - errors) / total_calls) * 100
        
        # 記錄世代統計
        generation = model_usage_stats[model_name]['generation']
        logger.info(f"📊 模型使用: {model_name} (第{generation}代) - {'成功' if success else '失敗'}")

def get_next_available_model() -> str:
    """智慧選擇下一個可用模型"""
    global model_rotation_index
    
    # 按優先順序選擇，而不是簡單循環
    current_index = AVAILABLE_MODELS.index(current_model_name) if current_model_name in AVAILABLE_MODELS else 0
    
    # 嘗試下一個優先順序更高的模型
    for i in range(current_index + 1, len(AVAILABLE_MODELS)):
        next_model = AVAILABLE_MODELS[i]
        # 檢查該模型最近是否有太多錯誤
        stats = model_usage_stats[next_model]
        error_rate = (stats['errors'] / max(stats['calls'], 1)) * 100
        
        if error_rate < 50:  # 錯誤率低於50%才考慮使用
            model_rotation_index = i
            return next_model
    
    # 如果所有優先順序高的都有問題，回到第一個
    model_rotation_index = 0
    return AVAILABLE_MODELS[0]

def switch_to_available_model() -> bool:
    """切換到可用模型"""
    global model, current_model_name
    
    if not GEMINI_API_KEY:
        return False
    
    # 嘗試切換到下一個模型
    new_model_name = get_next_available_model()
    
    try:
        new_model = genai.GenerativeModel(new_model_name)
        model = new_model
        current_model_name = new_model_name
        logger.info(f"✅ 成功切換到模型: {current_model_name}")
        return True
    except Exception as e:
        logger.error(f"❌ 切換模型失敗: {e}")
        return False

def get_quota_status() -> dict:
    """取得配額狀態 - 增強版本"""
    status = {
        'current_model': current_model_name,
        'current_generation': get_model_generation(current_model_name),
        'models': {},
        'generation_summary': {},
        'recommendations': []
    }
    
    generation_stats = {'2.5': 0, '2.0': 0, '1.5': 0, '1.0': 0}
    
    # 分析每個模型狀態
    for model_name in AVAILABLE_MODELS:
        stats = model_usage_stats[model_name]
        specs = MODEL_SPECIFICATIONS[model_name]
        error_rate = (stats['errors'] / max(stats['calls'], 1)) * 100
        
        # 基於錯誤率和規格估算可用性
        if error_rate > 70:
            usage_percent = 100
            status_text = "❌ 已用完"
        elif error_rate > 40:
            usage_percent = 85
            status_text = "⚠️ 配額緊張"
        elif error_rate > 20:
            usage_percent = 60
            status_text = "🟡 使用中"
        else:
            usage_percent = min(30, stats['calls'] * 1.5)
            status_text = "✅ 可用"
        
        status['models'][model_name] = {
            'usage_percent': usage_percent,
            'calls': stats['calls'],
            'errors': stats['errors'],
            'success_rate': round(stats.get('success_rate', 0), 1),
            'status': status_text,
            'generation': specs['generation'],
            'type': specs['type'],
            'cost_tier': specs['cost_tier'],
            'best_for': specs['best_for'],
            'free_limit': specs['free_limit']
        }
        
        # 統計世代可用性
        if usage_percent < 100:
            generation_stats[specs['generation']] += 1
    
    status['generation_summary'] = generation_stats
    
    # 生成智慧建議
    available_models = [name for name, info in status['models'].items() if info['usage_percent'] < 100]
    
    if not available_models:
        status['recommendations'].append("🚨 所有模型配額已用完，建議等待重置或升級方案")
    elif generation_stats['2.5'] > 0:
        status['recommendations'].append(f"✅ 建議優先使用 Gemini 2.5 系列（{generation_stats['2.5']} 個可用）")
    elif generation_stats['2.0'] > 0:
        status['recommendations'].append(f"⚡ 可使用 Gemini 2.0 系列（{generation_stats['2.0']} 個可用）")
    else:
        status['recommendations'].append("📦 目前僅備用模型可用，建議節約使用")
    
    return status

def test_ai_connection():
    """測試 AI 連接"""
    try:
        if not model:
            return False, "AI 模型未初始化"
        
        quota_status = get_quota_status()
        available_models = [name for name, info in quota_status['models'].items() if info['usage_percent'] < 100]
        
        if not available_models:
            return False, "所有模型配額已用完"
        
        return True, f"連接正常 - 當前: {current_model_name}, 可用模型: {len(available_models)}"
        
    except Exception as e:
        return False, f"連接錯誤: {str(e)[:60]}..."

# =================== app.py 修改版 - 第 1 段結束 ===================

# =================== app.py 修改版 - 第 2 段開始 ===================
# AI 回應生成核心功能 + 記憶管理功能 + 學習摘要生成（英文版本）

# =================== AI 回應生成核心功能 ===================

def get_ai_response(student_id, query, conversation_context="", student_context="", group_id=None):
    """智慧回應生成 - 包含模型切換和錯誤處理"""
    try:
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY 未設定")
            return "Hello! I'm currently being configured. Please check back soon. 👋"
        
        if not model:
            logger.error("❌ Gemini 模型未初始化")
            return "I'm having trouble connecting to my AI brain right now. Please try again in a moment. 🤖"
        
        # 檢查並處理配額限制
        quota_status = get_quota_status()
        available_models = [name for name, info in quota_status['models'].items() if info['usage_percent'] < 100]
        
        if not available_models:
            logger.warning("⚠️ 所有模型配額已用完")
            return "AI service quota exceeded. Please try again later when quota resets (typically at midnight UTC)."
        
        # 構建提示詞 - 修復 f-string 反斜線問題
        try:
            from models import Student
            student = Student.get_by_id(student_id) if student_id else None
        except:
            student = None
        
        # 修復：使用 chr(10) 替代 \n 來避免 f-string 中的反斜線
        newline = chr(10)
        
        # 構建前置對話內容
        conversation_prefix = f"Previous conversation context:{newline}{conversation_context}{newline}" if conversation_context else ""
        
        prompt = f"""You are an AI Teaching Assistant for English-medium instruction (EMI) courses.

{conversation_prefix}Student context: {student_context}

Current question/statement: {query}

Please provide a helpful, educational response in English that:
1. Addresses the student's question directly
2. Uses appropriate academic language for EMI learning
3. Encourages further learning and engagement
4. Maintains a supportive and encouraging tone

Response:"""

        # 記錄模型使用開始
        start_time = time.time()
        
        try:
            response = model.generate_content(prompt)
            response_time = time.time() - start_time
            
            if response and response.text:
                # 記錄成功使用
                record_model_usage(current_model_name, success=True)
                logger.info(f"✅ AI回應生成成功 ({response_time:.2f}秒)")
                return response.text.strip()
            else:
                raise Exception("Empty response from AI model")
                
        except Exception as ai_error:
            # 記錄失敗使用
            record_model_usage(current_model_name, success=False)
            logger.error(f"❌ AI回應生成失敗: {ai_error}")
            
            # 嘗試切換模型
            if switch_to_available_model():
                logger.info("🔄 已切換模型，重新嘗試...")
                try:
                    response = model.generate_content(prompt)
                    if response and response.text:
                        record_model_usage(current_model_name, success=True)
                        return response.text.strip()
                except:
                    pass
            
            # 如果所有嘗試都失敗，返回友好的錯誤訊息
            return "I'm experiencing some technical difficulties right now. Please try asking your question again in a moment! 🤖"
    
    except Exception as e:
        logger.error(f"❌ AI回應生成全域錯誤: {e}")
        return "Sorry, I'm having some technical issues. Please try again later. 🔧"

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
        context_summary = f"[Recent {len(recent_messages)} messages, {total_questions} questions]"
        
        return f"{context_summary}\n" + "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"❌ 獲取增強對話上下文錯誤: {e}")
        return ""

def get_student_learning_context(student_id):
    """
    獲取學生學習背景資訊
    用於提供更個人化的 AI 回應
    """
    try:
        from models import Student
        
        if not student_id:
            return ""
        
        student = Student.get_by_id(student_id)
        if not student:
            return ""
        
        context_parts = []
        
        # 基本資訊
        if hasattr(student, 'name') and student.name:
            context_parts.append(f"Student: {student.name}")
        
        # 學習等級
        if hasattr(student, 'level') and student.level:
            context_parts.append(f"Level: {student.level}")
        
        # 參與程度
        if hasattr(student, 'participation_rate') and student.participation_rate:
            participation_level = "High" if student.participation_rate > 70 else "Medium" if student.participation_rate > 40 else "Low"
            context_parts.append(f"Participation: {participation_level}")
        
        # 學習風格
        if hasattr(student, 'learning_style') and student.learning_style:
            context_parts.append(f"Learning style: {student.learning_style}")
        
        # 興趣領域
        if hasattr(student, 'interest_areas') and student.interest_areas:
            context_parts.append(f"Interests: {student.interest_areas[:100]}")
        
        # 最近活躍度
        if hasattr(student, 'last_active') and student.last_active:
            days_since_active = (datetime.datetime.now() - student.last_active).days
            if days_since_active == 0:
                context_parts.append("Status: Active today")
            elif days_since_active <= 3:
                context_parts.append(f"Status: Active {days_since_active} days ago")
        
        return "; ".join(context_parts)
        
    except Exception as e:
        logger.error(f"❌ 獲取學生學習背景錯誤: {e}")
        return ""

def update_conversation_memory(student_id, new_message_content, message_type='statement'):
    """
    更新對話記憶，智慧管理記憶容量
    當超過8次對話時，智慧清理較舊的記錄
    """
    try:
        from models import Message, Student
        
        # 記錄新訊息
        Message.create(
            student_id=student_id,
            content=new_message_content,
            message_type=message_type,
            timestamp=datetime.datetime.now()
        )
        
        # 檢查是否超過記憶限制（保持最近8次）
        total_messages = Message.select().where(Message.student_id == student_id).count()
        
        if total_messages > 8:
            # 刪除最舊的訊息，保留最新的8則
            oldest_messages = Message.select().where(
                Message.student_id == student_id
            ).order_by(Message.timestamp.asc()).limit(total_messages - 8)
            
            for old_msg in oldest_messages:
                old_msg.delete_instance()
            
            logger.info(f"🧹 清理學生 {student_id} 的舊對話記錄，保留最新8則")
        
        # 更新學生最後活躍時間
        student = Student.get_by_id(student_id)
        if student:
            student.last_active = datetime.datetime.now()
            student.save()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 更新對話記憶錯誤: {e}")
        return False

# =================== 學習檔案系統功能（修改為英文生成） ===================

def generate_student_learning_summary(student_id, summary_type='comprehensive', target_length=None):
    """
    生成學生學習摘要 - 完全修改為英文生成版本
    解決簡體中文問題，直接用英文提供學術標準的摘要
    完全移除截斷限制，確保完整內容顯示和匯出
    """
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return {
                'summary': 'Student record not found.',
                'message_count': 0,
                'error': 'Student not found',
                'generated_at': datetime.datetime.now().isoformat(),
                'language': 'english'
            }
        
        # 獲取學生所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.asc()))
        
        if not messages:
            return {
                'summary': 'No conversation data available for analysis. This student has not yet engaged in any recorded interactions.',
                'message_count': 0,
                'error': 'No data',
                'generated_at': datetime.datetime.now().isoformat(),
                'language': 'english'
            }
        
        message_count = len(messages)
        
        # 分類訊息類型 - 改進邏輯
        questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content.strip()]
        statements = [msg for msg in messages if msg not in questions]
        
        # 分析學習主題（英文關鍵詞分析）
        all_content = " ".join([msg.content for msg in messages]).lower()
        
        # 英文學習主題關鍵詞庫
        topic_keywords = {
            'grammar': ['grammar', 'tense', 'verb', 'noun', 'adjective', 'sentence', 'structure', 'syntax'],
            'vocabulary': ['word', 'meaning', 'definition', 'vocabulary', 'dictionary', 'phrase', 'expression'],
            'pronunciation': ['pronunciation', 'pronounce', 'sound', 'accent', 'speak', 'speaking', 'phonetic'],
            'writing': ['write', 'writing', 'essay', 'paragraph', 'composition', 'draft', 'edit'],
            'reading': ['read', 'reading', 'text', 'comprehension', 'article', 'book', 'story'],
            'listening': ['listen', 'listening', 'audio', 'hear', 'sound', 'video', 'podcast'],
            'conversation': ['conversation', 'talk', 'chat', 'discuss', 'dialogue', 'communicate'],
            'academic': ['academic', 'study', 'research', 'assignment', 'homework', 'exam', 'test'],
            'business': ['business', 'work', 'professional', 'meeting', 'presentation', 'email'],
            'culture': ['culture', 'cultural', 'tradition', 'custom', 'society', 'country']
        }
        
        # 識別主要學習主題
        topics = []
        for topic, keywords in topic_keywords.items():
            if any(keyword in all_content for keyword in keywords):
                topics.append(topic.title())
        
        # 時間範圍分析
        first_message_date = messages[0].timestamp.strftime('%B %d, %Y') if messages[0].timestamp else 'Unknown'
        last_message_date = messages[-1].timestamp.strftime('%B %d, %Y') if messages[-1].timestamp else 'Unknown'
        
        # 學習頻率分析
        if len(messages) > 1 and messages[0].timestamp and messages[-1].timestamp:
            days_span = (messages[-1].timestamp - messages[0].timestamp).days
            interaction_frequency = f"{len(messages)} messages over {days_span} days" if days_span > 0 else "Multiple messages in one day"
        else:
            interaction_frequency = "Single interaction session"
        
        # 生成完整的英文學習摘要 - 絕不截斷
        if summary_type == 'brief':
            full_summary = f"""**Brief Learning Summary for Student {student.name if hasattr(student, 'name') and student.name else student_id}**

This student has engaged in {message_count} learning interactions from {first_message_date} to {last_message_date}. The conversation pattern shows {len(questions)} questions and {len(statements)} statements, indicating {'an inquisitive learning approach' if len(questions) > len(statements) else 'a more declarative communication style'}.

**Primary Learning Areas:** {', '.join(topics[:3]) if topics else 'General English communication'}

**Learning Engagement:** {'High' if message_count > 20 else 'Moderate' if message_count > 10 else 'Initial'} level with consistent interaction patterns."""

        else:  # comprehensive summary
            # 構建完整詳細摘要
            full_summary = f"""**Comprehensive Learning Analysis for Student {student.name if hasattr(student, 'name') and student.name else student_id}**

**📊 Learning Overview:**
This student has demonstrated {message_count} recorded learning interactions spanning from {first_message_date} to {last_message_date}. The learning journey shows {interaction_frequency}, reflecting {'strong engagement' if message_count > 15 else 'developing engagement'} with the EMI (English-Medium Instruction) learning environment.

**🎯 Communication Patterns:**
The interaction analysis reveals {len(questions)} questions and {len(statements)} statements. This {len(questions)}/{len(statements)} question-to-statement ratio indicates a {'highly inquisitive' if len(questions) > len(statements) * 1.5 else 'balanced' if abs(len(questions) - len(statements)) <= 2 else 'more declarative'} learning approach. {'Students with high question frequency often show deeper engagement and critical thinking skills.' if len(questions) > len(statements) else 'A balanced interaction pattern suggests good comprehension and confident participation.'}

**📚 Learning Focus Areas:**
Primary learning topics identified include: {', '.join(topics) if topics else 'General English communication and academic discourse'}. {'These diverse topics indicate broad learning interests and comprehensive language development goals.' if len(topics) > 3 else 'This focused approach suggests targeted learning objectives.' if topics else 'The learning interactions cover general English communication skills.'}

**⏰ Engagement Timeline:**
Learning activity distribution shows {'consistent regular engagement' if message_count > 20 else 'steady participation' if message_count > 10 else 'initial exploration phase'}. The temporal pattern from {first_message_date} to {last_message_date} demonstrates {'sustained commitment to learning' if message_count > 15 else 'growing involvement in the learning process'}.

**💡 Learning Characteristics:**
Based on interaction patterns, this student shows {'strong self-directed learning tendencies' if len(questions) > 10 else 'developing autonomous learning skills'}. The conversation style suggests {'high academic engagement' if any(word in all_content for word in ['academic', 'study', 'research', 'assignment']) else 'practical communication focus'}. {'Question complexity and frequency indicate advanced critical thinking development.' if len(questions) > len(statements) else 'Statement patterns show good comprehension and confidence in expression.'}

**🎓 Academic Progress Indicators:**
Learning progression shows {'excellent advancement' if message_count > 25 else 'good development' if message_count > 15 else 'positive initial progress'}. The student demonstrates {'high participatory learning behavior' if len(messages) > 20 else 'active engagement' if len(messages) > 10 else 'emerging participation patterns'}.

**🔍 Recommendations:**
Continue encouraging {'this questioning approach' if len(questions) > len(statements) else 'more interactive questioning'} to enhance learning outcomes. Focus on {'maintaining current engagement levels' if hasattr(student, 'participation_rate') and student.participation_rate > 70 else 'increasing participation frequency'} and {'expanding topic diversity' if len(topics) < 3 else 'deepening expertise in identified areas'}.

**📈 Engagement Summary:**
Overall learning engagement is {'excellent' if message_count > 25 else 'good' if message_count > 15 else 'satisfactory'} with {'strong' if len(questions) > 10 else 'developing'} interaction patterns. The learning trajectory indicates {'high potential for advanced academic success' if len(questions) > len(statements) else 'solid foundation for continued learning growth'}."""
        
        # 完全移除截斷邏輯，返回完整摘要
        return {
            'summary': full_summary,  # 完整摘要，絕不截斷
            'message_count': message_count,
            'question_count': len(questions),
            'statement_count': len(statements),
            'summary_type': summary_type,
            'actual_length': len(full_summary),
            'topics': topics[:5],  # 最多顯示5個主題
            'participation_rate': getattr(student, 'participation_rate', 0),
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',  # 標記為英文摘要
            'truncated': False,  # 明確標記未被截斷
            'complete': True,  # 標記為完整摘要
            'student_name': getattr(student, 'name', f'Student_{student_id}'),
            'learning_period': f"{first_message_date} to {last_message_date}",
            'interaction_frequency': interaction_frequency
        }
        
    except Exception as e:
        logger.error(f"❌ 生成英文學習摘要錯誤: {e}")
        return {
            'summary': f'Error generating learning summary: {str(e)}',
            'message_count': 0,
            'error': str(e),
            'generated_at': datetime.datetime.now().isoformat(),
            'language': 'english',
            'truncated': False,
            'complete': False
        }

# =================== app.py 修改版 - 第 2 段結束 ===================

# =================== app.py 修改版 - 第 3 段開始 ===================
# 完整匯出功能 + 儲存空間管理功能

def export_student_complete_record(student_id, include_summary=True, include_analytics=True):
    """
    匯出學生完整記錄 - 確保摘要完整不截斷
    包含完整學習摘要、所有對話記錄和分析資料
    """
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return None
        
        # 建立完整匯出內容
        export_content = []
        
        # 檔案標頭
        export_content.append("="*60)
        export_content.append("EMI INTELLIGENT TEACHING ASSISTANT")
        export_content.append("COMPLETE STUDENT LEARNING RECORD")
        export_content.append("="*60)
        export_content.append("")
        
        # 學生基本資訊
        export_content.append("STUDENT INFORMATION:")
        export_content.append("-" * 20)
        export_content.append(f"Student ID: {student_id}")
        if hasattr(student, 'name') and student.name:
            export_content.append(f"Name: {student.name}")
        if hasattr(student, 'level') and student.level:
            export_content.append(f"Level: {student.level}")
        if hasattr(student, 'last_active') and student.last_active:
            export_content.append(f"Last Active: {student.last_active.strftime('%Y-%m-%d %H:%M:%S')}")
        
        export_content.append(f"Export Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_content.append("")
        
        # 完整學習摘要（不截斷）
        if include_summary:
            export_content.append("COMPREHENSIVE LEARNING SUMMARY:")
            export_content.append("-" * 40)
            
            learning_summary = generate_student_learning_summary(student_id, 'comprehensive')
            
            # 不截斷摘要內容，完整匯出
            export_content.append(learning_summary['summary'])
            
            if learning_summary.get('topics'):
                export_content.append("")
                export_content.append(f"Key Learning Topics: {', '.join(learning_summary['topics'])}")
            
            export_content.append("")
            export_content.append(f"Summary Statistics:")
            export_content.append(f"- Total Messages: {learning_summary.get('message_count', 0)}")
            export_content.append(f"- Questions: {learning_summary.get('question_count', 0)}")
            export_content.append(f"- Statements: {learning_summary.get('statement_count', 0)}")
            export_content.append(f"- Summary Length: {learning_summary.get('actual_length', 'N/A')} characters")
            export_content.append(f"- Complete Summary: {'Yes' if not learning_summary.get('truncated', True) else 'No (truncated)'}")
            export_content.append(f"- Generated At: {learning_summary.get('generated_at', 'Unknown')}")
            export_content.append(f"- Language: {learning_summary.get('language', 'Unknown')}")
            export_content.append("")
        
        # 獲取所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.asc()))
        
        # 完整對話記錄
        export_content.append("COMPLETE CONVERSATION HISTORY:")
        export_content.append("-" * 40)
        
        if messages:
            for i, message in enumerate(messages, 1):
                timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if message.timestamp else 'Unknown time'
                msg_type = '❓ Question' if (message.message_type == 'question' or '?' in message.content) else '💬 Statement'
                
                export_content.append(f"{i:3d}. [{timestamp}] {msg_type}")
                export_content.append(f"     {message.content}")
                export_content.append("")
        else:
            export_content.append("No conversation records available.")
            export_content.append("")
        
        # 學習分析資料
        if include_analytics:
            export_content.append("LEARNING ANALYTICS:")
            export_content.append("-" * 20)
            
            # 基本統計
            total_messages = len(messages)
            questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content]
            statements = [msg for msg in messages if msg not in questions]
            
            export_content.append(f"Total Interactions: {total_messages}")
            export_content.append(f"Questions Asked: {len(questions)}")
            export_content.append(f"Statements Made: {len(statements)}")
            export_content.append(f"Question-to-Statement Ratio: {len(questions)}/{len(statements)}")
            
            if messages:
                first_interaction = messages[0].timestamp.strftime('%Y-%m-%d') if messages[0].timestamp else 'Unknown'
                last_interaction = messages[-1].timestamp.strftime('%Y-%m-%d') if messages[-1].timestamp else 'Unknown'
                export_content.append(f"Learning Period: {first_interaction} to {last_interaction}")
            
            export_content.append("")
        
        # 檔案結尾
        export_content.append("="*60)
        export_content.append("END OF RECORD")
        export_content.append("="*60)
        
        return "\n".join(export_content)
        
    except Exception as e:
        logger.error(f"❌ 匯出學生完整記錄錯誤: {e}")
        return None

# =================== 儲存空間管理功能 ===================

def monitor_storage_usage():
    """監控儲存空間使用情況"""
    try:
        from models import Student, Message, Analysis
        
        # 計算各種資料的大小
        total_students = Student.select().count()
        total_messages = Message.select().count()
        total_analyses = Analysis.select().count() if hasattr(Analysis, 'select') else 0
        
        # 估算資料大小 (粗略估算)
        avg_message_size = 150  # bytes
        estimated_message_storage = total_messages * avg_message_size
        
        # 計算資料分布
        recent_messages = Message.select().where(
            Message.timestamp > (datetime.datetime.now() - datetime.timedelta(days=30))
        ).count()
        
        old_messages = total_messages - recent_messages
        
        storage_stats = {
            'total_students': total_students,
            'total_messages': total_messages,
            'recent_messages_30d': recent_messages,
            'old_messages': old_messages,
            'estimated_size_mb': round(estimated_message_storage / (1024 * 1024), 2),
            'total_analyses': total_analyses,
            'cleanup_recommended': old_messages > 1000,
            'storage_health': 'good' if total_messages < 5000 else 'warning' if total_messages < 10000 else 'critical'
        }
        
        return storage_stats
        
    except Exception as e:
        logger.error(f"❌ 監控儲存空間錯誤: {e}")
        return {}

def perform_smart_cleanup(cleanup_level='conservative'):
    """執行智慧資料清理"""
    try:
        from models import Message
        
        cleanup_stats = {
            'cleanup_level': cleanup_level,
            'deleted_messages': 0,
            'space_freed_mb': 0,
            'students_affected': 0
        }
        
        if cleanup_level == 'conservative':
            # 保守清理：只清理超過90天的舊資料
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=90)
        elif cleanup_level == 'moderate':
            # 中等清理：清理超過60天的舊資料
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=60)
        elif cleanup_level == 'aggressive':
            # 積極清理：清理超過30天的舊資料
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
        else:
            raise ValueError("Invalid cleanup level")
        
        # 查找要清理的訊息
        old_messages = Message.select().where(Message.timestamp < cutoff_date)
        
        # 統計將被刪除的資料
        cleanup_stats['deleted_messages'] = old_messages.count()
        cleanup_stats['space_freed_mb'] = round((cleanup_stats['deleted_messages'] * 150) / (1024 * 1024), 2)
        
        # 統計受影響的學生
        affected_students = set()
        for msg in old_messages:
            affected_students.add(msg.student_id)
        cleanup_stats['students_affected'] = len(affected_students)
        
        # 執行刪除
        if cleanup_stats['deleted_messages'] > 0:
            for msg in old_messages:
                msg.delete_instance()
            
            logger.info(f"🧹 清理完成：刪除 {cleanup_stats['deleted_messages']} 則舊訊息")
        
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"❌ 智慧清理錯誤: {e}")
        return {'error': str(e)}

# =================== app.py 修改版 - 第 3 段結束 ===================

# =================== app.py 修改版 - 第 4 段開始 ===================
# 網頁後台路由功能（首頁、管理後台、學生列表、教學分析等）

# =================== 網頁後台路由 ===================

@app.route('/')
def home():
    """首頁 - 增強版本包含最新功能展示"""
    try:
        # 獲取基本統計資訊
        from models import Student, Message
        
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 檢查AI連接狀態
        ai_connected, ai_status = test_ai_connection()
        ai_status_icon = "✅" if ai_connected else "❌"
        
        # 獲取配額狀態
        quota_status = get_quota_status()
        current_gen = quota_status.get('current_generation', 'Unknown')
        available_models = len([m for m, info in quota_status.get('models', {}).items() if info.get('usage_percent', 100) < 100])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>EMI智能教學助理</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .header h1 {{ color: #333; margin: 0; font-size: 2.5em; }}
                .header h2 {{ color: #666; margin: 10px 0; font-weight: 300; }}
                .features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
                .feature {{ background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #007bff; }}
                .feature h3 {{ color: #007bff; margin-top: 0; }}
                .nav-buttons {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 30px 0; }}
                .nav-btn {{ display: block; padding: 15px 25px; color: white; text-decoration: none; border-radius: 8px; text-align: center; font-weight: 500; transition: all 0.3s ease; }}
                .nav-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
                .btn-primary {{ background: #007bff; }}
                .btn-success {{ background: #28a745; }}
                .btn-info {{ background: #17a2b8; }}
                .btn-secondary {{ background: #6c757d; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #1976d2; }}
                .stat-label {{ color: #666; font-size: 0.9em; }}
                .status-indicator {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}
                .status-good {{ background: #28a745; }}
                .status-warning {{ background: #ffc107; }}
                .status-error {{ background: #dc3545; }}
                .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 EMI智能教學助理</h1>
                    <h2>🧠 2025年增強版本 - Gemini {current_gen} 系列</h2>
                    <p>LINE Bot + 最新 AI 模型 + 8次對話記憶 + 英文摘要系統</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_students}</div>
                        <div class="stat-label">註冊學生</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_messages}</div>
                        <div class="stat-label">對話記錄</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{available_models}</div>
                        <div class="stat-label">可用AI模型</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">8</div>
                        <div class="stat-label">記憶深度</div>
                    </div>
                </div>
                
                <div class="features">
                    <div class="feature">
                        <h3>🚀 最新 AI 模型支援</h3>
                        <p>支援 Gemini 2.5/2.0 全系列模型，包含 Pro、Flash、Flash-Lite 版本，提供最佳性價比和智能回應。</p>
                        <p><span class="status-indicator {'status-good' if ai_connected else 'status-error'}"></span>{ai_status_icon} AI狀態：{ai_status}</p>
                    </div>
                    <div class="feature">
                        <h3>🧠 增強記憶系統</h3>
                        <p>從3次對話提升到8次記憶深度，AI能記住更長的對話脈絡，提供更個人化的學習建議。</p>
                    </div>
                    <div class="feature">
                        <h3>🌍 英文學習摘要</h3>
                        <p>完全解決簡體中文問題，改為生成標準英文學術摘要，完整匯出不截斷。</p>
                    </div>
                    <div class="feature">
                        <h3>📊 智能健康檢查</h3>
                        <p>即時監控AI模型狀態、配額使用情況、系統效能，確保服務穩定運行。</p>
                    </div>
                </div>
                
                <div class="nav-buttons">
                    <a href="/students" class="nav-btn btn-primary">👥 學生管理</a>
                    <a href="/admin" class="nav-btn btn-success">⚙️ 管理後台</a>
                    <a href="/health" class="nav-btn btn-info">🏥 系統檢查</a>
                    <a href="/teaching-insights" class="nav-btn btn-warning">📈 教學分析</a>
                    <a href="/storage-management" class="nav-btn btn-secondary">💾 儲存管理</a>
                </div>
                
                <div class="footer">
                    <p>✨ 2025年增強功能：Gemini 2.5系列 | 8次記憶 | 英文摘要 | 完整匯出 | 智能監控</p>
                    <p>系統版本：EMI Teaching Assistant v2.5 | 最後更新：{datetime.datetime.now().strftime('%Y-%m-%d')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"❌ 首頁載入錯誤: {e}")
        return f"""
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
                <p style="color: #dc3545;">⚠️ 載入錯誤：{str(e)}</p>
            </div>
        </div>
        """

@app.route('/admin')
def admin():
    """管理後台 - 增強版本"""
    try:
        from models import Student, Message
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        active_students = Student.select().where(
            Student.last_active > (datetime.datetime.now() - datetime.timedelta(days=7))
        ).count()
        
        # 獲取AI狀態
        ai_connected, ai_status = test_ai_connection()
        quota_status = get_quota_status()
        
        # 最近活動統計
        today = datetime.datetime.now().date()
        today_messages = Message.select().where(
            Message.timestamp >= datetime.datetime.combine(today, datetime.time.min)
        ).count()
        
        # 儲存狀態
        storage_stats = monitor_storage_usage()
        
        # 構建管理後台 HTML
        admin_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>管理後台 - EMI智能教學助理</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin: 15px 0; }}
                .stat-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
                .stat-number {{ font-size: 1.8em; font-weight: bold; color: #007bff; }}
                .stat-label {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
                .status-good {{ color: #28a745; }}
                .status-warning {{ color: #ffc107; }}
                .status-error {{ color: #dc3545; }}
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-info {{ background: #17a2b8; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .model-list {{ margin: 10px 0; }}
                .model-item {{ padding: 8px; margin: 5px 0; background: #f8f9fa; border-radius: 5px; font-family: monospace; }}
                .progress-bar {{ background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; margin: 5px 0; }}
                .progress-fill {{ height: 100%; transition: width 0.3s ease; }}
                .progress-good {{ background: #28a745; }}
                .progress-warning {{ background: #ffc107; }}
                .progress-danger {{ background: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚙️ EMI智能教學助理 - 管理後台</h1>
                    <p>系統監控 • 配額管理 • 效能分析</p>
                    <div>
                        <a href="/" class="btn btn-primary">🏠 返回首頁</a>
                        <a href="/health" class="btn btn-info">🏥 詳細檢查</a>
                        <a href="/teaching-insights" class="btn btn-warning">📈 教學分析</a>
                    </div>
                </div>
                
                <div class="dashboard">
                    <div class="card">
                        <h3>📊 基本統計</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-number">{total_students}</div>
                                <div class="stat-label">總學生數</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{active_students}</div>
                                <div class="stat-label">活躍學生</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{total_messages}</div>
                                <div class="stat-label">總對話數</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{today_messages}</div>
                                <div class="stat-label">今日對話</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🤖 AI 系統狀態</h3>
                        <p><strong>連接狀態：</strong> <span class="{'status-good' if ai_connected else 'status-error'}">{'✅ 正常' if ai_connected else '❌ 異常'}</span></p>
                        <p><strong>當前模型：</strong> {current_model_name}</p>
                        <p><strong>模型世代：</strong> Gemini {quota_status.get('current_generation', 'Unknown')}</p>
                        <p><strong>可用模型：</strong> {len([m for m, info in quota_status.get('models', {}).items() if info.get('usage_percent', 100) < 100])}/{len(AVAILABLE_MODELS)}</p>
                        
                        <div class="model-list">
                            <strong>模型配額狀態：</strong>"""
        
        # 添加模型狀態列表
        for model_name, model_info in quota_status.get('models', {}).items():
            usage_percent = model_info.get('usage_percent', 100)
            status_class = 'progress-good' if usage_percent < 50 else 'progress-warning' if usage_percent < 85 else 'progress-danger'
            generation = model_info.get('generation', '?')
            
            admin_html += f"""
                            <div class="model-item">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span>📦 {model_name} (v{generation})</span>
                                    <span>{model_info.get('status', 'Unknown')}</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill {status_class}" style="width: {usage_percent}%"></div>
                                </div>
                                <small>使用: {model_info.get('calls', 0)} 次, 成功率: {model_info.get('success_rate', 0):.1f}%</small>
                            </div>"""
        
        admin_html += f"""
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>💾 儲存空間管理</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-number">{storage_stats.get('estimated_size_mb', 0)}</div>
                                <div class="stat-label">使用空間(MB)</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{storage_stats.get('recent_messages_30d', 0)}</div>
                                <div class="stat-label">近30天訊息</div>
                            </div>
                        </div>
                        <p><strong>儲存健康度：</strong> <span class="{'status-good' if storage_stats.get('storage_health') == 'good' else 'status-warning' if storage_stats.get('storage_health') == 'warning' else 'status-error'}">{storage_stats.get('storage_health', 'unknown').upper()}</span></p>
                        
                        <div style="margin-top: 15px;">
                            <a href="/storage-management" class="btn btn-info">💾 詳細管理</a>
                            {'<a href="/api/cleanup/conservative" class="btn btn-warning">🧹 建議清理</a>' if storage_stats.get('cleanup_recommended') else ''}
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📈 系統效能</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-number">{len(model_usage_stats)}</div>
                                <div class="stat-label">模型總數</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{sum(stats['calls'] for stats in model_usage_stats.values())}</div>
                                <div class="stat-label">總呼叫次數</div>
                            </div>
                        </div>
                        
                        <p><strong>主要建議：</strong></p>
                        <ul>"""
        
        # 添加智能建議
        recommendations = quota_status.get('recommendations', [])
        for rec in recommendations[:3]:  # 最多顯示3個建議
            admin_html += f"<li>{rec}</li>"
        
        admin_html += f"""
                        </ul>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: white; border-radius: 10px;">
                    <h3>🛠️ 快速操作</h3>
                    <a href="/students" class="btn btn-primary">👥 學生列表</a>
                    <a href="/api/export/all" class="btn btn-success">📥 匯出全部資料</a>
                    <a href="/health" class="btn btn-info">🏥 完整健康檢查</a>
                    <a href="/teaching-insights" class="btn btn-warning">📊 教學洞察</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return admin_html
        
    except Exception as e:
        logger.error(f"❌ 管理後台載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>⚙️ EMI智能教學助理 - 管理後台</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

@app.route('/students')
def students():
    """學生列表頁面 - 增強版本"""
    try:
        from models import Student, Message
        
        students = list(Student.select().order_by(Student.last_active.desc()))
        
        # 為每個學生計算統計資訊
        student_stats = []
        for student in students:
            message_count = Message.select().where(Message.student_id == student.id).count()
            
            # 計算最近活動
            if student.last_active:
                days_since_active = (datetime.datetime.now() - student.last_active).days
                if days_since_active == 0:
                    activity_status = "今天活躍"
                    activity_class = "status-good"
                elif days_since_active <= 3:
                    activity_status = f"{days_since_active}天前"
                    activity_class = "status-good"
                elif days_since_active <= 7:
                    activity_status = f"{days_since_active}天前"
                    activity_class = "status-warning"
                else:
                    activity_status = f"{days_since_active}天前"
                    activity_class = "status-error"
            else:
                activity_status = "從未活動"
                activity_class = "status-error"
            
            student_stats.append({
                'student': student,
                'message_count': message_count,
                'activity_status': activity_status,
                'activity_class': activity_class
            })
        
        # 構建學生列表頁面HTML
        students_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>學生管理 - EMI智能教學助理</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .controls {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .student-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .student-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 4px solid #007bff; }}
                .student-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: all 0.3s ease; }}
                .student-name {{ font-size: 1.2em; font-weight: bold; color: #333; margin-bottom: 10px; }}
                .student-info {{ color: #666; margin: 5px 0; }}
                .student-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0; }}
                .stat-item {{ text-align: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .stat-number {{ font-weight: bold; color: #007bff; }}
                .student-actions {{ margin-top: 15px; }}
                .btn {{ display: inline-block; padding: 8px 16px; margin: 2px; text-decoration: none; border-radius: 5px; font-size: 0.9em; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-info {{ background: #17a2b8; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .status-good {{ color: #28a745; }}
                .status-warning {{ color: #ffc107; }}
                .status-error {{ color: #dc3545; }}
                .search-box {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; }}
                .summary {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            </style>
            <script>
                function searchStudents() {{
                    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
                    const cards = document.querySelectorAll('.student-card');
                    
                    cards.forEach(card => {{
                        const name = card.querySelector('.student-name').textContent.toLowerCase();
                        const info = card.textContent.toLowerCase();
                        
                        if (name.includes(searchTerm) || info.includes(searchTerm)) {{
                            card.style.display = 'block';
                        }} else {{
                            card.style.display = 'none';
                        }}
                    }});
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 學生管理系統</h1>
                    <p>總計 {len(students)} 位學生 • 8次對話記憶 • 英文摘要系統</p>
                    <div>
                        <a href="/" class="btn btn-primary">🏠 返回首頁</a>
                        <a href="/admin" class="btn btn-info">⚙️ 管理後台</a>
                        <a href="/teaching-insights" class="btn btn-warning">📈 教學分析</a>
                    </div>
                </div>
                
                <div class="controls">
                    <h3>🔍 搜尋與篩選</h3>
                    <input type="text" id="searchBox" class="search-box" placeholder="搜尋學生姓名或ID..." onkeyup="searchStudents()">
                    
                    <div class="summary">
                        <strong>快速統計：</strong>
                        活躍學生：{len([s for s in student_stats if s['activity_class'] == 'status-good'])} 位 | 
                        總對話數：{sum(s['message_count'] for s in student_stats)} 則 | 
                        平均每人：{sum(s['message_count'] for s in student_stats) / len(student_stats) if student_stats else 0:.1f} 則對話
                    </div>
                </div>
                
                <div class="student-grid">"""
        
        # 生成學生卡片
        for stat in student_stats:
            student = stat['student']
            student_html = f"""
                    <div class="student-card">
                        <div class="student-name">
                            {getattr(student, 'name', f'學生_{student.id}')}
                        </div>
                        <div class="student-info">
                            <strong>ID:</strong> {student.id}
                        </div>"""
            
            # 安全地添加等級資訊
            if hasattr(student, 'level') and student.level:
                student_html += f"""
                        <div class="student-info"><strong>等級:</strong> {student.level}</div>"""
            
            student_html += f"""
                        <div class="student-info">
                            <strong>最後活動:</strong> 
                            <span class="{stat['activity_class']}">{stat['activity_status']}</span>
                        </div>
                        
                        <div class="student-stats">
                            <div class="stat-item">
                                <div class="stat-number">{stat['message_count']}</div>
                                <div>對話數</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{getattr(student, 'participation_rate', 0):.0f}%</div>
                                <div>參與度</div>
                            </div>
                        </div>
                        
                        <div class="student-actions">
                            <a href="/student/{student.id}" class="btn btn-primary">📋 詳細資料</a>
                            <a href="/api/export/student/{student.id}" class="btn btn-success">📥 匯出記錄</a>
                        </div>
                    </div>"""
            
            students_page += student_html
        
        if not student_stats:
            students_page += """
                    <div style="grid-column: 1 / -1; text-align: center; padding: 50px; color: #666;">
                        <h3>📝 尚無學生資料</h3>
                        <p>當學生開始使用 LINE Bot 互動時，資料會自動出現在這裡。</p>
                    </div>"""
        
        students_page += """
                </div>
            </div>
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

# =================== app.py 修改版 - 第 4 段結束 ===================

# =================== app.py 修改版 - 第 5 段開始 ===================
# 🔧 重要修改：整合 Learning Summary 到學生詳情頁面
# 移除獨立的 student_summary 路由，將功能合併到 student_detail

@app.route('/student/&lt;int:student_id&gt;')
def student_detail(student_id):
    """學生詳細資料頁面 - 整合 Learning Summary 功能"""
    try:
        from models import Student, Message
        
        student = Student.get_by_id(student_id)
        if not student:
            return """
            &lt;div style="font-family: sans-serif; text-align: center; padding: 50px;"&gt;
                &lt;h1&gt;❌ 學生不存在&lt;/h1&gt;
                &lt;p&gt;無法找到指定的學生記錄&lt;/p&gt;
                &lt;a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;"&gt;返回學生列表&lt;/a&gt;
            &lt;/div&gt;
            """
        
        # 🆕 生成 Learning Summary
        learning_summary = generate_student_learning_summary(student_id, 'comprehensive')
        
        # 獲取學生的對話記錄（最近8次）
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()).limit(8))
        
        # 分析對話模式
        total_messages = Message.select().where(Message.student_id == student_id).count()
        questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content]
        statements = [msg for msg in messages if msg not in questions]
        
        # 活動分析
        if messages:
            first_interaction = messages[-1].timestamp.strftime('%Y-%m-%d') if messages[-1].timestamp else 'Unknown'
            last_interaction = messages[0].timestamp.strftime('%Y-%m-%d') if messages[0].timestamp else 'Unknown'
            days_active = (messages[0].timestamp - messages[-1].timestamp).days if len(messages) &gt; 1 and messages[0].timestamp and messages[-1].timestamp else 0
        else:
            first_interaction = last_interaction = 'No interactions'
            days_active = 0
        
        # 生成整合後的HTML頁面
        return f"""
        &lt;!DOCTYPE html&gt;
        &lt;html&gt;
        &lt;head&gt;
            &lt;meta charset="UTF-8"&gt;
            &lt;title&gt;學生詳情 - {getattr(student, 'name', f'學生_{student_id}')}&lt;/title&gt;
            &lt;meta name="viewport" content="width=device-width, initial-scale=1.0"&gt;
            &lt;style&gt;
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .content-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                .card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin: 15px 0; }}
                .stat-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
                .stat-number {{ font-size: 1.8em; font-weight: bold; color: #007bff; }}
                .stat-label {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
                .conversation-list {{ max-height: 400px; overflow-y: auto; }}
                .message-item {{ padding: 10px; margin: 5px 0; border-left: 3px solid #ddd; background: #f8f9fa; border-radius: 5px; }}
                .message-question {{ border-left-color: #007bff; }}
                .message-statement {{ border-left-color: #28a745; }}
                .message-meta {{ font-size: 0.8em; color: #666; margin-bottom: 5px; }}
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .btn-info {{ background: #17a2b8; color: white; }}
                .full-width {{ grid-column: 1 / -1; }}
                .learning-summary {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; }}
                .learning-summary h3 {{ color: white; border-bottom-color: rgba(255,255,255,0.3); }}
                .summary-content {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 8px; white-space: pre-wrap; line-height: 1.6; }}
                .topics-grid {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 15px 0; }}
                .topic-tag {{ background: rgba(255,255,255,0.2); padding: 5px 12px; border-radius: 15px; font-size: 0.9em; }}
            &lt;/style&gt;
        &lt;/head&gt;
        &lt;body&gt;
            &lt;div class="container"&gt;
                &lt;div class="header"&gt;
                    &lt;h1&gt;👤 學生詳細資料&lt;/h1&gt;
                    &lt;h2&gt;{getattr(student, 'name', f'學生_{student_id}')} (ID: {student_id})&lt;/h2&gt;
                    &lt;p&gt;整合 Learning Summary • 8次對話記憶 • 完整分析報告&lt;/p&gt;
                    &lt;div&gt;
                        &lt;a href="/students" class="btn btn-primary"&gt;👥 返回學生列表&lt;/a&gt;
                        &lt;a href="/api/export/student/{student_id}" class="btn btn-success"&gt;📥 匯出完整記錄&lt;/a&gt;
                        &lt;a href="/admin" class="btn btn-info"&gt;⚙️ 管理後台&lt;/a&gt;
                    &lt;/div&gt;
                &lt;/div&gt;
                
                &lt;!-- 統計概覽 --&gt;
                &lt;div class="card full-width"&gt;
                    &lt;h3&gt;📊 學習統計概覽&lt;/h3&gt;
                    &lt;div class="stats-grid"&gt;
                        &lt;div class="stat-item"&gt;
                            &lt;div class="stat-number"&gt;{learning_summary.get('message_count', 0)}&lt;/div&gt;
                            &lt;div class="stat-label"&gt;💬 總對話數&lt;/div&gt;
                        &lt;/div&gt;
                        &lt;div class="stat-item"&gt;
                            &lt;div class="stat-number"&gt;{learning_summary.get('question_count', 0)}&lt;/div&gt;
                            &lt;div class="stat-label"&gt;❓ 提問次數&lt;/div&gt;
                        &lt;/div&gt;
                        &lt;div class="stat-item"&gt;
                            &lt;div class="stat-number"&gt;{learning_summary.get('statement_count', 0)}&lt;/div&gt;
                            &lt;div class="stat-label"&gt;💭 陳述次數&lt;/div&gt;
                        &lt;/div&gt;
                        &lt;div class="stat-item"&gt;
                            &lt;div class="stat-number"&gt;{learning_summary.get('participation_rate', getattr(student, 'participation_rate', 0)):.1f}%&lt;/div&gt;
                            &lt;div class="stat-label"&gt;🎯 參與度&lt;/div&gt;
                        &lt;/div&gt;
                        &lt;div class="stat-item"&gt;
                            &lt;div class="stat-number"&gt;{days_active}&lt;/div&gt;
                            &lt;div class="stat-label"&gt;📅 活躍天數&lt;/div&gt;
                        &lt;/div&gt;
                        &lt;div class="stat-item"&gt;
                            &lt;div class="stat-number"&gt;{first_interaction}&lt;/div&gt;
                            &lt;div class="stat-label"&gt;🚀 首次互動&lt;/div&gt;
                        &lt;/div&gt;
                    &lt;/div&gt;
                &lt;/div&gt;
                
                &lt;!-- 🆕 整合的 Learning Summary 區域 --&gt;
                &lt;div class="learning-summary full-width"&gt;
                    &lt;h3&gt;📝 Learning Analysis&lt;/h3&gt;
                    &lt;div class="summary-content"&gt;
{learning_summary.get('summary', 'No learning summary available.')}
                    &lt;/div&gt;
                    
                    &lt;div style="margin-top: 20px;"&gt;
                        &lt;h4&gt;🎯 主要學習主題：&lt;/h4&gt;
                        &lt;div class="topics-grid"&gt;
"""
        
        # 添加主題標籤
        for topic in learning_summary.get('topics', []):
            return_html += f"""
                            &lt;span class="topic-tag"&gt;{topic}&lt;/span&gt;
"""
        
        return_html = f"""
                        &lt;/div&gt;
                    &lt;/div&gt;
                    
                    &lt;div style="margin-top: 20px; font-size: 0.9em; color: rgba(255,255,255,0.8);"&gt;
                        📊 基於 {learning_summary.get('message_count', 0)} 條對話記錄分析 | 
                        🕒 生成時間: {learning_summary.get('generated_at', '未知')[:19].replace('T', ' ')}
                    &lt;/div&gt;
                &lt;/div&gt;
                
                &lt;!-- 對話記錄區域 --&gt;
                &lt;div class="card full-width"&gt;
                    &lt;h3&gt;💬 對話記錄 (最近8次記憶)&lt;/h3&gt;
                    &lt;div class="conversation-list"&gt;
"""
        
        # 添加對話記錄
        if messages:
            for msg in messages:
                msg_type_class = 'message-question' if msg.message_type == 'question' or '?' in msg.content else 'message-statement'
                msg_type_label = '❓ 問題' if msg.message_type == 'question' or '?' in msg.content else '💬 陳述'
                timestamp_str = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else 'Unknown time'
                
                return_html += f"""
                        &lt;div class="message-item {msg_type_class}"&gt;
                            &lt;div class="message-meta"&gt;
                                {timestamp_str} | {msg_type_label}
                            &lt;/div&gt;
                            &lt;div&gt;{msg.content}&lt;/div&gt;
                        &lt;/div&gt;"""
        else:
            return_html += """
                        &lt;p style="text-align: center; color: #666; padding: 20px;"&gt;尚無對話記錄&lt;/p&gt;"""
        
        return_html += f"""
                    &lt;/div&gt;
                    
                    {f'&lt;p style="text-align: center; margin-top: 15px; color: #666;"&gt;顯示最近8次對話 (共{total_messages}次) • &lt;a href="/api/export/student/{student_id}"&gt;下載完整記錄&lt;/a&gt;&lt;/p&gt;' if total_messages &gt; 8 else ''}
                &lt;/div&gt;
            &lt;/div&gt;
        &lt;/body&gt;
        &lt;/html&gt;
        """
        
        return return_html
        
    except Exception as e:
        logger.error(f"❌ 學生詳情載入錯誤: {e}")
        return f"""
        &lt;div style="font-family: sans-serif; text-align: center; padding: 50px;"&gt;
            &lt;h1&gt;❌ 載入錯誤&lt;/h1&gt;
            &lt;p&gt;無法載入學生詳細資料&lt;/p&gt;
            &lt;p style="color: #dc3545;"&gt;{str(e)}&lt;/p&gt;
            &lt;a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;"&gt;返回學生列表&lt;/a&gt;
        &lt;/div&gt;
        """

# ❌ 移除獨立的學習摘要路由 - 功能已整合到 student_detail 中
# @app.route('/student/&lt;int:student_id&gt;/summary')
# def student_summary(student_id):
#     """此路由已移除，功能整合到 student_detail 中"""
#     return redirect(f'/student/{student_id}')

# =================== app.py 修改版 - 第 5 段結束 ===================

# =================== app.py 修改版 - 第 6 段開始 ===================
# 主程式執行區段與結尾

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
    else:
        logger.warning("⚠️ LINE Bot 環境變數未完整設定")
    
    # 🤖 AI 模型檢查
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        logger.info("✅ Gemini AI API 金鑰已載入")
    else:
        logger.warning("⚠️ Gemini API 金鑰未設定")
    
    # 🚀 Flask 應用程式啟動
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"🌟 系統啟動完成!")
    logger.info(f"📍 服務地址: http://{host}:{port}")
    logger.info(f"🔧 除錯模式: {'開啟' if debug_mode else '關閉'}")
    logger.info(f"📊 主要功能: LINE Bot Webhook, 學生管理, AI 對話, 學習分析")
    logger.info(f"📝 新功能: 整合學習摘要, 移除獨立摘要頁面, 8次對話記憶")
    
    # 生產環境安全檢查
    if not debug_mode:
        logger.info("🔒 生產模式運行中 - 安全檢查已啟用")
        if not os.getenv('SECRET_KEY'):
            logger.warning("⚠️ 建議設定 SECRET_KEY 環境變數")
    
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
EMI 智能教學助理系統 - 2025年增強版本
=====================================

版本歷程:
--------
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

v2.0.0 (2025-06-20):
- LINE Bot 整合
- 學生管理系統
- 基礎 AI 對話功能
- SQLite 資料庫支援

主要功能:
--------
🤖 AI 對話系統: 支援 Gemini 2.5/2.0 系列模型
📱 LINE Bot 整合: 完整 Webhook 支援
👥 學生管理: 註冊、追蹤、分析
🧠 學習記憶: 8次對話上下文記憶
📊 學習分析: 即時英文摘要生成  
📥 資料匯出: 完整記錄下載
🔧 系統管理: 儲存監控與自動清理
🌐 網頁介面: 教師管理後台

技術架構:
--------
- 後端: Flask + Python 3.8+
- 資料庫: SQLite + Peewee ORM
- AI 模型: Google Gemini API
- 前端: Bootstrap + 原生 JavaScript
- 部署: Railway / Heroku 相容

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

聯絡資訊:
--------
系統開發: EMI教學助理開發團隊
技術支援: 請參考系統文件
更新日期: 2025年6月27日
"""

# =================== app.py 修改版 - 第 6 段結束 ===================
# =================== 程式檔案結束 ===================
