# coding=utf-8
"""Testes para gerador da página de changelog e validação do site."""

from pathlib import Path
import re
import sys
import tempfile
import unittest
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.build_changelog_page import (
    parse_metadata_changelog,
    build_changelog_markdown,
    main as build_changelog_main,
)


def extract_nav_targets(nav_item):
    """Extrai recursivamente todos os alvos .md declarados na nav de mkdocs.yml."""
    targets = []
    if isinstance(nav_item, str):
        if nav_item.endswith(".md"):
            targets.append(nav_item)
    elif isinstance(nav_item, list):
        for item in nav_item:
            targets.extend(extract_nav_targets(item))
    elif isinstance(nav_item, dict):
        for val in nav_item.values():
            targets.extend(extract_nav_targets(val))
    return targets


class TestChangelogGenerator(unittest.TestCase):
    """Testa a leitura do metadata.txt e a geração de docs/changelog.md."""

    def setUp(self):
        self.metadata_path = ROOT_DIR / "desire_lines" / "metadata.txt"

    def test_parse_metadata_changelog(self):
        """Confere se o changelog de metadata.txt é parseado corretamente."""
        entries = parse_metadata_changelog(self.metadata_path)
        self.assertTrue(len(entries) > 0, "Deveria encontrar ao menos uma versão no changelog.")

        for version, lines in entries:
            self.assertTrue(len(version.strip()) > 0, "Versão não pode ser vazia.")
            self.assertTrue(len(lines) > 0, f"A versão {version} não deve ter bloco de linhas vazio.")

    def test_current_version_in_changelog(self):
        """Confere se a versão corrente do metadata.txt aparece como seção."""
        content = self.metadata_path.read_text(encoding="utf-8")
        current_version = None
        for line in content.splitlines():
            if line.startswith("version="):
                current_version = line.split("version=", 1)[1].strip()
                break

        self.assertIsNotNone(current_version, "versão corrente não encontrada em metadata.txt")

        entries = parse_metadata_changelog(self.metadata_path)
        versions = [v for v, _ in entries]
        self.assertIn(current_version, versions, f"Versão corrente {current_version} deve constar nas versões parseadas.")

        md = build_changelog_markdown(entries)
        self.assertIn(f"## {current_version}", md, f"Markdown gerado deve conter a seção ## {current_version}")

    def test_build_changelog_page_execution(self):
        """Executa a geração em um diretório temporário para verificar a gravação."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_file = Path(tmp_dir) / "changelog.md"
            argv_original = sys.argv
            sys.argv = [
                "build_changelog_page.py",
                "--destino", str(dest_file),
            ]
            try:
                build_changelog_main()
            finally:
                sys.argv = argv_original

            self.assertTrue(dest_file.exists())
            written_content = dest_file.read_text(encoding="utf-8")
            self.assertIn("# Histórico de versões", written_content)
            self.assertIn("ATENÇÃO: Esta página é gerada automaticamente", written_content)


class TestDocsSiteValidation(unittest.TestCase):
    """Guarda e validação do site de documentação (D-I)."""

    def setUp(self):
        self.mkdocs_path = ROOT_DIR / "mkdocs.yml"
        self.docs_dir = ROOT_DIR / "docs"
        self.cname_path = self.docs_dir / "CNAME"

    def test_cname_content(self):
        """(c) Confere se docs/CNAME tem exatamente desirelines.dcamargo.com.br."""
        self.assertTrue(self.cname_path.exists(), "docs/CNAME deve existir.")
        content = self.cname_path.read_text(encoding="utf-8").strip()
        self.assertEqual(content, "desirelines.dcamargo.com.br")

    def test_exclude_docs_config(self):
        """(d) Confere se mkdocs.yml possui exclude_docs cobrindo topicos/."""
        self.assertTrue(self.mkdocs_path.exists(), "mkdocs.yml deve existir.")
        config = yaml.safe_load(self.mkdocs_path.read_text(encoding="utf-8"))
        self.assertIn("exclude_docs", config, "mkdocs.yml deve definir exclude_docs.")
        exclude_docs = config["exclude_docs"]
        if isinstance(exclude_docs, str):
            self.assertIn("topicos", exclude_docs)
        elif isinstance(exclude_docs, list):
            self.assertTrue(any("topicos" in str(item) for item in exclude_docs))
        else:
            self.fail("exclude_docs deve ser string ou lista.")

    def test_nav_and_docs_files_match(self):
        """(a) Casamento nos dois sentidos entre os alvos da nav e os .md de docs/."""
        self.assertTrue(self.mkdocs_path.exists(), "mkdocs.yml deve existir.")
        config = yaml.safe_load(self.mkdocs_path.read_text(encoding="utf-8"))
        self.assertIn("nav", config, "mkdocs.yml deve conter a chave nav.")

        nav_raw = extract_nav_targets(config["nav"])
        # Ignora topicos/ e a página gerada (changelog.md)
        nav_files = {
            t for t in nav_raw
            if t != "changelog.md" and not t.startswith("topicos/") and "topicos/" not in t
        }

        all_md = [
            p.relative_to(self.docs_dir).as_posix()
            for p in self.docs_dir.rglob("*.md")
        ]
        disk_files = {
            f for f in all_md
            if f != "changelog.md" and not f.startswith("topicos/") and "topicos/" not in f
        }

        self.assertEqual(
            nav_files,
            disk_files,
            f"Divergência entre alvos da nav e arquivos em docs/.\n"
            f"Apenas na nav: {nav_files - disk_files}\n"
            f"Apenas no disco: {disk_files - nav_files}"
        )

    def test_relative_links_resolve(self):
        """(b) Todo link relativo entre páginas resolve para arquivo existente."""
        link_pattern = re.compile(r"\[(?:[^\]]*)\]\(([^)]+)\)")

        all_md = list(self.docs_dir.rglob("*.md"))
        for md_file in all_md:
            if "topicos" in md_file.parts:
                continue
            content = md_file.read_text(encoding="utf-8")
            for match in link_pattern.findall(content):
                target = match.split()[0].strip()
                if target.startswith(("http://", "https://", "mailto:", "file://", "ftp://", "conversation://", "#")):
                    continue
                path_part = target.split("#")[0].strip()
                if not path_part:
                    continue
                resolved = (md_file.parent / path_part).resolve()
                self.assertTrue(
                    resolved.exists() or resolved.name == "changelog.md",
                    f"Link quebrado em {md_file.relative_to(self.docs_dir)}: "
                    f"aponta para '{target}', mas '{resolved}' não existe."
                )


if __name__ == "__main__":
    unittest.main()

