"""빌드 변환 test (원본 파일 없이 돌아감).  python -m unittest discover tests"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from common import load_rules
from guide_docx import guide_group, normalize_tables, restructure


class GuideTables(unittest.TestCase):
    def test_google_docs_header_cells_become_td(self):
        # 구글 문서에서 내보낸 docx는 모든 칸이 th·thead로 나온다 → 선 스타일이 빠졌던 원인
        src = '<table><thead><tr><th><p>a</p></th><th colspan="2"><p>b</p></th></tr></thead></table>'
        self.assertEqual(normalize_tables(src),
                         '<table><tr><td><p>a</p></td><td colspan="2"><p>b</p></td></tr></table>')

    def test_td_tables_unchanged(self):
        src = '<table><tr><td><p>a</p></td></tr></table><p>then</p>'
        self.assertEqual(normalize_tables(src), src)


class GuideRestructure(unittest.TestCase):
    def test_bold_single_bullet_becomes_topic(self):
        self.assertEqual(restructure('<ul><li><strong>치료</strong></li></ul>'), '<h3>치료</h3>')

    def test_bullet_with_text_after_bold_stays_list(self):
        src = '<ul><li><strong>정의:</strong> 요로감염 증상 없이</li></ul>'
        self.assertEqual(restructure(src), src)

    def test_bold_paragraph_becomes_subheading(self):
        self.assertEqual(restructure('<p><strong>1) 언제 검사를 해야 하나?</strong></p>'), '<h4>1) 언제 검사를 해야 하나?</h4>')
        underlined = '<p><strong><u>3) 주로 이것을 시행</u></strong></p>'  # 강조 문장은 제목으로 바꾸지 않음
        self.assertEqual(restructure(underlined), underlined)

    def test_dash_paragraphs_become_one_list(self):
        src = '<p>- 가</p><p>- <span class="muted">나</span></p><p>다음 문단</p><p><span class="muted">- 라</span></p>'
        self.assertEqual(restructure(src),
                         '<ul><li>가</li><li><span class="muted">나</span></li></ul><p>다음 문단</p>'
                         '<ul><li><span class="muted">라</span></li></ul>')

    def test_numbered_heading2_drops_repeated_disease_name(self):
        self.assertEqual(restructure('<h2>폐렴 (1) 지역사회획득 폐렴 (CAP)</h2>'), '<h2>1. 지역사회획득 폐렴 (CAP)</h2>')
        self.assertEqual(restructure('<h2>흉수 (Pleural effusion) (1) 부폐렴성 흉수</h2>'), '<h2>1. 부폐렴성 흉수</h2>')
        self.assertEqual(restructure('<h2>A형간염</h2>'), '<h2>A형간염</h2>')

    def test_image_at_paragraph_start_is_split_off(self):
        src = '<p><strong><img alt="" src="data/img/f.png" /></strong>- 단순 vs 복잡성</p>'
        self.assertEqual(restructure(src), '<p><img alt="" src="data/img/f.png" /></p><ul><li>단순 vs 복잡성</li></ul>')
        self.assertEqual(restructure('<p><strong><img src="x" /></strong></p>'), '<p><img src="x" /></p>')

    def test_tables_untouched(self):
        src = '<table><tr><td><p>- 표 안</p><ul><li><strong>표 안 굵게</strong></li></ul></td></tr></table>'
        self.assertEqual(restructure(src), src)


class GuideGroups(unittest.TestCase):
    def test_groups_from_rules(self):
        rules = load_rules()
        self.assertEqual(guide_group('감염내과 약제 목록', rules), '약제 부록')
        self.assertEqual(guide_group('성인 예방접종', rules), '예방접종')
        self.assertEqual(guide_group('요로감염', rules), '질환')


if __name__ == '__main__':
    unittest.main()
