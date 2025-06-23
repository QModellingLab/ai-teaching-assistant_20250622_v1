# utils.py - 配額感知的智慧備案系統

import os
import json
import datetime
import logging
import time
import google.generativeai as genai
from models import Student, Message, Analysis, db

logger = logging.getLogger(__name__)

# 初始化 Gemini AI - 智慧配額管理
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
model = None
current_model_name = None

# 配額追蹤字典
quota_tracker = {
    'gemini-2.0-flash': {'daily_limit': 200, 'used_today': 0, 'last_reset': None},
    'gemini-2.0-flash-lite': {'daily_limit': 200, 'used_today': 0, 'last_reset': None},
    'gemini-1.5-flash': {'daily_limit': 1500, 'used_today': 0, 'last_reset': None},  # 1.5 版本通常有更高限制
    'gemini-1.5-pro': {'daily_limit': 50, 'used_today': 0, 'last_reset': None},
}

def reset_daily_quota_if_needed():
    """檢查是否需要重置每日配額計數"""
    today = datetime.date.today()
    
    for model_name in quota_tracker:
        tracker = quota_tracker[model_name]
        if tracker['last_reset'] != today:
            tracker['used_today'] = 0
            tracker['last_reset'] = today
            logger.info(f"🔄 重置 {model_name} 每日配額計數")

def is_model_available(model_name):
    """檢查模型是否還有配額可用"""
    reset_daily_quota_if_needed()
    
    if model_name not in quota_tracker:
        return True  # 未知模型，假設可用
    
    tracker = quota_tracker[model_name]
    available = tracker['used_today'] < tracker['daily_limit']
    
    if not available:
        logger.warning(f"⚠️ {model_name} 配額已用完 ({tracker['used_today']}/{tracker['daily_limit']})")
    
    return available

def record_model_usage(model_name):
    """記錄模型使用次數"""
    if model_name in quota_tracker:
        quota_tracker[model_name]['used_today'] += 1
        used = quota_tracker[model_name]['used_today']
        limit = quota_tracker[model_name]['daily_limit']
        logger.info(f"📊 {model_name} 使用量: {used}/{limit}")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 智慧模型選擇 - 依配額可用性排序
        models_to_try = [
            # 優先使用還有配額的模型
            'gemini-2.0-flash-lite',     # 您還有 36% 配額可用
            'gemini-1.5-flash',          # 通常配額更高
            'gemini-1.5-flash-001',      
            'gemini-1.5-flash-8b',       # 8B 版本更經濟
            'gemini-1.5-pro',            # 功能更強但配額較少
            'gemini-1.5-pro-001',
            'gemini-2.0-flash',          # 已超限，但可能半夜重置
            'gemini-2.0-flash-001',      
            'gemini-1.0-pro',            # 最後備案
            'gemini-1.0-pro-001'
        ]
        
        for model_name in models_to_try:
            # 檢查配額狀態
            if not is_model_available(model_name):
                logger.info(f"⏭️ 跳過 {model_name} (配額不足)")
                continue
                
            try:
                test_model = genai.GenerativeModel(model_name)
                
                # 輕量測試（避免浪費配額）
                test_response = test_model.generate_content(
                    "Test",
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=5,
                        temperature=0.1
                    )
                )
                
                if test_response and test_response.text:
                    model = test_model
                    current_model_name = model_name
                    record_model_usage(model_name)  # 記錄測試使用
                    logger.info(f"✅ Gemini AI 成功初始化，使用模型: {model_name}")
                    break
                    
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    logger.warning(f"⚠️ {model_name} 配額超限，標記為不可用")
                    # 標記為已用完
                    if model_name in quota_tracker:
                        quota_tracker[model_name]['used_today'] = quota_tracker[model_name]['daily_limit']
                elif "403" in error_msg:
                    logger.warning(f"⚠️ {model_name} 權限不足: {error_msg[:50]}")
                elif "404" in error_msg:
                    logger.warning(f"⚠️ {model_name} 模型不存在")
                else:
                    logger.warning(f"⚠️ {model_name} 測試失敗: {error_msg[:50]}")
                continue
        
        if not model:
            logger.error("❌ 所有 Gemini 模型都不可用")
            logger.info("💡 建議解決方案:")
            logger.info("   1. 等待配額重置（通常為 UTC 午夜）")
            logger.info("   2. 升級到付費方案以獲得更高配額")
            logger.info("   3. 新增其他 AI 服務商作為備案")
            
    except Exception as e:
        logger.error(f"❌ Gemini AI 初始化失敗: {e}")
else:
    logger.warning("⚠️ Gemini API key not found")

def generate_ai_response_with_smart_fallback(student_id, query, conversation_context="", student_context="", group_id=None):
    """智慧備案的 AI 回應生成"""
    global model, current_model_name
    
    if not model:
        logger.error("❌ AI 模型未初始化")
        return "Sorry, AI service is currently unavailable. This might be due to daily quota limits. Please try again later."
    
    try:
        # 檢查當前模型是否還有配額
        if not is_model_available(current_model_name):
            logger.warning(f"⚠️ 當前模型 {current_model_name} 配額不足，嘗試切換...")
            
            # 嘗試切換到其他可用模型
            success = switch_to_available_model()
            if not success:
                return "AI service has reached daily quota limits. Please try again later or contact administrator to upgrade the service plan."
        
        # 構建提示詞
        student = Student.get_by_id(student_id) if student_id else None
        
        prompt = f"""You are an AI Teaching Assistant for English-medium instruction (EMI) courses.

{"Previous conversation context:" + chr(10) + conversation_context + chr(10) if conversation_context else ""}

Instructions:
- Respond primarily in clear, simple English suitable for university-level ESL learners
- Use vocabulary appropriate for intermediate English learners
- For technical terms, provide Chinese translation in parentheses when helpful
- Maintain a friendly, encouraging, and educational tone
- If this continues a previous conversation, build on what was discussed before
- Encourage further questions and deeper thinking

{student_context if student_context else ""}

Student question: {query}

Please provide a helpful response (100-150 words):"""
        
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
            record_model_usage(current_model_name)
            
            ai_response = response.text.strip()
            logger.info(f"✅ AI 回應成功生成，長度: {len(ai_response)} 字")
            return ai_response
        else:
            logger.error("❌ AI 回應為空")
            return "Sorry, I cannot generate an appropriate response right now. Please try again later."
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ AI 回應錯誤: {str(e)}")
        
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
        else:
            return "An error occurred while processing your question. Please try again later."

def switch_to_available_model():
    """切換到可用的模型"""
    global model, current_model_name
    
    models_to_try = [
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash', 
        'gemini-1.5-flash-8b',
        'gemini-1.5-pro',
        'gemini-2.0-flash',
        'gemini-1.0-pro'
    ]
    
    for model_name in models_to_try:
        if model_name == current_model_name:
            continue  # 跳過當前模型
            
        if not is_model_available(model_name):
            continue
            
        try:
            test_model = genai.GenerativeModel(model_name)
            # 快速測試
            test_response = test_model.generate_content(
                "Hi",
                generation_config=genai.types.GenerationConfig(max_output_tokens=3)
            )
            
            if test_response and test_response.text:
                model = test_model
                current_model_name = model_name
                record_model_usage(model_name)
                logger.info(f"✅ 成功切換到 {model_name}")
                return True
                
        except Exception as e:
            if "429" in str(e):
                # 標記為配額用完
                if model_name in quota_tracker:
                    quota_tracker[model_name]['used_today'] = quota_tracker[model_name]['daily_limit']
            continue
    
    logger.error("❌ 沒有可用的備案模型")
    return False

def get_quota_status():
    """取得配額狀態報告"""
    reset_daily_quota_if_needed()
    
    status = {
        'current_model': current_model_name,
        'models': {},
        'recommendations': []
    }
    
    for model_name, tracker in quota_tracker.items():
        used_pct = (tracker['used_today'] / tracker['daily_limit']) * 100 if tracker['daily_limit'] > 0 else 0
        status['models'][model_name] = {
            'used': tracker['used_today'],
            'limit': tracker['daily_limit'],
            'available': tracker['daily_limit'] - tracker['used_today'],
            'usage_percent': round(used_pct, 1),
            'status': '可用' if used_pct < 100 else '已用完'
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

# 兼容性：保持原有函數名稱
def generate_ai_response(student_id, query, conversation_context="", student_context="", group_id=None):
    """原有函數的兼容性包裝"""
    return generate_ai_response_with_smart_fallback(student_id, query, conversation_context, student_context, group_id)
