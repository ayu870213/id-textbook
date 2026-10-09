"""빌드 스크립트 공통: 경로, 오류, 규칙 파일."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(ROOT, 'config', 'rules.json')


class BuildError(Exception):
    pass


def load_rules():
    """config/rules.json: 약별 체중 규칙, 이름 예외, 가이드 분류, 기본 선택 약."""
    with open(RULES_PATH, encoding='utf-8') as f:
        rules = json.load(f)
    unknown = sorted(set(rules['drug_weight'].values()) - set(rules['weight_rules']))
    if unknown:
        raise BuildError(f'config/rules.json: weight_rules에 없는 체중 규칙: {", ".join(unknown)}')
    return rules
