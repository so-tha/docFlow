"""
Excel Sync Dialog - Interface PyQt6 para sincronização de dados com SharePoint.

Permite ao usuário:
1. Visualizar diferenças entre local e SharePoint
2. Selecionar quais mudanças sincronizar
3. Revisar impacto das mudanças antes de aplicar
4. Monitorar progresso da sincronização
"""

from typing import Optional, List, Callable
from pathlib import Path
from datetime import datetime
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QProgressBar, QComboBox, QCheckBox, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class SyncWorkerThread(QThread):
    """Thread de trabalho para sincronização não-bloqueante"""
    
    progress = pyqtSignal(int)  # Progresso 0-100
    finished = pyqtSignal(object)  # Resultado da sincronização
    error = pyqtSignal(str)  # Mensagem de erro
    status_update = pyqtSignal(str)  # Atualização de status
    
    def __init__(self, sync_service, diff_report, file_id, dry_run=False):
        super().__init__()
        self.sync_service = sync_service
        self.diff_report = diff_report
        self.file_id = file_id
        self.dry_run = dry_run
    
    def run(self):
        """Executa sincronização na thread"""
        try:
            self.status_update.emit("🔄 Iniciando sincronização...")
            
            # Criar backup antes de sincronizar
            if not self.dry_run:
                self.status_update.emit("💾 Criando backup...")
                backup_id = self.sync_service.create_backup(self.file_id)
                if not backup_id:
                    self.error.emit("Falha ao criar backup")
                    return
                self.progress.emit(10)
            
            # Aplicar mudanças
            self.status_update.emit("⚙️  Aplicando mudanças...")
            result = self.sync_service.apply_diff_report(
                self.diff_report,
                self.file_id,
                dry_run=self.dry_run
            )
            
            self.progress.emit(90)
            
            if result.success:
                self.status_update.emit("✅ Sincronização concluída com sucesso!")
                self.progress.emit(100)
            else:
                self.error.emit(f"Erros durante sincronização: {', '.join(result.errors)}")
            
            self.finished.emit(result)
        
        except Exception as e:
            self.error.emit(f"Erro inesperado: {str(e)}")


class ExcelSyncDialog(QDialog):
    """
    Dialog para sincronização de dados com SharePoint.
    
    Fluxo:
    1. Analisa diferenças
    2. Mostra preview das mudanças
    3. Usuário seleciona quais aplicar
    4. Executa sincronização
    5. Mostra resultado
    """
    
    sync_completed = pyqtSignal(object)  # Emite SyncResult quando finaliza
    
    def __init__(
        self,
        parent,
        diff_report,
        sync_service,
        excel_file_id: str,
        local_file_path: Path,
        comparator_service
    ):
        """
        Inicializa dialog de sincronização.
        
        Args:
            parent: Widget pai
            diff_report: DiffReport com as diferenças
            sync_service: ExcelSyncService para aplicar mudanças
            excel_file_id: ID do arquivo no SharePoint
            local_file_path: Caminho do arquivo Excel local
            comparator_service: ExcelComparatorService
        """
        super().__init__(parent)
        self.diff_report = diff_report
        self.sync_service = sync_service
        self.excel_file_id = excel_file_id
        self.local_file_path = local_file_path
        self.comparator_service = comparator_service
        self.sync_thread = None
        self.is_syncing = False
        
        self.setWindowTitle("Sincronização com SharePoint")
        self.setGeometry(100, 100, 1000, 700)
        
        self.init_ui()
        self.populate_data()
    
    def init_ui(self):
        """Inicializa interface"""
        layout = QVBoxLayout()
        
        # ===== Cabeçalho =====
        header_layout = QHBoxLayout()
        header_label = QLabel(f"📊 Sincronização: {self.diff_report.sheet_name}")
        header_font = header_label.font()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_layout.addWidget(header_label)
        layout.addLayout(header_layout)
        
        # ===== Resumo de mudanças =====
        summary_layout = QHBoxLayout()
        summary_text = (
            f"📈 Adições: {self.diff_report.additions_count} | "
            f"✏️  Atualizações: {self.diff_report.updates_count} | "
            f"🗑️  Deleções: {self.diff_report.deletions_count} | "
            f"⚠️  Conflitos: {self.diff_report.conflicts_count}"
        )
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        summary_layout.addWidget(summary_label)
        layout.addLayout(summary_layout)
        
        # ===== Tabs de visualização =====
        tabs = QTabWidget()
        
        # Tab 1: Atualizações
        self.updates_table = QTableWidget()
        self.updates_table.setColumnCount(4)
        self.updates_table.setHorizontalHeaderLabels(["Linha", "Coluna", "Valor Anterior", "Novo Valor"])
        self.updates_table.horizontalHeader().setStretchLastSection(True)
        tabs.addTab(self.updates_table, f"✏️  Atualizações ({self.diff_report.updates_count})")
        
        # Tab 2: Adições
        self.additions_table = QTableWidget()
        self.additions_table.setColumnCount(3)
        self.additions_table.setHorizontalHeaderLabels(["Linha", "Chave", "Status"])
        self.additions_table.horizontalHeader().setStretchLastSection(True)
        tabs.addTab(self.additions_table, f"➕ Adições ({self.diff_report.additions_count})")
        
        # Tab 3: Deleções
        self.deletions_table = QTableWidget()
        self.deletions_table.setColumnCount(3)
        self.deletions_table.setHorizontalHeaderLabels(["Linha", "Chave", "Status"])
        self.deletions_table.horizontalHeader().setStretchLastSection(True)
        tabs.addTab(self.deletions_table, f"🗑️  Deleções ({self.diff_report.deletions_count})")
        
        # Tab 4: Detalhes
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        tabs.addTab(self.details_text, "📋 Detalhes")
        
        layout.addWidget(tabs)
        
        # ===== Opções de sincronização =====
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Opções:"))
        
        self.dry_run_checkbox = QCheckBox("Simular (Dry-run)")
        self.dry_run_checkbox.setChecked(True)
        self.dry_run_checkbox.setToolTip("Valida mudanças sem aplicar")
        options_layout.addWidget(self.dry_run_checkbox)
        
        self.backup_checkbox = QCheckBox("Criar Backup")
        self.backup_checkbox.setChecked(True)
        self.backup_checkbox.setToolTip("Cria cópia antes de sincronizar")
        options_layout.addWidget(self.backup_checkbox)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # ===== Progresso =====
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("Progresso:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Pronto para sincronizar")
        self.status_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        progress_layout.addWidget(self.status_label)
        
        layout.addLayout(progress_layout)
        
        # ===== Botões =====
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.preview_btn = QPushButton("👁️  Preview JSON")
        self.preview_btn.clicked.connect(self.show_json_preview)
        button_layout.addWidget(self.preview_btn)
        
        self.sync_btn = QPushButton("🔄 Sincronizar")
        self.sync_btn.clicked.connect(self.start_sync)
        self.sync_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;"
        )
        button_layout.addWidget(self.sync_btn)
        
        self.cancel_btn = QPushButton("❌ Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def populate_data(self):
        """Preenche tabelas com dados de mudanças"""
        
        # Atualizações
        self.updates_table.setRowCount(0)
        for row_change in self.diff_report.updates:
            for cell_change in row_change.cells:
                row_pos = self.updates_table.rowCount()
                self.updates_table.insertRow(row_pos)
                
                self.updates_table.setItem(row_pos, 0, QTableWidgetItem(str(row_change.row_number)))
                self.updates_table.setItem(row_pos, 1, QTableWidgetItem(cell_change.column_name))
                
                old_item = QTableWidgetItem(str(cell_change.old_value)[:100])
                old_item.setBackground(QColor("#ffcccc"))
                self.updates_table.setItem(row_pos, 2, old_item)
                
                new_item = QTableWidgetItem(str(cell_change.new_value)[:100])
                new_item.setBackground(QColor("#ccffcc"))
                self.updates_table.setItem(row_pos, 3, new_item)
        
        # Adições
        self.additions_table.setRowCount(len(self.diff_report.additions))
        for row_pos, row_change in enumerate(self.diff_report.additions):
            self.additions_table.setItem(row_pos, 0, QTableWidgetItem(str(row_change.row_number)))
            self.additions_table.setItem(row_pos, 1, QTableWidgetItem(str(row_change.key_value)))
            status_item = QTableWidgetItem("✅ Novo")
            status_item.setBackground(QColor("#ccffcc"))
            self.additions_table.setItem(row_pos, 2, status_item)
        
        # Deleções
        self.deletions_table.setRowCount(len(self.diff_report.deletions))
        for row_pos, row_change in enumerate(self.diff_report.deletions):
            self.deletions_table.setItem(row_pos, 0, QTableWidgetItem(str(row_change.row_number)))
            self.deletions_table.setItem(row_pos, 1, QTableWidgetItem(str(row_change.key_value)))
            status_item = QTableWidgetItem("🗑️  Deletado")
            status_item.setBackground(QColor("#ffcccc"))
            self.deletions_table.setItem(row_pos, 2, status_item)
        
        # Detalhes
        details = f"""
📊 RELATÓRIO DE SINCRONIZAÇÃO
{'='*60}

Sheet: {self.diff_report.sheet_name}
Data: {self.diff_report.timestamp.strftime('%d/%m/%Y %H:%M:%S')}
Origem: {self.diff_report.source_local} → {self.diff_report.source_remote}

📈 RESUMO DE MUDANÇAS
Adições:     {self.diff_report.additions_count}
Atualizações: {self.diff_report.updates_count}
Deleções:    {self.diff_report.deletions_count}
Conflitos:   {self.diff_report.conflicts_count}
{'─'*60}
TOTAL:       {self.diff_report.total_changes}

⚠️  OBSERVAÇÕES
• Antes de sincronizar, um backup será criado
• Você pode reverter para a versão anterior se necessário
• Recomenda-se revisar todas as mudanças antes de aplicar
• A sincronização pode levar alguns minutos para arquivos grandes
        """
        self.details_text.setText(details)
    
    def show_json_preview(self):
        """Mostra preview em formato JSON"""
        json_str = self.comparator_service.export_diff_report(self.diff_report, format="json")
        
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Preview JSON")
        preview_dialog.setGeometry(150, 150, 800, 600)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setText(json_str)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_btn)
        
        preview_dialog.setLayout(layout)
        preview_dialog.exec()
    
    def start_sync(self):
        """Inicia processo de sincronização"""
        
        if self.is_syncing:
            QMessageBox.warning(self, "Aviso", "Sincronização já em andamento!")
            return
        
        # Confirmação
        reply = QMessageBox.question(
            self,
            "Confirmar Sincronização",
            f"Deseja sincronizar {self.diff_report.total_changes} mudanças?\n\n"
            f"Esta ação criará um backup antes de aplicar as mudanças.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Desabilitar botões
        self.is_syncing = True
        self.sync_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        
        # Criar e iniciar thread de sincronização
        dry_run = self.dry_run_checkbox.isChecked()
        self.sync_thread = SyncWorkerThread(
            self.sync_service,
            self.diff_report,
            self.excel_file_id,
            dry_run=dry_run
        )
        
        self.sync_thread.progress.connect(self.update_progress)
        self.sync_thread.status_update.connect(self.update_status)
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.error.connect(self.on_sync_error)
        
        self.sync_thread.start()
    
    def update_progress(self, value: int):
        """Atualiza barra de progresso"""
        self.progress_bar.setValue(value)
    
    def update_status(self, status: str):
        """Atualiza label de status"""
        self.status_label.setText(status)
    
    def on_sync_finished(self, result):
        """Sincronização finalizada com sucesso"""
        self.is_syncing = False
        self.sync_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "Sincronização Concluída",
            f"{result.get_summary()}\n\n"
            f"Mudanças aplicadas: {result.changes_applied}"
        )
        
        self.sync_completed.emit(result)
        self.accept()
    
    def on_sync_error(self, error_msg: str):
        """Erro durante sincronização"""
        self.is_syncing = False
        self.sync_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Erro na Sincronização", error_msg)
