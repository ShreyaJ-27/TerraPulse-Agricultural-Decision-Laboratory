import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import {
  BoxGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
  DoubleSide,
  Group,
  InstancedMesh,
  Object3D,
  PlaneGeometry,
  ShaderMaterial,
  SphereGeometry,
  Vector3,
} from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Sky } from "three/addons/objects/Sky.js";
import type { FieldVisual } from "./LivingFieldScene";
import { FieldLayout, FieldSide, plotDepth, plotWidth } from "./fieldLayout";

type ViewMode = "farm" | "soil";
type CameraView = "overview" | "focus" | "ground";
type CropKind = "maize" | "wheat" | "turmeric" | "millet" | "orchard";

type Props = {
  layout: FieldLayout[];
  selected: FieldLayout;
  side: FieldSide;
  visual?: FieldVisual;
  reduced: boolean;
  mode: ViewMode;
  showRoots: boolean;
  showMoisture: boolean;
  soilDepth: number;
  cameraCommand: { view: CameraView; revision: number };
  onSelect: (id: string) => void;
  onUnavailable: () => void;
};

const hash = (seed: number) => {
  const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return value - Math.floor(value);
};

export function cropKind(label: string): CropKind {
  const text = label.toLowerCase();
  if (text.includes("maize") || text.includes("corn")) return "maize";
  if (text.includes("wheat")) return "wheat";
  if (text.includes("turmeric") || text.includes("haldi")) return "turmeric";
  if (text.includes("orchard")) return "orchard";
  if (text.includes("millet")) return "millet";
  return "maize";
}

function terrainHeight(x: number, z: number, lastZ: number) {
  const distance = Math.max(Math.abs(x) - 36, -z - 28, z - lastZ - 18, 0);
  const wave = 3.4 * Math.sin(x * 0.046 + z * 0.021) + 4.6 * Math.cos(z * 0.03 - x * 0.013);
  return Math.min(1, distance / 68) * (2.2 + Math.max(0, wave));
}

const maizeStalk = new CylinderGeometry(0.055, 0.085, 2.7, 6);
maizeStalk.translate(0, 1.35, 0);
const maizeLeafA = new PlaneGeometry(0.95, 1.7);
maizeLeafA.translate(0, 0.7, 0);
maizeLeafA.rotateZ(-0.7);
maizeLeafA.rotateX(0.4);
maizeLeafA.translate(0.08, 1.05, 0);
const maizeLeafB = new PlaneGeometry(0.95, 1.7);
maizeLeafB.translate(0, 0.7, 0);
maizeLeafB.rotateZ(0.7);
maizeLeafB.rotateX(-0.35);
maizeLeafB.translate(-0.08, 1.15, 0);
const maizeLeafC = new PlaneGeometry(0.62, 1.2);
maizeLeafC.translate(0, 0.55, 0);
maizeLeafC.rotateZ(0.55);
maizeLeafC.rotateY(1.2);
maizeLeafC.translate(0.02, 1.55, 0);
const maizeTassel = new ConeGeometry(0.11, 0.46, 5);
maizeTassel.translate(0, 2.85, 0);

const wheatStalk = new CylinderGeometry(0.03, 0.048, 1.2, 5);
wheatStalk.translate(0, 0.6, 0);
const wheatHead = new ConeGeometry(0.1, 0.36, 5);
wheatHead.translate(0, 1.28, 0);

const turmericStem = new CylinderGeometry(0.045, 0.07, 0.42, 5);
turmericStem.translate(0, 0.21, 0);
function turmericLeaf(turn: number) {
  const leaf = new SphereGeometry(0.55, 7, 5);
  leaf.scale(1.55, 0.28, 0.72);
  leaf.translate(0, 0.46, 0.22);
  leaf.rotateY(turn);
  return leaf;
}
const turmericA = turmericLeaf(0.2);
const turmericB = turmericLeaf(2.15);
const turmericC = turmericLeaf(4.1);

const orchardTrunk = new CylinderGeometry(0.12, 0.18, 1.35, 6);
orchardTrunk.translate(0, 0.68, 0);
const orchardCrown = new SphereGeometry(0.85, 8, 6);
orchardCrown.translate(0, 1.85, 0);

const ridgeGeo = new BoxGeometry(0.78, 0.14, 15.6);
ridgeGeo.translate(0, 0.08, 0);

function cropSpec(kind: CropKind, reduced: boolean) {
  const scale = reduced ? 0.58 : 1;
  const table = {
    maize: { rows: 9, along: 8, rowGap: 2.2, alongGap: 1.95 },
    wheat: { rows: 16, along: 18, rowGap: 1.28, alongGap: 0.82 },
    turmeric: { rows: 8, along: 7, rowGap: 2.4, alongGap: 2.05 },
    millet: { rows: 15, along: 16, rowGap: 1.3, alongGap: 0.9 },
    orchard: { rows: 4, along: 3, rowGap: 4.6, alongGap: 4.4 },
  }[kind];
  return {
    rows: Math.max(2, Math.round(table.rows * scale)),
    along: Math.max(2, Math.round(table.along * scale)),
    rowGap: table.rowGap,
    alongGap: table.alongGap,
  };
}

function CameraRig({ layout, selected, cameraCommand, mode }: Props) {
  const { camera, gl, invalidate } = useThree();
  const controlsRef = useRef<OrbitControls | null>(null);
  const moving = useRef(false);
  const first = useRef(true);
  const position = useRef(new Vector3());
  const target = useRef(new Vector3());
  const modeRef = useRef(mode);
  const selectedRef = useRef(selected);
  const lastZ = layout[layout.length - 1].z;
  modeRef.current = mode;
  selectedRef.current = selected;

  useEffect(() => {
    const controls = new OrbitControls(camera, gl.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.12;
    controls.maxPolarAngle = Math.PI * 0.48;
    controls.minDistance = 3;
    controls.maxDistance = 180;
    const change = () => {
      const soil = modeRef.current === "soil";
      const plot = selectedRef.current;
      const x = Math.max(-48, Math.min(48, controls.target.x));
      const z = Math.max(-40, Math.min(lastZ + 30, controls.target.z));
      const y = soil
        ? Math.max(-3.4, Math.min(2.2, controls.target.y))
        : Math.max(0, Math.min(2.4, controls.target.y));
      const next = new Vector3(x, y, z);
      const delta = next.clone().sub(controls.target);
      if (delta.lengthSq() > 0.000001) {
        camera.position.add(delta);
        controls.target.copy(next);
      }
      if (!soil && camera.position.y < 1.15) camera.position.y = 1.15;
      if (soil && camera.position.z < plot.z + 3.5) camera.position.z = plot.z + 3.5;
      invalidate();
    };
    controls.addEventListener("change", change);
    controlsRef.current = controls;
    return () => {
      controls.dispose();
      controlsRef.current = null;
      first.current = true;
    };
  }, [camera, gl, invalidate, lastZ]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const focus = cameraCommand.view === "focus";
    const ground = cameraCommand.view === "ground";
    if (mode === "soil") {
      const faceZ = selected.z + 3.2;
      target.current.set(selected.x, -1.6, faceZ - 0.4);
      position.current.set(selected.x, 0.15, faceZ + 6.4);
      controls.minDistance = 4.5;
      controls.maxDistance = 28;
      controls.maxPolarAngle = Math.PI * 0.62;
    } else if (ground) {
      target.current.set(selected.x, 1.25, selected.z);
      position.current.set(0.15, 1.7, selected.z + plotDepth / 2 + 3.4);
      controls.minDistance = 2.4;
      controls.maxDistance = 80;
      controls.maxPolarAngle = Math.PI * 0.49;
    } else if (focus) {
      target.current.set(selected.x, 1.3, selected.z);
      position.current.set(selected.x + 11, 7.5, selected.z + 13);
      controls.minDistance = 6;
      controls.maxDistance = 90;
      controls.maxPolarAngle = Math.PI * 0.48;
    } else {
      target.current.set(0, 2.4, -9);
      position.current.set(18, 9.2, 22);
      controls.minDistance = 8;
      controls.maxDistance = 170;
      controls.maxPolarAngle = Math.PI * 0.47;
    }
    if (mode === "soil" || first.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      camera.position.copy(position.current);
      controls.target.copy(target.current);
      controls.update();
      first.current = false;
      moving.current = false;
    } else {
      moving.current = true;
    }
    invalidate();
  }, [camera, cameraCommand, invalidate, mode, selected.x, selected.z]);

  useFrame((_, delta) => {
    const controls = controlsRef.current;
    if (!controls) return;
    if (moving.current) {
      const step = 1 - Math.exp(-6.5 * Math.min(delta, 0.08));
      camera.position.lerp(position.current, step);
      controls.target.lerp(target.current, step);
      if (camera.position.distanceToSquared(position.current) + controls.target.distanceToSquared(target.current) < 0.004) {
        camera.position.copy(position.current);
        controls.target.copy(target.current);
        moving.current = false;
      } else invalidate();
    }
    controls.update();
  });
  return null;
}

function ContextGuard({ onUnavailable }: Pick<Props, "onUnavailable">) {
  const gl = useThree((state) => state.gl);
  useEffect(() => {
    const canvas = gl.domElement;
    canvas.addEventListener("webglcontextlost", onUnavailable);
    return () => canvas.removeEventListener("webglcontextlost", onUnavailable);
  }, [gl, onUnavailable]);
  return null;
}

function Atmosphere() {
  const { scene } = useThree();
  useLayoutEffect(() => {
    const sky = new Sky();
    sky.scale.setScalar(420);
    const uniforms = (sky.material as ShaderMaterial).uniforms;
    uniforms.turbidity.value = 3.6;
    uniforms.rayleigh.value = 1.35;
    uniforms.mieCoefficient.value = 0.0035;
    uniforms.mieDirectionalG.value = 0.72;
    uniforms.sunPosition.value.set(-0.72, 0.22, 0.18);
    scene.add(sky);
    return () => {
      scene.remove(sky);
      sky.geometry.dispose();
      (sky.material as ShaderMaterial).dispose();
    };
  }, [scene]);
  return null;
}

function Landscape({ lastZ, reduced, pit }: { lastZ: number; reduced: boolean; pit: { x: number; z: number } | null }) {
  const geometry = useMemo(() => {
    const terrain = new PlaneGeometry(420, 420, reduced ? 48 : 90, reduced ? 48 : 90);
    terrain.rotateX(-Math.PI / 2);
    const vertices = terrain.getAttribute("position");
    const colors: number[] = [];
    const grass = new Color("#3f6d38");
    const grassB = new Color("#6f9348");
    const dry = new Color("#c2b07a");
    const soil = new Color("#6a5136");
    const color = new Color();
    for (let index = 0; index < vertices.count; index++) {
      const x = vertices.getX(index);
      const z = vertices.getZ(index);
      const y = terrainHeight(x, z, lastZ);
      const inPit = pit && Math.abs(x - pit.x) < plotWidth * 0.48 && z > pit.z - 1.2 && z < pit.z + 6.2;
      vertices.setY(index, inPit ? -6.2 : y);
      const worked = Math.abs(x) < 32 && z > -26 && z < lastZ + 12;
      const mix = 0.35 + 0.4 * Math.sin(x * 0.11 + z * 0.07) + 0.2 * hash(index);
      if (worked && y < 0.2) color.copy(soil).lerp(grass, 0.22 + 0.15 * hash(index + 4));
      else color.copy(grass).lerp(grassB, Math.min(1, Math.max(0, mix))).lerp(dry, Math.min(0.55, y / 10));
      colors.push(color.r, color.g, color.b);
    }
    terrain.setAttribute("color", vertices.clone());
    terrain.getAttribute("color").array.set(colors);
    terrain.computeVertexNormals();
    return terrain;
  }, [lastZ, pit, reduced]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  const trees = useMemo(() => {
    const list: { x: number; z: number; scale: number; pine: boolean }[] = [];
    const target = reduced ? 28 : 64;
    let guard = 0;
    while (list.length < target && guard < 900) {
      guard += 1;
      const x = -70 + hash(guard * 3) * 140;
      const z = -55 + hash(guard * 3 + 1) * 120;
      const y = terrainHeight(x, z, lastZ);
      if (y < 0.35) continue;
      if (Math.abs(x) < 40 && z > -30 && z < lastZ + 16) continue;
      list.push({ x, z, scale: 0.75 + hash(guard * 3 + 2) * 1.15, pine: hash(guard) > 0.45 });
    }
    return list;
  }, [lastZ, reduced]);

  const crowns = useRef<InstancedMesh>(null);
  const pines = useRef<InstancedMesh>(null);
  const trunks = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    const crown = crowns.current;
    const pine = pines.current;
    const trunk = trunks.current;
    if (!crown || !pine || !trunk) return;
    const object = new Object3D();
    const color = new Color();
    trees.forEach(({ x, z, scale, pine: isPine }, index) => {
      const y = terrainHeight(x, z, lastZ);
      object.rotation.set(0, hash(index + 9) * Math.PI, 0);
      object.position.set(x, y + 1.55 * scale, z);
      object.scale.set(isPine ? 0 : scale, isPine ? 0 : scale, isPine ? 0 : scale);
      object.updateMatrix();
      crown.setMatrixAt(index, object.matrix);
      crown.setColorAt(index, color.set(hash(index) > 0.5 ? "#3d7344" : "#4e8a46"));
      object.position.set(x, y + 1.45 * scale, z);
      object.scale.set(isPine ? scale : 0, isPine ? scale * 1.45 : 0, isPine ? scale : 0);
      object.updateMatrix();
      pine.setMatrixAt(index, object.matrix);
      pine.setColorAt(index, color.set(hash(index + 2) > 0.5 ? "#2f5e3c" : "#3f7044"));
      object.position.set(x, y + 0.7 * scale, z);
      object.scale.set(scale, scale, scale);
      object.updateMatrix();
      trunk.setMatrixAt(index, object.matrix);
    });
    [crown, pine, trunk].forEach((mesh) => {
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.computeBoundingSphere();
    });
  }, [trees, lastZ]);

  const road = useMemo(() => {
    const plane = new PlaneGeometry(3.15, 76, 2, 36);
    plane.rotateX(-Math.PI / 2);
    const vertices = plane.getAttribute("position");
    const colors: number[] = [];
    const light = new Color("#a4845c");
    const dark = new Color("#6d5134");
    const color = new Color();
    for (let index = 0; index < vertices.count; index++) {
      const x = vertices.getX(index);
      color.copy(light).lerp(dark, hash(index + 3) * 0.65);
      if (Math.abs(Math.abs(x) - 0.72) < 0.16) color.multiplyScalar(0.78);
      colors.push(color.r, color.g, color.b);
    }
    plane.setAttribute("color", vertices.clone());
    plane.getAttribute("color").array.set(colors);
    return plane;
  }, []);
  useEffect(() => () => road.dispose(), [road]);

  return <>
    <mesh geometry={geometry} receiveShadow>
      <meshStandardMaterial vertexColors roughness={1} />
    </mesh>
    <mesh geometry={road} position={[0, 0.035, -1]} receiveShadow>
      <meshStandardMaterial vertexColors roughness={1} />
    </mesh>
    <mesh rotation-x={-Math.PI / 2} position={[0, 0.04, 0]} receiveShadow>
      <planeGeometry args={[34, 2.7]} />
      <meshStandardMaterial color="#8b6d49" roughness={1} />
    </mesh>
    <mesh rotation-x={-Math.PI / 2} position={[2, 0.04, -23.6]} receiveShadow>
      <planeGeometry args={[30, 2.35]} />
      <meshStandardMaterial color="#8d704c" roughness={1} />
    </mesh>
    <mesh rotation-x={-Math.PI / 2} position={[-2.15, 0.03, 2]} receiveShadow>
      <planeGeometry args={[1.15, 62]} />
      <meshStandardMaterial color="#4a7a3c" roughness={1} />
    </mesh>
    <mesh rotation-x={-Math.PI / 2} position={[2.15, 0.03, 2]} receiveShadow>
      <planeGeometry args={[1.15, 62]} />
      <meshStandardMaterial color="#528445" roughness={1} />
    </mesh>
    <instancedMesh ref={trunks} args={[undefined, undefined, trees.length]} castShadow>
      <cylinderGeometry args={[0.12, 0.2, 1.35, 6]} />
      <meshStandardMaterial color="#5a4632" roughness={0.9} />
    </instancedMesh>
    <instancedMesh ref={crowns} args={[undefined, undefined, trees.length]} castShadow>
      <sphereGeometry args={[1.15, 8, 6]} />
      <meshStandardMaterial roughness={0.86} />
    </instancedMesh>
    <instancedMesh ref={pines} args={[undefined, undefined, trees.length]} castShadow>
      <coneGeometry args={[0.95, 2.8, 7]} />
      <meshStandardMaterial roughness={0.82} />
    </instancedMesh>
    <YardTree position={[-24.5, 0, -23.2]} scale={1.35} />
    <YardTree position={[29.5, 0, -16]} scale={1.15} />
    <YardTree position={[18, 0, 22]} scale={0.95} />
  </>;
}

function YardTree({ position, scale }: { position: [number, number, number]; scale: number }) {
  return <group position={position} scale={scale}>
    <mesh position={[0, 0.9, 0]} castShadow>
      <cylinderGeometry args={[0.16, 0.28, 1.8, 6]} />
      <meshStandardMaterial color="#5c4634" roughness={0.9} />
    </mesh>
    <mesh position={[0, 2.35, 0]} castShadow>
      <sphereGeometry args={[1.2, 10, 8]} />
      <meshStandardMaterial color="#3d7342" roughness={0.84} />
    </mesh>
    <mesh position={[0.85, 2.55, 0.25]} castShadow>
      <sphereGeometry args={[0.82, 8, 6]} />
      <meshStandardMaterial color="#4d8b48" roughness={0.84} />
    </mesh>
  </group>;
}

function Fence({ reduced }: { reduced: boolean }) {
  const posts = useMemo(() => {
    const list: { x: number; z: number }[] = [];
    const step = reduced ? 4.2 : 2.7;
    for (let z = -34; z <= 30; z += step) list.push({ x: -42, z }, { x: 42, z });
    for (let x = -42; x <= 42; x += step) {
      if (Math.abs(x) < 2.4) continue;
      list.push({ x, z: -34 }, { x, z: 30 });
    }
    return list;
  }, [reduced]);
  const ref = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const object = new Object3D();
    posts.forEach((post, index) => {
      object.position.set(post.x, 0.55, post.z);
      object.rotation.set(0, 0, 0);
      object.scale.set(1, 0.85 + hash(index) * 0.3, 1);
      object.updateMatrix();
      mesh.setMatrixAt(index, object.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
    mesh.computeBoundingSphere();
  }, [posts]);
  const rail = (y: number, x: number, z: number, w: number, d: number, key: string) => (
    <mesh key={key} position={[x, y, z]} castShadow>
      <boxGeometry args={[w, 0.08, d]} />
      <meshStandardMaterial color="#7b5b3c" roughness={0.86} />
    </mesh>
  );
  return <>
    <instancedMesh ref={ref} args={[undefined, undefined, posts.length]} castShadow>
      <boxGeometry args={[0.12, 1.15, 0.12]} />
      <meshStandardMaterial color="#6d5138" roughness={0.9} />
    </instancedMesh>
    {rail(0.42, -42, -2, 0.08, 64, "w1")}
    {rail(0.78, -42, -2, 0.08, 64, "w2")}
    {rail(0.42, 42, -2, 0.08, 64, "e1")}
    {rail(0.78, 42, -2, 0.08, 64, "e2")}
    {rail(0.42, -22, -34, 18, 0.08, "n1")}
    {rail(0.78, -22, -34, 18, 0.08, "n2")}
    {rail(0.42, 22, -34, 18, 0.08, "n3")}
    {rail(0.78, 22, -34, 18, 0.08, "n4")}
    {rail(0.42, -22, 30, 18, 0.08, "s1")}
    {rail(0.78, -22, 30, 18, 0.08, "s2")}
    {rail(0.42, 22, 30, 18, 0.08, "s3")}
    {rail(0.78, 22, 30, 18, 0.08, "s4")}
  </>;
}

function Farmhouse() {
  return <group position={[-15.5, 0, -27.2]}>
    <mesh position={[0, 2.15, 0]} castShadow receiveShadow>
      <boxGeometry args={[8.4, 4.3, 6.4]} />
      <meshStandardMaterial color="#6d645c" roughness={0.88} />
    </mesh>
    <mesh position={[5.6, 1.55, 0.2]} castShadow receiveShadow>
      <boxGeometry args={[3.6, 3.1, 5.1]} />
      <meshStandardMaterial color="#74685e" roughness={0.9} />
    </mesh>
    <mesh position={[0, 4.85, 0]} rotation-y={Math.PI / 4} castShadow>
      <coneGeometry args={[6.15, 2.35, 4]} />
      <meshStandardMaterial color="#3a3532" roughness={0.72} />
    </mesh>
    <mesh position={[5.6, 3.55, 0.2]} rotation-y={Math.PI / 4} castShadow>
      <coneGeometry args={[3.15, 1.35, 4]} />
      <meshStandardMaterial color="#3f3935" roughness={0.72} />
    </mesh>
    <mesh position={[2.5, 6.15, -0.8]} castShadow>
      <boxGeometry args={[0.7, 1.7, 0.7]} />
      <meshStandardMaterial color="#5a453c" roughness={0.8} />
    </mesh>
    <mesh position={[0, 0.12, 3.7]} receiveShadow>
      <boxGeometry args={[5.4, 0.24, 1.8]} />
      <meshStandardMaterial color="#8a7560" roughness={0.9} />
    </mesh>
    {[-1.8, 0, 1.8].map((x) => (
      <mesh key={x} position={[x, 1.25, 4.45]} castShadow>
        <cylinderGeometry args={[0.08, 0.1, 2.15, 6]} />
        <meshStandardMaterial color="#efe8dc" roughness={0.6} />
      </mesh>
    ))}
    <mesh position={[0, 2.4, 4.15]} castShadow>
      <boxGeometry args={[5.8, 0.16, 1.7]} />
      <meshStandardMaterial color="#3f3935" roughness={0.7} />
    </mesh>
    <mesh position={[0, 1.05, 3.28]}>
      <boxGeometry args={[0.95, 2.05, 0.12]} />
      <meshStandardMaterial color="#4a3426" roughness={0.7} />
    </mesh>
    {[[-2.4, 1.35], [2.3, 1.35], [-2.4, 3.05], [0, 3.15], [2.3, 3.05]].map(([x, y]) => (
      <mesh key={x + ":" + y} position={[x, y, 3.24]}>
        <boxGeometry args={[0.72, 1.05, 0.08]} />
        <meshStandardMaterial color="#16303a" metalness={0.35} roughness={0.18} />
      </mesh>
    ))}
  </group>;
}

function Barn() {
  return <group position={[11.5, 0, -27.4]}>
    <mesh position={[0, 2.35, 0]} castShadow receiveShadow>
      <boxGeometry args={[11.2, 4.7, 7.4]} />
      <meshStandardMaterial color="#8d2e2a" roughness={0.74} />
    </mesh>
    <mesh position={[0, 5.35, 0]} rotation-y={Math.PI / 4} castShadow>
      <coneGeometry args={[7.4, 2.5, 4]} />
      <meshStandardMaterial color="#5b4634" roughness={0.78} />
    </mesh>
    <mesh position={[0, 1.55, 3.75]}>
      <boxGeometry args={[2.6, 3.05, 0.1]} />
      <meshStandardMaterial color="#d9c7a2" roughness={0.8} />
    </mesh>
    <mesh position={[0, 3.55, 3.76]}>
      <boxGeometry args={[10.4, 0.28, 0.08]} />
      <meshStandardMaterial color="#f3ead7" />
    </mesh>
    <mesh position={[-3.2, 2.4, 3.76]}>
      <boxGeometry args={[1.15, 0.9, 0.08]} />
      <meshStandardMaterial color="#1b2c33" metalness={0.3} roughness={0.2} />
    </mesh>
    <mesh position={[3.2, 2.4, 3.76]}>
      <boxGeometry args={[1.15, 0.9, 0.08]} />
      <meshStandardMaterial color="#1b2c33" metalness={0.3} roughness={0.2} />
    </mesh>
    {[-2.2, 2.2].map((x) => (
      <group key={x} position={[x, 0, -4.3]}>
        <mesh position={[0, 3.4, 0]} castShadow>
          <cylinderGeometry args={[1.45, 1.5, 6.8, 16]} />
          <meshStandardMaterial color="#c5c8cc" metalness={0.55} roughness={0.32} />
        </mesh>
        <mesh position={[0, 6.85, 0]} castShadow>
          <sphereGeometry args={[1.48, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial color="#6e8d86" metalness={0.48} roughness={0.38} />
        </mesh>
        <mesh position={[0, 2.2, 0]}>
          <cylinderGeometry args={[1.55, 1.55, 0.12, 16]} />
          <meshStandardMaterial color="#8d9498" metalness={0.6} roughness={0.3} />
        </mesh>
      </group>
    ))}
    <mesh position={[-6.4, 0.42, 1.2]} rotation={[0, 0.4, Math.PI / 2]} castShadow>
      <cylinderGeometry args={[0.42, 0.42, 1.15, 10]} />
      <meshStandardMaterial color="#c6a25a" roughness={0.85} />
    </mesh>
    <mesh position={[-6.2, 0.42, 2.3]} rotation={[0.2, 0.2, Math.PI / 2]} castShadow>
      <cylinderGeometry args={[0.38, 0.38, 1.05, 10]} />
      <meshStandardMaterial color="#b8924a" roughness={0.85} />
    </mesh>
  </group>;
}

function Windmill({ reduced }: { reduced: boolean }) {
  const blades = useRef<Group>(null);
  useFrame((_, delta) => {
    if (blades.current && !reduced) blades.current.rotation.z += delta * 0.65;
  });
  return <group position={[-37.5, 0, -1.5]}>
    <mesh position={[0, 3.3, 0]} castShadow>
      <cylinderGeometry args={[0.38, 0.85, 6.6, 8]} />
      <meshStandardMaterial color="#e4dfd6" roughness={0.78} />
    </mesh>
    <mesh position={[0, 1.15, 0.7]}>
      <boxGeometry args={[0.55, 1.3, 0.08]} />
      <meshStandardMaterial color="#4a3426" />
    </mesh>
    <mesh position={[0, 6.85, 0.35]} castShadow>
      <boxGeometry args={[1.05, 0.8, 1.25]} />
      <meshStandardMaterial color="#6a5644" roughness={0.7} />
    </mesh>
    <mesh position={[0, 7.55, 0.35]}>
      <coneGeometry args={[0.85, 0.7, 4]} />
      <meshStandardMaterial color="#3e3834" />
    </mesh>
    <group ref={blades} position={[0, 6.85, 1.05]}>
      {[0, 1, 2, 3].map((index) => (
        <group key={index} rotation-z={index * Math.PI / 2}>
          <mesh position={[0, 1.65, 0]} castShadow>
            <boxGeometry args={[0.22, 3.15, 0.06]} />
            <meshStandardMaterial color="#f4f1ea" roughness={0.55} />
          </mesh>
        </group>
      ))}
      <mesh>
        <sphereGeometry args={[0.22, 10, 8]} />
        <meshStandardMaterial color="#c0392b" />
      </mesh>
    </group>
  </group>;
}

function WaterTower() {
  const legs: [number, number][] = [[-1.35, -1.35], [1.35, -1.35], [-1.35, 1.35], [1.35, 1.35]];
  return <group position={[33.5, 0, -6]}>
    {legs.map(([x, z]) => (
      <mesh key={x + ":" + z} position={[x, 3.3, z]} castShadow>
        <cylinderGeometry args={[0.1, 0.16, 6.6, 6]} />
        <meshStandardMaterial color="#8d9294" metalness={0.45} roughness={0.4} />
      </mesh>
    ))}
    <mesh position={[0, 3.1, 0]}>
      <boxGeometry args={[2.4, 0.1, 2.4]} />
      <meshStandardMaterial color="#6a7072" metalness={0.4} />
    </mesh>
    <mesh position={[0, 6.9, 0]} castShadow>
      <cylinderGeometry args={[2.25, 2.35, 2.7, 18]} />
      <meshStandardMaterial color="#9aa2a4" metalness={0.62} roughness={0.28} />
    </mesh>
    <mesh position={[0, 8.15, 0]}>
      <cylinderGeometry args={[2.4, 2.15, 0.28, 18]} />
      <meshStandardMaterial color="#7f8789" metalness={0.55} roughness={0.3} />
    </mesh>
    <mesh position={[0, 7.55, 0]}>
      <cylinderGeometry args={[2.05, 2.05, 0.12, 18]} />
      <meshStandardMaterial color="#3e86b0" metalness={0.15} roughness={0.12} />
    </mesh>
    <mesh position={[0.2, 3.4, 2.15]}>
      <boxGeometry args={[0.45, 3.2, 0.08]} />
      <meshStandardMaterial color="#5c6568" metalness={0.4} />
    </mesh>
  </group>;
}

function Tractor() {
  return <group position={[0.2, 0, 12.4]} rotation-y={0.35}>
    <mesh position={[-0.72, 0.58, -0.15]} rotation-z={Math.PI / 2} castShadow>
      <cylinderGeometry args={[0.58, 0.58, 0.28, 14]} />
      <meshStandardMaterial color="#1a1a1a" roughness={0.7} />
    </mesh>
    <mesh position={[0.72, 0.58, -0.15]} rotation-z={Math.PI / 2} castShadow>
      <cylinderGeometry args={[0.58, 0.58, 0.28, 14]} />
      <meshStandardMaterial color="#1a1a1a" roughness={0.7} />
    </mesh>
    <mesh position={[-0.72, 0.58, -0.15]} rotation-z={Math.PI / 2}>
      <cylinderGeometry args={[0.32, 0.32, 0.3, 12]} />
      <meshStandardMaterial color="#666" metalness={0.6} roughness={0.35} />
    </mesh>
    <mesh position={[0.72, 0.58, -0.15]} rotation-z={Math.PI / 2}>
      <cylinderGeometry args={[0.32, 0.32, 0.3, 12]} />
      <meshStandardMaterial color="#666" metalness={0.6} roughness={0.35} />
    </mesh>
    <mesh position={[-0.62, 0.32, 1.15]} rotation-z={Math.PI / 2} castShadow>
      <cylinderGeometry args={[0.28, 0.28, 0.18, 12]} />
      <meshStandardMaterial color="#1a1a1a" roughness={0.7} />
    </mesh>
    <mesh position={[0.62, 0.32, 1.15]} rotation-z={Math.PI / 2} castShadow>
      <cylinderGeometry args={[0.28, 0.28, 0.18, 12]} />
      <meshStandardMaterial color="#1a1a1a" roughness={0.7} />
    </mesh>
    <mesh position={[0, 0.78, 0.15]} castShadow>
      <boxGeometry args={[1.15, 0.55, 2.15]} />
      <meshStandardMaterial color="#c0392b" roughness={0.45} metalness={0.08} />
    </mesh>
    <mesh position={[0, 1.25, -0.35]} castShadow>
      <boxGeometry args={[1.05, 0.7, 0.95]} />
      <meshStandardMaterial color="#d6453d" roughness={0.4} />
    </mesh>
    <mesh position={[0, 1.55, 0.35]}>
      <boxGeometry args={[0.95, 0.55, 0.08]} />
      <meshStandardMaterial color="#9fd8ea" metalness={0.2} roughness={0.08} />
    </mesh>
    <mesh position={[0.55, 1.15, -0.85]} castShadow>
      <cylinderGeometry args={[0.05, 0.05, 0.7, 6]} />
      <meshStandardMaterial color="#222" />
    </mesh>
    <mesh position={[0, 0.55, 1.55]}>
      <boxGeometry args={[0.9, 0.12, 0.45]} />
      <meshStandardMaterial color="#7f8c8d" metalness={0.4} />
    </mesh>
  </group>;
}

function Shed() {
  return <group position={[32.2, 0, 8.5]}>
    <mesh position={[0, 1.15, 0]} castShadow receiveShadow>
      <boxGeometry args={[3.4, 2.3, 2.5]} />
      <meshStandardMaterial color="#8d6844" roughness={0.86} />
    </mesh>
    <mesh position={[0, 2.55, 0]} rotation-y={Math.PI / 4} castShadow>
      <coneGeometry args={[2.45, 1.15, 4]} />
      <meshStandardMaterial color="#5c4030" roughness={0.8} />
    </mesh>
    <mesh position={[0, 0.85, 1.28]}>
      <boxGeometry args={[1.1, 1.5, 0.08]} />
      <meshStandardMaterial color="#4a3424" />
    </mesh>
  </group>;
}

function paint(mesh: InstancedMesh | null, index: number, object: Object3D, color: Color) {
  if (!mesh) return;
  mesh.setMatrixAt(index, object.matrix);
  mesh.setColorAt(index, color);
}

function stressTint(color: Color, stress?: number) {
  if (stress == null || !Number.isFinite(stress)) return color;
  return color.lerp(new Color("#a6843c"), Math.min(0.72, Math.max(0, stress)));
}

function CropPlot({
  plot, active, visual, reduced, cutaway, onSelect,
}: {
  plot: FieldLayout;
  active: boolean;
  visual?: FieldVisual;
  reduced: boolean;
  cutaway: boolean;
  onSelect: Props["onSelect"];
}) {
  const kind = cropKind(plot.label);
  const spec = cropSpec(kind, reduced);
  const count = spec.rows * spec.along;
  const stress = visual?.waterStress;
  const moisture = visual?.soilWaterMm;
  const stalk = useRef<InstancedMesh>(null);
  const leafA = useRef<InstancedMesh>(null);
  const leafB = useRef<InstancedMesh>(null);
  const leafC = useRef<InstancedMesh>(null);
  const head = useRef<InstancedMesh>(null);
  const blades = useRef<InstancedMesh>(null);

  useLayoutEffect(() => {
    const object = new Object3D();
    const color = new Color();
    const stalkColor = new Color();
    const headColor = new Color();
    let cursor = 0;
    for (let row = 0; row < spec.rows; row++) {
      for (let col = 0; col < spec.along; col++) {
        const seed = plot.index * 100000 + cursor * 17 + 3;
        const x = (row - (spec.rows - 1) / 2) * spec.rowGap + (hash(seed) - 0.5) * spec.rowGap * 0.18;
        const z = (col - (spec.along - 1) / 2) * spec.alongGap + (hash(seed + 1) - 0.5) * spec.alongGap * 0.18;
        const hidden = cutaway && z > -1;
        const vigorScale = visual?.vigor != null ? Math.max(0.4, Math.min(1.4, visual.vigor * 1.2)) : 1.0;
        const heightMultiplier = visual?.plantHeight != null ? Math.max(0.4, Math.min(1.3, visual.plantHeight * 1.15)) : 1.0;
        const baseHeight = hidden ? 0 : (0.78 + hash(seed + 2) * 0.4) * heightMultiplier;
        const bush = kind === "turmeric" ? baseHeight * vigorScale : kind === "orchard" ? (hidden ? 0 : 0.85 + hash(seed + 6) * 0.35) : vigorScale;
        object.position.set(x, 0, z);
        object.rotation.set((hash(seed + 3) - 0.5) * 0.12, hash(seed + 4) * Math.PI * 2, (hash(seed + 5) - 0.5) * 0.12);
        object.scale.set(baseHeight === 0 ? 0 : bush, baseHeight === 0 ? 0 : baseHeight, baseHeight === 0 ? 0 : bush);
        object.updateMatrix();
        if (kind === "wheat") {
          stalkColor.set("#c6a84e").multiplyScalar(0.88 + hash(seed + 8) * 0.28);
          headColor.set("#e0c15a").multiplyScalar(0.92 + hash(seed + 9) * 0.2);
        } else if (kind === "millet") {
          stalkColor.set("#6f8f3a").multiplyScalar(0.85 + hash(seed + 8) * 0.3);
          headColor.set("#9aaa55").multiplyScalar(0.9 + hash(seed + 9) * 0.2);
        } else if (kind === "turmeric") {
          stalkColor.set("#2f8a45").lerp(new Color("#145c30"), hash(seed + 7)).multiplyScalar(0.9 + hash(seed) * 0.25);
          headColor.copy(stalkColor);
        } else if (kind === "orchard") {
          stalkColor.set("#5c4634");
          headColor.set(hash(seed) > 0.5 ? "#3d7344" : "#4e8a46");
        } else {
          stalkColor.set("#2f7a34").multiplyScalar(0.86 + hash(seed + 8) * 0.28);
          headColor.set("#e6d48a").multiplyScalar(0.9 + hash(seed + 9) * 0.2);
        }
        stressTint(stalkColor, stress);
        stressTint(headColor, stress);
        paint(stalk.current, cursor, object, color.copy(stalkColor));
        paint(leafA.current, cursor, object, color.copy(stalkColor).multiplyScalar(0.92 + hash(seed + 11) * 0.16));
        paint(leafB.current, cursor, object, color.copy(stalkColor).multiplyScalar(0.88 + hash(seed + 12) * 0.2));
        paint(leafC.current, cursor, object, color.copy(stalkColor).multiplyScalar(1.02));
        paint(head.current, cursor, object, color.copy(headColor));
        cursor += 1;
      }
    }
    [stalk.current, leafA.current, leafB.current, leafC.current, head.current].forEach((mesh) => {
      if (!mesh) return;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.computeBoundingSphere();
    });
    const grass = blades.current;
    if (grass && kind === "maize") {
      for (let row = 0; row < spec.rows; row++) {
        const x = (row - (spec.rows - 1) / 2) * spec.rowGap;
        object.position.set(x, 0, cutaway ? -4.2 : 0);
        object.rotation.set(0, 0, 0);
        object.scale.set(1, 1, cutaway ? 0.42 : 1);
        object.updateMatrix();
        grass.setMatrixAt(row, object.matrix);
      }
      grass.instanceMatrix.needsUpdate = true;
      grass.computeBoundingSphere();
    }
  }, [count, cutaway, kind, plot.index, spec.along, spec.alongGap, spec.rowGap, spec.rows, stress, visual?.vigor, visual?.plantHeight]);

  const wetness = moisture == null ? 0.35 : Math.min(1, Math.max(0, (moisture - 25) / 70));
  const soil = new Color("#c2b07a").lerp(new Color("#2f4a28"), wetness).getStyle();
  const tint = active ? "#d6ff6a" : "#c8b48a";
  const select = (event: { delta: number; stopPropagation: () => void }) => {
    if (event.delta > 5) return;
    event.stopPropagation();
    onSelect(plot.id);
  };
  return <group position={[plot.x, 0, plot.z]}>
    {!cutaway && <mesh rotation-x={-Math.PI / 2} position={[0, 0.02, 0]} receiveShadow onClick={select}>
      <planeGeometry args={[plotWidth, plotDepth]} />
      <meshStandardMaterial color={soil} roughness={1} />
    </mesh>}
    {cutaway && <mesh rotation-x={-Math.PI / 2} position={[0, 0.025, -4.7]} receiveShadow onClick={select}>
      <planeGeometry args={[plotWidth, 8.4]} />
      <meshStandardMaterial color={soil} roughness={1} />
    </mesh>}
    {kind === "maize" && <instancedMesh ref={blades} args={[ridgeGeo, undefined, spec.rows]} raycast={() => null}>
      <meshStandardMaterial color="#5a4030" roughness={1} />
    </instancedMesh>}
    {kind === "maize" && <>
      <instancedMesh ref={stalk} args={[maizeStalk, undefined, count]} castShadow raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.72} /></instancedMesh>
      <instancedMesh ref={leafA} args={[maizeLeafA, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.72} side={DoubleSide} /></instancedMesh>
      <instancedMesh ref={leafB} args={[maizeLeafB, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.72} side={DoubleSide} /></instancedMesh>
      <instancedMesh ref={leafC} args={[maizeLeafC, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.72} side={DoubleSide} /></instancedMesh>
      <instancedMesh ref={head} args={[maizeTassel, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.55} /></instancedMesh>
    </>}
    {(kind === "wheat" || kind === "millet") && <>
      <instancedMesh ref={stalk} args={[wheatStalk, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.8} /></instancedMesh>
      <instancedMesh ref={head} args={[wheatHead, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.62} /></instancedMesh>
    </>}
    {kind === "turmeric" && <>
      <instancedMesh ref={stalk} args={[turmericStem, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.75} /></instancedMesh>
      <instancedMesh ref={leafA} args={[turmericA, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.7} /></instancedMesh>
      <instancedMesh ref={leafB} args={[turmericB, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.7} /></instancedMesh>
      <instancedMesh ref={leafC} args={[turmericC, undefined, count]} raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.7} /></instancedMesh>
    </>}
    {kind === "orchard" && <>
      <instancedMesh ref={stalk} args={[orchardTrunk, undefined, count]} castShadow raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.86} /></instancedMesh>
      <instancedMesh ref={head} args={[orchardCrown, undefined, count]} castShadow raycast={() => null}><meshStandardMaterial color="#ffffff" roughness={0.8} /></instancedMesh>
    </>}
    <mesh position={[plotWidth / 2 - 0.45, 0.12, cutaway ? -4.5 : 0]} rotation-x={Math.PI / 2}>
      <cylinderGeometry args={[0.045, 0.045, cutaway ? 8 : plotDepth * 0.92, 6]} />
      <meshStandardMaterial color="#2c5f86" emissive={wetness > 0.55 ? "#1a6ea5" : "#000"} emissiveIntensity={wetness > 0.55 ? 0.45 : 0} />
    </mesh>
    {[-1, 1].flatMap((direction) => [
      <mesh key={"x" + direction} position={[direction * plotWidth / 2, 0.08, 0]}>
        <boxGeometry args={[active ? 0.22 : 0.08, 0.12, plotDepth + 0.2]} />
        <meshBasicMaterial color={tint} />
      </mesh>,
      <mesh key={"z" + direction} position={[0, 0.08, direction * plotDepth / 2]}>
        <boxGeometry args={[plotWidth, 0.12, active ? 0.22 : 0.08]} />
        <meshBasicMaterial color={tint} />
      </mesh>,
    ])}
  </group>;
}

const SOIL_LAYERS = [
  { h: 0.55, color: "#6d8f3c" },
  { h: 0.72, color: "#2c1b12" },
  { h: 0.85, color: "#7a4a2e" },
  { h: 1.0, color: "#c49262" },
  { h: 1.25, color: "#edd7ae" },
];

function Specimen({ kind, stress }: { kind: CropKind; stress?: number }) {
  const dry = (stress ?? 0) >= 0.35;
  if (kind === "wheat" || kind === "millet") {
    const stalk = kind === "wheat" && !dry ? "#c6a84e" : "#7f9a3e";
    const head = kind === "wheat" && !dry ? "#f0d56a" : "#9aaa55";
    return <group>
      {[0, 0.14, -0.12, 0.06].map((x, index) => (
        <group key={index} position={[x, 0, (index - 1.5) * 0.07]}>
          <mesh position={[0, 0.5, 0]}>
            <cylinderGeometry args={[0.016, 0.026, 1, 4]} />
            <meshStandardMaterial color={stalk} />
          </mesh>
          <mesh position={[0, 1.08, 0]}>
            <coneGeometry args={[0.042, 0.22, 4]} />
            <meshStandardMaterial color={head} />
          </mesh>
        </group>
      ))}
    </group>;
  }
  if (kind === "turmeric") {
    return <group>
      <mesh position={[0, 0.2, 0]}>
        <cylinderGeometry args={[0.05, 0.07, 0.4, 5]} />
        <meshStandardMaterial color="#2f8a45" />
      </mesh>
      {[0.2, 2.2, 4.2].map((turn) => (
        <mesh key={turn} position={[Math.sin(turn) * 0.22, 0.5, Math.cos(turn) * 0.16]} rotation-y={turn} scale={[1.25, 0.32, 0.62]}>
          <sphereGeometry args={[0.42, 7, 5]} />
          <meshStandardMaterial color={dry ? "#7a9a48" : "#1f8a42"} />
        </mesh>
      ))}
    </group>;
  }
  if (kind === "orchard") {
    return <group>
      <mesh position={[0, 0.7, 0]}><cylinderGeometry args={[0.1, 0.16, 1.3, 5]} /><meshStandardMaterial color="#5c4634" /></mesh>
      <mesh position={[0, 1.8, 0]}><sphereGeometry args={[0.7, 8, 6]} /><meshStandardMaterial color="#3f7a44" /></mesh>
    </group>;
  }
  const leaf = dry ? "#8aaa44" : "#2f7a34";
  return <group>
    <mesh position={[0, 1.25, 0]}>
      <cylinderGeometry args={[0.055, 0.08, 2.5, 6]} />
      <meshStandardMaterial color={leaf} />
    </mesh>
    <mesh position={[0.28, 1.7, 0]} rotation-z={-0.7}>
      <planeGeometry args={[0.55, 1.15]} />
      <meshStandardMaterial color={leaf} side={DoubleSide} />
    </mesh>
    <mesh position={[-0.28, 1.45, 0]} rotation-z={0.65}>
      <planeGeometry args={[0.55, 1.15]} />
      <meshStandardMaterial color={leaf} side={DoubleSide} />
    </mesh>
    <mesh position={[0, 2.65, 0]}>
      <coneGeometry args={[0.1, 0.4, 5]} />
      <meshStandardMaterial color="#e6d48a" />
    </mesh>
  </group>;
}

function SoilCutaway({
  plot, visual, showRoots, showMoisture, soilDepth, onSelect,
}: {
  plot: FieldLayout;
  visual?: FieldVisual;
  showRoots: boolean;
  showMoisture: boolean;
  soilDepth: number;
  onSelect: Props["onSelect"];
}) {
  const kind = cropKind(plot.label);
  const shown = SOIL_LAYERS.slice(0, Math.max(2, Math.min(SOIL_LAYERS.length, soilDepth + 1)));
  let depth = 0;
  const layers = shown.map((layer) => {
    const entry = { ...layer, y: -(depth + layer.h / 2) };
    depth += layer.h;
    return entry;
  });
  const limit = depth;
  const faceZ = 3.15;
  const wetness = visual?.soilWaterMm == null ? 0.45 : Math.min(1, Math.max(0, (visual.soilWaterMm - 25) / 70));
  const waterY = Math.max(-limit + 0.15, -2.4 + wetness * 1.6);
  const select = (event: { delta: number; stopPropagation: () => void }) => {
    if (event.delta > 5) return;
    event.stopPropagation();
    onSelect(plot.id);
  };
  return <group position={[plot.x, 0, plot.z]}>
    {layers.map((layer) => (
      <mesh key={layer.color} position={[0, layer.y, faceZ - 2.05]} receiveShadow onClick={select}>
        <boxGeometry args={[plotWidth * 0.96, layer.h * 0.98, 4.1]} />
        <meshStandardMaterial color={layer.color} roughness={1} />
      </mesh>
    ))}
    {showMoisture && limit > 0.5 && <>
      <mesh position={[0, waterY, faceZ + 0.08]}>
        <boxGeometry args={[plotWidth * 0.86, 0.22, 0.12]} />
        <meshStandardMaterial color="#49b0e0" emissive="#1a6ea8" emissiveIntensity={0.35} transparent opacity={0.35 + wetness * 0.55} />
      </mesh>
      <mesh position={[0, waterY / 2, faceZ - 0.4]}>
        <boxGeometry args={[plotWidth * 0.72, Math.max(0.2, Math.abs(waterY) * 0.55), 2.4]} />
        <meshStandardMaterial color="#2e86c1" transparent opacity={0.08 + wetness * 0.2} depthWrite={false} />
      </mesh>
    </>}
    {showRoots && <Roots kind={kind} limit={limit} faceZ={faceZ} vigor={visual?.vigor ?? 1} />}
    {Array.from({ length: 6 }, (_, index) => (
      <group key={index} position={[(index - 2.5) * 3.3, 0, 1.7]}>
        <Specimen kind={kind} stress={visual?.waterStress} />
      </group>
    ))}
  </group>;
}

function Roots({ kind, limit, faceZ, vigor }: { kind: CropKind; limit: number; faceZ: number; vigor: number }) {
  const z = faceZ + 0.12;
  const bone = "#e4d2b4";
  if (kind === "turmeric") {
    return <group>
      {Array.from({ length: 5 }, (_, index) => {
        const x = (index - 2) * 3.6;
        return <group key={index} position={[x, -0.55, z]}>
          {limit > 0.5 && <mesh rotation-z={Math.PI / 2}>
            <cylinderGeometry args={[0.11, 0.14, 1.15, 6]} />
            <meshStandardMaterial color="#d0893a" roughness={0.7} />
          </mesh>}
          {limit > 0.9 && <>
            <mesh position={[0.2, -0.45, 0]}>
              <cylinderGeometry args={[0.02, 0.012, 0.7, 4]} />
              <meshStandardMaterial color={bone} />
            </mesh>
            <mesh position={[-0.25, -0.4, 0]} rotation-z={0.4}>
              <cylinderGeometry args={[0.018, 0.01, 0.55, 4]} />
              <meshStandardMaterial color={bone} />
            </mesh>
          </>}
        </group>;
      })}
    </group>;
  }
  if (kind === "wheat" || kind === "millet") {
    const reach = Math.min(limit - 0.15, (kind === "millet" ? 1.15 : 0.95) * vigor);
    if (reach < 0.25) return null;
    return <group>
      {Array.from({ length: 18 }, (_, index) => {
        const x = (index - 8.5) * 1.15;
        const lean = (hash(index + 4) - 0.5) * 0.5;
        return <mesh key={index} position={[x, -reach / 2, z]} rotation-z={lean}>
          <cylinderGeometry args={[0.028, 0.014, reach, 4]} />
          <meshStandardMaterial color={bone} />
        </mesh>;
      })}
    </group>;
  }
  const reach = Math.min(limit - 0.12, (kind === "orchard" ? 1.6 : 2.85) * vigor);
  if (reach < 0.3) return null;
  return <group>
    {Array.from({ length: kind === "orchard" ? 4 : 6 }, (_, index) => {
      const x = (index - (kind === "orchard" ? 1.5 : 2.5)) * (kind === "orchard" ? 4.2 : 3.35);
      return <group key={index} position={[x, 0, z]}>
        <mesh position={[0, -reach / 2, 0]}>
          <cylinderGeometry args={[kind === "orchard" ? 0.09 : 0.07, 0.02, reach, 5]} />
          <meshStandardMaterial color={bone} />
        </mesh>
        {reach > 0.8 && <>
          <mesh position={[-0.28, -0.55, 0]} rotation-z={0.9}>
            <cylinderGeometry args={[0.02, 0.01, 0.7, 4]} />
            <meshStandardMaterial color={bone} />
          </mesh>
          <mesh position={[0.32, -0.85, 0]} rotation-z={-0.85}>
            <cylinderGeometry args={[0.02, 0.01, 0.75, 4]} />
            <meshStandardMaterial color={bone} />
          </mesh>
        </>}
      </group>;
    })}
  </group>;
}

function GrassTufts({ reduced }: { reduced: boolean }) {
  const count = reduced ? 80 : 180;
  const ref = useRef<InstancedMesh>(null);
  const spots = useMemo(() => Array.from({ length: count }, (_, index) => {
    const band = index % 3;
    const x = band === 0 ? 6 + hash(index) * 22 : band === 1 ? -34 + hash(index + 2) * 8 : 28 + hash(index + 5) * 8;
    const z = band === 0 ? 6 + hash(index + 1) * 16 : -8 + hash(index + 3) * 28;
    return { x, z, scale: 0.6 + hash(index + 4) };
  }), [count]);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const object = new Object3D();
    const color = new Color();
    spots.forEach((spot, index) => {
      object.position.set(spot.x, 0.22, spot.z);
      object.rotation.set(0, hash(index) * Math.PI, 0);
      object.scale.set(spot.scale, spot.scale * (0.8 + hash(index + 6)), spot.scale);
      object.updateMatrix();
      mesh.setMatrixAt(index, object.matrix);
      mesh.setColorAt(index, color.set(hash(index + 7) > 0.5 ? "#4e8a3e" : "#6a9a48"));
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
  }, [spots]);
  return <instancedMesh ref={ref} args={[undefined, undefined, count]} raycast={() => null}>
    <coneGeometry args={[0.16, 0.55, 4]} />
    <meshStandardMaterial roughness={0.9} />
  </instancedMesh>;
}

export default function FarmCanvas(props: Props) {
  const { layout, onSelect, reduced, selected, visual, mode, showRoots, showMoisture, soilDepth } = props;
  const lastZ = layout[layout.length - 1].z;
  return <Canvas
    aria-label="Interactive three-dimensional farm"
    frameloop={reduced ? "demand" : "always"}
    dpr={reduced ? 1 : [1, 1.5]}
    shadows={!reduced}
    gl={{ alpha: false, antialias: !reduced, powerPreference: reduced ? "low-power" : "high-performance" }}
    camera={{ position: [18, 9.2, 22], near: 0.35, far: 500, fov: 46 }}
    fallback={<p className="lf-canvas-error">3D is unavailable. Choose 2D map to continue.</p>}
  >
    <color attach="background" args={["#c5d6e6"]} />
    <fog attach="fog" args={["#d5e2ee", 78, 250]} />
    <Atmosphere />
    <hemisphereLight args={["#e7f3ff", "#6a5438", 0.72]} />
    <ambientLight intensity={0.18} />
    <directionalLight
      castShadow={!reduced}
      position={[-48, 24, 14]}
      color="#ffe2b8"
      intensity={2.7}
      shadow-mapSize-width={1024}
      shadow-mapSize-height={1024}
      shadow-camera-near={2}
      shadow-camera-far={130}
      shadow-camera-left={-55}
      shadow-camera-right={55}
      shadow-camera-top={55}
      shadow-camera-bottom={-55}
      shadow-bias={-0.0004}
    />
    <directionalLight position={[28, 14, 24]} color="#d5e6f8" intensity={0.38} />
    <CameraRig {...props} />
    <ContextGuard onUnavailable={props.onUnavailable} />
    <Landscape lastZ={lastZ} reduced={reduced} pit={mode === "soil" ? selected : null} />
    <Fence reduced={reduced} />
    <Farmhouse />
    <Barn />
    <Windmill reduced={reduced} />
    <WaterTower />
    <Shed />
    <Tractor />
    <GrassTufts reduced={reduced} />
    {layout.map((plot) => <CropPlot key={plot.id} plot={plot} active={selected.id === plot.id} visual={plot.id === selected.id ? visual : undefined} reduced={reduced}
      cutaway={mode === "soil" && plot.id === selected.id} onSelect={onSelect} />)}
    {mode === "soil" && <SoilCutaway plot={selected} visual={visual} showRoots={showRoots} showMoisture={showMoisture} soilDepth={soilDepth} onSelect={onSelect} />}
  </Canvas>;
}
