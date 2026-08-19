# Makefile — desire_lines
# Deploy por symlink para o perfil default do QGIS; empacotamento via qgis-plugin-ci.
# (Substitui o Makefile legado do Plugin Builder — deploy Windows/nosetests/sphinx.)

PLUGINNAME = desire_lines
LOCALES = pt
LRELEASE = lrelease
VERSION = $(shell grep '^version=' $(PLUGINNAME)/metadata.txt | cut -d= -f2)
QGIS_PLUGINS = $(HOME)/.local/share/QGIS/QGIS3/profiles/default/python/plugins
FLATPAK_PLUGINS = $(HOME)/.var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/plugins
TARGET = $(QGIS_PLUGINS)/$(PLUGINNAME)
FLATPAK_TARGET = $(FLATPAK_PLUGINS)/$(PLUGINNAME)
SRC = $(CURDIR)/$(PLUGINNAME)

.PHONY: deploy deploy-flatpak undeploy undeploy-flatpak clean test package transup transcompile help docs-deps docs-build docs-serve

help:
	@echo "make deploy          - symlink do plugin no perfil do QGIS do sistema"
	@echo "make deploy-flatpak  - symlink no perfil do QGIS Flatpak"
	@echo "make undeploy        - remove o symlink (sistema)"
	@echo "make undeploy-flatpak- remove o symlink (flatpak)"
	@echo "make clean           - remove __pycache__"
	@echo "make test            - smoke test de sintaxe (sem QGIS)"
	@echo "make package         - gera o pacote zip via qgis-plugin-ci em dist/desire_lines-<version>.zip"
	@echo "make transup         - extrai strings para $(PLUGINNAME)/i18n/<locale>.ts"
	@echo "make transcompile    - compila i18n/*.ts para .qm (DesireLines_<locale>.qm)"
	@echo "make docs-deps       - cria .venv-docs e instala dependencias de docs"
	@echo "make docs-build      - gera a pagina de changelog e compila o site (mkdocs build --strict)"
	@echo "make docs-serve      - gera a pagina de changelog e inicia o servidor local (mkdocs serve)"

deploy:
	@mkdir -p $(QGIS_PLUGINS)
	@if [ -e "$(TARGET)" ] && [ ! -L "$(TARGET)" ]; then \
		echo "ERRO: $(TARGET) existe e nao e symlink. Remova manualmente."; exit 1; \
	fi
	@ln -sfn "$(SRC)" "$(TARGET)"
	@echo "symlink: $(TARGET) -> $(SRC)"
	@echo "Recarregue no QGIS (Plugin Reloader) ou reinicie."

deploy-flatpak:
	@if [ ! -d "$(dir $(FLATPAK_PLUGINS))" ]; then \
		echo "ERRO: perfil Flatpak nao existe ainda."; exit 1; \
	fi
	@mkdir -p "$(FLATPAK_PLUGINS)"
	@if [ -e "$(FLATPAK_TARGET)" ] && [ ! -L "$(FLATPAK_TARGET)" ]; then \
		echo "ERRO: $(FLATPAK_TARGET) existe e nao e symlink."; exit 1; \
	fi
	@ln -sfn "$(SRC)" "$(FLATPAK_TARGET)"
	@echo "symlink (flatpak): $(FLATPAK_TARGET) -> $(SRC)"

undeploy:
	@if [ -L "$(TARGET)" ]; then rm "$(TARGET)" && echo "removido $(TARGET)"; \
	else echo "nada a remover"; fi

undeploy-flatpak:
	@if [ -L "$(FLATPAK_TARGET)" ]; then rm "$(FLATPAK_TARGET)" && echo "removido $(FLATPAK_TARGET)"; \
	else echo "nada a remover"; fi

clean:
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "limpo"

test:
	@python3 -c "import ast,glob,sys; [ast.parse(open(f).read(), f) for f in glob.glob('**/*.py', recursive=True)]; print('sintaxe OK')"

package:
	@mkdir -p dist
	@qgis-plugin-ci package $(VERSION) --disable-submodule-update
	@mv $(PLUGINNAME).$(VERSION).zip dist/$(PLUGINNAME)-$(VERSION).zip 2>/dev/null || true
	@echo "Pacote gerado em dist/$(PLUGINNAME)-$(VERSION).zip"

transup:
	@cd $(PLUGINNAME) && $(CURDIR)/scripts/update-strings.sh $(LOCALES)

transcompile:
	@cd $(PLUGINNAME) && $(CURDIR)/scripts/compile-strings.sh $(LRELEASE) $(LOCALES)

docs-deps:
	@python3 -m venv .venv-docs
	@.venv-docs/bin/pip install -r docs/requirements.txt

docs-build:
	@.venv-docs/bin/python scripts/build_changelog_page.py
	@.venv-docs/bin/mkdocs build --strict

docs-serve:
	@.venv-docs/bin/python scripts/build_changelog_page.py
	@.venv-docs/bin/mkdocs serve
