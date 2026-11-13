import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Color, InstancedMesh, Object3D, PlaneGeometry, Vector3 } from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { FieldLayout, FieldSide, plotDepth, plotWidth, sideColors } from "./fieldLayout";

type Props = {
  layout: FieldLayout[];
  selected: FieldLayout;
  side: FieldSide;
  reduced: boolean;
  cameraCommand: { view: "overview" | "focus"; revision: number };
  onSelect: (id: string) => void;
  onUnavailable: () => void;
};

const groundTones = ["#737f45", "#81904f", "#63834c", "#8d9353"];
const cropTones = ["#587e3b", "#a3ad56", "#456d3e", "#739547"];
const hash = (seed: number) => {
  const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return value - Math.floor(value);
};

function CameraRig({ layout, selected, cameraCommand }: Props) {
  const { camera, gl, invalidate, size } = useThree();
  const controlsRef = useRef<OrbitControls>();
  const moving = useRef(false);
  const first = useRef(true);
  const position = useRef(new Vector3());
  const target = useRef(new Vector3());
  const lastZ = layout[layout.length - 1].z;

  useEffect(() => {
    const controls = new OrbitControls(camera, gl.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.11;
    controls.maxPolarAngle = Math.PI * 0.47;
    controls.minDistance = 9;
    controls.maxDistance = Math.max(135, lastZ + 80);
    const stop = () => { moving.current = false; };
    const change = () => {
      const x = Math.max(-45, Math.min(45, controls.target.x));
      const z = Math.max(-35, Math.min(lastZ + 26, controls.target.z));
      camera.position.x += x - controls.target.x;
      camera.position.z += z - controls.target.z;
      camera.position.y -= controls.target.y;
      controls.target.set(x, 0, z);
      invalidate();
    };
    controls.addEventListener("start", stop);
    controls.addEventListener("change", change);
    controlsRef.current = controls;
    return () => {
      controls.dispose();
      controlsRef.current = undefined;
      first.current = true;
    };
  }, [camera, gl, invalidate, lastZ]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const narrow = size.width / Math.max(size.height, 1) < 1.2;
    const focus = cameraCommand.view === "focus";
    const fit = (narrow ? 1.42 : 1) * Math.max(1, (lastZ + 24) / 52);
    target.current.set(focus ? selected.x : 0, 0, focus ? selected.z : (lastZ - 11.5) / 2);
    position.current.copy(target.current).add(focus
      ? new Vector3(narrow ? 17 : 15, narrow ? 32 : 23, narrow ? 23 : 20)
      : new Vector3(31 * fit, 39 * fit, 47 * fit));
    if (first.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      camera.position.copy(position.current);
      controls.target.copy(target.current);
      controls.update();
      first.current = false;
    } else {
      moving.current = true;
    }
    invalidate();
  }, [camera, cameraCommand, invalidate, lastZ, selected.x, selected.z, size.width, size.height]);

  useFrame((_, delta) => {
    const controls = controlsRef.current;
    if (!controls) return;
    if (moving.current) {
      const step = 1 - Math.exp(-7 * Math.min(delta, 0.08));
      camera.position.lerp(position.current, step);
      controls.target.lerp(target.current, step);
      if (camera.position.distanceToSquared(position.current) + controls.target.distanceToSquared(target.current) < 0.0025) {
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

function Landscape({ lastZ, reduced }: { lastZ: number; reduced: boolean }) {
  const geometry = useMemo(() => {
    const terrain = new PlaneGeometry(630, 630, 100, 100);
    terrain.rotateX(-Math.PI / 2);
    const vertices = terrain.getAttribute("position");
    const colors: number[] = [];
    const moss = new Color("#68794c");
    const dry = new Color("#a0a46b");
    const color = new Color();
    for (let index = 0; index < vertices.count; index++) {
      const x = vertices.getX(index);
      const z = vertices.getZ(index);
      const distance = Math.max(Math.abs(x) - 38, -z - 30, z - lastZ - 20, 0);
      const height = Math.min(1, distance / 110) * (5 + 7 * Math.sin(x * 0.031 + z * 0.019) + 9 * Math.cos(z * 0.033 - x * 0.009));
      vertices.setY(index, -0.15 + height);
      color.copy(moss).lerp(dry, 0.46 + 0.23 * Math.sin(x * 0.095 + z * 0.06) + 0.18 * hash(index));
      colors.push(color.r, color.g, color.b);
    }
    terrain.setAttribute("color", vertices.clone());
    terrain.getAttribute("color").array.set(colors);
    terrain.computeVertexNormals();
    return terrain;
  }, [lastZ]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  const trees = useMemo(() => Array.from({ length: reduced ? 44 : 92 }, (_, i) => {
    const x = i % 2 ? 36 + hash(i * 3) * 18 : -36 - hash(i * 3) * 18;
    const z = -27 + hash(i * 3 + 1) * (lastZ + 51);
    const scale = 0.7 + hash(i * 3 + 2) * 0.8;
    return { x, z, scale };
  }), [lastZ, reduced]);
  const crowns = useRef<InstancedMesh>(null);
  const trunks = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    const crown = crowns.current;
    const trunk = trunks.current;
    if (!crown || !trunk) return;
    const object = new Object3D();
    const color = new Color();
    trees.forEach(({ x, z, scale }, index) => {
      const distance = Math.max(Math.abs(x) - 38, -z - 30, z - lastZ - 20, 0);
      const y = Math.min(1, distance / 110) * (5 + 7 * Math.sin(x * 0.031 + z * 0.019) + 9 * Math.cos(z * 0.033 - x * 0.009));
      object.position.set(x, y + 0.65 * scale, z);
      object.scale.setScalar(scale);
      object.updateMatrix();
      trunk.setMatrixAt(index, object.matrix);
      object.position.y = y + 1.8 * scale;
      object.rotation.y = hash(index) * Math.PI;
      object.updateMatrix();
      crown.setMatrixAt(index, object.matrix);
      crown.setColorAt(index, color.set(index % 3 ? "#426849" : "#62834d"));
    });
    [crown, trunk].forEach((mesh) => {
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
    });
    if (crown.instanceColor) crown.instanceColor.needsUpdate = true;
  }, [trees, lastZ]);
  return <>
    <mesh geometry={geometry}><meshStandardMaterial vertexColors roughness={1} /></mesh>
    <mesh rotation-x={-Math.PI / 2} position={[0, -0.03, (lastZ - 11.5) / 2]}>
      <planeGeometry args={[3.5, lastZ + 48]} /><meshStandardMaterial color="#b8a178" />
    </mesh>
    {Array.from({ length: Math.floor((lastZ + 11.5) / 23) + 2 }, (_, index) =>
      <mesh key={index} rotation-x={-Math.PI / 2} position={[0, -0.04, -23 + index * 23]}>
        <planeGeometry args={[63, 2.6]} /><meshStandardMaterial color="#b9a27a" />
      </mesh>)}
    <instancedMesh key={"trunks" + trees.length} ref={trunks} args={[undefined, undefined, trees.length]}>
      <cylinderGeometry args={[0.12, 0.22, 1.65, 5]} /><meshStandardMaterial color="#594d37" />
    </instancedMesh>
    <instancedMesh key={"crowns" + trees.length} ref={crowns} args={[undefined, undefined, trees.length]}>
      <dodecahedronGeometry args={[1.35, 0]} /><meshStandardMaterial roughness={0.9} />
    </instancedMesh>
  </>;
}

function Plot({ plot, active, side, reduced, onSelect }: {
  plot: FieldLayout; active: boolean; side: FieldSide; reduced: boolean; onSelect: Props["onSelect"];
}) {
  const plants = useRef<InstancedMesh>(null);
  const rows = useRef<InstancedMesh>(null);
  const count = 12;
  const plantsPerRow = reduced ? 8 : 17;
  useLayoutEffect(() => {
    if (!plants.current || !rows.current) return;
    const object = new Object3D();
    const color = new Color();
    const base = new Color(cropTones[plot.index % cropTones.length]);
    for (let row = 0; row < count; row++) {
      const x = (row - (count - 1) / 2) * 1.8;
      object.position.set(x, 0.045, 0);
      object.rotation.set(0, 0, 0);
      object.scale.set(1, 1, 1);
      object.updateMatrix();
      rows.current.setMatrixAt(row, object.matrix);
      for (let column = 0; column < plantsPerRow; column++) {
        const index = row * plantsPerRow + column;
        const seed = plot.index * 10000 + index;
        const scale = 0.72 + hash(seed) * 0.36;
        object.position.set(x + (hash(seed + 32) - 0.5) * 0.52, 0.31 * scale, -7.5 + column * 15 / (plantsPerRow - 1));
        object.scale.set(0.86 * scale, scale, 0.72 * scale);
        object.rotation.set(0, hash(seed + 63) * Math.PI, 0.08);
        object.updateMatrix();
        plants.current.setMatrixAt(index, object.matrix);
        plants.current.setColorAt(index, color.copy(base).multiplyScalar(0.68 + hash(seed + 44) * 0.47));
      }
    }
    for (const mesh of [plants.current, rows.current]) {
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
    }
    if (plants.current.instanceColor) plants.current.instanceColor.needsUpdate = true;
  }, [plot.index, plantsPerRow]);

  const tint = active ? sideColors[side] : "#a4a47a";
  return <group position={[plot.x, 0, plot.z]}>
    <mesh rotation-x={-Math.PI / 2} onClick={(event) => {
      if (event.delta > 5) return;
      event.stopPropagation();
      onSelect(plot.id);
    }}>
      <planeGeometry args={[plotWidth, plotDepth]} /><meshStandardMaterial color={groundTones[plot.index % groundTones.length]} />
    </mesh>
    <instancedMesh ref={rows} args={[undefined, undefined, count]} raycast={() => null}>
      <boxGeometry args={[0.96, 0.14, 16.5]} /><meshStandardMaterial color="#645437" roughness={1} />
    </instancedMesh>
    <instancedMesh key={plantsPerRow} ref={plants} args={[undefined, undefined, count * plantsPerRow]} raycast={() => null}>
      <dodecahedronGeometry args={[0.52, 0]} /><meshStandardMaterial roughness={0.94} />
    </instancedMesh>
    {[-1, 1].flatMap((direction) => [
      <mesh key={"x" + direction} position={[direction * plotWidth / 2, 0.085, 0]}>
        <boxGeometry args={[active ? 0.35 : 0.12, 0.2, plotDepth + 0.35]} />
        <meshBasicMaterial color={tint} />
      </mesh>,
      <mesh key={"z" + direction} position={[0, 0.085, direction * plotDepth / 2]}>
        <boxGeometry args={[plotWidth, 0.2, active ? 0.35 : 0.12]} />
        <meshBasicMaterial color={tint} />
      </mesh>,
    ])}
    {active && <mesh position={[0, 1.45, plotDepth / 2 - 0.8]} rotation-z={Math.PI}>
      <coneGeometry args={[0.62, 1.25, 4]} /><meshBasicMaterial color={tint} />
    </mesh>}
  </group>;
}

export default function FarmCanvas(props: Props) {
  const { layout, onSelect, reduced, selected, side } = props;
  const lastZ = layout[layout.length - 1].z;
  return <Canvas
    aria-label="Interactive three-dimensional farm"
    frameloop="demand"
    dpr={reduced ? 1 : [1, 1.4]}
    gl={{ alpha: false, antialias: !reduced, powerPreference: "low-power" }}
    camera={{ position: [31, 39, 47], near: 0.7, far: 550, fov: 44 }}
    fallback={<p className="lf-canvas-error">3D is unavailable. Choose 2D map to continue.</p>}
  >
    <color attach="background" args={["#b6ced2"]} />
    <fog attach="fog" args={["#b6ced2", 75 + Math.max(0, lastZ), 265 + Math.max(0, lastZ)]} />
    <hemisphereLight args={["#effaff", "#a27d4b", 1.65]} />
    <directionalLight position={[-35, 50, 18]} color="#fff1ce" intensity={2.25} />
    <CameraRig {...props} />
    <ContextGuard onUnavailable={props.onUnavailable} />
    <Landscape lastZ={lastZ} reduced={reduced} />
    {layout.map((plot) => <Plot key={plot.id} plot={plot} active={selected.id === plot.id} side={side} reduced={reduced} onSelect={onSelect} />)}
  </Canvas>;
}
