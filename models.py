# models.py - 完整修復版本
# EMI智能教學助理系統 - 資料模型定義
# 修復遞迴錯誤、保留所有原有功能
# 更新日期：2025年6月27日

import os
import datetime
import logging
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

# =================== 學生模型 ===================

class Student(BaseModel):
    """學生資料模型 - 修復遞迴錯誤版本"""
    
    # 基本資料
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, default='', verbose_name="姓名")
    line_user_id = CharField(max_length=100, unique=True, verbose_name="LINE用戶ID")
    
    # 學習統計
    participation_rate = FloatField(default=0.0, verbose_name="參與度")
    question_count = IntegerField(default=0, verbose_name="提問次數")
    message_count = IntegerField(default=0, verbose_name="訊息總數")
    question_rate = FloatField(default=0.0, verbose_name="提問率")
    active_days = IntegerField(default=0, verbose_name="活躍天數")
    
    # 學習偏好
    learning_style = CharField(max_length=50, null=True, verbose_name="學習風格")
    language_preference = CharField(max_length=20, default='mixed', verbose_name="語言偏好")
    level = CharField(max_length=20, null=True, verbose_name="程度等級")
    
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
        )
    
    def __str__(self):
        return f"Student({self.name}, {self.line_user_id})"
    
    # =================== 查詢方法 (修復遞迴錯誤) ===================
    
    @classmethod
    def get_by_line_id(cls, line_user_id):
        """根據 LINE ID 取得學生"""
        try:
            return cls.select().where(cls.line_user_id == line_user_id).get()
        except cls.DoesNotExist:
            logger.warning(f"找不到 LINE ID: {line_user_id} 的學生")
            raise
    
    @classmethod
    def get_by_id(cls, student_id):
        """根據 ID 取得學生 - 修復遞迴錯誤"""
        try:
            # ✅ 修復：使用 select().where() 避免遞迴調用
            return cls.select().where(cls.id == student_id).get()
        except cls.DoesNotExist:
            logger.warning(f"找不到 ID: {student_id} 的學生")
            return None
        except Exception as e:
            logger.error(f"❌ 取得學生失敗: {e}")
            return None
    
    @classmethod
    def create_from_line_id(cls, line_user_id, name=None):
        """從 LINE ID 創建學生"""
        try:
            # 使用 LINE ID 或生成預設名稱
            display_name = name if name else f"User_{line_user_id[-6:]}"
            
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
        """取得或創建學生"""
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
    
    # =================== 實例方法 ===================
    
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
    
    # =================== 演示資料管理 ===================
    
    @property
    def is_demo_student(self):
        """檢查是否為演示學生"""
        return (self.name.startswith('[DEMO]') or 
                self.line_user_id.startswith('demo_') or
                self.name.startswith('學生_'))
    
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
        """清理演示學生及其相關資料"""
        try:
            demo_students = list(cls.get_demo_students())
            
            if not demo_students:
                return {
                    'success': True,
                    'students_deleted': 0,
                    'messages_deleted': 0,
                    'analyses_deleted': 0,
                    'message': '沒有找到演示學生'
                }
            
            deleted_counts = {
                'students': 0,
                'messages': 0,
                'analyses': 0,
                'ai_responses': 0
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
                
                # 刪除 AI 回應
                try:
                    deleted_counts['ai_responses'] += AIResponse.delete().where(
                        AIResponse.student == student
                    ).execute()
                except:
                    pass  # 如果 AIResponse 表不存在就跳過
                
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
                'message': f"成功清理 {deleted_counts['students']} 個演示學生及所有相關資料"
            }
            
        except Exception as e:
            logger.error(f"清理演示學生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示學生時發生錯誤'
            }

# =================== 訊息模型 ===================

class Message(BaseModel):
    """訊息模型"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='messages', verbose_name="學生")
    content = TextField(verbose_name="訊息內容")
    message_type = CharField(max_length=20, default='message', verbose_name="訊息類型")
    timestamp = DateTimeField(default=datetime.datetime.now, verbose_name="時間戳記")
    source_type = CharField(max_length=20, default='line', verbose_name="來源類型")
    
    class Meta:
        table_name = 'messages'
        indexes = (
            (('student', 'timestamp'), False),
            (('message_type',), False),
            (('timestamp',), False),
        )
    
    def __str__(self):
        return f"Message({self.student.name}, {self.message_type}, {self.timestamp})"
    
    @property
    def is_demo_message(self):
        """檢查是否為演示訊息"""
        return self.student.is_demo_student
    
    @property
    def is_real_message(self):
        """檢查是否為真實訊息"""
        return not self.is_demo_message
    
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

# =================== 分析模型 ===================

class Analysis(BaseModel):
    """分析模型"""
    
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

# =================== AI 回應模型 ===================

class AIResponse(BaseModel):
    """AI回應記錄模型"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='ai_responses', verbose_name="學生")
    query = TextField(verbose_name="用戶查詢")
    response = TextField(verbose_name="AI回應")
    
    # AI 相關資料
    response_type = CharField(max_length=20, default='gemini', verbose_name="回應類型")
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
    difficulty_level = CharField(max_length=10, null=True, verbose_name="難度等級")
    
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

# =================== 資料庫初始化 ===================

def initialize_db():
    """初始化資料庫"""
    try:
        # 連接資料庫
        if db.is_closed():
            db.connect()
            logger.info("✅ 資料庫連接建立")
        
        # 創建所有表格
        db.create_tables([Student, Message, Analysis, AIResponse], safe=True)
        logger.info("✅ 資料庫表格初始化完成")
        
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

# =================== 相容性別名 ===================

# 保持向後相容性
init_database = initialize_db

# 自動初始化（僅在被導入時執行）
if __name__ != '__main__':
    try:
        initialize_db()
    except Exception as e:
        logger.error(f"自動初始化失敗: {e}")

# =================== 模組匯出 ===================

__all__ = [
    'db', 'BaseModel', 
    'Student', 'Message', 'Analysis', 'AIResponse',
    'initialize_db', 'init_database', 'close_db'
]
