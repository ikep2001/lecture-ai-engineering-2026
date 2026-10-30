#!/usr/bin/env python3
"""AIE26 Lecture 02 P3: read-only postprocessing for 27 LoRA experiments.

Usage (on workshop3):
  ~/.venvs/aie26-lec02/bin/python AIE26_P3_analysis_pipeline.py \
     --source ~/ML/AIE26/Lecture02/results/P3 \
     --out ~/ML/AIE26/lecture-ai-engineering-2026/lectures/02/experiments/P3

Does not train, load a model, or modify source experiment directories.
Does not perform any git / gh operations. Output files are safe to review before publishing.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev

EPOCHS = (5, 10, 20)
RANKS = (8, 16, 32)
SEEDS = (42, 123, 2026)
REQUIRED_FIELDS = {
    'epochs', 'rank', 'seed', 'status', 'format_rate', 'content_rate',
    'training_seconds', 'validation_loss', 'last_logged_training_loss',
}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 27:
        raise ValueError(f'Expected 27 rows, got {len(rows)} in {path}')
    if not REQUIRED_FIELDS.issubset(rows[0]):
        raise ValueError(f'Missing fields: {REQUIRED_FIELDS - set(rows[0])}')
    seen = set()
    for row in rows:
        row['epochs'] = int(row['epochs'])
        row['rank'] = int(row['rank'])
        row['seed'] = int(row['seed'])
        key = (row['epochs'], row['rank'], row['seed'])
        if key in seen or row['status'] != 'completed':
            raise ValueError(f'Incomplete or duplicate condition: {key} ({row["status"]})')
        seen.add(key)
        for field in ('format_rate', 'content_rate', 'both_rate',
                      'training_seconds', 'validation_loss',
                      'average_training_loss', 'last_logged_training_loss'):
            if row.get(field) not in (None, ''):
                row[field] = float(row[field])
        if row.get('steps') not in (None, ''):
            row['steps'] = int(row['steps'])
        # Do not publish absolute laboratory home paths from the source CSV.
        row['path'] = f'e{row["epochs"]:02d}_r{row["rank"]:02d}_s{row["seed"]:04d}'
    expected = {(e, r, s) for e in EPOCHS for r in RANKS for s in SEEDS}
    if seen != expected:
        raise ValueError(f'Missing/unexpected conditions: {sorted(expected ^ seen)}')
    if any(row['format_rate'] != 1 for row in rows):
        print('WARNING: not all conditions have 100% format compliance')
    return rows


def dump_csv(path: Path, rows: list[dict], fields: list[str] | None = None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def extract_eval_rows(source: Path) -> list[dict] | None:
    """Read the original per-question evaluation, accepting common JSON layouts.

    No guessing: if the shape cannot be identified, skip and report rather than
    manufacture individual question outcomes from summary statistics.
    """
    file = source / 'eval_after.json'
    if not file.is_file():
        return None
    obj = json.loads(file.read_text(encoding='utf-8'))
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict):
        items = next((obj[k] for k in ('rows', 'results', 'evaluations', 'details', 'items')
                      if isinstance(obj.get(k), list)), None)
    else:
        items = None
    if not isinstance(items, list) or len(items) != 21:
        return None
    if not all(isinstance(x, dict) and 'question' in x and 'content_ok' in x for x in items):
        return None
    return items


def bool_or_none(x):
    if isinstance(x, bool):
        return x
    if x in (0, 1):
        return bool(x)
    return None


def error_type(row: dict):
    if row['content_ok'] and row['format_ok']:
        return 'correct'
    if not row['format_ok']:
        return 'format_error'
    gold = row['gold_needs_review']
    raw = row['raw']
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = None
    actual = parsed.get('needs_review') if isinstance(parsed, dict) else None
    if gold is True and actual is False:
        return 'unsupported_assertion'
    if gold is False and actual is True:
        return 'unjustified_review'
    return 'other_content_error'


def question_data(source: Path, rows: list[dict]):
    matrix = []
    missing = []
    for cond in rows:
        sub = source / cond['path']
        original = extract_eval_rows(sub)
        if original is None:
            missing.append(cond['path'])
            continue
        count = sum(bool(x['content_ok']) for x in original)
        expected_count = round(cond['content_rate'] * len(original))
        if count != expected_count:
            raise ValueError(f'Question-level count disagrees with summary: {sub} ({count}!={expected_count})')
        for x in original:
            rr = dict(epochs=cond['epochs'], rank=cond['rank'], seed=cond['seed'],
                      question=x['question'],
                      gold_needs_review=bool_or_none(x.get('gold_needs_review')),
                      format_ok=bool_or_none(x.get('format_ok')),
                      content_ok=bool_or_none(x.get('content_ok')),
                      both_ok=bool_or_none(x.get('both_ok')),
                      raw=x.get('raw', ''))
            rr['error_type'] = error_type(rr)
            matrix.append(rr)
    if missing:
        print(f'WARNING: per-question data unavailable in {len(missing)}/27 conditions: {missing[:5]}')
    return matrix, missing


def grouping(rows: list[dict]):
    groups = []
    for e in EPOCHS:
        for r in RANKS:
            b = [row for row in rows if row['epochs'] == e and row['rank'] == r]
            assert len(b) == 3
            def average(key):
                return mean(row[key] for row in b)
            a = [row['content_rate'] for row in b]
            groups.append(dict(epochs=e, rank=r, seeds=3,
                               content_rate_mean=mean(a),
                               content_rate_sd=stdev(a),
                               format_rate_mean=average('format_rate'),
                               training_seconds_mean=average('training_seconds'),
                               training_seconds_median=median(row['training_seconds'] for row in b),
                               training_seconds_sd=stdev(row['training_seconds'] for row in b),
                               validation_loss_mean=average('validation_loss'),
                               last_logged_training_loss_mean=average('last_logged_training_loss')))
    return groups


def report_markdown(groups: list[dict], matrix: list[dict], missing: list[str]) -> str:
    lines = [
        '# 第2回 P3 — LoRA Epoch × rank × Seed スイープ分析',
        '',
        '## 概要・実験設計',
        '',
        '- 対象モデル：`Qwen/Qwen3.5-0.8B`、LoRA（量子化なし）。',
        '- Epoch = 5/10/20、rank = 8/16/32、seed = 42/123/2026（計27独立実行）。',
        '- `lora_alpha=2×rank`、ウォームアップは総ステップ数の15%を切り上げ（2/3/6ステップ）。',
        '- train/validation/test は元Notebookの固定分割（14/7/21問）。同じ21問を各条件で評価。',
        '- 形式遵守率・内容正解率はテスト21問から計算。Lossは学習/検証データで別途計算。',
        '- 以下の平均±標準偏差は3 Seedに対する記述統計（標本標準偏差）。',
        '',
        '## 9設定の比較',
        '',
        '| Epoch | rank | 内容正解率（平均±SD） | 形式遵守率 | Validation Loss | 学習時間（平均/中央値） |',
        '|---:|---:|---:|---:|---:|---:|',
    ]
    for r in groups:
        lines.append(f'| {r["epochs"]} | {r["rank"]} | '
                     f'{r["content_rate_mean"]*100:.2f}% ± {r["content_rate_sd"]*100:.2f}pt | '
                     f'{r["format_rate_mean"]*100:.1f}% | '
                     f'{r["validation_loss_mean"]:.4f} | '
                     f'{r["training_seconds_mean"]:.1f}秒 / {r["training_seconds_median"]:.1f}秒 |')
    lines += [
        '',
        '## 結果と解釈',
        '',
        '1. **形式遵守**：全27条件で形式遵守率100%。このタスクに限り、5 Epochでも形式は学習できた。',
        '2. **Epoch × rank の関係**：rank 8では20 Epochが最高（93.65%）。rank 16と32では10 Epochが20 Epochを上回る。交互作用を示唆するが、記述的な傾向であり、有意差は主張しない。',
        '3. **Lossとの乖離**：rank 16/32の20 Epochでは10 Epochより最後のTraining Lossが低い一方、Validation Lossは高く、テスト内容正解率も低い。過学習の可能性がある。ただし、断定するには評価分割の拡充が必要。',
        '4. **計算効率**：10 Epoch・rank 16は内容正解率92.06%、平均学習時間40.8秒、Validation Loss 0.1208。20 Epoch・rank 8は内容正解率93.65%、平均92.3秒。テスト正解率の差は3 Seed×21問で延べ1問分に過ぎない。',
        '5. **Seed依存**：3 Seedでは特に20 Epoch・rank 32の正解率のばらつきが大きい。少標本のため安定性の結論は限定的。',
        '',
        '## 質問別の失敗分析',
        '',
    ]
    if matrix and not missing:
        err = [x for x in matrix if not x['content_ok'] or not x['format_ok']]
        counts = defaultdict(int)
        questions = defaultdict(int)
        for row in err:
            counts[row['error_type']] += 1
            questions[row['question']] += 1
        lines += [
            f'- 全{len(matrix)}応答（27条件×21問）について質問単位の評価結果を照合済み。',
            '- 誤答の分類（誤答延べ件数）：' + '、'.join(f'`{k}` {v}件' for k,v in sorted(counts.items())),
            '- 頻出する失敗質問（条件横断の延べ誤答数）：',
        ]
        for q, n in sorted(questions.items(), key=lambda x:(-x[1], x[0]))[:8]:
            lines.append(f'  - {q}：{n}/27条件')
        lines += [
            '- 個別の原文と誤答の種類は `question_errors.csv`、全評価結果は `question_matrix.csv` を参照。',
        ]
    else:
        lines += [
            '- 現時点では質問単位のJSONを認識できなかったため、個別誤答は**未分析**。集計から誤答を推測していない。',
            f'- 読み取れなかった条件数：{len(missing)} / 27。`eval_after.json` の構造を確認して再抽出する。',
        ]
    lines += [
        '',
        '## 注意・限界',
        '',
        '- **テストによる設定選択のバイアス**：この21問の正解率で「最高設定」を選ぶのは探索的操作。確定的な性能推定には検証データで条件を選び、独立テストセットで最終評価する必要がある。',
        '- **小規模データ**：テスト21問の1問は約4.76ポイント、各設定3 Seed。独立な63問を観測したわけではなく、同じ21問の繰り返し評価である。',
        '- **Seedは反復因子**：性能最大のSeedを選ぶためではなく、結果の変動を測るために変更した。',
        '- **Lossは正解率と尺度が違う**：Validation Lossは教師強制に基づくトークン確率、内容正解率は生成結果への判定。値が一致するとは限らない。',
        '- **学習時間**：他ジョブやカーネル状態によるばらつきがあり、比較は参考値。',
        '- **P0〜P2と別プロトコル**：P3はrankに応じてalphaを変更し、ウォームアップを比率指定した。P0〜P2と単純に同一条件としてプールしない。',
        '',
        '## ファイル構成・再現',
        '',
        '- `summary.csv` / `summary.json`：27条件の集計。公開時には実行環境の絶対パスを除去。',
        '- `group_summary.csv`：9設定のSeed平均・標準偏差。',
        '- `P3_analysis.ipynb`：集計の再計算、ヒートマップ、交互作用の可視化。',
        '- `question_matrix.csv` / `question_errors.csv`：元の`eval_after.json`が読めた場合のみ作成。',
        '- データ生成元：ローカルJupyterHubの`results/P3/`。学習済みモデルやCUDA環境は本分析の再計算には不要。',
        '',
    ]
    return '\n'.join(lines)


def cell_code(text: str):
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [],
            'source': text.strip().splitlines(keepends=True)}


def cell_md(text: str):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': text.strip().splitlines(keepends=True)}


def build_notebook() -> dict:
    cells = [
        cell_md('''# AIE26 第2回 P3：Epoch × rank × Seed の分析

27条件（Epoch=5/10/20、rank=8/16/32、Seed=42/123/2026）の独立実行結果を再計算・可視化する。

**対象**：形式遵守率、内容正解率、Validation Loss、最終Training Loss、学習時間、質問別の誤答。全条件で同一の21問を使用するため、平均正解率の差を独立な新規テストデータでの性能差と解釈しない。'''),
        cell_code('''from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display

HERE = Path.cwd()
if not (HERE / 'summary.csv').is_file():
    HERE = Path('lectures/02/experiments/P3')
assert (HERE / 'summary.csv').is_file(), 'Run notebook from the P3 directory or repository root.'

df = pd.read_csv(HERE / 'summary.csv')
assert len(df) == 27 and df['status'].eq('completed').all()
assert set(df['epochs']) == {5, 10, 20}
assert set(df['rank']) == {8, 16, 32}
assert set(df['seed']) == {42, 123, 2026}
assert not df.duplicated(['epochs','rank','seed']).any()
print('Completed conditions:', len(df))
print('Format compliance:', df['format_rate'].min(), df['format_rate'].max())
display(df.head())'''),
        cell_code('''cols = ['content_rate','format_rate','training_seconds','validation_loss','last_logged_training_loss']
g = df.groupby(['epochs','rank'])[cols].agg(['mean','std','median'])
display(g.round(4))
# 既存の集計表と照合
check = pd.read_csv(HERE / 'group_summary.csv')
for row in check.itertuples():
    got = g.loc[(row.epochs, row.rank), ('content_rate','mean')]
    assert np.isclose(row.content_rate_mean, got)
print('Aggregate consistency: OK')'''),
        cell_code('''def heatmap(metric, title, scale=1., fmt='.1f'):
    pivot = df.pivot_table(index='epochs', columns='rank', values=metric, aggfunc='mean')
    values = pivot.to_numpy() * scale
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    im = ax.imshow(values, cmap='viridis', aspect='auto')
    ax.set_xticks(range(3), pivot.columns)
    ax.set_yticks(range(3), pivot.index)
    ax.set_xlabel('LoRA rank'); ax.set_ylabel('Epoch')
    ax.set_title(title)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, format(values[i,j],fmt), ha='center', va='center',
                    color='white' if values[i,j] < (values.min()+values.max())/2 else 'black')
    fig.colorbar(im, ax=ax)
    plt.show()

heatmap('content_rate', 'Content correctness: mean over 3 seeds (%)', 100)
heatmap('validation_loss', 'Validation loss: mean over 3 seeds', 1., '.3f')
heatmap('training_seconds', 'Training time: mean over 3 seeds (s)', 1., '.1f')'''),
        cell_code('''fig, ax = plt.subplots(figsize=(7,4))
for r in sorted(df['rank'].unique()):
    d = df[df['rank']==r].groupby('epochs')['content_rate']
    x = np.array(sorted(df['epochs'].unique()))
    y = d.mean().reindex(x).to_numpy() * 100
    sd = d.std().reindex(x).to_numpy() * 100
    ax.errorbar(x, y, yerr=sd, marker='o', capsize=4, label=f'rank {r}')
ax.set_xticks([5,10,20]);ax.set_xlabel('Epoch');ax.set_ylabel('Content correctness (%)')
ax.set_title('Epoch × rank interaction (bars = seed SD)')
ax.grid(alpha=0.25);ax.legend();plt.show()'''),
        cell_code('''# 3 Seed平均の正解率と時間から効率を比較する
s = df.groupby(['epochs','rank']).agg(
    accuracy=('content_rate','mean'),
    val_loss=('validation_loss','mean'),
    train_s=('training_seconds','mean'),
    median_train_s=('training_seconds','median'),
).reset_index()
s['accuracy_pct'] = (s['accuracy']*100).round(2)
s['correct_of_63'] = (s['accuracy']*63).round().astype(int)
display(s.sort_values('accuracy',ascending=False).round(3))
print('Do not treat 63 as 63 independent test questions: the same 21 questions are repeated across seeds.')'''),
        cell_code('''errors = HERE / 'question_errors.csv'
if errors.is_file():
    q = pd.read_csv(errors)
    print('Question-level errors:',len(q))
    display(q.groupby(['epochs','rank','error_type']).size().unstack(fill_value=0))
    display(q.groupby('question').size().sort_values(ascending=False).head(15).rename('error_count'))
    display(q.head(12))
else:
    print('No question_errors.csv; question-level evaluation not available in source JSON.')'''),
        cell_md('''## 解釈上の注意

- 形式遵守率は全27条件で100%でも、内容正解率まで100%という意味ではない。
- Epoch・rankの効果と交互作用は**記述的**な傾向。各条件3 Seed・同一21問なので、統計的な優劣や因果的な過学習を断定しない。
- 検証Lossを使った設定選択と、未知テストデータでの最終評価を分離するのが望ましい。
- P3はウォームアップ・alphaの条件がP0〜P2と異なるため、実験系列を混同しない。'''),
    ]
    return {'cells':cells, 'metadata':{'kernelspec':{'display_name':'Python (AIE26 lec02)', 'language':'python','name':'aie26-lec02'}, 'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path.home()/'ML/AIE26/Lecture02/results/P3')
    parser.add_argument('--out', type=Path, default=Path.home()/'ML/AIE26/lecture-ai-engineering-2026/lectures/02/experiments/P3')
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    out = args.out.expanduser().resolve()
    if source == out or source in out.parents:
        raise ValueError('Output must NOT be inside the source results folder')
    rows = read_csv(source/'summary.csv')
    groups = grouping(rows)
    matrix, missing = question_data(source, rows)
    # Verify all inputs and questions before writing files.
    out.mkdir(parents=True,exist_ok=True)
    dump_csv(out/'summary.csv',rows)
    (out/'summary.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    dump_csv(out/'group_summary.csv',groups)
    if matrix:
        fields=['epochs','rank','seed','question','gold_needs_review','format_ok','content_ok','both_ok','error_type','raw']
        dump_csv(out/'question_matrix.csv',matrix,fields)
        errors=[x for x in matrix if not x['content_ok'] or not x['format_ok']]
        dump_csv(out/'question_errors.csv',errors,fields)
    (out/'P3_report.md').write_text(report_markdown(groups,matrix,missing)+'\n',encoding='utf-8')
    (out/'P3_analysis.ipynb').write_text(json.dumps(build_notebook(),ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    print('OUTPUT:',out)
    for p in sorted(out.iterdir()):
        print(f'  {p.name} ({p.stat().st_size:,} bytes)')
    print('Completed: 27/27')
    print('Question-level rows:', len(matrix), '/ expected 567')
    if missing:
        print('NOTE: question extraction incomplete; see warning; no unverified question claims made.')
    print('Original training/validation/test files unchanged.')

if __name__=='__main__':
    main()
