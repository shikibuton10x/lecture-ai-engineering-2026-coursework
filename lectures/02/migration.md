# 第2回 提出用成果物の移行記録

## 日付と出典

- 元の実験実施日：**2026年11月2日（JST）**。Colab ProのTesla T4で実行したLoRA学習・評価の記録である。
- 正式forkへの移行日：**2026年11月3日（JST）**。保存済みファイルの移行と、CPUでの整合性確認を行った。今回の移行ではモデルAPIの呼び出し・推論・再学習を行っていない。
- 移行元：[旧提出先のPR #2](https://github.com/shikibuton10x/lecture-ai-engineering-2026-submission/pull/2)。マージコミットは `018670fd9ac5deeccbcc83b643ef6fc9e987bbc1`、直前のコミットは `112b0f8cf23e9585f4546ddd45c5f462866a1e03`。
- 実験コードの元コミット：`8f807bebbed72243eb460d0819b8fa8615e5164c`。当時のコード・入力のハッシュは [source_manifest.json](advanced/source_manifest.json) に記録されている。
- 移行先：[正式fork](https://github.com/shikibuton10x/lecture-ai-engineering-2026-coursework)。開始時のmainは `7fcbb7c5ff892bcce3c559c69172450ef6dfe6f5`、保持した本家由来の基準コミットは `fae899a409e2c99feee9d44a3789f936f5fc64ee`。

## 引き継いだ内容

元PRのLesson02差分を作業ブランチへ取り込み、[answer.md](answer.md)、データ、採点基準、全回答、比較表、学習ログ、実行環境、実行済みノートブックを引き継いだ。これらの実験値と原文は変更していない。移行に合わせて `advanced/README.md` と `.gitignore` を更新し、この記録とハッシュの一覧を追加した。

元PRではGit管理対象外だった最終adapterも、実験当日のバックアップ `20261102_colab_T4_glossary_sft.zip` から復元した。用語集SFT用は [advanced/adapter/](advanced/adapter/)、FAQ演習用は [advanced/faq_baseline/adapter/](advanced/faq_baseline/adapter/) にある。各重みは25,584,224バイトであり、設定・自動生成されたモデルカードも原本のまま保存した。中間チェックポイントとベースモデル本体は含めていない。

バックアップのSHA256は `cb6a7386e8de81bbb34e15af24d20657a87582630d71a073718a1c3f743aa259`。各ファイルの照合用ハッシュと移行元のファイル一覧は [migration_manifest.json](advanced/migration_manifest.json) を参照する。

## 本家の更新と実験当時の入力

現在の `data/glossary.json` は、本家でADKの説明が更新されている。学習当時の入力とは1項目の定義が異なるため、現在の用語集からデータを再生成すると、保存済みデータのSHA256とは一致しない。本家の用語集を古い内容で上書きせず、当時の入力とコードを [advanced/experiment_source/](advanced/experiment_source/) に保存した。

`source_manifest.json` の `source_sha256` にある5つの相対パスは、`advanced/experiment_source/` を基準にするとすべて一致する。そのうちコード4ファイルは移行先ルートの対応ファイルとも一致し、用語集だけが異なる。保存済みの学習・検証・評価データ自体は元PRと同一である。

実験ノートブックと実行済みノートブックは実行履歴として原本を保持した。用語集SFTノートブック内のclone先が旧提出先を参照し、当時のコミットに固定されているのはそのためである。今回のforkで再学習を行ったことを表すものではない。現在のルートのスクリプトを使って再実験する場合は、当時の入力を使うか、更新された教材による別実験として区別する必要がある。

## 検証範囲

移行前mainに含まれるLesson01の成果物と本家由来のファイルを保持したうえで、次を確認した。

- 既存pytest全体：**24件成功、35 subtests成功**。実モデルへのリクエストとネットワーク接続を無効化し、MCPはローカルのstdio接続で検証した。検証環境のキャッシュ制約には、テスト時だけ `uv` をoffline・no-syncで起動して対応した。
- 元PRの34ファイル中、README・`.gitignore` を除く**32ファイルが同一バイト列**。移行前mainのその他40ファイルも同一であり、Lesson01と本家の更新を保持している。
- データ4ファイルのSHA256が一致。当時のスナップショットを一時ディレクトリへコピーしてデータだけを再生成し、保存済みデータと同一になることも確認した。
- 保存済み140回答を同じルーブリックで再採点・集計し、4条件の13/35・24/35・30/35・27/35を再確認した。CSVの35行も回答原文と一致した。
- 復元した最終adapter2組はバックアップとSHA256が一致し、各192テンソル・6,389,760パラメータのsafetensors構造が正常だった。
- ノートブック4本をJSONとして確認し、保存済みのエラー出力は0件。公開差分のファイル名・テキストを検査し、APIキー形式の文字列・`.env`・個人学習用資料を含めていない。

adapterはバイト列と保存構造の検査までとし、今回の移行ではモデルをロードした推論による再評価は行っていない。
