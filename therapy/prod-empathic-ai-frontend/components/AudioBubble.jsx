"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { MeshDistortMaterial } from "@react-three/drei";
import { useMemo, useRef } from "react";

function averageFft(fft) {
  if (!Array.isArray(fft) || fft.length === 0) {
    return 0;
  }

  const total = fft.reduce((sum, value) => sum + Number(value || 0), 0);
  return total / fft.length;
}

function AudioReactiveSphere({ activity, assistantActivity }) {
  const meshRef = useRef(null);
  const glowRef = useRef(null);

  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();

    if (meshRef.current) {
      const pulse = 1 + activity * 0.9 + assistantActivity * 0.5;
      meshRef.current.rotation.y = time * 0.18;
      meshRef.current.rotation.x = time * 0.1;
      meshRef.current.scale.setScalar(pulse);
    }

    if (glowRef.current) {
      glowRef.current.rotation.z = time * 0.08;
      glowRef.current.scale.setScalar(1.2 + activity * 0.7);
    }
  });

  return (
    <>
      <mesh ref={glowRef}>
        <torusGeometry args={[2.2, 0.08, 32, 96]} />
        <meshStandardMaterial color="#f3ffb6" emissive="#e6ff6a" emissiveIntensity={1.5 + activity * 2.5} />
      </mesh>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.5, 20]} />
        <MeshDistortMaterial
          color="#f6fbff"
          emissive="#8bd8ff"
          emissiveIntensity={1.4 + assistantActivity * 1.2}
          distort={0.32 + activity * 0.55}
          speed={1.6 + activity * 2.6}
          roughness={0.18}
          metalness={0.82}
        />
      </mesh>
    </>
  );
}

export default function AudioBubble({
  micFft = [],
  assistantFft = [],
  isConnected = false,
  isMuted = false,
  isPlaying = false,
}) {
  const micLevel = useMemo(() => Math.min(averageFft(micFft), 1), [micFft]);
  const assistantLevel = useMemo(() => Math.min(averageFft(assistantFft), 1), [assistantFft]);
  const activityLabel = !isConnected ? "Idle" : isMuted ? "Muted" : isPlaying ? "Listening and speaking" : "Listening";

  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-white/14 bg-[radial-gradient(circle_at_top,_rgba(252,242,172,0.24),_transparent_28%),linear-gradient(160deg,_rgba(9,22,39,0.92),_rgba(25,45,78,0.94))] p-6 shadow-[0_30px_80px_rgba(4,10,22,0.45)]">
      <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent,rgba(255,255,255,0.06),transparent)]" />
      <div className="relative flex min-h-[22rem] flex-col justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-sky-100/70">Live Voice</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Empathic session</h2>
        </div>

        <div className="h-[18rem]">
          <Canvas camera={{ position: [0, 0, 5.5], fov: 45 }}>
            <color attach="background" args={["#07111e"]} />
            <ambientLight intensity={0.9} />
            <pointLight position={[0, 4, 6]} intensity={22} color="#8ddfff" />
            <pointLight position={[-4, -2, -5]} intensity={8} color="#fff2ab" />
            <AudioReactiveSphere activity={micLevel} assistantActivity={assistantLevel} />
          </Canvas>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-3">
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-sky-100/60">State</p>
            <p className="mt-2 text-sm font-medium text-white">{activityLabel}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-3">
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-sky-100/60">Mic Activity</p>
            <p className="mt-2 text-sm font-medium text-white">{Math.round(micLevel * 100)}%</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-3">
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-sky-100/60">Assistant Audio</p>
            <p className="mt-2 text-sm font-medium text-white">{Math.round(assistantLevel * 100)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
