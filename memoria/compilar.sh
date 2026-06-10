#!/bin/bash
# Compilar la memoria TFG a PDF
# Requereix: pdflatex, biber (instal·lar amb: brew install --cask basictex)
# Despres de instal·lar: sudo tlmgr install biblatex biber glossaries pgfplots

cd "$(dirname "$0")"

echo "=== Compilant memoria TFG ==="

# Primera passada
pdflatex -interaction=nonstopmode memoria_tfg.tex

# Bibliografia
biber memoria_tfg

# Glossari
makeglossaries memoria_tfg

# Segones passades (per refs creuades)
pdflatex -interaction=nonstopmode memoria_tfg.tex
pdflatex -interaction=nonstopmode memoria_tfg.tex

echo ""
echo "=== Compilacio completada ==="
echo "PDF generat: memoria_tfg.pdf"
