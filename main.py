import json
import math
import re
import time
from pathlib import Path

EPSILON = 1e-9
DATA_FILE = Path(__file__).resolve().parent / "data.json"
CROSS_3 = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
PERFORMANCE_REPEATS = 1000


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


def display_manual_decision(result):
    if result == "UNDECIDED":
        return f"판정 불가 (|A-B| < {EPSILON:g})"
    return result


def measure_mac(pattern, filter_data, repeats=PERFORMANCE_REPEATS):
    # 첫 호출은 워밍업으로 사용하고 측정 시간에서 제외한다.
    mac(pattern, filter_data)

    start = time.perf_counter()
    for _ in range(repeats):
        mac(pattern, filter_data)
    elapsed = time.perf_counter() - start
    return elapsed * 1000 / repeats


def show_performance(samples):
    print(f"\n[성능 분석] MAC 함수 {PERFORMANCE_REPEATS}회 평균 (워밍업 1회 제외)")
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
        average_ms = measure_mac(pattern, filter_data)
        print(f"{str(size) + 'x' + str(size):<10} {average_ms:>15.6f} {size * size:>17}")


def flatten_matrix(matrix):
    """2차원 행렬을 행 순서대로 1차원 배열로 변환한다."""
    return [value for row in matrix for value in row]


def mac_flat(pattern_flat, filter_flat):
    """1차원 배열의 같은 위치끼리 곱하고 더한다."""
    if len(pattern_flat) != len(filter_flat):
        raise ValueError("1차원 배열 길이 불일치")
    score = 0.0
    for i in range(len(pattern_flat)):
        score += pattern_flat[i] * filter_flat[i]
    return score


def benchmark_bonus(samples, repeats=1000):
    """동일한 입력과 횟수로 2차원/1차원 MAC의 계산 구간만 측정한다."""
    print(f"\n[보너스 1] 2차원 vs 1차원 MAC 성능 비교 (각 {repeats}회 평균)")
    print(f"{'크기':<8} {'2차원(ms)':>13} {'1차원(ms)':>13} {'점수 일치':>12}")
    print("-" * 51)

    for size in (3, 5, 13, 25):
        sample = samples.get(size)
        if sample is None:
            print(f"{size}x{size:<5} {'측정 불가':>13}")
            continue
        pattern, filter_data = sample
        if not valid_matrix(pattern, size) or not valid_matrix(filter_data, size):
            print(f"{size}x{size:<5} {'데이터 오류':>13}")
            continue

        # 변환 시간은 MAC 연산 시간과 분리한다.
        p_flat = flatten_matrix(pattern)
        f_flat = flatten_matrix(filter_data)
        score_2d = mac(pattern, filter_data)
        score_1d = mac_flat(p_flat, f_flat)
        same = math.isclose(score_2d, score_1d, rel_tol=0, abs_tol=EPSILON)

        # 두 방식 모두 첫 호출을 워밍업으로 사용하고 측정에서 제외한다.
        mac(pattern, filter_data)
        mac_flat(p_flat, f_flat)

        start = time.perf_counter()
        for _ in range(repeats):
            mac(pattern, filter_data)
        time_2d = (time.perf_counter() - start) * 1000 / repeats

        start = time.perf_counter()
        for _ in range(repeats):
            mac_flat(p_flat, f_flat)
        time_1d = (time.perf_counter() - start) * 1000 / repeats

        print(f"{str(size) + 'x' + str(size):<8} {time_2d:>13.6f} "
              f"{time_1d:>13.6f} {('일치' if same else '불일치'):>12}")
        if not same:
            print(f"  주의: 점수 불일치 (2D={score_2d}, 1D={score_1d})")

    print("※ 배열 변환 및 출력 시간 제외, 동일 입력·동일 반복 횟수 기준")
    print("※ 각 방식 첫 호출은 워밍업으로 제외했습니다.")
    print("※ 1차원이 반드시 더 빠른 것은 아니며 실행마다 결과가 달라질 수 있습니다.")


def load_filter_groups(filters):
    """필터를 한 번만 검증하고 Cross/X 표준 라벨로 정리한다."""
    loaded = {}
    errors = {}

    for size in (5, 13, 25):
        filter_key = f"size_{size}"
        try:
            group = filters[filter_key]
            if not isinstance(group, dict):
                raise ValueError("필터 그룹 구조 오류")

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

            loaded[size] = standard
        except (KeyError, TypeError, ValueError) as error:
            errors[size] = str(error)

    return loaded, errors


def generate_pattern(size, label):
    """홀수 N에 대해 0/1 Cross 또는 X 패턴을 만든다."""
    if not isinstance(size, int) or isinstance(size, bool) or size < 3 or size > 25 or size % 2 == 0:
        raise ValueError("크기는 3~25 범위의 홀수여야 합니다.")
    label = normalize_label(label)
    center = size // 2
    matrix = []
    for row in range(size):
        values = []
        for col in range(size):
            if label == "Cross":
                value = 1 if row == center or col == center else 0
            else:
                value = 1 if row == col or row + col == size - 1 else 0
            values.append(value)
        matrix.append(values)
    return matrix


def generator_mode():
    print("\n[보너스 2] Cross / X 패턴 자동 생성")
    while True:
        raw = input("크기 N (3~25 사이 홀수): ").strip()
        try:
            size = int(raw)
            if size < 3 or size > 25 or size % 2 == 0:
                raise ValueError
            break
        except ValueError:
            print("입력 오류: 3~25 사이 홀수(예: 3, 5, 13, 25)를 입력하세요.")

    cross = generate_pattern(size, "Cross")
    x_pattern = generate_pattern(size, "X")
    for name, matrix in (("Cross", cross), ("X", x_pattern)):
        print(f"\n{name} ({size}x{size})")
        for row in matrix:
            print(" ".join(map(str, row)))

    print("\n[자동 생성 패턴 MAC 판정]")
    for label, pattern in (("Cross", cross), ("X", x_pattern)):
        score_cross = mac(pattern, cross)
        score_x = mac(pattern, x_pattern)
        result = decide(score_cross, score_x, "Cross", "X")
        print(f"{label}: Cross={score_cross:.1f}, X={score_x:.1f} -> {result}")

    avg_ms = measure_mac(cross, cross, repeats=PERFORMANCE_REPEATS)
    print(f"\n[생성된 {size}x{size} 패턴의 성능 분석]")
    print(f"{PERFORMANCE_REPEATS}회 평균 MAC 시간: {avg_ms:.6f} ms | 연산 횟수: {size * size}")
    # 보너스 1 함수도 자동 생성 패턴으로 재활용한다.
    flat_cross = flatten_matrix(cross)
    score_2d = mac(cross, cross)
    score_1d = mac_flat(flat_cross, flat_cross)
    same = math.isclose(score_2d, score_1d, rel_tol=0, abs_tol=EPSILON)
    print(f"2차원/1차원 MAC 점수 일치: {'일치' if same else '불일치'}")


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

    print("\n[3] 3x3 입력·MAC 계산 통합 결과")
    print("입력 필터: A(3x3), B(3x3) - 총 2개")
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"점수 차이: {abs(score_a - score_b):.12g}")
    print(f"평균 연산 시간(각 {PERFORMANCE_REPEATS}회, 단위 ms): {average_ms:.6f} ms")
    print(f"판정: {display_manual_decision(result)}")

    show_performance({3: (pattern, filter_a)})
    # 모드 1은 3x3 입력만 있으므로 해당 크기만 비교한다.
    benchmark_bonus({3: (pattern, filter_a)})


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

    print(f"JSON 로드 완료: filters={len(filters)}개 크기, patterns={len(patterns)}개 케이스")

    print("\n[2] 필터 로드 및 검증")
    loaded_filters, filter_errors = load_filter_groups(filters)
    for size in (5, 13, 25):
        filter_key = f"size_{size}"
        if size in loaded_filters:
            print(f"✓ {filter_key} 필터 로드 완료 (Cross, X)")
        else:
            print(f"✗ {filter_key} 필터 로드 실패: {filter_errors.get(size, '필터 누락')}")

    print("\n[3] 패턴 자동 분석")
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

            if size not in loaded_filters:
                filter_reason = filter_errors.get(size, "해당 크기의 필터 누락")
                raise ValueError(f"필터 로드 실패: {filter_reason}")

            standard = loaded_filters[size]
            filter_key = f"size_{size}"
            print(f"JSON 선택 로그: patterns[{case_id}] -> N={size} -> "
                  f"filters[{filter_key}] -> Cross/X 필터 선택 완료")

            cross_score = mac(pattern, standard["Cross"])
            x_score = mac(pattern, standard["X"])
            score_difference = abs(cross_score - x_score)
            result = decide(cross_score, x_score, "Cross", "X")
            samples[size] = (pattern, standard["Cross"])

            print(f"Cross 점수: {cross_score:.15f}")
            print(f"X 점수: {x_score:.15f}")
            print(f"점수 차이: {score_difference:.15g} (동점 기준: {EPSILON:g})")

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
    benchmark_bonus(samples)
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
    print("3. 패턴 자동 생성 (보너스 2)")
    mode = input("선택: ").strip()
    if mode == "1":
        manual_mode()
    elif mode == "2":
        json_mode()
    elif mode == "3":
        generator_mode()
    else:
        print("잘못된 선택입니다. 1, 2 또는 3을 입력하세요.")


if __name__ == "__main__":
    main()
