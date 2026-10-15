"""
RAG Evaluation Runner.
Jalankan: python tests/evaluation/run_evaluation.py --dataset sample_questions.jsonl

Membutuhkan API berjalan dan token valid.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalResult:
    question_id: str
    question: str
    category: str
    status: str
    answer: str
    sources: list
    latency_ms: float
    passed: bool
    failure_reason: str = ""


@dataclass
class EvalSummary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    hit_rate: float = 0.0
    fallback_correct: int = 0
    fallback_total: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    results: list[EvalResult] = field(default_factory=list)


async def run_question(
    session,
    base_url: str,
    token: str,
    question: str,
) -> tuple[dict, float]:
    """Kirim satu pertanyaan ke API dan ukur latency."""
    import aiohttp

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"question": question}

    start = time.monotonic()
    async with session.post(
        f"{base_url}/api/v1/chat",
        json=body,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=120),
    ) as resp:
        data = await resp.json()
    latency_ms = (time.monotonic() - start) * 1000

    return data, latency_ms


def evaluate_result(data: dict, test_case: dict) -> tuple[bool, str]:
    """Evaluasi apakah jawaban memenuhi kriteria test case."""
    answer = data.get("answer", "").lower()
    status = data.get("status", "")
    expected_status = test_case.get("expected_status", "completed")
    keywords = test_case.get("expected_answer_contains", [])

    # Cek status
    if expected_status == "no_sources" and status not in ("no_sources", "failed"):
        return False, f"Expected no_sources, got {status}"

    # Cek keywords jika ada
    missing = [kw for kw in keywords if kw.lower() not in answer]
    if missing:
        return False, f"Missing keywords: {missing}"

    return True, ""


async def main(dataset_path: str, base_url: str, token: str, output_path: str):
    import aiohttp

    dataset = []
    with open(dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                dataset.append(json.loads(line))

    print(f"Menjalankan evaluasi: {len(dataset)} pertanyaan")
    print(f"API: {base_url}")
    print("-" * 50)

    summary = EvalSummary(total=len(dataset))
    latencies = []

    async with aiohttp.ClientSession() as session:
        for tc in dataset:
            print(f"[{tc['id']}] {tc['question'][:60]}...")
            try:
                data, latency = await run_question(session, base_url, token, tc["question"])
                passed, reason = evaluate_result(data, tc)

                result = EvalResult(
                    question_id=tc["id"],
                    question=tc["question"],
                    category=tc["category"],
                    status=data.get("status", "unknown"),
                    answer=data.get("answer", "")[:200],
                    sources=[s.get("document_name") for s in data.get("sources", [])],
                    latency_ms=round(latency, 1),
                    passed=passed,
                    failure_reason=reason,
                )
                summary.results.append(result)
                latencies.append(latency)

                if passed:
                    summary.passed += 1
                    print(f"    ✅ PASS ({latency:.0f}ms)")
                else:
                    summary.failed += 1
                    print(f"    ❌ FAIL: {reason} ({latency:.0f}ms)")

                if tc.get("expected_status") == "no_sources":
                    summary.fallback_total += 1
                    if data.get("status") == "no_sources":
                        summary.fallback_correct += 1

            except Exception as e:
                print(f"    ⚠️  ERROR: {e}")
                summary.failed += 1

    # Hitung metrik
    if latencies:
        summary.avg_latency_ms = round(sum(latencies) / len(latencies), 1)
        sorted_lat = sorted(latencies)
        p95_idx = int(len(sorted_lat) * 0.95)
        summary.p95_latency_ms = round(sorted_lat[p95_idx], 1)

    if summary.total > 0:
        summary.hit_rate = round(summary.passed / summary.total * 100, 1)

    # Print summary
    print("\n" + "=" * 50)
    print("HASIL EVALUASI RAG")
    print("=" * 50)
    print(f"Total pertanyaan : {summary.total}")
    print(f"Lulus            : {summary.passed} ({summary.hit_rate}%)")
    print(f"Gagal            : {summary.failed}")
    print(f"Fallback correct : {summary.fallback_correct}/{summary.fallback_total}")
    print(f"Avg latency      : {summary.avg_latency_ms}ms")
    print(f"P95 latency      : {summary.p95_latency_ms}ms")
    print("=" * 50)

    # Simpan hasil
    output = {
        "summary": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "hit_rate_pct": summary.hit_rate,
            "fallback_correct": summary.fallback_correct,
            "fallback_total": summary.fallback_total,
            "avg_latency_ms": summary.avg_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
        },
        "results": [
            {
                "id": r.question_id,
                "category": r.category,
                "passed": r.passed,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "sources": r.sources,
                "failure_reason": r.failure_reason,
            }
            for r in summary.results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nHasil disimpan ke: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")
    parser.add_argument("--dataset", default="sample_questions.jsonl")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", default=os.environ.get("EVAL_TOKEN", ""))
    parser.add_argument("--output", default="eval_results.json")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: Set token via --token atau EVAL_TOKEN environment variable")
        print("Dapatkan token dari: POST /api/v1/auth/login")
        sys.exit(1)

    asyncio.run(main(args.dataset, args.base_url, args.token, args.output))
