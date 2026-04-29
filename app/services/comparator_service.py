"""Serviço de Comparação - Compara dados extraídos com SharePoint"""

import openpyxl
from openpyxl.utils import get_column_letter
from difflib import unified_diff
import csv
from app.models import db, Comparison, Report


class ComparatorService:
    
    @staticmethod
    def identify_new_rows(extracted_data, sharepoint_data, sheet_name):
        """
        Identifica linhas novas na comparação
        
        Uma linha é considerada "nova" se não existe no SharePoint
        Comparação: converte cada linha em tupla para comparação
        
        Args:
            extracted_data: {sheet_name: [[rows]]} do arquivo enviado
            sharepoint_data: {sheet_name: [[rows]]} do SharePoint
            sheet_name: Nome da sheet onde buscar dados
        
        Returns:
            [[new_rows]] apenas as linhas que não existem no SharePoint
        """
        try:
            # Pegar dados da sheet específica
            new_data = extracted_data.get(sheet_name, [])
            sp_data = sharepoint_data.get(sheet_name, [])
            
            if not new_data:
                return []
            
            # Converter SharePoint rows para set de tuplas para comparação rápida
            sp_rows_set = set()
            for row in sp_data[1:] if len(sp_data) > 1 else []:  # Pular header
                # Converter None para string vazia para comparação consistente
                clean_row = tuple(str(cell) if cell is not None else '' for cell in row)
                sp_rows_set.add(clean_row)
            
            # Identificar linhas novas
            new_rows = []
            new_row_indices = []
            for idx, row in enumerate(new_data[1:], start=2):  # Começar do 2 (line 1 é header)
                clean_row = tuple(str(cell) if cell is not None else '' for cell in row)
                
                # Se linha não existe no SharePoint, é nova
                if clean_row not in sp_rows_set:
                    new_rows.append(row)
                    new_row_indices.append(idx)
            
            return {
                'new_rows': new_rows,
                'new_row_indices': new_row_indices,
                'count': len(new_rows)
            }
        
        except Exception as e:
            raise Exception(f"Erro ao identificar linhas novas: {str(e)}")
    
    @staticmethod
    def compare_extracted_data(report_id, extracted_data, sharepoint_data):
        """
        Compara dados extraídos do arquivo com dados do SharePoint
        
        Args:
            report_id: ID do relatório
            extracted_data: {sheet_name: [[rows]]} do arquivo enviado
            sharepoint_data: {sheet_name: [[rows]]} do SharePoint
            
        Returns:
            {
                'differences_count': int,
                'differences': [
                    {
                        'sheet': 'Planilha1',
                        'row': 5,
                        'col': 'A',
                        'sharepoint_value': 'valor_antigo',
                        'new_value': 'valor_novo'
                    }
                ],
                'comparison_id': str
            }
        """
        try:
            differences = []
            
            # Comparar sheets comuns
            common_sheets = set(extracted_data.keys()) & set(sharepoint_data.keys())
            
            for sheet_name in common_sheets:
                new_rows = extracted_data[sheet_name]
                sp_rows = sharepoint_data[sheet_name]
                
                max_rows = max(len(new_rows), len(sp_rows))
                
                for row_idx in range(max_rows):
                    new_row = new_rows[row_idx] if row_idx < len(new_rows) else []
                    sp_row = sp_rows[row_idx] if row_idx < len(sp_rows) else []
                    
                    max_cols = max(len(new_row), len(sp_row))
                    
                    for col_idx in range(max_cols):
                        new_val = new_row[col_idx] if col_idx < len(new_row) else None
                        sp_val = sp_row[col_idx] if col_idx < len(sp_row) else None
                        
                        if new_val != sp_val:
                            differences.append({
                                'sheet': sheet_name,
                                'row': row_idx + 1,
                                'col': get_column_letter(col_idx + 1),
                                'sharepoint_value': str(sp_val) if sp_val is not None else '',
                                'new_value': str(new_val) if new_val is not None else ''
                            })
            
            # Registrar comparação no banco
            comparison = Comparison(
                report_id=report_id,
                differences_count=len(differences),
                differences_data={
                    'differences': differences,
                    'extracted_sheets': list(extracted_data.keys()),
                    'sharepoint_sheets': list(sharepoint_data.keys())
                }
            )
            db.session.add(comparison)
            db.session.commit()
            
            return {
                'differences_count': len(differences),
                'differences': differences,
                'comparison_id': comparison.id
            }
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao comparar dados: {str(e)}")
    
    @staticmethod
    def compare_excel_files(file_path_1, file_path_2, report_id=None):
        """
        Compara dois arquivos Excel e retorna as diferenças
        
        Args:
            file_path_1: Caminho do arquivo novo (enviado pelo usuário)
            file_path_2: Caminho do arquivo antigo (SharePoint)
            report_id: ID do relatório para registrar a comparação
            
        Returns:
            {
                'differences_count': int,
                'differences': [
                    {
                        'sheet': 'Planilha1',
                        'row': 5,
                        'col': 'A',
                        'current': 'valor_antigo',
                        'new': 'valor_novo'
                    }
                ],
                'comparison_id': str
            }
        """
        try:
            wb1 = openpyxl.load_workbook(file_path_1, data_only=True)
            wb2 = openpyxl.load_workbook(file_path_2, data_only=True)
            
            differences = []
            
            # Comparar planilhas comuns
            common_sheets = set(wb1.sheetnames) & set(wb2.sheetnames)
            
            for sheet_name in common_sheets:
                ws1 = wb1[sheet_name]
                ws2 = wb2[sheet_name]
                
                # Encontrar dimensões máximas
                max_row = max(ws1.max_row, ws2.max_row)
                max_col = max(ws1.max_column, ws2.max_column)
                
                for row in range(1, max_row + 1):
                    for col in range(1, max_col + 1):
                        cell1 = ws1.cell(row, col).value
                        cell2 = ws2.cell(row, col).value
                        
                        if cell1 != cell2:
                            differences.append({
                                'sheet': sheet_name,
                                'row': row,
                                'col': get_column_letter(col),
                                'current': str(cell2) if cell2 is not None else '',
                                'new': str(cell1) if cell1 is not None else ''
                            })
            
            # Registrar comparação no banco
            comparison = None
            if report_id:
                comparison = Comparison(
                    report_id=report_id,
                    differences_count=len(differences),
                    differences_data={'differences': differences}
                )
                db.session.add(comparison)
                db.session.commit()
            
            return {
                'differences_count': len(differences),
                'differences': differences,
                'comparison_id': comparison.id if comparison else None
            }
            
        except Exception as e:
            raise Exception(f"Erro ao comparar arquivos: {str(e)}")
    
    @staticmethod
    def compare_csv_files(file_path_1, file_path_2, report_id=None):
        """Compara dois arquivos CSV"""
        try:
            with open(file_path_1, 'r', encoding='utf-8') as f1, \
                 open(file_path_2, 'r', encoding='utf-8') as f2:
                
                rows1 = list(csv.reader(f1))
                rows2 = list(csv.reader(f2))
                
                differences = []
                max_rows = max(len(rows1), len(rows2))
                
                for row_idx in range(max_rows):
                    row1 = rows1[row_idx] if row_idx < len(rows1) else []
                    row2 = rows2[row_idx] if row_idx < len(rows2) else []
                    
                    max_cols = max(len(row1), len(row2))
                    
                    for col_idx in range(max_cols):
                        val1 = row1[col_idx] if col_idx < len(row1) else ''
                        val2 = row2[col_idx] if col_idx < len(row2) else ''
                        
                        if val1 != val2:
                            differences.append({
                                'row': row_idx + 1,
                                'col': col_idx + 1,
                                'current': val2,
                                'new': val1
                            })
            
            comparison = None
            if report_id:
                comparison = Comparison(
                    report_id=report_id,
                    differences_count=len(differences),
                    differences_data={'differences': differences}
                )
                db.session.add(comparison)
                db.session.commit()
            
            return {
                'differences_count': len(differences),
                'differences': differences,
                'comparison_id': comparison.id if comparison else None
            }
        except Exception as e:
            raise Exception(f"Erro ao comparar CSV: {str(e)}")
    
    @staticmethod
    def get_comparison(comparison_id):
        """Retorna detalhes de uma comparação"""
        return Comparison.query.get(comparison_id)
    
    @staticmethod
    def format_differences_for_display(differences):
        """Formata diferenças para exibição em HTML"""
        by_sheet = {}
        for diff in differences:
            sheet = diff.get('sheet', 'Geral')
            if sheet not in by_sheet:
                by_sheet[sheet] = []
            by_sheet[sheet].append(diff)
        return by_sheet
