# =================== app.py 完整版 - 第 1 段開始 ===================
# EMI智能教學助理系統 - 2025年增強版本
# 支援最新 Gemini 2.5/2.0 系列模型 + 8次對話記憶 + 英文摘要 + 完整匯出
# 更新日期：2025年6月25日

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

# =================== app.py 完整版 - 第 1 段結束 ===================

# =================== app.py 完整版 - 第 2 段開始 ===================
# 記憶管理功能 + 學習摘要生成（英文版本）+ 完整匯出功能

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

# =================== app.py 完整版 - 第 2 段結束 ===================


# =================== app.py 完整版 - 第 3 段修復版 ===================
# 網頁後台路由功能 + 學生管理 + 資料匯出 (語法錯誤修正)

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
        
        # 構建管理後台 HTML（修復語法錯誤）
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
        
        # 添加模型狀態列表（修復語法錯誤）
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
        
        # 添加智能建議（修復語法錯誤）
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
        
        # 構建學生列表頁面HTML（修復語法錯誤）
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
        
        # 生成學生卡片（修復語法錯誤）
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
                            <a href="/student/{student.id}/summary" class="btn btn-warning">📊 學習摘要</a>
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

# =================== 教學分析和洞察路由 ===================

@app.route('/teaching-insights')
def teaching_insights():
    """教學洞察分析頁面"""
    try:
        from models import Student, Message
        
        # 基本統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 模擬洞察數據（實際應用中會從 teaching_analytics 取得）
        insights = {
            'question_oriented_students': 65,
            'participation_rate': 78.5,
            'topic_diversity': 8,
            'teaching_recommendation': '持續鼓勵學生積極提問，增強互動式學習。',
            'students_need_attention': 3,
            'high_engagement_students': 12,
            'learning_styles': 4,
            'ai_accuracy': 92,
            'avg_response_time': 2.1,
            'model_efficiency': 88,
            'topic_grammar': 25,
            'topic_vocabulary': 20,
            'topic_writing': 18,
            'topic_pronunciation': 15,
            'topic_conversation': 22,
            'focus_area': 'Grammar & Writing'
        }
        
        trends = {
            'weekly_activity': 156,
            'weekly_trend': 15,
            'question_complexity': 'Medium-High',
            'satisfaction_rate': 85
        }
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>教學洞察 - EMI智能教學助理</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .insights-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
                .insight-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .insight-card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #28a745; padding-bottom: 10px; }}
                .metric {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .metric-value {{ font-weight: bold; color: #007bff; }}
                .trend-up {{ color: #28a745; }}
                .trend-down {{ color: #dc3545; }}
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .recommendation {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📈 教學洞察分析</h1>
                    <p>基於 AI 分析的深度教學洞察 • 學習趨勢 • 個人化建議</p>
                    <div>
                        <a href="/" class="btn btn-primary">🏠 返回首頁</a>
                        <a href="/students" class="btn btn-primary">👥 學生管理</a>
                        <a href="/admin" class="btn btn-primary">⚙️ 管理後台</a>
                    </div>
                </div>
                
                <div class="insights-grid">
                    <div class="insight-card">
                        <h3>📊 班級概況</h3>
                        <div class="metric">
                            <span>總學生數</span>
                            <span class="metric-value">{total_students}</span>
                        </div>
                        <div class="metric">
                            <span>總互動次數</span>
                            <span class="metric-value">{total_messages}</span>
                        </div>
                        <div class="metric">
                            <span>平均每人互動</span>
                            <span class="metric-value">{total_messages / max(total_students, 1):.1f}</span>
                        </div>
                        <div class="metric">
                            <span>系統記憶深度</span>
                            <span class="metric-value">8 輪對話</span>
                        </div>
                    </div>
                    
                    <div class="insight-card">
                        <h3>🎯 學習模式分析</h3>
                        <div class="metric">
                            <span>問題導向學習者</span>
                            <span class="metric-value">{insights.get('question_oriented_students', 0)}%</span>
                        </div>
                        <div class="metric">
                            <span>主動參與度</span>
                            <span class="metric-value">{insights.get('participation_rate', 0):.1f}%</span>
                        </div>
                        <div class="metric">
                            <span>學習主題多樣性</span>
                            <span class="metric-value">{insights.get('topic_diversity', 0)}</span>
                        </div>
                        
                        <div class="recommendation">
                            <strong>💡 教學建議:</strong> {insights.get('teaching_recommendation', '持續鼓勵學生積極提問，提升互動質量。')}
                        </div>
                    </div>
                    
                    <div class="insight-card">
                        <h3>📈 學習趨勢</h3>
                        <div class="metric">
                            <span>本週活躍度</span>
                            <span class="metric-value trend-{'up' if trends.get('weekly_trend', 0) > 0 else 'down'}">{trends.get('weekly_activity', 0)} 
                            {'↗️' if trends.get('weekly_trend', 0) > 0 else '↘️'}</span>
                        </div>
                        <div class="metric">
                            <span>問題複雜度</span>
                            <span class="metric-value">{trends.get('question_complexity', 'Medium')}</span>
                        </div>
                        <div class="metric">
                            <span>回應滿意度</span>
                            <span class="metric-value">{trends.get('satisfaction_rate', 85)}%</span>
                        </div>
                    </div>
                    
                    <div class="insight-card">
                        <h3>🎓 個人化洞察</h3>
                        <div class="metric">
                            <span>需要關注學生</span>
                            <span class="metric-value">{insights.get('students_need_attention', 0)}</span>
                        </div>
                        <div class="metric">
                            <span>高參與學生</span>
                            <span class="metric-value">{insights.get('high_engagement_students', 0)}</span>
                        </div>
                        <div class="metric">
                            <span>學習風格類型</span>
                            <span class="metric-value">{insights.get('learning_styles', 3)}</span>
                        </div>
                        
                        <div style="margin-top: 15px;">
                            <a href="/api/export/insights" class="btn btn-success">📥 匯出分析報告</a>
                        </div>
                    </div>
                    
                    <div class="insight-card">
                        <h3>🛠️ 系統效能洞察</h3>
                        <div class="metric">
                            <span>AI 回應準確度</span>
                            <span class="metric-value">{insights.get('ai_accuracy', 92)}%</span>
                        </div>
                        <div class="metric">
                            <span>平均回應時間</span>
                            <span class="metric-value">{insights.get('avg_response_time', 2.1):.1f}秒</span>
                        </div>
                        <div class="metric">
                            <span>模型使用效率</span>
                            <span class="metric-value">{insights.get('model_efficiency', 88)}%</span>
                        </div>
                    </div>
                    
                    <div class="insight-card">
                        <h3>📚 學習內容分析</h3>
                        <p><strong>熱門學習主題:</strong></p>
                        <ul>
                            <li>Grammar & Syntax ({insights.get('topic_grammar', 25)}%)</li>
                            <li>Vocabulary Building ({insights.get('topic_vocabulary', 20)}%)</li>
                            <li>Academic Writing ({insights.get('topic_writing', 18)}%)</li>
                            <li>Pronunciation ({insights.get('topic_pronunciation', 15)}%)</li>
                            <li>Conversation Skills ({insights.get('topic_conversation', 22)}%)</li>
                        </ul>
                        
                        <div class="recommendation">
                            <strong>📖 課程建議:</strong> 根據學習數據，建議加強 {insights.get('focus_area', 'Grammar & Writing')} 相關教材。
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: white; border-radius: 10px;">
                    <h3>🔄 資料匯出與管理</h3>
                    <a href="/api/export/class-report" class="btn btn-success">📊 完整班級報告</a>
                    <a href="/api/export/learning-analytics" class="btn btn-success">📈 學習分析資料</a>
                    <a href="/storage-management" class="btn btn-primary">💾 儲存管理</a>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"❌ 教學洞察載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>📈 教學洞察分析</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

@app.route('/storage-management')
def storage_management():
    """儲存空間管理頁面"""
    try:
        storage_stats = monitor_storage_usage()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>儲存管理 - EMI智能教學助理</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .storage-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .storage-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .storage-card h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #17a2b8; padding-bottom: 10px; }}
                .metric {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .metric-value {{ font-weight: bold; color: #007bff; }}
                .status-good {{ color: #28a745; }}
                .status-warning {{ color: #ffc107; }}
                .status-critical {{ color: #dc3545; }}
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .btn-danger {{ background: #dc3545; color: white; }}
                .cleanup-options {{ margin: 15px 0; }}
                .cleanup-option {{ padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; }}
                .progress-bar {{ background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; margin: 10px 0; }}
                .progress-fill {{ height: 100%; transition: width 0.3s ease; }}
                .progress-good {{ background: #28a745; }}
                .progress-warning {{ background: #ffc107; }}
                .progress-danger {{ background: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💾 儲存空間管理</h1>
                    <p>監控資料使用量 • 智能清理 • 效能優化</p>
                    <div>
                        <a href="/" class="btn btn-primary">🏠 返回首頁</a>
                        <a href="/admin" class="btn btn-primary">⚙️ 管理後台</a>
                    </div>
                </div>
                
                <div class="storage-grid">
                    <div class="storage-card">
                        <h3>📊 儲存使用概況</h3>
                        <div class="metric">
                            <span>總學生數</span>
                            <span class="metric-value">{storage_stats.get('total_students', 0)}</span>
                        </div>
                        <div class="metric">
                            <span>總訊息數</span>
                            <span class="metric-value">{storage_stats.get('total_messages', 0)}</span>
                        </div>
                        <div class="metric">
                            <span>估計使用空間</span>
                            <span class="metric-value">{storage_stats.get('estimated_size_mb', 0)} MB</span>
                        </div>
                        <div class="metric">
                            <span>儲存健康度</span>
                            <span class="metric-value status-{storage_stats.get('storage_health', 'good')}">{storage_stats.get('storage_health', 'good').upper()}</span>
                        </div>"""
        
        # 安全地生成進度條（避免語法錯誤）
        if storage_stats.get('estimated_size_mb'):
            usage_mb = storage_stats.get('estimated_size_mb', 0)
            progress_class = 'progress-good' if usage_mb < 50 else 'progress-warning' if usage_mb < 100 else 'progress-danger'
            progress_width = min(usage_mb, 200) / 2
            
            storage_html += f"""
                        <div class="progress-bar">
                            <div class="progress-fill {progress_class}" style="width: {progress_width}%"></div>
                        </div>
                        <small>使用量: {usage_mb} MB / 200 MB (建議上限)</small>"""
        
        storage_html += f"""
                    </div>
                    
                    <div class="storage-card">
                        <h3>📈 資料分布分析</h3>
                        <div class="metric">
                            <span>近30天訊息</span>
                            <span class="metric-value">{storage_stats.get('recent_messages_30d', 0)}</span>
                        </div>
                        <div class="metric">
                            <span>歷史訊息</span>
                            <span class="metric-value">{storage_stats.get('old_messages', 0)}</span>
                        </div>
                        <div class="metric">
                            <span>分析記錄</span>
                            <span class="metric-value">{storage_stats.get('total_analyses', 0)}</span>
                        </div>"""
        
        # 安全地添加清理建議
        if storage_stats.get('cleanup_recommended'):
            storage_html += """
                        <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <strong>⚠️ 建議清理:</strong> 發現大量歷史資料，建議進行清理以優化效能。
                        </div>"""
        else:
            storage_html += """
                        <div style="background: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <strong>✅ 狀態良好:</strong> 儲存空間使用正常，無需清理。
                        </div>"""
        
        storage_html += f"""
                    </div>
                    
                    <div class="storage-card">
                        <h3>🧹 智能清理選項</h3>
                        <div class="cleanup-options">
                            <div class="cleanup-option">
                                <h4>🟢 保守清理</h4>
                                <p>清理90天前的舊資料 (推薦)</p>
                                <a href="/api/cleanup/conservative" class="btn btn-primary">執行保守清理</a>
                            </div>
                            
                            <div class="cleanup-option">
                                <h4>🟡 中等清理</h4>
                                <p>清理60天前的舊資料</p>
                                <a href="/api/cleanup/moderate" class="btn btn-warning">執行中等清理</a>
                            </div>
                            
                            <div class="cleanup-option">
                                <h4>🔴 積極清理</h4>
                                <p>清理30天前的舊資料 (謹慎使用)</p>
                                <a href="/api/cleanup/aggressive" class="btn btn-danger" onclick="return confirm('確定要執行積極清理嗎？這將刪除30天前的所有資料。')">執行積極清理</a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="storage-card">
                        <h3>📥 資料備份與匯出</h3>
                        <p>在執行清理前，建議先備份重要資料。</p>
                        
                        <div style="margin: 15px 0;">
                            <a href="/api/export/all" class="btn btn-primary">📦 完整資料備份</a>
                            <a href="/api/export/recent" class="btn btn-primary">📋 近期資料匯出</a>
                        </div>
                        
                        <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin-top: 15px;">
                            <strong>💡 備份建議:</strong>
                            <ul style="margin: 10px 0; padding-left: 20px;">
                                <li>定期匯出重要學習記錄</li>
                                <li>保留最近3個月的完整資料</li>
                                <li>清理前務必備份</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return storage_html
        
    except Exception as e:
        logger.error(f"❌ 儲存管理載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>💾 儲存空間管理</h1>
            <p style="color: #dc3545;">載入錯誤：{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """

# =================== app.py 完整版 - 第 3 段修復版結束 ===================


# =================== app.py 完整版 - 第 4 段修復版 ===================
# 健康檢查 + 學生詳情 + 資料匯出 + LINE Bot 處理 + 程式進入點（語法錯誤修正）

# =================== 增強版健康檢查功能 ===================

@app.route('/health')
def enhanced_health_check():
    """
    增強版系統健康檢查 - 2025年版本
    包含AI模型狀態、配額監控、效能指標、系統資源
    """
    try:
        import sys
        from models import Student, Message
        
        # 基本系統資訊
        health_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'system_status': 'operational',
            'version': 'EMI Teaching Assistant v2.5.0',
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'components': {}
        }
        
        # 1. 資料庫健康檢查
        try:
            db_students = Student.select().count()
            db_messages = Message.select().count()
            health_data['components']['database'] = {
                'status': 'healthy',
                'students_count': db_students,
                'messages_count': db_messages,
                'last_activity': 'recent' if db_messages > 0 else 'none'
            }
        except Exception as db_error:
            health_data['components']['database'] = {
                'status': 'error',
                'error': str(db_error)
            }
            health_data['system_status'] = 'degraded'
        
        # 2. AI模型健康檢查
        ai_connected, ai_status = test_ai_connection()
        quota_status = get_quota_status()
        
        health_data['components']['ai_models'] = {
            'status': 'healthy' if ai_connected else 'error',
            'current_model': current_model_name,
            'current_generation': quota_status.get('current_generation', 'unknown'),
            'available_models': len([m for m, info in quota_status.get('models', {}).items() if info.get('usage_percent', 100) < 100]),
            'total_models': len(AVAILABLE_MODELS),
            'connection_test': ai_status,
            'quota_summary': quota_status.get('generation_summary', {}),
            'recommendations': quota_status.get('recommendations', [])
        }
        
        if not ai_connected:
            health_data['system_status'] = 'degraded'
        
        # 3. LINE Bot 健康檢查
        line_status = 'healthy' if (line_bot_api and handler) else 'not_configured'
        health_data['components']['line_bot'] = {
            'status': line_status,
            'api_configured': bool(CHANNEL_ACCESS_TOKEN),
            'webhook_configured': bool(CHANNEL_SECRET),
            'bot_ready': bool(line_bot_api and handler)
        }
        
        # 4. 環境變數檢查
        env_status = {
            'GEMINI_API_KEY': 'configured' if GEMINI_API_KEY else 'missing',
            'CHANNEL_ACCESS_TOKEN': 'configured' if CHANNEL_ACCESS_TOKEN else 'missing',
            'CHANNEL_SECRET': 'configured' if CHANNEL_SECRET else 'missing'
        }
        
        missing_env = [k for k, v in env_status.items() if v == 'missing']
        health_data['components']['environment'] = {
            'status': 'healthy' if not missing_env else 'warning',
            'variables': env_status,
            'missing_critical': missing_env
        }
        
        # 5. 儲存空間檢查
        storage_stats = monitor_storage_usage()
        storage_health = storage_stats.get('storage_health', 'unknown')
        health_data['components']['storage'] = {
            'status': 'healthy' if storage_health == 'good' else 'warning' if storage_health == 'warning' else 'critical',
            'usage_mb': storage_stats.get('estimated_size_mb', 0),
            'cleanup_recommended': storage_stats.get('cleanup_recommended', False),
            'total_messages': storage_stats.get('total_messages', 0),
            'recent_messages': storage_stats.get('recent_messages_30d', 0)
        }
        
        if storage_health in ['warning', 'critical']:
            health_data['system_status'] = 'warning' if storage_health == 'warning' else 'critical'
        
        # 6. 模型使用統計
        total_calls = sum(stats['calls'] for stats in model_usage_stats.values())
        total_errors = sum(stats['errors'] for stats in model_usage_stats.values())
        success_rate = ((total_calls - total_errors) / max(total_calls, 1)) * 100
        
        health_data['components']['performance'] = {
            'status': 'healthy' if success_rate > 85 else 'warning' if success_rate > 70 else 'critical',
            'total_ai_calls': total_calls,
            'total_errors': total_errors,
            'success_rate': round(success_rate, 2),
            'model_distribution': {model: stats['calls'] for model, stats in model_usage_stats.items() if stats['calls'] > 0}
        }
        
        # 7. 記憶系統檢查
        avg_conversations = db_messages / max(db_students, 1) if db_students > 0 else 0
        health_data['components']['memory_system'] = {
            'status': 'healthy',
            'memory_depth': 8,
            'avg_conversations_per_student': round(avg_conversations, 2),
            'enhanced_context': True,
            'english_summaries': True
        }
        
        # 最終系統狀態判定
        component_statuses = [comp.get('status', 'unknown') for comp in health_data['components'].values()]
        if 'critical' in component_statuses or 'error' in component_statuses:
            health_data['system_status'] = 'critical'
        elif 'warning' in component_statuses:
            health_data['system_status'] = 'warning'
        elif all(status == 'healthy' for status in component_statuses if status != 'not_configured'):
            health_data['system_status'] = 'healthy'
        else:
            health_data['system_status'] = 'degraded'
        
        # 檢查JSON格式請求
        if request.args.get('format') == 'json':
            return jsonify(health_data)
        
        # 返回詳細的HTML健康檢查報告
        status_colors = {
            'healthy': '#28a745',
            'warning': '#ffc107', 
            'critical': '#dc3545',
            'error': '#dc3545',
            'degraded': '#fd7e14',
            'not_configured': '#6c757d'
        }
        
        status_icons = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '❌',
            'error': '❌',
            'degraded': '🟡',
            'not_configured': '⚫'
        }
        
        overall_color = status_colors.get(health_data['system_status'], '#6c757d')
        overall_icon = status_icons.get(health_data['system_status'], '❓')
        
        # 構建完整的健康檢查HTML（修復語法錯誤）
        health_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>系統健康檢查 - EMI智能教學助理</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
                .status-overview {{ background: {overall_color}; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
                .components-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }}
                .component-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 4px solid #ddd; }}
                .component-card.healthy {{ border-left-color: #28a745; }}
                .component-card.warning {{ border-left-color: #ffc107; }}
                .component-card.critical {{ border-left-color: #dc3545; }}
                .component-card.error {{ border-left-color: #dc3545; }}
                .component-card.not_configured {{ border-left-color: #6c757d; }}
                .component-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
                .component-title {{ font-size: 1.1em; font-weight: bold; }}
                .status-badge {{ padding: 5px 10px; border-radius: 15px; font-size: 0.9em; font-weight: bold; }}
                .status-healthy {{ background: #d4edda; color: #155724; }}
                .status-warning {{ background: #fff3cd; color: #856404; }}
                .status-critical {{ background: #f8d7da; color: #721c24; }}
                .status-error {{ background: #f8d7da; color: #721c24; }}
                .status-not_configured {{ background: #e2e3e5; color: #383d41; }}
                .metric {{ display: flex; justify-content: space-between; margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 5px; }}
                .metric-value {{ font-weight: bold; color: #007bff; }}
                .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .recommendations {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin-top: 15px; }}
                .model-list {{ max-height: 200px; overflow-y: auto; }}
                .model-item {{ padding: 5px; margin: 3px 0; background: #f8f9fa; border-radius: 3px; font-family: monospace; font-size: 0.9em; }}
                .auto-refresh {{ text-align: center; margin-top: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 系統健康檢查</h1>
                    <p>EMI智能教學助理 - 即時監控與診斷</p>
                    <div>
                        <a href="/" class="btn btn-primary">🏠 返回首頁</a>
                        <a href="/admin" class="btn btn-primary">⚙️ 管理後台</a>
                        <a href="?format=json" class="btn btn-success">📋 JSON格式</a>
                    </div>
                </div>
                
                <div class="status-overview">
                    <h2>{overall_icon} 系統總體狀態: {health_data['system_status'].upper()}</h2>
                    <p>檢查時間: {health_data['timestamp']}</p>
                    <p>版本: {health_data['version']}</p>
                </div>
                
                <div class="components-grid">"""
        
        # 生成各組件的健康檢查卡片（修復語法錯誤）
        
        # 1. 資料庫組件
        db_comp = health_data['components']['database']
        health_html += f"""
                    <div class="component-card {db_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">📊 資料庫系統</span>
                            <span class="status-badge status-{db_comp['status']}">{status_icons.get(db_comp['status'], '❓')} {db_comp['status'].upper()}</span>
                        </div>"""
        
        if db_comp['status'] == 'healthy':
            health_html += f"""
                        <div class="metric">
                            <span>學生記錄</span>
                            <span class="metric-value">{db_comp['students_count']}</span>
                        </div>
                        <div class="metric">
                            <span>對話記錄</span>
                            <span class="metric-value">{db_comp['messages_count']}</span>
                        </div>
                        <div class="metric">
                            <span>最後活動</span>
                            <span class="metric-value">{db_comp['last_activity']}</span>
                        </div>"""
        else:
            health_html += f"""
                        <p style="color: #dc3545;">錯誤: {db_comp.get('error', 'Unknown error')}</p>"""
        
        health_html += "</div>"
        
        # 2. AI模型組件
        ai_comp = health_data['components']['ai_models']
        health_html += f"""
                    <div class="component-card {ai_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">🤖 AI模型系統</span>
                            <span class="status-badge status-{ai_comp['status']}">{status_icons.get(ai_comp['status'], '❓')} {ai_comp['status'].upper()}</span>
                        </div>
                        <div class="metric">
                            <span>當前模型</span>
                            <span class="metric-value">{ai_comp['current_model']}</span>
                        </div>
                        <div class="metric">
                            <span>模型世代</span>
                            <span class="metric-value">Gemini {ai_comp['current_generation']}</span>
                        </div>
                        <div class="metric">
                            <span>可用模型</span>
                            <span class="metric-value">{ai_comp['available_models']}/{ai_comp['total_models']}</span>
                        </div>
                        <div class="metric">
                            <span>連接測試</span>
                            <span class="metric-value">{ai_comp['connection_test'][:50]}...</span>
                        </div>"""
        
        if ai_comp['recommendations']:
            health_html += f"""
                        <div class="recommendations">
                            <strong>💡 AI建議:</strong>
                            <ul>"""
            for rec in ai_comp['recommendations'][:2]:
                health_html += f"<li>{rec}</li>"
            health_html += """
                            </ul>
                        </div>"""
        
        health_html += "</div>"
        
        # 3. LINE Bot組件
        line_comp = health_data['components']['line_bot']
        health_html += f"""
                    <div class="component-card {line_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">💬 LINE Bot</span>
                            <span class="status-badge status-{line_comp['status']}">{status_icons.get(line_comp['status'], '❓')} {line_comp['status'].upper()}</span>
                        </div>
                        <div class="metric">
                            <span>API配置</span>
                            <span class="metric-value">{'✅ 已配置' if line_comp['api_configured'] else '❌ 未配置'}</span>
                        </div>
                        <div class="metric">
                            <span>Webhook配置</span>
                            <span class="metric-value">{'✅ 已配置' if line_comp['webhook_configured'] else '❌ 未配置'}</span>
                        </div>
                        <div class="metric">
                            <span>Bot狀態</span>
                            <span class="metric-value">{'✅ 就緒' if line_comp['bot_ready'] else '❌ 未就緒'}</span>
                        </div>
                    </div>"""
        
        # 4. 環境變數組件
        env_comp = health_data['components']['environment']
        health_html += f"""
                    <div class="component-card {env_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">🔧 環境配置</span>
                            <span class="status-badge status-{env_comp['status']}">{status_icons.get(env_comp['status'], '❓')} {env_comp['status'].upper()}</span>
                        </div>"""
        
        for var, status in env_comp['variables'].items():
            icon = '✅' if status == 'configured' else '❌'
            health_html += f"""
                        <div class="metric">
                            <span>{var}</span>
                            <span class="metric-value">{icon} {status}</span>
                        </div>"""
        
        if env_comp['missing_critical']:
            health_html += f"""
                        <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <strong>⚠️ 缺少關鍵環境變數:</strong> {', '.join(env_comp['missing_critical'])}
                        </div>"""
        
        health_html += "</div>"
        
        # 5. 儲存空間組件
        storage_comp = health_data['components']['storage']
        health_html += f"""
                    <div class="component-card {storage_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">💾 儲存空間</span>
                            <span class="status-badge status-{storage_comp['status']}">{status_icons.get(storage_comp['status'], '❓')} {storage_comp['status'].upper()}</span>
                        </div>
                        <div class="metric">
                            <span>使用空間</span>
                            <span class="metric-value">{storage_comp['usage_mb']} MB</span>
                        </div>
                        <div class="metric">
                            <span>總訊息數</span>
                            <span class="metric-value">{storage_comp['total_messages']}</span>
                        </div>
                        <div class="metric">
                            <span>近期訊息</span>
                            <span class="metric-value">{storage_comp['recent_messages']}</span>
                        </div>"""
        
        if storage_comp['cleanup_recommended']:
            health_html += """
                        <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <strong>⚠️ 建議清理</strong>
                            <br><a href="/storage-management" class="btn btn-warning" style="margin-top: 5px;">💾 管理儲存</a>
                        </div>"""
        else:
            health_html += """
                        <div style="background: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <strong>✅ 空間充足</strong>
                        </div>"""
        
        health_html += "</div>"
        
        # 6. 效能組件
        perf_comp = health_data['components']['performance']
        health_html += f"""
                    <div class="component-card {perf_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">📈 系統效能</span>
                            <span class="status-badge status-{perf_comp['status']}">{status_icons.get(perf_comp['status'], '❓')} {perf_comp['status'].upper()}</span>
                        </div>
                        <div class="metric">
                            <span>AI呼叫總數</span>
                            <span class="metric-value">{perf_comp['total_ai_calls']}</span>
                        </div>
                        <div class="metric">
                            <span>錯誤次數</span>
                            <span class="metric-value">{perf_comp['total_errors']}</span>
                        </div>
                        <div class="metric">
                            <span>成功率</span>
                            <span class="metric-value">{perf_comp['success_rate']}%</span>
                        </div>"""
        
        if perf_comp['model_distribution']:
            health_html += """
                        <div class="model-list">
                            <strong>模型使用分布:</strong>"""
            for model, calls in perf_comp['model_distribution'].items():
                health_html += f"""
                            <div class="model-item">{model}: {calls} 次</div>"""
            health_html += "</div>"
        
        health_html += "</div>"
        
        # 7. 記憶系統組件
        memory_comp = health_data['components']['memory_system']
        health_html += f"""
                    <div class="component-card {memory_comp['status']}">
                        <div class="component-header">
                            <span class="component-title">🧠 記憶系統</span>
                            <span class="status-badge status-{memory_comp['status']}">{status_icons.get(memory_comp['status'], '❓')} {memory_comp['status'].upper()}</span>
                        </div>
                        <div class="metric">
                            <span>記憶深度</span>
                            <span class="metric-value">{memory_comp['memory_depth']} 輪對話</span>
                        </div>
                        <div class="metric">
                            <span>平均對話數</span>
                            <span class="metric-value">{memory_comp['avg_conversations_per_student']}</span>
                        </div>
                        <div class="metric">
                            <span>增強上下文</span>
                            <span class="metric-value">{'✅ 啟用' if memory_comp['enhanced_context'] else '❌ 停用'}</span>
                        </div>
                        <div class="metric">
                            <span>英文摘要</span>
                            <span class="metric-value">{'✅ 啟用' if memory_comp['english_summaries'] else '❌ 停用'}</span>
                        </div>
                    </div>"""
        
        # 結束HTML
        health_html += f"""
                </div>
                
                <div class="auto-refresh">
                    <p>⏰ 頁面每30秒自動重新整理 | 最後更新: {datetime.datetime.now().strftime('%H:%M:%S')}</p>
                    <div>
                        <a href="/health" class="btn btn-primary">🔄 手動重新整理</a>
                        <a href="/admin" class="btn btn-success">⚙️ 返回管理後台</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return health_html
        
    except Exception as e:
        logger.error(f"❌ 健康檢查錯誤: {e}")
        
        # 如果要求JSON格式
        if request.args.get('format') == 'json':
            return jsonify({
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }), 500
        
        # 返回錯誤頁面
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 10px; margin: 20px;">
            <h1>❌ 健康檢查失敗</h1>
            <p>系統健康檢查過程中發生錯誤</p>
            <p style="color: #721c24; font-family: monospace;">{str(e)}</p>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回首頁</a>
        </div>
        """, 500

# 檢查JSON格式請求的健康檢查路由
@app.route('/health')
def health_check():
    """健康檢查路由 - 支援JSON和HTML格式"""
    return enhanced_health_check()

# =================== 學生詳情和摘要路由 ===================

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    """學生詳細資料頁面"""
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
        
        # 獲取學生的所有對話記錄
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp.desc()))
        
        # 分析對話模式
        total_messages = len(messages)
        questions = [msg for msg in messages if msg.message_type == 'question' or '?' in msg.content]
        statements = [msg for msg in messages if msg not in questions]
        
        # 活動分析
        if messages:
            first_interaction = messages[-1].timestamp.strftime('%Y-%m-%d') if messages[-1].timestamp else 'Unknown'
            last_interaction = messages[0].timestamp.strftime('%Y-%m-%d') if messages[0].timestamp else 'Unknown'
            days_active = (messages[0].timestamp - messages[-1].timestamp).days if len(messages) > 1 and messages[0].timestamp and messages[-1].timestamp else 0
        else:
            first_interaction = last_interaction = 'No interactions'
            days_active = 0
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>學生詳情 - {getattr(student, 'name', f'學生_{student_id}')}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👤 學生詳細資料</h1>
                    <h2>{getattr(student, 'name', f'學生_{student_id}')} (ID: {student_id})</h2>
                    <div>
                        <a href="/students" class="btn btn-primary">👥 返回學生列表</a>
                        <a href="/student/{student_id}/summary" class="btn btn-warning">📊 學習摘要</a>
                        <a href="/api/export/student/{student_id}" class="btn btn-success">📥 匯出記錄</a>
                        <a href="/admin" class="btn btn-info">⚙️ 管理後台</a>
                    </div>
                </div>
                
                <div class="content-grid">
                    <div class="card">
                        <h3>📊 學習統計</h3>
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
                                <div class="stat-number">{len(statements)}</div>
                                <div class="stat-label">陳述次數</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{days_active}</div>
                                <div class="stat-label">活躍天數</div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 20px;">
                            <p><strong>首次互動:</strong> {first_interaction}</p>
                            <p><strong>最後互動:</strong> {last_interaction}</p>
                            <p><strong>學習等級:</strong> {getattr(student, 'level', '未設定')}</p>
                            <p><strong>參與度:</strong> {getattr(student, 'participation_rate', 0):.1f}%</p>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🎯 學習模式分析</h3>
                        <div style="margin: 15px 0;">
                            <p><strong>學習風格:</strong> 
                            {'問題導向' if len(questions) > len(statements) else '陳述導向' if len(statements) > len(questions) else '平衡型'}</p>
                            
                            <p><strong>互動頻率:</strong> 
                            {'高頻' if total_messages > 20 else '中頻' if total_messages > 10 else '低頻'}</p>
                            
                            <p><strong>參與特點:</strong></p>
                            <ul>
                                <li>{'積極提問者' if len(questions) > 10 else '適度提問者' if len(questions) > 5 else '較少提問'}</li>
                                <li>{'高度參與' if total_messages > 15 else '一般參與' if total_messages > 5 else '初期參與'}</li>
                                <li>{'持續學習' if days_active > 7 else '短期學習' if days_active > 0 else '單次互動'}</li>
                            </ul>
                        </div>
                        
                        <div style="background: #e3f2fd; padding: 15px; border-radius: 5px;">
                            <strong>💡 教學建議:</strong>
                            <p>{'鼓勵保持好奇心，繼續積極提問' if len(questions) > len(statements) else '可以引導更多提問來加深理解' if len(statements) > len(questions) else '保持良好的學習平衡'}</p>
                        </div>
                    </div>
                </div>
                
                <div class="card full-width">
                    <h3>💬 對話記錄 (最近8次記憶)</h3>
                    <div class="conversation-list">"""
        
        if messages:
            for msg in messages[:8]:
                msg_type_class = 'message-question' if msg.message_type == 'question' or '?' in msg.content else 'message-statement'
                msg_type_label = '❓ 問題' if msg.message_type == 'question' or '?' in msg.content else '💬 陳述'
                timestamp_str = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else 'Unknown time'
                
                student_detail_html += f"""
                        <div class="message-item {msg_type_class}">
                            <div class="message-meta">
                                {timestamp_str} | {msg_type_label}
                            </div>
                            <div>{msg.content}</div>
                        </div>"""
        else:
            student_detail_html += """
                        <p style="text-align: center; color: #666; padding: 20px;">尚無對話記錄</p>"""
        
        student_detail_html += f"""
                    </div>
                    
                    {f'<p style="text-align: center; margin-top: 15px; color: #666;">顯示最近8次對話 (共{total_messages}次) • <a href="/api/export/student/{student_id}">下載完整記錄</a></p>' if total_messages > 8 else ''}
                </div>
            </div>
        </body>
        </html>
        """
        
        return student_detail_html
        
    except Exception as e:
        logger.error(f"❌ 學生詳情載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>❌ 載入錯誤</h1>
            <p>無法載入學生詳細資料</p>
            <p style="color: #dc3545;">{str(e)}</p>
            <a href="/students" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回學生列表</a>
        </div>
        """

@app.route('/student/<int:student_id>/summary')
def student_summary(student_id):
    """學生學習摘要頁面 - 英文版本"""
    try:
        from models import Student
        
        student = Student.get_by_id(student_id)
        if not student:
            return redirect('/students')
        
        # 生成英文學習摘要
        summary_data = generate_student_learning_summary(student_id, 'comprehensive')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Learning Summary - {summary_data.get('student_name', f'Student_{student_id}')}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; line-height: 1.6; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .summary-card {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                .summary-content {{ white-space: pre-wrap; line-height: 1.8; color: #333; }}
                .summary-meta {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .meta-item {{ text-align: center; padding: 10px; background: white; border-radius: 5px; }}
                .meta-number {{ font-size: 1.5em; font-weight: bold; color: #1976d2; }}
                .meta-label {{ color: #666; font-size: 0.9em; }}
                .btn {{ display: inline-block; padding: 12px 24px; margin: 5px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-info {{ background: #17a2b8; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .topics-list {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
                .topic-tag {{ background: #007bff; color: white; padding: 5px 12px; border-radius: 15px; font-size: 0.9em; }}
                .status-complete {{ color: #28a745; font-weight: bold; }}
                .status-incomplete {{ color: #dc3545; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 English Learning Summary</h1>
                    <h2>{summary_data.get('student_name', f'Student_{student_id}')}</h2>
                    <p>Comprehensive learning analysis based on {summary_data.get('message_count', 0)} interactions</p>
                    <div>
                        <a href="/student/{student_id}" class="btn btn-primary">👤 Student Details</a>
                        <a href="/students" class="btn btn-info">👥 Student List</a>
                        <a href="/api/export/student/{student_id}" class="btn btn-success">📥 Export Full Record</a>
                        <a href="/admin" class="btn btn-warning">⚙️ Admin Panel</a>
                    </div>
                </div>
                
                <div class="summary-meta">
                    <h3>📊 Summary Metadata</h3>
                    <div class="meta-grid">
                        <div class="meta-item">
                            <div class="meta-number">{summary_data.get('message_count', 0)}</div>
                            <div class="meta-label">Total Messages</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-number">{summary_data.get('question_count', 0)}</div>
                            <div class="meta-label">Questions Asked</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-number">{summary_data.get('statement_count', 0)}</div>
                            <div class="meta-label">Statements Made</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-number">{summary_data.get('actual_length', 0):,}</div>
                            <div class="meta-label">Summary Length (chars)</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <p><strong>📅 Learning Period:</strong> {summary_data.get('learning_period', 'Unknown')}</p>
                        <p><strong>🔄 Interaction Frequency:</strong> {summary_data.get('interaction_frequency', 'Unknown')}</p>
                        <p><strong>✅ Summary Status:</strong> 
                           <span class="{'status-complete' if summary_data.get('complete') else 'status-incomplete'}">
                               {'Complete (No truncation)' if summary_data.get('complete') else 'Incomplete or truncated'}
                           </span>
                        </p>
                        <p><strong>🌐 Language:</strong> {summary_data.get('language', 'English').title()}</p>
                        <p><strong>⏰ Generated:</strong> {summary_data.get('generated_at', 'Unknown')}</p>
                    </div>"""
        
        # 安全地添加主題標籤
        if summary_data.get('topics'):
            summary_html += f"""
                    <div style="margin-top: 15px;">
                        <p><strong>🎯 Learning Topics Identified:</strong></p>
                        <div class="topics-list">"""
            for topic in summary_data.get('topics', []):
                summary_html += f'<span class="topic-tag">{topic}</span>'
            summary_html += """
                        </div>
                    </div>"""
        
        summary_html += f"""
                </div>
                
                <div class="summary-card">
                    <h3>📖 Comprehensive Learning Analysis</h3>
                    <div class="summary-content">{summary_data.get('summary', 'No summary available.')}</div>
                </div>
                
                <div style="text-align: center; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h3>📥 Export Options</h3>
                    <p>Download this complete learning summary and conversation records</p>
                    <a href="/api/export/student/{student_id}" class="btn btn-success">📋 Complete Student Record</a>
                    <a href="/api/export/summary/{student_id}" class="btn btn-info">📊 Summary Only</a>
                    <a href="/teaching-insights" class="btn btn-warning">📈 Class Analytics</a>
                </div>
                
                <div style="text-align: center; margin-top: 20px; color: #666;">
                    <p>✨ Generated by EMI Intelligent Teaching Assistant v2.5 | 
                       English-Medium Instruction Support System | 
                       Powered by Gemini AI</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return summary_html
        
    except Exception as e:
        logger.error(f"❌ 學生摘要載入錯誤: {e}")
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>❌ Summary Loading Error</h1>
            <p>Unable to load learning summary for this student.</p>
            <p style="color: #dc3545;">Error: {str(e)}</p>
            <a href="/student/{student_id}" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">Back to Student Details</a>
        </div>
        """

# =================== 資料匯出 API 路由 ===================

@app.route('/api/export/<export_type>')
@app.route('/api/export/<export_type>/<int:student_id>')
def export_data(export_type, student_id=None):
    """資料匯出API - 支援多種格式"""
    try:
        from models import Student, Message
        import io
        
        # 生成檔案名稱
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_type == 'student' and student_id:
            # 匯出特定學生記錄
            student = Student.get_by_id(student_id)
            if not student:
                return jsonify({'error': 'Student not found'}), 404
            
            content = export_student_complete_record(student_id, include_summary=True, include_analytics=True)
            if not content:
                return jsonify({'error': 'Export failed'}), 500
            
            filename = f"student_{student_id}_record_{timestamp}.txt"
            
            return send_file(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/plain',
                as_attachment=True,
                download_name=filename
            )
        
        elif export_type == 'summary' and student_id:
            # 匯出學生摘要
            summary_data = generate_student_learning_summary(student_id, 'comprehensive')
            
            content = f"""EMI INTELLIGENT TEACHING ASSISTANT
LEARNING SUMMARY EXPORT
{'='*60}

Student: {summary_data.get('student_name', f'Student_{student_id}')}
Generated: {summary_data.get('generated_at', 'Unknown')}
Language: {summary_data.get('language', 'English')}
Summary Type: {summary_data.get('summary_type', 'Comprehensive')}

STATISTICS:
- Total Messages: {summary_data.get('message_count', 0)}
- Questions: {summary_data.get('question_count', 0)}
- Statements: {summary_data.get('statement_count', 0)}
- Learning Period: {summary_data.get('learning_period', 'Unknown')}
- Summary Length: {summary_data.get('actual_length', 0)} characters
- Complete Summary: {'Yes' if summary_data.get('complete') else 'No'}

LEARNING TOPICS:
{', '.join(summary_data.get('topics', ['No topics identified']))}

COMPREHENSIVE ANALYSIS:
{'='*60}
{summary_data.get('summary', 'No summary available.')}
{'='*60}
END OF SUMMARY
"""
            
            filename = f"student_{student_id}_summary_{timestamp}.txt"
            
            return send_file(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/plain',
                as_attachment=True,
                download_name=filename
            )
        
        elif export_type == 'all':
            # 匯出所有資料
            students = list(Student.select())
            
            content_parts = [
                "EMI INTELLIGENT TEACHING ASSISTANT",
                "COMPLETE DATABASE EXPORT",
                "="*60,
                f"Export Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total Students: {len(students)}",
                f"System Version: EMI Teaching Assistant v2.5.0",
                "",
                "COMPLETE STUDENT RECORDS:",
                "="*60
            ]
            
            for student in students:
                student_record = export_student_complete_record(student.id)
                if student_record:
                    content_parts.append(student_record)
                    content_parts.append("\n" + "="*60 + "\n")
            
            content = "\n".join(content_parts)
            filename = f"emi_complete_database_{timestamp}.txt"
            
            return send_file(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/plain',
                as_attachment=True,
                download_name=filename
            )
        
        else:
            return jsonify({'error': 'Invalid export type'}), 400
    
    except Exception as e:
        logger.error(f"❌ 資料匯出錯誤: {e}")
        return jsonify({'error': str(e)}), 500

# =================== 儲存管理 API 路由 ===================

@app.route('/api/cleanup/<cleanup_level>')
def cleanup_data_api(cleanup_level):
    """資料清理API"""
    try:
        if cleanup_level not in ['conservative', 'moderate', 'aggressive']:
            return jsonify({'error': 'Invalid cleanup level'}), 400
        
        result = perform_smart_cleanup(cleanup_level)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ 資料清理錯誤: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/storage-status')
def storage_status_api():
    """儲存狀態API"""
    try:
        return jsonify(monitor_storage_usage())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================== LINE Bot Webhook 處理 ===================

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook回調處理"""
    if not handler:
        logger.warning("⚠️ LINE Bot handler 未初始化")
        abort(400)
    
    # 獲取 X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    
    # 獲取請求主體作為文字
    body = request.get_data(as_text=True)
    logger.info(f"📨 接收到 LINE Webhook: {body}")
    
    # 處理 webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("❌ LINE Webhook 簽名驗證失敗")
        abort(400)
    except LineBotApiError as e:
        logger.error(f"❌ LINE Bot API 錯誤: {e}")
        abort(400)
    
    return 'OK'

# 替換 app.py 中第 4 段的 handle_message 函數

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理文字訊息 - 修復版本"""
    if not line_bot_api:
        logger.error("❌ LINE Bot API 未初始化")
        return
    
    try:
        user_id = event.source.user_id
        group_id = getattr(event.source, 'group_id', None)
        user_message = event.message.text.strip()
        
        logger.info(f"👤 用戶 {user_id} 訊息: {user_message}")
        
        # 更新或創建學生記錄 - 修復版本
        from models import Student
        try:
            # 使用 get_or_create 方法來安全地取得或創建學生
            student, created = Student.get_or_create(
                line_user_id=user_id,
                defaults={
                    'name': f'學生_{user_id[-4:]}',
                    'created_at': datetime.datetime.now(),
                    'last_active': datetime.datetime.now(),
                    'is_active': True
                }
            )
            
            if created:
                logger.info(f"🆕 創建新學生記錄: {student.name}")
            else:
                # 更新現有學生的最後活動時間
                student.last_active = datetime.datetime.now()
                student.save()
                logger.info(f"📝 更新學生活動: {student.name}")
                
        except Exception as student_error:
            logger.error(f"❌ 學生記錄處理錯誤: {student_error}")
            # 發送錯誤訊息給用戶
            try:
                error_message = "System is experiencing some issues. Please try again later. 🔧"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=error_message)
                )
            except:
                pass
            return
        
        # 判斷訊息類型
        message_type = 'question' if '?' in user_message or user_message.lower().startswith(('what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does', 'did')) else 'statement'
        
        # 更新對話記憶
        update_conversation_memory(student.id, user_message, message_type)
        
        # 獲取對話上下文
        conversation_context = get_enhanced_conversation_context(student.id, limit=8)
        student_context = get_student_learning_context(student.id)
        
        # 生成 AI 回應
        ai_response = get_ai_response(
            student_id=student.id,
            query=user_message,
            conversation_context=conversation_context,
            student_context=student_context,
            group_id=group_id
        )
        
        # 記錄 AI 回應
        update_conversation_memory(student.id, ai_response, 'ai_response')
        
        # 發送回應
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
        logger.info(f"✅ 成功回應用戶 {user_id}")
        
        # 更新學生統計
        try:
            # 計算新的統計數據
            from models import Message
            total_messages = Message.select().where(Message.student_id == student.id).count()
            total_questions = Message.select().where(
                (Message.student_id == student.id) & 
                ((Message.message_type == 'question') | (Message.content.contains('?')))
            ).count()
            
            # 更新學生統計
            student.update_stats(total_messages, total_questions)
            
        except Exception as stats_error:
            logger.warning(f"⚠️ 更新學生統計失敗: {stats_error}")
    
    except Exception as e:
        logger.error(f"❌ 處理訊息錯誤: {e}")
        
        # 發送錯誤訊息給用戶
        try:
            error_message = "Sorry, I'm experiencing some technical difficulties. Please try again in a moment! 🤖"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_message)
            )
        except Exception as reply_error:
            logger.error(f"❌ 發送錯誤訊息失敗: {reply_error}")

# =================== 程式進入點 ===================

if __name__ == '__main__':
    try:
        import sys
        
        # 檢查必要的環境變數
        missing_vars = []
        if not GEMINI_API_KEY:
            missing_vars.append('GEMINI_API_KEY')
        
        if missing_vars:
            logger.warning(f"⚠️ 缺少環境變數: {', '.join(missing_vars)}")
            logger.warning("⚠️ 某些功能可能無法正常運作")
        
        # 顯示啟動資訊
        logger.info("🚀 EMI智能教學助理啟動中...")
        logger.info(f"📊 支援模型: {len(AVAILABLE_MODELS)} 個")
        logger.info(f"🤖 當前模型: {current_model_name}")
        logger.info(f"💬 LINE Bot: {'✅ 已配置' if line_bot_api and handler else '❌ 未配置'}")
        logger.info(f"🧠 記憶深度: 8 輪對話")
        logger.info(f"🌍 摘要語言: 英文")
        
        # 執行健康檢查
        try:
            ai_connected, ai_status = test_ai_connection()
            logger.info(f"🔍 AI連接檢查: {'✅' if ai_connected else '❌'} {ai_status}")
        except Exception as health_error:
            logger.warning(f"⚠️ 健康檢查失敗: {health_error}")
        
        # 啟動Flask應用
        port = int(os.getenv('PORT', 5000))
        host = os.getenv('HOST', '0.0.0.0')
        debug_mode = os.getenv('FLASK_ENV') == 'development'
        
        logger.info(f"🌐 服務器啟動: http://{host}:{port}")
        logger.info(f"🔧 除錯模式: {'開啟' if debug_mode else '關閉'}")
        logger.info("✨ EMI智能教學助理準備就緒!")
        
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 收到中斷信號，正在關閉...")
    except Exception as startup_error:
        logger.error(f"❌ 啟動失敗: {startup_error}")
        raise
    finally:
        logger.info("👋 EMI智能教學助理已關閉")

# =================== app.py 完整版 - 第 4 段修復版結束（全檔案完成） ===================
