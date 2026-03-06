# tse-hp-front — 東証 上場会社情報・CG情報 Python クライアント

[![Python](https://img.shields.io/pypi/pyversions/tse-hp-front.svg)](https://pypi.org/project/tse-hp-front/)

**tse-hp-front** は、[東京証券取引所 上場会社情報サービス](https://www2.jpx.co.jp/tseHpFront/JJK010010Action.do?Show=Show)および[コーポレート・ガバナンス情報サービス](https://www2.jpx.co.jp/tseHpFront/CGK010010Action.do?Show=Show)のスクレイピングクライアントライブラリです。上場会社検索（簡易・詳細）、企業詳細（基本情報・適時開示・縦覧書類・CG情報の全タブ）、CG検索（75以上の検索条件）をサポートし、同期・非同期クライアントを提供します。内部の HTTP 通信には [httpx](https://github.com/encode/httpx) を使用しています。

## インストール

```sh
pip install tse-hp-front
```

## クイックスタート

API キーは不要です。インストールしたらすぐに使えます。

```python
from tse_hp_front import TseClient, Market

with TseClient() as client:
    # トヨタ自動車を検索
    result = client.search(name="トヨタ")
    for item in result.items:
        print(item.code, item.name, item.market)

    # 企業詳細を取得（全タブ一括）
    detail = client.get_detail("7203")
    print(detail.basic.name)              # トヨタ自動車
    print(detail.basic.headquarters)      # 愛知
    print(detail.basic.representative_name)
```

## 上場会社検索

### 簡易検索

銘柄名・証券コード・市場区分で検索します。

```python
from tse_hp_front import TseClient, Market

with TseClient() as client:
    # 銘柄名で検索
    result = client.search(name="ソニー")
    print(result.total)  # 2
    for item in result.items:
        print(item.code, item.name, item.market, item.industry)

    # 証券コードで検索
    result = client.search(code="7203")

    # 市場区分で絞り込み
    result = client.search(
        markets=[Market.プライム, Market.スタンダード],
        limit=50,
    )

    # 上場廃止会社を含む
    result = client.search(name="東芝", include_delisted=True)
```

### 詳細検索

所在地、業種、決算期、決算発表予定日、株主総会日など全条件に対応します。

```python
from datetime import date
from tse_hp_front import TseClient, Market, Prefecture, Industry, AnnouncementType

with TseClient() as client:
    result = client.search(
        markets=[Market.プライム],
        prefecture=Prefecture.東京,
        industry=Industry.電気機器,
        fiscal_period=3,                           # 3月決算
        announcement_types=[AnnouncementType.決算], # 決算発表予定日で絞り込み
        announcement_date_from=date(2025, 4, 1),
        announcement_date_to=date(2025, 5, 31),
        accounting_membership=True,                # 財務会計基準機構加入
        j_iriss=True,                              # J-IRISS 登録あり
        going_concern=False,                       # GC注記なし
        controlling_shareholder=False,              # 支配株主なし
        limit=200,
    )
```

## 企業詳細

`get_detail()` は 1 リクエストで基本情報・適時開示・縦覧書類・CG情報の全タブを取得します。

```python
from tse_hp_front import TseClient

with TseClient() as client:
    detail = client.get_detail("6758")  # ソニーグループ
```

### 基本情報タブ

```python
b = detail.basic
print(b.code)                # 67580
print(b.isin)                # JP3435000009
print(b.name)                # ソニーグループ
print(b.name_en)             # Sony Group Corporation
print(b.market)              # プライム
print(b.industry)            # 電気機器
print(b.fiscal_period)       # 3月
print(b.headquarters)        # 東京
print(b.representative_name) # 十時　裕樹
print(b.listing_date)        # 1958/12/01
print(b.stock_price_url)     # 株価情報URL
```

### 適時開示情報タブ

法定開示・決算情報・決定事実/発生事実・その他のカテゴリ別に取得できます。

```python
disc = detail.disclosures
print(len(disc.legal))           # 法定開示
print(len(disc.earnings))        # 決算情報
print(len(disc.material_facts))  # 決定事実/発生事実
print(len(disc.other))           # その他

for item in disc.earnings[:3]:
    print(item.date, item.title)
    print(item.pdf_url)          # PDF ダウンロード URL
    print(item.xbrl_url)         # XBRL ダウンロード URL
    print(item.html_urls)        # HTML 版 URL 一覧
```

### 縦覧書類 / PR情報タブ

```python
fil = detail.filings
print(len(fil.shareholder_meeting))   # 株主総会招集通知
print(len(fil.independent_officers))  # 独立役員届出書
print(len(fil.articles))             # 定款
print(len(fil.esg))                  # ESG 報告書
print(len(fil.pr))                   # PR 情報

for item in fil.articles:
    print(item.date, item.title, item.pdf_url)
```

### コーポレート・ガバナンス情報タブ

過去の CG 報告書を世代別に取得できます。

```python
for cg in detail.cg_info:
    print(cg.organization_type)     # 組織形態（指名委 / 監査委 / 監査役）
    print(cg.directors)             # 取締役（独立社外）
    print(cg.viewing_date)          # 縦覧日
    print(cg.pdf_url)               # CG 報告書 PDF
    print(cg.html_url)              # CG 報告書 HTML
    print(cg.xbrl_url)              # CG 報告書 XBRL
```

## CG 検索

`search_cg()` はコーポレート・ガバナンス情報サービスの全検索条件（75以上のパラメータ）に対応します。

### 基本検索

```python
from tse_hp_front import TseClient, Market

with TseClient() as client:
    result = client.search_cg(name="トヨタ")
    print(result.total)           # 該当件数
    print(result.detailed_total)  # 詳細条件該当件数

    for item in result.items:
        print(item.code, item.name)
        print(item.organization_type)          # 組織形態
        print(item.directors_count)            # 取締役数
        print(item.independent_directors_count) # 独立社外取締役数
        print(item.major_shareholder_name)     # 筆頭株主
        print(item.major_shareholder_ratio)    # 筆頭株主比率
        print(item.viewing_date)               # 縦覧日
        print(item.pdf_url)                    # CG 報告書 PDF
        print(item.html_url)                   # CG 報告書 HTML
        print(item.xbrl_url)                   # CG 報告書 XBRL
```

### 組織形態・資本構成

```python
from tse_hp_front import (
    TseClient, OrganizationType, ForeignOwnershipFrom,
    ForeignOwnershipTo, ParentCompanyStatus,
)

with TseClient() as client:
    result = client.search_cg(
        organization_type=OrganizationType.指名委員会等設置会社,
        foreign_ownership_from=ForeignOwnershipFrom.PCT_20,
        foreign_ownership_to=ForeignOwnershipTo.PCT_30,
        controlling_shareholder=True,
        parent_company=ParentCompanyStatus.有_上場,
        parent_company_code="7203",
    )
```

### 取締役・監査役

人数レンジ、任期、社外役員属性、独立役員の関係で検索できます。

```python
from tse_hp_front import (
    TseClient, Market, DirectorTenure,
    OutsideOfficerAttribute, RelationPeriod, OutsideDirectorRelation,
)

with TseClient() as client:
    result = client.search_cg(
        markets=[Market.プライム],
        # 取締役
        director_tenure=DirectorTenure.一年,
        directors_from=5,
        directors_to=15,
        outside_directors_from=3,
        independent_directors_from=3,
        # 社外取締役の属性
        outside_director_attributes=[
            OutsideOfficerAttribute.弁護士,
            OutsideOfficerAttribute.公認会計士,
        ],
        # 社外取締役の関係
        outside_director_relation_period=RelationPeriod.本人現在,
        outside_director_relations=[
            OutsideDirectorRelation.F,  # コンサルタント、会計専門家、法律専門家
            OutsideDirectorRelation.G,  # 主要株主
        ],
        # 監査役
        auditors_from=3,
        outside_auditors_from=2,
        independent_auditors_from=2,
    )
```

### 委員会・その他

指名委員会等設置会社、監査等委員会設置会社、任意の委員会の委員数や、報酬開示・買収防衛策なども検索条件に指定できます。

```python
from datetime import date
from tse_hp_front import TseClient, CompensationDisclosure

with TseClient() as client:
    result = client.search_cg(
        # 指名委員会等設置会社 の委員数
        nomination_committee_from=3,
        compensation_committee_from=3,
        audit_committee_from=3,
        executive_officers_from=5,
        # 任意の委員会
        optional_committee_exists=True,
        # その他
        independent_officers_from=5,
        advisor_status_exists=True,
        advisor_count_from=1,
        electronic_voting=True,
        voting_platform=True,
        english_notice=True,
        director_compensation_disclosure=[CompensationDisclosure.全員個別開示],
        compensation_policy=True,
        takeover_defense=False,
        # 縦覧日
        viewing_date_from=date(2024, 1, 1),
        viewing_date_to=date(2024, 12, 31),
        # 英訳版 CG 報告書
        english_cg_report=True,
    )
```

## 日本語 Enum

すべての Enum は日本語名で定義されています。IDE の補完で直感的に指定できます。

```python
from tse_hp_front import Market, Prefecture, Industry, OrganizationType

Market.プライム          # "011"
Market.スタンダード      # "012"
Market.グロース          # "013"

Prefecture.東京          # "13"
Prefecture.大阪          # "27"
Prefecture.愛知          # "23"

Industry.電気機器        # "3650"
Industry.医薬品          # "3250"
Industry.情報_通信業     # "5250"
Industry.銀行業          # "7050"

OrganizationType.監査役設置会社      # "1"
OrganizationType.指名委員会等設置会社 # "2"
OrganizationType.監査等委員会設置会社 # "3"
```

全 Enum 一覧:

| Enum | 用途 | 値の例 |
|:---|:---|:---|
| `Market` | 市場区分（12種） | `プライム`, `スタンダード`, `グロース`, `ETF`, `REIT` |
| `Prefecture` | 都道府県（47種） | `北海道`, `東京`, `大阪`, `沖縄` |
| `Industry` | 業種分類（35種） | `建設業`, `化学`, `機械`, `電気機器`, `銀行業` |
| `AnnouncementType` | 決算発表種別（4種） | `決算`, `第一四半期`, `第二四半期`, `第三四半期` |
| `OrganizationType` | 組織形態（3種） | `監査役設置会社`, `指名委員会等設置会社`, `監査等委員会設置会社` |
| `ForeignOwnershipFrom` | 外国人所有比率 下限（4種） | `PCT_0`, `PCT_10`, `PCT_20`, `PCT_30` |
| `ForeignOwnershipTo` | 外国人所有比率 上限（3種） | `PCT_10`, `PCT_20`, `PCT_30` |
| `ParentCompanyStatus` | 親会社有無（4種） | `有`, `有_上場`, `有_非上場`, `無` |
| `DirectorTenure` | 取締役任期（2種） | `一年`, `二年` |
| `RelationPeriod` | 社外役員の関係 期間（4種） | `本人現在`, `本人過去`, `近親者現在`, `近親者過去` |
| `OutsideOfficerAttribute` | 社外役員属性（6種） | `他会社出身`, `弁護士`, `公認会計士`, `税理士`, `学者`, `その他` |
| `OutsideDirectorRelation` | 社外取締役の関係（11種） | `A`〜`K` |
| `OutsideAuditorRelation` | 社外監査役の関係（13種） | `A`〜`M` |
| `CompensationDisclosure` | 報酬開示状況（3種） | `全員個別開示`, `一部個別開示`, `個別開示なし` |

## 非同期クライアント

`AsyncTseClient` をインポートし、`await` を付けるだけです。API は同期版と同一です。

```python
import asyncio
from tse_hp_front import AsyncTseClient, Market

async def main():
    async with AsyncTseClient() as client:
        result = await client.search(name="トヨタ")
        for item in result.items:
            print(item.code, item.name)

        detail = await client.get_detail("7203")
        print(detail.basic.name)

        cg = await client.search_cg(markets=[Market.プライム], limit=10)
        print(cg.total)

asyncio.run(main())
```

## HTTP リソースの管理

コンテキストマネージャを使用して HTTP 接続を解放します。

```python
from tse_hp_front import TseClient

# コンテキストマネージャ（推奨）
with TseClient() as client:
    result = client.search(name="トヨタ")

# 手動クローズ
client = TseClient()
try:
    result = client.search(name="トヨタ")
finally:
    client.close()
```

非同期版:

```python
from tse_hp_front import AsyncTseClient

async with AsyncTseClient() as client:
    ...

# または
client = AsyncTseClient()
try:
    ...
finally:
    await client.close()
```

## タイムアウト

デフォルトのタイムアウトは 30 秒です。

```python
from tse_hp_front import TseClient

client = TseClient(timeout=60.0)  # 60 秒に変更
```

## データモデル

### 検索結果

| クラス | 用途 |
|:---|:---|
| `CompanySearchResult` | `search()` の戻り値。`total`（件数）と `items`（`SearchResultItem` リスト） |
| `SearchResultItem` | 検索結果 1 行。`code`, `name`, `market`, `industry`, `fiscal_period`, `has_notice`, `stock_price_url` |
| `CGSearchResult` | `search_cg()` の戻り値。`total`, `detailed_total`, `items`（`CGSearchResultItem` リスト） |
| `CGSearchResultItem` | CG 検索結果 1 行。`code`, `name`, `organization_type`, `directors_count`, `independent_directors_count`, `viewing_date`, `pdf_url`, `html_url`, `xbrl_url` 等 |

### 企業詳細

| クラス | 用途 |
|:---|:---|
| `CompanyDetail` | `get_detail()` の戻り値。全タブを統合 |
| `CompanyBasicInfo` | 基本情報タブ。コード、ISIN、市場、業種、決算期、代表者、本社所在地 等 25 フィールド |
| `DisclosureSection` | 適時開示情報タブ。`legal`, `earnings`, `material_facts`, `compliance_plan`, `other` |
| `DisclosureItem` | 開示 1 行。`date`, `title`, `pdf_url`, `xbrl_url`, `html_urls` |
| `FilingSection` | 縦覧書類タブ。`shareholder_meeting`, `independent_officers`, `articles`, `esg`, `pr`, `other` |
| `FilingItem` | 縦覧 1 行。`date`, `title`, `pdf_url` |
| `CGInfoItem` | CG 情報タブ 1 行。`organization_type`, `directors`, `auditors`, `viewing_date`, `pdf_url`, `html_url`, `xbrl_url` |

## 注意事項

- 本ライブラリは東証の公開 Web ページをスクレイピングしています。サイト構造の変更により動作しなくなる可能性があります。
- 完全に条件を指定しない空検索（名前・コード・市場すべて未指定）はサーバー側の仕様により結果が返りません。最低 1 つの条件を指定してください。
- 高頻度アクセスはサーバーに負荷をかけるため、適切な間隔をあけてご利用ください。

## 動作要件

Python 3.12 以上。
