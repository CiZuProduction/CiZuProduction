# RAG Evaluation Dataset

Dataset evaluasi untuk mengukur kualitas retrieval dan jawaban RAG.

## Format file

Setiap file JSONL berisi satu test case per baris:

```json
{
  "id": "unique-test-id",
  "category": "factual|comparison|summary|out_of_scope",
  "question": "Pertanyaan yang diajukan",
  "expected_answer_contains": ["kata kunci yang harus ada di jawaban"],
  "expected_sources": ["nama_dokumen.pdf"],
  "expected_status": "completed|no_sources",
  "notes": "Catatan tentang test case ini"
}
```

## Metrik yang diukur

| Metrik | Deskripsi |
|--------|-----------|
| **Hit Rate** | % pertanyaan yang menemukan sumber relevan |
| **Citation Precision** | % sumber yang benar-benar relevan |
| **Faithfulness** | Jawaban sesuai dengan konteks dokumen |
| **Fallback Correctness** | Sistem menyatakan tidak tahu jika info tidak ada |
| **Latency p50/p95** | Waktu respons median dan persentil 95 |

## Cara menjalankan evaluasi

```bash
# Dari root project
cd tests/evaluation
python run_evaluation.py --dataset sample_questions.jsonl --output results.json
```

## File dataset

- `sample_questions.jsonl` — contoh pertanyaan untuk testing awal
- Tambahkan dataset domain-spesifik sesuai dokumen yang diupload
