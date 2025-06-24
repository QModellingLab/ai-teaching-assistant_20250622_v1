# utils.py - 修復版本（解決第 595 行 f-string 反斜線錯誤）

import os
import logging
import json
import datetime
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
import google.generativeai as genai
from models import Student, Message, Analysis, AIResponse, db

# 設定日誌
logger = logging.getLogger(__name__)

# =================== AI 模型配置 ===================

# 取得 API 金鑰
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Gemini
model = None
current_model_name = "gemini-1.5-flash"
model_rotation_index = 0

# 建議的模型優先順序配置
# 基於配額、性能和版本新舊程度

AVAILABLE_MODELS = [
    "gemini-2.0-flash",        # 🥇 最優先：最新版本 + 高配額(200次/日)
    "gemini-2.0-flash-lite",   # 🥈 第二：輕量版 + 高配額(200次/日)  
    "gemini-1.5-flash",        # 🥉 第三：成熟穩定 + 中配額(50次/日)
    "gemini-1.5-flash-8b",     # 🏅 第四：效率優化 + 中配額(50次/日)
    "gemini-1.5-pro",          # 🏅 第五：功能完整但較慢
    "gemini-1.0-pro",          # 🏅 最後備用：舊版本但穩定
]

# 調整理由：
# 1. 2.0 版本優先（配額更高，性能更好）
# 2. 1.5-flash-8b 比 1.0-pro 優先（版本更新 + 速度更快）
# 3. 保持向下兼容的備用方案

# 模型使用統計
model_usage_stats = {model: {'calls': 0, 'errors': 0, 'last_used': None} for model in AVAILABLE_MODELS}

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(current_model_name)
        logger.info(f"✅ Gemini AI 初始化成功 - 使用模型: {current_model_name}")
    except Exception as e:
        logger.error(f"❌ Gemini AI 初始化失敗: {e}")
        model = None
else:
    logger.warning("⚠️ GEMINI_API_KEY 未設定")

# =================== 模型管理功能 ===================

def record_model_usage(model_name: str, success: bool = True):
    """記錄模型使用統計"""
    if model_name in model_usage_stats:
        model_usage_stats[model_name]['calls'] += 1
        model_usage_stats[model_name]['last_used'] = time.time()
        if not success:
            model_usage_stats[model_name]['errors'] += 1

def get_next_available_model() -> str:
    """取得下一個可用模型"""
    global model_rotation_index
    
    # 簡單的循環選擇
    model_rotation_index = (model_rotation_index + 1) % len(AVAILABLE_MODELS)
    return AVAILABLE_MODELS[model_rotation_index]

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

def get_quota_status() -> Dict:
    """取得配額狀態"""
    status = {
        'current_model': current_model_name,
        'models': {},
        'recommendations': []
    }
    
    # 模擬配額檢查（實際應用中需要真實的配額檢查）
    for model_name in AVAILABLE_MODELS:
        stats = model_usage_stats[model_name]
        error_rate = (stats['errors'] / max(stats['calls'], 1)) * 100
        
        # 基於錯誤率估算可用性
        if error_rate > 50:
            usage_percent = 100  # 可能配額已用完
        elif error_rate > 20:
            usage_percent = 80
        else:
            usage_percent = min(50, stats['calls'] * 2)  # 基於使用次數估算
        
        status['models'][model_name] = {
            'usage_percent': usage_percent,
            'calls': stats['calls'],
            'errors': stats['errors'],
            'status': '可用' if usage_percent < 100 else '已用完'
        }
    
    # 生成建議
    available_models = [name for name, info in status['models'].items() if info['usage_percent'] < 100]
    if not available_models:
        status['recommendations'].append("所有模型配額已用完，建議等待重置或升級方案")
    elif len(available_models) == 1:
        status['recommendations'].append(f"僅剩 {available_models[0]} 可用，建議節約使用")
    
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

# =================== AI 回應生成 ===================

def generate_ai_response_with_smart_fallback(student_id, query, conversation_context="", student_context="", group_id=None):
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
            return "AI service quota exceeded. Please try again later when quota resets (typically at midnight UTC). Please try again later or contact administrator to upgrade the service plan."
        
        # 構建提示詞 - 修復 f-string 反斜線問題
        student = Student.get_by_id(student_id) if student_id else None
        
        # 修復：使用 chr(10) 替代 \n 來避免 f-string 中的反斜線
        newline = chr(10)
        
        # 構建前置對話內容
        conversation_prefix = f"Previous conversation context:{newline}{conversation_context}{newline}" if conversation_context else ""
        
        prompt = f"""You are an AI Teaching Assistant for English-medium instruction (EMI) courses.

{conversation_prefix}

Instructions:
- Respond primarily in clear, simple English suitable for university-level ESL learners
- Use vocabulary appropriate for intermediate English learners
- For technical terms, provide Chinese translation in parentheses when helpful
- Maintain a friendly, encouraging, and educational tone
- Keep responses concise but helpful (50-150 words)
- If this continues a previous conversation, build on what was discussed before

{student_context if student_context else ""}

Student question: {query}

Please provide a helpful response:"""
        
        logger.info(f"🤖 使用 {current_model_name} 生成回應...")
        
        # 根據模型調整配置
        if 'lite' in current_model_name or '8b' in current_model_name:
            # 輕量模型使用較保守的設定
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=300,
                temperature=0.6,
                top_p=0.8,
                top_k=30
            )
        else:
            # 標準模型設定
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=350,
                temperature=0.7,
                top_p=0.9,
                top_k=40
            )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and response.text:
            # 記錄成功使用
            record_model_usage(current_model_name, True)
            
            ai_response = response.text.strip()
            logger.info(f"✅ AI 回應成功生成，長度: {len(ai_response)} 字")
            
            # 基本內容檢查
            if len(ai_response) < 10:
                logger.warning("⚠️ AI 回應過短，使用備用回應")
                return get_fallback_response(query)
            
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            record_model_usage(current_model_name, False)
            return get_fallback_response(query)
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ AI 回應錯誤: {str(e)}")
        record_model_usage(current_model_name, False)
        
        # 智慧錯誤處理
        if "429" in error_msg or "quota" in error_msg or "limit" in error_msg:
            # 配額問題，嘗試切換模型
            logger.warning("🔄 偵測到配額問題，嘗試切換模型...")
            success = switch_to_available_model()
            if success:
                logger.info(f"✅ 已切換到 {current_model_name}，重新嘗試...")
                # 遞迴重試一次
                return generate_ai_response_with_smart_fallback(student_id, query, conversation_context, student_context, group_id)
            else:
                return "AI service quota exceeded. Please try again later when quota resets (typically at midnight UTC)."
        elif "403" in error_msg or "unauthorized" in error_msg:
            return "I'm having authentication issues. Please contact your teacher to check the system configuration. 🔧"
        elif "network" in error_msg or "connection" in error_msg:
            return "I'm having connection problems. Please try again in a moment. 📡"
        else:
            return get_fallback_response(query)

def get_fallback_response(user_message):
    """備用回應生成器"""
    user_msg_lower = user_message.lower()
    
    # 基於關鍵詞的簡單回應
    if any(word in user_msg_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm your English learning assistant. How can I help you today? 👋"
    
    elif any(word in user_msg_lower for word in ['grammar', 'grammer']):
        return "I'd love to help with grammar! Can you share the specific sentence or rule you're wondering about? 📝"
    
    elif any(word in user_msg_lower for word in ['vocabulary', 'word', 'meaning']):
        return "I'm here to help with vocabulary! What word would you like to learn about? 📚"
    
    elif any(word in user_msg_lower for word in ['pronunciation', 'pronounce', 'speak']):
        return "Pronunciation is important! While I can't hear you speak, I can help explain how words are pronounced. What word are you working on? 🗣️"
    
    elif '?' in user_message:
        return "That's a great question! I'm having some technical difficulties right now, but I'm working to get back to full functionality. Can you try asking again in a moment? 🤔"
    
    else:
        return "I received your message! I'm currently having some technical issues, but I'm here to help with your English learning. Please try again in a moment. 📚"

# 兼容性：保持原有函數名稱
def generate_ai_response(student_id, query, conversation_context="", student_context="", group_id=None):
    """原有函數的兼容性包裝"""
    return generate_ai_response_with_smart_fallback(student_id, query, conversation_context, student_context, group_id)

# =================== 學生分析功能 ===================

def analyze_student_patterns(student_id):
    """分析學生學習模式"""
    try:
        student = Student.get_by_id(student_id)
        messages = list(Message.select().where(Message.student_id == student_id))
        
        # 分析訊息類型分布
        message_types = {}
        for msg in messages:
            msg_type = msg.message_type or 'general'
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        # 分析活動時間模式
        if messages:
            timestamps = [msg.timestamp for msg in messages if msg.timestamp]
            if timestamps:
                earliest = min(timestamps)
                latest = max(timestamps)
                active_days = (latest - earliest).days + 1
            else:
                active_days = 0
        else:
            active_days = 0
        
        # 計算平均訊息長度
        if messages:
            avg_length = sum(len(msg.content) for msg in messages) / len(messages)
        else:
            avg_length = 0
        
        # 分析參與度
        total_messages = len(messages)
        if total_messages >= 20:
            engagement_level = "高度參與"
        elif total_messages >= 10:
            engagement_level = "中度參與"
        elif total_messages >= 5:
            engagement_level = "輕度參與"
        else:
            engagement_level = "極少參與"
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'total_messages': total_messages,
            'message_types': message_types,
            'active_days': active_days,
            'avg_message_length': round(avg_length, 2),
            'engagement_level': engagement_level,
            'analysis_date': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"學生模式分析錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e),
            'analysis_date': datetime.datetime.now().isoformat()
        }

def update_student_stats(student_id):
    """更新學生統計資料"""
    try:
        student = Student.get_by_id(student_id)
        
        # 計算訊息統計
        messages = list(Message.select().where(Message.student_id == student_id))
        total_messages = len(messages)
        
        # 計算參與率（基於訊息數量）
        if total_messages >= 50:
            participation_rate = 95
        elif total_messages >= 20:
            participation_rate = 80
        elif total_messages >= 10:
            participation_rate = 60
        elif total_messages >= 5:
            participation_rate = 40
        else:
            participation_rate = 20
        
        # 更新學生記錄
        student.total_messages = total_messages
        student.participation_rate = participation_rate
        student.last_active = datetime.datetime.now()
        student.save()
        
        logger.info(f"✅ 學生統計已更新 - {student.name}: {total_messages} 訊息, 參與率 {participation_rate}%")
        
    except Exception as e:
        logger.error(f"更新學生統計錯誤: {e}")

def get_question_category_stats():
    """取得問題分類統計"""
    try:
        # 取得所有分析記錄
        analyses = list(Analysis.select().where(
            Analysis.analysis_type == 'question_classification'
        ))
        
        category_stats = {
            'total_questions': len(analyses),
            'categories': Counter(),
            'cognitive_levels': Counter(),
            'content_domains': Counter()
        }
        
        for analysis in analyses:
            try:
                data = json.loads(analysis.analysis_data)
                category_stats['categories'][data.get('category', 'Unknown')] += 1
                category_stats['cognitive_levels'][data.get('cognitive_level', 'Unknown')] += 1
                category_stats['content_domains'][data.get('content_domain', 'Unknown')] += 1
            except json.JSONDecodeError:
                continue
        
        # 轉換 Counter 為字典
        for key in ['categories', 'cognitive_levels', 'content_domains']:
            category_stats[key] = dict(category_stats[key])
        
        return category_stats
        
    except Exception as e:
        logger.error(f"問題分類統計錯誤: {e}")
        return {
            'total_questions': 0,
            'categories': {},
            'cognitive_levels': {},
            'content_domains': {},
            'error': str(e)
        }

def get_student_conversation_summary(student_id, days=30):
    """取得學生對話摘要"""
    try:
        student = Student.get_by_id(student_id)
        
        # 取得指定天數內的訊息
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        messages = list(Message.select().where(
            (Message.student_id == student_id) &
            (Message.timestamp >= cutoff_date)
        ).order_by(Message.timestamp.desc()))
        
        if not messages:
            return {
                'student_id': student_id,
                'student_name': student.name,
                'period_days': days,
                'message_count': 0,
                'summary': '在此期間沒有對話記錄',
                'status': 'no_data'
            }
        
        # 分析訊息類型
        questions = [msg for msg in messages if msg.message_type == 'question']
        statements = [msg for msg in messages if msg.message_type == 'statement']
        
        # 產生簡單摘要
        summary_parts = []
        summary_parts.append(f"在最近 {days} 天內，{student.name} 共發送了 {len(messages)} 則訊息")
        
        if questions:
            summary_parts.append(f"其中包含 {len(questions)} 個問題")
        
        if statements:
            summary_parts.append(f"以及 {len(statements)} 個陳述")
        
        # 計算活躍度
        if len(messages) >= 10:
            activity_level = "高度活躍"
        elif len(messages) >= 5:
            activity_level = "適度活躍"
        else:
            activity_level = "較少參與"
        
        summary_parts.append(f"整體參與度為：{activity_level}")
        
        return {
            'student_id': student_id,
            'student_name': student.name,
            'period_days': days,
            'message_count': len(messages),
            'question_count': len(questions),
            'statement_count': len(statements),
            'activity_level': activity_level,
            'summary': '。'.join(summary_parts) + '。',
            'generated_at': datetime.datetime.now().isoformat(),
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"對話摘要錯誤: {e}")
        return {
            'student_id': student_id,
            'error': str(e),
            'status': 'error'
        }

# =================== 相容性函數 ===================

# 主要 AI 回應函數別名
get_ai_response = generate_ai_response_with_smart_fallback

# 學生分析函數別名
analyze_student_pattern = analyze_student_patterns

# =================== 匯出函數列表 ===================

__all__ = [
    # AI 回應生成
    'generate_ai_response_with_smart_fallback',
    'generate_ai_response',
    'get_ai_response',
    'get_fallback_response',
    
    # 模型管理
    'switch_to_available_model',
    'get_quota_status',
    'test_ai_connection',
    'record_model_usage',
    
    # 學生分析
    'analyze_student_patterns',
    'analyze_student_pattern',
    'update_student_stats',
    'get_question_category_stats',
    'get_student_conversation_summary',
    
    # 常數
    'AVAILABLE_MODELS',
    'current_model_name'
]
