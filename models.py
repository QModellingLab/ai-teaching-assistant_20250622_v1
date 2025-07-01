# =================== models.py 修正版 - 第1段開始 ===================
# EMI智能教學助理系統 - 資料模型定義（修正版：添加缺失的 update_session_stats 方法）
# 支援優化的註冊流程，移除快取依賴，新增會話追蹤和學習歷程
# 修正日期：2025年6月30日 - 解決AI回應問題

import os
import datetime
import logging
import json
from peewee import *

logger = logging.getLogger(__name__)

# =================== 資料庫配置 ===================

# 從環境變數或預設值設定資料庫
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # 生產環境：使用 PostgreSQL
    import dj_database_url
    db_config = dj_database_url.parse(database_url)
    
    db = PostgresqlDatabase(
        db_config['NAME'],
        user=db_config['USER'],
        password=db_config['PASSWORD'],
        host=db_config['HOST'],
        port=db_config['PORT'],
    )
    logger.info("✅ 使用 PostgreSQL 資料庫")
else:
    # 開發環境：使用 SQLite
    db = SqliteDatabase('emi_teaching_assistant.db')
    logger.info("✅ 使用 SQLite 資料庫")

# =================== 基礎模型 ===================

class BaseModel(Model):
    """所有模型的基礎類別"""
    class Meta:
        database = db

# =================== 學生模型（增強版，支援完整的學習歷程） ===================

class Student(BaseModel):
    """學生模型 - 增強版，支援完整的學習歷程和優化的註冊"""
    
    id = AutoField(primary_key=True)
    line_user_id = CharField(max_length=100, unique=True, verbose_name="LINE用戶ID")
    name = CharField(max_length=100, verbose_name="學生姓名")
    student_id = CharField(max_length=20, verbose_name="學號")
    
    # ✨ 新增：註冊流程相關
    registration_step = IntegerField(default=0, verbose_name="註冊步驟")
    # 0: 未開始, 1: 已輸入學號, 2: 已輸入姓名, 3: 註冊完成
    
    temp_student_id = CharField(max_length=20, null=True, verbose_name="暫存學號")
    
    # ✨ 新增：時間追蹤
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    last_activity = DateTimeField(default=datetime.datetime.now, verbose_name="最後活動時間")
    
    # ✨ 新增：學習統計
    total_questions = IntegerField(default=0, verbose_name="總提問數")
    total_sessions = IntegerField(default=0, verbose_name="總會話數")
    
    class Meta:
        table_name = 'students'
        indexes = (
            (('line_user_id',), True),
            (('student_id',), False),
            (('last_activity',), False),
        )
    
    def __str__(self):
        return f"Student({self.name}, {self.student_id})"
    
    # =================== 演示學生相關屬性 ===================
    
    @property
    def is_demo_student(self):
        """檢查是否為演示學生"""
        return (
            self.line_user_id.startswith('demo_') or 
            self.name.startswith('[DEMO]') or 
            self.name.startswith('學生_')
        )
    
    @property
    def is_real_student(self):
        """檢查是否為真實學生"""
        return not self.is_demo_student
    
    # =================== 註冊流程管理（優化版） ===================
    
    def is_registration_complete(self):
        """檢查註冊是否完成"""
        return self.registration_step >= 3 and self.name and self.student_id
    
    def set_registration_step(self, step):
        """設置註冊步驟"""
        try:
            self.registration_step = step
            self.save()
            logger.debug(f"學生 {self.line_user_id} 註冊步驟更新為: {step}")
        except Exception as e:
            logger.error(f"❌ 更新註冊步驟失敗: {e}")
    
    def complete_registration(self, name, student_id):
        """完成註冊"""
        try:
            self.name = name
            self.student_id = student_id
            self.registration_step = 3
            self.temp_student_id = None  # 清除暫存學號
            self.save()
            
            logger.info(f"✅ 學生註冊完成: {name} ({student_id})")
            return True
        except Exception as e:
            logger.error(f"❌ 完成註冊失敗: {e}")
            return False
    
    def set_temp_student_id(self, student_id):
        """設置暫存學號"""
        try:
            self.temp_student_id = student_id
            self.registration_step = 1
            self.save()
            logger.debug(f"設置暫存學號: {student_id}")
        except Exception as e:
            logger.error(f"❌ 設置暫存學號失敗: {e}")
    
    # =================== 學習歷程和統計（增強版） ===================
    
    def update_activity(self):
        """更新最後活動時間"""
        try:
            self.last_activity = datetime.datetime.now()
            self.save()
        except Exception as e:
            logger.error(f"❌ 更新活動時間失敗: {e}")
    
    def increment_question_count(self):
        """增加提問數"""
        try:
            self.total_questions += 1
            self.update_activity()
            self.save()
            logger.debug(f"學生 {self.name} 總提問數: {self.total_questions}")
        except Exception as e:
            logger.error(f"❌ 更新提問數失敗: {e}")
    
    def increment_session_count(self):
        """增加會話數"""
        try:
            self.total_sessions += 1
            self.save()
            logger.debug(f"學生 {self.name} 總會話數: {self.total_sessions}")
        except Exception as e:
            logger.error(f"❌ 更新會話數失敗: {e}")
    
    def get_activity_summary(self):
        """取得學習活動摘要"""
        try:
            from datetime import timedelta
            
            # 計算學習天數
            days_since_first = (datetime.datetime.now() - self.created_at).days + 1
            
            # 計算平均每日提問數
            avg_daily_questions = self.total_questions / max(days_since_first, 1)
            
            # 計算最近活動
            days_since_last_activity = (datetime.datetime.now() - self.last_activity).days
            
            return {
                'total_questions': self.total_questions,
                'total_sessions': self.total_sessions,
                'days_since_first': days_since_first,
                'avg_daily_questions': round(avg_daily_questions, 1),
                'days_since_last_activity': days_since_last_activity,
                'created_at': self.created_at,
                'last_activity': self.last_activity
            }
        except Exception as e:
            logger.error(f"❌ 取得活動摘要失敗: {e}")
            return {}
    
    def get_learning_insights(self):
        """取得學習洞察"""
        try:
            summary = self.get_activity_summary()
            insights = []
            
            # 活躍度分析
            if summary.get('days_since_last_activity', 0) <= 1:
                insights.append("🟢 學習活躍度高")
            elif summary.get('days_since_last_activity', 0) <= 7:
                insights.append("🟡 學習活躍度中等")
            else:
                insights.append("🔴 學習活躍度低")
            
            # 提問頻率分析
            avg_daily = summary.get('avg_daily_questions', 0)
            if avg_daily >= 3:
                insights.append("📈 提問頻率高")
            elif avg_daily >= 1:
                insights.append("📊 提問頻率中等")
            else:
                insights.append("📉 提問頻率低")
            
            # 學習持續性分析
            days_since_first = summary.get('days_since_first', 0)
            if days_since_first >= 7:
                insights.append("🎯 持續學習超過一週")
            if days_since_first >= 30:
                insights.append("🏆 持續學習超過一個月")
            
            return insights
        except Exception as e:
            logger.error(f"❌ 取得學習洞察失敗: {e}")
            return []
    
    # =================== 會話管理（新增功能） ===================
    
    def get_active_session(self):
        """取得目前活躍的會話"""
        try:
            # 匯入在方法內部，避免循環匯入
            active_session = ConversationSession.select().where(
                ConversationSession.student == self,
                ConversationSession.session_end.is_null()
            ).first()
            
            return active_session
        except Exception as e:
            logger.error(f"❌ 取得活躍會話失敗: {e}")
            return None
    
    def start_new_session(self, topic_hint=''):
        """開始新的會話"""
        try:
            # 先結束任何現有的活躍會話
            active_session = self.get_active_session()
            if active_session:
                active_session.end_session("開始新會話時自動結束")
            
            # 創建新會話
            from models import ConversationSession  # 避免循環匯入
            new_session = ConversationSession.create(
                student=self,
                topic_hint=topic_hint
            )
            
            # 更新學生的會話計數
            self.increment_session_count()
            
            logger.info(f"✅ 學生 {self.name} 開始新會話 (ID: {new_session.id})")
            return new_session
            
        except Exception as e:
            logger.error(f"❌ 開始新會話失敗: {e}")
            return None
    
    def end_current_session(self, topic_summary=None):
        """結束目前的會話"""
        try:
            active_session = self.get_active_session()
            if active_session:
                active_session.end_session(topic_summary)
                logger.info(f"✅ 結束學生 {self.name} 的會話")
                return True
            else:
                logger.debug(f"學生 {self.name} 沒有活躍的會話可結束")
                return False
        except Exception as e:
            logger.error(f"❌ 結束會話失敗: {e}")
            return False
    
    def get_recent_sessions(self, limit=5):
        """取得最近的會話"""
        try:
            return list(ConversationSession.select().where(
                ConversationSession.student == self
            ).order_by(
                ConversationSession.session_start.desc()
            ).limit(limit))
        except Exception as e:
            logger.error(f"❌ 取得最近會話失敗: {e}")
            return []
    
    # =================== 資料驗證和清理 ===================
    
    def validate_student_data(self):
        """驗證學生資料的完整性"""
        errors = []
        
        if not self.line_user_id or len(self.line_user_id.strip()) == 0:
            errors.append("LINE用戶ID不能為空")
        
        if self.is_registration_complete():
            if not self.name or len(self.name.strip()) == 0:
                errors.append("學生姓名不能為空")
            
            if not self.student_id or len(self.student_id.strip()) == 0:
                errors.append("學號不能為空")
        
        return errors
    
    @classmethod
    def cleanup_incomplete_registrations(cls, days_old=7):
        """清理過舊的未完成註冊"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
            
            incomplete_students = cls.select().where(
                cls.registration_step < 3,
                cls.created_at < cutoff_date
            )
            
            deleted_count = 0
            for student in incomplete_students:
                # 也清理相關的訊息
                Message.delete().where(Message.student == student).execute()
                student.delete_instance()
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"✅ 清理了 {deleted_count} 個未完成的註冊")
            
            return deleted_count
        except Exception as e:
            logger.error(f"❌ 清理未完成註冊失敗: {e}")
            return 0
    
    @classmethod
    def get_real_students(cls):
        """取得所有真實學生（排除演示學生）"""
        return cls.select().where(
            (~cls.name.startswith('[DEMO]')) &
            (~cls.line_user_id.startswith('demo_')) &
            (~cls.name.startswith('學生_'))
        )
    
    @classmethod
    def get_demo_students(cls):
        """取得所有演示學生"""
        return cls.select().where(
            (cls.name.startswith('[DEMO]')) |
            (cls.line_user_id.startswith('demo_')) |
            (cls.name.startswith('學生_'))
        )
    
    @classmethod
    def cleanup_demo_students(cls):
        """清理所有演示學生和相關資料"""
        try:
            demo_students = list(cls.get_demo_students())
            
            if not demo_students:
                return {
                    'success': True,
                    'total_deleted': 0,
                    'message': '沒有找到演示學生'
                }
            
            deleted_count = 0
            for student in demo_students:
                # 清理相關的訊息
                Message.delete().where(Message.student == student).execute()
                
                # 清理相關的會話
                ConversationSession.delete().where(
                    ConversationSession.student == student
                ).execute()
                
                # 刪除學生
                student.delete_instance()
                deleted_count += 1
            
            logger.info(f"成功清理 {deleted_count} 個演示學生及相關資料")
            
            return {
                'success': True,
                'total_deleted': deleted_count,
                'message': f"成功清理 {deleted_count} 個演示學生及相關資料"
            }
            
        except Exception as e:
            logger.error(f"清理演示學生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示學生時發生錯誤'
            }
    
    @classmethod
    def get_or_create_student(cls, line_user_id):
        """取得或創建學生（優化版，支援註冊流程）"""
        try:
            student, created = cls.get_or_create(
                line_user_id=line_user_id,
                defaults={
                    'name': '',
                    'student_id': '',
                    'registration_step': 0
                }
            )
            
            if created:
                logger.info(f"✅ 創建新學生記錄: {line_user_id}")
            
            return student
        except Exception as e:
            logger.error(f"❌ 取得或創建學生失敗: {e}")
            return None

# =================== models.py 修正版 - 第1段結束 ===================

# =================== models.py 修正版 - 第2段-A開始 ===================
# 接續第1段，包含：對話會話模型（修正版：添加缺失的 update_session_stats 方法）

# =================== 對話會話模型（修正版） ===================

class ConversationSession(BaseModel):
    """對話會話模型 - 修正版：添加缺失的 update_session_stats 方法"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='conversation_sessions', verbose_name="學生")
    session_start = DateTimeField(default=datetime.datetime.now, verbose_name="會話開始時間")
    session_end = DateTimeField(null=True, verbose_name="會話結束時間")
    topic_hint = CharField(max_length=200, default='', verbose_name="主題提示")
    topic_summary = TextField(null=True, verbose_name="主題摘要")
    message_count = IntegerField(default=0, verbose_name="訊息數量")
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    
    class Meta:
        table_name = 'conversation_sessions'
        indexes = (
            (('student', 'session_start'), False),
            (('session_start',), False),
            (('session_end',), False),
        )
    
    def __str__(self):
        status = "進行中" if not self.session_end else "已結束"
        return f"Session({self.student.name}, {status}, {self.session_start})"
    
    def is_active(self):
        """檢查會話是否仍在進行中"""
        return self.session_end is None
    
    def get_duration_minutes(self):
        """取得會話持續時間（分鐘）"""
        if not self.session_end:
            end_time = datetime.datetime.now()
        else:
            end_time = self.session_end
        
        duration = end_time - self.session_start
        return duration.total_seconds() / 60
    
    def end_session(self, topic_summary=None):
        """結束會話"""
        try:
            self.session_end = datetime.datetime.now()
            if topic_summary:
                self.topic_summary = topic_summary
            
            # 更新訊息計數
            self.update_message_count()
            self.save()
            
            logger.info(f"✅ 結束會話 (ID: {self.id})，持續 {self.get_duration_minutes():.1f} 分鐘")
        except Exception as e:
            logger.error(f"❌ 結束會話失敗: {e}")
    
    def update_message_count(self):
        """更新會話中的訊息計數"""
        try:
            self.message_count = Message.select().where(
                Message.session == self
            ).count()
            self.save()
            logger.debug(f"更新會話 {self.id} 訊息計數: {self.message_count}")
        except Exception as e:
            logger.error(f"❌ 更新會話訊息計數失敗: {e}")
    
    # 🔧 **關鍵修正：添加缺失的 update_session_stats 方法**
    def update_session_stats(self):
        """
        更新會話統計 - 修正版
        這是app.py中調用但在原models.py中缺失的方法
        解決第二個專業問題後AI沒有回應的根本問題
        """
        try:
            # 更新訊息計數
            self.message_count = Message.select().where(
                Message.session == self
            ).count()
            
            # 更新最後活動時間（如果需要）
            if hasattr(self, 'last_activity'):
                self.last_activity = datetime.datetime.now()
            
            # 儲存更新
            self.save()
            
            logger.debug(f"✅ 更新會話統計 (ID: {self.id})，訊息數: {self.message_count}")
            
            # 同時更新學生的活動時間
            if self.student:
                self.student.update_activity()
            
        except Exception as e:
            logger.error(f"❌ 更新會話統計失敗 (ID: {getattr(self, 'id', 'unknown')}): {e}")
            # 即使統計更新失敗，也不要影響主要流程
    
    def get_messages(self):
        """取得會話中的所有訊息"""
        try:
            return list(Message.select().where(
                Message.session == self
            ).order_by(Message.timestamp))
        except Exception as e:
            logger.error(f"❌ 取得會話訊息失敗: {e}")
            return []
    
    def should_auto_end(self, timeout_minutes=30):
        """檢查是否應該自動結束會話（基於時間）"""
        if self.session_end:
            return False  # 已經結束
        
        time_since_start = datetime.datetime.now() - self.session_start
        return time_since_start.total_seconds() > (timeout_minutes * 60)
    
    def get_last_message_time(self):
        """取得最後一則訊息的時間"""
        try:
            last_message = Message.select().where(
                Message.session == self
            ).order_by(Message.timestamp.desc()).first()
            
            return last_message.timestamp if last_message else self.session_start
        except Exception as e:
            logger.error(f"❌ 取得最後訊息時間失敗: {e}")
            return self.session_start
    
    def should_auto_end_by_inactivity(self, timeout_minutes=30):
        """檢查是否應該基於非活躍狀態自動結束會話"""
        if self.session_end:
            return False  # 已經結束
        
        last_activity = self.get_last_message_time()
        time_since_activity = datetime.datetime.now() - last_activity
        return time_since_activity.total_seconds() > (timeout_minutes * 60)
    
    def get_context_summary(self):
        """取得會話的上下文摘要"""
        try:
            messages = self.get_messages()
            if not messages:
                return "空會話"
            
            # 簡單的上下文摘要
            total_messages = len(messages)
            topics = set()
            
            for msg in messages:
                if msg.topic_tags:
                    tags = [tag.strip() for tag in msg.topic_tags.split(',') if tag.strip()]
                    topics.update(tags)
            
            duration = self.get_duration_minutes()
            
            summary_parts = [
                f"{total_messages} 則訊息",
                f"{duration:.1f} 分鐘" if self.session_end else f"進行中 {duration:.1f} 分鐘"
            ]
            
            if topics:
                summary_parts.append(f"主題: {', '.join(list(topics)[:3])}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"❌ 取得會話摘要失敗: {e}")
            return "摘要生成失敗"
    
    @classmethod
    def cleanup_old_sessions(cls, days_old=30):
        """清理過舊的會話記錄"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
            deleted_count = cls.delete().where(
                cls.session_start < cutoff_date
            ).execute()
            
            if deleted_count > 0:
                logger.info(f"✅ 清理了 {deleted_count} 個舊會話記錄")
            
            return deleted_count
        except Exception as e:
            logger.error(f"❌ 清理舊會話失敗: {e}")
            return 0
    
    @classmethod
    def auto_end_inactive_sessions(cls, timeout_minutes=30):
        """自動結束非活躍的會話"""
        try:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=timeout_minutes)
            
            inactive_sessions = cls.select().where(
                cls.session_end.is_null(),
                cls.session_start < cutoff_time
            )
            
            ended_count = 0
            for session in inactive_sessions:
                # 檢查最後訊息時間，而不只是會話開始時間
                if session.should_auto_end_by_inactivity(timeout_minutes):
                    session.end_session("自動結束（非活躍）")
                    ended_count += 1
            
            if ended_count > 0:
                logger.info(f"✅ 自動結束了 {ended_count} 個非活躍會話")
            
            return ended_count
        except Exception as e:
            logger.error(f"❌ 自動結束會話失敗: {e}")
            return 0
    
    @classmethod
    def get_active_sessions_count(cls):
        """取得目前活躍會話數量"""
        try:
            return cls.select().where(cls.session_end.is_null()).count()
        except Exception as e:
            logger.error(f"❌ 取得活躍會話數量失敗: {e}")
            return 0
    
    @classmethod
    def get_recent_sessions(cls, limit=10):
        """取得最近的會話"""
        try:
            return list(cls.select().order_by(
                cls.session_start.desc()
            ).limit(limit))
        except Exception as e:
            logger.error(f"❌ 取得最近會話失敗: {e}")
            return []

# =================== models.py 修正版 - 第2段-A結束 ===================

# =================== models.py 修正版 - 第2段-B開始 ===================
# 接續第2段-A，包含：訊息模型（增強版，支援會話追蹤）

# =================== 訊息模型（增強版，支援會話追蹤） ===================

class Message(BaseModel):
    """訊息模型 - 增強版，支援會話追蹤和主題標籤"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='messages', verbose_name="學生")
    content = TextField(verbose_name="訊息內容")
    timestamp = DateTimeField(default=datetime.datetime.now, verbose_name="時間戳記")
    source_type = CharField(max_length=20, default='student', verbose_name="來源類型")
    # 支援的類型：'student', 'line', 'ai'
    
    # ✨ 新增：會話追蹤
    session = ForeignKeyField(ConversationSession, null=True, backref='messages', verbose_name="所屬會話")
    
    # ✨ 新增：主題標籤（用於記憶功能）
    topic_tags = CharField(max_length=500, default='', verbose_name="主題標籤")
    
    # ✨ 新增：AI回應（如果這是學生訊息，可以儲存對應的AI回應）
    ai_response = TextField(null=True, verbose_name="AI回應")
    
    class Meta:
        table_name = 'messages'
        indexes = (
            (('student', 'timestamp'), False),
            (('timestamp',), False),
            (('source_type',), False),
            (('session',), False),  # 新增：會話索引
        )
    
    def __str__(self):
        session_info = f", 會話{self.session.id}" if self.session else ""
        return f"Message({self.student.name}, {self.source_type}, {self.timestamp}{session_info})"
    
    # =================== 演示訊息相關屬性（保留向後相容） ===================
    
    @property
    def is_demo_message(self):
        """檢查是否為演示訊息"""
        return self.student.is_demo_student
    
    @property
    def is_real_message(self):
        """檢查是否為真實訊息"""
        return not self.is_demo_message
    
    @property
    def is_student_message(self):
        """檢查是否為學生訊息"""
        return self.source_type in ['line', 'student']
    
    @property
    def is_ai_message(self):
        """檢查是否為AI訊息"""
        return self.source_type == 'ai'
    
    @classmethod
    def get_real_messages(cls):
        """取得所有真實訊息"""
        return cls.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_')) &
            (~Student.name.startswith('學生_'))
        )
    
    @classmethod
    def get_demo_messages(cls):
        """取得所有演示訊息"""
        return cls.select().join(Student).where(
            (Student.name.startswith('[DEMO]')) |
            (Student.line_user_id.startswith('demo_')) |
            (Student.name.startswith('學生_'))
        )
    
    @classmethod
    def cleanup_demo_messages(cls):
        """清理所有演示訊息"""
        try:
            demo_messages = list(cls.get_demo_messages())
            
            if not demo_messages:
                return {
                    'success': True,
                    'total_deleted': 0,
                    'message': '沒有找到演示訊息'
                }
            
            deleted_count = 0
            for message in demo_messages:
                message.delete_instance()
                deleted_count += 1
            
            logger.info(f"成功清理 {deleted_count} 則演示訊息")
            
            return {
                'success': True,
                'total_deleted': deleted_count,
                'message': f"成功清理 {deleted_count} 則演示訊息"
            }
            
        except Exception as e:
            logger.error(f"清理演示訊息錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示訊息時發生錯誤'
            }
    
    # =================== 訊息創建和管理（修正版） ===================
    
    @classmethod
    def create(cls, **data):
        """創建訊息（覆寫以添加會話管理和統計更新）"""
        try:
            # 創建基本訊息記錄
            message = super().create(**data)
            
            # 如果有會話，更新會話統計
            if message.session:
                message.session.update_session_stats()
            
            # 更新學生活動統計
            if message.student:
                message.student.update_activity()
                if message.source_type in ['line', 'student']:
                    message.student.increment_question_count()
            
            logger.debug(f"✅ 創建訊息: {message}")
            return message
            
        except Exception as e:
            logger.error(f"❌ 創建訊息失敗: {e}")
            raise
    
    def add_topic_tags(self, tags):
        """新增主題標籤"""
        try:
            if isinstance(tags, list):
                tags_str = ', '.join(tags)
            else:
                tags_str = str(tags)
            
            if self.topic_tags:
                # 合併現有標籤
                existing_tags = [tag.strip() for tag in self.topic_tags.split(',')]
                new_tags = [tag.strip() for tag in tags_str.split(',')]
                combined_tags = list(set(existing_tags + new_tags))
                self.topic_tags = ', '.join(combined_tags)
            else:
                self.topic_tags = tags_str
            
            self.save()
            logger.debug(f"更新訊息主題標籤: {self.topic_tags}")
            
        except Exception as e:
            logger.error(f"❌ 新增主題標籤失敗: {e}")
    
    # =================== 訊息查詢和統計（基礎部分） ===================
    
    @classmethod
    def get_student_messages(cls, student, limit=None):
        """取得學生的所有訊息"""
        try:
            query = cls.select().where(cls.student == student).order_by(cls.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
            
            return list(query)
        except Exception as e:
            logger.error(f"❌ 取得學生訊息失敗: {e}")
            return []
    
    @classmethod
    def get_messages_by_date_range(cls, start_date, end_date):
        """根據日期範圍取得訊息"""
        try:
            return list(cls.select().where(
                cls.timestamp >= start_date,
                cls.timestamp <= end_date
            ).order_by(cls.timestamp))
        except Exception as e:
            logger.error(f"❌ 根據日期範圍取得訊息失敗: {e}")
            return []
    
    @classmethod
    def get_messages_with_topic(cls, topic):
        """取得包含特定主題的訊息"""
        try:
            return list(cls.select().where(
                cls.topic_tags.contains(topic)
            ).order_by(cls.timestamp.desc()))
        except Exception as e:
            logger.error(f"❌ 取得主題相關訊息失敗: {e}")
            return []
    
    @classmethod
    def get_student_statistics(cls, student):
        """取得學生的訊息統計"""
        try:
            total_messages = cls.select().where(cls.student == student).count()
            
            student_messages = cls.select().where(
                cls.student == student,
                cls.source_type.in_(['line', 'student'])
            ).count()
            
            ai_responses = cls.select().where(
                cls.student == student,
                cls.ai_response.is_null(False)
            ).count()
            
            # 取得最早和最晚的訊息時間
            first_message = cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp).first()
            
            last_message = cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp.desc()).first()
            
            # 計算使用天數
            usage_days = 0
            if first_message and last_message:
                delta = last_message.timestamp - first_message.timestamp
                usage_days = delta.days + 1
            
            return {
                'total_messages': total_messages,
                'student_messages': student_messages,
                'ai_responses': ai_responses,
                'usage_days': usage_days,
                'first_message_date': first_message.timestamp if first_message else None,
                'last_message_date': last_message.timestamp if last_message else None,
                'avg_messages_per_day': round(total_messages / max(usage_days, 1), 1)
            }
            
        except Exception as e:
            logger.error(f"❌ 取得學生統計失敗: {e}")
            return {}
    
    @classmethod
    def cleanup_old_messages(cls, days_old=90):
        """清理過舊的訊息"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
            
            deleted_count = cls.delete().where(
                cls.timestamp < cutoff_date
            ).execute()
            
            if deleted_count > 0:
                logger.info(f"✅ 清理了 {deleted_count} 則舊訊息")
            
            return deleted_count
        except Exception as e:
            logger.error(f"❌ 清理舊訊息失敗: {e}")
            return 0

# =================== models.py 修正版 - 第2段-B結束 ===================

# =================== models.py 修正版 - 第3段開始 ===================
# 接續第2段，包含：訊息創建、記憶功能優化版

        try:
            # 創建基本訊息記錄
            message = super().create(**data)
            
            # 如果有會話，更新會話統計
            if message.session:
                message.session.update_session_stats()
            
            # 更新學生活動統計
            if message.student:
                message.student.update_activity()
                if message.source_type in ['line', 'student']:
                    message.student.increment_question_count()
            
            logger.debug(f"✅ 創建訊息: {message}")
            return message
            
        except Exception as e:
            logger.error(f"❌ 創建訊息失敗: {e}")
            raise
    
    def add_topic_tags(self, tags):
        """新增主題標籤"""
        try:
            if isinstance(tags, list):
                tags_str = ', '.join(tags)
            else:
                tags_str = str(tags)
            
            if self.topic_tags:
                # 合併現有標籤
                existing_tags = [tag.strip() for tag in self.topic_tags.split(',')]
                new_tags = [tag.strip() for tag in tags_str.split(',')]
                combined_tags = list(set(existing_tags + new_tags))
                self.topic_tags = ', '.join(combined_tags)
            else:
                self.topic_tags = tags_str
            
            self.save()
            logger.debug(f"更新訊息主題標籤: {self.topic_tags}")
            
        except Exception as e:
            logger.error(f"❌ 新增主題標籤失敗: {e}")
    
    # =================== 🔧 記憶功能優化版 - 使用AI生成主題 ===================
    
    @classmethod
    def get_conversation_context(cls, student, limit=5):
        """
        取得對話上下文 - 優化版
        主要修改：使用AI動態生成主題標籤，取代固定的關鍵詞字典
        """
        try:
            # 取得最近的對話記錄
            recent_messages = list(cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp.desc()).limit(limit))
            
            if not recent_messages:
                return {
                    'conversation_flow': [],
                    'recent_topics': [],
                    'context_summary': '這是新的對話，沒有歷史記錄。'
                }
            
            # 建立對話流程
            conversation_flow = []
            all_content = []
            
            for msg in reversed(recent_messages):  # 按時間順序排列
                flow_item = {
                    'content': msg.content,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'source_type': msg.source_type
                }
                
                if msg.ai_response:
                    flow_item['ai_response'] = msg.ai_response
                
                conversation_flow.append(flow_item)
                all_content.append(msg.content)
                if msg.ai_response:
                    all_content.append(msg.ai_response)
            
            # 🔧 **關鍵優化：使用AI動態生成主題標籤**
            recent_topics = cls._generate_topics_with_ai(all_content)
            
            # 建立上下文摘要
            context_summary = cls._build_context_summary(conversation_flow, recent_topics)
            
            return {
                'conversation_flow': conversation_flow,
                'recent_topics': recent_topics,
                'context_summary': context_summary
            }
            
        except Exception as e:
            logger.error(f"❌ 取得對話上下文失敗: {e}")
            return {
                'conversation_flow': [],
                'recent_topics': [],
                'context_summary': '無法取得對話歷史記錄。'
            }
    
    @classmethod
    def _generate_topics_with_ai(cls, content_list):
        """
        🔧 **新增功能：使用AI動態生成主題標籤**
        取代原本固定的關鍵詞字典 'AI技術', '機器學習', '深度學習'
        避免侷限性，支援任何主題領域
        """
        try:
            if not content_list:
                return []
            
            # 合併所有對話內容
            combined_content = ' '.join(content_list)
            
            # 如果內容太短，不需要生成主題
            if len(combined_content.strip()) < 20:
                return []
            
            # 使用簡單的AI提示詞來提取主題
            try:
                import google.generativeai as genai
                
                # 設定API金鑰（從環境變數）
                api_key = os.environ.get('GEMINI_API_KEY')
                if not api_key:
                    logger.warning("⚠️ 沒有Gemini API金鑰，使用預設主題提取")
                    return cls._extract_topics_fallback(combined_content)
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""Based on the following conversation content, extract 3-5 relevant topic keywords in Traditional Chinese. 
Return only the keywords separated by commas, no explanations.

Content: {combined_content[:500]}

Keywords:"""
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    # 清理和格式化主題標籤
                    topics = [topic.strip() for topic in response.text.split(',')]
                    topics = [topic for topic in topics if len(topic) > 1 and len(topic) < 20]
                    
                    logger.debug(f"AI生成主題標籤: {topics}")
                    return topics[:5]  # 最多返回5個主題
                
            except Exception as ai_error:
                logger.warning(f"⚠️ AI主題生成失敗，使用備用方法: {ai_error}")
                return cls._extract_topics_fallback(combined_content)
            
            return []
            
        except Exception as e:
            logger.error(f"❌ 生成主題標籤失敗: {e}")
            return []
    
    @classmethod
    def _extract_topics_fallback(cls, content):
        """
        備用主題提取方法（當AI無法使用時）
        使用簡單的關鍵詞匹配，但比原本更靈活
        """
        try:
            content_lower = content.lower()
            
            # 擴展的主題字典（比原本更廣泛）
            topic_keywords = {
                'AI技術': ['ai', 'artificial intelligence', '人工智慧', '人工智能'],
                '機器學習': ['machine learning', 'ml', '機器學習', '機器學習'],
                '深度學習': ['deep learning', 'neural network', '深度學習', '神經網路'],
                '程式設計': ['programming', 'coding', '程式', '編程', 'python', 'java'],
                '資料科學': ['data science', '資料科學', '數據分析', 'analytics'],
                '網路技術': ['network', 'internet', '網路', '網際網路'],
                '軟體開發': ['software', 'development', '軟體', '開發'],
                '演算法': ['algorithm', '演算法', '算法'],
                '資料庫': ['database', '資料庫', '數據庫', 'sql'],
                '雲端計算': ['cloud computing', '雲端', '雲計算'],
                '物聯網': ['iot', 'internet of things', '物聯網'],
                '區塊鏈': ['blockchain', '區塊鏈', '比特幣'],
                '智慧家居': ['smart home', '智慧家居', '智能家居'],
                '自動化': ['automation', '自動化', '自動'],
                '科技趨勢': ['technology', 'tech', '科技', '技術']
            }
            
            found_topics = []
            for topic, keywords in topic_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    found_topics.append(topic)
            
            return found_topics[:5]  # 最多返回5個主題
            
        except Exception as e:
            logger.error(f"❌ 備用主題提取失敗: {e}")
            return []
    
    @classmethod
    def _build_context_summary(cls, conversation_flow, recent_topics):
        """建立上下文摘要"""
        try:
            total_messages = len(conversation_flow)
            
            if total_messages == 0:
                return "這是新的對話，沒有歷史記錄。"
            
            # 基本統計
            summary_parts = [f"最近有 {total_messages} 則對話記錄"]
            
            # 加入主題資訊
            if recent_topics:
                topics_str = '、'.join(recent_topics[:3])
                summary_parts.append(f"主要討論主題：{topics_str}")
            
            # 加入時間資訊
            if conversation_flow:
                latest_time = conversation_flow[-1]['timestamp']
                summary_parts.append(f"最後對話時間：{latest_time}")
            
            return "。".join(summary_parts) + "。"
            
        except Exception as e:
            logger.error(f"❌ 建立上下文摘要失敗: {e}")
            return "對話上下文摘要生成失敗。"
    
    # =================== 訊息查詢和統計 ===================
    
    @classmethod
    def get_student_messages(cls, student, limit=None):
        """取得學生的所有訊息"""
        try:
            query = cls.select().where(cls.student == student).order_by(cls.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
            
            return list(query)
        except Exception as e:
            logger.error(f"❌ 取得學生訊息失敗: {e}")
            return []
    
    @classmethod
    def get_messages_by_date_range(cls, start_date, end_date):
        """根據日期範圍取得訊息"""
        try:
            return list(cls.select().where(
                cls.timestamp >= start_date,
                cls.timestamp <= end_date
            ).order_by(cls.timestamp))
        except Exception as e:
            logger.error(f"❌ 根據日期範圍取得訊息失敗: {e}")
            return []
    
    @classmethod
    def get_messages_with_topic(cls, topic):
        """取得包含特定主題的訊息"""
        try:
            return list(cls.select().where(
                cls.topic_tags.contains(topic)
            ).order_by(cls.timestamp.desc()))
        except Exception as e:
            logger.error(f"❌ 取得主題相關訊息失敗: {e}")
            return []
    
    @classmethod
    def get_student_statistics(cls, student):
        """取得學生的訊息統計"""
        try:
            total_messages = cls.select().where(cls.student == student).count()
            
            student_messages = cls.select().where(
                cls.student == student,
                cls.source_type.in_(['line', 'student'])
            ).count()
            
            ai_responses = cls.select().where(
                cls.student == student,
                cls.ai_response.is_null(False)
            ).count()
            
            # 取得最早和最晚的訊息時間
            first_message = cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp).first()
            
            last_message = cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp.desc()).first()
            
            # 計算使用天數
            usage_days = 0
            if first_message and last_message:
                delta = last_message.timestamp - first_message.timestamp
                usage_days = delta.days + 1
            
            return {
                'total_messages': total_messages,
                'student_messages': student_messages,
                'ai_responses': ai_responses,
                'usage_days': usage_days,
                'first_message_date': first_message.timestamp if first_message else None,
                'last_message_date': last_message.timestamp if last_message else None,
                'avg_messages_per_day': round(total_messages / max(usage_days, 1), 1)
            }
            
        except Exception as e:
            logger.error(f"❌ 取得學生統計失敗: {e}")
            return {}
    
    @classmethod
    def cleanup_old_messages(cls, days_old=90):
        """清理過舊的訊息"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
            
            deleted_count = cls.delete().where(
                cls.timestamp < cutoff_date
            ).execute()
            
            if deleted_count > 0:
                logger.info(f"✅ 清理了 {deleted_count} 則舊訊息")
            
            return deleted_count
        except Exception as e:
            logger.error(f"❌ 清理舊訊息失敗: {e}")
            return 0

# =================== models.py 修正版 - 第3段結束 ===================

# =================== models.py 修正版 - 第4段開始 ===================
# 接續第3段，包含：學習歷程模型、資料庫初始化、演示資料

# =================== 學習歷程模型（保留完整功能） ===================

class LearningProgress(BaseModel):
    """學習歷程模型 - 追蹤學生的學習進度和成就"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='learning_progress', verbose_name="學生")
    topic = CharField(max_length=100, verbose_name="學習主題")
    skill_level = IntegerField(default=1, verbose_name="技能等級")  # 1-5
    questions_asked = IntegerField(default=0, verbose_name="提問次數")
    last_interaction = DateTimeField(default=datetime.datetime.now, verbose_name="最後互動時間")
    understanding_score = FloatField(default=0.0, verbose_name="理解分數")  # 0.0-1.0
    
    # ✨ 新增：學習里程碑
    milestones_achieved = TextField(default='[]', verbose_name="已達成里程碑")  # JSON格式
    notes = TextField(default='', verbose_name="學習筆記")
    
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    updated_at = DateTimeField(default=datetime.datetime.now, verbose_name="更新時間")
    
    class Meta:
        table_name = 'learning_progress'
        indexes = (
            (('student', 'topic'), True),  # 每個學生每個主題只有一條記錄
            (('topic',), False),
            (('skill_level',), False),
            (('last_interaction',), False),
        )
    
    def __str__(self):
        return f"Progress({self.student.name}, {self.topic}, Lv.{self.skill_level})"
    
    def update_progress(self, understanding_increment=0.1):
        """更新學習進度"""
        try:
            self.questions_asked += 1
            self.last_interaction = datetime.datetime.now()
            self.updated_at = datetime.datetime.now()
            
            # 更新理解分數
            self.understanding_score = min(1.0, self.understanding_score + understanding_increment)
            
            # 根據理解分數更新技能等級
            if self.understanding_score >= 0.8 and self.skill_level < 5:
                self.skill_level = min(5, self.skill_level + 1)
                logger.info(f"✨ 學生 {self.student.name} 在 {self.topic} 技能提升至 Lv.{self.skill_level}")
            
            self.save()
            
        except Exception as e:
            logger.error(f"❌ 更新學習進度失敗: {e}")
    
    def add_milestone(self, milestone):
        """新增學習里程碑"""
        try:
            milestones = json.loads(self.milestones_achieved)
            if milestone not in milestones:
                milestones.append({
                    'milestone': milestone,
                    'achieved_at': datetime.datetime.now().isoformat()
                })
                self.milestones_achieved = json.dumps(milestones, ensure_ascii=False)
                self.save()
                logger.info(f"🎉 學生 {self.student.name} 達成里程碑: {milestone}")
        except Exception as e:
            logger.error(f"❌ 新增里程碑失敗: {e}")
    
    def get_milestones(self):
        """取得已達成的里程碑"""
        try:
            return json.loads(self.milestones_achieved)
        except:
            return []
    
    @classmethod
    def get_or_create_progress(cls, student, topic):
        """取得或創建學習進度記錄"""
        try:
            progress, created = cls.get_or_create(
                student=student,
                topic=topic,
                defaults={
                    'skill_level': 1,
                    'understanding_score': 0.0
                }
            )
            
            if created:
                logger.info(f"✅ 創建新的學習進度記錄: {student.name} - {topic}")
            
            return progress
        except Exception as e:
            logger.error(f"❌ 取得或創建學習進度失敗: {e}")
            return None
    
    @classmethod
    def get_student_summary(cls, student):
        """取得學生的學習摘要"""
        try:
            progress_records = list(cls.select().where(cls.student == student))
            
            if not progress_records:
                return {
                    'total_topics': 0,
                    'average_skill_level': 0,
                    'total_questions': 0,
                    'strong_areas': [],
                    'improvement_areas': []
                }
            
            total_topics = len(progress_records)
            total_questions = sum(p.questions_asked for p in progress_records)
            average_skill_level = sum(p.skill_level for p in progress_records) / total_topics
            
            # 找出強項和需改進的領域
            strong_areas = [p.topic for p in progress_records if p.skill_level >= 4]
            improvement_areas = [p.topic for p in progress_records if p.skill_level <= 2]
            
            return {
                'total_topics': total_topics,
                'average_skill_level': round(average_skill_level, 1),
                'total_questions': total_questions,
                'strong_areas': strong_areas,
                'improvement_areas': improvement_areas
            }
            
        except Exception as e:
            logger.error(f"❌ 取得學習摘要失敗: {e}")
            return {}

# =================== 資料庫初始化和管理 ===================

def initialize_database():
    """初始化資料庫"""
    try:
        logger.info("🔧 開始初始化資料庫...")
        
        # 建立所有表格
        db.create_tables([
            Student, 
            ConversationSession, 
            Message, 
            LearningProgress
        ], safe=True)
        
        logger.info("✅ 資料庫初始化完成")
        
        # 檢查是否需要創建演示資料
        if Student.select().count() == 0:
            logger.info("🎯 資料庫為空，創建演示資料...")
            create_demo_data()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        return False

def create_demo_data():
    """創建演示資料"""
    try:
        logger.info("🎭 開始創建演示資料...")
        
        # 創建演示學生
        demo_students = [
            {
                'line_user_id': 'demo_student_001',
                'name': '[DEMO] 學生_小明',
                'student_id': 'A123456789',
                'registration_step': 3
            },
            {
                'line_user_id': 'demo_student_002', 
                'name': '[DEMO] 學生_小華',
                'student_id': 'B987654321',
                'registration_step': 3
            }
        ]
        
        created_students = []
        for student_data in demo_students:
            student = Student.create(**student_data)
            created_students.append(student)
            logger.info(f"✅ 創建演示學生: {student.name}")
        
        # 為演示學生創建一些對話記錄
        demo_messages = [
            "什麼是人工智慧？",
            "機器學習和深度學習有什麼差別？",
            "AI在日常生活中有哪些應用？",
            "請解釋什麼是神經網路",
            "智慧家居系統是如何運作的？"
        ]
        
        for i, student in enumerate(created_students):
            # 創建會話
            session = ConversationSession.create(
                student=student,
                topic_hint='AI基礎概念討論'
            )
            
            # 創建訊息
            for j, msg_content in enumerate(demo_messages[:3]):  # 每個學生3則訊息
                Message.create(
                    student=student,
                    content=msg_content,
                    session=session,
                    source_type='line',
                    ai_response=f"這是關於「{msg_content}」的詳細AI回應範例..."
                )
            
            # 結束會話
            session.end_session("演示對話結束")
            
            # 創建學習進度記錄
            for topic in ['人工智慧', '機器學習', '智慧家居']:
                LearningProgress.create(
                    student=student,
                    topic=topic,
                    skill_level=2 + (i % 3),  # 不同的技能等級
                    questions_asked=3 + j,
                    understanding_score=0.3 + (i * 0.2)
                )
        
        logger.info("✅ 演示資料創建完成")
        
    except Exception as e:
        logger.error(f"❌ 創建演示資料失敗: {e}")

def cleanup_database():
    """清理資料庫（生產環境慎用）"""
    try:
        logger.warning("⚠️ 開始清理資料庫...")
        
        # 清理演示資料
        demo_cleanup_results = Student.cleanup_demo_students()
        logger.info(f"清理演示學生: {demo_cleanup_results}")
        
        # 清理舊資料
        old_messages = Message.cleanup_old_messages(days_old=90)
        old_sessions = ConversationSession.cleanup_old_sessions(days_old=30)
        incomplete_registrations = Student.cleanup_incomplete_registrations(days_old=7)
        
        logger.info(f"✅ 資料庫清理完成 - 訊息: {old_messages}, 會話: {old_sessions}, 未完成註冊: {incomplete_registrations}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 資料庫清理失敗: {e}")
        return False

def get_database_stats():
    """取得資料庫統計資訊"""
    try:
        stats = {
            'total_students': Student.select().count(),
            'real_students': Student.get_real_students().count(),
            'demo_students': Student.get_demo_students().count(),
            'total_messages': Message.select().count(),
            'real_messages': Message.get_real_messages().count(),
            'demo_messages': Message.get_demo_messages().count(),
            'active_sessions': ConversationSession.get_active_sessions_count(),
            'total_sessions': ConversationSession.select().count(),
            'learning_records': LearningProgress.select().count()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ 取得資料庫統計失敗: {e}")
        return {}

# =================== 自動維護任務 ===================

def run_maintenance_tasks():
    """執行自動維護任務"""
    try:
        logger.info("🔧 開始執行維護任務...")
        
        # 自動結束非活躍會話
        ended_sessions = ConversationSession.auto_end_inactive_sessions(timeout_minutes=30)
        
        # 清理未完成的註冊（超過7天）
        incomplete_cleanup = Student.cleanup_incomplete_registrations(days_old=7)
        
        logger.info(f"✅ 維護任務完成 - 結束會話: {ended_sessions}, 清理註冊: {incomplete_cleanup}")
        
        return {
            'ended_sessions': ended_sessions,
            'incomplete_cleanup': incomplete_cleanup
        }
        
    except Exception as e:
        logger.error(f"❌ 維護任務執行失敗: {e}")
        return {}

# =================== 匯出所有模型 ===================

__all__ = [
    'db',
    'BaseModel', 
    'Student', 
    'ConversationSession', 
    'Message', 
    'LearningProgress',
    'initialize_database',
    'create_demo_data',
    'cleanup_database',
    'get_database_stats',
    'run_maintenance_tasks'
]

# =================== models.py 修正版 - 第4段結束 ===================

