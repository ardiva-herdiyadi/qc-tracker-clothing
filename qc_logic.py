"""
qc_logic.py - Modul Logika Bisnis End-of-Line Quality Control (QC)
PT. Ardiva Clothing (Muslim Wear Division)

Modul ini berisi fungsi-fungsi murni (pure functions) untuk menghitung
defect rate, menentukan status kelayakan batch garmen, dan validasi data.
"""

from typing import Dict, Any


def calculate_defect_rate(total_inspected: int, total_defects: int) -> float:
    """
    Menghitung persentase cacat pakaian (defect rate).

    Formula:
        (total_defects / total_inspected) * 100

    Args:
        total_inspected (int): Jumlah pakaian yang diperiksa (harus > 0).
        total_defects (int): Jumlah total pakaian cacat yang ditemukan (>= 0).

    Returns:
        float: Persentase cacat dibulatkan ke 2 angka di belakang koma.

    Raises:
        ValueError: Jika total_inspected <= 0, total_defects < 0,
                    atau total_defects > total_inspected.
    """
    if total_inspected <= 0:
        raise ValueError("Total pakaian yang diperiksa harus lebih dari 0.")
    if total_defects < 0:
        raise ValueError("Total cacat tidak boleh bernilai negatif.")
    if total_defects > total_inspected:
        raise ValueError(
            f"Total cacat ({total_defects} pcs) tidak boleh melebihi "
            f"total pakaian yang diperiksa ({total_inspected} pcs)."
        )

    rate = (total_defects / total_inspected) * 100.0
    return round(rate, 2)


def determine_qc_status(defect_rate: float) -> Dict[str, str]:
    """
    Menentukan keputusan dan rekomendasi status QC berdasarkan defect rate.

    Ambang Batas (Thresholds):
        - defect_rate <= 3.0% : LOLOS QC (PASS) - Hijau
        - 3.0% < defect_rate <= 5.0% : PERINGATAN (WARNING) - Oranye
        - defect_rate > 5.0% : TAHAN BATCH (HOLD / REJECT) - Merah

    Args:
        defect_rate (float): Persentase cacat (>= 0.0).

    Returns:
        dict: Dictionary berisi 'status', 'color', dan 'recommendation'.

    Raises:
        ValueError: Jika defect_rate bernilai negatif.
    """
    if defect_rate < 0.0:
        raise ValueError("Defect rate tidak boleh bernilai negatif.")

    if defect_rate <= 3.0:
        return {
            "status": "LOLOS QC (PASS)",
            "color": "green",
            "recommendation": (
                "Batch aman. Lanjutkan ke proses Packing & Gudang Barang Jadi."
            ),
        }
    elif defect_rate <= 5.0:
        return {
            "status": "PERINGATAN (WARNING)",
            "color": "orange",
            "recommendation": (
                "Perlu inspeksi ulang oleh Supervisor QC dan perbaikan (rework) "
                "pada pakaian yang cacat."
            ),
        }
    else:
        return {
            "status": "TAHAN BATCH (HOLD / REJECT)",
            "color": "red",
            "recommendation": (
                "STOP pengiriman batch ini! Kembalikan ke lini jahit dan "
                "lakukan evaluasi mesin/operator."
            ),
        }


def evaluate_batch(
    total_inspected: int,
    skip_stitch: int,
    stain: int,
    size_mismatch: int,
) -> Dict[str, Any]:
    """
    Mengevaluasi satu batch produksi garmen secara menyeluruh berdasarkan 3 jenis cacat umum:
    1. Jahitan Loncat (Skip Stitch)
    2. Noda Kain / Oli Mesin (Stain / Oil)
    3. Ukuran Meleset (Size Mismatch)

    Args:
        total_inspected (int): Total pakaian yang diperiksa.
        skip_stitch (int): Jumlah cacat jahitan loncat.
        stain (int): Jumlah cacat noda/oli.
        size_mismatch (int): Jumlah cacat ukuran tidak sesuai spek.

    Returns:
        dict: Ringkasan lengkap evaluasi batch berisi:
            - total_inspected (int)
            - total_defects (int)
            - defect_rate (float)
            - status (str)
            - color (str)
            - recommendation (str)
            - defects_breakdown (dict)

    Raises:
        ValueError: Jika ada input cacat negatif atau validasi perhitungan gagal.
    """
    if skip_stitch < 0 or stain < 0 or size_mismatch < 0:
        raise ValueError("Jumlah jenis cacat tidak boleh bernilai negatif.")

    total_defects = skip_stitch + stain + size_mismatch
    defect_rate = calculate_defect_rate(total_inspected, total_defects)
    qc_decision = determine_qc_status(defect_rate)

    return {
        "total_inspected": total_inspected,
        "total_defects": total_defects,
        "defect_rate": defect_rate,
        "status": qc_decision["status"],
        "color": qc_decision["color"],
        "recommendation": qc_decision["recommendation"],
        "defects_breakdown": {
            "skip_stitch": skip_stitch,
            "stain": stain,
            "size_mismatch": size_mismatch,
        },
    }
