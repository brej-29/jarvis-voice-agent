/* The orb: a canvas drawing whose motion is a readout of what Jarvis is doing.
   idle      drawn once, perfectly still
   listening ripples with the microphone level
   thinking  slow swirl while a real request is in flight
   speaking  gentle swell while the reply is read aloud
   declined  settles to grey for a moment, the "I did not act" state
   The animation loop only runs while something is happening, and not at all with reduced motion. */

const COLORS = {
  idle: [[127, 224, 208], [108, 182, 240]],
  listening: [[240, 176, 74], [255, 138, 92]],
  thinking: [[164, 122, 235], [108, 182, 240]],
  speaking: [[126, 212, 168], [108, 182, 240]],
  declined: [[154, 162, 182], [108, 120, 150]],
};
const PARAMS = { // amp: wobble of the outline, speed: how fast it moves
  idle: { amp: 0.03, speed: 0 },
  listening: { amp: 0.05, speed: 1.3 },
  thinking: { amp: 0.09, speed: 2.2 },
  speaking: { amp: 0.06, speed: 1.6 },
  declined: { amp: 0.02, speed: 0.4 },
};
const mix = (a, b, k) => a + (b - a) * k;
const rgba = (c, a) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;

export function createOrb(canvas) {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const ctx = canvas.getContext("2d");
  const size = canvas.width, dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = canvas.height = size * dpr;
  ctx.scale(dpr, dpr);

  let state = "idle", level = 0, smooth = 0, t = 0, raf = 0, last = 0;
  let cur = COLORS.idle.map((c) => [...c]);

  function draw() {
    const cx = size / 2, cy = size / 2, R = size * 0.25;
    const p = PARAMS[state];
    const amp = p.amp + (state === "listening" ? smooth * 0.2 : 0) + (state === "speaking" ? 0.04 * Math.sin(t * 5) : 0);
    ctx.clearRect(0, 0, size, size);
    ctx.globalCompositeOperation = "lighter";
    const glow = ctx.createRadialGradient(cx, cy, R * 0.4, cx, cy, R * 2.1);
    glow.addColorStop(0, rgba(cur[1], 0.16));
    glow.addColorStop(1, rgba(cur[1], 0));
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, size, size);
    ctx.globalCompositeOperation = "source-over"; // stacked blobs keep their colour instead of burning to white
    for (let i = 0; i < 3; i++) {
      const scale = 1 - i * 0.09 + smooth * 0.08 * (state === "listening");
      ctx.beginPath();
      for (let k = 0; k <= 72; k++) {
        const a = (k / 72) * Math.PI * 2;
        const w = Math.sin(3 * a + t * 1.1 + i * 2.1) + 0.6 * Math.sin(5 * a - t * 0.8 + i * 1.3) + 0.3 * Math.sin(2 * a + t * 1.7);
        const r = R * scale * (1 + amp * w);
        const x = cx + Math.cos(a + (state === "thinking" ? t * 0.35 : 0)) * r, y = cy + Math.sin(a + (state === "thinking" ? t * 0.35 : 0)) * r;
        k ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.closePath();
      const g = ctx.createRadialGradient(cx - R * 0.25, cy - R * 0.3, R * 0.1, cx, cy, R * 1.25);
      g.addColorStop(0, rgba(cur[0], 0.78 - i * 0.16));
      g.addColorStop(0.62, rgba(cur[1], 0.46 - i * 0.1));
      g.addColorStop(1, rgba(cur[1], 0));
      ctx.fillStyle = g;
      ctx.fill();
    }
    const core = ctx.createRadialGradient(cx - R * 0.2, cy - R * 0.25, 0, cx - R * 0.2, cy - R * 0.25, R * 0.55);
    core.addColorStop(0, "rgba(255,255,255,0.16)");
    core.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = core;
    ctx.fillRect(0, 0, size, size);
    ctx.globalCompositeOperation = "source-over";
  }

  function settled() {
    const goal = COLORS[state];
    return cur.every((c, i) => c.every((v, j) => Math.abs(v - goal[i][j]) < 1));
  }

  function frame(now) {
    const dt = Math.min((now - last) / 1000 || 0.016, 0.05);
    last = now;
    t += dt * PARAMS[state].speed;
    smooth = mix(smooth, level, 0.25);
    const goal = COLORS[state], k = 1 - Math.pow(0.001, dt); // about 0.5 s to settle
    cur.forEach((c, i) => c.forEach((_, j) => { c[j] = mix(c[j], goal[i][j], k); }));
    draw();
    raf = state !== "idle" || !settled() || smooth > 0.01 ? requestAnimationFrame(frame) : 0;
  }

  function kick() {
    if (reduced.matches) { cur = COLORS[state].map((c) => [...c]); draw(); return; }
    if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); }
  }

  draw();
  return {
    setState(s) { if (s !== state) { state = s; kick(); } },
    setLevel(v) { level = v; if (v > 0.01) kick(); },
  };
}
