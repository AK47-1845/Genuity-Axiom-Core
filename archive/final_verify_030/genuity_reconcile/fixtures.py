"""Generated, non-confidential industrial packet and mock existing-OCR output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _field(
    name: str,
    value: Any,
    *,
    unit: str | None = None,
    confidence: float = 0.99,
    region: str = "header",
    bbox: list[float] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "confidence": confidence,
        "page": 1,
        "region": region,
        "bbox": bbox or [0.08, 0.08, 0.92, 0.16],
    }


def packet_documents() -> list[dict[str, Any]]:
    """Return a twelve-page packet that contains controlled extraction failures."""
    coc_text = (
        "CERTIFICATE OF CONFORMANCE\nCOC NUMBER: COC-77\nPO NUMBER: PO-1001\n"
        "CERTIFICATE NUMBER: MTR-900\nHEAT NUMBER: W3535\nSUPPLIER: Apex Metals\n"
        "We certify that the supplied material conforms to PO-1001 and SPEC-725."
    )
    coc_fields = [
        _field("coc_number", "COC-77"),
        _field("po_number", "PO-1001"),
        _field("certificate_number", "MTR-900"),
        _field("heat_number", "W3535"),
        _field("supplier", "Apex Metals"),
    ]
    return [
        {
            "filename": "01_purchase_order.json",
            "text": (
                "PURCHASE ORDER\nPO NUMBER: PO-1001\nSUPPLIER: Apex Metals\n"
                "PART NUMBER: PN-70725\nMATERIAL: INCONEL alloy 725\n"
                "QUANTITY: 45 PCS\nUNIT PRICE: USD 125.00\nTOTAL: [blank]\nREVISION: 3"
            ),
            "fields": [
                _field("po_number", "PO-1001"),
                _field("supplier", "Apex Metals"),
                _field("part_number", "PN-70725"),
                _field("material_grade", "INCONEL alloy 725"),
                _field("quantity", 45, unit="pcs", region="line_items"),
                _field("unit_price", 125.0, unit="USD", region="line_items"),
                _field("total_amount", None, unit="USD", confidence=0.0, region="totals"),
                _field("revision", 3),
            ],
        },
        {
            "filename": "02_supplier_invoice.json",
            "text": (
                "SUPPLIER INVOICE\nINVOICE NUMBER: INV-8821\nPO NUMBER: PO-1001\n"
                "SUPPLIER: Apex Metals\nPART NUMBER: [not printed]\nQUANTITY: 44 PCS\n"
                "UNIT PRICE: USD 125.00\nTOTAL: USD 5500.00"
            ),
            "fields": [
                _field("invoice_number", "INV-8821"),
                _field("po_number", "PO-1001"),
                _field("supplier", "Apex Metals"),
                _field("part_number", None, confidence=0.0, region="line_items"),
                _field("quantity", 44, unit="pcs", region="line_items"),
                _field("unit_price", 125.0, unit="USD", region="line_items"),
                _field("total_amount", 5500.0, unit="USD", region="totals"),
            ],
        },
        {
            "filename": "03_bom_revision_3.json",
            "text": (
                "BILL OF MATERIALS\nBOM NUMBER: BOM-725-A\nPO NUMBER: PO-1001\n"
                "PART NUMBER: PN-7O725\nMATERIAL: UNS N07725\nSPECIFICATION: SPEC-725\nREVISION: 3"
            ),
            "fields": [
                _field("bom_number", "BOM-725-A"),
                _field("po_number", "PO-1001"),
                _field("part_number", "PN-7O725", confidence=0.74, region="parts_table"),
                _field("material_grade", "UNS N07725", region="parts_table"),
                _field("specification_number", "SPEC-725", region="parts_table"),
                _field("revision", 3),
            ],
        },
        {
            "filename": "04_material_spec_revision_9.json",
            "text": (
                "MATERIAL SPECIFICATION\nSPECIFICATION NUMBER: SPEC-725\nMATERIAL: INCONEL 725\n"
                "REVISION: 9\nCHEMISTRY TABLE: Cr 19.0-22.5, Ni >=55.0, Mo 7.0-9.5, "
                "Nb+Ta 2.75-4.0, B <=0.006\nTENSILE STRENGTH: 827-1034 MPa"
            ),
            "fields": [
                _field("specification_number", "SPEC-725"),
                _field("material_grade", "INCONEL 725"),
                _field("revision", 9),
                _field("limit.Cr.min", 19.0, unit="percent", region="chemistry_table"),
                _field("limit.Cr.max", 22.5, unit="percent", region="chemistry_table"),
                _field("limit.Ni.min", 55.0, unit="percent", region="chemistry_table"),
                _field("limit.Mo.min", 7.0, unit="percent", region="chemistry_table"),
                _field("limit.Mo.max", 9.5, unit="percent", region="chemistry_table"),
                _field("limit.NbTa.min", 2.75, unit="percent", region="chemistry_table"),
                _field("limit.NbTa.max", 4.0, unit="percent", region="chemistry_table"),
                _field("limit.B.max", 0.006, unit="percent", region="chemistry_table"),
                _field("limit.tensile.min", 827.0, unit="MPa", region="mechanical_table"),
                _field("limit.tensile.max", 1034.0, unit="MPa", region="mechanical_table"),
            ],
        },
        {
            "filename": "05_material_certificate.json",
            "text": (
                "MATERIAL TEST CERTIFICATE\nCERTIFICATE NUMBER: MTR-900\nHEAT NUMBER: W3535\n"
                "MATERIAL: INCONEL 725\nSUPPLIER: Apex Metals\nCHEMISTRY TABLE: C 0.004, "
                "Ni 58.10, Co 0.04, Cr 20.80, Mo 8.05, Nb 3.42, Ta 0.0032, B [blank]\n"
                "TENSILE TEST: [obscured stamp over value]"
            ),
            "fields": [
                _field("certificate_number", "MTR-900"),
                _field("heat_number", "W3535"),
                _field("material_grade", "INCONEL 725"),
                _field("supplier", "Apex Metals"),
                _field("chemistry.C", 0.004, unit="percent", region="chemistry_table"),
                _field("chemistry.Ni", 58.10, unit="percent", region="chemistry_table"),
                _field("chemistry.Co", 0.04, unit="percent", region="chemistry_table"),
                _field("chemistry.Cr", 20.80, unit="percent", region="chemistry_table"),
                _field("chemistry.Mo", 8.05, unit="percent", region="chemistry_table"),
                _field("chemistry.Nb", 3.42, unit="percent", region="chemistry_table"),
                _field("chemistry.Ta", 0.0032, unit="percent", region="chemistry_table"),
                _field("chemistry.B", None, unit="percent", confidence=0.0, region="chemistry_table"),
                _field(
                    "tensile_strength_mpa",
                    None,
                    unit="MPa",
                    confidence=0.0,
                    region="mechanical_table_crop_x430_y690_w260_h90",
                    bbox=[0.52, 0.65, 0.84, 0.76],
                ),
            ],
        },
        {
            "filename": "06_certificate_of_conformance.json",
            "text": coc_text,
            "fields": coc_fields,
        },
        {
            "filename": "07_ladle_chemistry.json",
            "text": (
                "CHEMISTRY TABLE - LADLE ANALYSIS\nHEAT NUMBER: W3535\nMATERIAL: INCONEL 725\n"
                "C 0.004, Ni 58.14, Cr 20.80, Mo 8.05, Nb 3.42, Ta 0.0032, B 0.0002"
            ),
            "fields": [
                _field("heat_number", "W3535"),
                _field("material_grade", "INCONEL 725"),
                _field("chemistry.C", 0.004, unit="percent", region="ladle_analysis"),
                _field("chemistry.Ni", 58.14, unit="percent", region="ladle_analysis"),
                _field("chemistry.Cr", 20.80, unit="percent", region="ladle_analysis"),
                _field("chemistry.Mo", 8.05, unit="percent", region="ladle_analysis"),
                _field("chemistry.Nb", 3.42, unit="percent", region="ladle_analysis"),
                _field("chemistry.Ta", 0.0032, unit="percent", region="ladle_analysis"),
                _field("chemistry.B", 0.0002, unit="percent", region="ladle_analysis"),
            ],
        },
        {
            "filename": "08_mechanical_properties.json",
            "text": (
                "MECHANICAL PROPERTIES\nHEAT NUMBER: W3535\nPART NUMBER: PN-70725\n"
                "TENSILE STRENGTH: 132000 MPa\nYIELD STRENGTH: 126000 PSI\nELONGATION: 24 percent"
            ),
            "fields": [
                _field("heat_number", "W3535"),
                _field("part_number", "PN-70725"),
                _field("tensile_strength_mpa", 132000.0, unit="MPa", region="mechanical_table"),
                _field("yield_strength_psi", 126000.0, unit="psi", region="mechanical_table"),
                _field("elongation_percent", 24.0, unit="percent", region="mechanical_table"),
            ],
        },
        {
            "filename": "09_hardness_table.json",
            "text": (
                "HARDNESS TEST TABLE\nHEAT NUMBER: W3535\nHRC ROW 9: 38.6, [obscured], 39.2, 39.0"
            ),
            "fields": [
                _field("heat_number", "W3535"),
                _field(
                    "hardness_readings_hrc",
                    [38.6, None, 39.2, 39.0],
                    unit="HRC",
                    confidence=0.79,
                    region="hardness_table_row_9",
                ),
            ],
        },
        {
            "filename": "10_certificate_duplicate_scan.json",
            "text": coc_text,
            "fields": coc_fields,
        },
        {
            "filename": "11_material_spec_old_revision.json",
            "text": (
                "MATERIAL SPECIFICATION\nSPECIFICATION NUMBER: SPEC-725\nMATERIAL: INCONEL 725\n"
                "REVISION: 8\nCHEMISTRY TABLE: Cr 19.0-21.0, Ni >=55.0, Mo 7.0-9.5"
            ),
            "fields": [
                _field("specification_number", "SPEC-725"),
                _field("material_grade", "INCONEL 725"),
                _field("revision", 8),
                _field("limit.Cr.min", 19.0, unit="percent", region="chemistry_table"),
                _field("limit.Cr.max", 21.0, unit="percent", region="chemistry_table"),
                _field("limit.Ni.min", 55.0, unit="percent", region="chemistry_table"),
                _field("limit.Mo.min", 7.0, unit="percent", region="chemistry_table"),
                _field("limit.Mo.max", 9.5, unit="percent", region="chemistry_table"),
            ],
        },
        {
            "filename": "12_final_inspection.json",
            "text": (
                "FINAL INSPECTION REPORT\nPART NUMBER: PN-70725\nHEAT NUMBER: W3535\n"
                "QUANTITY INSPECTED: 45\nQUANTITY ACCEPTED: 45\nINSPECTOR SIGNOFF: [missing]"
            ),
            "fields": [
                _field("part_number", "PN-70725"),
                _field("heat_number", "W3535"),
                _field("quantity_inspected", 45, unit="pcs"),
                _field("quantity_accepted", 45, unit="pcs"),
                _field("inspector_signoff", None, confidence=0.0, region="approval_block"),
            ],
        },
    ]


GROUND_TRUTH = {
    "part_number": "PN-70725",
    "po_total_amount": 5625.0,
    "mechanical_tensile_mpa": 910.107,
    "material_certificate_tensile_mpa": 910.0,
    "certificate_boron": 0.0002,
    "quantity_conflict": {"purchase_order": 45, "invoice": 44},
    "inspector_signoff": None,
}


EXPECTED_CRITICAL_FIELDS = [
    ("01_PURCHASE", "po_number", "PO-1001"),
    ("01_PURCHASE", "part_number", "PN-70725"),
    ("01_PURCHASE", "material_grade", "INCONEL 725"),
    ("01_PURCHASE", "quantity", 45),
    ("02_SUPPLIER", "po_number", "PO-1001"),
    ("02_SUPPLIER", "part_number", "PN-70725"),
    ("02_SUPPLIER", "quantity", 44),
    ("03_BOM", "po_number", "PO-1001"),
    ("03_BOM", "part_number", "PN-70725"),
    ("03_BOM", "material_grade", "INCONEL 725"),
    ("04_MATERIAL_SPEC", "material_grade", "INCONEL 725"),
    ("05_MATERIAL_CERT", "heat_number", "W3535"),
    ("05_MATERIAL_CERT", "material_grade", "INCONEL 725"),
    ("05_MATERIAL_CERT", "chemistry.Ni", 58.10),
    ("05_MATERIAL_CERT", "chemistry.Cr", 20.80),
    ("06_CERTIFICATE", "po_number", "PO-1001"),
    ("06_CERTIFICATE", "heat_number", "W3535"),
    ("07_LADLE", "heat_number", "W3535"),
    ("07_LADLE", "material_grade", "INCONEL 725"),
    ("07_LADLE", "chemistry.Ni", 58.14),
    ("07_LADLE", "chemistry.Cr", 20.80),
    ("08_MECHANICAL", "heat_number", "W3535"),
    ("08_MECHANICAL", "part_number", "PN-70725"),
    ("08_MECHANICAL", "tensile_strength_mpa", 910.107963),
    ("09_HARDNESS", "heat_number", "W3535"),
    ("11_MATERIAL_SPEC", "material_grade", "INCONEL 725"),
    ("12_FINAL", "part_number", "PN-70725"),
    ("12_FINAL", "heat_number", "W3535"),
]


def generate_demo_packet(root: str | Path) -> dict[str, Path]:
    """Write human-readable raw fixtures and adapter-ready mock OCR JSON."""
    packet_root = Path(root)
    raw_dir = packet_root / "raw_documents"
    ocr_dir = packet_root / "mock_ocr"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ocr_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for position, document in enumerate(packet_documents(), start=1):
        stem = Path(document["filename"]).stem
        raw_path = raw_dir / f"{stem}.txt"
        ocr_path = ocr_dir / document["filename"]
        raw_path.write_text(document["text"] + "\n", encoding="utf-8")
        payload = {
            "adapter": "existing_ocr_fixture_v1",
            "page_count": 1,
            "text": document["text"],
            "fields": document["fields"],
        }
        ocr_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        manifest.append(
            {
                "sequence": position,
                "raw_document": raw_path.name,
                "ocr_result": ocr_path.name,
            }
        )
    (packet_root / "fixture_manifest.json").write_text(
        json.dumps({"packet": "industrial_material_demo_v1", "documents": manifest}, indent=2),
        encoding="utf-8",
    )
    (packet_root / "ground_truth.json").write_text(
        json.dumps(
            {
                "scope": "sealed synthetic benchmark truth; not consumed by extraction or reconciliation",
                "record_truth": GROUND_TRUTH,
                "critical_field_truth": [
                    {"document_fragment": doc, "field_name": name, "expected": value}
                    for doc, name, value in EXPECTED_CRITICAL_FIELDS
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"root": packet_root, "raw": raw_dir, "ocr": ocr_dir}
