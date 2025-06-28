# teaching_analytics.py - EMI智能教學助理系統後端核心
# 修改日期：2025年6月28日
# 作者：後端核心開發團隊
# 功能：AI分析引擎、快取系統、錯誤處理機制

import os
import time
import logging
import datetime
from datetime import timedelta
from typing import Dict, Any, Optional, List
import json
import traceback

# 第三方套件
import google.generativeai as genai
from models import Student, Message, Analysis, db

# =================== 日誌配置 ===================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teaching_analytics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =================== API 配置 ===================

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY 環境變數未設定，AI功能將無法使用")

# AI模型配置
ANALYTICS_MODELS = [
    'gemini-2.0-flash-exp',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-pro'
]

# 當前使用的模型
current_analytics_model = None
analytics_model_name = ANALYTICS_MODELS[0]  # 預設使用最新模型
model_switch_count = 0

# =================== 快取系統實作 ===================

# 全域快取字典
analysis_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = 1800  # 30分鐘（1800秒）

def get_cached_analysis(cache_key: str) -> Optional[Dict[str, Any]]:
    """檢查並返回快取結果
    
    Args:
        cache_key (str): 快取鍵值
        
    Returns:
        Optional[Dict[str, Any]]: 快取結果或None
    """
    try:
        if cache_key in analysis_cache:
            cache_data = analysis_cache[cache_key]
            current_time = time.time()
            
            # 檢查是否過期
            if current_time < cache_data['expires_at']:
                logger.info(f"📋 快取命中: {cache_key}")
                return cache_data['result']
            else:
                # 過期則刪除
                del analysis_cache[cache_key]
                logger.info(f"🗑️ 清理過期快取: {cache_key}")
        
        return None
    except Exception as e:
        logger.error(f"獲取快取時發生錯誤: {e}")
        return None

def cache_analysis_result(cache_key: str, result: Dict[str, Any]) -> None:
    """將分析結果存入快取
    
    Args:
        cache_key (str): 快取鍵值
        result (Dict[str, Any]): 要快取的結果
    """
    try:
        current_time = time.time()
        analysis_cache[cache_key] = {
            'result': result,
            'timestamp': current_time,
            'expires_at': current_time + CACHE_DURATION
        }
        logger.info(f"💾 快取儲存: {cache_key} (有效期: {CACHE_DURATION/60:.1f}分鐘)")
    except Exception as e:
        logger.error(f"儲存快取時發生錯誤: {e}")

def clear_expired_cache() -> None:
    """清理所有過期的快取項目"""
    try:
        current_time = time.time()
        expired_keys = [
            key for key, data in analysis_cache.items() 
            if current_time >= data['expires_at']
        ]
        
        for key in expired_keys:
            del analysis_cache[key]
        
        if expired_keys:
            logger.info(f"🧹 清理了 {len(expired_keys)} 個過期快取項目")
    except Exception as e:
        logger.error(f"清理過期快取時發生錯誤: {e}")

def get_cached_or_generate(cache_key: str, generator_func, *args, **kwargs) -> Dict[str, Any]:
    """統一的快取獲取或生成函數
    
    Args:
        cache_key (str): 快取鍵值
        generator_func: 生成函數
        *args: 生成函數的位置參數
        **kwargs: 生成函數的關鍵字參數
        
    Returns:
        Dict[str, Any]: 分析結果
    """
    try:
        # 清理過期快取
        clear_expired_cache()
        
        # 檢查快取
        cached = get_cached_analysis(cache_key)
        if cached:
            return cached
        
        # 生成新結果
        logger.info(f"🔄 生成新分析: {cache_key}")
        start_time = time.time()
        
        result = generator_func(*args, **kwargs)
        
        generation_time = time.time() - start_time
        logger.info(f"⏱️ 分析生成時間: {generation_time:.2f}秒")
        
        if result and isinstance(result, dict) and 'error' not in result:
            # 添加生成時間資訊
            result['generation_time'] = generation_time
            result['cached'] = False
            
            cache_analysis_result(cache_key, result)
            return result
        else:
            logger.warning(f"生成結果異常: {result}")
            return {'error': '分析生成失敗', 'status': 'error'}
            
    except Exception as e:
        logger.error(f"生成分析時發生錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {'error': str(e), 'status': 'error'}

def get_cache_statistics() -> Dict[str, Any]:
    """獲取快取統計資訊
    
    Returns:
        Dict[str, Any]: 快取統計資訊
    """
    try:
        current_time = time.time()
        total_items = len(analysis_cache)
        active_items = 0
        expired_items = 0
        
        for data in analysis_cache.values():
            if current_time < data['expires_at']:
                active_items += 1
            else:
                expired_items += 1
        
        return {
            'total_items': total_items,
            'active_items': active_items,
            'expired_items': expired_items,
            'cache_duration_minutes': CACHE_DURATION / 60,
            'memory_efficiency': f"{(active_items/max(total_items, 1)*100):.1f}%"
        }
    except Exception as e:
        logger.error(f"獲取快取統計時發生錯誤: {e}")
        return {'error': str(e)}

# 檔案第一段結束 - 接下來是錯誤處理系統

# teaching_analytics.py - 第二段：錯誤處理系統
# 接續第一段：快取系統之後

# =================== 錯誤處理系統 ===================

def safe_ai_analysis(analysis_func, fallback_func, *args, **kwargs) -> Dict[str, Any]:
    """安全的AI分析執行包裝函數
    
    這個函數提供了一個安全的包裝器，當AI分析失敗時會自動切換到備用方案
    
    Args:
        analysis_func: 主要的AI分析函數
        fallback_func: 備用分析函數
        *args: 傳遞給函數的位置參數
        **kwargs: 傳遞給函數的關鍵字參數
        
    Returns:
        Dict[str, Any]: 分析結果
    """
    try:
        logger.info("🤖 嘗試AI分析...")
        start_time = time.time()
        
        result = analysis_func(*args, **kwargs)
        
        analysis_time = time.time() - start_time
        logger.info(f"⏱️ AI分析完成，耗時: {analysis_time:.2f}秒")
        
        # 檢查結果有效性
        if result and isinstance(result, dict) and 'error' not in result:
            result['analysis_method'] = 'ai'
            result['analysis_time'] = analysis_time
            return result
        else:
            logger.warning(f"⚠️ AI分析返回異常結果: {result}")
            logger.info("🔄 切換到備用方案...")
            return fallback_func(*args, **kwargs)
            
    except Exception as e:
        logger.error(f"❌ AI分析錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        logger.info("🔄 切換到備用方案...")
        return fallback_func(*args, **kwargs)

def get_fallback_individual_summary(student_id: int) -> Dict[str, Any]:
    """AI失敗時的個人摘要備用方案
    
    當AI分析無法使用時，提供基於資料庫統計的基本摘要
    
    Args:
        student_id (int): 學生ID
        
    Returns:
        Dict[str, Any]: 備用摘要結果
    """
    try:
        logger.info(f"📊 生成學生 {student_id} 的備用摘要...")
        
        # 從資料庫獲取學生資料
        student = Student.get_by_id(student_id)
        if not student:
            return {
                'status': 'error',
                'summary': '⚠️ 找不到指定學生資料',
                'message': '學生不存在',
                'error': f'學生ID {student_id} 不存在'
            }
        
        # 獲取學生的所有訊息
        messages = list(Message.select().where(Message.student_id == student_id))
        
        # 統計分析
        question_count = len([m for m in messages if '?' in m.content or '?' in m.content])
        total_messages = len(messages)
        
        # 計算最後活動時間
        last_active = None
        if messages:
            last_active = max([m.timestamp for m in messages])
        
        # 計算學習天數
        if student.created_at and messages:
            first_message = min([m.timestamp for m in messages])
            learning_days = (datetime.datetime.now() - first_message).days + 1
        else:
            learning_days = 0
        
        # 生成參與度評估
        if total_messages >= 20:
            engagement_level = '活躍'
            engagement_emoji = '🔥'
        elif total_messages >= 10:
            engagement_level = '一般'
            engagement_emoji = '📈'
        elif total_messages >= 5:
            engagement_level = '較低'
            engagement_emoji = '📊'
        else:
            engagement_level = '初始'
            engagement_emoji = '🌱'
        
        # 計算提問率
        question_rate = (question_count / max(total_messages, 1)) * 100
        
        summary_text = f"""📊 {student.name} 學習概況 {engagement_emoji}

🎯 **基本統計**
• 總互動次數：{total_messages} 次
• 提問數量：{question_count} 個 ({question_rate:.1f}%)
• 學習天數：{learning_days} 天
• 參與狀態：{engagement_level}

📅 **活動記錄**
• 最近活動：{last_active.strftime('%Y-%m-%d %H:%M') if last_active else '無記錄'}
• 帳號建立：{student.created_at.strftime('%Y-%m-%d') if student.created_at else '未知'}

💡 **學習建議**
• {'建議增加課堂互動和提問' if total_messages < 10 else '保持良好的學習互動'}
• {'可以多問問題來加深理解' if question_rate < 20 else '提問習慣良好'}

⚠️ **系統提示**
AI詳細分析暫時無法使用，以上為基於資料庫的基本統計。
建議稍後重試AI分析功能以獲得更深入的洞察。"""

        return {
            'status': 'fallback',
            'summary': summary_text,
            'message': 'AI分析暫時無法使用，顯示基本統計資料',
            'analysis_method': 'fallback',
            'data': {
                'student_name': student.name,
                'total_messages': total_messages,
                'question_count': question_count,
                'question_rate': question_rate,
                'learning_days': learning_days,
                'engagement_level': engagement_level,
                'last_active': last_active.isoformat() if last_active else None,
                'created_at': student.created_at.isoformat() if student.created_at else None
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 備用摘要生成錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {
            'status': 'error',
            'summary': '⚠️ 無法生成學習摘要，請檢查資料連接。',
            'message': '系統暫時無法取得學生資料',
            'error': str(e),
            'analysis_method': 'error'
        }

def get_fallback_class_summary() -> Dict[str, Any]:
    """AI失敗時的全班摘要備用方案
    
    當AI分析無法使用時，提供基於資料庫統計的全班概況
    
    Returns:
        Dict[str, Any]: 備用全班摘要結果
    """
    try:
        logger.info("📊 生成全班備用摘要...")
        
        # 統計全班資料
        all_students = list(Student.select())
        all_messages = list(Message.select())
        
        total_students = len(all_students)
        total_messages = len(all_messages)
        total_questions = len([m for m in all_messages if '?' in m.content or '?' in m.content])
        
        # 計算活躍學生數（7天內有活動）
        week_ago = datetime.datetime.now() - timedelta(days=7)
        active_students = len([
            s for s in all_students 
            if s.last_active and s.last_active >= week_ago
        ])
        
        # 計算平均參與度
        avg_participation = sum([s.participation_rate for s in all_students]) / max(total_students, 1)
        avg_messages_per_student = total_messages / max(total_students, 1)
        avg_questions_per_student = total_questions / max(total_students, 1)
        
        # 生成班級評估
        if active_students / max(total_students, 1) >= 0.7:
            class_engagement = '高度活躍'
            engagement_emoji = '🔥'
        elif active_students / max(total_students, 1) >= 0.4:
            class_engagement = '中等活躍'
            engagement_emoji = '📈'
        else:
            class_engagement = '需要鼓勵'
            engagement_emoji = '💪'
        
        summary_text = f"""📊 全班學習概況 {engagement_emoji}

👥 **班級統計**
• 總學生數：{total_students} 人
• 活躍學生：{active_students} 人 ({(active_students/max(total_students, 1)*100):.1f}%)
• 班級狀態：{class_engagement}

💬 **互動統計**
• 總互動次數：{total_messages} 次  
• 總提問數：{total_questions} 個
• 平均參與度：{avg_participation:.1f}%

📈 **平均表現**
• 平均互動：{avg_messages_per_student:.1f} 次/人
• 平均提問：{avg_questions_per_student:.1f} 個/人
• 提問率：{(total_questions/max(total_messages, 1)*100):.1f}%

💡 **教學建議**
• {'建議增加課堂互動活動' if avg_participation < 50 else '保持目前的教學方式'}
• {'可以鼓勵學生多提問' if total_questions/max(total_messages, 1) < 0.2 else '學生提問積極度良好'}

⚠️ **系統提示**
AI詳細分析暫時無法使用，以上為基於資料庫的基本統計。"""

        return {
            'status': 'fallback',
            'summary': summary_text,
            'message': 'AI分析暫時無法使用，顯示基本統計資料',
            'analysis_method': 'fallback',
            'data': {
                'total_students': total_students,
                'active_students': active_students,
                'total_messages': total_messages,
                'total_questions': total_questions,
                'avg_participation': avg_participation,
                'avg_messages_per_student': avg_messages_per_student,
                'avg_questions_per_student': avg_questions_per_student,
                'class_engagement': class_engagement
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 備用全班摘要生成錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {
            'status': 'error',
            'summary': '⚠️ 無法生成全班摘要，請檢查資料連接。',
            'message': '系統暫時無法取得班級資料',
            'error': str(e),
            'analysis_method': 'error'
        }

def get_fallback_keywords() -> Dict[str, Any]:
    """AI失敗時的關鍵詞備用方案
    
    當AI關鍵詞分析無法使用時，提供預設關鍵詞
    
    Returns:
        Dict[str, Any]: 備用關鍵詞結果
    """
    try:
        # 嘗試從資料庫中提取一些簡單的關鍵詞
        messages = list(Message.select().limit(100))
        
        # 簡單的關鍵詞統計（基於常見教學詞彙）
        common_keywords = {
            '英文': 0, '英語': 0, 'English': 0,
            '問題': 0, 'question': 0, '提問': 0,
            '課程': 0, 'course': 0, '教學': 0,
            '學習': 0, 'learning': 0, 'study': 0,
            '作業': 0, 'homework': 0, '練習': 0
        }
        
        # 統計詞頻
        for message in messages:
            content = message.content.lower()
            for keyword in common_keywords:
                if keyword.lower() in content:
                    common_keywords[keyword] += 1
        
        # 選取最常見的5個關鍵詞
        sorted_keywords = sorted(common_keywords.items(), key=lambda x: x[1], reverse=True)
        top_keywords = [kw[0] for kw in sorted_keywords[:5] if kw[1] > 0]
        
        # 如果沒有找到關鍵詞，使用預設值
        if not top_keywords:
            top_keywords = ['課程內容', '學習問題', '課堂互動', '英語教學', '學生參與']
        
        return {
            'status': 'fallback',
            'keywords': top_keywords,
            'message': 'AI關鍵詞分析暫時無法使用，顯示基於詞頻的關鍵詞',
            'analysis_method': 'fallback',
            'data': {
                'keyword_counts': dict(sorted_keywords[:10]),
                'total_messages_analyzed': len(messages)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 備用關鍵詞生成錯誤: {e}")
        return {
            'status': 'fallback',
            'keywords': ['課程內容', '學習問題', '課堂互動', '英語教學', '學生參與'],
            'message': 'AI關鍵詞分析暫時無法使用，顯示預設關鍵詞',
            'error': str(e),
            'analysis_method': 'error'
        }

# 檔案第二段結束 - 接下來是AI服務初始化和核心函數

# teaching_analytics.py - 第三段：AI服務初始化和核心函數
# 接續第二段：錯誤處理系統之後

# =================== AI服務初始化 ===================

def initialize_ai_service() -> bool:
    """初始化AI服務
    
    Returns:
        bool: 初始化是否成功
    """
    global current_analytics_model, analytics_model_name
    
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY 未設定，無法初始化AI服務")
        return False
    
    try:
        logger.info("🚀 初始化AI服務...")
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 嘗試初始化第一個可用的模型
        for model_name in ANALYTICS_MODELS:
            try:
                logger.info(f"🧪 測試模型: {model_name}")
                test_model = genai.GenerativeModel(model_name)
                
                # 簡單測試
                response = test_model.generate_content("測試AI服務")
                if response and response.text:
                    current_analytics_model = test_model
                    analytics_model_name = model_name
                    logger.info(f"✅ AI服務初始化成功，使用模型: {model_name}")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ 模型 {model_name} 無法使用: {e}")
                continue
        
        logger.error("❌ 所有模型都無法使用")
        return False
        
    except Exception as e:
        logger.error(f"❌ AI服務初始化失敗: {e}")
        return False

def call_ai_service(prompt: str, max_retries: int = 3) -> str:
    """呼叫AI服務進行分析
    
    Args:
        prompt (str): 分析提示
        max_retries (int): 最大重試次數
        
    Returns:
        str: AI回應文字
    """
    global current_analytics_model, analytics_model_name
    
    if not current_analytics_model:
        if not initialize_ai_service():
            raise Exception("AI服務初始化失敗")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🤖 呼叫AI服務 (嘗試 {attempt + 1}/{max_retries})")
            response = current_analytics_model.generate_content(prompt)
            
            if response and response.text:
                logger.info("✅ AI回應成功")
                return response.text.strip()
            else:
                raise Exception("AI回應為空")
                
        except Exception as e:
            logger.warning(f"⚠️ AI服務呼叫失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            
            if attempt == max_retries - 1:
                # 最後一次嘗試，嘗試切換模型
                if switch_to_next_model():
                    logger.info("🔄 已切換到下一個模型，再次嘗試...")
                    continue
                else:
                    raise Exception(f"AI服務呼叫失敗，已嘗試 {max_retries} 次")
            
            time.sleep(1)  # 稍作等待再重試
    
    raise Exception("AI服務呼叫超過最大重試次數")

def switch_to_next_model() -> bool:
    """切換到下一個可用的AI模型
    
    Returns:
        bool: 切換是否成功
    """
    global current_analytics_model, analytics_model_name, model_switch_count
    
    current_index = ANALYTICS_MODELS.index(analytics_model_name) if analytics_model_name in ANALYTICS_MODELS else 0
    
    # 嘗試下一個模型
    for i in range(1, len(ANALYTICS_MODELS)):
        next_index = (current_index + i) % len(ANALYTICS_MODELS)
        next_model_name = ANALYTICS_MODELS[next_index]
        
        try:
            logger.info(f"🔄 切換到模型: {next_model_name}")
            genai.configure(api_key=GEMINI_API_KEY)
            new_model = genai.GenerativeModel(next_model_name)
            
            # 測試新模型
            test_response = new_model.generate_content("測試")
            if test_response and test_response.text:
                current_analytics_model = new_model
                analytics_model_name = next_model_name
                model_switch_count += 1
                logger.info(f"✅ 模型切換成功: {next_model_name}")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ 模型 {next_model_name} 切換失敗: {e}")
            continue
    
    logger.error("❌ 所有模型都無法使用")
    return False

# =================== AI分析核心函數 ===================

def generate_individual_summary(student_id: int) -> Dict[str, Any]:
    """個人學習摘要生成（含快取和錯誤處理）
    
    Args:
        student_id (int): 學生ID
        
    Returns:
        Dict[str, Any]: 個人摘要分析結果
    """
    cache_key = f"individual_summary_{student_id}"
    
    def _generate_summary():
        """內部摘要生成函數"""
        logger.info(f"🎯 生成學生 {student_id} 的個人摘要...")
        
        # 從資料庫獲取學生的所有訊息
        student = Student.get_by_id(student_id)
        if not student:
            return {'error': '找不到指定學生'}
        
        messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp))
        
        if not messages:
            return {'error': '該學生沒有訊息記錄'}
        
        # 準備AI分析的資料
        message_content = "\n".join([
            f"[{m.timestamp.strftime('%Y-%m-%d %H:%M')}] {m.content[:200]}"  # 限制每則訊息長度
            for m in messages[-50:]  # 只取最近50則訊息
        ])
        
        # 統計基本資料
        question_count = len([m for m in messages if '?' in m.content])
        total_messages = len(messages)
        learning_days = (datetime.datetime.now() - messages[0].timestamp).days + 1 if messages else 0
        
        # 構建AI分析提示
        prompt = f"""作為EMI智能教學助理，請分析以下學生的學習記錄並生成個人學習摘要：

**學生基本資訊：**
- 姓名：{student.name}
- 參與度：{student.participation_rate}%
- 學習天數：{learning_days} 天
- 總訊息數：{total_messages} 則
- 提問次數：{question_count} 個

**最近學習記錄：**
{message_content}

請以專業且友善的語調，用繁體中文生成結構化的個人學習摘要，包含以下部分：

📊 **學習參與度分析**
[分析學生的課堂參與情況、互動頻率和學習積極性]

📚 **主要學習主題**
[識別學生最常討論的學習主題和關注重點]

❓ **提問特點與學習風格**
[分析學生的提問模式、學習偏好和認知特點]

💡 **個人化學習建議**
[提供具體、可行的學習改進建議和發展方向]

📈 **學習進展評估**
[評估學習成效和未來發展潜力]

請確保摘要內容具體、有建設性，並符合EMI教學環境的特點。"""

        # 呼叫AI服務
        ai_response = call_ai_service(prompt)
        
        return {
            'status': 'success',
            'summary': ai_response,
            'student_name': student.name,
            'message_count': total_messages,
            'question_count': question_count,
            'learning_days': learning_days,
            'analysis_model': analytics_model_name,
            'generated_at': datetime.datetime.now().isoformat()
        }
    
    # 使用快取系統和錯誤處理
    return get_cached_or_generate(
        cache_key, 
        lambda: safe_ai_analysis(_generate_summary, get_fallback_individual_summary, student_id)
    )

def generate_class_summary() -> Dict[str, Any]:
    """全班學習摘要生成（含快取和錯誤處理）
    
    Returns:
        Dict[str, Any]: 全班摘要分析結果
    """
    cache_key = "class_summary"
    
    def _generate_summary():
        """內部全班摘要生成函數"""
        logger.info("🏫 生成全班學習摘要...")
        
        # 獲取所有學生和訊息
        all_students = list(Student.select())
        all_messages = list(Message.select().order_by(Message.timestamp.desc()))
        
        if not all_students or not all_messages:
            return {'error': '找不到班級資料'}
        
        # 統計班級基本資料
        total_students = len(all_students)
        total_messages = len(all_messages)
        total_questions = len([m for m in all_messages if '?' in m.content])
        
        # 計算活躍學生
        week_ago = datetime.datetime.now() - timedelta(days=7)
        active_students = len([s for s in all_students if s.last_active and s.last_active >= week_ago])
        
        # 準備AI分析資料（最近100則訊息）
        recent_messages = all_messages[:100]
        message_content = "\n".join([
            f"[學生{m.student_id}] {m.content[:150]}" 
            for m in recent_messages
        ])
        
        # 學生參與度分布
        high_participation = len([s for s in all_students if s.participation_rate >= 70])
        medium_participation = len([s for s in all_students if 40 <= s.participation_rate < 70])
        low_participation = len([s for s in all_students if s.participation_rate < 40])
        
        prompt = f"""作為EMI智能教學助理，請分析以下全班學習記錄並生成班級學習摘要：

**班級基本概況：**
- 總學生數：{total_students} 人
- 活躍學生：{active_students} 人
- 總訊息數：{total_messages} 則
- 總提問數：{total_questions} 個
- 平均參與度：{sum([s.participation_rate for s in all_students]) / max(total_students, 1):.1f}%

**參與度分布：**
- 高參與度 (≥70%)：{high_participation} 人
- 中參與度 (40-69%)：{medium_participation} 人  
- 低參與度 (<40%)：{low_participation} 人

**最近班級互動記錄：**
{message_content}

請用繁體中文生成結構化的班級學習摘要，包含以下部分：

📊 **整體學習趨勢分析**
[分析班級整體的學習表現、參與趨勢和發展方向]

📚 **熱門學習主題與重點**
[識別班級最常討論的學習主題和共同關注點]

👥 **班級參與狀況評估**
[評估學生參與度分布、互動品質和課堂氛圍]

🎯 **教學效果分析**
[分析當前教學方法的效果和學生回饋情況]

💡 **班級管理建議**
[提供具體的教學策略建議和班級管理改進方案]

📈 **發展潛力與挑戰**
[識別班級發展機會和需要關注的問題]

請確保建議具體可行，符合EMI教學環境的特點。"""

        # 呼叫AI服務
        ai_response = call_ai_service(prompt)
        
        return {
            'status': 'success',
            'summary': ai_response,
            'total_students': total_students,
            'total_messages': total_messages,
            'total_questions': total_questions,
            'active_students': active_students,
            'analysis_model': analytics_model_name,
            'generated_at': datetime.datetime.now().isoformat()
        }
    
    # 使用快取系統和錯誤處理
    return get_cached_or_generate(
        cache_key,
        lambda: safe_ai_analysis(_generate_summary, get_fallback_class_summary)
    )

def extract_learning_keywords() -> Dict[str, Any]:
    """提取學習關鍵詞（含快取和錯誤處理）
    
    Returns:
        Dict[str, Any]: 關鍵詞分析結果
    """
    cache_key = "learning_keywords"
    
    def _extract_keywords():
        """內部關鍵詞提取函數"""
        logger.info("🔍 提取學習關鍵詞...")
        
        # 獲取所有訊息內容
        all_messages = list(Message.select().order_by(Message.timestamp.desc()).limit(200))
        
        if not all_messages:
            return {'error': '找不到訊息資料'}
        
        # 合併訊息內容
        message_content = " ".join([m.content for m in all_messages])
        
        prompt = f"""作為EMI智能教學助理，請從以下學習記錄中提取最重要的學習關鍵詞：

**學習內容樣本：**
{message_content[:2000]}  # 限制長度避免超出限制

**分析要求：**
1. 提取5-8個最重要的學習關鍵詞
2. 關鍵詞要能代表主要學習主題和教學重點
3. 使用繁體中文
4. 每個關鍵詞不超過4個字
5. 優先選擇EMI教學相關的詞彙

**輸出格式：**
請只返回關鍵詞列表，用逗號分隔，例如：
英語學習,課堂互動,學習問題,教學內容,學生參與

不要包含任何其他說明文字。"""

        # 呼叫AI服務
        ai_response = call_ai_service(prompt)
        
        # 解析關鍵詞
        keywords = [kw.strip() for kw in ai_response.split(',') if kw.strip()]
        
        # 限制關鍵詞數量
        keywords = keywords[:8] if len(keywords) > 8 else keywords
        
        # 如果關鍵詞太少，添加一些預設關鍵詞
        if len(keywords) < 3:
            default_keywords = ['EMI教學', '英語學習', '課堂互動', '學習問題', '教學內容']
            keywords.extend(default_keywords)
            keywords = list(set(keywords))[:8]  # 去重並限制數量
        
        return {
            'status': 'success',
            'keywords': keywords,
            'analysis_model': analytics_model_name,
            'message_count': len(all_messages),
            'generated_at': datetime.datetime.now().isoformat()
        }
    
    # 使用快取系統和錯誤處理
    return get_cached_or_generate(
        cache_key,
        lambda: safe_ai_analysis(_extract_keywords, get_fallback_keywords)
    )

# 檔案第三段結束 - 接下來是TSV匯出功能

# teaching_analytics.py - 第四段：TSV匯出功能
# 接續第三段：AI分析核心函數之後

# =================== TSV匯出功能 ===================

def export_student_questions_tsv(student_id: int) -> Dict[str, Any]:
    """匯出個別學生的提問記錄為TSV格式
    
    Args:
        student_id (int): 學生ID
        
    Returns:
        Dict[str, Any]: TSV匯出結果
    """
    try:
        logger.info(f"📄 匯出學生 {student_id} 的提問記錄...")
        
        # 檢查學生是否存在
        student = Student.get_by_id(student_id)
        if not student:
            return {
                'error': '找不到指定學生',
                'status': 'error'
            }
        
        # 獲取該學生的所有包含問號的訊息
        question_messages = list(Message.select().where(
            (Message.student_id == student_id) & 
            ((Message.content.contains('?')) | (Message.content.contains('？')))
        ).order_by(Message.timestamp))
        
        if not question_messages:
            return {
                'error': '該學生沒有提問記錄',
                'status': 'no_data',
                'student_name': student.name
            }
        
        # 生成TSV內容
        tsv_lines = ['學生姓名\t提問內容\t提問時間\t訊息類型\t字數']
        
        for message in question_messages:
            # 格式化時間
            formatted_time = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # 清理內容中的製表符、換行符和回車符
            clean_content = message.content.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            clean_content = clean_content.strip()
            
            # 計算字數
            word_count = len(clean_content)
            
            # 判斷訊息類型
            message_type = getattr(message, 'message_type', '一般提問')
            
            # 添加到TSV
            tsv_lines.append(f'{student.name}\t{clean_content}\t{formatted_time}\t{message_type}\t{word_count}')
        
        tsv_content = '\n'.join(tsv_lines)
        
        # 生成檔案名稱
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'student_{student_id}_{student.name}_questions_{timestamp}.tsv'
        
        logger.info(f"✅ 成功匯出 {len(question_messages)} 個提問記錄")
        
        return {
            'status': 'success',
            'content': tsv_content,
            'student_name': student.name,
            'question_count': len(question_messages),
            'filename': filename,
            'generated_at': datetime.datetime.now().isoformat(),
            'file_size': len(tsv_content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"❌ 匯出學生提問TSV錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {
            'error': f'匯出失敗: {str(e)}',
            'status': 'error'
        }

def export_all_questions_tsv() -> Dict[str, Any]:
    """匯出所有學生的提問記錄為TSV格式
    
    Returns:
        Dict[str, Any]: TSV匯出結果
    """
    try:
        logger.info("📄 匯出所有學生的提問記錄...")
        
        # 獲取所有包含問號的訊息，並包含學生資訊
        question_messages = list(
            Message.select(Message, Student.name.alias('student_name'))
            .join(Student)
            .where((Message.content.contains('?')) | (Message.content.contains('？')))
            .order_by(Message.timestamp)
        )
        
        if not question_messages:
            return {
                'error': '沒有找到任何提問記錄',
                'status': 'no_data'
            }
        
        # 生成TSV內容
        tsv_lines = ['學生姓名\t學生ID\t提問內容\t提問時間\t訊息類型\t字數\t參與度']
        
        # 統計資料
        student_question_counts = {}
        
        for message in question_messages:
            # 格式化時間
            formatted_time = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # 清理內容
            clean_content = message.content.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            clean_content = clean_content.strip()
            
            # 計算字數
            word_count = len(clean_content)
            
            # 獲取學生資訊
            student = message.student
            student_name = student.name
            student_id = student.id
            participation_rate = student.participation_rate
            
            # 統計學生提問次數
            if student_id not in student_question_counts:
                student_question_counts[student_id] = 0
            student_question_counts[student_id] += 1
            
            # 判斷訊息類型
            message_type = getattr(message, 'message_type', '一般提問')
            
            # 添加到TSV
            tsv_lines.append(
                f'{student_name}\t{student_id}\t{clean_content}\t{formatted_time}\t{message_type}\t{word_count}\t{participation_rate}%'
            )
        
        tsv_content = '\n'.join(tsv_lines)
        
        # 生成統計摘要
        total_students_with_questions = len(student_question_counts)
        total_questions = len(question_messages)
        avg_questions_per_student = total_questions / max(total_students_with_questions, 1)
        
        # 找出最活躍的提問學生
        top_questioners = sorted(
            student_question_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # 生成檔案名稱
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'all_students_questions_{timestamp}.tsv'
        
        logger.info(f"✅ 成功匯出 {total_questions} 個提問記錄，涵蓋 {total_students_with_questions} 位學生")
        
        return {
            'status': 'success',
            'content': tsv_content,
            'total_questions': total_questions,
            'total_students_with_questions': total_students_with_questions,
            'avg_questions_per_student': round(avg_questions_per_student, 2),
            'top_questioners': top_questioners,
            'filename': filename,
            'generated_at': datetime.datetime.now().isoformat(),
            'file_size': len(tsv_content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"❌ 匯出所有提問TSV錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {
            'error': f'匯出失敗: {str(e)}',
            'status': 'error'
        }

def export_student_analytics_tsv(student_id: int) -> Dict[str, Any]:
    """匯出個別學生的完整分析資料為TSV格式
    
    Args:
        student_id (int): 學生ID
        
    Returns:
        Dict[str, Any]: TSV匯出結果
    """
    try:
        logger.info(f"📊 匯出學生 {student_id} 的完整分析資料...")
        
        # 檢查學生是否存在
        student = Student.get_by_id(student_id)
        if not student:
            return {
                'error': '找不到指定學生',
                'status': 'error'
            }
        
        # 獲取學生的所有訊息
        all_messages = list(Message.select().where(
            Message.student_id == student_id
        ).order_by(Message.timestamp))
        
        if not all_messages:
            return {
                'error': '該學生沒有訊息記錄',
                'status': 'no_data',
                'student_name': student.name
            }
        
        # 生成TSV內容
        tsv_lines = ['時間\t內容\t類型\t字數\t是否提問\t參與度分數']
        
        for message in all_messages:
            # 格式化時間
            formatted_time = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # 清理內容
            clean_content = message.content.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            clean_content = clean_content.strip()
            
            # 計算字數
            word_count = len(clean_content)
            
            # 判斷是否為提問
            is_question = '是' if ('?' in clean_content or '？' in clean_content) else '否'
            
            # 計算參與度分數（簡單評分）
            participation_score = min(10, max(1, word_count // 10))
            
            # 訊息類型
            message_type = getattr(message, 'message_type', '一般訊息')
            
            # 添加到TSV
            tsv_lines.append(
                f'{formatted_time}\t{clean_content}\t{message_type}\t{word_count}\t{is_question}\t{participation_score}'
            )
        
        tsv_content = '\n'.join(tsv_lines)
        
        # 生成統計摘要
        total_messages = len(all_messages)
        question_count = len([m for m in all_messages if '?' in m.content or '？' in m.content])
        avg_word_count = sum([len(m.content) for m in all_messages]) / max(total_messages, 1)
        
        # 生成檔案名稱
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'student_{student_id}_{student.name}_analytics_{timestamp}.tsv'
        
        logger.info(f"✅ 成功匯出學生完整分析資料，包含 {total_messages} 則訊息")
        
        return {
            'status': 'success',
            'content': tsv_content,
            'student_name': student.name,
            'total_messages': total_messages,
            'question_count': question_count,
            'avg_word_count': round(avg_word_count, 2),
            'filename': filename,
            'generated_at': datetime.datetime.now().isoformat(),
            'file_size': len(tsv_content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"❌ 匯出學生分析TSV錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {
            'error': f'匯出失敗: {str(e)}',
            'status': 'error'
        }

def export_class_analytics_tsv() -> Dict[str, Any]:
    """匯出全班分析資料為TSV格式
    
    Returns:
        Dict[str, Any]: TSV匯出結果
    """
    try:
        logger.info("📊 匯出全班分析資料...")
        
        # 獲取所有學生
        all_students = list(Student.select())
        
        if not all_students:
            return {
                'error': '沒有找到學生資料',
                'status': 'no_data'
            }
        
        # 生成TSV內容
        tsv_lines = ['學生ID\t學生姓名\t參與度\t訊息數\t提問數\t最後活動\t建立時間\t活躍天數\t平均字數']
        
        total_stats = {
            'total_messages': 0,
            'total_questions': 0,
            'total_participation': 0
        }
        
        for student in all_students:
            # 獲取學生的訊息統計
            student_messages = list(Message.select().where(Message.student_id == student.id))
            message_count = len(student_messages)
            question_count = len([m for m in student_messages if '?' in m.content or '？' in m.content])
            
            # 計算平均字數
            avg_word_count = 0
            if student_messages:
                total_words = sum([len(m.content) for m in student_messages])
                avg_word_count = total_words / message_count
            
            # 格式化時間
            last_active = student.last_active.strftime('%Y-%m-%d %H:%M:%S') if student.last_active else '未知'
            created_at = student.created_at.strftime('%Y-%m-%d') if student.created_at else '未知'
            
            # 計算活躍天數
            active_days = student.active_days if hasattr(student, 'active_days') else 0
            
            # 更新總統計
            total_stats['total_messages'] += message_count
            total_stats['total_questions'] += question_count
            total_stats['total_participation'] += student.participation_rate
            
            # 添加到TSV
            tsv_lines.append(
                f'{student.id}\t{student.name}\t{student.participation_rate}%\t{message_count}\t{question_count}\t{last_active}\t{created_at}\t{active_days}\t{avg_word_count:.1f}'
            )
        
        tsv_content = '\n'.join(tsv_lines)
        
        # 計算班級平均值
        total_students = len(all_students)
        avg_participation = total_stats['total_participation'] / max(total_students, 1)
        avg_messages_per_student = total_stats['total_messages'] / max(total_students, 1)
        avg_questions_per_student = total_stats['total_questions'] / max(total_students, 1)
        
        # 生成檔案名稱
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'class_analytics_{timestamp}.tsv'
        
        logger.info(f"✅ 成功匯出全班分析資料，包含 {total_students} 位學生")
        
        return {
            'status': 'success',
            'content': tsv_content,
            'total_students': total_students,
            'total_messages': total_stats['total_messages'],
            'total_questions': total_stats['total_questions'],
            'avg_participation': round(avg_participation, 2),
            'avg_messages_per_student': round(avg_messages_per_student, 2),
            'avg_questions_per_student': round(avg_questions_per_student, 2),
            'filename': filename,
            'generated_at': datetime.datetime.now().isoformat(),
            'file_size': len(tsv_content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"❌ 匯出全班分析TSV錯誤: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return {
            'error': f'匯出失敗: {str(e)}',
            'status': 'error'
        }

# 檔案第四段結束 - 接下來是系統管理和初始化函數

# teaching_analytics.py - 第五段：系統管理和初始化函數
# 接續第四段：TSV匯出功能之後

# =================== 系統管理函數 ===================

def get_system_status() -> Dict[str, Any]:
    """獲取系統狀態資訊
    
    Returns:
        Dict[str, Any]: 系統狀態資訊
    """
    try:
        # 檢查AI服務狀態
        ai_status = 'available' if current_analytics_model else 'unavailable'
        
        # 檢查資料庫連接
        try:
            total_students = Student.select().count()
            total_messages = Message.select().count()
            db_status = 'connected'
        except Exception:
            total_students = 0
            total_messages = 0
            db_status = 'error'
        
        # 獲取快取統計
        cache_stats = get_cache_statistics()
        
        # 計算系統負載
        system_load = 'low'
        if cache_stats.get('active_items', 0) > 50:
            system_load = 'high'
        elif cache_stats.get('active_items', 0) > 20:
            system_load = 'medium'
        
        return {
            'status': 'operational',
            'ai_service': {
                'status': ai_status,
                'current_model': analytics_model_name,
                'model_switches': model_switch_count
            },
            'database': {
                'status': db_status,
                'total_students': total_students,
                'total_messages': total_messages
            },
            'cache': cache_stats,
            'system_load': system_load,
            'uptime_info': {
                'cache_duration_minutes': CACHE_DURATION / 60,
                'available_models': len(ANALYTICS_MODELS)
            },
            'last_check': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 獲取系統狀態錯誤: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'last_check': datetime.datetime.now().isoformat()
        }

def perform_system_health_check() -> Dict[str, Any]:
    """執行系統健康檢查
    
    Returns:
        Dict[str, Any]: 健康檢查結果
    """
    try:
        logger.info("🏥 執行系統健康檢查...")
        
        health_results = {
            'overall_status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # 1. AI服務檢查
        try:
            if current_analytics_model:
                test_response = call_ai_service("健康檢查測試")
                if test_response:
                    health_results['checks']['ai_service'] = 'pass'
                else:
                    health_results['checks']['ai_service'] = 'fail'
                    health_results['errors'].append('AI服務回應異常')
            else:
                health_results['checks']['ai_service'] = 'fail'
                health_results['errors'].append('AI服務未初始化')
        except Exception as e:
            health_results['checks']['ai_service'] = 'fail'
            health_results['errors'].append(f'AI服務檢查失敗: {str(e)}')
        
        # 2. 資料庫連接檢查
        try:
            db.execute_sql("SELECT 1")
            student_count = Student.select().count()
            message_count = Message.select().count()
            
            health_results['checks']['database'] = 'pass'
            health_results['checks']['data_availability'] = 'pass' if student_count > 0 and message_count > 0 else 'warning'
            
            if student_count == 0:
                health_results['warnings'].append('沒有學生資料')
            if message_count == 0:
                health_results['warnings'].append('沒有訊息資料')
                
        except Exception as e:
            health_results['checks']['database'] = 'fail'
            health_results['errors'].append(f'資料庫連接失敗: {str(e)}')
        
        # 3. 快取系統檢查
        try:
            cache_stats = get_cache_statistics()
            if 'error' in cache_stats:
                health_results['checks']['cache_system'] = 'fail'
                health_results['errors'].append('快取系統異常')
            else:
                health_results['checks']['cache_system'] = 'pass'
                
                # 檢查快取效率
                if cache_stats.get('expired_items', 0) > cache_stats.get('active_items', 0):
                    health_results['warnings'].append('快取過期項目過多，建議清理')
                    health_results['recommendations'].append('執行快取清理')
                    
        except Exception as e:
            health_results['checks']['cache_system'] = 'fail'
            health_results['errors'].append(f'快取系統檢查失敗: {str(e)}')
        
        # 4. API金鑰檢查
        if not GEMINI_API_KEY:
            health_results['checks']['api_key'] = 'fail'
            health_results['errors'].append('GEMINI_API_KEY 未設定')
        else:
            health_results['checks']['api_key'] = 'pass'
        
        # 5. 模型切換頻率檢查
        if model_switch_count > 10:
            health_results['warnings'].append(f'模型切換過於頻繁 ({model_switch_count} 次)')
            health_results['recommendations'].append('檢查網路連接和API配額')
        
        # 決定整體狀態
        if health_results['errors']:
            health_results['overall_status'] = 'unhealthy'
        elif health_results['warnings']:
            health_results['overall_status'] = 'warning'
        else:
            health_results['overall_status'] = 'healthy'
        
        # 添加建議
        if health_results['overall_status'] == 'healthy':
            health_results['recommendations'].append('系統運作正常')
        
        health_results['check_time'] = datetime.datetime.now().isoformat()
        
        logger.info(f"🏥 健康檢查完成，狀態: {health_results['overall_status']}")
        
        return health_results
        
    except Exception as e:
        logger.error(f"❌ 系統健康檢查錯誤: {e}")
        return {
            'overall_status': 'error',
            'error': str(e),
            'check_time': datetime.datetime.now().isoformat()
        }

def clear_all_cache() -> Dict[str, Any]:
    """清除所有快取
    
    Returns:
        Dict[str, Any]: 清除結果
    """
    try:
        global analysis_cache
        
        cache_count = len(analysis_cache)
        analysis_cache.clear()
        
        logger.info(f"🧹 已清除 {cache_count} 個快取項目")
        
        return {
            'status': 'success',
            'cleared_items': cache_count,
            'message': f'成功清除 {cache_count} 個快取項目',
            'cleared_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 清除快取錯誤: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

def reset_system() -> Dict[str, Any]:
    """重置系統（清除快取並重新初始化AI服務）
    
    Returns:
        Dict[str, Any]: 重置結果
    """
    try:
        logger.info("🔄 重置系統...")
        
        # 清除快取
        cache_result = clear_all_cache()
        
        # 重新初始化AI服務
        ai_init_success = initialize_ai_service()
        
        # 執行健康檢查
        health_check = perform_system_health_check()
        
        reset_success = ai_init_success and health_check['overall_status'] != 'error'
        
        return {
            'status': 'success' if reset_success else 'partial',
            'cache_cleared': cache_result['status'] == 'success',
            'ai_reinitialized': ai_init_success,
            'health_status': health_check['overall_status'],
            'message': '系統重置完成' if reset_success else '系統重置部分完成，請檢查錯誤',
            'reset_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 系統重置錯誤: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'reset_at': datetime.datetime.now().isoformat()
        }

def get_analytics_statistics() -> Dict[str, Any]:
    """獲取分析統計資訊
    
    Returns:
        Dict[str, Any]: 分析統計資訊
    """
    try:
        logger.info("📊 計算分析統計資訊...")
        
        # 資料庫統計
        total_students = Student.select().count()
        total_messages = Message.select().count()
        
        # 活躍度統計
        week_ago = datetime.datetime.now() - timedelta(days=7)
        active_students = Student.select().where(Student.last_active >= week_ago).count()
        
        # 提問統計
        question_messages = Message.select().where(
            (Message.content.contains('?')) | (Message.content.contains('？'))
        ).count()
        
        # 快取統計
        cache_stats = get_cache_statistics()
        
        # 計算分析覆蓋率
        students_with_messages = Student.select().join(Message).distinct().count()
        coverage_rate = (students_with_messages / max(total_students, 1)) * 100
        
        # 計算平均值
        avg_messages_per_student = total_messages / max(total_students, 1)
        avg_questions_per_student = question_messages / max(total_students, 1)
        
        # 系統效能指標
        if cache_stats.get('active_items', 0) > 0:
            cache_hit_potential = 'high'
        elif cache_stats.get('active_items', 0) > 0:
            cache_hit_potential = 'medium'
        else:
            cache_hit_potential = 'low'
        
        return {
            'status': 'success',
            'data_statistics': {
                'total_students': total_students,
                'total_messages': total_messages,
                'active_students': active_students,
                'question_messages': question_messages,
                'coverage_rate': round(coverage_rate, 2),
                'avg_messages_per_student': round(avg_messages_per_student, 2),
                'avg_questions_per_student': round(avg_questions_per_student, 2)
            },
            'system_statistics': {
                'current_model': analytics_model_name,
                'model_switches': model_switch_count,
                'cache_items': cache_stats.get('active_items', 0),
                'cache_hit_potential': cache_hit_potential
            },
            'performance_indicators': {
                'data_richness': 'high' if avg_messages_per_student >= 10 else 'medium' if avg_messages_per_student >= 5 else 'low',
                'question_engagement': 'high' if (question_messages / max(total_messages, 1)) >= 0.2 else 'medium' if (question_messages / max(total_messages, 1)) >= 0.1 else 'low',
                'system_stability': 'stable' if model_switch_count < 5 else 'moderate' if model_switch_count < 15 else 'unstable'
            },
            'generated_at': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 獲取分析統計錯誤: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'generated_at': datetime.datetime.now().isoformat()
        }

# =================== 系統初始化 ===================

def initialize_system() -> Dict[str, Any]:
    """初始化整個分析系統
    
    Returns:
        Dict[str, Any]: 初始化結果
    """
    try:
        logger.info("🚀 初始化 EMI 教學分析系統...")
        
        initialization_results = {
            'status': 'success',
            'components': {},
            'warnings': [],
            'errors': []
        }
        
        # 1. 檢查環境配置
        if not GEMINI_API_KEY:
            initialization_results['warnings'].append('GEMINI_API_KEY 未設定，AI功能將無法使用')
            initialization_results['components']['api_key'] = 'missing'
        else:
            initialization_results['components']['api_key'] = 'configured'
        
        # 2. 初始化AI服務
        if GEMINI_API_KEY:
            ai_init = initialize_ai_service()
            initialization_results['components']['ai_service'] = 'success' if ai_init else 'failed'
            if not ai_init:
                initialization_results['errors'].append('AI服務初始化失敗')
        else:
            initialization_results['components']['ai_service'] = 'skipped'
        
        # 3. 檢查資料庫連接
        try:
            db.connect()
            initialization_results['components']['database'] = 'connected'
            
            # 檢查資料可用性
            student_count = Student.select().count()
            message_count = Message.select().count()
            
            if student_count == 0:
                initialization_results['warnings'].append('沒有學生資料')
            if message_count == 0:
                initialization_results['warnings'].append('沒有訊息資料')
                
        except Exception as e:
            initialization_results['components']['database'] = 'failed'
            initialization_results['errors'].append(f'資料庫連接失敗: {str(e)}')
        
        # 4. 初始化快取系統
        try:
            clear_expired_cache()  # 清理可能存在的過期快取
            initialization_results['components']['cache_system'] = 'initialized'
        except Exception as e:
            initialization_results['components']['cache_system'] = 'failed'
            initialization_results['errors'].append(f'快取系統初始化失敗: {str(e)}')
        
        # 5. 執行健康檢查
        health_check = perform_system_health_check()
        initialization_results['health_status'] = health_check['overall_status']
        
        # 決定整體初始化狀態
        if initialization_results['errors']:
            initialization_results['status'] = 'failed'
        elif initialization_results['warnings']:
            initialization_results['status'] = 'partial'
        else:
            initialization_results['status'] = 'success'
        
        # 系統資訊
        initialization_results['system_info'] = {
            'version': '2025.06.28',
            'available_models': ANALYTICS_MODELS,
            'current_model': analytics_model_name,
            'cache_duration_minutes': CACHE_DURATION / 60
        }
        
        initialization_results['initialized_at'] = datetime.datetime.now().isoformat()
        
        status_message = {
            'success': '✅ 系統初始化完成',
            'partial': '⚠️ 系統部分初始化完成',
            'failed': '❌ 系統初始化失敗'
        }
        
        logger.info(status_message[initialization_results['status']])
        
        return initialization_results
        
    except Exception as e:
        logger.error(f"❌ 系統初始化錯誤: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'initialized_at': datetime.datetime.now().isoformat()
        }

# =================== 匯出的主要函數列表 ===================

# 快取管理函數
__cache_functions__ = [
    'get_cached_analysis',
    'cache_analysis_result', 
    'clear_expired_cache',
    'get_cached_or_generate',
    'get_cache_statistics',
    'clear_all_cache'
]

# AI分析函數
__analysis_functions__ = [
    'generate_individual_summary',
    'generate_class_summary',
    'extract_learning_keywords'
]

# TSV匯出函數
__export_functions__ = [
    'export_student_questions_tsv',
    'export_all_questions_tsv',
    'export_student_analytics_tsv',
    'export_class_analytics_tsv'
]

# 系統管理函數
__system_functions__ = [
    'get_system_status',
    'perform_system_health_check',
    'reset_system',
    'get_analytics_statistics',
    'initialize_system'
]

# 錯誤處理函數
__error_handling_functions__ = [
    'safe_ai_analysis',
    'get_fallback_individual_summary',
    'get_fallback_class_summary',
    'get_fallback_keywords'
]

# AI服務函數
__ai_service_functions__ = [
    'initialize_ai_service',
    'call_ai_service',
    'switch_to_next_model'
]

# 檔案第五段結束 - 接下來是最終的匯出和初始化

# teaching_analytics.py - 第六段：匯出和系統啟動（最終段）
# 接續第五段：系統管理和初始化函數之後

# =================== 統一匯出列表 ===================

__all__ = [
    # === 核心分析函數 ===
    'generate_individual_summary',
    'generate_class_summary', 
    'extract_learning_keywords',
    
    # === TSV匯出功能 ===
    'export_student_questions_tsv',
    'export_all_questions_tsv',
    'export_student_analytics_tsv',
    'export_class_analytics_tsv',
    
    # === 快取系統 ===
    'get_cached_analysis',
    'cache_analysis_result',
    'clear_expired_cache',
    'get_cached_or_generate',
    'get_cache_statistics',
    'clear_all_cache',
    
    # === 錯誤處理 ===
    'safe_ai_analysis',
    'get_fallback_individual_summary',
    'get_fallback_class_summary',
    'get_fallback_keywords',
    
    # === AI服務管理 ===
    'initialize_ai_service',
    'call_ai_service',
    'switch_to_next_model',
    
    # === 系統管理 ===
    'get_system_status',
    'perform_system_health_check',
    'reset_system',
    'get_analytics_statistics',
    'initialize_system',
    
    # === 系統變數（唯讀） ===
    'analytics_model_name',
    'model_switch_count',
    'CACHE_DURATION',
    'ANALYTICS_MODELS'
]

# =================== 相容性函數（與現有程式碼整合） ===================

def get_analytics_status() -> Dict[str, Any]:
    """獲取分析系統狀態（相容性函數）
    
    Returns:
        Dict[str, Any]: 系統狀態
    """
    return get_system_status()

def cleanup_old_cache() -> Dict[str, Any]:
    """清理舊快取（相容性函數）
    
    Returns:
        Dict[str, Any]: 清理結果
    """
    clear_expired_cache()
    return get_cache_statistics()

# =================== 系統版本資訊 ===================

SYSTEM_VERSION_INFO = {
    'name': 'EMI Teaching Analytics System - Backend Core',
    'version': '2025.06.28',
    'description': 'EMI智能教學助理系統後端核心，提供AI分析、快取、錯誤處理和TSV匯出功能',
    'features': [
        '智能快取系統（30分鐘有效期）',
        '完善錯誤處理機制',
        'AI分析引擎（個人和全班摘要）',
        'TSV檔案匯出功能',
        '多模型支援和自動切換',
        '系統健康監控',
        '效能統計和優化建議'
    ],
    'supported_models': ANALYTICS_MODELS,
    'cache_duration_minutes': CACHE_DURATION / 60,
    'last_updated': '2025-06-28',
    'author': 'EMI Backend Core Development Team',
    'performance_targets': {
        'ai_analysis_first_load': '≤ 10秒',
        'cache_hit_load': '≤ 1秒', 
        'api_error_rate': '< 1%',
        'system_stability': '99%+'
    }
}

# =================== 效能基準測試函數 ===================

def benchmark_performance() -> Dict[str, Any]:
    """效能基準測試
    
    Returns:
        Dict[str, Any]: 效能測試結果
    """
    try:
        logger.info("⏱️ 開始效能基準測試...")
        
        benchmark_results = {
            'test_status': 'completed',
            'test_time': datetime.datetime.now().isoformat(),
            'results': {},
            'performance_grade': 'unknown'
        }
        
        # 測試1：AI分析效能（如果有學生資料）
        try:
            students = list(Student.select().limit(1))
            if students:
                student_id = students[0].id
                
                # 清除可能的快取
                cache_key = f"individual_summary_{student_id}"
                if cache_key in analysis_cache:
                    del analysis_cache[cache_key]
                
                # 測試AI分析時間
                start_time = time.time()
                result = generate_individual_summary(student_id)
                analysis_time = time.time() - start_time
                
                benchmark_results['results']['ai_analysis_time'] = {
                    'time_seconds': round(analysis_time, 2),
                    'target_seconds': 10.0,
                    'meets_target': analysis_time <= 10.0,
                    'status': result.get('status', 'unknown')
                }
                
                # 測試快取存取時間
                start_time = time.time()
                cached_result = generate_individual_summary(student_id)
                cache_time = time.time() - start_time
                
                benchmark_results['results']['cache_access_time'] = {
                    'time_seconds': round(cache_time, 2),
                    'target_seconds': 1.0,
                    'meets_target': cache_time <= 1.0,
                    'is_from_cache': cached_result.get('cached', True)
                }
            else:
                benchmark_results['results']['ai_analysis_time'] = {
                    'status': 'skipped',
                    'reason': 'no_student_data'
                }
                benchmark_results['results']['cache_access_time'] = {
                    'status': 'skipped', 
                    'reason': 'no_student_data'
                }
                
        except Exception as e:
            benchmark_results['results']['ai_analysis_error'] = str(e)
        
        # 測試2：系統回應時間
        start_time = time.time()
        system_status = get_system_status()
        system_response_time = time.time() - start_time
        
        benchmark_results['results']['system_response_time'] = {
            'time_seconds': round(system_response_time, 2),
            'target_seconds': 0.5,
            'meets_target': system_response_time <= 0.5
        }
        
        # 測試3：快取系統效能
        start_time = time.time()
        cache_stats = get_cache_statistics()
        cache_response_time = time.time() - start_time
        
        benchmark_results['results']['cache_system_time'] = {
            'time_seconds': round(cache_response_time, 2),
            'target_seconds': 0.1,
            'meets_target': cache_response_time <= 0.1
        }
        
        # 計算效能等級
        passed_tests = 0
        total_tests = 0
        
        for test_name, test_result in benchmark_results['results'].items():
            if isinstance(test_result, dict) and 'meets_target' in test_result:
                total_tests += 1
                if test_result['meets_target']:
                    passed_tests += 1
        
        if total_tests > 0:
            pass_rate = passed_tests / total_tests
            if pass_rate >= 0.9:
                benchmark_results['performance_grade'] = 'excellent'
            elif pass_rate >= 0.7:
                benchmark_results['performance_grade'] = 'good'
            elif pass_rate >= 0.5:
                benchmark_results['performance_grade'] = 'acceptable'
            else:
                benchmark_results['performance_grade'] = 'needs_improvement'
        
        benchmark_results['summary'] = {
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'pass_rate': round((passed_tests / max(total_tests, 1)) * 100, 1)
        }
        
        logger.info(f"⏱️ 效能測試完成，等級: {benchmark_results['performance_grade']}")
        
        return benchmark_results
        
    except Exception as e:
        logger.error(f"❌ 效能測試錯誤: {e}")
        return {
            'test_status': 'error',
            'error': str(e),
            'test_time': datetime.datetime.now().isoformat()
        }

# =================== 系統啟動和自動初始化 ===================

def auto_startup():
    """系統自動啟動
    
    這個函數會在模組載入時自動執行，執行必要的初始化
    """
    try:
        logger.info("🔄 教學分析系統自動啟動中...")
        
        # 清理過期快取
        clear_expired_cache()
        
        # 如果有API金鑰，嘗試初始化AI服務
        if GEMINI_API_KEY:
            ai_init_success = initialize_ai_service()
            if ai_init_success:
                logger.info("✅ AI服務自動初始化成功")
            else:
                logger.warning("⚠️ AI服務自動初始化失敗，將在需要時重試")
        else:
            logger.warning("⚠️ 未設定API金鑰，AI功能將無法使用")
        
        # 輸出系統資訊
        logger.info(f"📚 {SYSTEM_VERSION_INFO['name']} v{SYSTEM_VERSION_INFO['version']}")
        logger.info(f"🎯 支援 {len(ANALYTICS_MODELS)} 個AI模型")
        logger.info(f"💾 快取有效期: {CACHE_DURATION/60:.0f} 分鐘")
        logger.info("🚀 系統啟動完成")
        
    except Exception as e:
        logger.error(f"❌ 系統自動啟動錯誤: {e}")

# =================== 模組載入時自動執行 ===================

# 只在模組被匯入時執行自動啟動，不在直接執行時執行
if __name__ != '__main__':
    auto_startup()

# =================== 主程式入口（用於測試） ===================

if __name__ == '__main__':
    print("=== EMI Teaching Analytics System - Backend Core ===")
    print(f"版本: {SYSTEM_VERSION_INFO['version']}")
    print("正在執行完整系統測試...")
    
    # 執行完整系統初始化
    init_result = initialize_system()
    print(f"初始化狀態: {init_result['status']}")
    
    # 執行健康檢查
    health_result = perform_system_health_check()
    print(f"健康狀態: {health_result['overall_status']}")
    
    # 執行效能測試
    benchmark_result = benchmark_performance()
    print(f"效能等級: {benchmark_result['performance_grade']}")
    
    # 輸出系統統計
    stats_result = get_analytics_statistics()
    if stats_result['status'] == 'success':
        data_stats = stats_result['data_statistics']
        print(f"資料統計: {data_stats['total_students']} 學生, {data_stats['total_messages']} 訊息")
    
    print("=== 測試完成 ===")

# =================== 檔案結束 ===================

"""
teaching_analytics.py - EMI智能教學助理系統後端核心
Version: 2025.06.28

這個檔案包含了完整的後端核心功能：
1. 智能快取系統（30分鐘有效期）
2. 完善的錯誤處理機制  
3. AI分析引擎（個人和全班摘要）
4. TSV檔案匯出功能
5. 多模型支援和自動切換
6. 系統健康監控
7. 效能統計和優化建議

主要函數：
- generate_individual_summary(): 個人學習摘要
- generate_class_summary(): 全班學習摘要  
- extract_learning_keywords(): 學習關鍵詞提取
- export_student_questions_tsv(): 匯出學生提問
- export_all_questions_tsv(): 匯出全班提問
- get_system_status(): 系統狀態檢查
- perform_system_health_check(): 健康檢查
- benchmark_performance(): 效能測試

效能目標：
- AI分析首次載入：≤ 10秒
- 快取命中載入：≤ 1秒
- API錯誤率：< 1%
- 系統穩定性：99%+
"""
