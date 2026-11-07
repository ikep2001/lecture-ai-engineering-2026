# 第3回 解答

## 演習

### 素のLLMとエージェントの比較

質問：「AIE2026の講座の宿題にある3レベルとは？」

- 素のLLM：講座固有の情報を参照せず、一般的な習熟度分類を推測して回答した。
- エージェント：search_glossary(query="3レベル")を呼び出し、基礎・実装・発展の定義と、いずれか1つで完了することを回答した。
- LLM呼び出し：2回
- ツール呼び出し：1回

### ツール呼び出し

「LoRAとQLoRAの違いは？」に対して、

- search_glossary(query="LoRA")
- search_glossary(query="QLoRA")
- LLM呼び出し：2回
- ツール呼び出し：2回

### 追加ツール make_quiz

指定回の用語から確認問題を1件生成するツールを追加した。
docstringに用途と引数の意味を記述し、エージェントに登録した。
存在しない回のエラー処理も実装した。単体テスト2件PASS。

## 宿題

### 取り組んだレベル

基礎・実装・発展（Google ADK）。

### 基礎：指示文とdocstringの比較

同じ質問「LoRAとQLoRAの違いは？」で、変更箇所を1か所に限定して比較した。

| 指標 | Baseline | A: 必須検索指示を削除 | B: 複数用語検索を許容 |
|---|---:|---:|---:|
| ツール呼び出し回数 | 2 | 2 | 1 |
| LLM呼び出し回数 | 2 | 2 | 2 |
| 入力トークン数 | 1644 | 1596 | 1344 |
| API費用(USD) | 0.0009332 | 0.0009263 | 0.0009032 |

条件Aでは必須検索指示を削除しても2回の検索が残った。
条件Bではsearch_glossary(query="LoRA、QLoRA")を1回呼び出した。

検索結果を直接検査し、LoRAとQLoRAの両方が取得できることを確認した。
条件Bの入力トークン数はBaselineより18.2%少なかった。

各条件1回の探索的実験であり、効果の再現性や一般性は未検証。

### 実装：承認付き学習ログ

save_learning_log(topic, notes)を実装。
learning_log/にJSONで保存し、Git管理から除外した。

Pydantic AIのrequires_approval=Trueを使用し、
DeferredToolRequestsで中断、
DeferredToolResultsで承認・拒否を渡して再開する。

TestModelで以下を確認した。

- 承認待ち：保存しない
- 拒否：保存しない
- 承認：JSONを1件保存する

CLIからn/yを入力する動作確認も実施した。
TestModelの引数はダミー値であり、実際のGeminiの保存内容は未検証。

関連する回帰テスト14件PASS。

### 発展：Google ADK

Pydantic AIと同じGeminiモデル・指示文・読み取り系3ツールを
Google ADKのroot_agentに登録して再構築した。

| 質問 | Pydantic AI | Google ADK |
|---|---:|---:|
| 宿題の3レベル：検索回数 | 1 | 1 |
| LoRAとQLoRA：検索回数 | 2 | 2 |

両方とも用語集に基づいて正しく回答した。
ADKではInMemoryRunnerのイベントから、
ツールの呼び出し名・引数・戻り値を確認した。

Pydantic AIはagent.tool_plainでツールを登録し、
ADKではroot_agentのtools引数で指定する。

承認付き保存はADK版に移植しておらず比較対象外とした。
実測ログはresults/advanced_adk_trace.txtに保存した。

### 気づき・疑問

モデルに対する全体指示だけでなく、
ツールのdocstringもツール選択に影響する。
書き込み操作ではモデルの判断とは独立した承認機構が必要である。

詳細な実行ログはresults/を参照。
