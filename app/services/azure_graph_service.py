"""
Serviço de integração com Microsoft Graph API
Autenticação com Azure AD e acesso a SharePoint/OneDrive
"""

import requests
from flask import current_app
import os
from datetime import datetime, timedelta
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AzureGraphService:
    """
    Serviço para integração com Microsoft Graph API
    Autentica com Azure AD e acessa SharePoint/OneDrive
    """
    
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self):
        """Inicializar serviço com credenciais do .env"""
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.authority = os.getenv('AZURE_AUTHORITY')
        
        self._token = None
        self._token_expiry = None
        
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Credenciais do Azure AD não configuradas no .env")
    
    def _get_token(self):
        """
        Obter token de acesso do Azure AD
        Cache o token até sua expiração
        """
        # Se token válido em cache, retornar
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token
        
        try:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            
            data = response.json()
            self._token = data['access_token']
            
            # Expiração: expires_in - 60 segundos (margem de segurança)
            expires_in = data.get('expires_in', 3600)
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            
            logger.info("Token de acesso obtido com sucesso do Azure AD")
            return self._token
        
        except Exception as e:
            logger.error(f"Erro ao obter token do Azure AD: {str(e)}")
            raise Exception(f"Falha na autenticação Azure: {str(e)}")
    
    def _get_headers(self):
        """Obter headers com token de autorização"""
        token = self._get_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_workbook_data(self, site_url, library, document_id, sheet_name):
        """
        Buscar dados de uma aba específica do Excel no SharePoint/OneDrive
        
        Args:
            site_url: URL do site SharePoint (ex: https://loglifeacademy-my.sharepoint.com)
            library: Library/Drive (ex: personal/thais_souza_loglifelogistica_com_br)
            document_id: ID do documento no SharePoint
            sheet_name: Nome da aba (ex: "ABR 26")
        
        Returns:
            [[rows]] com dados da aba
        """
        try:
            # 1. Obter ID do arquivo via drive search
            logger.info(f"Buscando arquivo com documentId: {document_id}")
            
            # Construir URL da aba
            url = f"{self.GRAPH_URL}/drives/0/items/{document_id}/workbook/worksheets('{sheet_name}')/range(address='A:Z')"
            
            # Versão alternativa: usar site + library
            # TODO: Testar com drive ID real
            
            headers = self._get_headers()
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                logger.warning(f"Aba '{sheet_name}' não encontrada no workbook")
                return [[]]
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extrair valores das células
            values = data.get('values', [[]])
            
            logger.info(f"Dados da aba '{sheet_name}' obtidos com sucesso. Linhas: {len(values)}")
            
            return values
        
        except Exception as e:
            logger.error(f"Erro ao buscar dados do workbook: {str(e)}")
            raise Exception(f"Erro ao buscar dados do SharePoint: {str(e)}")
    
    def append_rows_to_worksheet(self, site_url, library, document_id, sheet_name, new_rows):
        """
        Adicionar novas linhas a uma aba específica do Excel
        
        Args:
            site_url: URL do site SharePoint
            library: Library/Drive
            document_id: ID do documento
            sheet_name: Nome da aba (ex: "ABR 26")
            new_rows: [[rows]] com as novas linhas a adicionar
        
        Returns:
            {'status': 'success', 'rows_added': int}
        """
        try:
            if not new_rows:
                return {'status': 'success', 'rows_added': 0}
            
            logger.info(f"Adicionando {len(new_rows)} linhas à aba '{sheet_name}'")
            
            # 1. Buscar última linha usada
            url_range = f"{self.GRAPH_URL}/drives/0/items/{document_id}/workbook/worksheets('{sheet_name}')/range(address='A:Z')"
            headers = self._get_headers()
            
            response = requests.get(url_range, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            existing_rows = data.get('values', [[]])
            last_row = len(existing_rows)
            
            logger.info(f"Última linha usada: {last_row}")
            
            # 2. Preparar dados para adicionar
            # Convertendo None e tipos para string
            formatted_rows = []
            for row in new_rows:
                formatted_row = [str(cell) if cell is not None else '' for cell in row]
                formatted_rows.append(formatted_row)
            
            # 3. Adicionar linhas (POST para criar nova área)
            start_row = last_row
            num_cols = len(new_rows[0]) if new_rows else 0
            
            # Construir range (ex: A10:Z15 para adicionar 5 linhas)
            end_row = start_row + len(new_rows)
            range_address = f"A{start_row + 1}:Z{end_row}"
            
            url_update = f"{self.GRAPH_URL}/drives/0/items/{document_id}/workbook/worksheets('{sheet_name}')/range(address='{range_address}')"
            
            payload = {
                'values': formatted_rows
            }
            
            response = requests.patch(url_update, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Sucesso ao adicionar {len(new_rows)} linhas à aba '{sheet_name}'")
            
            return {
                'status': 'success',
                'rows_added': len(new_rows),
                'start_row': start_row,
                'end_row': end_row
            }
        
        except Exception as e:
            logger.error(f"Erro ao adicionar linhas ao workbook: {str(e)}")
            raise Exception(f"Erro ao sincronizar com SharePoint: {str(e)}")
    
    def get_sheet_names(self, document_id):
        """
        Listar todas as abas de um workbook
        
        Args:
            document_id: ID do documento
        
        Returns:
            [sheet_names] ex: ["JAN 26", "FEV 26", "MAR 26", ...]
        """
        try:
            url = f"{self.GRAPH_URL}/drives/0/items/{document_id}/workbook/worksheets"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            sheets = [sheet['name'] for sheet in data.get('value', [])]
            
            logger.info(f"Abas encontradas no workbook: {sheets}")
            
            return sheets
        
        except Exception as e:
            logger.error(f"Erro ao listar abas: {str(e)}")
            raise Exception(f"Erro ao listar abas do workbook: {str(e)}")


class SharePointGraphIntegration:
    """
    Integração específica para o arquivo de testes do SharePoint
    Usa as credenciais e URLs do .env
    """
    
    def __init__(self):
        self.graph = AzureGraphService()
        
        # Usar configuração de TESTE do .env
        self.site_url = os.getenv('SHAREPOINT_TEST_SITE_URL')
        self.library = os.getenv('SHAREPOINT_TEST_LIBRARY')
        self.document_id = os.getenv('SHAREPOINT_TEST_DOCUMENT_ID')
        self.file_name = os.getenv('SHAREPOINT_TEST_FILE')
    
    def get_month_sheet_data(self, month, year):
        """
        Buscar dados de uma aba específica do mês
        
        Args:
            month: Número do mês (1-12)
            year: Ano (ex: 2026)
        
        Returns:
            [[rows]] com dados da aba
        """
        from app.services.report_service import ReportService
        
        sheet_name = ReportService.get_sheet_name_for_month(month, year)
        logger.info(f"Buscando dados da aba '{sheet_name}' (Mês: {month}, Ano: {year})")
        
        return self.graph.get_workbook_data(
            site_url=self.site_url,
            library=self.library,
            document_id=self.document_id,
            sheet_name=sheet_name
        )
    
    def sync_new_rows(self, month, year, new_rows):
        """
        Sincronizar novas linhas para aba do mês
        
        Args:
            month: Número do mês
            year: Ano
            new_rows: [[rows]] com novas linhas
        
        Returns:
            {'status': 'success', 'rows_added': int, ...}
        """
        from app.services.report_service import ReportService
        
        sheet_name = ReportService.get_sheet_name_for_month(month, year)
        logger.info(f"Sincronizando {len(new_rows)} linhas para aba '{sheet_name}'")
        
        return self.graph.append_rows_to_worksheet(
            site_url=self.site_url,
            library=self.library,
            document_id=self.document_id,
            sheet_name=sheet_name,
            new_rows=new_rows
        )
    
    def list_available_sheets(self):
        """Listar todas as abas disponíveis no workbook"""
        return self.graph.get_sheet_names(self.document_id)
