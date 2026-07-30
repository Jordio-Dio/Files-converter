"""
Extraction de tableaux sur PDF texte natif, via Camelot.

Stratégie en cascade (cf. conception validée) :
1. Mode 'lattice' en premier -- plus fiable quand le tableau a des bordures.
2. Si aucun tableau trouvé, repli automatique sur le mode 'stream'
   -- détecte les tableaux par simple alignement du texte, sans bordures.

Camelot travaille sur un CHEMIN de fichier, pas sur des bytes en mémoire --
pour l'API HTTP (étape ultérieure), il faudra donc écrire le fichier
temporairement sur disque avant d'appeler cette fonction.
"""

"""
Extraction de tableaux sur PDF texte natif, via Camelot.
"""
import camelot
from app.core.logging import get_logger
from app.domain.entities.extracted_table import ExtractedTable, ExtractionMethod

logger = get_logger(__name__)

def _camelot_tables_to_entities(tables: camelot.core.TableList, method: ExtractionMethod) -> list[ExtractedTable]:
    result = []
    for table in tables:
        rows = table.df.values.tolist()
        result.append(
            ExtractedTable(
                page_number=int(table.page),
                rows=rows,
                extraction_method=method,
                camelot_accuracy=table.parsing_report.get("accuracy", 0.0),
            )
        )
    return result

def extract_tables_from_native_pdf(pdf_path: str) -> list[ExtractedTable]:
    """Extrait tous les tableaux d'un PDF texte natif."""
    logger.info("Extraction Camelot (lattice) sur %s", pdf_path)
    
    try:
        # Tente l'extraction Lattice (avec ghostscript par défaut ou poppler/pdfium)
        lattice_tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
        if len(lattice_tables) > 0:
            logger.info("%d tableau(x) trouvé(s) en mode lattice", len(lattice_tables))
            return _camelot_tables_to_entities(lattice_tables, ExtractionMethod.CAMELOT_LATTICE)
    except Exception as e:
        logger.warning("Échec du mode lattice (%s), bascule sur stream...", e)

    logger.info("Repli sur le mode stream")
    stream_tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
    logger.info("%d tableau(x) trouvé(s) en mode stream", len(stream_tables))
    return _camelot_tables_to_entities(stream_tables, ExtractionMethod.CAMELOT_STREAM)