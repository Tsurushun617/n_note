# -*- coding: utf-8 -*-
"""
書いたあとの健康診断。writing-style.md の 0項「数値は書いたあとの健康診断」用。

使い方:
    python tools/style-check.py articles/2026-08-03-yufukage-kyoukan/draft.md
    python tools/style-check.py articles/*/final.md
    python tools/style-check.py --mode 感情 articles/xxx/draft.md

書く前に数値を狙わないこと。書き上げたあと、素から外れていないかを見るだけに使う。
基準値の根拠は knowledge/reference-tsuru-solo.md（つるが単独執筆した4記事の実測）。
"""
import re
import sys
import io
import os
import glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# モード別の目安（reference-tsuru-solo.md の実測より）
MODES = {
    "感情": {"avg": (17, 27), "short": (58, 78), "q": (12, 18)},
    # 葛藤は確認済みサンプルが1本のみ（2025-11-29）。暫定値。
    "葛藤": {"avg": (22, 28), "short": (52, 68), "q": (4, 10)},
    "論評": {"avg": (18, 23), "short": (65, 75), "q": (6, 11)},
    # 回想は長編（2025-08-29）と短編（2026-08-12）で幅がある
    "回想": {"avg": (23, 32), "short": (48, 60), "q": (2, 6)},
}

# つるの素の下限（確認済み6記事の実測より）。AI判定に使う。
Q_FLOOR = 2.8          # 疑問符：100文あたり（文中の？も数える）実測の最小は2.9（2026-08-12）
CONJ_FLOOR = 20.1      # 接続詞：これより「文/回」が大きい＝少なすぎる

CONJ = ["しかし", "だが", "ところが", "また", "そして", "さらに", "つまり", "なお",
        "だから", "なぜなら", "ただ", "ただし", "逆に", "そこで", "それでも",
        "とはいえ", "というのも", "けれど"]
KEIGO = ["です", "ます", "ました", "ません", "でした", "ましょう", "ですが", "ますが"]


def sentences(text):
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("http") or line.startswith("#"):
            continue
        if line.startswith("|") or line.startswith("---"):
            continue
        for p in re.split(r"(?<=[。？！])", line):
            p = p.strip()
            if p:
                out.append(p)
    return out


def analyze(path, mode=None):
    text = open(path, encoding="utf-8").read()
    ss = sentences(text)
    if not ss:
        print("  （文が取れませんでした）")
        return
    n = len(ss)
    lens = [len(s) for s in ss]
    avg = sum(lens) / n
    short = sum(1 for l in lens if l <= 25) / n * 100
    mid = sum(1 for l in lens if 26 <= l <= 50) / n * 100
    long_ = sum(1 for l in lens if 51 <= l <= 80) / n * 100
    over = [s for s in ss if len(s) > 80]
    # つるは文末だけでなく文中にも「？」を置く（「じゃあ社長に聞けば？」と思ったが／（冷めすぎ？））
    # 文末だけ数えると取りこぼすので、総数を文数で割った値を使う。
    q_tail = sum(1 for s in ss if s.endswith("？")) / n * 100
    q = (text.count("？") + text.count("?")) / n * 100
    keigo = sum(1 for s in ss if any(s.rstrip("。？！").endswith(k) for k in KEIGO)) / n * 100
    conj = sum(1 for s in ss if any(s.startswith(c) for c in CONJ))
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]

    print("=" * 60)
    print(os.path.basename(path) + (f"  [モード: {mode}]" if mode else ""))
    print(f"  {len(text)}字 / {n}文 / 平均文長 {avg:.1f}字 / 段落{len(paras)}")
    print(f"  短文(〜25) {short:.1f}%   中文(26-50) {mid:.1f}%   長文(51-80) {long_:.1f}%")
    print(f"  疑問符 {q:.1f}%（文末のみ {q_tail:.1f}%）   敬体 {keigo:.1f}%   接続詞 "
          + (f"{n/conj:.1f}文に1回" if conj else "0（少なすぎ）"))

    flags = []
    if short < 50:
        flags.append(f"短文が{short:.1f}%。50%を切っている → 整えすぎを疑う（0項）")
    if q < Q_FLOOR:
        flags.append(f"疑問符が100文あたり{q:.1f}個。つるの下限{Q_FLOOR}を切っている"
                     " → ★AIの指紋（最強）。Claudeの初稿は3本中3本で0個だった。"
                     "問いを立てず答えを書いていないか（0項-4）")
    if conj and n / conj < 7.5:
        flags.append(f"接続詞が{n/conj:.1f}文に1回。多い（つるの実測下限は8文に1回・C項）")
    if conj == 0 or (conj and n / conj > 25):
        flags.append(f"接続詞が{n/conj:.1f}文に1回。つるの下限{CONJ_FLOOR}文に1回より少ない"
                     " → ★AIの指紋。思考の継ぎ目が消えていないか（C項）"
                     if conj else "接続詞がゼロ → ★AIの指紋（C項）")
    # 81字超の許容数（つるの実測：感情0本・葛藤0本・論評1本・回想5本）
    allowed = {"感情": 0, "葛藤": 1, "論評": 1, "回想": 8}.get(mode)
    if allowed is not None and len(over) > allowed:
        flags.append(f"81字超が{len(over)}文。{mode}モードの実測では{allowed}文まで（B項）")

    if mode in MODES:
        m = MODES[mode]
        if not (m["avg"][0] <= avg <= m["avg"][1]):
            flags.append(f"平均文長 {avg:.1f}字 が {mode}モードの目安 {m['avg'][0]}〜{m['avg'][1]}字 から外れている")
        if not (m["q"][0] <= q <= m["q"][1]):
            flags.append(f"疑問符 {q:.1f}% が {mode}モードの目安 {m['q'][0]}〜{m['q'][1]}% から外れている")

    if flags:
        print("  ── 気になる点 ──")
        for f in flags:
            print("   ・" + f)
    else:
        print("  ── 指摘なし ──")

    if over:
        print(f"  81字超の文 {len(over)}本:")
        for s in over:
            print(f"     ({len(s)}字) {s[:60]}…")


def main():
    args = sys.argv[1:]
    mode = None
    if "--mode" in args:
        i = args.index("--mode")
        mode = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        return
    targets = []
    for a in args:
        targets.extend(glob.glob(a) or [a])
    for t in targets:
        if os.path.isfile(t):
            analyze(t, mode)


if __name__ == "__main__":
    main()
