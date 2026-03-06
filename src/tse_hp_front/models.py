"""東証検索サービスのデータモデル."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# 共通 Enum（JJK / CGK 共用）
# ---------------------------------------------------------------------------


class Market(str, Enum):
    """市場区分."""

    プライム = "011"
    スタンダード = "012"
    グロース = "013"
    PRO_MARKET = "008"
    """TOKYO PRO Market"""
    外国株プライム = "111"
    外国株スタンダード = "112"
    外国株グロース = "113"
    ETF = "ETF"
    ETN = "ETN"
    REIT = "RET"
    """不動産投資信託"""
    インフラファンド = "IFD"
    その他 = "999"


class Prefecture(str, Enum):
    """本社所在地（都道府県）."""

    北海道 = "01"
    青森 = "02"
    岩手 = "03"
    宮城 = "04"
    秋田 = "05"
    山形 = "06"
    福島 = "07"
    茨城 = "08"
    栃木 = "09"
    群馬 = "10"
    埼玉 = "11"
    千葉 = "12"
    東京 = "13"
    神奈川 = "14"
    新潟 = "15"
    富山 = "16"
    石川 = "17"
    福井 = "18"
    山梨 = "19"
    長野 = "20"
    岐阜 = "21"
    静岡 = "22"
    愛知 = "23"
    三重 = "24"
    滋賀 = "25"
    京都 = "26"
    大阪 = "27"
    兵庫 = "28"
    奈良 = "29"
    和歌山 = "30"
    鳥取 = "31"
    島根 = "32"
    岡山 = "33"
    広島 = "34"
    山口 = "35"
    徳島 = "36"
    香川 = "37"
    愛媛 = "38"
    高知 = "39"
    福岡 = "40"
    佐賀 = "41"
    長崎 = "42"
    熊本 = "43"
    大分 = "44"
    宮崎 = "45"
    鹿児島 = "46"
    沖縄 = "47"


class Industry(str, Enum):
    """業種分類."""

    水産_農林業 = "0050"
    鉱業 = "1050"
    建設業 = "2050"
    食料品 = "3050"
    繊維製品 = "3100"
    パルプ_紙 = "3150"
    化学 = "3200"
    医薬品 = "3250"
    石油_石炭製品 = "3300"
    ゴム製品 = "3350"
    ガラス_土石製品 = "3400"
    鉄鋼 = "3450"
    非鉄金属 = "3500"
    金属製品 = "3550"
    機械 = "3600"
    電気機器 = "3650"
    輸送用機器 = "3700"
    精密機器 = "3750"
    その他製品 = "3800"
    電気_ガス業 = "4050"
    陸運業 = "5050"
    海運業 = "5100"
    空運業 = "5150"
    倉庫_運輸関連業 = "5200"
    情報_通信業 = "5250"
    卸売業 = "6050"
    小売業 = "6100"
    銀行業 = "7050"
    証券_商品先物取引業 = "7100"
    保険業 = "7150"
    その他金融業 = "7200"
    不動産業 = "8050"
    サービス業 = "9050"
    その他 = "9999"


# ---------------------------------------------------------------------------
# JJK 検索条件用 Enum
# ---------------------------------------------------------------------------


class AnnouncementType(str, Enum):
    """決算発表予定日の種別."""

    決算 = "kssn"
    第一四半期 = "diyhk"
    第二四半期 = "mid"
    第三四半期 = "dsyhk"


# ---------------------------------------------------------------------------
# CGK 検索条件用 Enum
# ---------------------------------------------------------------------------


class OrganizationType(str, Enum):
    """組織形態."""

    監査役設置会社 = "1"
    指名委員会等設置会社 = "2"
    監査等委員会設置会社 = "3"


class ForeignOwnershipFrom(str, Enum):
    """外国人株式所有比率 下限."""

    PCT_0 = "1"
    """0%以上"""
    PCT_10 = "2"
    """10%以上"""
    PCT_20 = "3"
    """20%以上"""
    PCT_30 = "4"
    """30%以上"""


class ForeignOwnershipTo(str, Enum):
    """外国人株式所有比率 上限."""

    PCT_10 = "1"
    """10%未満"""
    PCT_20 = "2"
    """20%未満"""
    PCT_30 = "3"
    """30%未満"""


class ParentCompanyStatus(str, Enum):
    """親会社有無."""

    有 = "3"
    有_上場 = "1"
    有_非上場 = "2"
    無 = "0"


class DirectorTenure(str, Enum):
    """定款上の取締役任期."""

    一年 = "1"
    二年 = "2"


class RelationPeriod(str, Enum):
    """社外役員の関係 期間."""

    本人現在 = "01"
    """本人（現在・最近）"""
    本人過去 = "02"
    """本人（過去）"""
    近親者現在 = "03"
    """近親者（現在・最近）"""
    近親者過去 = "04"
    """近親者（過去）"""


class OutsideOfficerAttribute(str, Enum):
    """社外取締役/社外監査役属性."""

    他会社出身 = "1"
    弁護士 = "2"
    公認会計士 = "3"
    税理士 = "4"
    学者 = "5"
    その他 = "6"


class OutsideDirectorRelation(str, Enum):
    """社外取締役の関係 (a-k)."""

    A = "1"
    """上場会社又はその子会社の業務執行者"""
    B = "2"
    """上場会社の親会社の業務執行者又は非業務執行取締役"""
    C = "3"
    """上場会社の兄弟会社の業務執行者"""
    D = "4"
    """上場会社を主要な取引先とする者又はその業務執行者"""
    E = "5"
    """上場会社の主要な取引先又はその業務執行者"""
    F = "6"
    """コンサルタント、会計専門家、法律専門家"""
    G = "7"
    """上場会社の主要株主"""
    H = "8"
    """上場会社の取引先の業務執行者"""
    I = "9"
    """社外役員の相互就任"""
    J = "10"
    """上場会社が寄付を行っている先の業務執行者"""
    K = "11"
    """その他"""


class OutsideAuditorRelation(str, Enum):
    """社外監査役の関係 (a-m)."""

    A = "1"
    """上場会社又はその子会社の業務執行者"""
    B = "2"
    """上場会社又はその子会社の非業務執行取締役又は会計参与"""
    C = "3"
    """上場会社の親会社の業務執行者又は非業務執行取締役"""
    D = "4"
    """上場会社の親会社の監査役"""
    E = "5"
    """上場会社の兄弟会社の業務執行者"""
    F = "6"
    """上場会社を主要な取引先とする者又はその業務執行者"""
    G = "7"
    """上場会社の主要な取引先又はその業務執行者"""
    H = "8"
    """コンサルタント、会計専門家、法律専門家"""
    I = "9"
    """上場会社の主要株主"""
    J = "10"
    """上場会社の取引先の業務執行者"""
    K = "11"
    """社外役員の相互就任"""
    L = "12"
    """上場会社が寄付を行っている先の業務執行者"""
    M = "13"
    """その他"""


class CompensationDisclosure(str, Enum):
    """報酬の開示状況."""

    全員個別開示 = "1"
    一部個別開示 = "2"
    個別開示なし = "3"


# ---------------------------------------------------------------------------
# JJK 検索結果
# ---------------------------------------------------------------------------


@dataclass
class SearchResultItem:
    """JJK 検索結果一覧の 1 行.

    Attributes:
        code: 証券コード（5桁）.
        name: 銘柄名.
        market: 市場区分.
        industry: 業種分類.
        fiscal_period: 決算期.
        has_notice: 注意情報等の有無.
        stock_price_url: 株価表示の URL.
    """

    code: str
    name: str
    market: str
    industry: str
    fiscal_period: str
    has_notice: bool
    stock_price_url: str | None = None


@dataclass
class CompanySearchResult:
    """JJK 検索結果.

    Attributes:
        total: 該当件数.
        items: 検索結果一覧.
    """

    total: int
    items: list[SearchResultItem]


# ---------------------------------------------------------------------------
# CGK 検索結果
# ---------------------------------------------------------------------------


@dataclass
class CGSearchResultItem:
    """CGK 検索結果の 1 行.

    Attributes:
        code: 証券コード（5桁）.
        name: 銘柄名.
        organization_type: 組織形態.
        organization_type_code: 組織形態コード.
        parent_company: 親会社.
        parent_company_code: 親会社コード.
        major_shareholder_name: 筆頭株主 名称.
        major_shareholder_ratio: 筆頭株主 比率(%).
        directors_count: 取締役.
        independent_directors_count: 独立社外取締役.
        viewing_date: 縦覧日.
        pdf_url: PDF ファイル URL.
        html_url: HTML ファイル URL.
        xbrl_url: XBRL ファイル URL.
    """

    code: str
    name: str
    organization_type: str
    organization_type_code: str
    parent_company: str
    parent_company_code: str
    major_shareholder_name: str
    major_shareholder_ratio: str
    directors_count: str
    independent_directors_count: str
    viewing_date: str
    pdf_url: str | None = None
    html_url: str | None = None
    xbrl_url: str | None = None


@dataclass
class CGSearchResult:
    """CGK 検索結果.

    Attributes:
        total: 該当件数.
        detailed_total: 詳細該当件数.
        items: 検索結果一覧.
    """

    total: int
    detailed_total: int
    items: list[CGSearchResultItem]


# ---------------------------------------------------------------------------
# JJK 詳細ページ - 基本情報タブ
# ---------------------------------------------------------------------------


@dataclass
class CompanyBasicInfo:
    """基本情報タブ.

    Attributes:
        code: 証券コード（5桁）.
        isin: ISINコード.
        market: 市場区分.
        industry: 業種分類.
        fiscal_period: 決算期.
        trading_unit: 売買単位.
        name: 銘柄名.
        name_en: 英文社名.
        transfer_agent: 株主名簿管理人.
        established: 設立年月日.
        headquarters: 本店所在地.
        listed_exchange: 上場取引所.
        investment_unit: 投資単位.
        earnings_announcement: 決算発表予定日.
        q1_announcement: 第一四半期決算発表予定日.
        q2_announcement: 第二四半期決算発表予定日.
        q3_announcement: 第三四半期決算発表予定日.
        shareholders_meeting: 株主総会開催予定日.
        representative_title: 代表者役職名.
        representative_name: 代表者氏名.
        listing_date: 上場年月日.
        notice_info: 注意情報等.
        listed_shares: 上場株式数.
        shares_outstanding: 発行済株式数.
        j_iriss: J-IRISS 登録状況.
        margin_trading: 信用取引区分.
        credit_trading: 貸借取引区分.
        accounting_standards_membership: 財務会計基準機構への加入.
        going_concern: 継続企業の前提の注記.
        controlling_shareholder: 支配株主等.
        other_notices: その他注意事項.
        stock_price_url: 株価情報 URL.
    """

    # ヘッダー行
    code: str
    isin: str
    market: str
    industry: str
    fiscal_period: str
    trading_unit: str
    # 基本情報テーブル
    name: str
    name_en: str
    transfer_agent: str
    established: str
    headquarters: str
    listed_exchange: str
    investment_unit: str
    earnings_announcement: str
    q1_announcement: str
    q2_announcement: str
    q3_announcement: str
    shareholders_meeting: str
    representative_title: str
    representative_name: str
    listing_date: str
    # 注意情報等
    notice_info: str
    listed_shares: str
    shares_outstanding: str
    j_iriss: str
    margin_trading: str
    credit_trading: str
    accounting_standards_membership: str
    going_concern: str
    controlling_shareholder: str
    other_notices: list[str] = field(default_factory=list)
    # 株価情報URL
    stock_price_url: str | None = None


# ---------------------------------------------------------------------------
# JJK 詳細ページ - 適時開示情報タブ
# ---------------------------------------------------------------------------


@dataclass
class DisclosureItem:
    """開示情報の 1 行.

    Attributes:
        date: 開示日.
        title: タイトル.
        pdf_url: PDF URL.
        xbrl_url: XBRL URL.
        html_urls: HTML URL 一覧.
    """

    date: str
    title: str
    pdf_url: str | None = None
    xbrl_url: str | None = None
    html_urls: list[str] = field(default_factory=list)


@dataclass
class DisclosureSection:
    """適時開示情報タブ.

    Attributes:
        legal: 法定開示情報 (hotei).
        earnings: 決算情報 (1101).
        material_facts: 決定事実/発生事実 (1102).
        compliance_plan: 上場維持基準への適合に向けた計画 (1103).
        other: その他 (1104).
    """

    legal: list[DisclosureItem] = field(default_factory=list)
    earnings: list[DisclosureItem] = field(default_factory=list)
    material_facts: list[DisclosureItem] = field(default_factory=list)
    compliance_plan: list[DisclosureItem] = field(default_factory=list)
    other: list[DisclosureItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JJK 詳細ページ - 縦覧書類 / PR情報タブ
# ---------------------------------------------------------------------------


@dataclass
class FilingItem:
    """縦覧書類・PR 情報の 1 行.

    Attributes:
        date: 開示日.
        title: タイトル.
        pdf_url: PDF URL.
    """

    date: str
    title: str
    pdf_url: str | None = None


@dataclass
class FilingSection:
    """縦覧書類 / PR 情報タブ.

    Attributes:
        shareholder_meeting: 株主総会招集通知 / 株主総会資料 (1105).
        independent_officers: 独立役員届出書 (1106).
        articles: 定款 (1107).
        other: その他 (1109).
        esg: ESG に関する報告書 (1110).
        pr: PR 情報 (1108).
    """

    shareholder_meeting: list[FilingItem] = field(default_factory=list)
    independent_officers: list[FilingItem] = field(default_factory=list)
    articles: list[FilingItem] = field(default_factory=list)
    other: list[FilingItem] = field(default_factory=list)
    esg: list[FilingItem] = field(default_factory=list)
    pr: list[FilingItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JJK 詳細ページ - コーポレート・ガバナンス情報タブ
# ---------------------------------------------------------------------------


@dataclass
class CGInfoItem:
    """CG 情報タブの 1 行.

    Attributes:
        organization_type: 組織形態.
        parent_company: 親会社.
        foreign_ownership_ratio: 外国人株式所有比率.
        major_shareholder_name: 筆頭株主 名称.
        major_shareholder_ratio: 筆頭株主 比率(%).
        directors: 取締役（独立社外）.
        auditors: 監査役（独立社外）.
        viewing_date: 縦覧日.
        pdf_url: PDF URL.
        html_url: HTML URL.
        xbrl_url: XBRL URL.
    """

    organization_type: str
    parent_company: str
    foreign_ownership_ratio: str
    major_shareholder_name: str
    major_shareholder_ratio: str
    directors: str
    auditors: str
    viewing_date: str
    pdf_url: str | None = None
    html_url: str | None = None
    xbrl_url: str | None = None


# ---------------------------------------------------------------------------
# JJK 詳細ページ - 統合
# ---------------------------------------------------------------------------


@dataclass
class CompanyDetail:
    """企業詳細（全タブ統合）.

    Attributes:
        basic: 基本情報タブ.
        disclosures: 適時開示情報タブ.
        filings: 縦覧書類 / PR 情報タブ.
        cg_info: コーポレート・ガバナンス情報タブ.
    """

    basic: CompanyBasicInfo
    disclosures: DisclosureSection = field(default_factory=DisclosureSection)
    filings: FilingSection = field(default_factory=FilingSection)
    cg_info: list[CGInfoItem] = field(default_factory=list)
