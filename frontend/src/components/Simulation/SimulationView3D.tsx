/**
 * Full-screen 3D view of a flood simulation.
 *
 * Draws the terrain and the water as two meshes on the solver's own grid,
 * with a hand-rolled orbit camera. Deliberately its own WebGL2 renderer
 * rather than a Mapbox custom layer: the whole point of this view is that
 * water disappears behind ridges as you orbit, and depth-testing custom
 * geometry against Mapbox's terrain depends on renderer internals that are
 * not a stable contract. Owning both meshes means the occlusion is simply
 * correct (see lib/terrainMesh.ts for how), at the cost of this view being
 * its own mode rather than an overlay on the globe.
 *
 * No 3D library: the maths is in lib/mat4.ts and lib/orbitCamera.ts, both
 * unit-checked, and the shaders below are short enough to read in one go.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Compass,
  Layers,
  Loader2,
  Mountain,
  RotateCcw,
  Sun,
  Waves,
  X,
} from "lucide-react";
import { useSimulationStore } from "../../stores/simulationStore";
import { rampCss } from "../../lib/simulation";
import {
  buildGridMesh,
  dryOffsetFor,
  hillshadeTexture,
  terrainHeights,
  skirtFlags,
  terrainNormals,
  waterColors,
  waterHeights,
  type GridMesh,
} from "../../lib/terrainMesh";
import {
  createOrbit,
  dollyBy,
  orbitBy,
  viewProjection,
  type OrbitState,
} from "../../lib/orbitCamera";

type Basemap = "satellite" | "relief" | "none";

const TERRAIN_VS = `#version 300 es
precision highp float;
in vec2 aXZ;
in float aY;
in vec3 aNormal;
in vec2 aUV;
in float aSkirt;
uniform mat4 uViewProj;
out vec2 vUV;
out vec3 vNormal;
out float vSkirt;
void main() {
  vUV = aUV;
  vNormal = aNormal;
  vSkirt = aSkirt;
  gl_Position = uViewProj * vec4(aXZ.x, aY, aXZ.y, 1.0);
}`;

const TERRAIN_FS = `#version 300 es
precision highp float;
in vec2 vUV;
in vec3 vNormal;
in float vSkirt;
uniform sampler2D uTexture;
uniform float uHasTexture;
uniform vec3 uLightDir;
out vec4 outColor;
void main() {
  // Fixed key light from the north-west, plus enough ambient that shadowed
  // slopes stay readable rather than going to black.
  float lambert = max(dot(normalize(vNormal), normalize(uLightDir)), 0.0);
  float shade = 0.46 + 0.54 * lambert;
  vec3 base = uHasTexture > 0.5 ? texture(uTexture, vUV).rgb : vec3(0.30, 0.35, 0.29);
  // The cut edge gets a flat, darker face instead of a vertical smear of the
  // basemap, so the domain reads as a clean sample of ground.
  base = mix(base, vec3(0.17, 0.19, 0.16), vSkirt);
  outColor = vec4(base * shade, 1.0);
}`;

const WATER_VS = `#version 300 es
precision highp float;
in vec2 aXZ;
in float aY;
in vec4 aColor;
uniform mat4 uViewProj;
out vec4 vColor;
void main() {
  vColor = aColor;
  gl_Position = uViewProj * vec4(aXZ.x, aY, aXZ.y, 1.0);
}`;

const WATER_FS = `#version 300 es
precision highp float;
in vec4 vColor;
uniform float uOpacity;
out vec4 outColor;
void main() {
  if (vColor.a <= 0.0) discard;   // dry vertices contribute nothing
  outColor = vec4(vColor.rgb, vColor.a * uOpacity);
}`;

function compile(gl: WebGL2RenderingContext, type: number, src: string) {
  const shader = gl.createShader(type)!;
  gl.shaderSource(shader, src);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Shader failed to compile: ${log}`);
  }
  return shader;
}

function link(gl: WebGL2RenderingContext, vsSrc: string, fsSrc: string) {
  const program = gl.createProgram()!;
  const vs = compile(gl, gl.VERTEX_SHADER, vsSrc);
  const fs = compile(gl, gl.FRAGMENT_SHADER, fsSrc);
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error(`Program failed to link: ${gl.getProgramInfoLog(program)}`);
  }
  return program;
}

/** Mapbox Static Images: one draped satellite image for the AOI. */
function satelliteUrl(bbox: number[], widthM: number, depthM: number): string | null {
  const token = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";
  if (!token) return null;
  // Match the image aspect to the domain's, or the drape stretches: the
  // static endpoint fits the bbox into whatever size it is given.
  const aspect = widthM / depthM;
  const w = Math.min(1280, 1024);
  const h = Math.max(1, Math.min(1280, Math.round(w / aspect)));
  const [a, b, c, d] = bbox;
  return (
    `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/` +
    `[${a},${b},${c},${d}]/${w}x${h}` +
    `?access_token=${token}&attribution=false&logo=false`
  );
}

/**
 * Where the camera starts, and what "reset view" returns to.
 *
 * Distance has to account for relief as well as footprint: framing a canyon
 * purely on its footprint put the camera down among the peaks, because 2x
 * exaggerated relief is a large fraction of a small domain. The target is
 * lifted to roughly a third of the terrain height so orbiting pivots around
 * the landscape rather than around its base.
 */
function defaultOrbit(
  mesh: GridMesh,
  sim: { meta: { dem_min: number; dem_max: number } },
  exaggeration: number
): OrbitState {
  const span = Math.max(mesh.widthM, mesh.depthM);
  const relief = (sim.meta.dem_max - sim.meta.dem_min) * exaggeration;
  return createOrbit(span * 1.1 + relief, [0, relief * 0.3, 0]);
}

interface GlScene {
  gl: WebGL2RenderingContext;
  terrainProgram: WebGLProgram;
  waterProgram: WebGLProgram;
  vaoTerrain: WebGLVertexArrayObject;
  vaoWater: WebGLVertexArrayObject;
  indexBuffer: WebGLBuffer;
  waterYBuffer: WebGLBuffer;
  waterColorBuffer: WebGLBuffer;
  texture: WebGLTexture;
  mesh: GridMesh;
  terrainY: Float32Array;
  waterY: Float32Array;
  waterRgba: Uint8Array;
  dryOffset: number;
}

export default function SimulationView3D({ onClose }: { onClose: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<GlScene | null>(null);
  const orbitRef = useRef<OrbitState | null>(null);
  const frameRef = useRef<number>(0);
  const rafRef = useRef<number>(0);
  const dirtyRef = useRef(true);

  const sim = useSimulationStore((s) => s.sim);
  const frame = useSimulationStore((s) => s.frame);
  const opacity = useSimulationStore((s) => s.opacity);
  const depthScaleM = useSimulationStore((s) => s.depthScaleM);
  const showFlood = useSimulationStore((s) => s.showFlood);

  const [exaggeration, setExaggeration] = useState(2.2);
  const [occlude, setOcclude] = useState(true);
  const [basemap, setBasemap] = useState<Basemap>("satellite");
  const [textureNote, setTextureNote] = useState<string | null>(null);
  // Why satellite was abandoned, kept separate: switching to relief re-runs
  // this effect, and the relief branch would otherwise overwrite the reason
  // with its own generic note before anyone could read it.
  const [satelliteFailed, setSatelliteFailed] = useState<string | null>(null);
  const [loadingTexture, setLoadingTexture] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---------- build the scene when the simulation or exaggeration changes ----
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !sim) return;

    const gl = canvas.getContext("webgl2", {
      antialias: true,
      alpha: false,
      depth: true,
    });
    if (!gl) {
      setError("This browser or device does not support WebGL2.");
      return;
    }

    let scene: GlScene;
    try {
      const mesh = buildGridMesh(sim.ny, sim.nx, sim.meta.dx);
      const demMin = sim.meta.dem_min;
      const demMax = sim.meta.dem_max;
      const dryOffsetM = dryOffsetFor(demMin, demMax);
      // The skirt only has to reach below the deepest buried water at the
      // boundary — its whole job is giving that water something to be hidden
      // behind. Sizing it off the relief instead produced a plinth taller
      // than the landscape on a high-relief scene like a canyon.
      const skirtDrop = dryOffsetM * 1.5 + 5;
      const terrainY = terrainHeights(
        sim.dem, mesh, exaggeration, demMin, skirtDrop
      );
      const normals = terrainNormals(
        sim.dem, mesh, sim.ny, sim.nx, sim.meta.dx, exaggeration
      );
      const dryOffset = dryOffsetM;

      const terrainProgram = link(gl, TERRAIN_VS, TERRAIN_FS);
      const waterProgram = link(gl, WATER_VS, WATER_FS);

      // AllowSharedBufferSource, not BufferSource: the decoded arrays are
      // views over a buffer TypeScript widens to ArrayBufferLike, and this is
      // the overload WebGL actually exposes for them.
      const staticBuffer = (data: AllowSharedBufferSource) => {
        const buf = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
        return buf;
      };
      const xzBuffer = staticBuffer(mesh.xz);
      const uvBuffer = staticBuffer(mesh.uv);
      const normalBuffer = staticBuffer(normals);
      const terrainYBuffer = staticBuffer(terrainY);
      const skirtBuffer = staticBuffer(skirtFlags(mesh));

      const indexBuffer = gl.createBuffer()!;
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);

      const bindAttrib = (
        program: WebGLProgram, name: string, buffer: WebGLBuffer,
        size: number, type: number, normalized = false
      ) => {
        const loc = gl.getAttribLocation(program, name);
        if (loc < 0) return;
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, size, type, normalized, 0, 0);
      };

      // Terrain VAO — everything static.
      const vaoTerrain = gl.createVertexArray()!;
      gl.bindVertexArray(vaoTerrain);
      bindAttrib(terrainProgram, "aXZ", xzBuffer, 2, gl.FLOAT);
      bindAttrib(terrainProgram, "aY", terrainYBuffer, 1, gl.FLOAT);
      bindAttrib(terrainProgram, "aNormal", normalBuffer, 3, gl.FLOAT);
      bindAttrib(terrainProgram, "aUV", uvBuffer, 2, gl.FLOAT);
      bindAttrib(terrainProgram, "aSkirt", skirtBuffer, 1, gl.FLOAT);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);

      // Water VAO — height and colour are rewritten every frame.
      const waterY = new Float32Array(mesh.gridVertexCount);
      const waterRgba = new Uint8Array(mesh.gridVertexCount * 4);
      const waterYBuffer = gl.createBuffer()!;
      gl.bindBuffer(gl.ARRAY_BUFFER, waterYBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, waterY, gl.DYNAMIC_DRAW);
      const waterColorBuffer = gl.createBuffer()!;
      gl.bindBuffer(gl.ARRAY_BUFFER, waterColorBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, waterRgba, gl.DYNAMIC_DRAW);

      const vaoWater = gl.createVertexArray()!;
      gl.bindVertexArray(vaoWater);
      bindAttrib(waterProgram, "aXZ", xzBuffer, 2, gl.FLOAT);
      bindAttrib(waterProgram, "aY", waterYBuffer, 1, gl.FLOAT);
      bindAttrib(waterProgram, "aColor", waterColorBuffer, 4, gl.UNSIGNED_BYTE, true);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      gl.bindVertexArray(null);

      const texture = gl.createTexture()!;
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA,
        gl.UNSIGNED_BYTE, new Uint8Array([80, 90, 78, 255]));
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

      scene = {
        gl, terrainProgram, waterProgram, vaoTerrain, vaoWater, indexBuffer,
        waterYBuffer, waterColorBuffer, texture, mesh, terrainY, waterY,
        waterRgba, dryOffset,
      };
      sceneRef.current = scene;
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not initialise the 3D view.");
      return;
    }

    // Frame the whole domain.
    orbitRef.current = defaultOrbit(scene.mesh, sim, exaggeration);
    dirtyRef.current = true;

    return () => {
      const s = sceneRef.current;
      if (!s) return;
      const g = s.gl;
      g.deleteProgram(s.terrainProgram);
      g.deleteProgram(s.waterProgram);
      g.deleteVertexArray(s.vaoTerrain);
      g.deleteVertexArray(s.vaoWater);
      g.deleteTexture(s.texture);
      sceneRef.current = null;
    };
  }, [sim, exaggeration]);

  // ---------- basemap texture ------------------------------------------------
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !sim) return;
    const { gl, texture } = scene;

    const upload = (source: TexImageSource) => {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      dirtyRef.current = true;
    };

    if (basemap === "relief") {
      const shade = hillshadeTexture(sim.dem, sim.ny, sim.nx);
      const c = document.createElement("canvas");
      c.width = sim.nx;
      c.height = sim.ny;
      c.getContext("2d")?.putImageData(shade, 0, 0);
      upload(c);
      setTextureNote(
        satelliteFailed ?? "Shaded relief computed from the elevation model."
      );
      return;
    }

    if (basemap === "none") {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA,
        gl.UNSIGNED_BYTE, new Uint8Array([80, 90, 78, 255]));
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      setTextureNote(null);
      dirtyRef.current = true;
      return;
    }

    const url = satelliteUrl(
      sim.meta.bbox ?? [], scene.mesh.widthM, scene.mesh.depthM
    );
    if (!url) {
      setSatelliteFailed("No Mapbox token configured — showing shaded relief.");
      setBasemap("relief");
      return;
    }

    let cancelled = false;
    setLoadingTexture(true);
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      if (cancelled) return;
      upload(img);
      setLoadingTexture(false);
      setTextureNote(null);
      setSatelliteFailed(null);
    };
    img.onerror = () => {
      if (cancelled) return;
      setLoadingTexture(false);
      // Falling back keeps the view usable rather than showing a blank drape.
      setSatelliteFailed("Satellite imagery unavailable — showing shaded relief.");
      setBasemap("relief");
    };
    img.src = url;
    return () => {
      cancelled = true;
    };
  }, [basemap, sim, satelliteFailed]);

  // ---------- keep the frame index in a ref for the render loop --------------
  useEffect(() => {
    frameRef.current = frame;
    dirtyRef.current = true;
  }, [frame]);
  useEffect(() => {
    dirtyRef.current = true;
  }, [opacity, depthScaleM, showFlood, occlude]);

  // ---------- render loop ----------------------------------------------------
  const render = useCallback(() => {
    rafRef.current = requestAnimationFrame(render);
    const scene = sceneRef.current;
    const canvas = canvasRef.current;
    const orbit = orbitRef.current;
    if (!scene || !canvas || !orbit || !sim) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.floor(canvas.clientWidth * dpr);
    const h = Math.floor(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      dirtyRef.current = true;
    }
    if (!dirtyRef.current) return;
    dirtyRef.current = false;

    const { gl, mesh } = scene;
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.043, 0.071, 0.055, 1);
    gl.clearDepth(1);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(true);
    gl.disable(gl.BLEND);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    const vp = viewProjection(orbit, canvas.width / Math.max(canvas.height, 1));

    // --- terrain ---
    gl.useProgram(scene.terrainProgram);
    gl.uniformMatrix4fv(
      gl.getUniformLocation(scene.terrainProgram, "uViewProj"), false, vp
    );
    gl.uniform3f(
      gl.getUniformLocation(scene.terrainProgram, "uLightDir"), -0.6, 0.72, -0.35
    );
    gl.uniform1f(
      gl.getUniformLocation(scene.terrainProgram, "uHasTexture"),
      basemap === "none" ? 0 : 1
    );
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, scene.texture);
    gl.uniform1i(gl.getUniformLocation(scene.terrainProgram, "uTexture"), 0);
    gl.bindVertexArray(scene.vaoTerrain);
    gl.drawElements(gl.TRIANGLES, mesh.indexCount, gl.UNSIGNED_INT, 0);   // + skirt

    // --- water ---
    if (showFlood) {
      waterHeights(
        sim, frameRef.current, scene.terrainY, exaggeration,
        scene.dryOffset, scene.waterY
      );
      waterColors(sim, frameRef.current, depthScaleM, scene.waterRgba);
      gl.bindBuffer(gl.ARRAY_BUFFER, scene.waterYBuffer);
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, scene.waterY);
      gl.bindBuffer(gl.ARRAY_BUFFER, scene.waterColorBuffer);
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, scene.waterRgba);

      gl.useProgram(scene.waterProgram);
      gl.uniformMatrix4fv(
        gl.getUniformLocation(scene.waterProgram, "uViewProj"), false, vp
      );
      gl.uniform1f(
        gl.getUniformLocation(scene.waterProgram, "uOpacity"), opacity
      );
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      // Depth *test* on so ridges hide the water behind them; depth *write*
      // off so the translucent surface does not occlude itself. Turning the
      // test off is the "occlude behind terrain" toggle: the full modelled
      // extent then shows through the landscape.
      if (occlude) gl.enable(gl.DEPTH_TEST);
      else gl.disable(gl.DEPTH_TEST);
      gl.depthMask(false);
      gl.bindVertexArray(scene.vaoWater);
      // Surface triangles only — the skirt is terrain, not water.
      gl.drawElements(gl.TRIANGLES, mesh.gridIndexCount, gl.UNSIGNED_INT, 0);
      gl.depthMask(true);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
    }

    gl.bindVertexArray(null);
  }, [sim, basemap, showFlood, opacity, depthScaleM, exaggeration, occlude]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
  }, [render]);

  // ---------- orbit interaction ---------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    const down = (e: PointerEvent) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!dragging || !orbitRef.current) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      orbitRef.current = orbitBy(orbitRef.current, -dx * 0.006, dy * 0.006);
      dirtyRef.current = true;
    };
    const up = (e: PointerEvent) => {
      dragging = false;
      if (canvas.hasPointerCapture(e.pointerId)) {
        canvas.releasePointerCapture(e.pointerId);
      }
    };
    const wheel = (e: WheelEvent) => {
      if (!orbitRef.current) return;
      e.preventDefault();
      const span = sceneRef.current
        ? Math.max(sceneRef.current.mesh.widthM, sceneRef.current.mesh.depthM)
        : 1000;
      orbitRef.current = dollyBy(
        orbitRef.current, Math.exp(e.deltaY * 0.0012), span * 0.18, span * 6
      );
      dirtyRef.current = true;
    };

    canvas.addEventListener("pointerdown", down);
    canvas.addEventListener("pointermove", move);
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("pointercancel", up);
    canvas.addEventListener("wheel", wheel, { passive: false });
    return () => {
      canvas.removeEventListener("pointerdown", down);
      canvas.removeEventListener("pointermove", move);
      canvas.removeEventListener("pointerup", up);
      canvas.removeEventListener("pointercancel", up);
      canvas.removeEventListener("wheel", wheel);
    };
  }, [sim]);

  const resetView = () => {
    const scene = sceneRef.current;
    if (!scene || !sim) return;
    orbitRef.current = defaultOrbit(scene.mesh, sim, exaggeration);
    dirtyRef.current = true;
  };

  if (!sim) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      // Above the floating panels (z-40): this is a full-screen mode, not an
      // overlay, and its own controls duplicate everything the tools panel
      // offers. The scrubber sits above it at z-50 so playback stays reachable.
      className="absolute inset-0 z-[45] bg-bg"
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full touch-none cursor-grab active:cursor-grabbing"
      />

      {error && (
        <div className="absolute inset-0 grid place-items-center px-6">
          <p className="max-w-sm text-center text-xs text-amber leading-relaxed">
            {error}
          </p>
        </div>
      )}

      {/* Title block */}
      <div className="absolute left-5 top-5 z-10 max-w-[22rem] rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel px-4 py-3">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-amber/15 ring-1 ring-amber/40 px-2 py-[3px] font-mono text-[9px] tracking-[0.18em] text-amber">
          <Waves size={10} />
          SIMULATED
        </span>
        <h2 className="mt-2 text-sm text-ink leading-snug">
          {sim.meta.scene_name ?? "Flood simulation"}
        </h2>
        <p className="font-mono text-[10px] text-dim mt-0.5">
          {sim.nx}×{sim.ny} @ {sim.meta.dx.toFixed(0)} m ·{" "}
          {(sim.meta.dem_min ?? 0).toFixed(0)}–{(sim.meta.dem_max ?? 0).toFixed(0)} m
        </p>
        <p className="text-[10px] text-dim leading-relaxed mt-1.5">
          Modelled water over real terrain. Not an observation, not a forecast.
        </p>
      </div>

      {/* Controls */}
      <div className="absolute right-5 top-5 z-10 w-[16.5rem] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-3.5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
            3D VIEW
          </span>
          <button onClick={onClose} className="text-dim hover:text-ink" title="Exit 3D view">
            <X size={15} />
          </button>
        </div>

        <div className="flex gap-1.5">
          {(["satellite", "relief", "none"] as const).map((b) => (
            <button
              key={b}
              onClick={() => setBasemap(b)}
              className={`flex-1 h-8 rounded-lg text-[11px] capitalize ring-1 transition ${
                basemap === b
                  ? "bg-raised text-teal ring-teal/50"
                  : "text-dim ring-line hover:text-ink"
              }`}
            >
              {b === "none" ? "Plain" : b}
            </button>
          ))}
        </div>
        {loadingTexture && (
          <p className="flex items-center gap-1.5 font-mono text-[10px] text-teal">
            <Loader2 size={11} className="animate-spin" />
            loading imagery…
          </p>
        )}
        {textureNote && (
          <p className="text-[10px] text-dim leading-snug">{textureNote}</p>
        )}

        <Toggle
          icon={Waves}
          label="Flood depth"
          on={showFlood}
          onClick={() => useSimulationStore.getState().setShowFlood(!showFlood)}
        />
        <Toggle
          icon={Mountain}
          label="Occlude behind terrain"
          on={occlude}
          onClick={() => setOcclude(!occlude)}
        />

        <Range
          label="Vertical exaggeration"
          value={exaggeration}
          min={1}
          max={6}
          step={0.1}
          display={`${exaggeration.toFixed(1)}×`}
          onChange={setExaggeration}
        />
        <Range
          label="Depth scale"
          value={depthScaleM}
          min={0.25}
          max={Math.max(sim.peakCm / 100, 0.5)}
          step={0.05}
          display={`${depthScaleM.toFixed(2)} m`}
          onChange={(v) => useSimulationStore.getState().setDepthScaleM(v)}
        />
        <Range
          label="Water opacity"
          value={opacity}
          min={0.1}
          max={1}
          step={0.05}
          display={`${Math.round(opacity * 100)}%`}
          onChange={(v) => useSimulationStore.getState().setOpacity(v)}
        />

        <div className="space-y-1">
          <div
            className="h-2.5 rounded-full ring-1 ring-line"
            style={{ background: rampCss() }}
          />
          <div className="flex justify-between font-mono text-[9px] text-dim">
            <span>0 m</span>
            <span>{depthScaleM.toFixed(1)} m</span>
          </div>
        </div>

        <button
          onClick={resetView}
          className="w-full h-8 rounded-lg bg-bg/70 ring-1 ring-line text-[11px] text-dim hover:text-ink hover:ring-teal/50 transition flex items-center justify-center gap-1.5"
        >
          <RotateCcw size={12} />
          Reset view
        </button>
      </div>

      {/* Interaction hint */}
      <div className="absolute left-5 bottom-5 z-10 flex items-center gap-3 rounded-xl bg-surface/80 backdrop-blur ring-1 ring-line px-3 py-2 font-mono text-[10px] text-dim">
        <span className="flex items-center gap-1.5">
          <Compass size={11} /> drag to orbit
        </span>
        <span className="flex items-center gap-1.5">
          <Sun size={11} /> scroll to zoom
        </span>
        <span className="flex items-center gap-1.5">
          <Layers size={11} /> {sim.frames} frames
        </span>
      </div>
    </motion.div>
  );
}

function Toggle({
  icon: Icon, label, on, onClick,
}: {
  icon: typeof Waves; label: string; on: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 rounded-lg ring-1 px-2.5 py-2 text-left transition ${
        on ? "bg-raised text-teal ring-teal/50" : "bg-bg/70 text-dim ring-line hover:text-ink"
      }`}
    >
      <Icon size={13} className={on ? "text-teal" : "text-dim"} />
      <span className="text-[11px] text-ink">{label}</span>
      <span className={`ml-auto font-mono text-[9px] ${on ? "text-teal" : "text-dim"}`}>
        {on ? "ON" : "OFF"}
      </span>
    </button>
  );
}

function Range({
  label, value, min, max, step, display, onChange,
}: {
  label: string; value: number; min: number; max: number; step: number;
  display: string; onChange: (v: number) => void;
}) {
  return (
    <label className="block space-y-1">
      <span className="flex items-center justify-between text-[11px]">
        <span className="text-dim">{label}</span>
        <span className="font-mono text-ink">{display}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-teal h-1"
      />
    </label>
  );
}
