#!/usr/bin/env python3
"""Gera docs/changelog.md a partir do campo multilinha changelog= em desire_lines/metadata.txt."""

import argparse
from pathlib import Path
import re
import sys


def parse_metadata_changelog(metadata_path: Path) -> list[tuple[str, list[str]]]:
    """Lê o arquivo metadata.txt e extrai as seções do changelog por versão.

    Retorna uma lista de tuplas: (versao, linhas_de_texto)
    """
    content = metadata_path.read_text(encoding="utf-8")

    lines = content.splitlines()
    in_changelog = False
    changelog_lines = []

    for line in lines:
        if not in_changelog:
            if line.strip().startswith("changelog="):
                in_changelog = True
                val = line.split("changelog=", 1)[1].strip()
                if val:
                    changelog_lines.append(val)
        else:
            if line and not line.startswith(" ") and not line.startswith("\t") and ("=" in line or line.startswith("#")):
                break
            changelog_lines.append(line)

    version_regex = re.compile(r"^\s*(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)\s*$")

    entries: list[tuple[str, list[str]]] = []
    current_version = None
    current_lines = []

    for line in changelog_lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = version_regex.match(line)
        if m:
            if current_version is not None:
                entries.append((current_version, current_lines))
            current_version = m.group(1)
            current_lines = []
        else:
            if current_version is not None:
                current_lines.append(stripped)

    if current_version is not None:
        entries.append((current_version, current_lines))

    return entries


def build_changelog_markdown(entries: list[tuple[str, list[str]]]) -> str:
    """Gera o texto em Markdown a partir dos blocos de versão."""
    md_lines = [
        "# Histórico de versões",
        "",
        "<!-- ATENÇÃO: Esta página é gerada automaticamente por scripts/build_changelog_page.py a partir de desire_lines/metadata.txt. NÃO EDITE DIRETAMENTE. -->",
        "",
    ]

    for version, lines in entries:
        md_lines.append(f"## {version}")
        md_lines.append("")
        for line in lines:
            md_lines.append(line)
        md_lines.append("")

    return "\n".join(md_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera docs/changelog.md a partir de metadata.txt")
    parser.add_argument(
        "-o", "--origem",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "desire_lines" / "metadata.txt",
        help="Caminho para desire_lines/metadata.txt"
    )
    parser.add_argument(
        "-d", "--destino",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "changelog.md",
        help="Caminho de saída do changelog.md"
    )

    args = parser.parse_args()

    if not args.origem.exists():
        print(f"Erro: Arquivo de origem não encontrado: {args.origem}", file=sys.stderr)
        sys.exit(1)

    entries = parse_metadata_changelog(args.origem)
    if not entries:
        print("Aviso: Nenhum bloco de changelog encontrado no metadata.txt", file=sys.stderr)

    md_content = build_changelog_markdown(entries)

    args.destino.parent.mkdir(parents=True, exist_ok=True)
    args.destino.write_text(md_content, encoding="utf-8")
    print(f"Changelog gerado com sucesso em: {args.destino}")


if __name__ == "__main__":
    main()
