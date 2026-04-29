"""
OneDrive Personal Service - Integração simples com OneDrive pessoal via Microsoft Graph.

Este serviço é responsável por:
1. Autenticar com Azure AD (via MSAL - client credentials)
2. Acessar /me/drive (OneDrive pessoal)
3. Listar e baixar arquivos
4. Simples e direto - sem precisar de site_id ou drive_id
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging
import requests
import msal

logger = logging.getLogger(__name__)


@dataclass
class OneDriveFile:
    """Representa um arquivo no OneDrive"""
    item_id: str
    name: str
    size: int
    created_at: datetime
    modified_at: datetime
    web_url: str
    
    def __str__(self) -> str:
        return f"{self.name} ({self.size} bytes)"


class OneDrivePersonalService:
    """Serviço simplificado para OneDrive pessoal"""
    
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        user_email: str = None,
        user_principal_name: str = None
    ):
        """
        Inicializar serviço OneDrive.
        
        Args:
            tenant_id: ID do tenant Azure
            client_id: ID do app Azure
            client_secret: Secret do app
            user_email: Email do usuário (opcional, apenas para logs)
            user_principal_name: UPN para acesso (ex: thais_souza@loglifelogistica.com.br)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_email = user_email
        self.user_principal_name = user_principal_name
        self.access_token = None
        self.authority_url = f"https://login.microsoftonline.com/{tenant_id}"
        self.scopes = ["https://graph.microsoft.com/.default"]
        self.session = requests.Session()
        
        logger.info(f"OneDrivePersonalService inicializado para: {user_email or 'acesso de app'}")
    
    def authenticate(self) -> bool:
        """
        Autenticar com Azure AD usando Client Credentials.
        
        Returns:
            True se autenticação bem-sucedida
        """
        try:
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority_url,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(scopes=self.scopes)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("✅ Token obtido com sucesso")
                return True
            else:
                error = result.get("error_description", "Erro desconhecido")
                logger.error(f"❌ Erro na autenticação: {error}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Erro ao autenticar: {str(e)}")
            return False
    
    def use_user_token(self, user_token: str):
        """Usar token de usuário existente"""
        self.access_token = user_token
        logger.info("✅ Token de usuário armazenado")
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers padrão para requisições"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
        timeout: int = 30
    ) -> Tuple[bool, Any]:
        """Fazer requisição ao Microsoft Graph"""
        if not self.access_token:
            logger.error("❌ Sem token. Execute authenticate() primeiro")
            return False, None
        
        url = f"{self.GRAPH_BASE}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code in [200, 201, 204]:
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, response.text
            else:
                error = response.json() if response.text else response.reason
                logger.error(f"❌ Erro {response.status_code}: {error}")
                return False, error
        
        except Exception as e:
            logger.error(f"❌ Erro na requisição: {str(e)}")
            return False, str(e)
    
    def get_drive_info(self) -> bool:
        """
        Obter informações do OneDrive pessoal.
        
        Funciona tanto com delegated como application authentication.
        
        Returns:
            True se bem-sucedido
        """
        try:
            logger.info("⏳ Obtendo informações do OneDrive pessoal...")
            
            # Tentar dois endpoints:
            # 1. /me/drive (delegated auth) - vai falhar com app-only, mas temos como fallback
            # 2. /users/{upn}/drive (application auth)
            
            endpoints = []
            
            # Se temos UPN, usar esse (application auth)
            if self.user_principal_name:
                endpoints.append(f"/users/{self.user_principal_name}/drive")
            
            # Fallback: tentar /me/drive (só funciona se o token for de usuário)
            endpoints.append("/me/drive")
            
            for endpoint in endpoints:
                logger.info(f"   Tentando: {endpoint}")
                success, response = self._make_request("GET", endpoint)
                
                if success and response:
                    drive_id = response.get("id")
                    quota = response.get("quota", {})
                    logger.info(f"✅ Drive ID: {drive_id}")
                    logger.info(f"   Usado: {quota.get('used', 0) / (1024**3):.2f} GB")
                    logger.info(f"   Total: {quota.get('total', 0) / (1024**3):.2f} GB")
                    return True
            
            # Se nenhum funcionou, informar
            logger.error(f"❌ Não conseguiu acessar o drive")
            logger.info("   Dica: Para application auth, use user_principal_name no init")
            return False
        
        except Exception as e:
            logger.error(f"❌ Erro: {str(e)}")
            return False
    
    def list_files(self, folder_path: str = "/") -> List[OneDriveFile]:
        """
        Listar arquivos no OneDrive.
        
        Args:
            folder_path: Caminho da pasta (ex: "/", "/Documentos")
        
        Returns:
            Lista de arquivos
        """
        try:
            logger.info(f"📂 Listando arquivos em: {folder_path}")
            
            # Determinar se usar /me/drive ou /users/{upn}/drive
            drive_path = "/me/drive"
            if self.user_principal_name:
                drive_path = f"/users/{self.user_principal_name}/drive"
            
            if folder_path == "/":
                # Raiz do drive
                endpoint = f"{drive_path}/root/children"
            else:
                # Pasta específica
                folder_encoded = folder_path.replace(" ", "%20")
                endpoint = f"{drive_path}/root:{folder_encoded}:/children"
            
            success, response = self._make_request("GET", endpoint)
            
            if success and response:
                files = []
                items = response.get("value", [])
                logger.info(f"   Encontrados {len(items)} itens")
                
                for item in items:
                    if "file" in item:  # É um arquivo
                        file = OneDriveFile(
                            item_id=item["id"],
                            name=item["name"],
                            size=item.get("size", 0),
                            created_at=datetime.fromisoformat(
                                item.get("createdDateTime", "").replace("Z", "+00:00")
                            ),
                            modified_at=datetime.fromisoformat(
                                item.get("lastModifiedDateTime", "").replace("Z", "+00:00")
                            ),
                            web_url=item.get("webUrl", "")
                        )
                        files.append(file)
                        logger.info(f"   📄 {file.name} ({file.size / 1024:.1f} KB)")
                
                return files
            else:
                logger.error(f"❌ Erro ao listar: {response}")
                return []
        
        except Exception as e:
            logger.error(f"❌ Erro: {str(e)}")
            return []
    
    def download_file(self, file_id: str, output_path: Path) -> bool:
        """
        Baixar arquivo do OneDrive.
        
        Args:
            file_id: ID do arquivo no OneDrive
            output_path: Caminho local para salvar
        
        Returns:
            True se bem-sucedido
        """
        try:
            logger.info(f"⬇️  Baixando: {file_id}")
            
            # O endpoint de download é o mesmo independentemente da autenticação
            endpoint = f"/me/drive/items/{file_id}/content"
            
            if not self.access_token:
                logger.error("❌ Sem token")
                return False
            
            url = f"{self.GRAPH_BASE}{endpoint}"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=60)
            
            if response.status_code == 200:
                # Garantir que a pasta existe
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"✅ Arquivo salvo em: {output_path}")
                logger.info(f"   Tamanho: {len(response.content) / 1024:.1f} KB")
                return True
            else:
                logger.error(f"❌ Erro {response.status_code} ao baixar")
                return False
        
        except Exception as e:
            logger.error(f"❌ Erro: {str(e)}")
            return False
    
    def find_file(self, filename: str) -> Optional[OneDriveFile]:
        """
        Procurar um arquivo por nome.
        
        Args:
            filename: Nome do arquivo (parcial ou completo)
        
        Returns:
            OneDriveFile se encontrado, None se não
        """
        logger.info(f"🔍 Procurando: {filename}")
        
        files = self.list_files("/")
        
        for f in files:
            if filename.lower() in f.name.lower():
                logger.info(f"✅ Encontrado: {f.name}")
                return f
        
        logger.warning(f"⚠️  Arquivo não encontrado: {filename}")
        return None
