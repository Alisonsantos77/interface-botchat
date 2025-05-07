import os
import json
from cryptography.fernet import Fernet

# Obtenha a chave de criptografia via variável de ambiente ou gere uma nova (atenção: a geração de chave em runtime não é ideal para produção)
FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())

fernet = Fernet(FERNET_KEY.encode())

def encrypt_data(data: dict) -> str:
    """
    Converte o dicionário para JSON e criptografa o conteúdo.
    """
    json_data = json.dumps(data)
    encrypted_data = fernet.encrypt(json_data.encode()).decode()
    return encrypted_data

def decrypt_data(encrypted_data: str) -> dict:
    """
    Descriptografa o texto e converte de volta para dicionário.
    """
    decrypted_bytes = fernet.decrypt(encrypted_data.encode())
    data = json.loads(decrypted_bytes.decode())
    print(data)
    return data
