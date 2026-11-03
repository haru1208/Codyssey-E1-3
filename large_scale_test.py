"""Codyssey E1-3: 1000x1000 MAC 실제 실행 및 행 단위 최적화 비교.

기존 main.py와 같은 폴더에 저장하고 실행하세요.
원본 main.py/data.json은 수정하지 않습니다.
"""

import sys
import time
from main import EPSILON, decide, mac

N = 1000


def bit_at(kind, row, col, size):
    """짝수 크기는 중앙 두 행/열을 Cross로 정의합니다."""
    if kind == "Cross":
        centers = (size // 2 - 1, size // 2) if size % 2 == 0 else (size // 2,)
        return int(row in centers or col in centers)
    if kind == "X":
        return int(row == col or row + col == size - 1)
    raise ValueError(f"알 수 없는 패턴: {kind}")


def build_matrix(kind, size):
    return [[bit_at(kind, r, c, size) for c in range(size)] for r in range(size)]


def mac_streaming(pattern_kind, filter_kind, size):
    """전체 N×N 배열을 보관하지 않고 행 단위로 생성해 MAC 계산합니다."""
    score = 0.0
    for r in range(size):
        p_row = [bit_at(pattern_kind, r, c, size) for c in range(size)]
        f_row = [bit_at(filter_kind, r, c, size) for c in range(size)]
        for c in range(size):
            score += p_row[c] * f_row[c]
    return score


def matrix_container_bytes(matrix):
    """리스트 객체와 참조 공간을 세며, 공유된 정수 0/1 객체는 제외합니다."""
    return sys.getsizeof(matrix) + sum(sys.getsizeof(row) for row in matrix)


def main():
    print(f"=== {N}x{N} 대형 MAC 실제 실행 검증 ===")
    print("짝수 N의 Cross: 중앙 두 행과 중앙 두 열을 1로 정의")
    print("X: 두 대각선을 1로 정의")
    print("※ N=1000을 실제 생성·계산합니다. 기존 과제 모드는 변경하지 않습니다.\n")

    start = time.perf_counter()
    cross = build_matrix("Cross", N)
    x_pattern = build_matrix("X", N)
    build_s = time.perf_counter() - start
    full_container_mb = (matrix_container_bytes(cross) + matrix_container_bytes(x_pattern)) / 1024**2
    print(f"두 개의 2차원 행렬 생성: {build_s:.3f}초")
    print(f"2개 행렬의 리스트/참조 공간: 약 {full_container_mb:.2f} MiB (정수 객체·Python 프로세스 전체 메모리는 제외)")
    print(f"한 번의 MAC 연산 위치 수: {N*N:,}개\n")

    all_ok = True
    for label, pattern in (("Cross", cross), ("X", x_pattern)):
        start = time.perf_counter()
        score_cross_2d = mac(pattern, cross)
        score_x_2d = mac(pattern, x_pattern)
        full_time = time.perf_counter() - start

        start = time.perf_counter()
        score_cross_stream = mac_streaming(label, "Cross", N)
        score_x_stream = mac_streaming(label, "X", N)
        stream_time = time.perf_counter() - start

        matches = (abs(score_cross_2d - score_cross_stream) < EPSILON and
                   abs(score_x_2d - score_x_stream) < EPSILON)
        verdict = decide(score_cross_2d, score_x_2d, "Cross", "X")
        ok = matches and verdict == label
        all_ok = all_ok and ok
        print(f"[{label} 입력]")
        print(f"  2차원 MAC: Cross={score_cross_2d:.1f}, X={score_x_2d:.1f} → {verdict}")
        print(f"  행 단위 MAC: Cross={score_cross_stream:.1f}, X={score_x_stream:.1f}")
        print(f"  점수 일치: {'PASS' if matches else 'FAIL'} / 판정: {'PASS' if ok else 'FAIL'}")
        print(f"  2차원 MAC 2회: {full_time:.3f}초 / 행 단위 MAC 2회: {stream_time:.3f}초\n")

    print("행 단위 방식은 전체 N×N 행렬을 저장하지 않고 O(N) 크기의 행 버퍼만 사용합니다.")
    print("성능: 행 단위 Python 생성 비용이 있어 반드시 더 빠른 방식은 아닙니다.")
    print(f"최종 검증: {'PASS' if all_ok else 'FAIL'}")
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
