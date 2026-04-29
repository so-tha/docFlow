from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from datetime import datetime
from src.services import ReportService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReportTable(QTableWidget):
    report_selected = pyqtSignal(str)  
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_reports()
    
    def init_ui(self):
        columns = ["ID", "Arquivo", "Tamanho", "Status", "Data"]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.SingleSelection)
        
        self.setSortingEnabled(True)
    
    def load_reports(self, status: str = None, limit: int = 50):
        try:
            if status:
                reports = ReportService.get_reports_by_status(status, limit=limit)
            else:
                reports = ReportService.get_all_reports(limit=limit)
            
            self.setRowCount(0)
            
            for report in reports:
                self.add_report_row(report)
            
            logger.info(f"Carregados {len(reports)} relatórios")
        
        except Exception as e:
            logger.error(f"Falha ao carregar relatórios: {str(e)}")
    
    def add_report_row(self, report):
        row = self.rowCount()
        self.insertRow(row)
        
        id_item = QTableWidgetItem(report.id[:8] + "...")
        id_item.setData(Qt.ItemDataRole.UserRole, report.id)  
        self.setItem(row, 0, id_item)
        
        filename_item = QTableWidgetItem(report.original_filename)
        self.setItem(row, 1, filename_item)
        
        from src.utils.file_handler import FileHandler
        size_str = FileHandler.format_file_size(report.file_size or 0)
        size_item = QTableWidgetItem(size_str)
        self.setItem(row, 2, size_item)
        
        status_colors = {
            'pending': QColor('#FFA500'),   
            'approved': QColor('#00AA00'),   
            'rejected': QColor('#FF0000')    
        }
        status_map = {
            'pending': 'Pendente',
            'approved': 'Aprovado',
            'rejected': 'Rejeitado'
        }
        status_item = QTableWidgetItem(status_map.get(report.status, report.status.upper()))
        status_item.setBackground(status_colors.get(report.status, QColor('#CCCCCC')))
        self.setItem(row, 3, status_item)
        
        date_str = report.created_at.strftime("%Y-%m-%d %H:%M")
        date_item = QTableWidgetItem(date_str)
        self.setItem(row, 4, date_item)
        
    
    def on_view_clicked(self, report_id: str):
        self.report_selected.emit(report_id)
    
    def refresh(self, status: str = None):
        self.load_reports(status=status)
