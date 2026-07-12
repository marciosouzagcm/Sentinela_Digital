import os

# Regra 1: Segredo Hardcoded
api_key = "MINHA_SENHA_SUPER_SECRETA_12345"

# Regra 2: Uso de eval()
entrada = input("Digite algo: ")
eval(entrada)

# Regra 3: SQLi via f-string
query = f"SELECT * FROM users WHERE id = {entrada}"
