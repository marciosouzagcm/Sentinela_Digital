# Scanner de Vulnerabilidades (Python)

Ferramenta de escaneamento de vulnerabilidades desenvolvida em **Python 3** para
ambiente **Linux** (testado em VM via VMware). Identifica fraquezas conhecidas
em sistemas e redes seguindo as categorias do **OWASP Top 10**.

## Objetivos

1. Apoiar a segurança da informação protegendo ativos e dados sensíveis.
2. Identificar, avaliar, priorizar e mitigar falhas em sistemas e aplicações.

## Processo de identificação implementado

1. **Coleta de Informações** (`modulos/coleta.py`)
2. **Escaneamento** (`modulos/escaneamento.py`)
3. **Análise de Código** (`modulos/analise_codigo.py`)
4. **Teste de Penetração leve** (`modulos/pentest.py`)

## Categorias OWASP cobertas

- A01 Controle de Acesso Quebrado
- A02 Falhas Criptográficas
- A03 Injeção
- A04 Design Inseguro
- A05 Configuração Incorreta de Segurança
- A06 Componentes Vulneráveis e Desatualizados
- A07 Falhas de Identificação e Autenticação
- A08 Falhas de Integridade de Software e Dados
- A09 Falhas de Registro e Monitoramento
- A10 Server-Side Request Forgery (SSRF)

## Ciclo de gestão (Identificação → Relatório)

`modulos/gestao.py` implementa as 6 etapas: Identificação, Categorização,
Priorização (CVSS simplificado), Mitigação (sugestões), Reavaliação e
Relatório (JSON + texto em `relatorios/`).

## Instalação

```bash
sudo apt update && sudo apt install -y python3 python3-pip nmap
cd scanner
python3 -m pip install -r requirements.txt
```

## Uso

```bash
# Alvo de rede (IP, host ou faixa CIDR)
python3 main.py --alvo 192.168.0.1

# Alvo web + análise de código local
python3 main.py --alvo https://exemplo.com --codigo ./meu_projeto

# Modo contínuo (reavaliação periódica a cada N minutos)
python3 main.py --alvo 192.168.0.1 --continuo 60
```

Relatórios são gravados em `relatorios/` e logs em `logs/`.

> **Aviso legal:** utilize apenas em ativos próprios ou com autorização
> formal por escrito. Uso indevido pode infringir a Lei 12.737/2012.

