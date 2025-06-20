import os
import datetime
from peewee import *
import logging

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
    """學生模型"""
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
        """更新統計資料"""
        # 計算總訊息數
        self.message_count = Message.select().where(Message.student == self).count()
        
        # 計算提問數
        self.question_count = Message.select().where(
            (Message.student == self) & 
            (Message.message_type == 'question')
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
            self.participation_rate = min(100.0, round(daily_rate * 20, 2))  # 調整參數
        
        self.save()

class Message(BaseModel):
    """訊息模型"""
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
    source_type = CharField(max_length=20, default='user', verbose_name="來源類型")  # user, group, room
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
        )
    
    def __str__(self):
        return f"Message({self.student.name}, {self.message_type}, {self.timestamp})"
    
    @property
    def word_count(self):
        """計算字數"""
        return len(self.content.split())
    
    @property
    def is_recent(self):
        """是否為近期訊息 (24小時內)"""
        now = datetime.datetime.now()
        return (now - self.timestamp).total_seconds() < 86400  # 24小時

class Analysis(BaseModel):
    """分析記錄模型"""
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='analyses', verbose_name="學生")
    analysis_type = CharField(
        max_length=50,
        choices=[
            ('pattern_analysis', '模式分析'),
            ('learning_style', '學習風格'),
            ('progress_tracking', '進度追蹤'),
            ('recommendation', '學習建議'),
            ('engagement_analysis', '參與度分析')
        ],
        verbose_name="分析類型"
    )
    
    # 分析內容
    title = CharField(max_length=200, verbose_name="分析標題")
    content = TextField(verbose_name="分析內容")
    insights = TextField(null=True, verbose_name="洞察結果")
    recommendations = TextField(null=True, verbose_name="建議事項")
    
    # 分析數據
    confidence_score = FloatField(null=True, verbose_name="可信度分數")
    data_points = IntegerField(null=True, verbose_name="數據點數量")
    analysis_period_start = DateTimeField(null=True, verbose_name="分析期間開始")
    analysis_period_end = DateTimeField(null=True, verbose_name="分析期間結束")
    
    # 時間戳記
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    updated_at = DateTimeField(default=datetime.datetime.now, verbose_name="更新時間")
    
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
        )
    
    def __str__(self):
        return f"Analysis({self.student.name}, {self.analysis_type}, {self.created_at})"
    
    def save(self, *args, **kwargs):
        """覆寫保存方法，自動更新時間"""
        self.updated_at = datetime.datetime.now()
        return super().save(*args, **kwargs)

class AIResponse(BaseModel):
    """AI回應記錄模型"""
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
    def response_length(self):
        """回應長度"""
        return len(self.response)
    
    @property
    def query_length(self):
        """查詢長度"""
        return len(self.query)

class LearningSession(BaseModel):
    """學習會話模型"""
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
    
    def calculate_duration(self):
        """計算會話持續時間"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
            self.save()

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
            "CREATE INDEX IF NOT EXISTS idx_message_processed ON messages(is_processed, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_active ON analyses(is_active, priority, created_at)",
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
    """取得資料庫統計資訊"""
    try:
        stats = {
            'students': Student.select().count(),
            'active_students': Student.select().where(Student.is_active == True).count(),
            'messages': Message.select().count(),
            'questions': Message.select().where(Message.message_type == 'question').count(),
            'analyses': Analysis.select().count(),
            'ai_responses': AIResponse.select().count(),
            'learning_sessions': LearningSession.select().count(),
        }
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

# 清理函數
def cleanup_old_data(days=90):
    """清理舊資料"""
    try:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # 清理舊的分析記錄 (保留重要的)
        old_analyses = Analysis.select().where(
            (Analysis.created_at < cutoff_date) & 
            (Analysis.priority == 'low') &
            (Analysis.is_active == False)
        )
        
        deleted_count = 0
        for analysis in old_analyses:
            analysis.delete_instance()
            deleted_count += 1
        
        logger.info(f"清理了 {deleted_count} 筆舊分析記錄")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"清理資料時發生錯誤: {e}")
        return 0
