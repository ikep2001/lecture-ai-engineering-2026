# 第6回 解答

実施環境：workshop3（Ubuntu）、uv
使用モデル：gemini-3.5-flash-lite

## 演習

- STEP 1 のツールの名前：glossary_search_glossary
- STEP 2 の [tool call]：
  - [tool call]   glossary_search_glossary({'query': '3レベル'})
- STEP 3 の [tool call]：
  - [tool call]   fetch_fetch({'url': 'https://modelcontextprotocol.io/'})
- STEP 4 の [tool call]：
  - [tool call]   aws_aws___search_documentation({'topics': ['general'], 'search_phrase': 'Amazon S3 バージョニング'})
  - [tool call]   aws_aws___search_documentation({'topics': ['general'], 'search_phrase': 'Using versioning in S3 buckets'})

### 演習結果

| STEP | 公開ツール総数 | 入力tokens | 出力tokens | モデル応答回数 |
|---|---:|---:|---:|---:|
| 2 | 1 | 709 | 144 | 2 |
| 3 | 2 | 2173 | 110 | 2 |
| 4 | 7 | 11106 | 132 | 3 |

STEP 4は最新の実行結果を記録した。

### 気づき・疑問

自作サーバー、公開パッケージとして提供されるサーバー、
リモートサーバーの3種類を同じエージェントから利用できた。
ローカルサーバーはcommand、リモートサーバーはurlで
接続先を指定する。

エージェント本体を変更することなく、設定ファイルへの
追記だけで利用可能なツールを増やせることを確認した。

fetchではrobots.txtの確認とリダイレクトへの対応が
行われていた。外部ツールの導入時には、提供元だけでなく、
アクセス先や外部に送信される情報も確認する必要がある。

AWS Knowledge MCP Serverでは最初の検索結果から
検索語を変更して再検索する挙動が観察された。

## 宿題

- 取り組んだレベル：基礎・実装

### 基礎：get_lecture_summaryの公開

app/mcp_server.pyに以下の1行を追加した。

    server.tool()(tools.get_lecture_summary)

エージェント本体を変更せず、公開ツール数が7個から
8個に増えることを確認した。

質問：「第2回では何を学びますか？」

    [tool call]   glossary_get_lecture_summary({'lecture': 2})

第2回のファインチューニングとLoRAについての
講義概要を取得し、回答できることを確認した。

回帰テスト：31 passed（5.98秒）

### 実装：make_quizの公開とエラー応答の改善

第3回で作成したmake_quizをMCPツールとして公開した。

    server.tool()(tools.make_quiz)

また、範囲外の講義回を指定した場合の戻り値に、
利用可能な講義回と修正方法を追加した。

公開ツール総数は8個から9個に増加した。

範囲外入力（lecture=99）の実際の戻り値：

    {
      "error": "第99回の用語がありません。",
      "available_lectures": [1, 2, 3, 4, 6],
      "hint": "利用可能な講義回を指定してください。"
    }

これはJSON形式のアプリケーションレベルのエラー応答であり、
MCPプロトコルのisErrorによる通知とは区別される。

### 動作検証

| ID | 条件 | 実際の処理 | 判定 |
|---|---|---|---|
| T1 | 第2回のクイズ | make_quiz(2) | PASS |
| T2 | 第99回のクイズ | ツール呼び出しなし | 未検証 |
| T3 | 第99回、なければ第2回 | get_lecture_summary(99) → make_quiz(2) | 部分PASS |
| T2b | 対象ツールを明示した異常系 | make_quiz(99) | PASS |
| T3b | 対象ツールと再試行条件を明示 | make_quiz(99) → make_quiz(2) | PASS |

T2bの実行記録：

    [tool call]   glossary_make_quiz({'lecture': 99})

T3bの実行記録：

    [tool call]   glossary_make_quiz({'lecture': 99})
    [tool call]   glossary_make_quiz({'lecture': 2})

### トークン使用量

| ID | 入力tokens | 出力tokens | モデル応答回数 |
|---|---:|---:|---:|
| T1 | 5649 | 70 | 2 |
| T2 | 2783 | 77 | 1 |
| T3 | 8646 | 155 | 3 |
| T2b | 5736 | 97 | 2 |
| T3b | 8743 | 200 | 3 |

各条件1試行であり、質問内容と処理経路が異なるため、
性能の直接比較には用いない。

### テスト結果

- 回帰テスト：31 passed（3.83秒）
- make_quizの正常系・異常系の関数単体検証：
  ALL ASSERTIONS PASSED
- app/mcp_agent.pyの変更なし
- git diff --check：問題なし

### 気づき・疑問

通常の質問では、モデルがツールを呼び出さずに回答したり、
別のツールを用いて事前に情報を確認したりする場合があった。

そのため、最終回答が妥当であることと、意図したツールが
正しく実行されたことは区別して評価する必要がある。

対象ツールを明示した追加実験では、エラーの内容と利用可能な
講義回がモデルに伝わることを確認できた。
さらに、再試行条件を明示することで、同じツールを使って
有効な講義回で再実行できた。

ただし、自律的なエラー回復の成功率や、エラーメッセージの
改善そのものによる効果は、今回の実験では評価していない。

第3回で作成した関数をMCPサーバーから公開することで、
エージェント本体を変更せずに再利用できた。
ツールの実装とエージェントの分離は、保守性と拡張性の
向上に有効であると考える。
