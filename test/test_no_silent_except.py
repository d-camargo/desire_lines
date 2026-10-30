# coding=utf-8
"""Gate de regressão contra handlers de exceção mudos (decisão D4).

O repositório oficial do QGIS (plugins.qgis.org) executa um scanner de segurança
baseado no Bandit que reprova pacotes contendo handlers 'except' que engolem erros
em silêncio (regras B110 e B112: try/except/pass e try/except/continue).
Marcas '# nosec' são ignoradas pelo scanner oficial.

Este teste inspeciona via AST todos os arquivos .py do pacote desire_lines/ e
garante que nenhum handler capture Exception, BaseException ou bare com corpo
composto exclusivamente de 'pass', 'continue' ou '...'.
"""

import ast
import os
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT_DIR / "desire_lines"


def is_broad_exception(node):
    """Retorna True se o nó representa exceção ampla: bare (None), Exception ou BaseException."""
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in ("Exception", "BaseException")
    if isinstance(node, ast.Attribute):
        return node.attr in ("Exception", "BaseException")
    if isinstance(node, ast.Tuple):
        return any(is_broad_exception(elt) for elt in node.elts)
    return False


def is_silent_statement(stmt):
    """Retorna True se a instrução for pass, continue ou ellipsis (...)."""
    if isinstance(stmt, (ast.Pass, ast.Continue)):
        return True
    if isinstance(stmt, ast.Expr):
        val = stmt.value
        if isinstance(val, ast.Constant) and val.value is Ellipsis:
            return True
    return False


def is_silent_body(body):
    """Retorna True se o corpo do handler for não-vazio e composto apenas de pass/continue/..."""
    return bool(body) and all(is_silent_statement(stmt) for stmt in body)


def find_silent_handlers_in_code(source_code, filename="<string>"):
    """Varre código-fonte e retorna lista de (lineno, handler_node) para handlers mudos."""
    tree = ast.parse(source_code, filename=filename)
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if is_broad_exception(node.type) and is_silent_body(node.body):
                findings.append((node.lineno, node))
    return findings


class TestNoSilentExcept(unittest.TestCase):
    """Testa ausência de handlers de exceção mudos (regras B110/B112 do bandit / D4)."""

    def test_desire_lines_has_no_silent_broad_except(self):
        """Varre desire_lines/ e falha se achar handlers mudos com exceção ampla."""
        violations = []
        py_files = sorted(PLUGIN_DIR.rglob("*.py"))
        self.assertTrue(len(py_files) > 0, f"Nenhum arquivo .py encontrado em {PLUGIN_DIR}")

        for py_path in py_files:
            rel_path = py_path.relative_to(ROOT_DIR)
            with open(py_path, "r", encoding="utf-8") as f:
                content = f.read()

            findings = find_silent_handlers_in_code(content, filename=str(py_path))
            for lineno, _ in findings:
                violations.append(f"{rel_path}:{lineno}")

        if violations:
            msg = (
                f"Encontrado(s) {len(violations)} handler(s) de exceção mudo(s) em desire_lines:\n"
                + "\n".join(f"  {v}" for v in violations)
                + "\n\nHandlers que capturam 'Exception', 'BaseException' ou bare (except:) "
                "com corpo apenas pass, continue ou ... violam as regras B110/B112 do bandit "
                "e barram o pacote no scanner de segurança do plugins.qgis.org.\n"
                "Aviso: '# nosec' não vale no scanner do plugins.qgis.org."
            )
            self.fail(msg)

    def test_detector_identifies_all_silent_broad_forms(self):
        """Garante que a lógica de detecção reconhece todas as variações de B110/B112."""
        cases = [
            ("try:\n    x()\nexcept:\n    pass\n", "bare except pass"),
            ("try:\n    x()\nexcept Exception:\n    pass\n", "except Exception pass"),
            ("try:\n    x()\nexcept BaseException:\n    pass\n", "except BaseException pass"),
            ("try:\n    x()\nexcept Exception:\n    continue\n", "except Exception continue"),
            ("try:\n    x()\nexcept:\n    continue\n", "bare except continue"),
            ("try:\n    x()\nexcept Exception:\n    ...\n", "except Exception ellipsis"),
            ("try:\n    x()\nexcept (ValueError, Exception):\n    pass\n", "tuple with Exception"),
            ("try:\n    x()\nexcept (KeyError, BaseException):\n    continue\n", "tuple with BaseException"),
        ]
        for snippet, desc in cases:
            findings = find_silent_handlers_in_code(snippet)
            self.assertEqual(len(findings), 1, f"Deveria detectar violação em: {desc}")

    def test_detector_allows_typed_or_non_silent_handlers(self):
        """Garante que exceções específicas ou handlers com ações reais são permitidos."""
        allowed = [
            ("try:\n    x()\nexcept (TypeError, ValueError):\n    pass\n", "typed tuple pass"),
            ("try:\n    x()\nexcept ImportError:\n    pass\n", "ImportError pass"),
            ("try:\n    x()\nexcept (KeyError, IndexError, TypeError):\n    continue\n", "typed continue"),
            ("try:\n    x()\nexcept Exception:\n    return False\n", "Exception with return"),
            ("try:\n    x()\nexcept Exception as err:\n    log(err)\n", "Exception with log"),
            ("try:\n    x()\nexcept Exception:\n    raise\n", "Exception with raise"),
        ]
        for snippet, desc in allowed:
            findings = find_silent_handlers_in_code(snippet)
            self.assertEqual(len(findings), 0, f"Não deveria detectar violação em: {desc}")


if __name__ == "__main__":
    unittest.main()
