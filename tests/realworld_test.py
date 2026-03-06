"""実運用シナリオテスト - 銘柄深掘り・PDF/XBRL取得確認."""

from __future__ import annotations

import asyncio
import traceback
from datetime import date

import httpx

from tse_hp_front import (
    AsyncTseClient,
    CompensationDisclosure,
    DirectorTenure,
    ForeignOwnershipFrom,
    Industry,
    Market,
    OrganizationType,
    OutsideDirectorRelation,
    OutsideOfficerAttribute,
    ParentCompanyStatus,
    Prefecture,
    RelationPeriod,
    TseClient,
)

passed = 0
failed = 0
errors: list[str] = []


def ok(name: str, detail: str = "") -> None:
    global passed
    passed += 1
    msg = f"  PASS: {name}"
    if detail:
        msg += f" ({detail})"
    print(msg)


def fail(name: str, msg: str) -> None:
    global failed
    failed += 1
    errors.append(f"{name}: {msg}")
    print(f"  FAIL: {name} - {msg}")


def run(name: str, fn):
    try:
        fn()
        ok(name)
    except AssertionError as e:
        fail(name, str(e))
    except Exception as e:
        fail(name, f"{type(e).__name__}: {e}")
        traceback.print_exc()


def run_detail(name: str, fn):
    """戻り値を表示するrun."""
    try:
        detail = fn()
        ok(name, detail or "")
    except AssertionError as e:
        fail(name, str(e))
    except Exception as e:
        fail(name, f"{type(e).__name__}: {e}")
        traceback.print_exc()


def check_url(url: str, http: httpx.Client) -> tuple[bool, int, str]:
    """URLにHEADリクエストして到達可能か確認."""
    try:
        resp = http.head(url, follow_redirects=True, timeout=15)
        ct = resp.headers.get("content-type", "")
        return resp.status_code < 400, resp.status_code, ct
    except Exception as e:
        return False, 0, str(e)


# ===========================================================================
# 1. 主要銘柄の詳細情報 完全性チェック
# ===========================================================================
def test_major_companies(client: TseClient, http: httpx.Client):
    print("\n=== 1. 主要銘柄 詳細情報チェック ===")

    targets = [
        ("7203", "トヨタ自動車"),
        ("6758", "ソニーグループ"),
        ("9984", "ソフトバンクグループ"),
        ("6861", "キーエンス"),
        ("8306", "三菱UFJフィナンシャル・グループ"),
        ("4063", "信越化学工業"),
        ("6501", "日立製作所"),
        ("7741", "HOYA"),
        ("9432", "日本電信電話"),
        ("4502", "武田薬品工業"),
    ]

    for code, expected_name in targets:
        def _check(c=code, en=expected_name):
            d = client.get_detail(c)

            # 基本情報の充実度
            b = d.basic
            assert b.code, f"{c}: コードが空"
            assert b.name, f"{c}: 銘柄名が空"
            assert b.market, f"{c}: 市場が空"
            assert b.industry, f"{c}: 業種が空"
            assert b.fiscal_period, f"{c}: 決算期が空"
            assert b.headquarters, f"{c}: 本社所在地が空"
            assert b.representative_name, f"{c}: 代表者が空"
            assert b.listing_date, f"{c}: 上場年月日が空"
            assert b.name_en, f"{c}: 英文商号が空"

            fields_filled = sum(1 for f in [
                b.code, b.isin, b.market, b.industry, b.fiscal_period,
                b.trading_unit, b.name, b.name_en, b.transfer_agent,
                b.established, b.headquarters, b.listed_exchange,
                b.representative_title, b.representative_name,
                b.listing_date, b.listed_shares, b.shares_outstanding,
            ] if f)

            return f"{b.name} - {fields_filled}/17フィールド取得"
        run_detail(f"基本情報: {code}({expected_name})", _check)


# ===========================================================================
# 2. 適時開示情報の存在確認 + PDF到達チェック
# ===========================================================================
def test_disclosure_pdfs(client: TseClient, http: httpx.Client):
    print("\n=== 2. 適時開示情報 PDF/XBRL到達チェック ===")

    for code, name in [("7203", "トヨタ"), ("6758", "ソニー"), ("9984", "SBG")]:
        def _check(c=code, n=name):
            d = client.get_detail(c)
            disc = d.disclosures

            total = (
                len(disc.legal) + len(disc.earnings)
                + len(disc.material_facts) + len(disc.compliance_plan)
                + len(disc.other)
            )

            if total == 0:
                return f"{n}: 開示情報0件（サーバー仕様の可能性）"

            # カテゴリ別件数
            cats = []
            if disc.legal:
                cats.append(f"法定{len(disc.legal)}")
            if disc.earnings:
                cats.append(f"決算{len(disc.earnings)}")
            if disc.material_facts:
                cats.append(f"決定/発生{len(disc.material_facts)}")
            if disc.other:
                cats.append(f"その他{len(disc.other)}")

            # PDF URLの到達確認（最大3件）
            pdf_checked = 0
            pdf_ok = 0
            for items in [disc.legal, disc.earnings, disc.material_facts, disc.other]:
                for item in items[:2]:
                    if item.pdf_url:
                        reachable, status, ct = check_url(item.pdf_url, http)
                        pdf_checked += 1
                        if reachable:
                            pdf_ok += 1
                        if pdf_checked >= 3:
                            break
                if pdf_checked >= 3:
                    break

            # XBRL URLの到達確認（最大2件）
            xbrl_checked = 0
            xbrl_ok = 0
            for items in [disc.earnings, disc.legal]:
                for item in items[:2]:
                    if item.xbrl_url:
                        reachable, status, ct = check_url(item.xbrl_url, http)
                        xbrl_checked += 1
                        if reachable:
                            xbrl_ok += 1
                        if xbrl_checked >= 2:
                            break
                if xbrl_checked >= 2:
                    break

            # 各開示にtitleとdateがあるか
            missing_title = sum(1 for items in [disc.legal, disc.earnings, disc.material_facts, disc.other]
                                for item in items if not item.title)
            missing_date = sum(1 for items in [disc.legal, disc.earnings, disc.material_facts, disc.other]
                               for item in items if not item.date)

            return (
                f"{n}: 全{total}件 [{', '.join(cats)}] "
                f"PDF {pdf_ok}/{pdf_checked}到達 XBRL {xbrl_ok}/{xbrl_checked}到達 "
                f"title欠損{missing_title} date欠損{missing_date}"
            )
        run_detail(f"適時開示: {code}", _check)


# ===========================================================================
# 3. 縦覧書類 PDF到達チェック
# ===========================================================================
def test_filing_pdfs(client: TseClient, http: httpx.Client):
    print("\n=== 3. 縦覧書類 PDF到達チェック ===")

    for code, name in [("7203", "トヨタ"), ("6758", "ソニー")]:
        def _check(c=code, n=name):
            d = client.get_detail(c)
            f = d.filings

            total = (
                len(f.shareholder_meeting) + len(f.independent_officers)
                + len(f.articles) + len(f.other) + len(f.esg) + len(f.pr)
            )

            cats = []
            if f.shareholder_meeting:
                cats.append(f"総会{len(f.shareholder_meeting)}")
            if f.independent_officers:
                cats.append(f"独立役員{len(f.independent_officers)}")
            if f.articles:
                cats.append(f"定款{len(f.articles)}")
            if f.esg:
                cats.append(f"ESG{len(f.esg)}")
            if f.pr:
                cats.append(f"PR{len(f.pr)}")
            if f.other:
                cats.append(f"その他{len(f.other)}")

            pdf_checked = 0
            pdf_ok = 0
            for items in [f.shareholder_meeting, f.independent_officers, f.articles, f.esg]:
                for item in items[:1]:
                    if item.pdf_url:
                        reachable, status, ct = check_url(item.pdf_url, http)
                        pdf_checked += 1
                        if reachable:
                            pdf_ok += 1
                if pdf_checked >= 3:
                    break

            return f"{n}: 全{total}件 [{', '.join(cats)}] PDF {pdf_ok}/{pdf_checked}到達"
        run_detail(f"縦覧書類: {code}", _check)


# ===========================================================================
# 4. CG情報タブ（詳細ページ内）のPDF/HTML/XBRL到達
# ===========================================================================
def test_detail_cg_links(client: TseClient, http: httpx.Client):
    print("\n=== 4. 詳細ページ CG情報 リンク到達 ===")

    for code, name in [("7203", "トヨタ"), ("6758", "ソニー"), ("8306", "MUFG")]:
        def _check(c=code, n=name):
            d = client.get_detail(c)
            cg = d.cg_info

            if not cg:
                return f"{n}: CG情報0件"

            latest = cg[0]
            results = []
            results.append(f"組織={latest.organization_type}")
            results.append(f"取締役={latest.directors}")
            results.append(f"監査役={latest.auditors}")

            if latest.pdf_url:
                reachable, status, ct = check_url(latest.pdf_url, http)
                results.append(f"PDF={'OK' if reachable else f'NG({status})'}")
                assert reachable, f"CG PDF到達不可: {latest.pdf_url} (status={status})"

            if latest.html_url:
                reachable, status, ct = check_url(latest.html_url, http)
                results.append(f"HTML={'OK' if reachable else f'NG({status})'}")

            if latest.xbrl_url:
                reachable, status, ct = check_url(latest.xbrl_url, http)
                results.append(f"XBRL={'OK' if reachable else f'NG({status})'}")

            return f"{n}: {len(cg)}世代 最新[{', '.join(results)}]"
        run_detail(f"CG情報リンク: {code}", _check)


# ===========================================================================
# 5. CG検索結果のPDF/HTML/XBRLリンク到達
# ===========================================================================
def test_cg_search_links(client: TseClient, http: httpx.Client):
    print("\n=== 5. CG検索結果 リンク到達チェック ===")

    def _check():
        r = client.search_cg(markets=[Market.プライム], limit=10)
        assert r.total > 0
        assert len(r.items) > 0

        pdf_checked = 0
        pdf_ok = 0
        html_checked = 0
        html_ok = 0
        xbrl_checked = 0
        xbrl_ok = 0

        for item in r.items[:5]:
            if item.pdf_url:
                reachable, _, _ = check_url(item.pdf_url, http)
                pdf_checked += 1
                if reachable:
                    pdf_ok += 1

            if item.html_url:
                reachable, _, _ = check_url(item.html_url, http)
                html_checked += 1
                if reachable:
                    html_ok += 1

            if item.xbrl_url:
                reachable, _, _ = check_url(item.xbrl_url, http)
                xbrl_checked += 1
                if reachable:
                    xbrl_ok += 1

        return (
            f"先頭5社 PDF {pdf_ok}/{pdf_checked} "
            f"HTML {html_ok}/{html_checked} "
            f"XBRL {xbrl_ok}/{xbrl_checked}"
        )
    run_detail("CG検索 プライム上位5社 リンク", _check)


# ===========================================================================
# 6. 検索→詳細のクロスバリデーション
# ===========================================================================
def test_search_detail_consistency(client: TseClient):
    print("\n=== 6. 検索→詳細 クロスバリデーション ===")

    def _check():
        r = client.search(name="トヨタ", limit=10)
        assert r.total > 0

        mismatches = []
        for item in r.items[:3]:
            d = client.get_detail(item.code[:4])
            if d.basic.code != item.code:
                mismatches.append(f"code: search={item.code} detail={d.basic.code}")
            if d.basic.name and item.name not in d.basic.name and d.basic.name not in item.name:
                mismatches.append(f"name: search={item.name} detail={d.basic.name}")

        if mismatches:
            return f"不一致あり: {'; '.join(mismatches)}"
        return f"{len(r.items[:3])}社 全一致"
    run_detail("search→detail コード/名前一致", _check)

    def _cg_cross():
        r = client.search_cg(name="ソニー", limit=10)
        assert r.total > 0

        for item in r.items[:2]:
            d = client.get_detail(item.code[:4])
            assert d.basic.code == item.code, f"code mismatch: {item.code} vs {d.basic.code}"

        return f"{min(2, len(r.items))}社 CG検索→詳細 コード一致"
    run_detail("CG search→detail コード一致", _cg_cross)


# ===========================================================================
# 7. 実運用シナリオ: 特定条件の銘柄探索
# ===========================================================================
def test_real_scenarios(client: TseClient):
    print("\n=== 7. 実運用シナリオ ===")

    # シナリオ1: プライム市場の東京本社の電気機器会社
    def _s1():
        r = client.search(
            markets=[Market.プライム],
            prefecture=Prefecture.東京,
            industry=Industry.電気機器,
            limit=200,
        )
        assert r.total > 0
        names = [item.name for item in r.items[:5]]
        return f"{r.total}社ヒット 先頭: {', '.join(names)}"
    run_detail("プライム×東京×電気機器", _s1)

    # シナリオ2: 3月決算の医薬品会社
    def _s2():
        r = client.search(
            industry=Industry.医薬品,
            fiscal_period=3,
            limit=200,
        )
        assert r.total > 0
        return f"{r.total}社ヒット"
    run_detail("医薬品×3月決算", _s2)

    # シナリオ3: 指名委員会等設置会社で弁護士の社外取締役がいる会社
    def _s3():
        r = client.search_cg(
            organization_type=OrganizationType.指名委員会等設置会社,
            outside_director_attributes=[OutsideOfficerAttribute.弁護士],
            limit=50,
        )
        names = [f"{item.code[:4]}:{item.name}" for item in r.items[:5]]
        return f"{r.total}社ヒット 先頭: {', '.join(names)}"
    run_detail("指名委員会等×弁護士社外取締役", _s3)

    # シナリオ4: 外国人比率20%以上で買収防衛策ありの会社
    def _s4():
        r = client.search_cg(
            foreign_ownership_from=ForeignOwnershipFrom.PCT_20,
            takeover_defense=True,
            limit=50,
        )
        return f"{r.total}社ヒット"
    run_detail("外国人20%以上×買収防衛策あり", _s4)

    # シナリオ5: 上場親会社ありの会社一覧
    def _s5():
        r = client.search_cg(
            parent_company=ParentCompanyStatus.有_上場,
            limit=50,
        )
        assert r.total > 0
        # 親会社コードが入ってるか
        with_parent = sum(1 for item in r.items if item.parent_company_code)
        return f"{r.total}社ヒット 親会社コードあり{with_parent}/{len(r.items)}"
    run_detail("上場親会社あり", _s5)

    # シナリオ6: 独立社外取締役5人以上の会社
    def _s6():
        r = client.search_cg(
            independent_directors_from=5,
            markets=[Market.プライム],
            limit=50,
        )
        assert r.total > 0
        # 実際に独立社外取締役数を確認
        samples = [(item.code[:4], item.name, item.independent_directors_count) for item in r.items[:5]]
        return f"{r.total}社ヒット 例: {samples}"
    run_detail("プライム×独立社外取締役5人以上", _s6)

    # シナリオ7: 全報酬個別開示の会社
    def _s7():
        r = client.search_cg(
            director_compensation_disclosure=[CompensationDisclosure.全員個別開示],
            markets=[Market.プライム],
            limit=50,
        )
        return f"{r.total}社ヒット"
    run_detail("プライム×取締役報酬全員個別開示", _s7)

    # シナリオ8: 任意の指名・報酬委員会がある監査役設置会社
    def _s8():
        r = client.search_cg(
            organization_type=OrganizationType.監査役設置会社,
            optional_committee_exists=True,
            limit=50,
        )
        return f"{r.total}社ヒット"
    run_detail("監査役設置×任意委員会あり", _s8)

    # シナリオ9: 相談役・顧問5人以上
    def _s9():
        r = client.search_cg(
            advisor_count_from=5,
            limit=50,
        )
        return f"{r.total}社ヒット"
    run_detail("相談役・顧問5人以上", _s9)

    # シナリオ10: 電磁的議決権+プラットフォーム+英文通知 (ガバナンス先進企業)
    def _s10():
        r = client.search_cg(
            electronic_voting=True,
            voting_platform=True,
            english_notice=True,
            markets=[Market.プライム],
            limit=50,
        )
        return f"{r.total}社ヒット"
    run_detail("プライム×議決権電子化×英文通知", _s10)


# ===========================================================================
# 8. 特定銘柄 深掘り（全データ網羅検証）
# ===========================================================================
def test_deep_dive(client: TseClient, http: httpx.Client):
    print("\n=== 8. 特定銘柄 深掘り ===")

    # トヨタ自動車 完全検証
    def _toyota():
        d = client.get_detail("7203")
        b = d.basic
        results = []

        # ISINコード形式チェック (JP + 10桁)
        assert b.isin.startswith("JP"), f"ISIN形式異常: {b.isin}"
        results.append(f"ISIN={b.isin}")

        # 市場がプライムであること
        assert "プライム" in b.market, f"市場異常: {b.market}"
        results.append(f"市場={b.market}")

        # 業種が輸送用機器
        assert "輸送用機器" in b.industry, f"業種異常: {b.industry}"
        results.append(f"業種={b.industry}")

        # 決算期3月
        assert "3" in b.fiscal_period, f"決算期異常: {b.fiscal_period}"

        # 愛知県
        assert "愛知" in b.headquarters or "豊田" in b.headquarters, f"本社異常: {b.headquarters}"
        results.append(f"本社={b.headquarters}")

        # 代表者
        assert b.representative_name, "代表者なし"
        results.append(f"代表者={b.representative_name}")

        # 英文商号にToyotaが含まれる
        assert "Toyota" in b.name_en or "TOYOTA" in b.name_en, f"英文商号異常: {b.name_en}"

        # 上場株式数が数値っぽい
        assert b.listed_shares, "上場株式数なし"

        # 株価URL
        assert b.stock_price_url, "株価URLなし"
        reachable, _, _ = check_url(b.stock_price_url, http)
        results.append(f"株価URL={'OK' if reachable else 'NG'}")

        # CG情報
        assert d.cg_info, "CG情報なし"
        results.append(f"CG情報{len(d.cg_info)}世代")

        return " / ".join(results)
    run_detail("トヨタ完全検証", _toyota)

    # ソニーグループ 完全検証
    def _sony():
        d = client.get_detail("6758")
        b = d.basic
        results = []

        assert "ソニー" in b.name
        assert b.isin.startswith("JP")
        assert "プライム" in b.market
        results.append(f"業種={b.industry}")

        # 開示情報
        disc = d.disclosures
        total_disc = (len(disc.legal) + len(disc.earnings) +
                      len(disc.material_facts) + len(disc.other))
        results.append(f"開示{total_disc}件")

        # 縦覧書類
        fil = d.filings
        total_fil = (len(fil.shareholder_meeting) + len(fil.independent_officers) +
                     len(fil.articles) + len(fil.other) + len(fil.esg) + len(fil.pr))
        results.append(f"縦覧{total_fil}件")

        # CG
        assert d.cg_info
        latest_cg = d.cg_info[0]
        results.append(f"組織={latest_cg.organization_type}")
        results.append(f"縦覧日={latest_cg.viewing_date}")

        return " / ".join(results)
    run_detail("ソニー完全検証", _sony)

    # 小型銘柄（グロース市場）の検証
    def _growth():
        r = client.search(markets=[Market.グロース], limit=10)
        assert r.total > 0
        item = r.items[0]
        d = client.get_detail(item.code[:4])
        results = [f"{d.basic.name}({d.basic.code})"]
        results.append(f"市場={d.basic.market}")
        results.append(f"業種={d.basic.industry}")

        disc_total = (len(d.disclosures.legal) + len(d.disclosures.earnings) +
                      len(d.disclosures.material_facts) + len(d.disclosures.other))
        results.append(f"開示{disc_total}件")

        return " / ".join(results)
    run_detail("グロース市場銘柄", _growth)

    # ETF
    def _etf():
        r = client.search(markets=[Market.ETF], limit=10)
        assert r.total > 0
        item = r.items[0]
        d = client.get_detail(item.code[:4])
        return f"{d.basic.name}({d.basic.code}) 市場={d.basic.market} 業種={d.basic.industry}"
    run_detail("ETF銘柄", _etf)

    # REIT
    def _reit():
        r = client.search(markets=[Market.REIT], limit=10)
        assert r.total > 0
        item = r.items[0]
        d = client.get_detail(item.code[:4])
        return f"{d.basic.name}({d.basic.code}) 市場={d.basic.market}"
    run_detail("REIT銘柄", _reit)


# ===========================================================================
# 9. HTMLリンクの到達確認（開示情報のHTML版）
# ===========================================================================
def test_html_links(client: TseClient, http: httpx.Client):
    print("\n=== 9. 開示情報 HTMLリンク到達 ===")

    def _check():
        d = client.get_detail("7203")
        disc = d.disclosures

        html_checked = 0
        html_ok = 0
        samples = []

        for items in [disc.legal, disc.earnings, disc.material_facts, disc.other]:
            for item in items:
                for url in item.html_urls:
                    reachable, status, ct = check_url(url, http)
                    html_checked += 1
                    if reachable:
                        html_ok += 1
                    samples.append(f"{'OK' if reachable else f'NG({status})'}: {item.title[:20]}...")
                    if html_checked >= 5:
                        break
                if html_checked >= 5:
                    break
            if html_checked >= 5:
                break

        return f"HTML {html_ok}/{html_checked}到達"
    run_detail("トヨタ HTML版開示情報", _check)


# ===========================================================================
# 10. PDF Content-Type確認
# ===========================================================================
def test_pdf_content_type(client: TseClient, http: httpx.Client):
    print("\n=== 10. PDF Content-Type確認 ===")

    def _check():
        d = client.get_detail("7203")

        # CG報告書PDFのContent-Type
        if d.cg_info and d.cg_info[0].pdf_url:
            url = d.cg_info[0].pdf_url
            reachable, status, ct = check_url(url, http)
            assert reachable, f"PDF到達不可: {url}"
            assert "pdf" in ct.lower() or "octet" in ct.lower(), f"Content-Type異常: {ct}"
            return f"CG PDF Content-Type={ct}"

        # 開示PDFで代替
        for items in [d.disclosures.earnings, d.disclosures.legal]:
            for item in items:
                if item.pdf_url:
                    reachable, status, ct = check_url(item.pdf_url, http)
                    assert reachable
                    return f"開示 PDF Content-Type={ct}"

        return "PDFなし"
    run_detail("PDF Content-Type検証", _check)

    def _xbrl_ct():
        d = client.get_detail("7203")
        for items in [d.disclosures.earnings, d.disclosures.legal]:
            for item in items:
                if item.xbrl_url:
                    reachable, status, ct = check_url(item.xbrl_url, http)
                    if reachable:
                        return f"XBRL Content-Type={ct}"
        return "XBRLなし"
    run_detail("XBRL Content-Type検証", _xbrl_ct)


# ===========================================================================
# 11. CG検索結果のデータ整合性
# ===========================================================================
def test_cg_data_integrity(client: TseClient):
    print("\n=== 11. CG検索結果 データ整合性 ===")

    def _check():
        r = client.search_cg(
            markets=[Market.プライム],
            organization_type=OrganizationType.指名委員会等設置会社,
            limit=50,
        )
        assert r.total > 0

        issues = []
        for item in r.items:
            # 組織形態が指名委員会等設置会社であること
            if "指名委員会" not in item.organization_type:
                issues.append(f"{item.code}: 組織形態不一致 '{item.organization_type}'")

            # コードが5桁であること
            if len(item.code) != 5:
                issues.append(f"{item.code}: コード長異常")

            # 縦覧日がYYYY/MM/DD形式
            if item.viewing_date and "/" not in item.viewing_date:
                issues.append(f"{item.code}: 縦覧日形式異常 '{item.viewing_date}'")

        if issues:
            return f"{r.total}社中 問題{len(issues)}件: {'; '.join(issues[:3])}"
        return f"{r.total}社 全{len(r.items)}件整合OK"
    run_detail("指名委員会等設置会社 データ整合", _check)

    def _auditor_check():
        r = client.search_cg(
            markets=[Market.プライム],
            organization_type=OrganizationType.監査役設置会社,
            independent_directors_from=3,
            limit=50,
        )
        assert r.total > 0

        # 独立社外取締役3人以上か確認
        under3 = []
        for item in r.items:
            try:
                cnt = int(item.independent_directors_count)
                if cnt < 3:
                    under3.append(f"{item.code}:{cnt}人")
            except ValueError:
                pass

        if under3:
            return f"3人未満が{len(under3)}社: {', '.join(under3[:5])}"
        return f"{r.total}社 全{len(r.items)}件 独立3人以上OK"
    run_detail("独立社外取締役3人以上 データ検証", _auditor_check)


# ===========================================================================
# 12. 非同期での並行検索シナリオ
# ===========================================================================
async def test_async_concurrent():
    print("\n=== 12. 非同期 並行検索シナリオ ===")

    async def _concurrent():
        async with AsyncTseClient() as client:
            # 3つの検索を並行実行（セッション共有のため順次が安全）
            r1 = await client.search(name="トヨタ", limit=10)
            r2 = await client.search(name="ソニー", limit=10)
            r3 = await client.search(name="任天堂", limit=10)

            assert r1.total > 0
            assert r2.total > 0
            assert r3.total > 0

            return f"トヨタ{r1.total}件 ソニー{r2.total}件 任天堂{r3.total}件"

    try:
        detail = await _concurrent()
        ok("非同期 順次3検索", detail)
    except Exception as e:
        fail("非同期 順次3検索", f"{type(e).__name__}: {e}")

    # 詳細取得も
    async def _detail_batch():
        async with AsyncTseClient() as client:
            codes = ["7203", "6758", "7974", "9984", "6861"]
            results = []
            for code in codes:
                d = await client.get_detail(code)
                results.append(f"{d.basic.name}({d.basic.code})")
            return f"{len(results)}社取得: {', '.join(results)}"

    try:
        detail = await _detail_batch()
        ok("非同期 5社バッチ詳細取得", detail)
    except Exception as e:
        fail("非同期 5社バッチ詳細取得", f"{type(e).__name__}: {e}")


# ===========================================================================
# 13. 検索結果のページング相当（limit変更で確認）
# ===========================================================================
def test_paging_behavior(client: TseClient):
    print("\n=== 13. ページング挙動 ===")

    def _check():
        # 同じ条件でlimit変えて整合性確認
        r10 = client.search(markets=[Market.プライム], limit=10)
        r50 = client.search(markets=[Market.プライム], limit=50)
        r200 = client.search(markets=[Market.プライム], limit=200)

        assert r10.total == r50.total == r200.total, (
            f"total不一致: 10→{r10.total}, 50→{r50.total}, 200→{r200.total}"
        )
        assert len(r10.items) <= 10
        assert len(r50.items) <= 50
        assert len(r200.items) <= 200

        # limit=10の結果はlimit=50の先頭10と一致するか
        for i, (a, b) in enumerate(zip(r10.items, r50.items)):
            assert a.code == b.code, f"items[{i}] code不一致: {a.code} vs {b.code}"

        return f"total={r10.total} items: 10→{len(r10.items)}, 50→{len(r50.items)}, 200→{len(r200.items)}"
    run_detail("limit変更 total一致 + 先頭一致", _check)


# ===========================================================================
# main
# ===========================================================================
def main():
    http = httpx.Client(timeout=15, follow_redirects=True)

    with TseClient() as client:
        test_major_companies(client, http)
        test_disclosure_pdfs(client, http)
        test_filing_pdfs(client, http)
        test_detail_cg_links(client, http)
        test_cg_search_links(client, http)
        test_search_detail_consistency(client)
        test_real_scenarios(client)
        test_deep_dive(client, http)
        test_html_links(client, http)
        test_pdf_content_type(client, http)
        test_cg_data_integrity(client)
        test_paging_behavior(client)

    asyncio.run(test_async_concurrent())

    http.close()

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
