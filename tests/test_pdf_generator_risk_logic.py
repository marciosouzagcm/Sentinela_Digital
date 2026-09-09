from pdf_generator import _calcular_score_exposicao, _nivel_risco_geral


def test_score_and_risk_vector_are_based_on_confirmed_findings_only():
    resumo = {
        "ferramentas": {
            "gitleaks": {
                "status": "success",
                "destaques": ["No leaks found"],
                "resumo": "Varredura concluída. Nenhum vazamento detectado.",
            },
            "holehe": {
                "status": "success",
                "destaques": ["[+] conta ativa", "[+] github.com"],
                "resumo": "Contas ativas confirmadas.",
            },
            "h8mail": {
                "status": "success",
                "destaques": ["[found] breach for usuario@provedor.com"],
                "resumo": "Execução concluída com resultados relevantes.",
            },
            "sherlock": {
                "status": "success",
                "destaques": ["No result found"],
                "resumo": "Execução concluída sem evidência útil.",
            },
        }
    }

    score = _calcular_score_exposicao(resumo)
    nivel, vetores, contas_ativas, _ = _nivel_risco_geral(resumo)

    assert score > 0, "O score deve refletir achados confirmados e não permanecer em zero"
    assert contas_ativas == 3, "Contas ativas deve contar apenas achados reais"
    assert nivel in {"MÉDIO", "ALTO"}, "O nível deve indicar risco real"
    assert all("gitleaks" not in item.lower() for item in vetores), "Gitleaks sem achados não deve entrar em risco"
    assert any("holehe" in item.lower() for item in vetores), "Holehe com achados deve entrar na lista de risco"
    assert any("h8mail" in item.lower() for item in vetores), "H8mail com breach deve entrar na lista de risco"
