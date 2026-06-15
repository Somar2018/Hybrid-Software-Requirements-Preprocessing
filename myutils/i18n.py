LANG = "en"   # default language

translations = {
    "pt": {
        "start": "Iniciar",
        "phase_title": "Fase: ESTRUTURA",
        "structural_validation": "Validação Estrutural (Fase 1)",
        "requirement": "Requisito",
        "class": "Classe",
        "subclass": "Subclasse",
        "correction": "Correção",
        "approve": "Aprovar",
        "reject": "Rejeitar",
        "suggest": "Sugerir",
        "save_suggestion": "Guardar Sugestão",
        "no_file": "❗ Nenhum arquivo enviado",
        "completed": "✅ Finalizado",
        "download": "📥 Download",
    },

    "en": {
        "start": "Start",
        "phase_title": "Phase: STRUCTURE",
        "structural_validation": "Structural Validation (Phase 1)",
        "requirement": "Requirement",
        "class": "Class",
        "subclass": "Subclass",
        "correction": "Correction",
        "approve": "Approve",
        "reject": "Reject",
        "suggest": "Suggest",
        "save_suggestion": "Save Suggestion",
        "no_file": "❗ No file uploaded",
        "completed": "✅ Completed",
        "download": "📥 Download",
    }
}

def t(key: str) -> str:
    return translations.get(LANG, translations["en"]).get(key, key)
