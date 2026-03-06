"""ストレステスト - エッジケース網羅."""

from __future__ import annotations

import asyncio
import traceback
from datetime import date

from tse_hp_front import (
    AnnouncementType,
    AsyncTseClient,
    CompensationDisclosure,
    DirectorTenure,
    ForeignOwnershipFrom,
    ForeignOwnershipTo,
    Industry,
    Market,
    OrganizationType,
    OutsideAuditorRelation,
    OutsideDirectorRelation,
    OutsideOfficerAttribute,
    ParentCompanyStatus,
    Prefecture,
    RelationPeriod,
    TseClient,
)
from tse_hp_front.parsers import parse_cg_search_result, parse_detail, parse_search_result

passed = 0
failed = 0
errors: list[str] = []


def ok(name: str) -> None:
    global passed
    passed += 1
    print(f"  PASS: {name}")


def fail(name: str, msg: str) -> None:
    global failed
    failed += 1
    errors.append(f"{name}: {msg}")
    print(f"  FAIL: {name} - {msg}")


def run(name: str, fn):
    try:
        fn()
        ok(name)
    except Exception as e:
        fail(name, f"{type(e).__name__}: {e}")
        traceback.print_exc()


async def run_async(name: str, fn):
    try:
        await fn()
        ok(name)
    except Exception as e:
        fail(name, f"{type(e).__name__}: {e}")
        traceback.print_exc()


# ===========================================================================
# 1. パーサー単体テスト（ネットワーク不要）
# ===========================================================================
def test_parsers():
    print("\n=== 1. パーサー単体テスト ===")

    # 空HTML
    def _empty_html():
        r = parse_search_result("")
        assert r.total == 0 and r.items == [], f"got {r}"

    run("parse_search_result(空HTML)", _empty_html)

    def _empty_cg():
        r = parse_cg_search_result("")
        assert r.total == 0 and r.items == [], f"got {r}"

    run("parse_cg_search_result(空HTML)", _empty_cg)

    def _empty_detail():
        d = parse_detail("")
        assert d.basic.code == "", f"got {d.basic.code}"
        assert d.cg_info == []
        assert d.disclosures.legal == []

    run("parse_detail(空HTML)", _empty_detail)

    # 壊れたHTML
    def _broken():
        r = parse_search_result("<html><body><div>incomplete")
        assert r.total == 0

    run("parse_search_result(壊れたHTML)", _broken)

    def _broken_cg():
        r = parse_cg_search_result("<<<not even html>>>")
        assert r.total == 0

    run("parse_cg_search_result(壊れたHTML)", _broken_cg)

    def _broken_detail():
        d = parse_detail("<div id='body_basicInformation'></div>")
        assert d.basic.name == ""

    run("parse_detail(壊れたHTML)", _broken_detail)

    # ランダムテキスト
    def _random():
        r = parse_search_result("これはHTMLではない。ただの日本語テキスト。")
        assert r.total == 0

    run("parse_search_result(ランダムテキスト)", _random)


# ===========================================================================
# 2. _to_code5 ヘルパー
# ===========================================================================
def test_to_code5():
    print("\n=== 2. _to_code5 ===")
    from tse_hp_front.client import _to_code5

    cases = [
        ("7203", "72030"),   # 4桁→5桁
        ("72030", "72030"),  # 5桁はそのまま
        (" 7203 ", "72030"), # 前後スペースstrip
        ("", ""),            # 空文字→空文字（len!=4なのでそのまま）
        ("1", "1"),          # 1桁→そのまま（4桁専用関数）
        ("12345", "12345"),  # 5桁→そのまま
        ("123456", "123456"),# 6桁→そのまま
    ]
    for inp, expected in cases:
        def _check(i=inp, e=expected):
            result = _to_code5(i)
            assert result == e, f"_to_code5({i!r}) = {result!r}, expected {e!r}"
        run(f"_to_code5({inp!r})", _check)


# ===========================================================================
# 3. ヘルパー関数テスト
# ===========================================================================
def test_helpers():
    print("\n=== 3. ヘルパー関数 ===")
    from tse_hp_front.client import _bool_val, _date_fields, _int_val

    # _bool_val
    def _bv():
        assert _bool_val(True) == "1"
        assert _bool_val(False) == "0"
        assert _bool_val(None) == " "
    run("_bool_val", _bv)

    # _int_val
    def _iv():
        assert _int_val(0) == "0"
        assert _int_val(100) == "100"
        assert _int_val(-1) == "-1"
        assert _int_val(None) == ""
    run("_int_val", _iv)

    # _date_fields
    def _df():
        r = _date_fields(None, "test")
        assert r == {"testYearPd": " ", "testTskPd": " ", "testDayPd": " "}

        r = _date_fields(date(2025, 1, 5), "test")
        assert r == {"testYearPd": "2025", "testTskPd": "01", "testDayPd": "05"}

        # 閏日
        r = _date_fields(date(2024, 2, 29), "x")
        assert r == {"xYearPd": "2024", "xTskPd": "02", "xDayPd": "29"}
    run("_date_fields", _df)


# ===========================================================================
# 4. Enum全値テスト
# ===========================================================================
def test_enums():
    print("\n=== 4. Enum全値 ===")

    def _market():
        assert len(Market) == 12
        for m in Market:
            assert isinstance(m.value, str) and m.value
    run("Market全値", _market)

    def _pref():
        assert len(Prefecture) == 47
        codes = [p.value for p in Prefecture]
        assert codes == [f"{i:02d}" for i in range(1, 48)]
    run("Prefecture全47値+連番", _pref)

    def _ind():
        assert len(Industry) >= 30
        for i in Industry:
            assert i.value.isdigit() or i.value == "9999"
    run("Industry全値", _ind)

    def _ann():
        assert len(AnnouncementType) == 4
    run("AnnouncementType", _ann)

    def _org():
        assert len(OrganizationType) == 3
    run("OrganizationType", _org)

    def _fof():
        assert len(ForeignOwnershipFrom) == 4
    run("ForeignOwnershipFrom", _fof)

    def _fot():
        assert len(ForeignOwnershipTo) == 3
    run("ForeignOwnershipTo", _fot)

    def _pcs():
        assert len(ParentCompanyStatus) == 4
    run("ParentCompanyStatus", _pcs)

    def _dt():
        assert len(DirectorTenure) == 2
    run("DirectorTenure", _dt)

    def _rp():
        assert len(RelationPeriod) == 4
    run("RelationPeriod", _rp)

    def _ooa():
        assert len(OutsideOfficerAttribute) == 6
    run("OutsideOfficerAttribute", _ooa)

    def _odr():
        assert len(OutsideDirectorRelation) == 11
    run("OutsideDirectorRelation", _odr)

    def _oar():
        assert len(OutsideAuditorRelation) == 13
    run("OutsideAuditorRelation", _oar)

    def _cd():
        assert len(CompensationDisclosure) == 3
    run("CompensationDisclosure", _cd)


# ===========================================================================
# 5. 同期クライアント - 検索エッジケース
# ===========================================================================
def test_sync_search_edges(client: TseClient):
    print("\n=== 5. 同期 search() エッジケース ===")

    # 完全空検索 → サーバーが検索フォームを再表示（0件）
    def _empty():
        r = client.search(limit=10)
        assert r.total == 0, "完全空検索は条件不足でフォーム再表示"
    run("完全空検索(条件なし→0件)", _empty)

    # 市場のみ指定 → ヒットあり
    def _market_only():
        r = client.search(markets=[Market.プライム], limit=10)
        assert r.total > 0, "市場指定でヒットなし"
        assert len(r.items) <= 10
    run("市場のみ指定(limit=10)", _market_only)

    # limit境界値
    for lim in [10, 50, 100, 200]:
        def _lim(l=lim):
            r = client.search(limit=l)
            assert len(r.items) <= l
        run(f"limit={lim}", _lim)

    # ヒット0件になる検索
    def _no_hit():
        r = client.search(name="ZZZZXXXXXNEVEREXIST99999")
        assert r.total == 0 and r.items == []
    run("ヒット0件", _no_hit)

    # 特殊文字入力
    for chars, label in [
        ("'; DROP TABLE --", "SQLインジェクション"),
        ("<script>alert(1)</script>", "XSS"),
        ("' OR '1'='1", "SQL OR"),
        ("%00%0d%0a", "ヌルバイト/CRLF"),
        ("あ" * 500, "超長文（500文字）"),
        ("🏢📈💹", "絵文字"),
        ("\t\n\r", "制御文字"),
        ("", "空文字"),
    ]:
        def _special(c=chars):
            r = client.search(name=c)
            # エラーにならなければOK（0件でも可）
            assert isinstance(r.total, int)
        run(f"特殊文字: {label}", _special)

    # コード検索エッジケース
    for code, label in [
        ("7203", "正常4桁"),
        ("72030", "正常5桁"),
        ("0000", "0000"),
        ("9999", "9999"),
        ("ABC", "非数字"),
        ("", "空"),
    ]:
        def _code(c=code):
            r = client.search(code=c)
            assert isinstance(r.total, int)
        run(f"code={code!r} ({label})", _code)

    # 全市場指定
    def _all_markets():
        r = client.search(markets=list(Market), limit=10)
        assert isinstance(r.total, int)
    run("全市場指定", _all_markets)

    # 上場廃止含む
    def _delisted():
        r = client.search(include_delisted=True, limit=10)
        assert r.total > 0
    run("上場廃止含む", _delisted)

    # 全都道府県で検索
    def _all_pref():
        for p in Prefecture:
            r = client.search(prefecture=p, limit=10)
            assert isinstance(r.total, int)
    run("全47都道府県", _all_pref)

    # 全業種で検索
    def _all_ind():
        for i in Industry:
            r = client.search(industry=i, limit=10)
            assert isinstance(r.total, int)
    run("全業種", _all_ind)


# ===========================================================================
# 6. 同期クライアント - 詳細検索パラメータ
# ===========================================================================
def test_sync_search_detailed(client: TseClient):
    print("\n=== 6. 同期 search() 詳細検索 ===")

    # 売買単位
    for unit in [1, 10, 50, 100, 500, 1000, 3000, -1]:
        def _unit(u=unit):
            r = client.search(trading_unit=u, limit=10)
            assert isinstance(r.total, int)
        run(f"売買単位={unit}", _unit)

    # 決算期
    for m in range(1, 13):
        def _fp(mm=m):
            r = client.search(fiscal_period=mm, limit=10)
            assert isinstance(r.total, int)
        run(f"決算期={m}月", _fp)

    # 決算期1+2の組み合わせ
    def _fp_combo():
        r = client.search(fiscal_period=3, fiscal_period_2=9, limit=10)
        assert isinstance(r.total, int)
    run("決算期3月+9月", _fp_combo)

    # 決算発表種別 全種
    def _all_ann():
        r = client.search(announcement_types=list(AnnouncementType), limit=10)
        assert isinstance(r.total, int)
    run("全決算発表種別", _all_ann)

    # 日付: 過去日
    def _past_date():
        r = client.search(
            announcement_date_from=date(2020, 1, 1),
            announcement_date_to=date(2020, 12, 31),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("日付: 2020年", _past_date)

    # 日付: 未来日
    def _future_date():
        r = client.search(
            shareholders_meeting_from=date(2030, 1, 1),
            shareholders_meeting_to=date(2030, 12, 31),
            limit=10,
        )
        assert r.total == 0
    run("日付: 2030年(未来)", _future_date)

    # 日付: from > to（逆転）
    def _reversed_date():
        r = client.search(
            announcement_date_from=date(2025, 12, 31),
            announcement_date_to=date(2025, 1, 1),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("日付: from>to逆転", _reversed_date)

    # 閏日
    def _leap():
        r = client.search(
            announcement_date_from=date(2024, 2, 29),
            announcement_date_to=date(2024, 2, 29),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("日付: 閏日2024-02-29", _leap)

    # bool系全パターン
    def _bools():
        r = client.search(
            accounting_membership=True,
            j_iriss=True,
            going_concern=False,
            controlling_shareholder=False,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("bool系: True/False混在", _bools)

    # 全パラメータ同時指定
    def _all_params():
        r = client.search(
            name="ト",
            code="",
            markets=[Market.プライム],
            limit=10,
            include_delisted=False,
            prefecture=Prefecture.東京,
            industry=Industry.電気機器,
            fiscal_period=3,
            announcement_types=[AnnouncementType.決算],
            accounting_membership=True,
            j_iriss=None,
            going_concern=False,
            controlling_shareholder=None,
        )
        assert isinstance(r.total, int)
    run("全パラメータ同時指定", _all_params)


# ===========================================================================
# 7. 同期クライアント - get_detail エッジケース
# ===========================================================================
def test_sync_detail(client: TseClient):
    print("\n=== 7. 同期 get_detail() ===")

    # 正常ケース
    def _normal():
        d = client.get_detail("7203")
        assert d.basic.code == "72030"
        assert "トヨタ" in d.basic.name
        assert d.basic.market != ""
    run("正常: 7203(トヨタ)", _normal)

    # 5桁コード
    def _code5():
        d = client.get_detail("72030")
        assert d.basic.code == "72030"
    run("5桁コード: 72030", _code5)

    # 存在しないコード
    def _nonexist():
        d = client.get_detail("0001")
        assert d.basic.code == "" or d.basic.name == ""
    run("存在しないコード: 0001", _nonexist)

    # 上場廃止銘柄（東芝）
    def _delisted():
        d = client.get_detail("6502")
        # 上場廃止でもデータは返る可能性がある
        assert isinstance(d.basic.code, str)
    run("上場廃止: 6502(東芝)", _delisted)

    # 詳細の全セクション確認
    def _sections():
        d = client.get_detail("7203")
        assert d.disclosures is not None
        assert d.filings is not None
        assert isinstance(d.cg_info, list)
    run("全セクション存在確認", _sections)


# ===========================================================================
# 8. 同期クライアント - search_cg エッジケース
# ===========================================================================
def test_sync_cg(client: TseClient):
    print("\n=== 8. 同期 search_cg() ===")

    # 完全空検索 → サーバー仕様で条件不足時はフォーム再表示
    def _empty():
        r = client.search_cg(limit=10)
        # 条件なしでもCGKは結果を返す場合がある
        assert isinstance(r.total, int)
    run("CG空検索", _empty)

    # 市場のみ指定 → ヒットあり
    def _market_only():
        r = client.search_cg(markets=[Market.プライム], limit=10)
        assert r.total > 0
        assert len(r.items) <= 10
    run("CG市場のみ指定", _market_only)

    # ヒット0件
    def _no_hit():
        r = client.search_cg(name="ZZZXXX_NEVEREXIST_999")
        assert r.total == 0
    run("CGヒット0件", _no_hit)

    # 全組織形態
    for ot in OrganizationType:
        def _ot(o=ot):
            r = client.search_cg(organization_type=o, limit=10)
            assert isinstance(r.total, int)
        run(f"組織形態: {ot.name}", _ot)

    # 外国人株式所有比率 全組合せ
    def _foreign():
        for f in ForeignOwnershipFrom:
            for t in ForeignOwnershipTo:
                r = client.search_cg(
                    foreign_ownership_from=f,
                    foreign_ownership_to=t,
                    limit=10,
                )
                assert isinstance(r.total, int)
    run("外国人所有比率 全組合せ(4x3)", _foreign)

    # 親会社状態
    for ps in ParentCompanyStatus:
        def _ps(p=ps):
            r = client.search_cg(parent_company=p, limit=10)
            assert isinstance(r.total, int)
        run(f"親会社: {ps.name}", _ps)

    # 任期
    for dt in DirectorTenure:
        def _dt(d=dt):
            r = client.search_cg(director_tenure=d, limit=10)
            assert isinstance(r.total, int)
        run(f"取締役任期: {dt.name}", _dt)

    # 社外取締役属性 全選択
    def _all_attrs():
        r = client.search_cg(
            outside_director_attributes=list(OutsideOfficerAttribute),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("社外取締役属性 全選択", _all_attrs)

    # 社外取締役の関係 全選択
    def _all_rels():
        r = client.search_cg(
            outside_director_relation_period=RelationPeriod.本人現在,
            outside_director_relations=list(OutsideDirectorRelation),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("社外取締役の関係 全選択", _all_rels)

    # 社外監査役属性 全選択
    def _aud_attrs():
        r = client.search_cg(
            outside_auditor_attributes=list(OutsideOfficerAttribute),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("社外監査役属性 全選択", _aud_attrs)

    # 社外監査役の関係 全選択
    def _aud_rels():
        r = client.search_cg(
            outside_auditor_relation_period=RelationPeriod.近親者過去,
            outside_auditor_relations=list(OutsideAuditorRelation),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("社外監査役の関係 全選択", _aud_rels)

    # 報酬開示 全選択
    def _comp():
        r = client.search_cg(
            director_compensation_disclosure=list(CompensationDisclosure),
            executive_compensation_disclosure=list(CompensationDisclosure),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("報酬開示 全選択", _comp)

    # 人数レンジ: 境界値
    def _range_boundary():
        r = client.search_cg(
            directors_from=0,
            directors_to=0,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("取締役 0〜0人", _range_boundary)

    def _range_large():
        r = client.search_cg(
            directors_from=100,
            directors_to=999,
            limit=10,
        )
        assert r.total == 0
    run("取締役 100〜999人(0件)", _range_large)

    # 逆転レンジ (from > to)
    def _range_reversed():
        r = client.search_cg(
            directors_from=20,
            directors_to=1,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("取締役 逆転レンジ 20〜1", _range_reversed)

    # bool系全パターン
    def _bools():
        r = client.search_cg(
            controlling_shareholder=True,
            optional_committee_exists=True,
            advisor_status_exists=True,
            electronic_voting=True,
            voting_platform=True,
            english_notice=True,
            compensation_policy=True,
            takeover_defense=True,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("CG bool系 全True", _bools)

    def _bools_false():
        r = client.search_cg(
            controlling_shareholder=False,
            optional_committee_exists=False,
            advisor_status_exists=False,
            electronic_voting=False,
            voting_platform=False,
            english_notice=False,
            compensation_policy=False,
            takeover_defense=False,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("CG bool系 全False", _bools_false)

    # 縦覧日
    def _viewing():
        r = client.search_cg(
            viewing_date_from=date(2024, 1, 1),
            viewing_date_to=date(2024, 12, 31),
            limit=10,
        )
        assert isinstance(r.total, int)
    run("縦覧日: 2024年", _viewing)

    # 英訳版CG報告書
    def _english():
        r = client.search_cg(english_cg_report=True, limit=10)
        assert isinstance(r.total, int)
    run("英訳版CG報告書", _english)

    # 全パラメータ同時指定（指名委員会等含む）
    def _all_params():
        r = client.search_cg(
            name="",
            markets=[Market.プライム],
            limit=10,
            organization_type=OrganizationType.指名委員会等設置会社,
            nomination_committee_from=1,
            nomination_committee_to=10,
            nomination_committee_outside_from=1,
            compensation_committee_from=1,
            audit_committee_from=1,
            executive_officers_from=1,
        )
        assert isinstance(r.total, int)
    run("CG 指名委員会系パラメータ", _all_params)

    # 監査等委員会設置会社パラメータ
    def _audit_sup():
        r = client.search_cg(
            organization_type=OrganizationType.監査等委員会設置会社,
            audit_supervisory_committee_from=1,
            audit_supervisory_committee_to=10,
            audit_supervisory_committee_outside_from=1,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("CG 監査等委員会系パラメータ", _audit_sup)

    # 任意委員会パラメータ
    def _optional():
        r = client.search_cg(
            optional_committee_exists=True,
            optional_nomination_from=1,
            optional_compensation_from=1,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("CG 任意委員会パラメータ", _optional)

    # 独立役員 + 相談役
    def _indep_adv():
        r = client.search_cg(
            independent_officers_from=3,
            advisor_status_exists=True,
            advisor_count_from=1,
            advisor_count_to=5,
            limit=10,
        )
        assert isinstance(r.total, int)
    run("独立役員+相談役", _indep_adv)

    # 親会社コード指定
    def _parent_code():
        r = client.search_cg(
            parent_company=ParentCompanyStatus.有_上場,
            parent_company_code="7203",
            limit=10,
        )
        assert isinstance(r.total, int)
    run("親会社コード指定", _parent_code)


# ===========================================================================
# 9. セッション管理
# ===========================================================================
def test_session(client: TseClient):
    print("\n=== 9. セッション管理 ===")

    # リセット後に再利用
    def _reset_reuse():
        client.reset_session()
        r = client.search(name="トヨタ", limit=10)
        assert r.total > 0
    run("reset→search", _reset_reuse)

    def _reset_cg():
        client.reset_session()
        r = client.search_cg(name="ソニー", limit=10)
        assert r.total > 0
    run("reset→search_cg", _reset_cg)

    def _reset_detail():
        client.reset_session()
        d = client.get_detail("7203")
        assert d.basic.code == "72030"
    run("reset→get_detail", _reset_detail)

    # 連続リセット
    def _multi_reset():
        for _ in range(5):
            client.reset_session()
        r = client.search(name="ソニー", limit=10)
        assert r.total > 0
    run("5回連続reset→search", _multi_reset)

    # JJKとCGK交互
    def _alternate():
        r1 = client.search(name="ソニー", limit=10)
        r2 = client.search_cg(name="ソニー", limit=10)
        r3 = client.search(name="トヨタ", limit=10)
        r4 = client.search_cg(name="トヨタ", limit=10)
        assert r1.total > 0 and r2.total > 0 and r3.total > 0 and r4.total > 0
    run("JJK/CGK交互実行", _alternate)


# ===========================================================================
# 10. 非同期クライアント
# ===========================================================================
async def test_async():
    print("\n=== 10. 非同期クライアント ===")

    async with AsyncTseClient() as client:
        # 基本動作
        async def _search():
            r = await client.search(name="トヨタ", limit=10)
            assert r.total > 0
        await run_async("async search", _search)

        async def _detail():
            d = await client.get_detail("7203")
            assert d.basic.code == "72030"
        await run_async("async get_detail", _detail)

        async def _cg():
            r = await client.search_cg(name="ソニー", limit=10)
            assert r.total > 0
        await run_async("async search_cg", _cg)

        # セッションリセット
        async def _reset():
            client.reset_session()
            r = await client.search(name="トヨタ", limit=10)
            assert r.total > 0
        await run_async("async reset→search", _reset)

        # 0件
        async def _no_hit():
            r = await client.search(name="ZZZZXXXXXNEVER")
            assert r.total == 0
        await run_async("async 0件", _no_hit)

        # 特殊文字
        async def _special():
            r = await client.search(name="<script>alert(1)</script>")
            assert isinstance(r.total, int)
        await run_async("async XSS入力", _special)

        # 全パラメータ
        async def _full():
            r = await client.search(
                name="ト",
                markets=[Market.プライム, Market.スタンダード],
                limit=10,
                prefecture=Prefecture.大阪,
                industry=Industry.機械,
                fiscal_period=3,
            )
            assert isinstance(r.total, int)
        await run_async("async 全パラメータ", _full)

        async def _full_cg():
            r = await client.search_cg(
                markets=[Market.プライム],
                organization_type=OrganizationType.監査役設置会社,
                director_tenure=DirectorTenure.二年,
                outside_director_attributes=[OutsideOfficerAttribute.弁護士],
                limit=10,
            )
            assert isinstance(r.total, int)
        await run_async("async CG全パラメータ", _full_cg)


# ===========================================================================
# 11. 同期/非同期 結果一致テスト
# ===========================================================================
async def test_sync_async_consistency():
    print("\n=== 11. 同期/非同期 結果一致 ===")

    async def _compare():
        sync = TseClient()
        async_client = AsyncTseClient()

        try:
            sync_r = sync.search(name="トヨタ", limit=10)
            async_r = await async_client.search(name="トヨタ", limit=10)

            assert sync_r.total == async_r.total, (
                f"total mismatch: sync={sync_r.total}, async={async_r.total}"
            )
            assert len(sync_r.items) == len(async_r.items), (
                f"items count mismatch: sync={len(sync_r.items)}, async={len(async_r.items)}"
            )
            for s, a in zip(sync_r.items, async_r.items):
                assert s.code == a.code, f"code mismatch: {s.code} vs {a.code}"
                assert s.name == a.name, f"name mismatch: {s.name} vs {a.name}"
        finally:
            sync.close()
            await async_client.close()

    await run_async("search結果一致", _compare)

    async def _compare_cg():
        sync = TseClient()
        async_client = AsyncTseClient()
        try:
            sync_r = sync.search_cg(name="ソニー", limit=10)
            async_r = await async_client.search_cg(name="ソニー", limit=10)

            assert sync_r.total == async_r.total
            assert len(sync_r.items) == len(async_r.items)
        finally:
            sync.close()
            await async_client.close()

    await run_async("search_cg結果一致", _compare_cg)


# ===========================================================================
# 12. コンテキストマネージャ
# ===========================================================================
def test_context_manager():
    print("\n=== 12. コンテキストマネージャ ===")

    def _sync_cm():
        with TseClient() as client:
            r = client.search(name="トヨタ", limit=10)
            assert r.total > 0
    run("sync with文", _sync_cm)

    def _sync_explicit():
        c = TseClient()
        r = c.search(name="トヨタ", limit=10)
        assert r.total > 0
        c.close()
    run("sync 明示close", _sync_explicit)


async def test_async_context_manager():
    print("\n=== 12b. 非同期コンテキストマネージャ ===")

    async def _async_cm():
        async with AsyncTseClient() as client:
            r = await client.search(name="トヨタ", limit=10)
            assert r.total > 0
    await run_async("async with文", _async_cm)

    async def _async_explicit():
        c = AsyncTseClient()
        r = await c.search(name="トヨタ", limit=10)
        assert r.total > 0
        await c.close()
    await run_async("async 明示close", _async_explicit)


# ===========================================================================
# 13. マジックストリング非露出確認
# ===========================================================================
def test_no_magic_strings():
    print("\n=== 13. マジックストリング非露出 ===")
    import tse_hp_front
    import tse_hp_front.client as client_mod

    def _no_base_url():
        assert not hasattr(tse_hp_front, "BASE_URL")
        assert not hasattr(client_mod, "BASE_URL")
        # _付きは内部のみ
        assert hasattr(client_mod, "_BASE_URL")
    run("BASE_URL非露出", _no_base_url)

    def _no_actions():
        for name in ["JJK_INIT", "JJK_SEARCH", "JJK_DETAIL", "CGK_INIT"]:
            assert not hasattr(client_mod, name), f"{name} is exposed"
            assert hasattr(client_mod, f"_{name}"), f"_{name} missing"
    run("Action URL非露出", _no_actions)

    def _all_exports():
        for name in tse_hp_front.__all__:
            assert hasattr(tse_hp_front, name), f"{name} not in module"
    run("__all__整合性", _all_exports)


# ===========================================================================
# main
# ===========================================================================
def main():
    # ネットワーク不要テスト
    test_parsers()
    test_to_code5()
    test_helpers()
    test_enums()
    test_no_magic_strings()
    test_context_manager()

    # ネットワーク必要テスト
    with TseClient() as client:
        test_sync_search_edges(client)
        test_sync_search_detailed(client)
        test_sync_detail(client)
        test_sync_cg(client)
        test_session(client)

    # 非同期テスト
    asyncio.run(test_async())
    asyncio.run(test_async_context_manager())
    asyncio.run(test_sync_async_consistency())

    # サマリー
    print(f"\n{'='*60}")
    print(f"結果: {passed} passed, {failed} failed / {passed + failed} total")
    if errors:
        print(f"\n失敗一覧:")
        for e in errors:
            print(f"  - {e}")
    print(f"{'='*60}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
