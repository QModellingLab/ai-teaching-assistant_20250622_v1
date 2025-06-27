# models.py - 修復版本
import os
import datetime
import logging
from peewee import *

logger = logging.getLogger(__name__)

# 資料庫配置
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    db = PostgresqlDatabase(DATABASE_URL)
else:
    db = SqliteDatabase('teaching_assistant.db')

class BaseModel(Model):
    class Meta:
        database = db

class Student(BaseModel):
    """學生資料模型 - 修復遞迴錯誤版本"""
    name = CharField(max_length=100, default='')
    line_user_id = CharField(max_length=100, unique=True)
    participation_rate = FloatField(default=0.0)
    question_count = IntegerField(default=0)
    message_count = IntegerField(default=0)
    question_rate = FloatField(default=0.0)
    active_days = IntegerField(default=0)
    learning_style = CharField(max_length=50, null=True)
    language_preference = CharField(max_length=20, default='mixed')
    level = CharField(max_length=20, null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    last_active = DateTimeField(default=datetime.datetime.now)
    is_active = BooleanField(default=True)
    
    @classmethod
    def get_by_line_id(cls, line_user_id):
        """根據 LINE ID 取得學生 - 修復版本"""
        try:
            return cls.select().where(cls.line_user_id == line_user_id).get()
        except cls.DoesNotExist:
            logger.warning(f"找不到 LINE ID: {line_user_id} 的學生")
            raise
    
    @classmethod
    def create_from_line_id(cls, line_user_id, name=None):
        """從 LINE ID 創建學生 - 修復版本"""
        try:
            # 使用 LINE ID 或生成預設名稱
            display_name = name if name else f"學生_{line_user_id[-4:]}"
            
            student = cls.create(
                name=display_name,
                line_user_id=line_user_id,
                participation_rate=0.0,
                question_count=0,
                message_count=0,
                question_rate=0.0,
                active_days=1,
                created_at=datetime.datetime.now(),
                last_active=datetime.datetime.now(),
                is_active=True
            )
            logger.info(f"✅ 創建新學生: {student.name} (LINE ID: {line_user_id})")
            return student
        except Exception as e:
            logger.error(f"❌ 創建學生失敗: {e}")
            raise
    
    @classmethod
    def get_or_create_from_line_id(cls, line_user_id, name=None):
        """取得或創建學生 - 修復版本"""
        try:
            # 嘗試取得現有學生
            student = cls.get_by_line_id(line_user_id)
            # 更新最後活動時間和名稱
            if name and name != student.name:
                student.name = name
            student.last_active = datetime.datetime.now()
            student.save()
            return student, False  # (學生物件, 是否為新創建)
        except cls.DoesNotExist:
            # 創建新學生
            student = cls.create_from_line_id(line_user_id, name)
            return student, True  # (學生物件, 是否為新創建)
    
    @classmethod
    def get_by_id(cls, student_id):
        """根據 ID 取得學生 - 修復遞迴錯誤"""
        try:
            # 直接使用 select().where() 避免遞迴
            return cls.select().where(cls.id == student_id).get()
        except cls.DoesNotExist:
            logger.warning(f"找不到 ID: {student_id} 的學生")
            return None
        except Exception as e:
            logger.error(f"❌ 取得學生失敗: {e}")
            return None
    
    def update_activity(self):
        """更新學生活動狀態"""
        self.last_active = datetime.datetime.now()
        self.save()
    
    def update_stats(self, new_message_count=None, new_question_count=None):
        """更新學生統計資料"""
        try:
            if new_message_count is not None:
                self.message_count = new_message_count
            if new_question_count is not None:
                self.question_count = new_question_count
                # 計算提問率
                if self.message_count > 0:
                    self.question_rate = (self.question_count / self.message_count) * 100
            
            # 更新參與度 (簡單演算法)
            if self.message_count > 0:
                base_participation = min(self.message_count * 5, 50)  # 每則訊息5分，最多50分
                question_bonus = min(self.question_count * 10, 30)    # 每個問題10分，最多30分
                self.participation_rate = min(base_participation + question_bonus, 100)
            
            self.save()
            logger.info(f"✅ 更新學生 {self.name} 統計資料")
        except Exception as e:
            logger.error(f"❌ 更新學生統計失敗: {e}")
    
    def get_activity_status(self):
        """取得活動狀態文字和CSS類別"""
        if not self.last_active:
            return "未知時間", "inactive"
        
        time_diff = datetime.datetime.now() - self.last_active
        
        if time_diff.days == 0:
            return "今天活躍", "active-today"
        elif time_diff.days == 1:
            return "昨天活躍", "active-yesterday"
        elif time_diff.days <= 7:
            return f"{time_diff.days}天前", "active-week"
        elif time_diff.days <= 30:
            return f"{time_diff.days}天前", "active-month"
        else:
            return f"{time_diff.days}天前", "inactive"
    
    def __str__(self):
        return f"Student({self.name}, {self.line_user_id})"
    
    class Meta:
        table_name = 'students'
        indexes = (
            (('line_user_id',), True),  # 唯一索引
            (('created_at',), False),   # 一般索引
            (('last_active',), False),
        )

class Message(BaseModel):
    """訊息模型"""
    student = ForeignKeyField(Student, backref='messages')
    content = TextField()
    message_type = CharField(max_length=20, default='message')
    timestamp = DateTimeField(default=datetime.datetime.now)
    source_type = CharField(max_length=20, default='line')
    
    class Meta:
        table_name = 'messages'

class Analysis(BaseModel):
    """分析模型"""
    student = ForeignKeyField(Student, backref='analyses')
    analysis_type = CharField(max_length=50)
    analysis_data = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        table_name = 'analyses'

class AIResponse(BaseModel):
    """AI 回應模型"""
    student = ForeignKeyField(Student, backref='ai_responses')
    original_message = TextField()
    ai_response = TextField()
    model_used = CharField(max_length=50)
    response_time = FloatField(default=0.0)
    created_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        table_name = 'ai_responses'

# 初始化資料庫
def init_database():
    """初始化資料庫"""
    try:
        db.connect()
        db.create_tables([Student, Message, Analysis, AIResponse], safe=True)
        logger.info("✅ 資料庫初始化成功")
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        raise

# 自動初始化
if __name__ != '__main__':
    try:
        init_database()
    except Exception as e:
        logger.error(f"自動初始化失敗: {e}")
