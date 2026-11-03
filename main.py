import json
import math
import re
import time
from pathlib import Path

EPSILON = 1e-9
DATA_FILE = Path(__file__).resolve().parent / "data.json"
CROSS_3 = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]


def mac(pattern, filter_data):
    score = 0.0
    for i in range(len(pattern)):
        for j in range(len(pattern[i])):
            score += pattern[i][j] * filter_data[i][j]
    return score


def valid_matrix(matrix, size):
    if not isinstance(matrix, list) or len(matrix) != size:
        return False
    for row in matrix:
        if not isinstance(row, list) or len(row) != size:
            return False
        for value in row:
            if (isinstance(value, bool) or
                    not isinstance(value, (int, float)) or
                    not math.isfinite(value)):
                return False
    return True


def normalize_label(label):
    if not isinstance(label, str):
        raise ValueError("라벨은 문자열이어야 합니다.")
    labels = {"+": "Cross", "cross": "Cross", "x": "X"}
    result = labels.get(label.strip().lower())
    if result is None:
        raise ValueError(f"알 수 없는 라벨: {label}")
    return result


def decide(score_a, score_b, label_a="A", label_b="B"):
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b


def measure_mac(pattern, filter_data, repeats=10):
    start = time.perf_counter()
    for _ in range(repeats):
        mac(pattern, filter_data)
    elapsed = time.perf_counter() - start
    return elapsed * 1000 / repeats


def show_performance(samples):
    print("\n[성능 분석] MAC 함수 10회 평균")
    print(f"{'크기':<10} {'평균 시간(ms)':>15} {'연산 횟수(N²)':>17}")
    print("-" * 46)
    for size in (3, 5, 13, 25):
        if size not in samples:
            print(f"{size}x{size:<7} {'측정 불가':>15} {'-':>17}")
            continue
        pattern, filter_data = samples[size]
        if not valid_matrix(pattern, size) or not valid_matrix(filter_data, size):
            print(f"{size}x{size:<7} {'데이터 오류':>15} {'-':>17}")
            continue
        average_ms = measure_mac(pattern, filter_data, repeats=10)
        print(f"{str(size) + 'x' + str(size):<10} {average_ms:>15.6f} {size * size:>17}")


def input_matrix(name):
    print(f"\n{name} (3줄 입력, 공백 구분)")
    matrix = []
    while len(matrix) < 3:
        try:
            row = [float(value) for value in input().split()]
            if len(row) != 3 or not all(math.isfinite(v) for v in row):
                print("입력 형식 오류: 각 줄에 3개의 유한한 숫자를 입력하세요.")
                continue
            matrix.append(row)
        except ValueError:
            print("입력 형식 오류: 숫자만 입력하세요.")
    return matrix


def manual_mode():
    print("\n[1] 필터 입력")
    filter_a = input_matrix("필터 A")
    filter_b = input_matrix("필터 B")
    print("\n필터 A, B 저장 완료")
    print("\n[2] 패턴 입력")
    pattern = input_matrix("패턴")

    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    result = decide(score_a, score_b)
    average_ms = (measure_mac(pattern, filter_a) +
                  measure_mac(pattern, filter_b)) / 2

    print("\n[3] MAC 계산 결과")
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"평균 연산 시간(각 10회): {average_ms:.6f} ms")
    print(f"판정: {result}")
    show_performance({3: (pattern, filter_a)})


def json_mode():
    print("\n[1] JSON 데이터 로드")
    try:
        with DATA_FILE.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("JSON 최상위 구조 오류")
        filters = data["filters"]
        patterns = data["patterns"]
        if not isinstance(filters, dict) or not isinstance(patterns, dict):
            raise ValueError("filters 또는 patterns 구조 오류")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"JSON 파일 로드 실패: {error}")
        return

    for size in (5, 13, 25):
        key = f"size_{size}"
        print(f"{key} 필터 {'확인' if key in filters else '누락'}")

    print("\n[2] 패턴 자동 분석")
    passed = 0
    failures = []
    samples = {3: (CROSS_3, CROSS_3)}

    for case_id, case in patterns.items():
        print(f"\n--- {case_id} ---")
        try:
            match = re.fullmatch(r"size_(\d+)_(\d+)", case_id)
            if not match:
                raise ValueError("패턴 키 형식 오류")
            size = int(match.group(1))
            if not isinstance(case, dict):
                raise ValueError("패턴 구조 오류")
            pattern = case["input"]
            expected = normalize_label(case["expected"])
            if not valid_matrix(pattern, size):
                raise ValueError("패턴 크기 또는 숫자 데이터 오류")

            group = filters[f"size_{size}"]
            if not isinstance(group, dict):
                raise ValueError("필터 구조 오류")
            standard = {}
            for label, matrix in group.items():
                normalized = normalize_label(label)
                if normalized in standard:
                    raise ValueError("필터 라벨 중복")
                if not valid_matrix(matrix, size):
                    raise ValueError("필터 크기 또는 숫자 데이터 오류")
                standard[normalized] = matrix
            if set(standard) != {"Cross", "X"}:
                raise ValueError("Cross 또는 X 필터 누락")

            cross_score = mac(pattern, standard["Cross"])
            x_score = mac(pattern, standard["X"])
            result = decide(cross_score, x_score, "Cross", "X")
            samples[size] = (pattern, standard["Cross"])
            print(f"Cross 점수: {cross_score:.15f}")
            print(f"X 점수: {x_score:.15f}")
            if result == expected:
                passed += 1
                print(f"판정: {result} | expected: {expected} | PASS")
            else:
                reason = ("동점 규칙에 따른 UNDECIDED" if result == "UNDECIDED"
                          else "판정과 정답 불일치")
                failures.append((case_id, reason))
                print(f"판정: {result} | expected: {expected} | FAIL ({reason})")
        except (KeyError, TypeError, ValueError) as error:
            reason = f"데이터/스키마 오류: {error}"
            failures.append((case_id, reason))
            print(f"FAIL ({reason})")

    show_performance(samples)
    print("\n[4] 결과 요약")
    print(f"총 테스트: {len(patterns)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(failures)}개")
    if failures:
        print("\n실패 케이스:")
        for case_id, reason in failures:
            print(f"- {case_id}: {reason}")
    else:
        print("실패 케이스 없음")


def main():
    print("=== Mini NPU Simulator ===")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    mode = input("선택: ").strip()
    if mode == "1":
        manual_mode()
    elif mode == "2":
        json_mode()
    else:
        print("잘못된 선택입니다. 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
