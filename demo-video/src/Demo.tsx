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
  | { kind: "img"; src: string; from: number; to: number; reveal?: boolean; zoom?: boolean; label?: string }
  | { kind: "clip"; src: string; from: number; to: number; rate?: number; label?: string };

// 画面の隅のラベル（何の画面かを示す）
const APP = "iPhone アプリ";
const PIC = "音の絵（自宅の Mac が描く）";
const COACH = "Claude のコーチ";

type Scene = {
  start: number;
  end: number;
  voice: string;
  voiceAt: number; // 場面の頭から語りを始めるまでの秒
  voiceSec: number; // 語りの長さ（字幕の割り振りに使う）
  lines: string[]; // 字幕（表記は demo.md）
  visuals: Visual[];
  // 語りを何本かに分けて映像に合わせて置くとき（③）
  parts?: { at: number; voice: string; sec: number; lines: string[] }[];
};

const SCENES: Scene[] = [
  {
    // 私の困りごと
    start: 0, end: 15, voice: "scene1.mp3", voiceAt: 1.0, voiceSec: 6.61,
    lines: ["家でラテアートを練習しています。", "でも、一人だと、失敗した理由が分かりません。"],
    visuals: [
      { kind: "clip", src: "wide_kitchen.mp4", from: 0, to: 10 },
      { kind: "img", src: "c1_title.png", from: 10, to: 15 },
    ],
  },
  {
    // なぜ音か
    start: 15, end: 36, voice: "scene2.mp3", voiceAt: 0.5, voiceSec: 19.57,
    lines: [
      "形にはなる。でも、輪郭がぼやける。",
      "原因はたいてい、注ぐ前のスチームにあります。",
      "写真には写らず、音にしか残りません。",
      "しかも、やり方もマシンも人によって違う。",
      "だから、正解を押し付けるのではなく、",
      "一緒に育つコーチを作りました。",
    ],
    visuals: [
      { kind: "img", src: "IMG_1852.jpg", from: 0, to: 7, zoom: true },
      { kind: "img", src: "IMG_1846.jpg", from: 7, to: 14, zoom: true },
      { kind: "img", src: "1108_cup2.png", from: 14, to: 21, reveal: true, label: PIC },
    ],
  },
  {
    // 使ってみる（今朝の1回目）
    start: 36, end: 76, voice: "", voiceAt: 0, voiceSec: 0, lines: [],
    parts: [
      { at: 0.5, voice: "scene3a.mp3", sec: 4.52, lines: ["今朝の1回目です。", "開始を押して、台所に置くだけ。"] },
      { at: 10.5, voice: "scene3b.mp3", sec: 7.08, lines: ["スチームが終わると、知らせが来ます。", "注ぎ終わったら、ピッチャーの残りを1枚撮って送ります。"] },
      {
        at: 23.5, voice: "scene3c.mp3", sec: 14.92,
        lines: [
          "1、2分で、Claude のコーチから返事が届きます。",
          "原因の工程を1つ。",
          "次の1回で直す点を1つ、耳と手でできる言葉で。",
          "そして、次に淹れたときに起きるはずの変化を1つ。",
        ],
      },
    ],
    visuals: [
      { kind: "clip", src: "sr_start.mp4", from: 0, to: 4, label: APP },
      { kind: "clip", src: "wide_steam.mp4", from: 4, to: 10 },
      { kind: "clip", src: "sr_done.mp4", from: 10, to: 14, label: APP },
      { kind: "clip", src: "wide_pour.mp4", from: 14, to: 18 },
      { kind: "clip", src: "sr_photo.mp4", from: 18, to: 23, rate: 1.8, label: APP },
      { kind: "img", src: "s4_cup1_diagnosis.png", from: 23, to: 31, label: APP + " ／ " + COACH + "の返事" },
      { kind: "img", src: "c4_diagnosis.png", from: 31, to: 40, label: COACH },
    ],
  },
  {
    // 2回目で確かめる
    start: 76, end: 101, voice: "scene4.mp3", voiceAt: 0.5, voiceSec: 19.72,
    lines: [
      "今朝は、渦の途中で、うっかり空気を入れていました。",
      "続けて2回目。",
      "言われたとおりにすると、空気が入っていた音が消え、",
      "泡の膜も薄くなりました。",
      "コーチの判定は「ほぼ当たり」。",
      "ただし、続けて淹れたので、言い切れない、とも書いてきます。",
    ],
    visuals: [
      { kind: "img", src: "1108_cup1.png", from: 0, to: 6, label: PIC },
      { kind: "img", src: "c5_compare.png", from: 6, to: 17 },
      { kind: "img", src: "c5_verdict.png", from: 17, to: 25, label: COACH },
    ],
  },
  {
    // 山場: AI が自分の誤りに気づく
    start: 101, end: 135, voice: "scene5.mp3", voiceAt: 0.5, voiceSec: 26.2,
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
      { kind: "img", src: "1107_v1.png", from: 0, to: 8, label: PIC },
      { kind: "img", src: "c6a_doubt.png", from: 8, to: 17, label: COACH },
      { kind: "img", src: "1107_v2.png", from: 17, to: 26, label: PIC },
      { kind: "img", src: "c6b_v2.png", from: 26, to: 34, label: APP + "の判定" },
    ],
  },
  {
    // 仕組みと Claude の使い方
    start: 135, end: 162, voice: "scene6.mp3", voiceAt: 0.5, voiceSec: 22.83,
    lines: [
      "仕組みです。",
      "iPhone アプリが音を聞き、自宅の Mac に送ります。",
      "音は、家から出しません。",
      "Claude には、音の数値と絵、写真だけを渡します。",
      "毎回の診断では、採点役の AI が、言いすぎた返事を差し戻します。",
      "毎晩の振り返りで、教わったことを記憶に書き足していきます。",
    ],
    visuals: [
      { kind: "img", src: "c_arch.png", from: 0, to: 16 },
      { kind: "img", src: "s7_taught_by_user.png", from: 16, to: 27, label: "コーチの記憶（" + APP + "で見られる）" },
    ],
  },
  {
    // 締め
    start: 162, end: 179, voice: "scene7.mp3", voiceAt: 0.5, voiceSec: 11.0,
    lines: [
      "ラテアートの正解は、人によって違います。",
      "だから、あなたの音から、一緒に正解を見つけていく。",
      "AI も、私も、初心者からのスタートです。",
    ],
    visuals: [
      { kind: "img", src: "IMG_1853.jpg", from: 0, to: 11.5, zoom: true },
      { kind: "img", src: "c_end.png", from: 11.5, to: 17 },
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

const Label: React.FC<{ text: string }> = ({ text }) => (
  <AbsoluteFill style={{ alignItems: "flex-start", justifyContent: "flex-start", padding: 28 }}>
    <div
      style={{
        fontFamily: FONT,
        fontSize: 30,
        fontWeight: 600,
        color: "white",
        background: "rgba(10,132,255,0.85)",
        padding: "8px 18px",
        borderRadius: 10,
      }}
    >
      {text}
    </div>
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
          volume={(f) => interpolate(f, [0, 10, s(1), s(1.5), s(7), s(8)], [0, 1, 1, 0.3, 0.3, 0], { extrapolateRight: "clamp" })}
        />
      </Sequence>
      {SCENES.map((sc, i) => (
        <Sequence key={i} from={s(sc.start)} durationInFrames={s(sc.end - sc.start)}>
          {sc.visuals.map((v, j) => {
            const dur = s(v.to - v.from);
            return (
              <Sequence key={j} from={s(v.from)} durationInFrames={dur}>
                <Fade dur={dur}>
                  {v.kind === "img" ? <Still v={v} dur={dur} /> : <Clip v={v} />}
                  {v.label ? <Label text={v.label} /> : null}
                </Fade>
              </Sequence>
            );
          })}
          {sc.parts ? (
            sc.parts.map((p, k) => (
              <Sequence key={k} from={s(p.at)} durationInFrames={s(p.sec + 0.3)}>
                <Audio src={staticFile(`voice3/${p.voice}`)} />
                <Subtitles lines={p.lines} sec={p.sec} />
              </Sequence>
            ))
          ) : (
            <Sequence from={s(sc.voiceAt)}>
              <Audio src={staticFile(`voice3/${sc.voice}`)} />
              <Subtitles lines={sc.lines} sec={sc.voiceSec} />
            </Sequence>
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
