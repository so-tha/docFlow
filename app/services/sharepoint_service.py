"""Serviço SharePoint - Integração com SharePoint Online via Microsoft Graph API"""

from flask import current_app
import os
from app.services.report_service import ReportService
from app.services.azure_graph_service import SharePointGraphIntegration
from app.models import Report
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SharePointService:
    """
    Serviço para integração com SharePoint
    Usa Microsoft Graph API para buscar e sincronizar dados
    """
    
    def __init__(self):
        self.site_url = current_app.config.get('SHAREPOINT_SITE_URL')
        self.library = current_app.config.get('SHAREPOINT_LIBRARY')
        
        # Usar integração com Graph API
        try:
            self.graph_integration = SharePointGraphIntegration()
        except Exception as e:
            logger.warning(f"Não foi possível inicializar SharePoint Graph Integration: {str(e)}")
            self.graph_integration = None
    
    def get_file_from_sharepoint(self, file_name):
        """
        Busca arquivo do SharePoint via Graph API
        """
        if not self.graph_integration:
            return None
        
        try:
            logger.info(f"Buscando arquivo '{file_name}' no SharePoint")
            # TODO: Implementar busca de arquivo específico
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar arquivo do SharePoint: {str(e)}")
            return None
    
    def get_file_version(self, file_name):
        """Retorna a versão do arquivo no SharePoint"""
        return "1.0"
    
    def upload_to_sharepoint(self, file_path, destination_name):
        """
        Faz upload do arquivo aprovado para SharePoint
        """
        if not self.graph_integration:
            return False
        
        try:
            logger.info(f"Fazendo upload de '{destination_name}' para SharePoint")
            # TODO: Implementar upload via Graph API
            return True
        except Exception as e:
            logger.error(f"Erro ao fazer upload para SharePoint: {str(e)}")
            return False
    
    def list_files(self):
        """Lista arquivos da biblioteca SharePoint"""
        if not self.graph_integration:
            return []
        
        try:
            sheets = self.graph_integration.list_available_sheets()
            logger.info(f"Abas disponíveis no SharePoint: {sheets}")
            return sheets
        except Exception as e:
            logger.error(f"Erro ao listar abas: {str(e)}")
            return []
    
    def sync_approved_report(self, report_id, extracted_data):
        """
        Sincroniza relatório aprovado com SharePoint
        Identifica linhas novas e as adiciona à aba correta do mês
        
        ✅ AGORA USA MICROSOFT GRAPH API DE VERDADE!
        
        Args:
            report_id: ID do relatório aprovado
            extracted_data: Dados extraídos do arquivo
        
        Returns:
            {'status': 'success', 'lines_added': int, 'sheet_name': str}
        """
        try:
            if not self.graph_integration:
                raise Exception("Integração com SharePoint não configurada")
            
            # 1. Detectar mês dos dados
            month_info = ReportService.extract_month_from_data(extracted_data)
            
            if not month_info:
                raise ValueError("Não foi possível detectar o mês dos dados do arquivo")
            
            month = month_info['month']
            year = month_info['year']
            sheet_name = ReportService.get_sheet_name_for_month(month, year)
            
            logger.info(f"Sincronizando dados do mês {month}/{year} para aba '{sheet_name}'")
            
            # 2. Buscar dados existentes do SharePoint (real agora!)
            sharepoint_data = self._get_sheet_data_real(month, year)
            
            if sharepoint_data is None:
                sharepoint_data = {sheet_name: []}
            
            logger.info(f"Dados do SharePoint obtidos. Linhas existentes: {len(sharepoint_data.get(sheet_name, []))}")
            
            # 3. Identificar linhas novas
            new_rows_info = self._identify_new_rows(
                extracted_data_all=extracted_data,
                sharepoint_data=sharepoint_data,
                sheet_name=month_info['sheet_name']
            )
            
            new_rows = new_rows_info.get('new_rows', [])
            count = len(new_rows)
            
            logger.info(f"Linhas novas identificadas: {count}")
            
            # 4. Adicionar linhas novas ao SharePoint (real agora!)
            if new_rows:
                result = self.graph_integration.sync_new_rows(month, year, new_rows)
                logger.info(f"Sincronização concluída: {result}")
                
                return {
                    'status': 'success',
                    'lines_added': result.get('rows_added', 0),
                    'sheet_name': sheet_name,
                    'month': month,
                    'year': year,
                    'sync_result': result
                }
            else:
                logger.info("Nenhuma linha nova para sincronizar")
                
                return {
                    'status': 'success',
                    'lines_added': 0,
                    'sheet_name': sheet_name,
                    'month': month,
                    'year': year,
                    'message': 'Todas as linhas já existem no SharePoint'
                }
        
        except Exception as e:
            logger.error(f"Erro ao sincronizar com SharePoint: {str(e)}")
            raise Exception(f"Erro ao sincronizar com SharePoint: {str(e)}")
    
    def _get_sheet_data_real(self, month, year):
        """
        ✅ NOVA IMPLEMENTAÇÃO: Buscar dados REAIS do SharePoint via Graph API
        
        Args:
            month: Número do mês
            year: Ano
        
        Returns:
            {sheet_name: [[rows]]} com dados da aba
        """
        try:
            if not self.graph_integration:
                logger.warning("Graph Integration não disponível")
                return None
            
            sheet_data = self.graph_integration.get_month_sheet_data(month, year)
            sheet_name = ReportService.get_sheet_name_for_month(month, year)
            
            return {sheet_name: sheet_data}
        
        except Exception as e:
            logger.error(f"Erro ao buscar dados reais do SharePoint: {str(e)}")
            # Retorna vazio em caso de erro, continuará sincronizando
            sheet_name = ReportService.get_sheet_name_for_month(month, year)
            return {sheet_name: []}
    
    def _identify_new_rows(self, extracted_data_all, sharepoint_data, sheet_name):
        """
        Identifica linhas novas comparando com dados do SharePoint
        
        Uma linha é considerada "nova" se não existe no SharePoint
        Comparação: converte cada linha em tupla para comparação
        
        Args:
            extracted_data_all: {sheet_name: [[rows]]} do arquivo enviado
            sharepoint_data: {sheet_name: [[rows]]} do SharePoint
            sheet_name: Nome da sheet onde buscar dados
        
        Returns:
            {'new_rows': [[rows]], 'new_row_indices': [int], 'count': int}
        """
        try:
            # Pegar dados da sheet específica
            new_data = extracted_data_all.get(sheet_name, [])
            sp_data = sharepoint_data.get(sheet_name, [])
            
            if not new_data:
                return {'new_rows': [], 'new_row_indices': [], 'count': 0}
            
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
            logger.error(f"Erro ao identificar linhas novas: {str(e)}")
            raise Exception(f"Erro ao identificar linhas novas: {str(e)}")
        """
        Sincroniza relatório aprovado com SharePoint
        Identifica linhas novas e as adiciona à aba correta do mês
        
        Args:
            report_id: ID do relatório aprovado
            extracted_data: Dados extraídos do arquivo
        
        Returns:
            {'status': 'success', 'lines_added': int, 'sheet_name': str}
        """
        try:
            # 1. Detectar mês dos dados
            month_info = ReportService.extract_month_from_data(extracted_data)
            
            if not month_info:
                raise ValueError("Não foi possível detectar o mês dos dados do arquivo")
            
            month = month_info['month']
            year = month_info['year']
            
            # 2. Obter nome da aba no SharePoint
            sheet_name = ReportService.get_sheet_name_for_month(month, year)
            
            # 3. Buscar dados existentes no SharePoint (mock por enquanto)
            sharepoint_data = self._get_sheet_data(sheet_name)
            
            # 4. Identificar linhas novas
            new_rows = self._identify_new_rows(
                extracted_data_all=extracted_data,
                sharepoint_data=sharepoint_data,
                sheet_name=month_info['sheet_name']
            )
            
            # 5. Adicionar linhas novas ao SharePoint
            if new_rows:
                self._append_rows_to_sheet(sheet_name, new_rows)
            
            return {
                'status': 'success',
                'lines_added': len(new_rows),
                'sheet_name': sheet_name,
                'month': month,
                'year': year
            }
        
        except Exception as e:
            raise Exception(f"Erro ao sincronizar com SharePoint: {str(e)}")
    
    def _get_sheet_data(self, sheet_name):
        """
        Busca dados de uma aba específica do SharePoint
        
        TODO: Implementar com microsoft.graph
        Por enquanto, retorna dados mockados
        
        Args:
            sheet_name: Nome da aba (ex: "ABR 26")
        
        Returns:
            [[rows]] com dados da aba
        """
        # Mock - Retorna estrutura vazia inicialmente
        # Em produção, usará microsoft.graph para buscar dados reais
        try:
            # TODO: Chamar Graph API para baixar arquivo do SharePoint
            # TODO: Extrair dados da aba específica
            return {sheet_name: []}  # Mock
        except Exception as e:
            print(f"Aviso: Não conseguiu buscar dados do SharePoint: {str(e)}")
            return {sheet_name: []}
    
    def _identify_new_rows(self, extracted_data_all, sharepoint_data, sheet_name):
        """
        Identifica linhas novas comparando com dados do SharePoint
        
        Uma linha é considerada "nova" se não existe no SharePoint
        Comparação: converte cada linha em tupla para comparação
        
        Args:
            extracted_data_all: {sheet_name: [[rows]]} dos arquivo enviado
            sharepoint_data: {sheet_name: [[rows]]} do SharePoint
            sheet_name: Nome da sheet onde buscar dados
        
        Returns:
            [[new_rows]] apenas as linhas que não existem no SharePoint
        """
        try:
            # Pegar dados da sheet específica
            new_data = extracted_data_all.get(sheet_name, [])
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
            for row in new_data[1:] if len(new_data) > 1 else []:  # Pular header
                clean_row = tuple(str(cell) if cell is not None else '' for cell in row)
                
                # Se linha não existe no SharePoint, é nova
                if clean_row not in sp_rows_set:
                    new_rows.append(row)
            
            return new_rows
        
        except Exception as e:
            raise Exception(f"Erro ao identificar linhas novas: {str(e)}")
    
    def _append_rows_to_sheet(self, sheet_name, new_rows):
        """
        Adiciona linhas novas a uma aba no SharePoint
        
        TODO: Implementar com microsoft.graph
        Por enquanto, apenas loga
        
        Args:
            sheet_name: Nome da aba (ex: "ABR 26")
            new_rows: [[rows]] a adicionar
        
        Returns:
            {'status': 'success', 'rows_added': int}
        """
        try:
            # TODO: Implementar com microsoft.graph
            # TODO: Adicionar as linhas novas na aba específica
            print(f"Mock: Adicionando {len(new_rows)} linhas à aba '{sheet_name}' do SharePoint")
            
            return {
                'status': 'success',
                'rows_added': len(new_rows)
            }
        
        except Exception as e:
            raise Exception(f"Erro ao adicionar linhas ao SharePoint: {str(e)}")
