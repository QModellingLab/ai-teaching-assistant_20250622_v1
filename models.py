# =================== models.py 簡化版 - 第1段開始 ===================
# EMI智能教學助理系統 - 資料模型定義（簡化版）
# 簡化統計邏輯，新增註冊流程欄位
# 更新日期：2025年6月29日

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

# =================== 學生模型（簡化版） ===================

class Student(BaseModel):
    """學生資料模型 - 簡化版本，專注核心功能"""
    
    # 基本資料
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, default='', verbose_name="姓名")
    line_user_id = CharField(max_length=100, unique=True, verbose_name="LINE用戶ID")
    
    # ✨ 新增：學號欄位
    student_id = CharField(max_length=20, default='', verbose_name="學號")
    
    # ✨ 新增：註冊流程追蹤
    registration_step = IntegerField(default=0, verbose_name="註冊步驟")
    # 0=已完成註冊, 1=等待姓名, 2=等待學號
    
    # 保留必要欄位（向後相容）
    grade = CharField(max_length=20, null=True, default=None, verbose_name="年級") 
    
    # 簡化統計 - 只保留基本的
    message_count = IntegerField(default=0, verbose_name="訊息總數")
    
    # 時間戳記
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name="建立時間")
    last_active = DateTimeField(default=datetime.datetime.now, verbose_name="最後活動")
    is_active = BooleanField(default=True, verbose_name="是否活躍")
    
    # ❌ 移除的複雜統計欄位（簡化）
    # participation_rate = FloatField(default=0.0, verbose_name="參與度")
    # question_count = IntegerField(default=0, verbose_name="提問次數") 
    # question_rate = FloatField(default=0.0, verbose_name="提問率")
    # active_days = IntegerField(default=0, verbose_name="活躍天數")
    # learning_style = CharField(max_length=50, null=True, verbose_name="學習風格")
    # language_preference = CharField(max_length=20, default='mixed', verbose_name="語言偏好")
    # level = CharField(max_length=20, null=True, verbose_name="程度等級")
    
    class Meta:
        table_name = 'students'
        indexes = (
            (('line_user_id',), True),  # 唯一索引
            (('created_at',), False),   # 一般索引
            (('last_active',), False),
        )
    
    def __str__(self):
        return f"Student({self.name}, {self.student_id}, {self.line_user_id})"
    
    # =================== 基本查詢方法 ===================
    
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
        """安全取得學生，不存在時回傳None"""
        try:
            return cls.get(*args, **kwargs)
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"❌ 查詢學生失敗: {e}")
            return None
    
    @classmethod
    def create(cls, **data):
        """創建學生（覆寫以添加日誌）"""
        try:
            student = super().create(**data)
            logger.info(f"✅ 創建新學生: {student.name} (LINE ID: {student.line_user_id})")
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
    
    # =================== 簡化的實例方法 ===================
    
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
    
    def is_registered(self):
        """檢查是否已完成註冊"""
        return self.registration_step == 0 and self.name and self.student_id
    
    def needs_registration(self):
        """檢查是否需要註冊"""
        return self.registration_step > 0 or not self.name or not self.student_id
    
    # =================== 演示資料管理（保留） ===================
    
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
                    'message': '沒有找到演示學生'
                }
            
            deleted_counts = {
                'students': 0,
                'messages': 0,
                'analyses': 0
            }
            
            # 為每個演示學生清理相關資料
            for student in demo_students:
                # 刪除訊息
                deleted_counts['messages'] += Message.delete().where(
                    Message.student == student
                ).execute()
                
                # 刪除分析記錄（如果存在）
                try:
                    deleted_counts['analyses'] += Analysis.delete().where(
                        Analysis.student == student
                    ).execute()
                except:
                    pass  # 如果 Analysis 表不存在就跳過
                
                # 最後刪除學生本身
                student.delete_instance()
                deleted_counts['students'] += 1
            
            logger.info(f"成功清理 {deleted_counts['students']} 個演示學生及其相關資料")
            
            return {
                'success': True,
                'students_deleted': deleted_counts['students'],
                'messages_deleted': deleted_counts['messages'],
                'analyses_deleted': deleted_counts['analyses'],
                'message': f"成功清理 {deleted_counts['students']} 個演示學生及所有相關資料"
            }
            
        except Exception as e:
            logger.error(f"清理演示學生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '清理演示學生時發生錯誤'
            }

# =================== 訊息模型（簡化版） ===================

class Message(BaseModel):
    """訊息模型 - 簡化版本"""
    
    id = AutoField(primary_key=True)
    student = ForeignKeyField(Student, backref='messages', verbose_name="學生")
    content = TextField(verbose_name="訊息內容")
    timestamp = DateTimeField(default=datetime.datetime.now, verbose_name="時間戳記")
    source_type = CharField(max_length=20, default='line', verbose_name="來源類型")
    # 'line' = 學生訊息, 'ai' = AI回應
    
    # ❌ 移除的複雜欄位（簡化）
    # message_type = CharField(max_length=20, default='message', verbose_name="訊息類型")
    
    class Meta:
        table_name = 'messages'
        indexes = (
            (('student', 'timestamp'), False),
            (('timestamp',), False),
            (('source_type',), False),
        )
    
    def __str__(self):
        return f"Message({self.student.name}, {self.source_type}, {self.timestamp})"
    
    @classmethod
    def create(cls, **data):
        """創建訊息（覆寫以添加日誌）"""
        try:
            message = super().create(**data)
            logger.debug(f"創建訊息: {message.student.name} - {message.source_type}")
            return message
        except Exception as e:
            logger.error(f"❌ 創建訊息失敗: {e}")
            raise
    
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
        return self.source_type == 'line'
    
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

# =================== models.py 簡化版 - 第1段結束 ===================

# =================== models.py 簡化版 - 第2段開始 ===================
# 分析模型和資料庫管理功能

# =================== 分析模型（保留但簡化） ===================

class Analysis(BaseModel):
    """分析模型 - 保留但簡化"""
    
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

# =================== 資料庫初始化和管理 ===================

def initialize_db():
    """初始化資料庫"""
    try:
        # 連接資料庫
        if db.is_closed():
            db.connect()
            logger.info("✅ 資料庫連接建立")
        
        # 創建所有表格（簡化版）
        db.create_tables([Student, Message, Analysis], safe=True)
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

# =================== 資料庫遷移功能（簡化版） ===================

def migrate_database():
    """資料庫遷移 - 添加新欄位"""
    try:
        logger.info("🔄 開始資料庫遷移...")
        
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
            
            logger.info("✅ 現有學生記錄已更新預設值")
        except Exception as e:
            logger.warning(f"⚠️ 更新現有記錄時出現問題: {e}")
        
        logger.info("✅ 資料庫遷移完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 資料庫遷移失敗: {e}")
        return False

def reset_registration_for_incomplete_students():
    """重設不完整註冊的學生"""
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

# =================== 資料庫統計功能（簡化版） ===================

def get_database_stats():
    """取得資料庫統計資訊（簡化版）"""
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
                'student_messages': Message.select().where(Message.source_type == 'line').count(),
                'ai_messages': Message.select().where(Message.source_type == 'ai').count(),
            },
            'analyses': {
                'total': Analysis.select().count(),
                'real': Analysis.get_real_analyses().count(),
                'demo': Analysis.get_demo_analyses().count(),
            }
        }
        
        # 計算活躍學生（7天內有活動）
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        stats['students']['active_this_week'] = Student.select().where(
            Student.last_active.is_null(False) & 
            (Student.last_active >= week_ago)
        ).count()
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ 取得資料庫統計失敗: {e}")
        return {
            'students': {'total': 0, 'real': 0, 'demo': 0, 'registered': 0, 'need_registration': 0, 'active_this_week': 0},
            'messages': {'total': 0, 'real': 0, 'demo': 0, 'student_messages': 0, 'ai_messages': 0},
            'analyses': {'total': 0, 'real': 0, 'demo': 0}
        }

def cleanup_all_demo_data():
    """清理所有演示資料"""
    try:
        logger.info("🧹 開始清理所有演示資料...")
        
        results = {}
        
        # 清理演示訊息
        message_result = Message.cleanup_demo_messages()
        results['messages'] = message_result
        
        # 清理演示分析
        analysis_result = Analysis.cleanup_demo_analyses()
        results['analyses'] = analysis_result
        
        # 清理演示學生（最後執行）
        student_result = Student.cleanup_demo_students()
        results['students'] = student_result
        
        total_cleaned = {
            'students': results['students'].get('students_deleted', 0),
            'messages': results['messages'].get('total_deleted', 0),
            'analyses': results['analyses'].get('analyses_deleted', 0)
        }
        
        logger.info(f"✅ 演示資料清理完成: {total_cleaned}")
        
        return {
            'success': True,
            'total_cleaned': total_cleaned,
            'details': results,
            'message': f"成功清理演示資料：{total_cleaned['students']}位學生，{total_cleaned['messages']}則訊息，{total_cleaned['analyses']}項分析"
        }
        
    except Exception as e:
        logger.error(f"❌ 清理演示資料失敗: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': '清理演示資料時發生錯誤'
        }

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
        
        logger.info("✅ models.py 自動初始化完成")
        
    except Exception as e:
        logger.error(f"❌ models.py 自動初始化失敗: {e}")

# =================== 模組匯出 ===================

__all__ = [
    # 核心類別
    'db', 'BaseModel', 
    'Student', 'Message', 'Analysis',
    
    # 資料庫管理函數
    'initialize_db', 'init_database', 'initialize_database', 'create_tables', 'close_db',
    'migrate_database', 'reset_registration_for_incomplete_students',
    
    # 統計和清理函數
    'get_database_stats', 'cleanup_all_demo_data'
]

# =================== 版本說明 ===================

"""
EMI 智能教學助理系統 - models.py 簡化版
=====================================

🎯 簡化重點:
- ✨ 新增學號欄位 (student_id)
- ✨ 新增註冊流程追蹤 (registration_step)  
- ❌ 移除複雜統計欄位（參與度、提問率等）
- 🔧 簡化方法，專注核心功能
- 💾 保留向後相容性

✨ 新增功能:
- 註冊流程追蹤：0=已完成, 1=等待姓名, 2=等待學號
- 學號欄位：儲存學生的學號資訊
- 簡化統計：只保留必要的基本統計
- 自動遷移：升級現有資料庫結構

🗂️ 資料模型:
- Student: 學生基本資料 + 註冊狀態
- Message: 對話記錄（學生/AI訊息）
- Analysis: 分析記錄（保留但簡化）

🔄 資料庫遷移:
- 自動添加新欄位
- 保持現有資料完整
- 向後相容舊版本

📊 統計功能:
- 基本計數統計
- 演示資料管理
- 清理功能

版本日期: 2025年6月29日
簡化版本: v3.0
設計理念: 簡潔、實用、易維護
"""

# =================== models.py 簡化版 - 第2段結束 ===================
# =================== 程式檔案結束 ===================
