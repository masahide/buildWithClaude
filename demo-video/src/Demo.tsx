// デモ動画（3分）。台本は docs/project/demo.md の「筋」の表。
// 素材（public/）は git 管理外。語りは scripts/demo/narration.py で作った音声。
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";

export const FPS = 30;
export const TOTAL_SEC = 179; // 「3分以内」に余裕を持たせる
const s = (sec: number) => Math.round(sec * FPS);

const BG = "#121214";
const FONT = '"Hiragino Sans", "Hiragino Kaku Gothic ProN", sans-serif';

type Visual =
  | { kind: "img"; src: string; from: number; to: number; reveal?: boolean; zoom?: boolean }
  | { kind: "clip"; src: string; from: number; to: number; rate?: number };

type Scene = {
  start: number;
  end: number;
  voice: string;
  voiceAt: number; // 場面の頭から語りを始めるまでの秒
  voiceSec: number; // 語りの長さ（字幕の割り振りに使う）
  lines: string[]; // 字幕（表記は demo.md）
  visuals: Visual[];
  // 語りを文ごとに切って映像に合わせて置くとき（③）。from/to は音声の中の秒（無音で区切った位置）
  parts?: { at: number; from: number; to: number; line: string }[];
};

const SCENES: Scene[] = [
  {
    start: 0, end: 12, voice: "scene1.mp3", voiceAt: 3.5, voiceSec: 7.47,
    lines: ["この音の違い、聞こえますか。", "ラテアートの出来は、この数十秒のスチームで、ほぼ決まります。"],
    visuals: [
      { kind: "img", src: "1108_cup2.png", from: 0, to: 8.5, reveal: true },
      { kind: "img", src: "c1_title.png", from: 8.5, to: 12 },
    ],
  },
  {
    start: 12, end: 35, voice: "scene2.mp3", voiceAt: 0.5, voiceSec: 19.57,
    lines: [
      "形にはなる。でも、輪郭がぼやける。",
      "原因はたいてい、注ぐ前のスチームにあります。",
      "写真には写らず、音にしか残りません。",
      "しかも、やり方もマシンも人によって違う。",
      "だから、正解を押し付けるのではなく、",
      "一緒に育つコーチを作りました。",
    ],
    visuals: [
      { kind: "img", src: "IMG_1852.jpg", from: 0, to: 10, zoom: true },
      { kind: "img", src: "IMG_1846.jpg", from: 10, to: 23, zoom: true },
    ],
  },
  {
    start: 35, end: 55, voice: "scene3.mp3", voiceAt: 0.5, voiceSec: 9.33,
    lines: ["開始を押して、台所に置くだけ。", "スチームが終わると知らせが来ます。", "注ぎ終わったら、ピッチャーの残りを1枚撮ります。"],
    parts: [
      { at: 0.5, from: 0, to: 2.6, line: "開始を押して、台所に置くだけ。" },
      { at: 8.3, from: 3.0, to: 5.35, line: "スチームが終わると知らせが来ます。" },
      { at: 12.0, from: 5.7, to: 9.33, line: "注ぎ終わったら、ピッチャーの残りを1枚撮ります。" },
    ],
    visuals: [
      { kind: "clip", src: "sr_start.mp4", from: 0, to: 3 },
      { kind: "clip", src: "wide_steam.mp4", from: 3, to: 8 },
      { kind: "clip", src: "sr_done.mp4", from: 8, to: 11.5 },
      { kind: "clip", src: "wide_pour.mp4", from: 11.5, to: 15.5 },
      { kind: "clip", src: "sr_photo.mp4", from: 15.5, to: 20, rate: 1.8 },
    ],
  },
  {
    start: 55, end: 85, voice: "scene4.mp3", voiceAt: 0.5, voiceSec: 25.63,
    lines: [
      "コーチは、音の形と写真を見て、3つだけ返します。",
      "原因の工程を1つ。",
      "次の1回で直す点を1つ、耳と手でできる言葉で。",
      "そして、次に淹れたときに起きるはずの変化を1つ。",
      "採点役の AI が、言いすぎた診断を差し戻します。",
      "今朝の1回目は、渦の途中で、うっかり空気を入れていました。",
    ],
    visuals: [
      { kind: "img", src: "s4_cup1_diagnosis.png", from: 0, to: 9 },
      { kind: "img", src: "c4_diagnosis.png", from: 9, to: 19 },
      { kind: "img", src: "1108_cup1.png", from: 19, to: 30 },
    ],
  },
  {
    start: 85, end: 108, voice: "scene5.mp3", voiceAt: 0.5, voiceSec: 17.55,
    lines: [
      "続けて2回目。",
      "言われたとおりにすると、1回目で空気が入っていた音が消え、",
      "泡の膜も薄くなりました。",
      "コーチの判定は「ほぼ当たり」。",
      "ただし、続けて淹れたので、直しの効果とは言い切れない、",
      "とも書いてきます。",
    ],
    visuals: [
      { kind: "img", src: "c5_compare.png", from: 0, to: 13 },
      { kind: "img", src: "c5_verdict.png", from: 13, to: 23 },
    ],
  },
  {
    start: 108, end: 145, voice: "scene6.mp3", voiceAt: 0.5, voiceSec: 26.2,
    lines: [
      "最初は、AI の耳も初心者でした。",
      "ある日、コーチが自分から書いてきました。",
      "「アプリの判定が早すぎる」。",
      "残っていた音で確かめると、そのとおりでした。",
      "静かな渦の音が、部屋の物音と同じ大きさだったんです。",
      "判定は直り、バージョンが上がりました。",
      "私が耳で教え、AI が形で気づく。",
      "こうして一緒に育っていきます。",
    ],
    visuals: [
      { kind: "img", src: "1107_v1.png", from: 0, to: 9 },
      { kind: "img", src: "c6a_doubt.png", from: 9, to: 19 },
      { kind: "img", src: "1107_v2.png", from: 19, to: 29 },
      { kind: "img", src: "c6b_v2.png", from: 29, to: 37 },
    ],
  },
  {
    start: 145, end: 166, voice: "scene7.mp3", voiceAt: 0.5, voiceSec: 14.68,
    lines: [
      "毎晩、コーチがその日の練習を振り返ります。",
      "当たった直し方は「あなたの正解」に。",
      "私が教えたことは、コーチの読みより優先して覚えます。",
      "そして、翌朝のテーマを1つ決めます。",
    ],
    visuals: [
      { kind: "img", src: "s7_theme.png", from: 0, to: 7 },
      { kind: "img", src: "s7_your_answer.png", from: 7, to: 14 },
      { kind: "img", src: "s7_taught_by_user.png", from: 14, to: 21 },
    ],
  },
  {
    start: 166, end: 179, voice: "scene8.mp3", voiceAt: 0.5, voiceSec: 9.25,
    lines: ["渦の回転方向は、音では分かりません。", "だから、次に淹れたときの結果で確かめます。", "音は、家から出しません。"],
    visuals: [
      { kind: "clip", src: "wide_kitchen.mp4", from: 0, to: 8 },
      { kind: "img", src: "c8_privacy.png", from: 8, to: 13 },
    ],
  },
];

const Fade: React.FC<{ dur: number; children: React.ReactNode }> = ({ dur, children }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 8, dur - 8, dur], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

const Still: React.FC<{ v: Extract<Visual, { kind: "img" }>; dur: number }> = ({ v, dur }) => {
  const f = useCurrentFrame();
  const scale = v.zoom ? interpolate(f, [0, dur], [1, 1.06]) : 1;
  // 左から描かれていく（①）
  const right = v.reveal ? interpolate(f, [0, dur - 10], [100, 0], { extrapolateRight: "clamp" }) : 0;
  const card = v.src.startsWith("c");
  return (
    <AbsoluteFill
      style={{ backgroundColor: BG, alignItems: "center", justifyContent: "center", padding: card ? 0 : "24px 0 130px" }}
    >
      <Img
        src={staticFile(`img/${v.src}`)}
        style={{
          maxWidth: "100%",
          maxHeight: "100%",
          objectFit: "contain",
          transform: `scale(${scale})`,
          clipPath: `inset(0 ${right}% 0 0)`,
        }}
      />
    </AbsoluteFill>
  );
};

const Clip: React.FC<{ v: Extract<Visual, { kind: "clip" }> }> = ({ v }) => (
  <AbsoluteFill style={{ backgroundColor: BG, alignItems: "center", justifyContent: "center" }}>
    <OffthreadVideo src={staticFile(`clips/${v.src}`)} muted playbackRate={v.rate ?? 1} style={{ height: "100%" }} />
  </AbsoluteFill>
);

const Subtitles: React.FC<{ lines: string[]; sec: number }> = ({ lines, sec }) => {
  const f = useCurrentFrame();
  const total = lines.reduce((a, l) => a + l.length, 0);
  let t = 0;
  let current = "";
  for (const l of lines) {
    const d = (l.length / total) * sec;
    if (f >= s(t) && f < s(t + d)) current = l;
    t += d;
  }
  if (!current) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 48 }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 44,
          fontWeight: 600,
          color: "white",
          background: "rgba(0,0,0,0.72)",
          padding: "12px 28px",
          borderRadius: 12,
          maxWidth: 1600,
          textAlign: "center",
        }}
      >
        {current}
      </div>
    </AbsoluteFill>
  );
};

export const Demo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      {/* ① 冒頭のスチームの音（11-05 のボイスメモ。家の中で編集し、動画として本人が公開する） */}
      <Sequence from={0} durationInFrames={s(8)}>
        <Audio
          src={staticFile("steam.m4a")}
          volume={(f) => interpolate(f, [0, 10, s(3), s(8)], [0, 1, 0.9, 0], { extrapolateRight: "clamp" })}
        />
      </Sequence>
      {SCENES.map((sc, i) => (
        <Sequence key={i} from={s(sc.start)} durationInFrames={s(sc.end - sc.start)}>
          {sc.visuals.map((v, j) => {
            const dur = s(v.to - v.from);
            return (
              <Sequence key={j} from={s(v.from)} durationInFrames={dur}>
                <Fade dur={dur}>{v.kind === "img" ? <Still v={v} dur={dur} /> : <Clip v={v} />}</Fade>
              </Sequence>
            );
          })}
          {sc.parts ? (
            sc.parts.map((p, k) => (
              <Sequence key={k} from={s(p.at)} durationInFrames={s(p.to - p.from)}>
                <Audio src={staticFile(`voice/${sc.voice}`)} trimBefore={s(p.from)} durationInFrames={s(p.to - p.from)} />
                <Subtitles lines={[p.line]} sec={p.to - p.from} />
              </Sequence>
            ))
          ) : (
            <Sequence from={s(sc.voiceAt)}>
              <Audio src={staticFile(`voice/${sc.voice}`)} />
              <Subtitles lines={sc.lines} sec={sc.voiceSec} />
            </Sequence>
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
