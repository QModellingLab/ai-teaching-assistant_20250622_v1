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

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Railway/Heroku PostgreSQL 支援
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    db = PostgresqlDatabase(DATABASE_URL)
else:
    # 本地開發使用 SQLite
    db = SqliteDatabase('teaching_assistant.db')

class BaseModel(Model):
    """基礎模型類別"""
    class Meta:
        database = db

# =================== 學生模型（優化版，支援新註冊流程） ===================

class Student(BaseModel):
    """學生資料模型 - 優化版本，與app.py v4.0完全兼容"""
    
    # 基本資料
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, default='', verbose_name="姓名")
    line_user_id = CharField(max_length=100, unique=True, verbose_name="LINE用戶ID")
    
    # ✨ 學號欄位（支援新註冊流程）
    student_id = CharField(max_length=20, default='', verbose_name="學號")
    
    # ✨ 註冊流程追蹤（與app.py v4.0完全兼容）
    registration_step = IntegerField(default=0, verbose_name="註冊步驟")
    # 0=已完成註冊, 1=等待學號, 2=等待姓名, 3=等待確認
    
    # 保留必要欄位（向後相容）
    grade = CharField(max_length=20, null=True, default=None, verbose_name="年級") 
    
    # 簡化統計 - 只保留基本的
    message_count = IntegerField(default=0, verbose_name="訊息總數")
    
    # 時間戳記
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    last_active = DateTimeField(default=datetime.datetime.now, verbose_name="最後活動")
    is_active = BooleanField(default=True, verbose_name="是否活躍")
    
    class Meta:
        table_name = 'students'
        indexes = (
            (('line_user_id',), True),  # 唯一索引
            (('created_at',), False),   # 一般索引
            (('last_active',), False),
            (('registration_step',), False),  # 新增：註冊步驟索引
        )
    
    def __str__(self):
        return f"Student({self.name}, {self.student_id}, {self.line_user_id})"
    
    # =================== 演示學生相關屬性（保留向後相容） ===================
    
    @property
    def is_demo_student(self):
        """檢查是否為演示學生"""
        return (
            self.name.startswith('[DEMO]') or 
            self.line_user_id.startswith('demo_') or 
            self.name.startswith('學生_')
        )
    
    @property
    def is_real_student(self):
        """檢查是否為真實學生"""
        return not self.is_demo_student
    
    @classmethod
    def get_real_students(cls):
        """取得所有真實學生"""
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
        """清理所有演示學生"""
        try:
            demo_students = list(cls.get_demo_students())
            
            if not demo_students:
                return {
                    'success': True,
                    'students_deleted': 0,
                    'message': '沒有找到演示學生'
                }
            
            deleted_count = 0
            for student in demo_students:
                student.delete_instance(recursive=True)
                deleted_count += 1
            
            logger.info(f"成功清理 {deleted_count} 位演示學生")
            
            return {
                'success': True,
                'students_deleted': deleted_count,
                'message': f"成功清理 {deleted_count} 位演示學生"
            }
            
        except Exception as e:
            logger.error(f"清理演示學生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示學生時發生錯誤'
            }
    
    # =================== 基本查詢方法（優化版） ===================
    
    @classmethod
    def get_by_line_id(cls, line_user_id):
        """根據 LINE ID 取得學生"""
        try:
            return cls.select().where(cls.line_user_id == line_user_id).get()
        except cls.DoesNotExist:
            logger.info(f"找不到 LINE ID: {line_user_id} 的學生")
            return None
    
    @classmethod
    def get_by_id(cls, student_id):
        """根據 ID 取得學生"""
        try:
            return cls.select().where(cls.id == student_id).get()
        except cls.DoesNotExist:
            logger.warning(f"找不到 ID: {student_id} 的學生")
            return None
        except Exception as e:
            logger.error(f"❌ 取得學生失敗: {e}")
            return None
    
    @classmethod
    def get_or_none(cls, *args, **kwargs):
        """安全取得學生，不存在時回傳None（與app.py兼容）"""
        try:
            return cls.get(*args, **kwargs)
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"❌ 查詢學生失敗: {e}")
            return None
    
    @classmethod
    def create(cls, **data):
        """創建學生（覆寫以添加日誌和預設值）"""
        try:
            # 確保新學生有正確的預設值
            if 'registration_step' not in data:
                data['registration_step'] = 1  # 新學生從步驟1開始（等待學號）
            if 'created_at' not in data:
                data['created_at'] = datetime.datetime.now()
            if 'last_active' not in data:
                data['last_active'] = datetime.datetime.now()
            
            student = super().create(**data)
            logger.info(f"✅ 創建新學生: {student.name or '[待設定]'} (LINE ID: {student.line_user_id})")
            return student
        except Exception as e:
            logger.error(f"❌ 創建學生失敗: {e}")
            raise
    
    @classmethod
    def get_or_create(cls, **kwargs):
        """取得或創建學生"""
        try:
            defaults = kwargs.pop('defaults', {})
            
            # 嘗試取得現有學生
            try:
                instance = cls.get(**kwargs)
                return instance, False  # (學生物件, 是否為新創建)
            except cls.DoesNotExist:
                # 創建新學生
                create_data = kwargs.copy()
                create_data.update(defaults)
                instance = cls.create(**create_data)
                return instance, True  # (學生物件, 是否為新創建)
                
        except Exception as e:
            logger.error(f"❌ get_or_create 失敗: {e}")
            raise
    
    # =================== 註冊狀態管理（支援app.py新流程） ===================
    
    def is_registered(self):
        """檢查是否已完成註冊（與app.py兼容）"""
        return self.registration_step == 0 and self.name and self.student_id
    
    def needs_registration(self):
        """檢查是否需要註冊（與app.py兼容）"""
        return self.registration_step > 0 or not self.name or not self.student_id
    
    def get_registration_status(self):
        """取得詳細註冊狀態"""
        if self.registration_step == 0 and self.name and self.student_id:
            return "已完成"
        elif self.registration_step == 1:
            return "等待學號"
        elif self.registration_step == 2:
            return "等待姓名"
        elif self.registration_step == 3:
            return "等待確認"
        else:
            return "需要重新註冊"
    
    def reset_registration(self):
        """重設註冊狀態"""
        self.registration_step = 1
        self.name = ""
        self.student_id = ""
        self.save()
        logger.info(f"重設學生 {self.line_user_id} 的註冊狀態")
    
    # =================== 活動和統計管理（簡化版） ===================
    
    def update_activity(self):
        """更新學生活動狀態"""
        try:
            self.last_active = datetime.datetime.now()
            self.save()
            logger.debug(f"更新學生 {self.name} 活動時間")
        except Exception as e:
            logger.error(f"❌ 更新活動狀態失敗: {e}")
    
    def update_message_count(self):
        """更新訊息計數（簡化版）"""
        try:
            # 計算該學生的總訊息數
            self.message_count = Message.select().where(Message.student == self).count()
            self.save()
            logger.debug(f"更新學生 {self.name} 訊息計數: {self.message_count}")
        except Exception as e:
            logger.error(f"❌ 更新訊息計數失敗: {e}")
    
    def get_activity_status(self):
        """取得活動狀態（簡化版）"""
        if not self.last_active:
            return "從未活動"
        
        time_diff = datetime.datetime.now() - self.last_active
        
        if time_diff.days == 0:
            return "今天活躍"
        elif time_diff.days <= 7:
            return "本週活躍"
        else:
            return f"{time_diff.days}天前"
    
    def get_conversation_count(self):
        """取得對話總數"""
        try:
            return Message.select().where(Message.student == self).count()
        except Exception as e:
            logger.error(f"❌ 取得對話數失敗: {e}")
            return 0
    
    def get_days_since_created(self):
        """取得註冊天數"""
        if not self.created_at:
            return 0
        return (datetime.datetime.now() - self.created_at).days
    
    # =================== 會話相關方法（新增） ===================
    
    def get_active_session(self):
        """取得目前的活躍會話"""
        try:
            return ConversationSession.select().where(
                ConversationSession.student == self,
                ConversationSession.session_end.is_null()
            ).order_by(ConversationSession.session_start.desc()).first()
        except Exception as e:
            logger.error(f"❌ 取得活躍會話失敗: {e}")
            return None
    
    def start_new_session(self, topic_hint=None):
        """開始新的對話會話"""
        try:
            # 先結束任何現有的活躍會話
            active_session = self.get_active_session()
            if active_session:
                active_session.end_session()
            
            # 創建新會話
            session = ConversationSession.create(
                student=self,
                session_start=datetime.datetime.now(),
                topic_hint=topic_hint or ''
            )
            logger.info(f"✅ 學生 {self.name} 開始新會話 (ID: {session.id})")
            return session
        except Exception as e:
            logger.error(f"❌ 開始新會話失敗: {e}")
            return None
    
    def get_recent_sessions(self, limit=5):
        """取得最近的對話會話"""
        try:
            return list(ConversationSession.select().where(
                ConversationSession.student == self
            ).order_by(ConversationSession.session_start.desc()).limit(limit))
        except Exception as e:
            logger.error(f"❌ 取得最近會話失敗: {e}")
            return []
    
    def get_session_count(self):
        """取得總會話次數"""
        try:
            return ConversationSession.select().where(ConversationSession.student == self).count()
        except Exception as e:
            logger.error(f"❌ 取得會話次數失敗: {e}")
            return 0

# =================== models.py 修正版 - 第1段結束 ===================

# =================== models.py 修正版 - 第2段開始 ===================
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
            # 規範化來源類型（與app.py兼容）
            if 'source_type' in data:
                source = data['source_type']
                if source == 'line':
                    data['source_type'] = 'student'  # 統一使用'student'
            
            # 處理會話關聯
            if 'session' not in data or data['session'] is None:
                student = data.get('student')
                if student and data.get('source_type') == 'student':
                    # 如果是學生訊息，嘗試關聯到活躍會話或創建新會話
                    active_session = student.get_active_session()
                    if not active_session:
                        # 如果沒有活躍會話，創建新會話
                        active_session = student.start_new_session()
                    
                    if active_session:
                        data['session'] = active_session
            
            message = super().create(**data)
            logger.debug(f"創建訊息: {message.student.name} - {message.source_type}")
            
            # 自動更新學生的活動時間和訊息計數
            try:
                student = message.student
                student.update_activity()
                student.update_message_count()
            except Exception as e:
                logger.warning(f"更新學生統計失敗: {e}")
            
            # 🔧 **關鍵修正：使用修正版的 update_session_stats 方法**
            if message.session:
                try:
                    message.session.update_session_stats()
                except Exception as e:
                    logger.warning(f"更新會話統計失敗: {e}")
                    # 不要因為統計更新失敗而影響訊息創建
            
            return message
        except Exception as e:
            logger.error(f"❌ 創建訊息失敗: {e}")
            raise
    
    def add_topic_tags(self, tags):
        """添加主題標籤"""
        try:
            if isinstance(tags, list):
                new_tags = ','.join(tags)
            else:
                new_tags = str(tags)
            
            if self.topic_tags:
                existing_tags = set(self.topic_tags.split(','))
                new_tags_set = set(new_tags.split(','))
                combined_tags = existing_tags.union(new_tags_set)
                self.topic_tags = ','.join(combined_tags)
            else:
                self.topic_tags = new_tags
            
            self.save()
            logger.debug(f"更新訊息主題標籤: {self.topic_tags}")
        except Exception as e:
            logger.error(f"❌ 添加主題標籤失敗: {e}")
    
    def get_topic_tags_list(self):
        """取得主題標籤列表"""
        if not self.topic_tags:
            return []
        return [tag.strip() for tag in self.topic_tags.split(',') if tag.strip()]
    
    def set_ai_response(self, response_text):
        """設定AI回應"""
        try:
            self.ai_response = response_text
            self.save()
            logger.debug(f"設定AI回應長度: {len(response_text)} 字")
        except Exception as e:
            logger.error(f"❌ 設定AI回應失敗: {e}")
    
    # =================== 對話上下文功能（記憶功能核心） ===================
    
    @classmethod
    def get_conversation_context(cls, student, limit=5):
        """
        取得學生的對話上下文（用於記憶功能）- 修正版
        這是app.py中需要調用的核心記憶功能方法
        """
        try:
            recent_messages = list(cls.select().where(
                cls.student == student
            ).order_by(cls.timestamp.desc()).limit(limit))
            
            context = {
                'recent_topics': [],
                'conversation_flow': [],
                'session_info': None
            }
            
            for msg in reversed(recent_messages):  # 按時間順序排列
                context['conversation_flow'].append({
                    'content': msg.content,
                    'ai_response': msg.ai_response,
                    'timestamp': msg.timestamp.isoformat(),
                    'source_type': msg.source_type,
                    'topic_tags': msg.get_topic_tags_list()
                })
                
                # 收集主題標籤
                context['recent_topics'].extend(msg.get_topic_tags_list())
            
            # 去重並保留最近的主題
            context['recent_topics'] = list(dict.fromkeys(context['recent_topics']))[-10:]
            
            # 取得目前會話資訊
            if recent_messages:
                latest_session = recent_messages[0].session
                if latest_session and latest_session.is_active():
                    context['session_info'] = {
                        'session_id': latest_session.id,
                        'start_time': latest_session.session_start.isoformat(),
                        'topic_hint': latest_session.topic_hint,
                        'message_count': latest_session.message_count
                    }
            
            return context
            
        except Exception as e:
            logger.error(f"❌ 取得對話上下文失敗: {e}")
            return {
                'recent_topics': [],
                'conversation_flow': [],
                'session_info': None
            }

# =================== models.py 修正版 - 第2段結束 ===================

# =================== models.py 修正版 - 第3段開始 ===================
# 接續第2段，包含：學習歷程模型、分析模型

# =================== 學習歷程模型（新增） ===================

class LearningHistory(BaseModel):
    """學習歷程模型 - 記錄學生的學習歷程和發展軌跡"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='learning_histories', verbose_name="學生")
    
    # 學習歷程內容
    topics_discussed = TextField(default='{}', verbose_name="討論主題（JSON格式）")
    learning_progression = TextField(default='{}', verbose_name="學習軌跡（JSON格式）")
    key_interactions = TextField(default='{}', verbose_name="關鍵互動（JSON格式）")
    depth_analysis = TextField(verbose_name="深度分析文本")
    
    # 統計資訊
    total_sessions = IntegerField(default=0, verbose_name="總會話次數")
    total_messages = IntegerField(default=0, verbose_name="總訊息數")
    analysis_period_start = DateTimeField(verbose_name="分析期間開始")
    analysis_period_end = DateTimeField(verbose_name="分析期間結束")
    
    # 元資料
    generated_at = DateTimeField(default=datetime.datetime.now, verbose_name="生成時間")
    generated_by = CharField(max_length=50, default='system', verbose_name="生成者")
    version = CharField(max_length=10, default='1.0', verbose_name="版本")
    
    class Meta:
        table_name = 'learning_histories'
        indexes = (
            (('student', 'generated_at'), False),
            (('generated_at',), False),
            (('student',), False),
        )
    
    def __str__(self):
        return f"LearningHistory({self.student.name}, {self.generated_at})"
    
    def set_topics_discussed(self, topics_data):
        """設定討論主題資料"""
        try:
            if isinstance(topics_data, dict):
                self.topics_discussed = json.dumps(topics_data, ensure_ascii=False)
            else:
                self.topics_discussed = str(topics_data)
            self.save()
            logger.debug(f"設定學習歷程主題資料")
        except Exception as e:
            logger.error(f"❌ 設定主題資料失敗: {e}")
    
    def get_topics_discussed(self):
        """取得討論主題資料"""
        try:
            if self.topics_discussed:
                return json.loads(self.topics_discussed)
            return {}
        except Exception as e:
            logger.error(f"❌ 解析主題資料失敗: {e}")
            return {}
    
    def set_learning_progression(self, progression_data):
        """設定學習軌跡資料"""
        try:
            if isinstance(progression_data, dict):
                self.learning_progression = json.dumps(progression_data, ensure_ascii=False)
            else:
                self.learning_progression = str(progression_data)
            self.save()
            logger.debug(f"設定學習軌跡資料")
        except Exception as e:
            logger.error(f"❌ 設定學習軌跡失敗: {e}")
    
    def get_learning_progression(self):
        """取得學習軌跡資料"""
        try:
            if self.learning_progression:
                return json.loads(self.learning_progression)
            return {}
        except Exception as e:
            logger.error(f"❌ 解析學習軌跡失敗: {e}")
            return {}
    
    def set_key_interactions(self, interactions_data):
        """設定關鍵互動資料"""
        try:
            if isinstance(interactions_data, dict):
                self.key_interactions = json.dumps(interactions_data, ensure_ascii=False)
            else:
                self.key_interactions = str(interactions_data)
            self.save()
            logger.debug(f"設定關鍵互動資料")
        except Exception as e:
            logger.error(f"❌ 設定關鍵互動失敗: {e}")
    
    def get_key_interactions(self):
        """取得關鍵互動資料"""
        try:
            if self.key_interactions:
                return json.loads(self.key_interactions)
            return {}
        except Exception as e:
            logger.error(f"❌ 解析關鍵互動失敗: {e}")
            return {}
    
    def update_statistics(self):
        """更新統計資訊"""
        try:
            # 計算學生的總會話次數和訊息數
            self.total_sessions = ConversationSession.select().where(
                ConversationSession.student == self.student
            ).count()
            
            self.total_messages = Message.select().where(
                Message.student == self.student
            ).count()
            
            # 設定分析期間
            if not self.analysis_period_start:
                first_message = Message.select().where(
                    Message.student == self.student
                ).order_by(Message.timestamp).first()
                if first_message:
                    self.analysis_period_start = first_message.timestamp
                else:
                    self.analysis_period_start = datetime.datetime.now()
            
            self.analysis_period_end = datetime.datetime.now()
            self.save()
            
            logger.debug(f"更新學習歷程統計: {self.total_sessions} 會話, {self.total_messages} 訊息")
        except Exception as e:
            logger.error(f"❌ 更新統計資訊失敗: {e}")
    
    def get_analysis_summary(self):
        """取得分析摘要"""
        return {
            'student_name': self.student.name,
            'student_id': getattr(self.student, 'student_id', ''),
            'total_sessions': self.total_sessions,
            'total_messages': self.total_messages,
            'analysis_period': {
                'start': self.analysis_period_start.isoformat() if self.analysis_period_start else None,
                'end': self.analysis_period_end.isoformat() if self.analysis_period_end else None,
                'days': (self.analysis_period_end - self.analysis_period_start).days if self.analysis_period_start and self.analysis_period_end else 0
            },
            'topics_discussed': self.get_topics_discussed(),
            'learning_progression': self.get_learning_progression(),
            'key_interactions': self.get_key_interactions(),
            'generated_at': self.generated_at.isoformat(),
            'version': self.version
        }
    
    @classmethod
    def get_latest_for_student(cls, student):
        """取得學生的最新學習歷程"""
        try:
            return cls.select().where(
                cls.student == student
            ).order_by(cls.generated_at.desc()).first()
        except Exception as e:
            logger.error(f"❌ 取得最新學習歷程失敗: {e}")
            return None
    
    @classmethod
    def cleanup_old_histories(cls, keep_latest=3, days_old=90):
        """清理過舊的學習歷程記錄"""
        try:
            deleted_count = 0
            
            # 為每個學生保留最新的N個記錄
            students = Student.select()
            for student in students:
                histories = list(cls.select().where(
                    cls.student == student
                ).order_by(cls.generated_at.desc()))
                
                # 刪除超過保留數量的記錄
                if len(histories) > keep_latest:
                    for history in histories[keep_latest:]:
                        history.delete_instance()
                        deleted_count += 1
            
            # 額外刪除非常舊的記錄
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
            old_deleted = cls.delete().where(
                cls.generated_at < cutoff_date
            ).execute()
            deleted_count += old_deleted
            
            if deleted_count > 0:
                logger.info(f"✅ 清理了 {deleted_count} 個舊學習歷程記錄")
            
            return deleted_count
        except Exception as e:
            logger.error(f"❌ 清理舊學習歷程失敗: {e}")
            return 0

# =================== 分析模型（保留但簡化） ===================

class Analysis(BaseModel):
    """分析模型 - 保留但簡化，主要用於向後相容"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='analyses', verbose_name="學生")
    analysis_type = CharField(max_length=50, verbose_name="分析類型")
    analysis_data = TextField(verbose_name="分析資料")
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    
    class Meta:
        table_name = 'analyses'
        indexes = (
            (('student', 'analysis_type'), False),
            (('analysis_type',), False),
            (('created_at',), False),
        )
    
    def __str__(self):
        return f"Analysis({self.student.name}, {self.analysis_type}, {self.created_at})"
    
    @property
    def is_demo_analysis(self):
        """檢查是否為演示分析"""
        return self.student.is_demo_student
    
    @property
    def is_real_analysis(self):
        """檢查是否為真實分析"""
        return not self.is_demo_analysis
    
    @classmethod
    def get_real_analyses(cls):
        """取得所有真實分析"""
        return cls.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_')) &
            (~Student.name.startswith('學生_'))
        )
    
    @classmethod
    def get_demo_analyses(cls):
        """取得所有演示分析"""
        return cls.select().join(Student).where(
            (Student.name.startswith('[DEMO]')) |
            (Student.line_user_id.startswith('demo_')) |
            (Student.name.startswith('學生_'))
        )
    
    @classmethod
    def cleanup_demo_analyses(cls):
        """清理所有演示分析"""
        try:
            demo_analyses = list(cls.get_demo_analyses())
            
            if not demo_analyses:
                return {
                    'success': True,
                    'analyses_deleted': 0,
                    'message': '沒有找到演示分析記錄'
                }
            
            deleted_count = 0
            for analysis in demo_analyses:
                analysis.delete_instance()
                deleted_count += 1
            
            logger.info(f"成功清理 {deleted_count} 個演示分析記錄")
            
            return {
                'success': True,
                'analyses_deleted': deleted_count,
                'message': f"成功清理 {deleted_count} 個演示分析記錄"
            }
            
        except Exception as e:
            logger.error(f"清理演示分析錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示分析時發生錯誤'
            }

# =================== models.py 修正版 - 第3段結束 ===================

# =================== models.py 修正版 - 第4段開始 ===================
# 接續第3段，包含：資料庫初始化、遷移、管理功能

# =================== 資料庫初始化和管理 ===================

def initialize_db():
    """初始化資料庫（包含新增的會話和學習歷程表）"""
    try:
        # 連接資料庫
        if db.is_closed():
            db.connect()
            logger.info("✅ 資料庫連接建立")
        
        # 創建所有表格（包含新增的表格）
        db.create_tables([
            Student, Message, Analysis,           # 原有表格
            ConversationSession, LearningHistory  # 新增表格
        ], safe=True)
        logger.info("✅ 資料庫表格初始化完成（包含會話和學習歷程表）")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        return False

def close_db():
    """關閉資料庫連接"""
    try:
        if not db.is_closed():
            db.close()
            logger.info("✅ 資料庫連接已關閉")
    except Exception as e:
        logger.error(f"❌ 關閉資料庫連接失敗: {e}")

# =================== 資料庫遷移功能（增強版） ===================

def migrate_database():
    """資料庫遷移 - 添加新欄位和新表格，支援記憶功能和學習歷程"""
    try:
        logger.info("🔄 開始資料庫遷移（支援記憶功能和學習歷程）...")
        
        # === 原有欄位遷移（保持向後相容） ===
        
        # 檢查並添加 student_id 欄位
        try:
            if isinstance(db, SqliteDatabase):
                db.execute_sql('ALTER TABLE students ADD COLUMN student_id VARCHAR(20) DEFAULT ""')
            else:
                db.execute_sql('ALTER TABLE students ADD COLUMN student_id VARCHAR(20) DEFAULT ""')
            logger.info("✅ 成功添加 student_id 欄位")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                logger.info("✅ student_id 欄位已經存在")
            else:
                logger.warning(f"⚠️ 添加 student_id 欄位時出現問題: {e}")
        
        # 檢查並添加 registration_step 欄位
        try:
            if isinstance(db, SqliteDatabase):
                db.execute_sql('ALTER TABLE students ADD COLUMN registration_step INTEGER DEFAULT 0')
            else:
                db.execute_sql('ALTER TABLE students ADD COLUMN registration_step INTEGER DEFAULT 0')
            logger.info("✅ 成功添加 registration_step 欄位")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                logger.info("✅ registration_step 欄位已經存在")
            else:
                logger.warning(f"⚠️ 添加 registration_step 欄位時出現問題: {e}")
        
        # 檢查並添加 grade 欄位（向後相容）
        try:
            if isinstance(db, SqliteDatabase):
                db.execute_sql('ALTER TABLE students ADD COLUMN grade VARCHAR(20)')
            else:
                db.execute_sql('ALTER TABLE students ADD COLUMN grade VARCHAR(20)')
            logger.info("✅ 成功添加 grade 欄位")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                logger.info("✅ grade 欄位已經存在")
            else:
                logger.warning(f"⚠️ 添加 grade 欄位時出現問題: {e}")
        
        # === 新增欄位遷移（記憶功能相關） ===
        
        # 為 messages 表添加 session 欄位
        try:
            if isinstance(db, SqliteDatabase):
                db.execute_sql('ALTER TABLE messages ADD COLUMN session_id INTEGER')
            else:
                db.execute_sql('ALTER TABLE messages ADD COLUMN session_id INTEGER REFERENCES conversation_sessions(id)')
            logger.info("✅ 成功添加 messages.session_id 欄位")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                logger.info("✅ messages.session_id 欄位已經存在")
            else:
                logger.warning(f"⚠️ 添加 messages.session_id 欄位時出現問題: {e}")
        
        # 為 messages 表添加 topic_tags 欄位
        try:
            if isinstance(db, SqliteDatabase):
                db.execute_sql('ALTER TABLE messages ADD COLUMN topic_tags VARCHAR(500) DEFAULT ""')
            else:
                db.execute_sql('ALTER TABLE messages ADD COLUMN topic_tags VARCHAR(500) DEFAULT ""')
            logger.info("✅ 成功添加 messages.topic_tags 欄位")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                logger.info("✅ messages.topic_tags 欄位已經存在")
            else:
                logger.warning(f"⚠️ 添加 messages.topic_tags 欄位時出現問題: {e}")
        
        # 為 messages 表添加 ai_response 欄位
        try:
            if isinstance(db, SqliteDatabase):
                db.execute_sql('ALTER TABLE messages ADD COLUMN ai_response TEXT')
            else:
                db.execute_sql('ALTER TABLE messages ADD COLUMN ai_response TEXT')
            logger.info("✅ 成功添加 messages.ai_response 欄位")
        except Exception as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                logger.info("✅ messages.ai_response 欄位已經存在")
            else:
                logger.warning(f"⚠️ 添加 messages.ai_response 欄位時出現問題: {e}")
        
        # === 新表格創建 ===
        
        # 創建新表格（如果不存在）
        try:
            db.create_tables([ConversationSession, LearningHistory], safe=True)
            logger.info("✅ 成功創建新表格（會話和學習歷程）")
        except Exception as e:
            logger.warning(f"⚠️ 創建新表格時出現問題: {e}")
        
        # === 資料一致性更新 ===
        
        # 更新現有學生記錄的預設值
        try:
            # 為沒有 student_id 的學生設定空字串
            Student.update(student_id='').where(
                (Student.student_id.is_null()) | (Student.student_id == None)
            ).execute()
            
            # 為沒有 registration_step 的學生設定為已完成註冊（0）
            Student.update(registration_step=0).where(
                (Student.registration_step.is_null()) | (Student.registration_step == None)
            ).execute()
            
            # 為沒有 topic_tags 的訊息設定空字串
            try:
                Message.update(topic_tags='').where(
                    (Message.topic_tags.is_null()) | (Message.topic_tags == None)
                ).execute()
            except:
                pass  # 如果欄位不存在就跳過
            
            logger.info("✅ 現有記錄已更新預設值")
        except Exception as e:
            logger.warning(f"⚠️ 更新現有記錄時出現問題: {e}")
        
        logger.info("✅ 資料庫遷移完成（支援記憶功能和學習歷程）")
        return True
        
    except Exception as e:
        logger.error(f"❌ 資料庫遷移失敗: {e}")
        return False

def reset_registration_for_incomplete_students():
    """重設不完整註冊的學生（支援新註冊流程）"""
    try:
        # 找出姓名或學號為空的學生，設定為需要重新註冊
        incomplete_students = Student.update(registration_step=1).where(
            (Student.name == '') | (Student.student_id == '') |
            (Student.name.is_null()) | (Student.student_id.is_null())
        ).execute()
        
        if incomplete_students > 0:
            logger.info(f"✅ 重設了 {incomplete_students} 位學生的註冊狀態")
        
        return incomplete_students
        
    except Exception as e:
        logger.error(f"❌ 重設註冊狀態失敗: {e}")
        return 0

# =================== 會話管理功能（新增） ===================

def manage_conversation_sessions():
    """管理對話會話，自動清理和結束非活躍會話"""
    try:
        # 自動結束非活躍會話（30分鐘無活動）
        ended_count = ConversationSession.auto_end_inactive_sessions(timeout_minutes=30)
        
        # 清理過舊的會話記錄（30天前）
        cleaned_count = ConversationSession.cleanup_old_sessions(days_old=30)
        
        return {
            'ended_sessions': ended_count,
            'cleaned_sessions': cleaned_count,
            'message': f'結束了 {ended_count} 個非活躍會話，清理了 {cleaned_count} 個舊會話'
        }
    except Exception as e:
        logger.error(f"❌ 會話管理失敗: {e}")
        return {'error': str(e)}

# =================== 學習歷程管理功能（新增） ===================

def manage_learning_histories():
    """管理學習歷程記錄"""
    try:
        # 清理過舊的學習歷程（保留每位學生最新3個，清理90天前的記錄）
        cleaned_count = LearningHistory.cleanup_old_histories(keep_latest=3, days_old=90)
        
        return {
            'cleaned_histories': cleaned_count,
            'message': f'清理了 {cleaned_count} 個舊學習歷程記錄'
        }
    except Exception as e:
        logger.error(f"❌ 學習歷程管理失敗: {e}")
        return {'error': str(e)}

# =================== 資料庫統計功能（增強版） ===================

def get_database_stats():
    """取得資料庫統計資訊（增強版，包含會話和學習歷程統計）"""
    try:
        stats = {
            'students': {
                'total': Student.select().count(),
                'real': Student.get_real_students().count(),
                'demo': Student.get_demo_students().count(),
                'registered': Student.select().where(Student.registration_step == 0).count(),
                'need_registration': Student.select().where(Student.registration_step > 0).count(),
            },
            'messages': {
                'total': Message.select().count(),
                'real': Message.get_real_messages().count(),
                'demo': Message.get_demo_messages().count(),
                'student_messages': Message.select().where(Message.source_type.in_(['line', 'student'])).count(),
                'ai_messages': Message.select().where(Message.source_type == 'ai').count(),
            },
            'analyses': {
                'total': Analysis.select().count(),
                'real': Analysis.get_real_analyses().count(),
                'demo': Analysis.get_demo_analyses().count(),
            },
            # 新增：會話統計
            'conversation_sessions': {
                'total': 0,
                'active': 0,
                'completed': 0,
                'avg_duration_minutes': 0
            },
            # 新增：學習歷程統計
            'learning_histories': {
                'total': 0,
                'students_with_history': 0,
                'latest_generation': None
            }
        }
        
        # 計算活躍學生（7天內有活動）
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        stats['students']['active_this_week'] = Student.select().where(
            Student.last_active.is_null(False) & 
            (Student.last_active >= week_ago)
        ).count()
        
        # 計算會話統計
        try:
            total_sessions = ConversationSession.select().count()
            active_sessions = ConversationSession.select().where(
                ConversationSession.session_end.is_null()
            ).count()
            completed_sessions = total_sessions - active_sessions
            
            stats['conversation_sessions'].update({
                'total': total_sessions,
                'active': active_sessions,
                'completed': completed_sessions
            })
            
            # 計算平均會話時間
            if completed_sessions > 0:
                completed_session_objects = ConversationSession.select().where(
                    ConversationSession.session_end.is_null(False)
                ).limit(100)  # 取樣本計算
                
                total_duration = 0
                count = 0
                for session in completed_session_objects:
                    duration = session.get_duration_minutes()
                    if duration > 0:
                        total_duration += duration
                        count += 1
                
                if count > 0:
                    stats['conversation_sessions']['avg_duration_minutes'] = round(total_duration / count, 1)
        except Exception as e:
            logger.warning(f"計算會話統計失敗: {e}")
        
        # 計算學習歷程統計
        try:
            total_histories = LearningHistory.select().count()
            students_with_history = LearningHistory.select(
                LearningHistory.student
            ).distinct().count()
            
            latest_history = LearningHistory.select().order_by(
                LearningHistory.generated_at.desc()
            ).first()
            
            stats['learning_histories'].update({
                'total': total_histories,
                'students_with_history': students_with_history,
                'latest_generation': latest_history.generated_at.isoformat() if latest_history else None
            })
        except Exception as e:
            logger.warning(f"計算學習歷程統計失敗: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ 取得資料庫統計失敗: {e}")
        return {
            'students': {'total': 0, 'real': 0, 'demo': 0, 'registered': 0, 'need_registration': 0, 'active_this_week': 0},
            'messages': {'total': 0, 'real': 0, 'demo': 0, 'student_messages': 0, 'ai_messages': 0},
            'analyses': {'total': 0, 'real': 0, 'demo': 0},
            'conversation_sessions': {'total': 0, 'active': 0, 'completed': 0, 'avg_duration_minutes': 0},
            'learning_histories': {'total': 0, 'students_with_history': 0, 'latest_generation': None}
        }

def cleanup_all_demo_data():
    """清理所有演示資料（包含新增的會話和學習歷程）"""
    try:
        logger.info("🧹 開始清理所有演示資料...")
        
        results = {}
        
        # 清理演示訊息
        message_result = Message.cleanup_demo_messages()
        results['messages'] = message_result
        
        # 清理演示分析
        analysis_result = Analysis.cleanup_demo_analyses()
        results['analyses'] = analysis_result
        
        # 清理演示學生的會話記錄
        try:
            demo_students = list(Student.get_demo_students())
            demo_sessions_deleted = 0
            demo_histories_deleted = 0
            
            for student in demo_students:
                # 刪除該學生的會話記錄
                student_sessions = ConversationSession.delete().where(
                    ConversationSession.student == student
                ).execute()
                demo_sessions_deleted += student_sessions
                
                # 刪除該學生的學習歷程
                student_histories = LearningHistory.delete().where(
                    LearningHistory.student == student
                ).execute()
                demo_histories_deleted += student_histories
            
            results['sessions'] = {
                'success': True,
                'sessions_deleted': demo_sessions_deleted,
                'message': f"成功清理 {demo_sessions_deleted} 個演示會話記錄"
            }
            
            results['histories'] = {
                'success': True,
                'histories_deleted': demo_histories_deleted,
                'message': f"成功清理 {demo_histories_deleted} 個演示學習歷程"
            }
            
        except Exception as e:
            logger.error(f"清理演示會話和學習歷程失敗: {e}")
            results['sessions'] = {'success': False, 'error': str(e)}
            results['histories'] = {'success': False, 'error': str(e)}
        
        # 清理演示學生（最後執行）
        student_result = Student.cleanup_demo_students()
        results['students'] = student_result
        
        total_cleaned = {
            'students': results['students'].get('students_deleted', 0),
            'messages': results['messages'].get('total_deleted', 0),
            'analyses': results['analyses'].get('analyses_deleted', 0),
            'sessions': results.get('sessions', {}).get('sessions_deleted', 0),
            'histories': results.get('histories', {}).get('histories_deleted', 0)
        }
        
        logger.info(f"✅ 演示資料清理完成: {total_cleaned}")
        
        return {
            'success': True,
            'total_cleaned': total_cleaned,
            'details': results,
            'message': f"成功清理演示資料：{total_cleaned['students']}位學生，{total_cleaned['messages']}則訊息，{total_cleaned['analyses']}項分析，{total_cleaned['sessions']}個會話，{total_cleaned['histories']}個學習歷程"
        }
        
    except Exception as e:
        logger.error(f"❌ 清理演示資料失敗: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': '清理演示資料時發生錯誤'
        }

# =================== models.py 修正版 - 第4段結束 ===================

# =================== models.py 修正版 - 第5段開始 ===================
# 接續第4段，包含：資料驗證、修復功能、相容性和初始化

# =================== 資料驗證和修復功能（增強版） ===================

def validate_database_integrity():
    """驗證資料庫完整性（包含新增的會話和學習歷程檢查）"""
    try:
        validation_report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': 'healthy',
            'issues': [],
            'recommendations': [],
            'stats': {}
        }
        
        # === 學生資料檢查 ===
        students = list(Student.select())
        missing_name = sum(1 for s in students if not s.name)
        missing_student_id = sum(1 for s in students if not getattr(s, 'student_id', ''))
        incomplete_registration = sum(1 for s in students if s.registration_step > 0)
        
        validation_report['stats']['students'] = {
            'total': len(students),
            'missing_name': missing_name,
            'missing_student_id': missing_student_id,
            'incomplete_registration': incomplete_registration
        }
        
        if missing_name > 0:
            validation_report['issues'].append(f'{missing_name} 位學生缺少姓名')
            validation_report['recommendations'].append('使用 reset_registration_for_incomplete_students() 重設註冊狀態')
        
        if missing_student_id > 0:
            validation_report['issues'].append(f'{missing_student_id} 位學生缺少學號')
        
        if incomplete_registration > 0:
            validation_report['issues'].append(f'{incomplete_registration} 位學生尚未完成註冊')
        
        # === 訊息資料檢查 ===
        messages = Message.select().count()
        try:
            orphaned_messages = Message.select().join(Student, join_type='LEFT OUTER').where(Student.id.is_null()).count()
        except:
            orphaned_messages = 0
        
        # 檢查會話關聯
        try:
            messages_without_session = Message.select().where(
                Message.source_type == 'student',
                Message.session.is_null()
            ).count()
        except:
            messages_without_session = 0
        
        validation_report['stats']['messages'] = {
            'total': messages,
            'orphaned': orphaned_messages,
            'without_session': messages_without_session
        }
        
        if orphaned_messages > 0:
            validation_report['issues'].append(f'{orphaned_messages} 則訊息缺少對應學生')
            validation_report['recommendations'].append('清理孤立的訊息記錄')
        
        if messages_without_session > 0:
            validation_report['issues'].append(f'{messages_without_session} 則學生訊息未關聯到會話')
            validation_report['recommendations'].append('為學生訊息創建會話關聯')
        
        # === 會話資料檢查 ===
        try:
            total_sessions = ConversationSession.select().count()
            active_sessions = ConversationSession.select().where(
                ConversationSession.session_end.is_null()
            ).count()
            
            # 檢查過長的活躍會話
            long_active_sessions = ConversationSession.select().where(
                ConversationSession.session_end.is_null(),
                ConversationSession.session_start < (datetime.datetime.now() - datetime.timedelta(hours=24))
            ).count()
            
            validation_report['stats']['sessions'] = {
                'total': total_sessions,
                'active': active_sessions,
                'long_active': long_active_sessions
            }
            
            if long_active_sessions > 0:
                validation_report['issues'].append(f'{long_active_sessions} 個會話活躍時間超過24小時')
                validation_report['recommendations'].append('使用 manage_conversation_sessions() 清理長時間活躍的會話')
        
        except Exception as e:
            validation_report['stats']['sessions'] = {'error': str(e)}
        
        # === 學習歷程資料檢查 ===
        try:
            total_histories = LearningHistory.select().count()
            students_with_multiple_histories = LearningHistory.select(
                LearningHistory.student
            ).group_by(LearningHistory.student).having(
                fn.COUNT(LearningHistory.id) > 5
            ).count()
            
            validation_report['stats']['learning_histories'] = {
                'total': total_histories,
                'students_with_multiple': students_with_multiple_histories
            }
            
            if students_with_multiple_histories > 0:
                validation_report['issues'].append(f'{students_with_multiple_histories} 位學生有超過5個學習歷程記錄')
                validation_report['recommendations'].append('使用 manage_learning_histories() 清理過多的學習歷程記錄')
        
        except Exception as e:
            validation_report['stats']['learning_histories'] = {'error': str(e)}
        
        # === 決定整體狀態 ===
        if validation_report['issues']:
            validation_report['overall_status'] = 'warning'
        
        if not validation_report['recommendations']:
            validation_report['recommendations'].append('資料庫狀態良好')
        
        return validation_report
        
    except Exception as e:
        logger.error(f"❌ 資料庫完整性檢查失敗: {e}")
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }

def fix_database_issues():
    """修復常見的資料庫問題（包含新增功能的修復）"""
    try:
        fix_report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'fixes_applied': [],
            'errors': []
        }
        
        # === 修復1：清理孤立的訊息 ===
        try:
            orphaned_count = Message.delete().join(Student, join_type='LEFT OUTER').where(Student.id.is_null()).execute()
            if orphaned_count > 0:
                fix_report['fixes_applied'].append(f'清理了 {orphaned_count} 則孤立訊息')
        except Exception as e:
            fix_report['errors'].append(f'清理孤立訊息失敗: {str(e)}')
        
        # === 修復2：重設不完整的註冊 ===
        try:
            reset_count = reset_registration_for_incomplete_students()
            if reset_count > 0:
                fix_report['fixes_applied'].append(f'重設了 {reset_count} 位學生的註冊狀態')
        except Exception as e:
            fix_report['errors'].append(f'重設註冊狀態失敗: {str(e)}')
        
        # === 修復3：更新訊息計數 ===
        try:
            students = Student.select()
            updated_count = 0
            for student in students:
                old_count = student.message_count
                student.update_message_count()
                if student.message_count != old_count:
                    updated_count += 1
            
            if updated_count > 0:
                fix_report['fixes_applied'].append(f'更新了 {updated_count} 位學生的訊息計數')
        except Exception as e:
            fix_report['errors'].append(f'更新訊息計數失敗: {str(e)}')
        
        # === 修復4：為學生訊息創建會話關聯 ===
        try:
            messages_without_session = Message.select().where(
                Message.source_type == 'student',
                Message.session.is_null()
            )
            
            created_sessions = 0
            current_student = None
            current_session = None
            
            for message in messages_without_session.order_by(Message.student, Message.timestamp):
                if message.student != current_student:
                    # 為新學生創建新會話
                    current_student = message.student
                    current_session = ConversationSession.create(
                        student=current_student,
                        session_start=message.timestamp,
                        topic_hint='歷史訊息會話'
                    )
                    created_sessions += 1
                
                # 關聯訊息到會話
                message.session = current_session
                message.save()
            
            if created_sessions > 0:
                fix_report['fixes_applied'].append(f'為歷史訊息創建了 {created_sessions} 個會話')
        except Exception as e:
            fix_report['errors'].append(f'創建會話關聯失敗: {str(e)}')
        
        # === 修復5：自動結束長時間活躍的會話 ===
        try:
            session_management = manage_conversation_sessions()
            if 'ended_sessions' in session_management and session_management['ended_sessions'] > 0:
                fix_report['fixes_applied'].append(f"自動結束了 {session_management['ended_sessions']} 個長時間活躍會話")
        except Exception as e:
            fix_report['errors'].append(f'會話管理失敗: {str(e)}')
        
        # === 修復6：清理過多的學習歷程記錄 ===
        try:
            history_management = manage_learning_histories()
            if 'cleaned_histories' in history_management and history_management['cleaned_histories'] > 0:
                fix_report['fixes_applied'].append(f"清理了 {history_management['cleaned_histories']} 個舊學習歷程記錄")
        except Exception as e:
            fix_report['errors'].append(f'學習歷程管理失敗: {str(e)}')
        
        return fix_report
        
    except Exception as e:
        logger.error(f"❌ 資料庫修復失敗: {e}")
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'error': str(e)
        }

# =================== 演示學生擴展方法（新增會話和學習歷程支援） ===================

def get_student_demo_data_summary(student):
    """取得學生的演示資料摘要（包含會話和學習歷程）"""
    try:
        return {
            'student_info': {
                'name': student.name,
                'line_user_id': student.line_user_id,
                'is_demo': student.is_demo_student
            },
            'messages': Message.select().where(Message.student == student).count(),
            'analyses': Analysis.select().where(Analysis.student == student).count(),
            'sessions': ConversationSession.select().where(ConversationSession.student == student).count(),
            'learning_histories': LearningHistory.select().where(LearningHistory.student == student).count()
        }
    except Exception as e:
        logger.error(f"❌ 取得學生演示資料摘要失敗: {e}")
        return {}

# =================== 檢查資料庫就緒狀態（修正版） ===================

def check_database_ready():
    """檢查資料庫是否就緒，包含修正版的會話統計檢查"""
    try:
        # 基本表格檢查
        Student.select().count()
        Message.select().count()
        Analysis.select().count()
        
        # 🔧 **關鍵修正：檢查新增表格和 update_session_stats 方法**
        try:
            ConversationSession.select().count()
            LearningHistory.select().count()
            
            # 測試 update_session_stats 方法是否可用
            test_sessions = ConversationSession.select().limit(1)
            for session in test_sessions:
                # 測試方法是否存在（不實際執行）
                if hasattr(session, 'update_session_stats'):
                    logger.debug("✅ update_session_stats 方法已可用")
                else:
                    logger.warning("⚠️ update_session_stats 方法缺失")
                break
            
        except Exception as e:
            logger.warning(f"新增表格檢查失敗: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 資料庫就緒檢查失敗: {e}")
        return False

# =================== 相容性和初始化 ===================

# 保持向後相容性的別名
init_database = initialize_db
initialize_database = initialize_db
create_tables = initialize_db

# 自動初始化（僅在被導入時執行）
if __name__ != '__main__':
    try:
        # 初始化資料庫
        initialize_db()
        
        # 執行資料庫遷移
        migrate_database()
        
        # 重設不完整的註冊狀態
        reset_registration_for_incomplete_students()
        
        logger.info("✅ models.py 自動初始化完成（修正版：支援記憶功能、學習歷程和 update_session_stats 方法）")
        
    except Exception as e:
        logger.error(f"❌ models.py 自動初始化失敗: {e}")

# =================== 模組匯出 ===================

__all__ = [
    # 核心類別
    'db', 'BaseModel', 
    'Student', 'Message', 'Analysis',
    
    # 新增類別（包含修正版的 ConversationSession）
    'ConversationSession', 'LearningHistory',
    
    # 資料庫管理函數
    'initialize_db', 'init_database', 'initialize_database', 'create_tables', 'close_db',
    'migrate_database', 'reset_registration_for_incomplete_students',
    
    # 統計和清理函數
    'get_database_stats', 'cleanup_all_demo_data',
    
    # 驗證和修復函數
    'validate_database_integrity', 'fix_database_issues',
    
    # 新增管理函數
    'manage_conversation_sessions', 'manage_learning_histories',
    'get_student_demo_data_summary', 'check_database_ready'
]

# =================== 版本說明 ===================

"""
EMI 智能教學助理系統 - models.py 修正版
=====================================

🔧 關鍵修正 (2025年6月30日):
- ✅ **添加缺失的 update_session_stats() 方法**：解決第二個專業問題後AI沒有回應的根本問題
- ✅ **修正 ConversationSession 類別**：確保與 app.py 完全兼容
- ✅ **改善錯誤處理**：即使統計更新失敗也不影響主要流程
- ✅ **保持向後相容**：所有原有功能維持不變

🎯 主要問題解決:
1. **註冊流程修正**：新用戶第一次發訊息會正確詢問學號 (在app.py中已修正)
2. **AI回應問題修正**：添加缺失的 update_session_stats() 方法 (✅ 本次修正)

✨ 新增功能保持不變:
- 對話會話追蹤：支援連續對話的記憶功能
- 學習歷程生成：深度分析學生學習軌跡和發展
- 主題標籤系統：自動識別和標記討論主題
- 會話管理：自動結束非活躍會話，清理舊記錄
- 增強統計：包含會話和學習歷程的完整統計

🗂️ 資料模型更新:
- Student: 新增會話相關方法（get_active_session, start_new_session等）
- Message: 新增 session, topic_tags, ai_response 欄位
- ConversationSession: **修正版**，包含缺失的 update_session_stats() 方法
- LearningHistory: 全新模型，記錄學習歷程
- Analysis: 保持不變，向後相容

🔧 關鍵修正詳情:
```python
def update_session_stats(self):
    """更新會話統計 - 修正版"""
    try:
        # 更新訊息計數
        self.message_count = Message.select().where(
            Message.session == self
        ).count()
        
        # 儲存更新
        self.save()
        
        # 同時更新學生的活動時間
        if self.student:
            self.student.update_activity()
            
    except Exception as e:
        logger.error(f"❌ 更新會話統計失敗: {e}")
        # 即使統計更新失敗，也不要影響主要流程
```

🚀 部署建議:
1. 替換完整的 models.py 檔案
2. 重新啟動應用程式
3. 測試註冊流程和AI回應功能
4. 檢查健康檢查頁面確認修正狀態

📊 修正驗證:
- check_database_ready() 函數會檢查 update_session_stats 方法是否可用
- 健康檢查頁面會顯示修正狀態
- 日誌會記錄方法的可用性

版本: v4.2.2 (修正版)
修正日期: 2025年6月30日
修正重點: 解決AI回應中斷問題
設計理念: 向後相容、功能完整、問題修正
核心修正: 添加缺失的 update_session_stats() 方法
"""

# =================== models.py 修正版 - 第5段結束 ===================
# =================== 完整檔案結束 ===================
