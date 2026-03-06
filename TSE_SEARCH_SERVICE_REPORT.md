# 東証検索サービス 仕様調査レポート

## 1. 概要

東京証券取引所（JPX）は以下の2つの検索サービスを `www2.jpx.co.jp` 上で提供している。

| サービス | URL | 目的 |
|---------|-----|------|
| **東証上場会社情報サービス (JJK)** | `/tseHpFront/JJK010010Action.do?Show=Show` | 上場会社の基本情報・開示情報・株価の検索 |
| **コーポレート・ガバナンス情報サービス (CGK)** | `/tseHpFront/CGK010010Action.do?Show=Show` | CG報告書・ガバナンス属性の検索 |

---

## 2. 技術スタック

| 項目 | 値 |
|------|-----|
| **Webサーバー** | Cosminexus HTTP Server（日立製作所のJava EEアプリケーションサーバー） |
| **フレームワーク** | Java Servlet/Struts系（`.do` アクション URL、フォーム Bean パターン） |
| **セッション管理** | JSESSIONID（Cookie + URL Rewriting） |
| **文字エンコーディング** | `Content-Type: text/html;charset=utf-8`（レスポンス）、CSSは `charset=shift_jis` |
| **HTML仕様** | XHTML 1.0 Transitional |
| **CSS** | 独自CSS（`HPLCDS_import_listed.css`, `HPLCDS_listed.css`） |
| **JavaScript** | Vanilla JS（フレームワークなし、jQuery等不使用） |
| **robots.txt** | **存在しない**（404）— クローリングの明示的制限なし |
| **Cache-Control** | `private` — キャッシュ不可 |
| **Cookie** | `JSESSIONID`（Secure, Path=/tseHpFront）、`mi-w1-pri`（ロードバランサ振り分け用） |

---

## 3. 画面遷移とアクション体系

### 3.1 JJK（上場会社情報サービス）

```
JJK010010Action.do  ← 検索条件入力（簡易/詳細）
    ↓ POST (ListShow)
JJK010030Action.do  ← 検索結果一覧
    ↓ POST (BaseJh)
JJK010040Action.do  ← 会社詳細（4タブ: 基本情報/適時開示/CG情報/縦覧書類）
```

### 3.2 CGK（CG情報サービス）

```
CGK010010Action.do  ← 検索条件入力
    ↓ POST (ListShow)
CGK010030Action.do  ← 検索結果一覧（PDF/HTMLリンク付き）
```

---

## 4. セッション管理の仕組み

### 重要：2段階アクセスが必須

1. **初回GET**で検索フォームを取得し、`JSESSIONID` を受け取る
2. **同一セッション**でPOSTリクエストを送信する

```
GET  /tseHpFront/JJK010010Action.do?Show=Show
     → Set-Cookie: JSESSIONID=xxxx; Path=/tseHpFront; Secure
     → formのaction属性にもjsessionidが埋め込まれる

POST /tseHpFront/JJK010010Action.do;jsessionid=xxxx
     Cookie: JSESSIONID=xxxx
     → セッションが一致しない場合、検索フォームに戻される
```

### URL Rewriting

- formの `action` 属性にはサーバーサイドで `jsessionid` が埋め込まれる
- 例: `action="/tseHpFront/JJK010010Action.do;jsessionid=00BE75A05A..."`
- Cookie送信と併用推奨

---

## 5. JJK フォーム仕様

### 5.1 フォーム定義

| 属性 | 値 |
|------|-----|
| フォーム名 | `JJK010010Form` |
| method | `POST` |
| action | `/tseHpFront/JJK010010Action.do;jsessionid=xxx` |

### 5.2 検索パラメータ（簡易検索）

| パラメータ名 | 型 | 説明 | 必須 | 値の例 |
|-------------|-----|------|------|--------|
| `ListShow` | hidden | イベントID（検索実行） | **必須** | `ListShow` |
| `dspSsuPd` | select | 表示件数 | 任意 | `10`, `50`, `100`, `200` |
| `mgrMiTxtBx` | text | 銘柄名（会社名） | 任意 | 部分一致検索 `maxlength=150` |
| `eqMgrCd` | text | 証券コード | 任意 | `7203` `maxlength=5` |
| `szkbuChkbx` | checkbox[] | 市場区分（複数選択可） | 任意 | 下表参照 |
| `jjHisiKbnChkbx` | checkbox | 上場廃止会社検索 | 任意 | `on` |

### 5.3 市場区分コード

| value | 市場 |
|-------|------|
| `011` | プライム |
| `012` | スタンダード |
| `013` | グロース |
| `008` | TOKYO PRO Market |
| `111` | 外国株プライム |
| `112` | 外国株スタンダード |
| `113` | 外国株グロース |
| `ETF` | ETF |
| `ETN` | ETN |
| `RET` | 不動産投資信託(REIT) |
| `IFD` | インフラファンド |
| `999` | その他 |

### 5.4 Hidden フィールド（イベント制御）

| name | value | 説明 |
|------|-------|------|
| `Show` | `Show` | 初期表示イベント（disabled） |
| `ListShow` | `ListShow` | 検索実行イベント（disabled→JS有効化） |
| `Switch` | `Switch` | 簡易/詳細タブ切替イベント（disabled） |
| `sniMtGmnId` | 空 | 遷移元画面ID |

### 5.5 フォーム送信メカニズム

```javascript
// 共通関数 (TWJ_Common.js)
function submitPage(obj, eventObj, action) {
    eventObj.disabled = false;  // disabled解除してイベントIDを送信可能に
    obj.submit();
    eventObj.disabled = true;   // 送信後に再度disabled
}

// 検索ボタン onclick
submitPage(
    document.forms['JJK010010Form'],
    document.forms['JJK010010Form'].ListShow
);
```

**ポイント**: Hidden フィールドは通常 `disabled` 状態。JSが `disabled=false` にしてから submit するため、プログラムからは明示的に送信する必要がある。

---

## 6. JJK 検索結果（JJK010030）

### 6.1 結果ページ構造

結果ページのフォーム名は `JJK010030Form`。以下の情報を含む：

| カラム | 対応hidden name |
|--------|----------------|
| コード | `ccJjCrpSelKekkLst_st[N].eqMgrCd` |
| 銘柄名 | `ccJjCrpSelKekkLst_st[N].eqMgrNm` |
| 市場区分 | `ccJjCrpSelKekkLst_st[N].szkbuNm` |
| 業種分類 | `ccJjCrpSelKekkLst_st[N].gyshDspNm` |
| 決算期 | `ccJjCrpSelKekkLst_st[N].dspYuKssnKi` |

### 6.2 ページング制御

| パラメータ | 説明 |
|-----------|------|
| `lstDspPg` | 現在ページ番号 |
| `dspGs` | 表示行数 |
| `souKnsu` | 総件数 |
| `dspJnKbn` | ソート順（0:昇順, 1:降順） |
| `dspJnKmkNo` | ソート項目番号（0:コード, 1:市場区分, 2:業種, 3:決算期） |

### 6.3 詳細ページ遷移

```javascript
// 基本情報詳細へ遷移
function gotoBaseJh(code, jjhsFlg) {
    document.forms['JJK010030Form'].mgrCd.value = code;    // 例: '72030'
    document.forms['JJK010030Form'].jjHisiFlg.value = jjhsFlg;
    submitPage(..., BaseJh);
}
```

**注意**: 証券コードは5桁（末尾にチェックディジット `0` が付く）。例：`7203` → `72030`

---

## 7. JJK 詳細ページ（JJK010040）

405KB の大型ページ。4つのタブを含む（クライアントサイドの `display:none/block` 切替）。

### タブ構成

| タブID | セクション | div ID |
|--------|----------|--------|
| 1 | 基本情報 | `body_basicInformation` |
| 2 | 適時開示情報 | `body_disclosure` |
| 3 | CG情報 | `body_CorporateGovernance` |
| 4 | 縦覧書類 / PR情報 | `body_filing` |

### 基本情報で取得可能なデータ

- コード、ISINコード、銘柄名、英文商号
- 業種、決算期、売買単位
- 株主名簿管理人、設立年月日、本社所在地
- 上場取引所、月末投資単位
- 決算発表予定日、株主総会開催日
- 代表者（役職・氏名）
- **株価表示リンク**: `https://quote.jpx.co.jp/jpxhp/main/index.aspx?F=stock_detail&disptype=information&qcode=7203`

### 開示書類リンク

- PDF: `/disc/{コード}/{文書ID}.pdf`
- HTML: `/disc/{コード}/{文書ID}.html`
- XBRL: `doDownload()` 関数経由でダウンロード

---

## 8. CGK フォーム仕様

### 8.1 フォーム定義

| 属性 | 値 |
|------|-----|
| フォーム名 | `CGK010010Form` |
| method | `POST` |
| action | `/tseHpFront/CGK010010Action.do;jsessionid=xxx` |

### 8.2 検索パラメータ一覧

CGKは非常に多くの検索条件を持つ。以下にカテゴリ別に整理する。

#### 会社属性情報（第一次検索でのみ設定可能 — 赤字項目）

| パラメータ名 | 型 | 説明 |
|-------------|-----|------|
| `mgrMiTxtBx` | text | 銘柄名（会社名） |
| `eqMgrCd` | text | コード |
| `hnsShzitPd` | select | 本社所在地（`01`〜`47` 都道府県コード） |
| `szkbuChkbx` | checkbox[] | 市場区分（`011`:プライム, `012`:スタンダード, `013`:グロース） |
| `gyshBnriPd` | select | 業種分類（`0050`〜`9999`、33分類） |
| `bibiTniPd` | select | 売買単位（`1`,`10`,`50`,`100`,`500`,`1000`,`3000`,`-1`） |
| `kssnKiPd` | select | 決算期（`01`〜`12`） |

#### 組織形態・資本構成等

| パラメータ名 | 型 | 説明 | 値 |
|-------------|-----|------|-----|
| `sskKitiPd` | select | 組織形態 | `1`:監査役設置, `2`:指名委員会等, `3`:監査等委員会 |
| `gikkNnEqSyuHrtFrmPd` | select | 外国人株式所有比率（下限） | `1`:0%〜, `2`:10%〜, `3`:20%〜, `4`:30%〜 |
| `gikkNnEqSyuHrtToPd` | select | 外国人株式所有比率（上限） | `1`:〜10%, `2`:〜20%, `3`:〜30% |
| `shiEqnsUmPd` | select | 支配株主の有無 | `1`:有, `0`:無 |
| `oyaCrpUmPd` | select | 親会社有無 | `3`:有, `1`:有(上場), `2`:有(非上場), `0`:無 |
| `oyaCrpCd` | text | 親会社のコード |

#### 取締役関係（範囲指定: XxxFrmTxtBx ～ XxxToTxtBx）

| パラメータ名 | 説明 |
|-------------|------|
| `tiknJoTrshmrykIzuFrm/ToTxtBx` | 定款上の取締役員数 |
| `tiknJoTrshmrykNnkPd` | 定款上の取締役任期（`1`:1年, `2`:2年） |
| `tsynzFrm/ToTxtBx` | 取締役人数 |
| `sgiTsynzFrm/ToTxtBx` | 社外取締役人数 |
| `sgiTrshmrykDryiNzuFrm/ToTxtBx` | 社外取締役（独立役員）人数 |
| `sgiTrshmrykZksi1〜6Chkbx` | 社外取締役属性（6種） |
| `sgiTrshmrykKnkiPd` | 社外取締役の関係（`01`〜`04`） |
| `snYuskSgiTrshmrykKnki1〜11Chkbx` | 社外取締役関係の詳細（a〜k） |

#### 監査役関係

| パラメータ名 | 説明 |
|-------------|------|
| `tiknJoKsykIzuFrm/ToTxtBx` | 定款上の監査役員数 |
| `ksykNzuFrm/ToTxtBx` | 監査役人数 |
| `sgiKsykNzuFrm/ToTxtBx` | 社外監査役人数 |
| `sgiKsykDryiNzuFrm/ToTxtBx` | 社外監査役（独立役員）人数 |
| `sgiKsykZksi1〜6Chkbx` | 社外監査役属性（6種） |
| `sgiKsykKnkiPd` | 社外監査役の関係 |
| `snYuskSgiKsykKnki1〜13Chkbx` | 社外監査役関係の詳細（a〜m） |

#### その他ガバナンス指標

| パラメータ名 | 説明 | 値 |
|-------------|------|-----|
| `dryiNzuFrm/ToTxtBx` | 独立役員人数 |
| `sdnykkmnUmPd` | 相談役・顧問の有無 | `1`:有, `0`:無 |
| `sdnykkmnNzuFrm/ToTxtBx` | 相談役・顧問の人数 |
| `dnjTekiGktKnKsPd` | 電磁的方法による議決権行使 | `1`:導入, `0`:非導入 |
| `gkkdsksBrtfmPd` | 議決権行使プラットフォーム | `1`:有, `0`:無 |
| `sstcyyEibnTikyPd` | 招集通知英文提供 | `1`:有, `0`:無 |
| `kttiHusnPd` | 買収防衛策 | `1`:有, `0`:無 |
| `bsbesDunuPd` | 報酬方針の有無 | `1`:有, `0`:無 |
| `smiHsuStNniIikiUmPd` | 任意の委員会の有無 | `1`:有, `0`:無 |

#### 日付範囲

| パラメータ名 | 説明 |
|-------------|------|
| `jhUpdDayFrmYearPd` / `jhUpdDayToYearPd` | 縦覧日（年）: `2020`〜`2027` |
| `jhUpdDayFrmTskPd` / `jhUpdDayToTskPd` | 縦覧日（月）: `01`〜`12` |
| `jhUpdDayFrmDayPd` / `jhUpdDayToDayPd` | 縦覧日（日）: `01`〜`31` |

### 8.3 CGK特有のフォーム送信メカニズム

```javascript
// 全フィールドを有効化してから送信
function submitCG() {
    var elements = document.forms['CGK010010Form'].elements;
    // 会社属性フィールドを有効化
    elements['mgrMiTxtBx'].disabled = false;
    elements['eqMgrCd'].disabled = false;
    // ... 全select/text/checkboxを有効化
    for(var i=0; i<elements.length; i++) {
        if (elements[i].type=='text' || elements[i].type=='checkbox' ||
            (elements[i].type=='select-one' && elements[i].name!='dspSsuPd')) {
            elements[i].disabled = false;
        }
    }
    submitPage(document.forms['CGK010010Form'],
               document.forms['CGK010010Form'].ListShow);
}
```

### 8.4 CGK 絞り込み検索

- `SearchFromResults` イベント: 検索結果からの二次絞り込み
- `sbrkmFlg`: 絞り込みフラグ（`1`）
- `jyuKmkAti1`: disabled化された項目名の集合（カンマ区切り）
- **制約**: 会社属性情報（赤字項目）は第一次検索でのみ設定可能

### 8.5 CGK 検索結果のリンク

結果には直接的なPDF/HTMLリンクが含まれる:

```
PDF: /disc/{コード}/{文書ID}.pdf
HTML: /disc/{コード}/{文書ID}.html
```

---

## 9. プログラムからの利用手順

### 9.1 JJK検索の実装手順

```
1. GET  /tseHpFront/JJK010010Action.do?Show=Show
   → JSESSIONIDをCookieから取得
   → formのaction URLからjsessionidも取得

2. POST /tseHpFront/JJK010010Action.do;jsessionid=xxx
   Cookie: JSESSIONID=xxx
   Content-Type: application/x-www-form-urlencoded
   Body: ListShow=ListShow&eqMgrCd=7203&mgrMiTxtBx=&dspSsuPd=10
   → 検索結果HTML（JJK010030）を取得

3. POST /tseHpFront/JJK010030Action.do
   Cookie: JSESSIONID=xxx
   Body: BaseJh=BaseJh&mgrCd=72030&jjHisiFlg=1&lstDspPg=1&dspGs=10
         &souKnsu=1&sniMtGmnId=JJK010010&dspJnKbn=0&dspJnKmkNo=0
   → 詳細HTML（JJK010040）を取得（~400KB）
```

### 9.2 CGK検索の実装手順

```
1. GET  /tseHpFront/CGK010010Action.do?Show=Show
   → JSESSIONID取得

2. POST /tseHpFront/CGK010010Action.do;jsessionid=xxx
   Cookie: JSESSIONID=xxx
   Body: （全フィールド送信が必要 — 空のselect/textフィールドも含む）
   最低限必要なパラメータ:
     ListShow=ListShow
     eqMgrCd=7203
     mgrMiTxtBx=
     dspSsuPd=10
     hnsShzitPd= (空白)
     gyshBnriPd= (空白)
     bibiTniPd= (空白)
     kssnKiPd= (空白)
     sskKitiPd= (空白)
     ... (全select-one: 空白, 全TxtBx: 空文字列)
     sbrkmFlg=1
     souKnsu=0
     jyuKmkAti1=
     sgiTrshmrykKnkiPd=01
     sgiKsykKnkiPd=01
   → 検索結果HTML
```

**CGKの注意点**: JJKと異なり、CGKは**全フォームフィールド**を送信しないと検索フォームに戻される。空値のselectは半角スペースで送信する。

---

## 10. 検証済みの動作確認結果

| テスト項目 | 結果 |
|-----------|------|
| JJK: コード検索（7203→トヨタ自動車） | **成功** — 正常に結果取得 |
| JJK: 詳細ページ取得 | **成功** — 405KB、4タブ分のデータ取得 |
| CGK: コード検索（7203→トヨタ自動車） | **成功** — PDF/HTMLリンク付き結果取得 |
| セッション無効時の動作 | 検索フォームにリダイレクト（エラーなし） |
| 連続5リクエスト（レートリミット） | **制限なし** — 全て200 OK、応答150〜250ms |
| PDF直接アクセス | `/disc/72030/140120250721517384.pdf` 形式でアクセス可能 |

---

## 11. 制限事項と注意点

### 11.1 技術的制限

| 制限 | 詳細 |
|------|------|
| **セッション必須** | JSESSIONID なしではPOST検索不可 |
| **CGK全フィールド送信** | 空フィールドも含め全パラメータ送信が必要 |
| **MapOutフィールド** | 送信不要（サーバーサイドの表示用マッピング） |
| **コード5桁** | 内部では末尾にチェックディジット付き（例: `72030`） |
| **ページング** | 最大200件/ページ。`lstDspPg` と `souKnsu` で制御 |
| **ソート** | コード/市場区分/業種/決算期の4項目、昇順/降順 |

### 11.2 利用上の注意

- **robots.txt が存在しない**: 明示的なクローリング制限はないが、利用規約を確認すべき
- **データ利用注意事項**: https://www.jpx.co.jp/listing/co-search/01.html（JJK）、https://www.jpx.co.jp/listing/cg-search/index.html（CGK）を参照
- **SSL必須**: Cookie に `Secure` フラグが付与されており、HTTPS通信必須
- **ロードバランサ**: `mi-w1-pri` Cookieでサーバー振り分け。セッション継続にはこのCookieも保持推奨
- **レートリミット**: 連続リクエストでは確認されなかったが、大量アクセスには注意が必要

### 11.3 CGK固有の制約

- **会社属性情報（赤字項目）は第一次検索でのみ設定可能** — 絞り込み検索（二次検索）では変更不可
- `setReadOnly()` 関数でフィールドをdisabled化→`jyuKmkAti1` に記録

---

## 12. 共通JavaScriptファイル

| ファイル | 用途 |
|---------|------|
| `/common/js/TWJ_Common.js` | フォーム送信(`submitPage`)、タブ切替、ページング、PDF表示、XBRLダウンロード |
| `/common/js/verchk.js` | ブラウザバージョンチェック |
| `/common/js/default.js` | デフォルト初期化 |
| `/common/js/gnavi.js` | グローバルナビゲーション |
| `/common/js/page_1column01.js` | レイアウト制御 |

---

## 13. データ構造まとめ

### JJK 検索結果テーブルのカラム

| # | カラム | 幅 |
|---|-------|-----|
| 1 | コード | 63px |
| 2 | 銘柄名 | 275px |
| 3 | 市場区分 | 89px |
| 4 | 業種分類 | 126px |
| 5-6 | 決算期 | 64px |
| 7 | 注意情報等 | 63px |
| 8 | 基本情報（ボタン） | 80px |
| 9 | 株価表示（リンク） | 80px |

### JJK 詳細ページで取得可能な情報

- **基本情報**: コード、ISINコード、銘柄名、英文商号、業種、決算期（月日）、売買単位、株主名簿管理人、設立年月日、本社所在地、上場取引所、月末投資単位、決算発表予定日、株主総会開催日、代表者（役職・氏名）
- **適時開示情報**: 法定開示情報（有価証券報告書等）、適時開示情報の一覧（PDFリンク）
- **CG情報**: コーポレート・ガバナンス報告書（PDF/HTML/XBRLリンク）
- **縦覧書類 / PR情報**: 各種縦覧書類のリスト

### 開示書類URLパターン

```
PDF:  https://www2.jpx.co.jp/disc/{銘柄コード5桁}/{文書ID}.pdf
HTML: https://www2.jpx.co.jp/disc/{銘柄コード5桁}/{文書ID}.html
```

---

## 14. 推奨実装アプローチ

1. **HTTPクライアント**: Cookie管理対応のHTTPクライアントを使用（Python: `requests.Session()`, Node: `tough-cookie` + `axios` 等）
2. **HTMLパーサー**: テーブルデータの抽出に `cheerio`（Node）や `BeautifulSoup`（Python）を使用
3. **セッション管理**: 初回GETでセッション確立→Cookie自動管理
4. **エラーハンドリング**: セッション切れ時は再度初回GETからやり直す
5. **リクエスト間隔**: サーバー負荷軽減のため適切なディレイ（1〜2秒）を設定推奨
6. **CGK全フィールド送信**: 初回GETで取得したHTMLから全フィールド名を動的に抽出してPOSTに含めると堅牢
