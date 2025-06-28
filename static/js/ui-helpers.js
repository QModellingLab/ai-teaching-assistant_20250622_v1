// ===== UI輔助功能 =====

// 複製到剪貼簿
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showSuccess('已複製到剪貼簿');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showSuccess('已複製到剪貼簿');
    } catch (err) {
        showError('複製失敗');
    }
    
    document.body.removeChild(textArea);
}

// 格式化日期
function formatDate(date) {
    if (!date) return '--';
    
    const now = new Date();
    const targetDate = new Date(date);
    const diffTime = Math.abs(now - targetDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)}週前`;
    if (diffDays < 365) return `${Math.ceil(diffDays / 30)}個月前`;
    return `${Math.ceil(diffDays / 365)}年前`;
}

// 格式化數字
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// 節流函數
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// 防抖函數
function debounce(func, wait, immediate) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

// 模態視窗管理
class ModalManager {
    constructor() {
        this.activeModals = [];
    }
    
    open(modalId, content = '') {
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.style.display = 'flex';
            this.activeModals.push(modalId);
            return existingModal;
        }
        
        const modal = this.createModal(modalId, content);
        document.body.appendChild(modal);
        this.activeModals.push(modalId);
        
        // 添加淡入動畫
        setTimeout(() => {
            modal.style.opacity = '1';
        }, 10);
        
        return modal;
    }
    
    close(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.opacity = '0';
            setTimeout(() => {
                modal.style.display = 'none';
                this.activeModals = this.activeModals.filter(id => id !== modalId);
            }, 300);
        }
    }
    
    closeAll() {
        this.activeModals.forEach(modalId => {
            this.close(modalId);
        });
    }
    
    createModal(modalId, content) {
        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal-overlay';
        
        Object.assign(modal.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: '2000',
            opacity: '0',
            transition: 'opacity 0.3s ease-in-out'
        });
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.innerHTML = content;
        
        Object.assign(modalContent.style, {
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '0.75rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            maxWidth: '90%',
            maxHeight: '90%',
            overflow: 'auto'
        });
        
        // 點擊外部關閉
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close(modalId);
            }
        });
        
        modal.appendChild(modalContent);
        return modal;
    }
}

// 全域模態視窗管理器
const modalManager = new ModalManager();

// 表單驗證
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        const value = input.value.trim();
        const errorElement = input.parentNode.querySelector('.error-message');
        
        // 移除之前的錯誤訊息
        if (errorElement) {
            errorElement.remove();
        }
        
        // 重置樣式
        input.style.borderColor = 'var(--gray-200)';
        
        if (!value) {
            showFieldError(input, '此欄位為必填');
            isValid = false;
        } else if (input.type === 'email' && !isValidEmail(value)) {
            showFieldError(input, '請輸入有效的電子郵件地址');
            isValid = false;
        }
    });
    
    return isValid;
}

function showFieldError(input, message) {
    input.style.borderColor = 'var(--error-color)';
    
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    errorElement.style.color = 'var(--error-color)';
    errorElement.style.fontSize = 'var(--font-size-sm)';
    errorElement.style.marginTop = 'var(--spacing-1)';
    
    input.parentNode.appendChild(errorElement);
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// 資料表格功能
function initDataTable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const headers = table.querySelectorAll('th[data-sortable]');
    
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';
        header.addEventListener('click', () => {
            sortTable(table, header.cellIndex, header.dataset.type || 'string');
        });
    });
}

function sortTable(table, columnIndex, dataType = 'string') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const sortedRows = rows.sort((a, b) => {
        const cellA = a.cells[columnIndex].textContent.trim();
        const cellB = b.cells[columnIndex].textContent.trim();
        
        switch (dataType) {
            case 'number':
                return parseFloat(cellA) - parseFloat(cellB);
            case 'date':
                return new Date(cellA) - new Date(cellB);
            default:
                return cellA.localeCompare(cellB);
        }
    });
    
    sortedRows.forEach(row => tbody.appendChild(row));
}

// 效能監控
class PerformanceMonitor {
    constructor() {
        this.metrics = {};
    }
    
    startTimer(name) {
        this.metrics[name] = { start: performance.now() };
    }
    
    endTimer(name) {
        if (this.metrics[name]) {
            this.metrics[name].duration = performance.now() - this.metrics[name].start;
            console.log(`⏱️ ${name}: ${this.metrics[name].duration.toFixed(2)}ms`);
        }
    }
    
    measureFunction(func, name) {
        return (...args) => {
            this.startTimer(name);
            const result = func.apply(this, args);
            this.endTimer(name);
            return result;
        };
    }
    
    getMetrics() {
        return this.metrics;
    }
}

// 全域效能監控器
const performanceMonitor = new PerformanceMonitor();

// 本地儲存輔助函數（使用記憶體替代localStorage）
class MemoryStorage {
    constructor() {
        this.storage = {};
    }
    
    setItem(key, value) {
        this.storage[key] = JSON.stringify(value);
    }
    
    getItem(key) {
        const item = this.storage[key];
        return item ? JSON.parse(item) : null;
    }
    
    removeItem(key) {
        delete this.storage[key];
    }
    
    clear() {
        this.storage = {};
    }
    
    getAll() {
        return Object.keys(this.storage).reduce((acc, key) => {
            acc[key] = this.getItem(key);
            return acc;
        }, {});
    }
}

// 全域記憶體儲存
const memoryStorage = new MemoryStorage();

// 響應式設計輔助
function getScreenSize() {
    const width = window.innerWidth;
    if (width < 768) return 'mobile';
    if (width < 1024) return 'tablet';
    return 'desktop';
}

function isMobile() {
    return getScreenSize() === 'mobile';
}

function isTablet() {
    return getScreenSize() === 'tablet';
}

function isDesktop() {
    return getScreenSize() === 'desktop';
}

// 滾動到元素
function scrollToElement(elementId, offset = 0) {
    const element = document.getElementById(elementId);
    if (element) {
        const top = element.offsetTop - offset;
        window.scrollTo({
            top: top,
            behavior: 'smooth'
        });
    }
}

// 元素可見性檢測
function isElementInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// 延遲載入圖片
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-lazy]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.lazy;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// 初始化所有UI功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化延遲載入
    lazyLoadImages();
    
    // 初始化所有資料表格
    document.querySelectorAll('table[data-sortable]').forEach(table => {
        initDataTable(table.id);
    });
    
    // 監聽視窗大小變化
    window.addEventListener('resize', debounce(() => {
        console.log('螢幕尺寸:', getScreenSize());
    }, 250));
    
    // ESC鍵關閉模態視窗
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            modalManager.closeAll();
        }
    });
});

