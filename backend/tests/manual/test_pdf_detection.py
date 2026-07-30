"""
Script manuel pour verifier validation + detection de type + extraction
de tableaux (branche PDF texte natif uniquement pour l'instant).

Usage :
    python -m tests.manual.test_pdf_detection storage/uploads/mon_fichier.pdf
"""

"""
Script manuel : test bout-en-bout de la branche PDF texte natif -> Excel.

Usage :
    python tests/manual/test_pdf_detection.py storage/uploads/mon_fichier.pdf
"""

import sys
from pathlib import Path

from app.application.use_cases.convert_native_pdf_to_excel import (
    NoNativeTextPageError,
    NoTableFoundError,
    convert_native_pdf_to_excel,
)
from app.infrastructure.pdf.validator import InvalidPdfError

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tests/manual/test_pdf_detection.py <chemin_du_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_name = Path(pdf_path).stem + "_converted.xlsx"
    output_path = str(Path("storage/outputs") / output_name)

    try:
        result = convert_native_pdf_to_excel(pdf_path, output_path)
    except InvalidPdfError as e:
        print(f"❌ PDF invalide : {e}")
        sys.exit(1)
    except NoNativeTextPageError as e:
        print(f"⚠️  {e}")
        sys.exit(1)
    except NoTableFoundError as e:
        print(f"⚠️  {e}")
        sys.exit(1)

    print("✅ Conversion réussie !")
    print(f"   Pages traitées : {result.page_count}")
    print(f"   Tableaux extraits : {result.table_count}")
    print(f"   Fichier généré : {result.output_path}")