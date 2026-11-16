# 発展課題：SWE-bench Verifiedの問題読解ノート

調査日：2026年11月16日（Asia/Taipei）。SWE-bench Verifiedの5件について、問題文・公開修正・追加テストを読解した。

作成・検証・採点の方法と講義との比較は[提出用回答の発展節](../answer.md#発展)に記録した。このノートでは、読んだ問題の難しさと解く見通しを補足する。

## データと選び方

[公式データセット](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)の500件を、固定リビジョン `78f471bf655a3137b2e8a75af1501690ec009ec3` で読み取った。5つのリポジトリから、それぞれ収録順で最初の1件を選んだ。異なる領域を見るための目的抽出であり、無作為標本ではない。

問題文と公開修正をAIを用いて整理し、修正に取り組む場合の見通しを以下に記録した。公開修正を参照した読解であり、初見での解答や修正の実装・実行は行っていない。登録難度は、経験ある開発者が問題を理解して実装する時間の推定ラベルである。

## 1. astropy__astropy-12907

- 元の問題：[公開issue](https://github.com/astropy/astropy/issues/12906)／[修正PR](https://github.com/astropy/astropy/pull/12907)
- データ上の位置：[testの行0](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/viewer/default/test?row=0)。ビューアーは現行版のため、参照した版は上記SHAで識別する。
- 収録難度：`15 min - 1 hour`。

**問題の要約**：複合モデルを入れ子にすると、本来独立な入出力まで依存しているような行列になる。

**期待する振る舞い**：同じモデルの結合を平坦に書いた場合と入れ子に書いた場合で、入出力の独立性が保たれること。

**難しさ**：数値結果だけでなく依存関係の行列、モデル結合演算と再帰的な部分行列の扱いを理解する必要がある。

**解く見通し**：依存行列を手で追えば原因の候補は考えられる。公開修正も参照したため初見で解けるという判定ではなく、Astropy内部での一般性の検証は未実施。

**テストを読んで分かったこと**：追加テストは複数の括り方と入れ子の深さを扱い、同じ独立性を保てるかを確認する。単一の出力例への対応だけでは足りない。

## 2. django__django-10097

- 元の問題：[公開issue](https://code.djangoproject.com/ticket/29528)／[修正PR](https://github.com/django/django/pull/10097)
- データ上の位置：[testの行22](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/viewer/default/test?row=22)。ビューアーは現行版のため、参照した版は上記SHAで識別する。
- 収録難度：`<15 min fix`。

**問題の要約**：URLの認証情報に未エスケープの区切り文字があっても、URLValidatorが不正なURLを受理する。

**期待する振る舞い**：ユーザー名・パスワード部分の不正な文字を拒否しつつ、正当なURLや既存の検証を壊さないこと。

**難しさ**：正規表現の小さな変更でも、認証部・ホスト・パス・クエリの解釈と既存の有効な入力との整合が必要になる。

**解く見通し**：問題文から要件は追える。修正量の小ささだけで容易とはせず、URL文法と既存テストの理解が必要。実装・動作検証はしていない。

**テストを読んで分かったこと**：追加された不正URLだけでなく、以前は有効とされていた例の期待値も変更される。今回のテスト登録数は実行数ではなくデータセット列の値として扱う。

## 3. pytest-dev__pytest-10051

- 元の問題：[公開issue](https://github.com/pytest-dev/pytest/issues/9877)／[修正PR](https://github.com/pytest-dev/pytest/pull/10051)
- データ上の位置：[testの行330](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/viewer/default/test?row=330)。ビューアーは現行版のため、参照した版は上記SHAで識別する。
- 収録難度：`15 min - 1 hour`。

**問題の要約**：caplog.clearの後、段階別ログを得るget_recordsと現在のrecordsが食い違い、以後のログも反映されない。

**期待する振る舞い**：call段階のログを消し、その後の追加も両方から見え、setup段階のログは残ること。

**難しさ**：リストの中身を消す操作と新しいリストへの置換、別オブジェクトが保持する参照、fixtureの段階管理を追う必要がある。

**解く見通し**：Pythonの参照の違いから原因仮説は立てられる。pytest内部の状態管理と別段階への影響はテストで確認する必要があり、今回は未実行。

**テストを読んで分かったこと**：消去直後だけでなく、新しいログの追加とsetupログの維持も確認する。直ったように見える一瞬の状態だけで採点しない。

## 4. scikit-learn__scikit-learn-10297

- 元の問題：[公開issue](https://github.com/scikit-learn/scikit-learn/issues/10284)／[修正PR](https://github.com/scikit-learn/scikit-learn/pull/10297)
- データ上の位置：[testの行349](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/viewer/default/test?row=349)。ビューアーは現行版のため、参照した版は上記SHAで識別する。
- 収録難度：`15 min - 1 hour`。

**問題の要約**：RidgeClassifierCVが、文書に示されるstore_cv_values引数を受け取れずTypeErrorになる。

**期待する振る舞い**：引数を受け取り基底クラスへ伝え、学習後に交差検証値を適切な形で保持すること。

**難しさ**：コンストラクタの引数追加に加え、継承先への伝達、単一・複数出力での配列形状、公開APIと文書の整合が必要。

**解く見通し**：引数の伝達漏れという修正方針は考えられるが、分類器の内部処理と配列形状の検証なしには正しいとは言えない。今回は読解のみ。

**テストを読んで分かったこと**：追加テストは引数が通るかだけでなく、単一・複数の分類出力に対するcv_values_の形を確認する。

## 5. sympy__sympy-11618

- 元の問題：[公開issue](https://github.com/sympy/sympy/issues/11617)／[修正PR](https://github.com/sympy/sympy/pull/11618)
- データ上の位置：[testの行425](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/viewer/default/test?row=425)。ビューアーは現行版のため、参照した版は上記SHAで識別する。
- 収録難度：`15 min - 1 hour`。

**問題の要約**：2次元の点と3次元の点の距離で、短い側に合わせた計算により第3座標が無視される。

**期待する振る舞い**：欠けた座標を0として扱い、例の距離が1ではなく√5となること。

**難しさ**：数学的には単純でも、次元の異なるPointの型や引数、既存の距離計算と整合させる必要がある。

**解く見通し**：zipが短い列で止まる性質から原因は理解しやすい。逆向きの引数や別入力への一般性は未検証で、解決済みとはしない。

**テストを読んで分かったこと**：追加テストの例は3Dの点から2Dの点への距離が√5になることを確認する。1つの例の通過と、すべての入力での正しさを区別する。

## 読解から得たこと

変更行数の少なさだけでは難しさは分からない。依存関係、参照の共有、入力の次元、公開APIなど、コードベースの前提を理解し、修正後も既存機能を維持する必要がある。

今回はDjangoが15分未満、他4件が15分〜1時間のラベルで、1時間以上の課題は読んでいない。5件から500件全体の難しさを一般化しない。

データ内のFAIL_TO_PASS／PASS_TO_PASSの件数は、登録された識別子の数であり、今回実行して確認したテスト数ではない。特にDjango行には広い範囲のテスト名が収録されており、件数だけからテストの妥当性を推測しない。

品質確認者は、解答者に渡される情報だけで要件が分かるか、テストが特定の実装だけを正解にしていないかを検討する。[公開された注釈指示](https://cdn.openai.com/introducing-swe-bench-verified/swe-b-annotation-instructions.pdf)は、この点を具体的に確認できる資料だった。

また、[2026年の監査](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)が示すように、作成時の人手検証は将来にわたる完全性の保証ではない。問題とテストの版、評価環境、モデルが訓練中に答えを見た可能性まで考慮する必要がある。

## 参照資料

- [ケースの要約とメタデータ](cases_reviewed.json)：元の問題全文や修正全文は含めず、対象の識別子・要約・原フィールドのハッシュを保存。
- [版とデータファイルのハッシュ](dataset_snapshot.json)：参照した公開Parquetを同定。
- [元PRとの照合](pull_request_checks.json)：各課題の修正前コミットを確認。
- [一次資料一覧](sources.json)：方法・採点・限界を確認した文書。
- [確認結果](validation.json)：収録件数、版、5件の所属、原フィールドと各資料のハッシュを照合。
