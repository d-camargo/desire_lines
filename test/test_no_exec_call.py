# coding=utf-8
"""Gate de regressão contra chamadas a exec() e eval() (decisão D4).

O repositório oficial do QGIS (plugins.qgis.org) e o scanner de segurança do motor
reprovam pacotes contendo chamadas a 'exec' ou 'eval' (regras B102 exec e B307 eval),
incluindo chamadas de métodos de interface como QDialog.exec() ou QMessageBox.exec().
Marcas '# nosec' são ignoradas pelo scanner oficial.

Este teste inspeciona via AST todos os arquivos .py do pacote desire_lines/ e
garante que nenhuma chamada tenha como alvo 'exec', 'eval' ou termine em '.exec'
ou '.eval'.
"""

import ast
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT_DIR / "desire_lines"


def is_exec_or_eval_call(call_node):
    """Retorna o alvo se a chamada for exec/eval ou método terminando em .exec/.eval, senão None."""
    if not hasattr(ast, "unparse"):
        return None
    alvo = ast.unparse(call_node.func)
    for chave in ("exec", "eval"):
        if alvo == chave or alvo.endswith("." + chave):
            return alvo
    return None


def find_exec_calls_in_code(source_code, filename="<string>"):
    """Varre código-fonte e retorna lista de (lineno, alvo) para chamadas proibidas."""
    tree = ast.parse(source_code, filename=filename)
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            alvo = is_exec_or_eval_call(node)
            if alvo:
                findings.append((node.lineno, alvo))
    return findings


class TestNoExecCall(unittest.TestCase):
    """Testa ausência de chamadas a exec() e eval() (decisão D4 / B102 e B307)."""

    def test_desire_lines_has_no_exec_or_eval_calls(self):
        """Varre desire_lines/ e falha se achar chamadas a exec/eval ou *.exec/*.eval."""
        violations = []
        py_files = sorted(PLUGIN_DIR.rglob("*.py"))
        self.assertTrue(len(py_files) > 0, f"Nenhum arquivo .py encontrado em {PLUGIN_DIR}")

        for py_path in py_files:
            rel_path = py_path.relative_to(ROOT_DIR)
            with open(py_path, "r", encoding="utf-8") as f:
                content = f.read()

            findings = find_exec_calls_in_code(content, filename=str(py_path))
            for lineno, alvo in findings:
                violations.append(f"{rel_path}:{lineno} (alvo: {alvo})")

        if violations:
            msg = (
                f"Encontrada(s) {len(violations)} chamada(s) a exec/eval em desire_lines:\n"
                + "\n".join(f"  {v}" for v in violations)
                + "\n\nO scanner de segurança do plugins.qgis.org e do motor reprovam chamadas a "
                "exec/eval e métodos terminados em .exec/.eval (regras B102/B307).\n"
                "Para diálogos e caixas de mensagem Qt, use open() ou show() + sinal "
                "(ex.: finished.connect(...)), não exec_() (que não existe no PyQt6) e não # nosec."
            )
            self.fail(msg)

    def test_detector_identifies_exec_and_eval_calls(self):
        """Garante que a lógica de detecção reconhece exec, eval e métodos .exec/.eval."""
        cases = [
            ("exec('print(1)')\n", "exec builtin"),
            ("eval('1 + 1')\n", "eval builtin"),
            ("box.exec()\n", "box.exec()"),
            ("self.dlg.exec()\n", "self.dlg.exec()"),
            ("x.exec(arg)\n", "x.exec(arg)"),
            ("foo.bar.eval('x')\n", "foo.bar.eval()"),
        ]
        for snippet, desc in cases:
            findings = find_exec_calls_in_code(snippet)
            self.assertEqual(len(findings), 1, f"Deveria detectar violação em: {desc}")

    def test_detector_allows_safe_calls(self):
        """Garante que chamadas seguras (show, open, execute, etc.) não são marcadas."""
        cases = [
            ("dlg.show()\n", "dlg.show()"),
            ("dlg.open()\n", "dlg.open()"),
            ("dlg.setModal(True)\n", "dlg.setModal(True)"),
            ("cursor.execute('SELECT 1')\n", "cursor.execute"),
            ("x = evaluate(val)\n", "evaluate function"),
            ("def exec():\n    pass\n", "def exec"),
            ("x = obj.exec\n", "attribute access without call"),
        ]
        for snippet, desc in cases:
            findings = find_exec_calls_in_code(snippet)
            self.assertEqual(len(findings), 0, f"Não deveria detectar violação em: {desc}")


if __name__ == "__main__":
    unittest.main()
