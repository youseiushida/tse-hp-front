"""HTMLパーサー群."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from tse_hp_front.models import (
    CGInfoItem,
    CGSearchResult,
    CGSearchResultItem,
    CompanyBasicInfo,
    CompanyDetail,
    CompanySearchResult,
    DisclosureItem,
    DisclosureSection,
    FilingItem,
    FilingSection,
    SearchResultItem,
)

BASE_URL = "https://www2.jpx.co.jp"

# 適時開示情報のカテゴリ → row id prefix
_DISCLOSURE_CATEGORIES = {
    "hotei": "legal",
    "1101": "earnings",
    "1102": "material_facts",
    "1103": "compliance_plan",
    "1104": "other",
}

# 縦覧書類のカテゴリ → row id prefix
_FILING_CATEGORIES = {
    "1105": "shareholder_meeting",
    "1106": "independent_officers",
    "1107": "articles",
    "1108": "pr",
    "1109": "other",
    "1110": "esg",
}


def _text(tag: Tag | None) -> str:
    return tag.get_text(strip=True) if tag else ""


def _abs_url(path: str | None) -> str | None:
    if not path or path.startswith("javascript:"):
        return None
    if path.startswith("http"):
        return path
    return BASE_URL + path


def _val(soup: BeautifulSoup | Tag, name: str) -> str:
    """hidden input の value を取得."""
    inp = soup.find("input", {"name": name})
    return str(inp["value"]) if inp and inp.get("value") else ""


# ---------------------------------------------------------------------------
# JJK 検索結果 (JJK010030)
# ---------------------------------------------------------------------------


def parse_search_result(html: str) -> CompanySearchResult:
    """JJK010030 検索結果一覧をパース."""
    soup = BeautifulSoup(html, "lxml")

    total = _parse_total(soup)

    items: list[SearchResultItem] = []
    form = soup.find("form", {"name": "JJK010030Form"})
    if not form:
        return CompanySearchResult(total=0, items=[])

    for tr in form.find_all("tr", height="50"):
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue

        prefix = _find_prefix(tds[0], "eqMgrCd")
        if not prefix:
            continue

        stock_link = tds[7].find("a")

        items.append(
            SearchResultItem(
                code=_val(tr, f"{prefix}.eqMgrCd"),
                name=_val(tr, f"{prefix}.eqMgrNm"),
                market=_val(tr, f"{prefix}.szkbuNm"),
                industry=_val(tr, f"{prefix}.gyshDspNm"),
                fiscal_period=_val(tr, f"{prefix}.dspYuKssnKi"),
                has_notice=bool(_text(tds[5])),
                stock_price_url=_abs_url(str(stock_link["href"])) if stock_link and stock_link.get("href") else None,
            )
        )

    return CompanySearchResult(total=total, items=items)


# ---------------------------------------------------------------------------
# CGK 検索結果
# ---------------------------------------------------------------------------


def parse_cg_search_result(html: str) -> CGSearchResult:
    """CGK検索結果をパース."""
    soup = BeautifulSoup(html, "lxml")

    total = _parse_total(soup)
    detailed_total = _parse_detailed_total(soup)

    items: list[CGSearchResultItem] = []
    idx = 0
    while True:
        p = f"ccCGSelKekkLst_st[{idx}]"
        code_input = soup.find("input", {"name": f"{p}.eqMgrCd"})
        if not code_input:
            break

        parent_tr = code_input.find_parent("tr")
        tds = parent_tr.find_all("td") if parent_tr else []

        pdf_path = _val(soup, f"{p}.pdfFlePs")
        html_path = _val(soup, f"{p}.htmlFlePs")
        xbrl_path = _val(soup, f"{p}.xbrlFlePs")

        items.append(
            CGSearchResultItem(
                code=_val(soup, f"{p}.eqMgrCd"),
                name=_val(soup, f"{p}.eqMgrNm"),
                organization_type=_text(tds[2]) if len(tds) > 2 else "",
                organization_type_code=_val(soup, f"{p}.sskKiti"),
                parent_company=_text(tds[3]) if len(tds) > 3 else "",
                parent_company_code=_val(soup, f"{p}.oyaCrpUm"),
                major_shareholder_name=_val(soup, f"{p}.daiEqnsNm"),
                major_shareholder_ratio=_val(soup, f"{p}.daiEqnsEqSyuHrt"),
                directors_count=_val(soup, f"{p}.tsynz"),
                independent_directors_count=_val(soup, f"{p}.sgiTrshmrykDryiNzu"),
                viewing_date=_val(soup, f"{p}.jhUpdDay"),
                pdf_url=_abs_url(pdf_path) if pdf_path else None,
                html_url=_abs_url(html_path) if html_path else None,
                xbrl_url=_abs_url("/disc" + xbrl_path) if xbrl_path else None,
            )
        )
        idx += 1

    return CGSearchResult(total=total, detailed_total=detailed_total, items=items)


# ---------------------------------------------------------------------------
# JJK 詳細 - 基本情報タブ
# ---------------------------------------------------------------------------


def _parse_alternating_table(table: Tag) -> dict[str, str]:
    """TH行とTD行が交互に並ぶテーブルをパース."""
    data: dict[str, str] = {}
    rows = table.find_all("tr")
    i = 0
    while i < len(rows):
        ths = rows[i].find_all("th")
        if ths and i + 1 < len(rows):
            tds = rows[i + 1].find_all("td")
            for th, td in zip(ths, tds):
                key = _text(th)
                val = _text(td)
                if key:
                    data[key] = val
            i += 2
        else:
            i += 1
    return data


def _parse_basic_info(section: Tag) -> CompanyBasicInfo:
    """body_basicInformation からパース."""
    name = ""
    h3 = section.find("h3")
    if h3:
        name = h3.get_text(strip=True)

    # 株価情報URL
    stock_url: str | None = None
    for a in section.find_all("a"):
        href = str(a.get("href", ""))
        if "quote.jpx.co.jp" in href:
            stock_url = href
            break

    data: dict[str, str] = {}
    tables = section.find_all("table")
    for table in tables:
        cls_raw = table.get("class")
        cls = " ".join(cls_raw) if isinstance(cls_raw, list) else str(cls_raw or "")
        if "fontsizeS" in cls and ("margin20" in cls or "tableStyle02" in cls):
            data.update(_parse_alternating_table(table))

    def _get(key: str) -> str:
        if key in data:
            return data[key]
        for k, v in data.items():
            if k.startswith(key):
                return v
        return ""

    # その他お知らせ: 最後のテーブルの TD 値（複数セル）
    other_notices: list[str] = []
    if "その他お知らせ" in data:
        val = data["その他お知らせ"]
        if val:
            other_notices.append(val)

    return CompanyBasicInfo(
        code=_get("コード"),
        isin=_get("ISINコード"),
        market=_get("市場区分"),
        industry=_get("業種"),
        fiscal_period=_get("決算期"),
        trading_unit=_get("売買単位"),
        name=name,
        name_en=_get("英文商号"),
        transfer_agent=_get("株主名簿管理人"),
        established=_get("設立年月日"),
        headquarters=_get("本社所在地"),
        listed_exchange=_get("上場取引所"),
        investment_unit=_get("月末投資単位"),
        earnings_announcement=_get("決算発表（予定）"),
        q1_announcement=_get("第一四半期（予定）"),
        q2_announcement=_get("第二四半期（予定）"),
        q3_announcement=_get("第三四半期（予定）"),
        shareholders_meeting=_get("株主総会開催日"),
        representative_title=_get("代表者役職"),
        representative_name=_get("代表者氏名"),
        listing_date=_get("上場年月日"),
        notice_info=_get("注意情報"),
        listed_shares=_get("上場株式数"),
        shares_outstanding=_get("発行済株式数"),
        j_iriss=_get("J-IRISS"),
        margin_trading=_get("貸借銘柄"),
        credit_trading=_get("信用銘柄"),
        accounting_standards_membership=_get("財務会計基準機構"),
        going_concern=_get("継続企業"),
        controlling_shareholder=_get("支配株主"),
        other_notices=other_notices,
        stock_price_url=stock_url,
    )


# ---------------------------------------------------------------------------
# JJK 詳細 - 適時開示情報タブ
# ---------------------------------------------------------------------------


def _parse_disclosure_row(row: Tag) -> DisclosureItem:
    """開示情報の1行をパース."""
    tds = row.find_all("td")
    date = _text(tds[0]) if tds else ""

    title_div = tds[1].find("div", class_="txtLink2_InnerDiv") if len(tds) > 1 else None
    title_link = tds[1].find("a") if len(tds) > 1 else None
    title = _text(title_div) if title_div else (_text(title_link) if title_link else (_text(tds[1]) if len(tds) > 1 else ""))

    pdf_href = str(title_link["href"]) if title_link and title_link.get("href") else None
    pdf_url = _abs_url(pdf_href)

    xbrl_url: str | None = None
    xbrl_img = row.find("img", alt="XBRL")
    if xbrl_img:
        onclick = str(xbrl_img.get("onclick", ""))
        for p in onclick.split("'"):
            if p.endswith(".zip"):
                xbrl_url = _abs_url("/disc" + p)
                break

    html_urls: list[str] = []
    for td in tds[2:]:
        for a in td.find_all("a"):
            href = str(a.get("href", ""))
            if href.endswith(".htm") or href.endswith(".html"):
                url = _abs_url(href)
                if url:
                    html_urls.append(url)

    return DisclosureItem(
        date=date, title=title, pdf_url=pdf_url,
        xbrl_url=xbrl_url, html_urls=html_urls,
    )


def _parse_disclosures(section: Tag) -> DisclosureSection:
    """body_disclosure からカテゴリ分けしてパース."""
    result = DisclosureSection()
    categorized: dict[str, list[DisclosureItem]] = {v: [] for v in _DISCLOSURE_CATEGORIES.values()}

    for row in section.find_all("tr", id=True):
        row_id = str(row.get("id", ""))
        prefix = row_id.rsplit("_", 1)[0]
        category = _DISCLOSURE_CATEGORIES.get(prefix)
        if category is None:
            continue
        item = _parse_disclosure_row(row)
        categorized[category].append(item)

    result.legal = categorized["legal"]
    result.earnings = categorized["earnings"]
    result.material_facts = categorized["material_facts"]
    result.compliance_plan = categorized["compliance_plan"]
    result.other = categorized["other"]
    return result


# ---------------------------------------------------------------------------
# JJK 詳細 - 縦覧書類 / PR情報タブ
# ---------------------------------------------------------------------------


def _parse_filing_row(row: Tag) -> FilingItem:
    """縦覧書類の1行をパース."""
    tds = row.find_all("td")
    date = _text(tds[0]) if tds else ""
    link = tds[1].find("a") if len(tds) > 1 else None
    title = _text(link) if link else (_text(tds[1]) if len(tds) > 1 else "")
    pdf_href = str(link["href"]) if link and link.get("href") else None
    return FilingItem(date=date, title=title, pdf_url=_abs_url(pdf_href))


def _parse_filings(section: Tag) -> FilingSection:
    """body_filing からカテゴリ分けしてパース."""
    result = FilingSection()
    categorized: dict[str, list[FilingItem]] = {v: [] for v in _FILING_CATEGORIES.values()}

    for row in section.find_all("tr", id=True):
        row_id = str(row.get("id", ""))
        prefix = row_id.rsplit("_", 1)[0]
        category = _FILING_CATEGORIES.get(prefix)
        if category is None:
            continue
        item = _parse_filing_row(row)
        categorized[category].append(item)

    result.shareholder_meeting = categorized["shareholder_meeting"]
    result.independent_officers = categorized["independent_officers"]
    result.articles = categorized["articles"]
    result.other = categorized["other"]
    result.esg = categorized["esg"]
    result.pr = categorized["pr"]
    return result


# ---------------------------------------------------------------------------
# JJK 詳細 - CG情報タブ
# ---------------------------------------------------------------------------


def _parse_cg_info(section: Tag) -> list[CGInfoItem]:
    """body_CorporateGovernance からパース."""
    items: list[CGInfoItem] = []

    # CG情報テーブル: class=fontsizeS の中の data rows (TH行を除く)
    for table in section.find_all("table"):
        cls_raw = table.get("class")
        cls = " ".join(cls_raw) if isinstance(cls_raw, list) else str(cls_raw or "")
        if "fontsizeS" not in cls:
            continue

        rows = table.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 8:
                continue

            # PDF/HTML links
            pdf_url: str | None = None
            html_url: str | None = None
            xbrl_url: str | None = None
            for a in row.find_all("a"):
                href = str(a.get("href", ""))
                if href.endswith(".pdf"):
                    pdf_url = _abs_url(href)
                elif href.endswith(".html"):
                    html_url = _abs_url(href)
            for img in row.find_all("img", alt="XBRL"):
                onclick = str(img.get("onclick", ""))
                for p in onclick.split("'"):
                    if p.endswith(".zip"):
                        xbrl_url = _abs_url("/disc" + p)
                        break

            items.append(
                CGInfoItem(
                    organization_type=_text(tds[0]),
                    parent_company=_text(tds[1]),
                    foreign_ownership_ratio=_text(tds[2]),
                    major_shareholder_name=_text(tds[3]),
                    major_shareholder_ratio=_text(tds[4]),
                    directors=_text(tds[5]),
                    auditors=_text(tds[6]),
                    viewing_date=_text(tds[7]),
                    pdf_url=pdf_url,
                    html_url=html_url,
                    xbrl_url=xbrl_url,
                )
            )

    return items


# ---------------------------------------------------------------------------
# JJK 詳細ページ統合
# ---------------------------------------------------------------------------


_EMPTY_BASIC = CompanyBasicInfo(
    code="", isin="", market="", industry="", fiscal_period="", trading_unit="",
    name="", name_en="", transfer_agent="", established="", headquarters="",
    listed_exchange="", investment_unit="", earnings_announcement="",
    q1_announcement="", q2_announcement="", q3_announcement="",
    shareholders_meeting="", representative_title="", representative_name="",
    listing_date="", notice_info="", listed_shares="", shares_outstanding="",
    j_iriss="", margin_trading="", credit_trading="",
    accounting_standards_membership="", going_concern="",
    controlling_shareholder="",
)


def parse_detail(html: str) -> CompanyDetail:
    """JJK010040 詳細ページをパース."""
    soup = BeautifulSoup(html, "lxml")

    basic_section = soup.find("div", id="body_basicInformation")
    disclosure_section = soup.find("div", id="body_disclosure")
    filing_section = soup.find("div", id="body_filing")
    cg_section = soup.find("div", id="body_CorporateGovernance")

    basic = _parse_basic_info(basic_section) if basic_section else _EMPTY_BASIC
    disclosures = _parse_disclosures(disclosure_section) if disclosure_section else DisclosureSection()
    filings = _parse_filings(filing_section) if filing_section else FilingSection()
    cg_info = _parse_cg_info(cg_section) if cg_section else []

    return CompanyDetail(
        basic=basic, disclosures=disclosures,
        filings=filings, cg_info=cg_info,
    )


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _parse_total(soup: BeautifulSoup) -> int:
    paging = soup.select_one("div.pagingmenu div.left strong")
    if paging:
        text = paging.get_text()
        if "／" in text and "件中" in text:
            return int(text.split("／")[1].replace("件中", "").strip())
    return 0


def _parse_detailed_total(soup: BeautifulSoup) -> int:
    for tag in soup.find_all(string=re.compile("詳細条件該当銘柄数")):
        m = re.search(r"詳細条件該当銘柄数[：:]\s*(\d+)", tag)
        if m:
            return int(m.group(1))
    return 0


def _find_prefix(td: Tag, suffix: str) -> str | None:
    inp = td.find("input", {"name": re.compile(rf".*\.{suffix}$")})
    if inp:
        name = str(inp["name"])
        return name.rsplit(".", 1)[0]
    return None
