"""
Excel Comparator Service - Compara dados entre Excel local e SharePoint.

Este serviço é responsável por:
1. Ler arquivo Excel local (múltiplas abas)
2. Baixar dados do SharePoint
3. Comparar estrutura e dados
4. Gerar relatório de diferenças
"""

from typing import Dict, List, Tuple, Any, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging
from enum import Enum

import pandas as pd
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Tipos de mudanças detectadas"""
    ADD = "add"           # Nova linha/célula
    UPDATE = "update"     # Valor modificado
    DELETE = "delete"     # Linha/célula removida
    CONFLICT = "conflict" # Conflito entre versões


@dataclass
class CellChange:
    """Representa mudança em uma célula individual"""
    row: int
    column: int
    column_letter: str
    column_name: str
    old_value: Any = None
    new_value: Any = None
    change_type: ChangeType = ChangeType.UPDATE
    severity: Literal["low", "medium", "high"] = "medium"  # Para UI prioritization
    
    def __str__(self) -> str:
        return (f"Cell {self.column_letter}{self.row}: "
                f"{self.column_name} = {self.new_value} (was {self.old_value})")


@dataclass
class RowChange:
    """Representa mudanças em uma linha completa"""
    row_number: int
    key_value: Any  # Valor da coluna chave (p.ex. código do cliente)
    cells: List[CellChange] = field(default_factory=list)
    change_type: ChangeType = ChangeType.UPDATE
    
    def __str__(self) -> str:
        return f"Row {self.row_number} ({self.key_value}): {len(self.cells)} changes"


@dataclass
class DiffReport:
    """Relatório completo de diferenças entre duas fontes"""
    sheet_name: str
    timestamp: datetime
    source_local: str
    source_remote: str
    
    # Estatísticas
    total_changes: int = 0
    additions_count: int = 0
    updates_count: int = 0
    deletions_count: int = 0
    conflicts_count: int = 0
    
    # Dados de mudança
    additions: List[RowChange] = field(default_factory=list)
    updates: List[RowChange] = field(default_factory=list)
    deletions: List[RowChange] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate_totals(self):
        """Recalcula contadores"""
        self.additions_count = len(self.additions)
        self.updates_count = len(self.updates)
        self.deletions_count = len(self.deletions)
        self.conflicts_count = len(self.conflicts)
        self.total_changes = sum([
            self.additions_count,
            self.updates_count,
            self.deletions_count,
            self.conflicts_count
        ])
    
    def has_changes(self) -> bool:
        """Retorna True se há alguma mudança"""
        return self.total_changes > 0
    
    def has_conflicts(self) -> bool:
        """Retorna True se há conflitos"""
        return self.conflicts_count > 0
    
    def get_summary(self) -> str:
        """Retorna resumo em texto"""
        return (f"Sheet '{self.sheet_name}': "
                f"{self.additions_count} additions, "
                f"{self.updates_count} updates, "
                f"{self.deletions_count} deletions, "
                f"{self.conflicts_count} conflicts")


class ExcelComparatorService:
    """Serviço de comparação de dados Excel entre local e SharePoint"""
    
    def __init__(self, key_column: str = "Código"):
        """
        Inicializa serviço de comparação.
        
        Args:
            key_column: Coluna para usar como chave única (default: "Código")
        """
        self.key_column = key_column
        self.logger = logging.getLogger(__name__)
    
    def read_local_excel(self, filepath: Path, sheet_name: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Lê arquivo Excel local.
        
        Args:
            filepath: Caminho do arquivo Excel
            sheet_name: Se fornecido, lê apenas essa aba. Se None, lê todas.
        
        Returns:
            Dict com {sheet_name: DataFrame}
        
        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se arquivo não é Excel válido
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        try:
            if sheet_name:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                self.logger.info(f"✅ Lido sheet '{sheet_name}' com {len(df)} linhas")
                return {sheet_name: df}
            else:
                # Lê todas as abas
                excel_file = pd.ExcelFile(filepath)
                sheets = {}
                for name in excel_file.sheet_names:
                    df = pd.read_excel(filepath, sheet_name=name)
                    sheets[name] = df
                    self.logger.info(f"✅ Lido sheet '{name}' com {len(df)} linhas")
                return sheets
        
        except Exception as e:
            self.logger.error(f"❌ Erro ao ler Excel: {e}")
            raise ValueError(f"Erro ao ler Excel: {e}")
    
    def read_sharepoint_csv(self, csv_content: str, sep: str = ";") -> pd.DataFrame:
        """
        Lê dados do SharePoint (CSV).
        
        Args:
            csv_content: Conteúdo do CSV (string)
            sep: Separador (default: ";")
        
        Returns:
            DataFrame com dados
        """
        from io import StringIO
        
        try:
            df = pd.read_csv(StringIO(csv_content), sep=sep, encoding="latin-1")
            self.logger.info(f"✅ CSV carregado com {len(df)} linhas")
            return df
        except Exception as e:
            self.logger.error(f"❌ Erro ao ler CSV: {e}")
            raise ValueError(f"Erro ao ler CSV: {e}")
    
    def compare_dataframes(
        self,
        local_df: pd.DataFrame,
        remote_df: pd.DataFrame,
        sheet_name: str = "Sheet1"
    ) -> DiffReport:
        """
        Compara dois DataFrames (local vs remoto).
        
        Estratégia:
        1. Identifica coluna chave
        2. Encontra linhas novas (em local, não em remote)
        3. Encontra linhas deletadas (em remote, não em local)
        4. Para linhas comuns, compara células
        5. Detecta conflitos
        
        Args:
            local_df: DataFrame local
            remote_df: DataFrame remoto
            sheet_name: Nome da aba para o relatório
        
        Returns:
            DiffReport com todas as diferenças
        """
        report = DiffReport(
            sheet_name=sheet_name,
            timestamp=datetime.now(),
            source_local="Excel Local",
            source_remote="SharePoint"
        )
        
        # Verificar se coluna chave existe
        if self.key_column not in local_df.columns:
            self.logger.warning(f"⚠️  Coluna chave '{self.key_column}' não encontrada em local")
        if self.key_column not in remote_df.columns:
            self.logger.warning(f"⚠️  Coluna chave '{self.key_column}' não encontrada em remoto")
        
        # Se não há coluna chave, usar índice
        key_col = self.key_column if self.key_column in local_df.columns else None
        
        # Converter NaN para None para comparação
        local_df = local_df.where(pd.notna(local_df), None)
        remote_df = remote_df.where(pd.notna(remote_df), None)
        
        if key_col:
            local_keys = set(local_df[key_col].dropna())
            remote_keys = set(remote_df[key_col].dropna())
        else:
            local_keys = set(range(len(local_df)))
            remote_keys = set(range(len(remote_df)))
        
        # 1. Detectar adições (em local, não em remote)
        added_keys = local_keys - remote_keys
        for key in added_keys:
            if key_col:
                row_data = local_df[local_df[key_col] == key].iloc[0]
                row_num = local_df[local_df[key_col] == key].index[0] + 2  # +2 para incluir header
            else:
                row_data = local_df.iloc[key]
                row_num = key + 2
            
            row_change = RowChange(
                row_number=row_num,
                key_value=key,
                change_type=ChangeType.ADD
            )
            report.additions.append(row_change)
        
        # 2. Detectar deleções (em remote, não em local)
        deleted_keys = remote_keys - local_keys
        for key in deleted_keys:
            if key_col:
                row_data = remote_df[remote_df[key_col] == key].iloc[0]
                row_num = remote_df[remote_df[key_col] == key].index[0] + 2
            else:
                row_data = remote_df.iloc[key]
                row_num = key + 2
            
            row_change = RowChange(
                row_number=row_num,
                key_value=key,
                change_type=ChangeType.DELETE
            )
            report.deletions.append(row_change)
        
        # 3. Comparar linhas comuns para detectar atualizações
        common_keys = local_keys & remote_keys
        for key in common_keys:
            if key_col:
                local_row = local_df[local_df[key_col] == key].iloc[0]
                remote_row = remote_df[remote_df[key_col] == key].iloc[0]
                row_num = local_df[local_df[key_col] == key].index[0] + 2
            else:
                local_row = local_df.iloc[key]
                remote_row = remote_df.iloc[key]
                row_num = key + 2
            
            # Comparar coluna por coluna
            cells_changed = []
            for col_idx, col_name in enumerate(local_df.columns, 1):
                if col_name in remote_df.columns:
                    local_val = local_row[col_name]
                    remote_val = remote_row[col_name]
                    
                    if local_val != remote_val:
                        cell_change = CellChange(
                            row=row_num,
                            column=col_idx,
                            column_letter=self._num_to_col(col_idx),
                            column_name=col_name,
                            old_value=remote_val,
                            new_value=local_val,
                            change_type=ChangeType.UPDATE
                        )
                        cells_changed.append(cell_change)
            
            if cells_changed:
                row_change = RowChange(
                    row_number=row_num,
                    key_value=key,
                    cells=cells_changed,
                    change_type=ChangeType.UPDATE
                )
                report.updates.append(row_change)
        
        report.calculate_totals()
        self.logger.info(f"✅ Comparação concluída: {report.get_summary()}")
        return report
    
    def _num_to_col(self, num: int) -> str:
        """Converte número de coluna para letra (1 -> A, 27 -> AA)"""
        result = ""
        while num > 0:
            num -= 1
            result = chr(65 + num % 26) + result
            num //= 26
        return result
    
    def compare_sheet_versions(
        self,
        local_excel_path: Path,
        sharepoint_csv_content: str,
        sheet_name: str = "DATABASE"
    ) -> DiffReport:
        """
        Fluxo completo: Lê local + remoto, compara, retorna relatório.
        
        Args:
            local_excel_path: Caminho do Excel local
            sharepoint_csv_content: Conteúdo CSV do SharePoint
            sheet_name: Nome da aba para ler do Excel local
        
        Returns:
            DiffReport completo
        """
        # 1. Ler dados locais
        local_sheets = self.read_local_excel(local_excel_path, sheet_name=sheet_name)
        local_df = local_sheets[sheet_name]
        
        # 2. Ler dados remotos
        remote_df = self.read_sharepoint_csv(sharepoint_csv_content)
        
        # 3. Comparar
        report = self.compare_dataframes(local_df, remote_df, sheet_name)
        
        return report
    
    def export_diff_report(self, report: DiffReport, format: Literal["json", "csv", "html"] = "json") -> str:
        """
        Exporta relatório de diferenças em vários formatos.
        
        Args:
            report: DiffReport a exportar
            format: Formato de saída
        
        Returns:
            String com conteúdo formatado
        """
        if format == "json":
            import json
            data = {
                "sheet_name": report.sheet_name,
                "timestamp": report.timestamp.isoformat(),
                "summary": report.get_summary(),
                "totals": {
                    "additions": report.additions_count,
                    "updates": report.updates_count,
                    "deletions": report.deletions_count,
                    "conflicts": report.conflicts_count
                },
                "additions": [
                    {"row": r.row_number, "key": str(r.key_value)}
                    for r in report.additions
                ],
                "updates": [
                    {
                        "row": r.row_number,
                        "key": str(r.key_value),
                        "changes": [
                            {"column": c.column_name, "old": str(c.old_value), "new": str(c.new_value)}
                            for c in r.cells
                        ]
                    }
                    for r in report.updates
                ],
                "deletions": [
                    {"row": r.row_number, "key": str(r.key_value)}
                    for r in report.deletions
                ]
            }
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif format == "csv":
            lines = [
                f"Sheet,Row,Type,Key,Column,OldValue,NewValue",
            ]
            for row_change in report.additions:
                lines.append(f"{report.sheet_name},{row_change.row_number},ADD,{row_change.key_value},,,,")
            for row_change in report.updates:
                for cell_change in row_change.cells:
                    lines.append(
                        f"{report.sheet_name},{row_change.row_number},UPDATE,{row_change.key_value},"
                        f"{cell_change.column_name},{cell_change.old_value},{cell_change.new_value}"
                    )
            for row_change in report.deletions:
                lines.append(f"{report.sheet_name},{row_change.row_number},DELETE,{row_change.key_value},,,,")
            return "\n".join(lines)
        
        elif format == "html":
            html = f"<h2>Relatório de Sincronização: {report.sheet_name}</h2>"
            html += f"<p><strong>Data:</strong> {report.timestamp.isoformat()}</p>"
            html += f"<p><strong>Resumo:</strong> {report.get_summary()}</p>"
            
            if report.additions:
                html += f"<h3>Adições ({len(report.additions)})</h3><ul>"
                for row in report.additions:
                    html += f"<li>Linha {row.row_number}: {row.key_value}</li>"
                html += "</ul>"
            
            if report.updates:
                html += f"<h3>Atualizações ({len(report.updates)})</h3><ul>"
                for row in report.updates:
                    html += f"<li>Linha {row.row_number}: {row.key_value} ({len(row.cells)} mudanças)</li>"
                html += "</ul>"
            
            if report.deletions:
                html += f"<h3>Deleções ({len(report.deletions)})</h3><ul>"
                for row in report.deletions:
                    html += f"<li>Linha {row.row_number}: {row.key_value}</li>"
                html += "</ul>"
            
            return html
        
        else:
            raise ValueError(f"Formato não suportado: {format}")
    
    def detect_duplicate_rows(self, new_file_path: str) -> dict:
        """
        Detecta linhas duplicadas entre novo arquivo e relatórios existentes.
        
        Args:
            new_file_path: Caminho do novo arquivo a verificar
        
        Returns:
            Dict com:
            - has_duplicates: bool
            - duplicate_count: int
            - duplicated_reports: list com IDs dos relatórios que têm duplicatas
            - message: str com resumo
        """
        try:
            from src.core import get_session
            from src.core.models import Report
            import hashlib
            
            # Ler novo arquivo
            local_sheets = self.read_local_excel(Path(new_file_path))
            
            # Extrair todas as linhas do novo arquivo como hashes
            new_file_hashes = set()
            new_file_rows = []
            
            for sheet_name, df in local_sheets.items():
                for idx, row in df.iterrows():
                    # Converter linha para string e fazer hash
                    row_str = "|".join(str(v) for v in row.values)
                    row_hash = hashlib.md5(row_str.encode()).hexdigest()
                    new_file_hashes.add(row_hash)
                    new_file_rows.append({
                        'sheet': sheet_name,
                        'row_num': idx + 2,  # Excel começa em 1, header é linha 1
                        'hash': row_hash,
                        'data': row_str[:100]  # Primeiros 100 chars para debug
                    })
            
            # Buscar todos os relatórios já existentes
            session = get_session()
            existing_reports = session.query(Report).all()
            
            duplicated_reports = []
            duplicate_count = 0
            
            # Comparar com cada relatório existente
            for report in existing_reports:
                try:
                    # Ler arquivo do relatório existente
                    if not Path(report.file_path).exists():
                        continue
                    
                    existing_sheets = self.read_local_excel(Path(report.file_path))
                    
                    # Extrair hashes do arquivo existente
                    existing_hashes = set()
                    for sheet_name, df in existing_sheets.items():
                        for idx, row in df.iterrows():
                            row_str = "|".join(str(v) for v in row.values)
                            row_hash = hashlib.md5(row_str.encode()).hexdigest()
                            existing_hashes.add(row_hash)
                    
                    # Encontrar interseção (linhas que existem em ambos)
                    common_hashes = new_file_hashes & existing_hashes
                    
                    if common_hashes:
                        duplicate_count += len(common_hashes)
                        duplicated_reports.append({
                            'report_id': report.id,
                            'filename': report.original_filename,
                            'duplicate_rows': len(common_hashes)
                        })
                
                except Exception as e:
                    self.logger.warning(f"Erro ao comparar com relatório {report.id}: {str(e)}")
                    continue
            
            session.close()
            
            has_duplicates = len(duplicated_reports) > 0
            
            return {
                'has_duplicates': has_duplicates,
                'duplicate_count': duplicate_count,
                'duplicated_reports': duplicated_reports,
                'message': (
                    f"⚠️ Encontradas {duplicate_count} linhas duplicadas em {len(duplicated_reports)} relatório(s)"
                    if has_duplicates
                    else "✅ Nenhuma linha duplicada encontrada"
                )
            }
        
        except Exception as e:
            self.logger.error(f"Erro ao detectar duplicatas: {str(e)}")
            return {
                'has_duplicates': False,
                'duplicate_count': 0,
                'duplicated_reports': [],
                'message': f"⚠️ Erro ao verificar duplicatas: {str(e)}"
            }


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Será usado assim:
    # service = ExcelComparatorService(key_column="Código")
    # report = service.compare_sheet_versions(
    #     local_excel_path=Path("/path/to/Bsoft.xlsx"),
    #     sharepoint_csv_content=csv_data,
    #     sheet_name="DATABASE"
    # )
    # print(report.get_summary())
