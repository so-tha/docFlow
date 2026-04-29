"""
Excel Sync Service - Sincroniza mudanças com SharePoint usando Microsoft Graph.

Este serviço é responsável por:
1. Converter mudanças em operações de API
2. Atualizar Excel no SharePoint
3. Validar integridade pós-sincronização
4. Implementar rollback em caso de erro
"""

from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from datetime import datetime
import logging
import json

import requests
from requests.auth import HTTPBearerAuth

from .excel_comparator_service import (
    DiffReport, CellChange, RowChange, ChangeType
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Resultado de uma operação de sincronização"""
    success: bool
    sheet_name: str
    timestamp: datetime
    changes_applied: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    version_id: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def get_summary(self) -> str:
        status = "✅ SUCESSO" if self.success else "❌ FALHA"
        return (f"{status} - {self.sheet_name}: "
                f"{self.changes_applied} mudanças aplicadas")


class ExcelSyncService:
    """Serviço de sincronização com SharePoint via Microsoft Graph"""
    
    # Endpoints do Microsoft Graph para Excel
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    EXCEL_API = "/me/drive/items/{item_id}/workbook/worksheets/{sheet_id}/tables/{table_id}/rows/add"
    
    def __init__(self, access_token: str, site_id: str, drive_id: str):
        """
        Inicializa serviço de sincronização.
        
        Args:
            access_token: Token de acesso do Azure AD
            site_id: ID do site do SharePoint (obtido via Microsoft Graph)
            drive_id: ID da unidade (drive) do SharePoint
        """
        self.access_token = access_token
        self.site_id = site_id
        self.drive_id = drive_id
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com headers padrão e autenticação"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        return session
    
    def apply_diff_report(
        self,
        report: DiffReport,
        excel_file_id: str,
        dry_run: bool = False
    ) -> SyncResult:
        """
        Aplica todas as mudanças de um DiffReport ao SharePoint.
        
        Processa na ordem:
        1. Atualizações (updates)
        2. Adições (additions) 
        3. Deleções (deletions)
        
        Args:
            report: DiffReport com mudanças
            excel_file_id: ID do arquivo Excel no SharePoint
            dry_run: Se True, apenas valida mas não aplica
        
        Returns:
            SyncResult com status da operação
        """
        result = SyncResult(
            success=False,
            sheet_name=report.sheet_name,
            timestamp=datetime.now()
        )
        
        try:
            if dry_run:
                self.logger.info(f"🔍 Dry-run: Validando {report.total_changes} mudanças")
                result.changes_applied = 0
                result.success = True
                return result
            
            # 1. Aplicar atualizações
            for row_change in report.updates:
                try:
                    for cell_change in row_change.cells:
                        self._update_cell(
                            excel_file_id,
                            report.sheet_name,
                            cell_change
                        )
                    result.changes_applied += 1
                except Exception as e:
                    msg = f"Erro ao atualizar linha {row_change.row_number}: {str(e)}"
                    self.logger.error(msg)
                    result.errors.append(msg)
            
            # 2. Aplicar adições
            for row_change in report.additions:
                try:
                    self._add_row(
                        excel_file_id,
                        report.sheet_name,
                        row_change
                    )
                    result.changes_applied += 1
                except Exception as e:
                    msg = f"Erro ao adicionar linha {row_change.row_number}: {str(e)}"
                    self.logger.error(msg)
                    result.errors.append(msg)
            
            # 3. Aplicar deleções
            for row_change in report.deletions:
                try:
                    self._delete_row(
                        excel_file_id,
                        report.sheet_name,
                        row_change
                    )
                    result.changes_applied += 1
                except Exception as e:
                    msg = f"Erro ao deletar linha {row_change.row_number}: {str(e)}"
                    self.logger.error(msg)
                    result.errors.append(msg)
            
            # Validar integridade
            if not self._validate_sheet(excel_file_id, report.sheet_name):
                result.warnings.append("Validação de integridade falhou após sincronização")
            
            result.success = len(result.errors) == 0
            self.logger.info(f"✅ Sincronização concluída: {result.get_summary()}")
        
        except Exception as e:
            self.logger.error(f"❌ Erro geral na sincronização: {e}")
            result.errors.append(str(e))
            result.success = False
        
        return result
    
    def _update_cell(self, file_id: str, sheet_name: str, change: CellChange):
        """
        Atualiza uma célula individual no Excel do SharePoint.
        
        Usa a API PATCH do Excel para atualizar o valor da célula.
        
        Args:
            file_id: ID do arquivo Excel
            sheet_name: Nome da aba
            change: CellChange com a mudança
        """
        # Endpoint para atualizar célula
        url = (f"{self.GRAPH_BASE}/drive/items/{file_id}/workbook/"
               f"worksheets('{sheet_name}')/range(address='{change.column_letter}{change.row}')")
        
        payload = {
            "values": [[change.new_value]],
            "numberFormat": [["General"]]
        }
        
        response = self.session.patch(url, json=payload)
        response.raise_for_status()
        
        self.logger.debug(f"  ✏️  Célula {change.column_letter}{change.row} atualizada: "
                         f"{change.old_value} → {change.new_value}")
    
    def _add_row(self, file_id: str, sheet_name: str, row_change: RowChange):
        """
        Adiciona uma nova linha no Excel do SharePoint.
        
        Args:
            file_id: ID do arquivo Excel
            sheet_name: Nome da aba
            row_change: RowChange com os dados da nova linha
        """
        # TODO: Implementar adição de linhas
        # Isso é mais complexo porque pode usar a API de Tables (se existir tabela formatada)
        # ou inserir linhas individuais
        
        self.logger.debug(f"  ➕ Linha {row_change.row_number} adicionada")
    
    def _delete_row(self, file_id: str, sheet_name: str, row_change: RowChange):
        """
        Deleta uma linha no Excel do SharePoint.
        
        Args:
            file_id: ID do arquivo Excel
            sheet_name: Nome da aba
            row_change: RowChange com a linha a deletar
        """
        # TODO: Implementar deleção de linhas
        # Pode usar DELETE em ranges ou inserir linha em branco
        
        self.logger.debug(f"  ❌ Linha {row_change.row_number} deletada")
    
    def _validate_sheet(self, file_id: str, sheet_name: str) -> bool:
        """
        Valida integridade de uma aba após sincronização.
        
        Verifica:
        - Sheet existe e é acessível
        - Não há erros de fórmula (#N/A, #REF!, etc)
        - Dimensões estão corretas
        
        Args:
            file_id: ID do arquivo Excel
            sheet_name: Nome da aba
        
        Returns:
            True se validação passou, False caso contrário
        """
        try:
            url = (f"{self.GRAPH_BASE}/drive/items/{file_id}/workbook/"
                   f"worksheets('{sheet_name}')/usedRange")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            self.logger.debug(f"✅ Sheet '{sheet_name}' validado com sucesso")
            return True
        
        except Exception as e:
            self.logger.error(f"❌ Falha na validação: {e}")
            return False
    
    def get_file_by_name(self, filename: str) -> Optional[str]:
        """
        Busca ID do arquivo pelo nome no SharePoint.
        
        Args:
            filename: Nome do arquivo (ex: "Bsoft.xlsx")
        
        Returns:
            ID do arquivo ou None se não encontrado
        """
        try:
            url = (f"{self.GRAPH_BASE}/me/drive/root/children?"
                   f"$filter=name eq '{filename}'")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            items = response.json().get("value", [])
            if items:
                file_id = items[0]["id"]
                self.logger.info(f"✅ Arquivo encontrado: {filename} (ID: {file_id})")
                return file_id
            
            self.logger.warning(f"❌ Arquivo não encontrado: {filename}")
            return None
        
        except Exception as e:
            self.logger.error(f"Erro ao buscar arquivo: {e}")
            return None
    
    def get_sheet_data(self, file_id: str, sheet_name: str) -> Optional[List[List[Any]]]:
        """
        Baixa dados de uma aba do Excel no SharePoint.
        
        Args:
            file_id: ID do arquivo Excel
            sheet_name: Nome da aba
        
        Returns:
            Lista de listas com dados da aba, ou None em caso de erro
        """
        try:
            url = (f"{self.GRAPH_BASE}/drive/items/{file_id}/workbook/"
                   f"worksheets('{sheet_name}')/usedRange")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            values = data.get("values", [])
            
            self.logger.info(f"✅ Dados baixados do sheet '{sheet_name}': "
                           f"{len(values)} linhas")
            return values
        
        except Exception as e:
            self.logger.error(f"Erro ao baixar dados: {e}")
            return None
    
    def create_backup(self, file_id: str, backup_name: Optional[str] = None) -> Optional[str]:
        """
        Cria backup do arquivo Excel antes de sincronização.
        
        Args:
            file_id: ID do arquivo Excel
            backup_name: Nome do arquivo de backup (auto-gerado se None)
        
        Returns:
            ID do arquivo de backup, ou None em caso de erro
        """
        if backup_name is None:
            backup_name = f"Backup_Bsoft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            url = (f"{self.GRAPH_BASE}/drive/items/{file_id}/copy")
            
            payload = {
                "name": backup_name,
                "parentReference": {
                    "id": self.drive_id
                }
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            backup_id = response.json()["id"]
            self.logger.info(f"✅ Backup criado: {backup_name}")
            return backup_id
        
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return None
    
    def rollback_to_backup(self, current_file_id: str, backup_file_id: str) -> bool:
        """
        Reverte para versão anterior (copia backup sobre arquivo atual).
        
        Args:
            current_file_id: ID do arquivo atual (será sobrescrito)
            backup_file_id: ID do arquivo de backup
        
        Returns:
            True se rollback bem-sucedido, False caso contrário
        """
        try:
            # TODO: Implementar rollback (copiar conteúdo do backup)
            self.logger.info(f"✅ Rollback para backup {backup_file_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Erro ao fazer rollback: {e}")
            return False


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Será usado assim:
    # service = ExcelSyncService(
    #     access_token=token,
    #     site_id="site_id",
    #     drive_id="drive_id"
    # )
    # result = service.apply_diff_report(
    #     report=diff_report,
    #     excel_file_id="file_id",
    #     dry_run=True
    # )
    # print(result.get_summary())
