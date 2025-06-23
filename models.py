# models.py - 加入資料庫清理方法版本

import os
import datetime
import logging
from peewee import *

# 設定日誌
logger = logging.getLogger(__name__)

# 資料庫設定
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # 生產環境 - 使用 PostgreSQL (Railway 等平台)
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    
    db = PostgresqlDatabase(
        url.path[1:],  # 移除開頭的 '/'
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    logger.info("使用 PostgreSQL 資料庫")
else:
    # 開發環境 - 使用 SQLite
    db = SqliteDatabase('learning_analytics.db')
    logger.info("使用 SQLite 資料庫")

class BaseModel(Model):
    """基礎模型類別"""
    class Meta:
        database = db

class Student(BaseModel):
    """學生模型 - 加入真實資料管理功能"""
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, verbose_name="姓名")
    line_user_id = CharField(max_length=100, unique=True, verbose_name="LINE用戶ID")
    email = CharField(max_length=200, null=True, verbose_name="電子郵件")
    student_id = CharField(max_length=50, null=True, verbose_name="學號")
    
    # 時間戳記
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="註冊時間")
    last_active = DateTimeField(null=True, verbose_name="最後活動時間")
    
    # 統計資料
    message_count = IntegerField(default=0, verbose_name="總訊息數")
    question_count = IntegerField(default=0, verbose_name="提問次數")
    participation_rate = FloatField(default=0.0, verbose_name="參與度")
    question_rate = FloatField(default=0.0, verbose_name="提問率")
    
    # 學習資料
    learning_style = CharField(max_length=50, null=True, verbose_name="學習風格")
    interest_areas = TextField(null=True, verbose_name="興趣領域")
    language_preference = CharField(max_length=20, default='mixed', verbose_name="語言偏好")
    
    # 狀態
    is_active = BooleanField(default=True, verbose_name="是否活躍")
    notes = TextField(null=True, verbose_name="備註")
    
    class Meta:
        table_name = 'students'
        indexes = (
            (('line_user_id',), True),  # 唯一索引
            (('created_at',), False),   # 一般索引
            (('last_active',), False),
        )
    
    def __str__(self):
        return f"Student({self.name}, {self.line_user_id})"
    
    @property
    def is_demo_student(self):
        """檢查是否為演示學生"""
        return (self.name.startswith('[DEMO]') or 
                self.line_user_id.startswith('demo_'))
    
    @property
    def is_real_student(self):
        """檢查是否為真實學生"""
        return not self.is_demo_student
    
    @property
    def active_days(self):
        """計算活躍天數"""
        if not self.last_active:
            return 0
        delta = self.last_active.date() - self.created_at.date()
        return max(1, delta.days + 1)
    
    @property
    def daily_message_rate(self):
        """每日平均訊息數"""
        return round(self.message_count / max(1, self.active_days), 2)
    
    def update_stats(self):
        """更新統計資料 - 只計算真實訊息"""
        # 計算總訊息數（排除演示訊息）
        self.message_count = Message.select().where(
            (Message.student == self) & 
            (Message.source_type != 'demo')
        ).count()
        
        # 計算提問數（排除演示訊息）
        self.question_count = Message.select().where(
            (Message.student == self) & 
            (Message.message_type == 'question') &
            (Message.source_type != 'demo')
        ).count()
        
        # 計算提問率
        if self.message_count > 0:
            self.question_rate = round((self.question_count / self.message_count) * 100, 2)
        else:
            self.question_rate = 0.0
        
        # 更新最後活動時間
        self.last_active = datetime.datetime.now()
        
        # 計算參與度 (基於訊息頻率和活躍度)
        days_active = self.active_days
        if days_active > 0:
            daily_rate = self.message_count / days_active
            self.participation_rate = min(100.0, round(daily_rate * 20, 2))
        
        self.save()
    
    @classmethod
    def get_real_students(cls):
        """取得所有真實學生"""
        return cls.select().where(
            (~cls.name.startswith('[DEMO]')) &
            (~cls.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def get_demo_students(cls):
        """取得所有演示學生"""
        return cls.select().where(
            (cls.name.startswith('[DEMO]')) |
            (cls.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def count_real_students(cls):
        """計算真實學生數量"""
        return cls.get_real_students().count()
    
    @classmethod
    def count_demo_students(cls):
        """計算演示學生數量"""
        return cls.get_demo_students().count()
    
    @classmethod
    def cleanup_demo_students(cls):
        """清理所有演示學生及其相關資料"""
        try:
            demo_students = list(cls.get_demo_students())
            
            if not demo_students:
                return {
                    'success': True,
                    'students_deleted': 0,
                    'messages_deleted': 0,
                    'analyses_deleted': 0,
                    'ai_responses_deleted': 0,
                    'message': '沒有找到演示學生'
                }
            
            deleted_counts = {
                'students': 0,
                'messages': 0,
                'analyses': 0,
                'ai_responses': 0,
                'learning_sessions': 0
            }
            
            # 為每個演示學生清理相關資料
            for student in demo_students:
                # 刪除訊息
                deleted_counts['messages'] += Message.delete().where(
                    Message.student == student
                ).execute()
                
                # 刪除分析記錄
                deleted_counts['analyses'] += Analysis.delete().where(
                    Analysis.student == student
                ).execute()
                
                # 刪除 AI 回應（如果存在）
                try:
                    deleted_counts['ai_responses'] += AIResponse.delete().where(
                        AIResponse.student == student
                    ).execute()
                except:
                    pass  # 如果 AIResponse 表不存在就跳過
                
                # 刪除學習會話（如果存在）
                try:
                    deleted_counts['learning_sessions'] += LearningSession.delete().where(
                        LearningSession.student == student
                    ).execute()
                except:
                    pass  # 如果 LearningSession 表不存在就跳過
                
                # 最後刪除學生本身
                student.delete_instance()
                deleted_counts['students'] += 1
            
            logger.info(f"成功清理 {deleted_counts['students']} 個演示學生及其相關資料")
            
            return {
                'success': True,
                'students_deleted': deleted_counts['students'],
                'messages_deleted': deleted_counts['messages'],
                'analyses_deleted': deleted_counts['analyses'],
                'ai_responses_deleted': deleted_counts['ai_responses'],
                'learning_sessions_deleted': deleted_counts['learning_sessions'],
                'message': f"成功清理 {deleted_counts['students']} 個演示學生及所有相關資料"
            }
            
        except Exception as e:
            logger.error(f"清理演示學生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示學生時發生錯誤'
            }

class Message(BaseModel):
    """訊息模型 - 加入真實資料管理功能"""
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='messages', verbose_name="學生")
    content = TextField(verbose_name="訊息內容")
    message_type = CharField(
        max_length=20, 
        choices=[('question', '問題'), ('statement', '陳述'), ('response', '回應')],
        default='statement',
        verbose_name="訊息類型"
    )
    
    # 時間和來源
    timestamp = DateTimeField(default=datetime.datetime.now, verbose_name="時間戳記")
    source_type = CharField(max_length=20, default='user', verbose_name="來源類型")  # user, group, room, demo
    group_id = CharField(max_length=100, null=True, verbose_name="群組ID")
    room_id = CharField(max_length=100, null=True, verbose_name="聊天室ID")
    
    # 分析資料
    sentiment = CharField(max_length=20, null=True, verbose_name="情感分析")
    topic_category = CharField(max_length=50, null=True, verbose_name="主題分類")
    language_detected = CharField(max_length=10, null=True, verbose_name="偵測語言")
    complexity_score = FloatField(null=True, verbose_name="複雜度分數")
    
    # 狀態
    is_processed = BooleanField(default=False, verbose_name="是否已處理")
    processing_notes = TextField(null=True, verbose_name="處理備註")
    
    class Meta:
        table_name = 'messages'
        indexes = (
            (('student', 'timestamp'), False),
            (('message_type',), False),
            (('timestamp',), False),
            (('group_id',), False),
            (('source_type',), False),  # 新增索引
        )
    
    def __str__(self):
        return f"Message({self.student.name}, {self.message_type}, {self.timestamp})"
    
    @property
    def is_demo_message(self):
        """檢查是否為演示訊息"""
        return (self.source_type == 'demo' or 
                self.student.is_demo_student)
    
    @property
    def is_real_message(self):
        """檢查是否為真實訊息"""
        return not self.is_demo_message
    
    @property
    def word_count(self):
        """計算字數"""
        return len(self.content.split())
    
    @property
    def is_recent(self):
        """是否為近期訊息 (24小時內)"""
        now = datetime.datetime.now()
        return (now - self.timestamp).total_seconds() < 86400
    
    @classmethod
    def get_real_messages(cls):
        """取得所有真實訊息"""
        return cls.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_')) &
            (cls.source_type != 'demo')
        )
    
    @classmethod
    def get_demo_messages(cls):
        """取得所有演示訊息"""
        return cls.select().where(
            (cls.source_type == 'demo')
        )
    
    @classmethod
    def count_real_messages(cls):
        """計算真實訊息數量"""
        return cls.get_real_messages().count()
    
    @classmethod
    def count_demo_messages(cls):
        """計算演示訊息數量"""
        return cls.get_demo_messages().count()
    
    @classmethod
    def cleanup_demo_messages(cls):
        """清理所有演示訊息"""
        try:
            # 清理 source_type 為 demo 的訊息
            demo_messages_count = cls.delete().where(
                cls.source_type == 'demo'
            ).execute()
            
            # 清理孤立的演示訊息（學生已被刪除但訊息還在）
            orphaned_count = 0
            try:
                orphaned_messages = cls.select().join(Student, join_type=JOIN.LEFT_OUTER).where(
                    Student.id.is_null()
                )
                orphaned_count = orphaned_messages.count()
                if orphaned_count > 0:
                    cls.delete().where(
                        cls.student_id.in_([msg.student_id for msg in orphaned_messages])
                    ).execute()
            except:
                pass  # 如果查詢失敗就跳過
            
            total_deleted = demo_messages_count + orphaned_count
            
            logger.info(f"成功清理 {total_deleted} 則演示訊息")
            
            return {
                'success': True,
                'demo_messages_deleted': demo_messages_count,
                'orphaned_messages_deleted': orphaned_count,
                'total_deleted': total_deleted,
                'message': f"成功清理 {total_deleted} 則演示訊息"
            }
            
        except Exception as e:
            logger.error(f"清理演示訊息錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示訊息時發生錯誤'
            }

class Analysis(BaseModel):
    """分析記錄模型 - 加入真實資料管理功能"""
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='analyses', verbose_name="學生")
    analysis_type = CharField(
        max_length=50,
        choices=[
            ('pattern_analysis', '模式分析'),
            ('learning_style', '學習風格'),
            ('progress_tracking', '進度追蹤'),
            ('recommendation', '學習建議'),
            ('engagement_analysis', '參與度分析'),
            ('question_classification', '問題分類')  # 新增
        ],
        verbose_name="分析類型"
    )
    
    # 分析內容
    title = CharField(max_length=200, null=True, verbose_name="分析標題")
    content = TextField(null=True, verbose_name="分析內容")
    insights = TextField(null=True, verbose_name="洞察結果")
    recommendations = TextField(null=True, verbose_name="建議事項")
    analysis_data = TextField(null=True, verbose_name="分析資料JSON")  # 新增
    
    # 分析數據
    confidence_score = FloatField(null=True, verbose_name="可信度分數")
    data_points = IntegerField(null=True, verbose_name="數據點數量")
    analysis_period_start = DateTimeField(null=True, verbose_name="分析期間開始")
    analysis_period_end = DateTimeField(null=True, verbose_name="分析期間結束")
    
    # 時間戳記
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    updated_at = DateTimeField(default=datetime.datetime.now, verbose_name="更新時間")
    timestamp = DateTimeField(default=datetime.datetime.now, verbose_name="時間戳記")  # 新增相容性
    
    # 狀態
    is_active = BooleanField(default=True, verbose_name="是否有效")
    priority = CharField(
        max_length=10,
        choices=[('low', '低'), ('medium', '中'), ('high', '高')],
        default='medium',
        verbose_name="優先級"
    )
    
    class Meta:
        table_name = 'analyses'
        indexes = (
            (('student', 'created_at'), False),
            (('analysis_type',), False),
            (('created_at',), False),
            (('timestamp',), False),  # 新增索引
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
    
    def save(self, *args, **kwargs):
        """覆寫保存方法，自動更新時間"""
        self.updated_at = datetime.datetime.now()
        if not self.timestamp:
            self.timestamp = self.created_at or datetime.datetime.now()
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_real_analyses(cls):
        """取得所有真實分析"""
        return cls.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def get_demo_analyses(cls):
        """取得所有演示分析"""
        return cls.select().join(Student).where(
            (Student.name.startswith('[DEMO]')) |
            (Student.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def count_real_analyses(cls):
        """計算真實分析數量"""
        return cls.get_real_analyses().count()
    
    @classmethod
    def count_demo_analyses(cls):
        """計算演示分析數量"""
        return cls.get_demo_analyses().count()
    
    @classmethod
    def cleanup_demo_analyses(cls):
        """清理所有演示分析"""
        try:
            # 取得所有演示學生的分析
            demo_analyses = list(cls.get_demo_analyses())
            
            if not demo_analyses:
                return {
                    'success': True,
                    'analyses_deleted': 0,
                    'message': '沒有找到演示分析記錄'
                }
            
            # 刪除演示分析
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

class AIResponse(BaseModel):
    """AI回應記錄模型 - 加入真實資料管理功能"""
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='ai_responses', verbose_name="學生")
    query = TextField(verbose_name="用戶查詢")
    response = TextField(verbose_name="AI回應")
    
    # AI 相關資料
    response_type = CharField(
        max_length=20,
        choices=[('gemini', 'Gemini'), ('gpt', 'GPT'), ('custom', '自定義')],
        default='gemini',
        verbose_name="回應類型"
    )
    model_version = CharField(max_length=50, null=True, verbose_name="模型版本")
    processing_time = FloatField(null=True, verbose_name="處理時間(秒)")
    
    # 品質評估
    relevance_score = FloatField(null=True, verbose_name="相關性分數")
    helpfulness_score = FloatField(null=True, verbose_name="有用性分數")
    accuracy_score = FloatField(null=True, verbose_name="準確性分數")
    
    # 時間和狀態
    timestamp = DateTimeField(default=datetime.datetime.now, verbose_name="時間戳記")
    is_helpful = BooleanField(null=True, verbose_name="是否有幫助")
    user_feedback = TextField(null=True, verbose_name="用戶回饋")
    
    # 分類資料
    query_category = CharField(max_length=50, null=True, verbose_name="查詢分類")
    difficulty_level = CharField(
        max_length=10,
        choices=[('basic', '基礎'), ('intermediate', '中級'), ('advanced', '進階')],
        null=True,
        verbose_name="難度等級"
    )
    
    class Meta:
        table_name = 'ai_responses'
        indexes = (
            (('student', 'timestamp'), False),
            (('response_type',), False),
            (('timestamp',), False),
            (('query_category',), False),
        )
    
    def __str__(self):
        return f"AIResponse({self.student.name}, {self.response_type}, {self.timestamp})"
    
    @property
    def is_demo_response(self):
        """檢查是否為演示回應"""
        return self.student.is_demo_student
    
    @property
    def is_real_response(self):
        """檢查是否為真實回應"""
        return not self.is_demo_response
    
    @property
    def response_length(self):
        """回應長度"""
        return len(self.response)
    
    @property
    def query_length(self):
        """查詢長度"""
        return len(self.query)
    
    @classmethod
    def get_real_responses(cls):
        """取得所有真實回應"""
        return cls.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def get_demo_responses(cls):
        """取得所有演示回應"""
        return cls.select().join(Student).where(
            (Student.name.startswith('[DEMO]')) |
            (Student.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def cleanup_demo_responses(cls):
        """清理所有演示回應"""
        try:
            demo_responses = list(cls.get_demo_responses())
            
            if not demo_responses:
                return {
                    'success': True,
                    'responses_deleted': 0,
                    'message': '沒有找到演示回應記錄'
                }
            
            deleted_count = 0
            for response in demo_responses:
                response.delete_instance()
                deleted_count += 1
            
            logger.info(f"成功清理 {deleted_count} 個演示回應記錄")
            
            return {
                'success': True,
                'responses_deleted': deleted_count,
                'message': f"成功清理 {deleted_count} 個演示回應記錄"
            }
            
        except Exception as e:
            logger.error(f"清理演示回應錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示回應時發生錯誤'
            }

class LearningSession(BaseModel):
    """學習會話模型 - 加入真實資料管理功能"""
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='learning_sessions', verbose_name="學生")
    session_name = CharField(max_length=200, verbose_name="會話名稱")
    
    # 會話時間
    start_time = DateTimeField(verbose_name="開始時間")
    end_time = DateTimeField(null=True, verbose_name="結束時間")
    duration_minutes = IntegerField(null=True, verbose_name="持續時間(分鐘)")
    
    # 會話統計
    message_count = IntegerField(default=0, verbose_name="訊息數量")
    question_count = IntegerField(default=0, verbose_name="提問數量")
    ai_interaction_count = IntegerField(default=0, verbose_name="AI互動次數")
    
    # 學習成果
    topics_covered = TextField(null=True, verbose_name="涵蓋主題")
    learning_objectives = TextField(null=True, verbose_name="學習目標")
    achievements = TextField(null=True, verbose_name="學習成果")
    
    # 評估
    engagement_score = FloatField(null=True, verbose_name="參與度分數")
    comprehension_score = FloatField(null=True, verbose_name="理解度分數")
    satisfaction_score = FloatField(null=True, verbose_name="滿意度分數")
    
    class Meta:
        table_name = 'learning_sessions'
        indexes = (
            (('student', 'start_time'), False),
            (('start_time',), False),
        )
    
    def __str__(self):
        return f"LearningSession({self.student.name}, {self.session_name}, {self.start_time})"
    
    @property
    def is_demo_session(self):
        """檢查是否為演示會話"""
        return self.student.is_demo_student
    
    @property
    def is_real_session(self):
        """檢查是否為真實會話"""
        return not self.is_demo_session
    
    def calculate_duration(self):
        """計算會話持續時間"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
            self.save()
    
    @classmethod
    def get_real_sessions(cls):
        """取得所有真實會話"""
        return cls.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def get_demo_sessions(cls):
        """取得所有演示會話"""
        return cls.select().join(Student).where(
            (Student.name.startswith('[DEMO]')) |
            (Student.line_user_id.startswith('demo_'))
        )
    
    @classmethod
    def cleanup_demo_sessions(cls):
        """清理所有演示會話"""
        try:
            demo_sessions = list(cls.get_demo_sessions())
            
            if not demo_sessions:
                return {
                    'success': True,
                    'sessions_deleted': 0,
                    'message': '沒有找到演示會話記錄'
                }
            
            deleted_count = 0
            for session in demo_sessions:
                session.delete_instance()
                deleted_count += 1
            
            logger.info(f"成功清理 {deleted_count} 個演示會話記錄")
            
            return {
                'success': True,
                'sessions_deleted': deleted_count,
                'message': f"成功清理 {deleted_count} 個演示會話記錄"
            }
            
        except Exception as e:
            logger.error(f"清理演示會話錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示會話時發生錯誤'
            }

# =========================================
# 資料庫管理功能
# =========================================

class DatabaseCleaner:
    """資料庫清理器 - 專門處理演示資料清理"""
    
    @staticmethod
    def get_demo_data_summary():
        """取得演示資料摘要"""
        try:
            summary = {
                'demo_students': Student.count_demo_students(),
                'demo_messages': Message.count_demo_messages(),
                'demo_analyses': Analysis.count_demo_analyses(),
                'demo_ai_responses': 0,
                'demo_learning_sessions': 0,
                'real_students': Student.count_real_students(),
                'real_messages': Message.count_real_messages(),
                'real_analyses': Analysis.count_real_analyses()
            }
            
            # 嘗試計算其他表的演示資料（如果存在）
            try:
                summary['demo_ai_responses'] = AIResponse.get_demo_responses().count()
                summary['demo_learning_sessions'] = LearningSession.get_demo_sessions().count()
            except:
                pass  # 如果表不存在就跳過
            
            # 計算清理後可節省的空間（估算）
            total_demo_records = (summary['demo_students'] + summary['demo_messages'] + 
                                 summary['demo_analyses'] + summary['demo_ai_responses'] + 
                                 summary['demo_learning_sessions'])
            
            estimated_space_mb = total_demo_records * 0.002  # 每筆記錄約 2KB
            
            summary.update({
                'total_demo_records': total_demo_records,
                'estimated_space_mb': round(estimated_space_mb, 2),
                'cleanup_recommended': total_demo_records > 0
            })
            
            return summary
            
        except Exception as e:
            logger.error(f"取得演示資料摘要錯誤: {e}")
            return {
                'error': str(e),
                'demo_students': 0,
                'demo_messages': 0,
                'cleanup_recommended': False
            }
    
    @staticmethod
    def cleanup_all_demo_data():
        """清理所有演示資料"""
        try:
            cleanup_results = {}
            total_deleted = 0
            
            # 1. 清理演示學生（會連帶清理相關的訊息和分析）
            student_result = Student.cleanup_demo_students()
            cleanup_results['students'] = student_result
            if student_result['success']:
                total_deleted += student_result['students_deleted']
            
            # 2. 清理孤立的演示訊息
            message_result = Message.cleanup_demo_messages()
            cleanup_results['messages'] = message_result
            if message_result['success']:
                total_deleted += message_result['total_deleted']
            
            # 3. 清理孤立的演示分析
            analysis_result = Analysis.cleanup_demo_analyses()
            cleanup_results['analyses'] = analysis_result
            if analysis_result['success']:
                total_deleted += analysis_result['analyses_deleted']
            
            # 4. 清理演示 AI 回應（如果存在）
            try:
                ai_response_result = AIResponse.cleanup_demo_responses()
                cleanup_results['ai_responses'] = ai_response_result
                if ai_response_result['success']:
                    total_deleted += ai_response_result['responses_deleted']
            except Exception as e:
                cleanup_results['ai_responses'] = {'success': False, 'error': str(e)}
            
            # 5. 清理演示學習會話（如果存在）
            try:
                session_result = LearningSession.cleanup_demo_sessions()
                cleanup_results['learning_sessions'] = session_result
                if session_result['success']:
                    total_deleted += session_result['sessions_deleted']
            except Exception as e:
                cleanup_results['learning_sessions'] = {'success': False, 'error': str(e)}
            
            # 檢查清理結果
            all_success = all(result.get('success', False) for result in cleanup_results.values())
            
            if all_success:
                logger.info(f"成功完成演示資料清理，總共刪除 {total_deleted} 筆記錄")
                
                return {
                    'success': True,
                    'total_deleted': total_deleted,
                    'cleanup_details': cleanup_results,
                    'message': f'成功清理所有演示資料，共刪除 {total_deleted} 筆記錄',
                    'timestamp': datetime.datetime.now().isoformat()
                }
            else:
                failed_operations = [key for key, result in cleanup_results.items() 
                                   if not result.get('success', False)]
                
                return {
                    'success': False,
                    'partial_success': True,
                    'total_deleted': total_deleted,
                    'cleanup_details': cleanup_results,
                    'failed_operations': failed_operations,
                    'message': f'部分清理成功，刪除 {total_deleted} 筆記錄，但有些操作失敗',
                    'timestamp': datetime.datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"清理所有演示資料錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示資料時發生嚴重錯誤',
                'timestamp': datetime.datetime.now().isoformat()
            }
    
    @staticmethod
    def verify_cleanup():
        """驗證清理是否完成"""
        try:
            summary = DatabaseCleaner.get_demo_data_summary()
            
            is_clean = (summary['demo_students'] == 0 and 
                       summary['demo_messages'] == 0 and 
                       summary['demo_analyses'] == 0)
            
            return {
                'is_clean': is_clean,
                'remaining_demo_data': {
                    'students': summary['demo_students'],
                    'messages': summary['demo_messages'],
                    'analyses': summary['demo_analyses'],
                    'ai_responses': summary.get('demo_ai_responses', 0),
                    'learning_sessions': summary.get('demo_learning_sessions', 0)
                },
                'real_data_preserved': {
                    'students': summary['real_students'],
                    'messages': summary['real_messages'],
                    'analyses': summary['real_analyses']
                },
                'cleanup_quality': 'excellent' if is_clean else 'incomplete',
                'verification_time': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"驗證清理結果錯誤: {e}")
            return {
                'is_clean': False,
                'error': str(e),
                'cleanup_quality': 'unknown'
            }

def initialize_db():
    """初始化資料庫"""
    try:
        # 連接資料庫
        db.connect()
        
        # 建立所有表格
        tables = [Student, Message, Analysis, AIResponse, LearningSession]
        db.create_tables(tables, safe=True)
        
        logger.info("資料庫表格建立成功")
        
        # 檢查是否需要建立索引
        create_additional_indexes()
        
        return True
        
    except Exception as e:
        logger.error(f"資料庫初始化失敗: {e}")
        raise
    finally:
        if not db.is_closed():
            db.close()

def create_additional_indexes():
    """建立額外的索引以提升查詢效能"""
    try:
        # 複合索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_student_active ON students(is_active, last_active)",
            "CREATE INDEX IF NOT EXISTS idx_student_real ON students(name, line_user_id)",  # 新增：真實學生識別索引
            "CREATE INDEX IF NOT EXISTS idx_message_processed ON messages(is_processed, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_message_real ON messages(source_type, timestamp)",  # 新增：真實訊息索引
            "CREATE INDEX IF NOT EXISTS idx_analysis_active ON analyses(is_active, priority, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_real ON analyses(analysis_type, timestamp)",  # 新增：真實分析索引
            "CREATE INDEX IF NOT EXISTS idx_ai_response_helpful ON ai_responses(is_helpful, timestamp)",
        ]
        
        for index_sql in indexes:
            try:
                db.execute_sql(index_sql)
            except Exception as e:
                logger.warning(f"索引建立警告: {e}")
                
        logger.info("額外索引建立完成")
        
    except Exception as e:
        logger.error(f"建立索引時發生錯誤: {e}")

def get_db_stats():
    """取得資料庫統計資訊 - 區分真實和演示資料"""
    try:
        stats = {
            # 真實資料統計
            'real_students': Student.count_real_students(),
            'real_messages': Message.count_real_messages(),
            'real_analyses': Analysis.count_real_analyses(),
            
            # 演示資料統計
            'demo_students': Student.count_demo_students(),
            'demo_messages': Message.count_demo_messages(),
            'demo_analyses': Analysis.count_demo_analyses(),
            
            # 總計
            'total_students': Student.select().count(),
            'total_messages': Message.select().count(),
            'total_analyses': Analysis.select().count(),
            
            # 活躍學生（真實學生）
            'active_real_students': Student.select().where(
                (~Student.name.startswith('[DEMO]')) &
                (~Student.line_user_id.startswith('demo_')) &
                (Student.is_active == True)
            ).count(),
            
            # 問題統計（真實問題）
            'real_questions': Message.select().join(Student).where(
                (~Student.name.startswith('[DEMO]')) &
                (~Student.line_user_id.startswith('demo_')) &
                (Message.message_type == 'question') &
                (Message.source_type != 'demo')
            ).count(),
        }
        
        # 嘗試計算其他表的統計（如果存在）
        try:
            stats['ai_responses'] = AIResponse.select().count()
            stats['learning_sessions'] = LearningSession.select().count()
        except:
            stats['ai_responses'] = 0
            stats['learning_sessions'] = 0
        
        # 計算資料清潔度
        total_records = stats['total_students'] + stats['total_messages'] + stats['total_analyses']
        demo_records = stats['demo_students'] + stats['demo_messages'] + stats['demo_analyses']
        
        if total_records > 0:
            stats['data_cleanliness_percentage'] = round(((total_records - demo_records) / total_records) * 100, 1)
        else:
            stats['data_cleanliness_percentage'] = 100.0
        
        stats['cleanup_recommended'] = demo_records > 0
        
        return stats
        
    except Exception as e:
        logger.error(f"取得資料庫統計時發生錯誤: {e}")
        return {}

# 資料庫連接管理
def connect_db():
    """連接資料庫"""
    if db.is_closed():
        db.connect()

def close_db():
    """關閉資料庫連接"""
    if not db.is_closed():
        db.close()

# 清理函數（已更新為只處理真實資料）
def cleanup_old_data(days=90):
    """清理舊資料 - 只影響真實資料，保留演示資料供選擇性清理"""
    try:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # 清理舊的真實分析記錄（保留重要的）
        old_real_analyses = Analysis.select().join(Student).where(
            (~Student.name.startswith('[DEMO]')) &
            (~Student.line_user_id.startswith('demo_')) &
            (Analysis.created_at < cutoff_date) & 
            (Analysis.priority == 'low') &
            (Analysis.is_active == False)
        )
        
        deleted_count = 0
        for analysis in old_real_analyses:
            analysis.delete_instance()
            deleted_count += 1
        
        logger.info(f"清理了 {deleted_count} 筆舊的真實分析記錄")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"清理資料時發生錯誤: {e}")
        return 0

# =========================================
# 新增：資料完整性檢查函數
# =========================================

def check_data_integrity():
    """檢查資料完整性"""
    try:
        issues = []
        
        # 檢查孤立的訊息（學生已被刪除但訊息還在）
        orphaned_messages = Message.select().join(Student, join_type=JOIN.LEFT_OUTER).where(
            Student.id.is_null()
        ).count()
        
        if orphaned_messages > 0:
            issues.append(f"發現 {orphaned_messages} 則孤立訊息")
        
        # 檢查孤立的分析（學生已被刪除但分析還在）
        orphaned_analyses = Analysis.select().join(Student, join_type=JOIN.LEFT_OUTER).where(
            Student.id.is_null()
        ).count()
        
        if orphaned_analyses > 0:
            issues.append(f"發現 {orphaned_analyses} 個孤立分析")
        
        # 檢查學生統計是否準確
        students_with_wrong_stats = 0
        for student in Student.select():
            actual_messages = Message.select().where(
                (Message.student == student) & 
                (Message.source_type != 'demo')
            ).count()
            
            if abs(student.message_count - actual_messages) > 1:  # 允許1的誤差
                students_with_wrong_stats += 1
        
        if students_with_wrong_stats > 0:
            issues.append(f"發現 {students_with_wrong_stats} 位學生的統計資料不準確")
        
        return {
            'integrity_ok': len(issues) == 0,
            'issues_found': len(issues),
            'issues': issues,
            'check_time': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"資料完整性檢查錯誤: {e}")
        return {
            'integrity_ok': False,
            'error': str(e),
            'check_time': datetime.datetime.now().isoformat()
        }

def fix_data_integrity_issues():
    """修復資料完整性問題"""
    try:
        fixes_applied = []
        
        # 修復孤立的訊息
        orphaned_messages = Message.delete().join(Student, join_type=JOIN.LEFT_OUTER).where(
            Student.id.is_null()
        ).execute()
        
        if orphaned_messages > 0:
            fixes_applied.append(f"刪除了 {orphaned_messages} 則孤立訊息")
        
        # 修復孤立的分析
        orphaned_analyses = Analysis.delete().join(Student, join_type=JOIN.LEFT_OUTER).where(
            Student.id.is_null()
        ).execute()
        
        if orphaned_analyses > 0:
            fixes_applied.append(f"刪除了 {orphaned_analyses} 個孤立分析")
        
        # 修復學生統計
        students_fixed = 0
        for student in Student.select():
            old_count = student.message_count
            student.update_stats()
            if student.message_count != old_count:
                students_fixed += 1
        
        if students_fixed > 0:
            fixes_applied.append(f"修復了 {students_fixed} 位學生的統計資料")
        
        return {
            'success': True,
            'fixes_applied': len(fixes_applied),
            'fixes': fixes_applied,
            'fix_time': datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"修復資料完整性問題錯誤: {e}")
        return {
            'success': False,
            'error': str(e),
            'fix_time': datetime.datetime.now().isoformat()
        }
