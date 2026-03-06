"""東証検索サービスクライアント."""

from __future__ import annotations

import re
from datetime import date
from typing import Sequence

import httpx

from tse_hp_front.models import (
    AnnouncementType,
    CGSearchResult,
    CompensationDisclosure,
    CompanyDetail,
    CompanySearchResult,
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
)
from tse_hp_front.parsers import parse_cg_search_result, parse_detail, parse_search_result

_BASE_URL = "https://www2.jpx.co.jp"
_JJK_INIT = "/tseHpFront/JJK010010Action.do"
_JJK_SEARCH = "/tseHpFront/JJK010020Action.do"
_JJK_DETAIL = "/tseHpFront/JJK010030Action.do"
_CGK_INIT = "/tseHpFront/CGK010010Action.do"


def _to_code5(code: str) -> str:
    """4桁コードを5桁（チェックディジット付き）に変換. 5桁はそのまま返す."""
    code = code.strip()
    if len(code) == 4:
        return code + "0"
    return code


def _date_fields(d: date | None, prefix: str) -> dict[str, str]:
    """date を年/月/日の3セレクトに展開."""
    if d is None:
        return {
            f"{prefix}YearPd": " ",
            f"{prefix}TskPd": " ",
            f"{prefix}DayPd": " ",
        }
    return {
        f"{prefix}YearPd": str(d.year),
        f"{prefix}TskPd": f"{d.month:02d}",
        f"{prefix}DayPd": f"{d.day:02d}",
    }


def _bool_val(v: bool | None) -> str:
    """bool | None → "1" / "0" / " "."""
    if v is None:
        return " "
    return "1" if v else "0"


def _int_val(v: int | None) -> str:
    """int | None → str / ""."""
    return str(v) if v is not None else ""


class TseClient:
    """東証上場会社情報・CG情報の検索クライアント.

    httpx.Client のセッション管理を利用してJSESSIONIDを自動処理する.
    """

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._http = httpx.Client(
            base_url=_BASE_URL,
            timeout=timeout,
            follow_redirects=True,
        )
        self._jjk_ready = False
        self._cgk_ready = False
        self._cgk_jsessionid: str = ""

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> TseClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -- セッション確立 --

    def _ensure_jjk_session(self) -> None:
        if self._jjk_ready:
            return
        self._http.get(_JJK_INIT, params={"Show": "Show"})
        self._jjk_ready = True

    def _ensure_cgk_session(self) -> str:
        """CGKセッション確立し、jsessionidを返す."""
        if self._cgk_ready:
            return self._cgk_jsessionid
        resp = self._http.get(_CGK_INIT, params={"Show": "Show"})
        m = re.search(r'jsessionid=([^"]+)', resp.text)
        self._cgk_jsessionid = m.group(1) if m else ""
        self._cgk_ready = True
        return self._cgk_jsessionid

    # -- JJK: 上場会社情報 --

    def search(
        self,
        *,
        name: str = "",
        code: str = "",
        markets: Sequence[Market] = (),
        limit: int = 100,
        include_delisted: bool = False,
        # 詳細検索条件
        prefecture: Prefecture | None = None,
        industry: Industry | None = None,
        trading_unit: int | None = None,
        fiscal_period: int | None = None,
        fiscal_period_2: int | None = None,
        announcement_types: Sequence[AnnouncementType] = (),
        announcement_date_from: date | None = None,
        announcement_date_to: date | None = None,
        shareholders_meeting_from: date | None = None,
        shareholders_meeting_to: date | None = None,
        accounting_membership: bool | None = None,
        j_iriss: bool | None = None,
        going_concern: bool | None = None,
        controlling_shareholder: bool | None = None,
    ) -> CompanySearchResult:
        """上場会社を検索する.

        簡易検索・詳細検索の全条件に対応する.

        Args:
            name: 銘柄名（会社名）.
            code: 証券コード.
            markets: 市場区分.
            limit: 表示社数 (10, 50, 100, 200).
            include_delisted: 上場廃止会社を含む.
            prefecture: 本社所在地.
            industry: 業種分類.
            trading_unit: 売買単位 (1, 10, 50, 100, 500, 1000, 3000, -1=その他).
            fiscal_period: 決算期1 (1-12).
            fiscal_period_2: 決算期2 (1-12).
            announcement_types: 決算発表予定日の種別.
            announcement_date_from: 決算発表予定日 開始.
            announcement_date_to: 決算発表予定日 終了.
            shareholders_meeting_from: 株主総会開催予定日 開始.
            shareholders_meeting_to: 株主総会開催予定日 終了.
            accounting_membership: 財務会計基準機構への加入有無.
            j_iriss: J-IRISS の登録有無.
            going_concern: 継続企業の前提の注記の有無.
            controlling_shareholder: 支配株主等の有無.

        Returns:
            検索結果.
        """
        self._ensure_jjk_session()
        data: dict[str, str | list[str]] = {
            "ListShow": "ListShow",
            "mgrMiTxtBx": name,
            "eqMgrCd": code,
            "dspSsuPd": str(limit),
            "hnsShzitPd": prefecture.value if prefecture else " ",
            "gyshKbnPd": industry.value if industry else " ",
            "bibiTniPd": str(trading_unit) if trading_unit is not None else " ",
            "kssnKiPd": f"{fiscal_period:02d}" if fiscal_period else " ",
            "kssnKi2Pd": f"{fiscal_period_2:02d}" if fiscal_period_2 else " ",
            "zmkkKjnKkPd": _bool_val(accounting_membership),
            "jirissPd": _bool_val(j_iriss),
            "kizkKguZntCukPd": _bool_val(going_concern),
            "shiEqnsJkuPd": _bool_val(controlling_shareholder),
        }
        data.update(_date_fields(announcement_date_from, "kssnHpuYtiDayFrm"))
        data.update(_date_fields(announcement_date_to, "kssnHpuYtiDayTo"))
        data.update(_date_fields(shareholders_meeting_from, "eqnsskKaisiDayFrm"))
        data.update(_date_fields(shareholders_meeting_to, "eqnsskKaisiDayTo"))
        if markets:
            data["szkbuChkbx"] = [m.value for m in markets]
        if include_delisted:
            data["jjHisiKbnChkbx"] = "on"
        _ann_map = {
            AnnouncementType.決算: "kssnChkbx",
            AnnouncementType.第一四半期: "diyhkChkbx",
            AnnouncementType.第二四半期: "midChkbx",
            AnnouncementType.第三四半期: "dsyhkChkbx",
        }
        for at in announcement_types:
            data[_ann_map[at]] = "on"

        resp = self._http.post(_JJK_SEARCH, data=data)
        return parse_search_result(resp.text)

    def get_detail(self, code: str) -> CompanyDetail:
        """企業詳細を取得する（1 リクエストで全タブ）.

        Args:
            code: 4 桁 or 5 桁の証券コード.

        Returns:
            全タブを統合した企業詳細.
        """
        self._ensure_jjk_session()
        resp = self._http.post(
            _JJK_DETAIL,
            data={
                "BaseJh": "BaseJh",
                "mgrCd": _to_code5(code),
                "jjHisiFlg": "1",
            },
        )
        return parse_detail(resp.text)

    # -- CGK: CG情報 --

    def search_cg(  # noqa: C901, PLR0913
        self,
        *,
        # 基本
        name: str = "",
        code: str = "",
        markets: Sequence[Market] = (),
        limit: int = 100,
        include_delisted: bool = False,
        english_cg_report: bool = False,
        # 会社属性情報
        prefecture: Prefecture | None = None,
        industry: Industry | None = None,
        trading_unit: int | None = None,
        fiscal_period: int | None = None,
        # 組織形態・資本構成等
        organization_type: OrganizationType | None = None,
        foreign_ownership_from: ForeignOwnershipFrom | None = None,
        foreign_ownership_to: ForeignOwnershipTo | None = None,
        controlling_shareholder: bool | None = None,
        parent_company: ParentCompanyStatus | None = None,
        parent_company_code: str = "",
        # 取締役関係
        articles_directors_from: int | None = None,
        articles_directors_to: int | None = None,
        director_tenure: DirectorTenure | None = None,
        directors_from: int | None = None,
        directors_to: int | None = None,
        outside_directors_from: int | None = None,
        outside_directors_to: int | None = None,
        independent_directors_from: int | None = None,
        independent_directors_to: int | None = None,
        outside_director_attributes: Sequence[OutsideOfficerAttribute] = (),
        outside_director_relation_period: RelationPeriod | None = None,
        outside_director_relations: Sequence[OutsideDirectorRelation] = (),
        # 監査役関係
        articles_auditors_from: int | None = None,
        articles_auditors_to: int | None = None,
        auditors_from: int | None = None,
        auditors_to: int | None = None,
        outside_auditors_from: int | None = None,
        outside_auditors_to: int | None = None,
        independent_auditors_from: int | None = None,
        independent_auditors_to: int | None = None,
        outside_auditor_attributes: Sequence[OutsideOfficerAttribute] = (),
        outside_auditor_relation_period: RelationPeriod | None = None,
        outside_auditor_relations: Sequence[OutsideAuditorRelation] = (),
        # 指名委員会等設置会社関係
        nomination_committee_from: int | None = None,
        nomination_committee_to: int | None = None,
        nomination_committee_outside_from: int | None = None,
        nomination_committee_outside_to: int | None = None,
        compensation_committee_from: int | None = None,
        compensation_committee_to: int | None = None,
        compensation_committee_outside_from: int | None = None,
        compensation_committee_outside_to: int | None = None,
        audit_committee_from: int | None = None,
        audit_committee_to: int | None = None,
        audit_committee_outside_from: int | None = None,
        audit_committee_outside_to: int | None = None,
        executive_officers_from: int | None = None,
        executive_officers_to: int | None = None,
        # 監査等委員会設置会社関係
        audit_supervisory_committee_from: int | None = None,
        audit_supervisory_committee_to: int | None = None,
        audit_supervisory_committee_outside_from: int | None = None,
        audit_supervisory_committee_outside_to: int | None = None,
        # 任意の委員会関係
        optional_committee_exists: bool | None = None,
        optional_nomination_from: int | None = None,
        optional_nomination_to: int | None = None,
        optional_nomination_outside_from: int | None = None,
        optional_nomination_outside_to: int | None = None,
        optional_compensation_from: int | None = None,
        optional_compensation_to: int | None = None,
        optional_compensation_outside_from: int | None = None,
        optional_compensation_outside_to: int | None = None,
        # その他
        independent_officers_from: int | None = None,
        independent_officers_to: int | None = None,
        advisor_status_exists: bool | None = None,
        advisor_count_from: int | None = None,
        advisor_count_to: int | None = None,
        electronic_voting: bool | None = None,
        voting_platform: bool | None = None,
        english_notice: bool | None = None,
        director_compensation_disclosure: Sequence[CompensationDisclosure] = (),
        executive_compensation_disclosure: Sequence[CompensationDisclosure] = (),
        compensation_policy: bool | None = None,
        takeover_defense: bool | None = None,
        viewing_date_from: date | None = None,
        viewing_date_to: date | None = None,
    ) -> CGSearchResult:
        """コーポレート・ガバナンス情報を検索する.

        Args:
            name: 銘柄名（会社名）.
            code: 証券コード.
            markets: 市場区分 (プライム/スタンダード/グロース).
            limit: 表示社数 (10, 50, 100, 200).
            include_delisted: 上場廃止会社.
            english_cg_report: 英訳版 CG 報告書を開示している会社.
            prefecture: 本社所在地.
            industry: 業種分類.
            trading_unit: 売買単位.
            fiscal_period: 決算期 (1-12).
            organization_type: 組織形態.
            foreign_ownership_from: 外国人株式所有比率 下限.
            foreign_ownership_to: 外国人株式所有比率 上限.
            controlling_shareholder: 支配株主の有無.
            parent_company: 親会社有無.
            parent_company_code: 親会社のコード.
            articles_directors_from: 定款上の取締役員数 下限.
            articles_directors_to: 定款上の取締役員数 上限.
            director_tenure: 定款上の取締役任期.
            directors_from: 取締役人数 下限.
            directors_to: 取締役人数 上限.
            outside_directors_from: 社外取締役人数 下限.
            outside_directors_to: 社外取締役人数 上限.
            independent_directors_from: 社外取締役（独立役員）人数 下限.
            independent_directors_to: 社外取締役（独立役員）人数 上限.
            outside_director_attributes: 社外取締役属性.
            outside_director_relation_period: 社外取締役の関係 期間.
            outside_director_relations: 社外取締役の関係 (a-k).
            articles_auditors_from: 定款上の監査役員数 下限.
            articles_auditors_to: 定款上の監査役員数 上限.
            auditors_from: 監査役人数 下限.
            auditors_to: 監査役人数 上限.
            outside_auditors_from: 社外監査役人数 下限.
            outside_auditors_to: 社外監査役人数 上限.
            independent_auditors_from: 社外監査役（独立役員）人数 下限.
            independent_auditors_to: 社外監査役（独立役員）人数 上限.
            outside_auditor_attributes: 社外監査役属性.
            outside_auditor_relation_period: 社外監査役の関係 期間.
            outside_auditor_relations: 社外監査役の関係 (a-m).
            nomination_committee_from: 指名委員会 全委員数 下限.
            nomination_committee_to: 指名委員会 全委員数 上限.
            nomination_committee_outside_from: 指名委員会 社外取締役人数 下限.
            nomination_committee_outside_to: 指名委員会 社外取締役人数 上限.
            compensation_committee_from: 報酬委員会 全委員数 下限.
            compensation_committee_to: 報酬委員会 全委員数 上限.
            compensation_committee_outside_from: 報酬委員会 社外取締役人数 下限.
            compensation_committee_outside_to: 報酬委員会 社外取締役人数 上限.
            audit_committee_from: 監査委員会 全委員数 下限.
            audit_committee_to: 監査委員会 全委員数 上限.
            audit_committee_outside_from: 監査委員会 社外取締役人数 下限.
            audit_committee_outside_to: 監査委員会 社外取締役人数 上限.
            executive_officers_from: 執行役人数 下限.
            executive_officers_to: 執行役人数 上限.
            audit_supervisory_committee_from: 監査等委員会 全委員数 下限.
            audit_supervisory_committee_to: 監査等委員会 全委員数 上限.
            audit_supervisory_committee_outside_from: 監査等委員会 社外取締役人数 下限.
            audit_supervisory_committee_outside_to: 監査等委員会 社外取締役人数 上限.
            optional_committee_exists: 任意の委員会の有無.
            optional_nomination_from: 指名委員会相当の任意委員会 全委員数 下限.
            optional_nomination_to: 指名委員会相当の任意委員会 全委員数 上限.
            optional_nomination_outside_from: 指名委員会相当の任意委員会 社外取締役人数 下限.
            optional_nomination_outside_to: 指名委員会相当の任意委員会 社外取締役人数 上限.
            optional_compensation_from: 報酬委員会相当の任意委員会 全委員数 下限.
            optional_compensation_to: 報酬委員会相当の任意委員会 全委員数 上限.
            optional_compensation_outside_from: 報酬委員会相当の任意委員会 社外取締役人数 下限.
            optional_compensation_outside_to: 報酬委員会相当の任意委員会 社外取締役人数 上限.
            independent_officers_from: 独立役員人数 下限.
            independent_officers_to: 独立役員人数 上限.
            advisor_status_exists: 相談役・顧問等の状況の記載の有無.
            advisor_count_from: 相談役・顧問等の人数 下限.
            advisor_count_to: 相談役・顧問等の人数 上限.
            electronic_voting: 電磁的方法による議決権行使.
            voting_platform: 議決権電子行使プラットフォームへの参加.
            english_notice: 招集通知（要約）の英文での提供.
            director_compensation_disclosure: 取締役報酬の開示状況.
            executive_compensation_disclosure: 執行役報酬の開示状況.
            compensation_policy: 報酬の額又はその算定方法の決定方針の有無.
            takeover_defense: 買収防衛策の導入の有無.
            viewing_date_from: 縦覧日 開始.
            viewing_date_to: 縦覧日 終了.

        Returns:
            検索結果.
        """
        jsid = self._ensure_cgk_session()

        data: dict[str, str | list[str]] = {
            "ListShow": "ListShow",
            "mgrMiTxtBx": name,
            "eqMgrCd": code,
            "dspSsuPd": str(limit),
            "sbrkmFlg": "1",
            "souKnsu": "0",
            "jyuKmkAti1": "",
            # 会社属性情報
            "hnsShzitPd": prefecture.value if prefecture else " ",
            "gyshBnriPd": industry.value if industry else " ",
            "bibiTniPd": str(trading_unit) if trading_unit is not None else " ",
            "kssnKiPd": f"{fiscal_period:02d}" if fiscal_period else " ",
            # 組織形態・資本構成等
            "sskKitiPd": organization_type.value if organization_type else " ",
            "gikkNnEqSyuHrtFrmPd": foreign_ownership_from.value if foreign_ownership_from else " ",
            "gikkNnEqSyuHrtToPd": foreign_ownership_to.value if foreign_ownership_to else " ",
            "shiEqnsUmPd": _bool_val(controlling_shareholder),
            "oyaCrpUmPd": parent_company.value if parent_company else " ",
            "oyaCrpCd": parent_company_code,
            # 取締役関係
            "tiknJoTrshmrykIzuFrmTxtBx": _int_val(articles_directors_from),
            "tiknJoTrshmrykIzuToTxtBx": _int_val(articles_directors_to),
            "tiknJoTrshmrykNnkPd": director_tenure.value if director_tenure else " ",
            "tsynzFrmTxtBx": _int_val(directors_from),
            "tsynzToTxtBx": _int_val(directors_to),
            "sgiTsynzFrmTxtBx": _int_val(outside_directors_from),
            "sgiTsynzToTxtBx": _int_val(outside_directors_to),
            "sgiTrshmrykDryiNzuFrmTxtBx": _int_val(independent_directors_from),
            "sgiTrshmrykDryiNzuToTxtBx": _int_val(independent_directors_to),
            "sgiTrshmrykKnkiPd": (
                outside_director_relation_period.value
                if outside_director_relation_period
                else "01"
            ),
            # 監査役関係
            "tiknJoKsykIzuFrmTxtBx": _int_val(articles_auditors_from),
            "tiknJoKsykIzuToTxtBx": _int_val(articles_auditors_to),
            "ksykNzuFrmTxtBx": _int_val(auditors_from),
            "ksykNzuToTxtBx": _int_val(auditors_to),
            "sgiKsykNzuFrmTxtBx": _int_val(outside_auditors_from),
            "sgiKsykNzuToTxtBx": _int_val(outside_auditors_to),
            "sgiKsykDryiNzuFrmTxtBx": _int_val(independent_auditors_from),
            "sgiKsykDryiNzuToTxtBx": _int_val(independent_auditors_to),
            "sgiKsykKnkiPd": (
                outside_auditor_relation_period.value
                if outside_auditor_relation_period
                else "01"
            ),
            # 指名委員会等設置会社関係
            "smiIikiNzuFrmTxtBx": _int_val(nomination_committee_from),
            "smiIikiNzuToTxtBx": _int_val(nomination_committee_to),
            "smiIikiSgiTsynzFrmTxtBx": _int_val(nomination_committee_outside_from),
            "smiIikiSgiTsynzToTxtBx": _int_val(nomination_committee_outside_to),
            "hsuIikiNzuFrmTxtBx": _int_val(compensation_committee_from),
            "hsuIikiNzuToTxtBx": _int_val(compensation_committee_to),
            "hsuIikiSgiTsynzFrmTxtBx": _int_val(compensation_committee_outside_from),
            "hsuIikiSgiTsynzToTxtBx": _int_val(compensation_committee_outside_to),
            "knsIikiNzuFrmTxtBx": _int_val(audit_committee_from),
            "knsIikiNzuToTxtBx": _int_val(audit_committee_to),
            "knsIikiSgiTsynzFrmTxtBx": _int_val(audit_committee_outside_from),
            "knsIikiSgiTsynzToTxtBx": _int_val(audit_committee_outside_to),
            "skykNzuFrmTxtBx": _int_val(executive_officers_from),
            "skykNzuToTxtBx": _int_val(executive_officers_to),
            # 監査等委員会設置会社関係
            "knsToIikiNzuFrmTxtBx": _int_val(audit_supervisory_committee_from),
            "knsToIikiNzuToTxtBx": _int_val(audit_supervisory_committee_to),
            "knsToIikiSgiTsynzFrmTxtBx": _int_val(audit_supervisory_committee_outside_from),
            "knsToIikiSgiTsynzToTxtBx": _int_val(audit_supervisory_committee_outside_to),
            # 任意の委員会関係
            "smiHsuStNniIikiUmPd": _bool_val(optional_committee_exists),
            "smiStNniIikiNzuFrmTxtBx": _int_val(optional_nomination_from),
            "smiStNniIikiNzuToTxtBx": _int_val(optional_nomination_to),
            "smiStNniIikiSgiTsynzFrmTxtBx": _int_val(optional_nomination_outside_from),
            "smiStNniIikiSgiTsynzToTxtBx": _int_val(optional_nomination_outside_to),
            "hsuStNniIikiNzuFrmTxtBx": _int_val(optional_compensation_from),
            "hsuStNniIikiNzuToTxtBx": _int_val(optional_compensation_to),
            "hsuStNniIikiSgiTsynzFrmTxtBx": _int_val(optional_compensation_outside_from),
            "hsuStNniIikiSgiTsynzToTxtBx": _int_val(optional_compensation_outside_to),
            # その他
            "dryiNzuFrmTxtBx": _int_val(independent_officers_from),
            "dryiNzuToTxtBx": _int_val(independent_officers_to),
            "sdnykkmnUmPd": _bool_val(advisor_status_exists),
            "sdnykkmnNzuFrmTxtBx": _int_val(advisor_count_from),
            "sdnykkmnNzuToTxtBx": _int_val(advisor_count_to),
            "dnjTekiGktKnKsPd": _bool_val(electronic_voting),
            "gkkdsksBrtfmPd": _bool_val(voting_platform),
            "sstcyyEibnTikyPd": _bool_val(english_notice),
            "kttiHusnPd": _bool_val(compensation_policy),
            "bsbesDunuPd": _bool_val(takeover_defense),
        }

        # 縦覧日
        data.update(_date_fields(viewing_date_from, "jhUpdDayFrm"))
        data.update(_date_fields(viewing_date_to, "jhUpdDayTo"))

        # 市場区分チェックボックス
        if markets:
            data["szkbuChkbx"] = [m.value for m in markets]

        # 上場廃止 / 英訳版
        if include_delisted:
            data["jjHisiKbnChkbx"] = "on"
        if english_cg_report:
            data["eibnCGJhSelChkbx"] = "on"

        # 社外取締役属性チェックボックス
        for attr in outside_director_attributes:
            data[f"sgiTrshmrykZksi{attr.value}Chkbx"] = "on"

        # 社外取締役の関係チェックボックス
        for rel in outside_director_relations:
            data[f"snYuskSgiTrshmrykKnki{rel.value}Chkbx"] = "on"

        # 社外監査役属性チェックボックス
        for attr in outside_auditor_attributes:
            data[f"sgiKsykZksi{attr.value}Chkbx"] = "on"

        # 社外監査役の関係チェックボックス
        for rel in outside_auditor_relations:
            data[f"snYuskSgiKsykKnki{rel.value}Chkbx"] = "on"

        # 報酬開示状況チェックボックス
        if director_compensation_disclosure:
            data["trshmrykHsuKijJukyChkbx"] = [
                d.value for d in director_compensation_disclosure
            ]
        if executive_compensation_disclosure:
            data["skykHsuKijJukyChkbx"] = [
                d.value for d in executive_compensation_disclosure
            ]

        url = f"{_CGK_INIT};jsessionid={jsid}" if jsid else _CGK_INIT
        resp = self._http.post(url, data=data)
        return parse_cg_search_result(resp.text)

    def reset_session(self) -> None:
        """セッションをリセット."""
        self._jjk_ready = False
        self._cgk_ready = False
        self._cgk_jsessionid = ""
        self._http.cookies.clear()


class AsyncTseClient:
    """東証上場会社情報・CG情報の非同期検索クライアント.

    httpx.AsyncClient のセッション管理を利用してJSESSIONIDを自動処理する.
    """

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=timeout,
            follow_redirects=True,
        )
        self._jjk_ready = False
        self._cgk_ready = False
        self._cgk_jsessionid: str = ""

    async def close(self) -> None:
        """HTTPクライアントを閉じる."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncTseClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # -- セッション確立 --

    async def _ensure_jjk_session(self) -> None:
        if self._jjk_ready:
            return
        await self._http.get(_JJK_INIT, params={"Show": "Show"})
        self._jjk_ready = True

    async def _ensure_cgk_session(self) -> str:
        """CGKセッション確立し、jsessionidを返す."""
        if self._cgk_ready:
            return self._cgk_jsessionid
        resp = await self._http.get(_CGK_INIT, params={"Show": "Show"})
        m = re.search(r'jsessionid=([^"]+)', resp.text)
        self._cgk_jsessionid = m.group(1) if m else ""
        self._cgk_ready = True
        return self._cgk_jsessionid

    # -- JJK: 上場会社情報 --

    async def search(
        self,
        *,
        name: str = "",
        code: str = "",
        markets: Sequence[Market] = (),
        limit: int = 100,
        include_delisted: bool = False,
        # 詳細検索条件
        prefecture: Prefecture | None = None,
        industry: Industry | None = None,
        trading_unit: int | None = None,
        fiscal_period: int | None = None,
        fiscal_period_2: int | None = None,
        announcement_types: Sequence[AnnouncementType] = (),
        announcement_date_from: date | None = None,
        announcement_date_to: date | None = None,
        shareholders_meeting_from: date | None = None,
        shareholders_meeting_to: date | None = None,
        accounting_membership: bool | None = None,
        j_iriss: bool | None = None,
        going_concern: bool | None = None,
        controlling_shareholder: bool | None = None,
    ) -> CompanySearchResult:
        """上場会社を検索する.

        簡易検索・詳細検索の全条件に対応する.

        Args:
            name: 銘柄名（会社名）.
            code: 証券コード.
            markets: 市場区分.
            limit: 表示社数 (10, 50, 100, 200).
            include_delisted: 上場廃止会社を含む.
            prefecture: 本社所在地.
            industry: 業種分類.
            trading_unit: 売買単位 (1, 10, 50, 100, 500, 1000, 3000, -1=その他).
            fiscal_period: 決算期1 (1-12).
            fiscal_period_2: 決算期2 (1-12).
            announcement_types: 決算発表予定日の種別.
            announcement_date_from: 決算発表予定日 開始.
            announcement_date_to: 決算発表予定日 終了.
            shareholders_meeting_from: 株主総会開催予定日 開始.
            shareholders_meeting_to: 株主総会開催予定日 終了.
            accounting_membership: 財務会計基準機構への加入有無.
            j_iriss: J-IRISS の登録有無.
            going_concern: 継続企業の前提の注記の有無.
            controlling_shareholder: 支配株主等の有無.

        Returns:
            検索結果.
        """
        await self._ensure_jjk_session()
        data: dict[str, str | list[str]] = {
            "ListShow": "ListShow",
            "mgrMiTxtBx": name,
            "eqMgrCd": code,
            "dspSsuPd": str(limit),
            "hnsShzitPd": prefecture.value if prefecture else " ",
            "gyshKbnPd": industry.value if industry else " ",
            "bibiTniPd": str(trading_unit) if trading_unit is not None else " ",
            "kssnKiPd": f"{fiscal_period:02d}" if fiscal_period else " ",
            "kssnKi2Pd": f"{fiscal_period_2:02d}" if fiscal_period_2 else " ",
            "zmkkKjnKkPd": _bool_val(accounting_membership),
            "jirissPd": _bool_val(j_iriss),
            "kizkKguZntCukPd": _bool_val(going_concern),
            "shiEqnsJkuPd": _bool_val(controlling_shareholder),
        }
        data.update(_date_fields(announcement_date_from, "kssnHpuYtiDayFrm"))
        data.update(_date_fields(announcement_date_to, "kssnHpuYtiDayTo"))
        data.update(_date_fields(shareholders_meeting_from, "eqnsskKaisiDayFrm"))
        data.update(_date_fields(shareholders_meeting_to, "eqnsskKaisiDayTo"))
        if markets:
            data["szkbuChkbx"] = [m.value for m in markets]
        if include_delisted:
            data["jjHisiKbnChkbx"] = "on"
        _ann_map = {
            AnnouncementType.決算: "kssnChkbx",
            AnnouncementType.第一四半期: "diyhkChkbx",
            AnnouncementType.第二四半期: "midChkbx",
            AnnouncementType.第三四半期: "dsyhkChkbx",
        }
        for at in announcement_types:
            data[_ann_map[at]] = "on"

        resp = await self._http.post(_JJK_SEARCH, data=data)
        return parse_search_result(resp.text)

    async def get_detail(self, code: str) -> CompanyDetail:
        """企業詳細を取得する（1 リクエストで全タブ）.

        Args:
            code: 4 桁 or 5 桁の証券コード.

        Returns:
            全タブを統合した企業詳細.
        """
        await self._ensure_jjk_session()
        resp = await self._http.post(
            _JJK_DETAIL,
            data={
                "BaseJh": "BaseJh",
                "mgrCd": _to_code5(code),
                "jjHisiFlg": "1",
            },
        )
        return parse_detail(resp.text)

    # -- CGK: CG情報 --

    async def search_cg(  # noqa: C901, PLR0913
        self,
        *,
        # 基本
        name: str = "",
        code: str = "",
        markets: Sequence[Market] = (),
        limit: int = 100,
        include_delisted: bool = False,
        english_cg_report: bool = False,
        # 会社属性情報
        prefecture: Prefecture | None = None,
        industry: Industry | None = None,
        trading_unit: int | None = None,
        fiscal_period: int | None = None,
        # 組織形態・資本構成等
        organization_type: OrganizationType | None = None,
        foreign_ownership_from: ForeignOwnershipFrom | None = None,
        foreign_ownership_to: ForeignOwnershipTo | None = None,
        controlling_shareholder: bool | None = None,
        parent_company: ParentCompanyStatus | None = None,
        parent_company_code: str = "",
        # 取締役関係
        articles_directors_from: int | None = None,
        articles_directors_to: int | None = None,
        director_tenure: DirectorTenure | None = None,
        directors_from: int | None = None,
        directors_to: int | None = None,
        outside_directors_from: int | None = None,
        outside_directors_to: int | None = None,
        independent_directors_from: int | None = None,
        independent_directors_to: int | None = None,
        outside_director_attributes: Sequence[OutsideOfficerAttribute] = (),
        outside_director_relation_period: RelationPeriod | None = None,
        outside_director_relations: Sequence[OutsideDirectorRelation] = (),
        # 監査役関係
        articles_auditors_from: int | None = None,
        articles_auditors_to: int | None = None,
        auditors_from: int | None = None,
        auditors_to: int | None = None,
        outside_auditors_from: int | None = None,
        outside_auditors_to: int | None = None,
        independent_auditors_from: int | None = None,
        independent_auditors_to: int | None = None,
        outside_auditor_attributes: Sequence[OutsideOfficerAttribute] = (),
        outside_auditor_relation_period: RelationPeriod | None = None,
        outside_auditor_relations: Sequence[OutsideAuditorRelation] = (),
        # 指名委員会等設置会社関係
        nomination_committee_from: int | None = None,
        nomination_committee_to: int | None = None,
        nomination_committee_outside_from: int | None = None,
        nomination_committee_outside_to: int | None = None,
        compensation_committee_from: int | None = None,
        compensation_committee_to: int | None = None,
        compensation_committee_outside_from: int | None = None,
        compensation_committee_outside_to: int | None = None,
        audit_committee_from: int | None = None,
        audit_committee_to: int | None = None,
        audit_committee_outside_from: int | None = None,
        audit_committee_outside_to: int | None = None,
        executive_officers_from: int | None = None,
        executive_officers_to: int | None = None,
        # 監査等委員会設置会社関係
        audit_supervisory_committee_from: int | None = None,
        audit_supervisory_committee_to: int | None = None,
        audit_supervisory_committee_outside_from: int | None = None,
        audit_supervisory_committee_outside_to: int | None = None,
        # 任意の委員会関係
        optional_committee_exists: bool | None = None,
        optional_nomination_from: int | None = None,
        optional_nomination_to: int | None = None,
        optional_nomination_outside_from: int | None = None,
        optional_nomination_outside_to: int | None = None,
        optional_compensation_from: int | None = None,
        optional_compensation_to: int | None = None,
        optional_compensation_outside_from: int | None = None,
        optional_compensation_outside_to: int | None = None,
        # その他
        independent_officers_from: int | None = None,
        independent_officers_to: int | None = None,
        advisor_status_exists: bool | None = None,
        advisor_count_from: int | None = None,
        advisor_count_to: int | None = None,
        electronic_voting: bool | None = None,
        voting_platform: bool | None = None,
        english_notice: bool | None = None,
        director_compensation_disclosure: Sequence[CompensationDisclosure] = (),
        executive_compensation_disclosure: Sequence[CompensationDisclosure] = (),
        compensation_policy: bool | None = None,
        takeover_defense: bool | None = None,
        viewing_date_from: date | None = None,
        viewing_date_to: date | None = None,
    ) -> CGSearchResult:
        """コーポレート・ガバナンス情報を検索する.

        Args:
            name: 銘柄名（会社名）.
            code: 証券コード.
            markets: 市場区分 (プライム/スタンダード/グロース).
            limit: 表示社数 (10, 50, 100, 200).
            include_delisted: 上場廃止会社.
            english_cg_report: 英訳版 CG 報告書を開示している会社.
            prefecture: 本社所在地.
            industry: 業種分類.
            trading_unit: 売買単位.
            fiscal_period: 決算期 (1-12).
            organization_type: 組織形態.
            foreign_ownership_from: 外国人株式所有比率 下限.
            foreign_ownership_to: 外国人株式所有比率 上限.
            controlling_shareholder: 支配株主の有無.
            parent_company: 親会社有無.
            parent_company_code: 親会社のコード.
            articles_directors_from: 定款上の取締役員数 下限.
            articles_directors_to: 定款上の取締役員数 上限.
            director_tenure: 定款上の取締役任期.
            directors_from: 取締役人数 下限.
            directors_to: 取締役人数 上限.
            outside_directors_from: 社外取締役人数 下限.
            outside_directors_to: 社外取締役人数 上限.
            independent_directors_from: 社外取締役（独立役員）人数 下限.
            independent_directors_to: 社外取締役（独立役員）人数 上限.
            outside_director_attributes: 社外取締役属性.
            outside_director_relation_period: 社外取締役の関係 期間.
            outside_director_relations: 社外取締役の関係 (a-k).
            articles_auditors_from: 定款上の監査役員数 下限.
            articles_auditors_to: 定款上の監査役員数 上限.
            auditors_from: 監査役人数 下限.
            auditors_to: 監査役人数 上限.
            outside_auditors_from: 社外監査役人数 下限.
            outside_auditors_to: 社外監査役人数 上限.
            independent_auditors_from: 社外監査役（独立役員）人数 下限.
            independent_auditors_to: 社外監査役（独立役員）人数 上限.
            outside_auditor_attributes: 社外監査役属性.
            outside_auditor_relation_period: 社外監査役の関係 期間.
            outside_auditor_relations: 社外監査役の関係 (a-m).
            nomination_committee_from: 指名委員会 全委員数 下限.
            nomination_committee_to: 指名委員会 全委員数 上限.
            nomination_committee_outside_from: 指名委員会 社外取締役人数 下限.
            nomination_committee_outside_to: 指名委員会 社外取締役人数 上限.
            compensation_committee_from: 報酬委員会 全委員数 下限.
            compensation_committee_to: 報酬委員会 全委員数 上限.
            compensation_committee_outside_from: 報酬委員会 社外取締役人数 下限.
            compensation_committee_outside_to: 報酬委員会 社外取締役人数 上限.
            audit_committee_from: 監査委員会 全委員数 下限.
            audit_committee_to: 監査委員会 全委員数 上限.
            audit_committee_outside_from: 監査委員会 社外取締役人数 下限.
            audit_committee_outside_to: 監査委員会 社外取締役人数 上限.
            executive_officers_from: 執行役人数 下限.
            executive_officers_to: 執行役人数 上限.
            audit_supervisory_committee_from: 監査等委員会 全委員数 下限.
            audit_supervisory_committee_to: 監査等委員会 全委員数 上限.
            audit_supervisory_committee_outside_from: 監査等委員会 社外取締役人数 下限.
            audit_supervisory_committee_outside_to: 監査等委員会 社外取締役人数 上限.
            optional_committee_exists: 任意の委員会の有無.
            optional_nomination_from: 指名委員会相当の任意委員会 全委員数 下限.
            optional_nomination_to: 指名委員会相当の任意委員会 全委員数 上限.
            optional_nomination_outside_from: 指名委員会相当の任意委員会 社外取締役人数 下限.
            optional_nomination_outside_to: 指名委員会相当の任意委員会 社外取締役人数 上限.
            optional_compensation_from: 報酬委員会相当の任意委員会 全委員数 下限.
            optional_compensation_to: 報酬委員会相当の任意委員会 全委員数 上限.
            optional_compensation_outside_from: 報酬委員会相当の任意委員会 社外取締役人数 下限.
            optional_compensation_outside_to: 報酬委員会相当の任意委員会 社外取締役人数 上限.
            independent_officers_from: 独立役員人数 下限.
            independent_officers_to: 独立役員人数 上限.
            advisor_status_exists: 相談役・顧問等の状況の記載の有無.
            advisor_count_from: 相談役・顧問等の人数 下限.
            advisor_count_to: 相談役・顧問等の人数 上限.
            electronic_voting: 電磁的方法による議決権行使.
            voting_platform: 議決権電子行使プラットフォームへの参加.
            english_notice: 招集通知（要約）の英文での提供.
            director_compensation_disclosure: 取締役報酬の開示状況.
            executive_compensation_disclosure: 執行役報酬の開示状況.
            compensation_policy: 報酬の額又はその算定方法の決定方針の有無.
            takeover_defense: 買収防衛策の導入の有無.
            viewing_date_from: 縦覧日 開始.
            viewing_date_to: 縦覧日 終了.

        Returns:
            検索結果.
        """
        jsid = await self._ensure_cgk_session()

        data: dict[str, str | list[str]] = {
            "ListShow": "ListShow",
            "mgrMiTxtBx": name,
            "eqMgrCd": code,
            "dspSsuPd": str(limit),
            "sbrkmFlg": "1",
            "souKnsu": "0",
            "jyuKmkAti1": "",
            # 会社属性情報
            "hnsShzitPd": prefecture.value if prefecture else " ",
            "gyshBnriPd": industry.value if industry else " ",
            "bibiTniPd": str(trading_unit) if trading_unit is not None else " ",
            "kssnKiPd": f"{fiscal_period:02d}" if fiscal_period else " ",
            # 組織形態・資本構成等
            "sskKitiPd": organization_type.value if organization_type else " ",
            "gikkNnEqSyuHrtFrmPd": foreign_ownership_from.value if foreign_ownership_from else " ",
            "gikkNnEqSyuHrtToPd": foreign_ownership_to.value if foreign_ownership_to else " ",
            "shiEqnsUmPd": _bool_val(controlling_shareholder),
            "oyaCrpUmPd": parent_company.value if parent_company else " ",
            "oyaCrpCd": parent_company_code,
            # 取締役関係
            "tiknJoTrshmrykIzuFrmTxtBx": _int_val(articles_directors_from),
            "tiknJoTrshmrykIzuToTxtBx": _int_val(articles_directors_to),
            "tiknJoTrshmrykNnkPd": director_tenure.value if director_tenure else " ",
            "tsynzFrmTxtBx": _int_val(directors_from),
            "tsynzToTxtBx": _int_val(directors_to),
            "sgiTsynzFrmTxtBx": _int_val(outside_directors_from),
            "sgiTsynzToTxtBx": _int_val(outside_directors_to),
            "sgiTrshmrykDryiNzuFrmTxtBx": _int_val(independent_directors_from),
            "sgiTrshmrykDryiNzuToTxtBx": _int_val(independent_directors_to),
            "sgiTrshmrykKnkiPd": (
                outside_director_relation_period.value
                if outside_director_relation_period
                else "01"
            ),
            # 監査役関係
            "tiknJoKsykIzuFrmTxtBx": _int_val(articles_auditors_from),
            "tiknJoKsykIzuToTxtBx": _int_val(articles_auditors_to),
            "ksykNzuFrmTxtBx": _int_val(auditors_from),
            "ksykNzuToTxtBx": _int_val(auditors_to),
            "sgiKsykNzuFrmTxtBx": _int_val(outside_auditors_from),
            "sgiKsykNzuToTxtBx": _int_val(outside_auditors_to),
            "sgiKsykDryiNzuFrmTxtBx": _int_val(independent_auditors_from),
            "sgiKsykDryiNzuToTxtBx": _int_val(independent_auditors_to),
            "sgiKsykKnkiPd": (
                outside_auditor_relation_period.value
                if outside_auditor_relation_period
                else "01"
            ),
            # 指名委員会等設置会社関係
            "smiIikiNzuFrmTxtBx": _int_val(nomination_committee_from),
            "smiIikiNzuToTxtBx": _int_val(nomination_committee_to),
            "smiIikiSgiTsynzFrmTxtBx": _int_val(nomination_committee_outside_from),
            "smiIikiSgiTsynzToTxtBx": _int_val(nomination_committee_outside_to),
            "hsuIikiNzuFrmTxtBx": _int_val(compensation_committee_from),
            "hsuIikiNzuToTxtBx": _int_val(compensation_committee_to),
            "hsuIikiSgiTsynzFrmTxtBx": _int_val(compensation_committee_outside_from),
            "hsuIikiSgiTsynzToTxtBx": _int_val(compensation_committee_outside_to),
            "knsIikiNzuFrmTxtBx": _int_val(audit_committee_from),
            "knsIikiNzuToTxtBx": _int_val(audit_committee_to),
            "knsIikiSgiTsynzFrmTxtBx": _int_val(audit_committee_outside_from),
            "knsIikiSgiTsynzToTxtBx": _int_val(audit_committee_outside_to),
            "skykNzuFrmTxtBx": _int_val(executive_officers_from),
            "skykNzuToTxtBx": _int_val(executive_officers_to),
            # 監査等委員会設置会社関係
            "knsToIikiNzuFrmTxtBx": _int_val(audit_supervisory_committee_from),
            "knsToIikiNzuToTxtBx": _int_val(audit_supervisory_committee_to),
            "knsToIikiSgiTsynzFrmTxtBx": _int_val(audit_supervisory_committee_outside_from),
            "knsToIikiSgiTsynzToTxtBx": _int_val(audit_supervisory_committee_outside_to),
            # 任意の委員会関係
            "smiHsuStNniIikiUmPd": _bool_val(optional_committee_exists),
            "smiStNniIikiNzuFrmTxtBx": _int_val(optional_nomination_from),
            "smiStNniIikiNzuToTxtBx": _int_val(optional_nomination_to),
            "smiStNniIikiSgiTsynzFrmTxtBx": _int_val(optional_nomination_outside_from),
            "smiStNniIikiSgiTsynzToTxtBx": _int_val(optional_nomination_outside_to),
            "hsuStNniIikiNzuFrmTxtBx": _int_val(optional_compensation_from),
            "hsuStNniIikiNzuToTxtBx": _int_val(optional_compensation_to),
            "hsuStNniIikiSgiTsynzFrmTxtBx": _int_val(optional_compensation_outside_from),
            "hsuStNniIikiSgiTsynzToTxtBx": _int_val(optional_compensation_outside_to),
            # その他
            "dryiNzuFrmTxtBx": _int_val(independent_officers_from),
            "dryiNzuToTxtBx": _int_val(independent_officers_to),
            "sdnykkmnUmPd": _bool_val(advisor_status_exists),
            "sdnykkmnNzuFrmTxtBx": _int_val(advisor_count_from),
            "sdnykkmnNzuToTxtBx": _int_val(advisor_count_to),
            "dnjTekiGktKnKsPd": _bool_val(electronic_voting),
            "gkkdsksBrtfmPd": _bool_val(voting_platform),
            "sstcyyEibnTikyPd": _bool_val(english_notice),
            "kttiHusnPd": _bool_val(compensation_policy),
            "bsbesDunuPd": _bool_val(takeover_defense),
        }

        # 縦覧日
        data.update(_date_fields(viewing_date_from, "jhUpdDayFrm"))
        data.update(_date_fields(viewing_date_to, "jhUpdDayTo"))

        # 市場区分チェックボックス
        if markets:
            data["szkbuChkbx"] = [m.value for m in markets]

        # 上場廃止 / 英訳版
        if include_delisted:
            data["jjHisiKbnChkbx"] = "on"
        if english_cg_report:
            data["eibnCGJhSelChkbx"] = "on"

        # 社外取締役属性チェックボックス
        for attr in outside_director_attributes:
            data[f"sgiTrshmrykZksi{attr.value}Chkbx"] = "on"

        # 社外取締役の関係チェックボックス
        for rel in outside_director_relations:
            data[f"snYuskSgiTrshmrykKnki{rel.value}Chkbx"] = "on"

        # 社外監査役属性チェックボックス
        for attr in outside_auditor_attributes:
            data[f"sgiKsykZksi{attr.value}Chkbx"] = "on"

        # 社外監査役の関係チェックボックス
        for rel in outside_auditor_relations:
            data[f"snYuskSgiKsykKnki{rel.value}Chkbx"] = "on"

        # 報酬開示状況チェックボックス
        if director_compensation_disclosure:
            data["trshmrykHsuKijJukyChkbx"] = [
                d.value for d in director_compensation_disclosure
            ]
        if executive_compensation_disclosure:
            data["skykHsuKijJukyChkbx"] = [
                d.value for d in executive_compensation_disclosure
            ]

        url = f"{_CGK_INIT};jsessionid={jsid}" if jsid else _CGK_INIT
        resp = await self._http.post(url, data=data)
        return parse_cg_search_result(resp.text)

    def reset_session(self) -> None:
        """セッションをリセット."""
        self._jjk_ready = False
        self._cgk_ready = False
        self._cgk_jsessionid = ""
        self._http.cookies.clear()
