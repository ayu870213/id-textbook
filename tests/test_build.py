"""빌드 변환 test (원본 파일 없이 돌아감).  python -m unittest discover tests"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from common import load_rules
from guide_docx import guide_group, normalize_tables


class GuideTables(unittest.TestCase):
    def test_google_docs_header_cells_become_td(self):
        # 구글 문서에서 내보낸 docx는 모든 칸이 th·thead로 나온다 → 선 스타일이 빠졌던 원인
        src = '<table><thead><tr><th><p>a</p></th><th colspan="2"><p>b</p></th></tr></thead></table>'
        self.assertEqual(normalize_tables(src),
                         '<table><tr><td><p>a</p></td><td colspan="2"><p>b</p></td></tr></table>')

    def test_td_tables_unchanged(self):
        src = '<table><tr><td><p>a</p></td></tr></table><p>then</p>'
        self.assertEqual(normalize_tables(src), src)


class GuideGroups(unittest.TestCase):
    def test_groups_from_rules(self):
        rules = load_rules()
        self.assertEqual(guide_group('감염내과 약제 목록', rules), '약제 부록')
        self.assertEqual(guide_group('성인 예방접종', rules), '예방접종')
        self.assertEqual(guide_group('요로감염', rules), '질환')


if __name__ == '__main__':
    unittest.main()
