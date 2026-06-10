"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { EffectComposer, EffectPass, RenderPass } from "postprocessing";
import { ASCIIEffect } from "./ascii-effect";
import { motion } from "framer-motion";

interface FloatingShape {
  mesh: THREE.Mesh;
  baseY: number;
  phase: number;
  rotationSpeed: { x: number; y: number; z: number };
  floatSpeed: number;
  floatAmplitude: number;
}

export function AsciiScene() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);

    const camera = new THREE.PerspectiveCamera(60, width / height, 1, 2000);
    camera.position.z = 700;
    camera.position.y = 50;

    const renderer = new THREE.WebGLRenderer({ antialias: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);

    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(
      new EffectPass(
        camera,
        new ASCIIEffect({
          characters: " .:░▒▓█",
          cellSize: 12,
          color: "#ffffff",
          background: "#ffffff",
          invert: true,
          colorize: true,
        }),
      ),
    );

    renderer.domElement.style.position = "absolute";
    renderer.domElement.style.inset = "0";
    renderer.domElement.style.zIndex = "0";
    renderer.domElement.style.pointerEvents = "auto";
    renderer.domElement.style.backgroundColor = "white";

    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.1);
    scene.add(ambientLight);

    const light1 = new THREE.DirectionalLight(0xff9045, 3.5);
    light1.position.set(300, 400, 500);
    scene.add(light1);

    const light2 = new THREE.DirectionalLight(0x4590ff, 3.5);
    light2.position.set(-200, -200, -400);
    scene.add(light2);

    const mouseLight = new THREE.PointLight(0xffffff, 2, 600);
    mouseLight.position.set(0, 0, 200);
    scene.add(mouseLight);

    // Interactive raycasting
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const plane = new THREE.Plane();
    const planeNormal = new THREE.Vector3(0, 0, 1);
    const intersection = new THREE.Vector3();
    const offset = new THREE.Vector3();
    let draggedShape: FloatingShape | null = null;

    const geometries: THREE.BufferGeometry[] = [];
    const shapes: FloatingShape[] = [];

    const sharedMaterial = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      flatShading: true,
      metalness: 0.2,
      roughness: 0.1,
    });

    const createShape = (
      geometry: THREE.BufferGeometry,
      x: number,
      y: number,
      z: number,
      scale: number,
    ): FloatingShape => {
      const mesh = new THREE.Mesh(geometry, sharedMaterial);
      mesh.position.set(x, y, z);
      mesh.scale.setScalar(scale);
      mesh.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI,
        Math.random() * Math.PI,
      );
      scene.add(mesh);

      return {
        mesh,
        baseY: y,
        phase: Math.random() * Math.PI * 2,
        // Configure random rotation speeds for each axis
        rotationSpeed: {
          x: (Math.random() - 0.5) * 0.001,
          y: (Math.random() - 0.5) * 0.0015,
          z: (Math.random() - 0.5) * 0.001,
        },
        floatSpeed: 0.0002 + Math.random() * 0.0003,
        floatAmplitude: 15 + Math.random() * 25,
      };
    };

    const icosahedronGeom = new THREE.IcosahedronGeometry(50, 0);
    const octahedronGeom = new THREE.OctahedronGeometry(45, 0);
    const dodecahedronGeom = new THREE.DodecahedronGeometry(40, 0);
    const tetrahedronGeom = new THREE.TetrahedronGeometry(55, 0);
    const torusGeom = new THREE.TorusGeometry(35, 15, 8, 6);

    geometries.push(
      icosahedronGeom,
      octahedronGeom,
      dodecahedronGeom,
      tetrahedronGeom,
      torusGeom,
    );

    shapes.push(createShape(icosahedronGeom, -320, 120, -100, 1.8));
    shapes.push(createShape(octahedronGeom, 380, -80, -200, 2.2));
    shapes.push(createShape(dodecahedronGeom, -180, -180, 50, 1.5));
    shapes.push(createShape(tetrahedronGeom, 280, 200, -150, 1.6));

    shapes.push(createShape(icosahedronGeom, 150, 280, -300, 1.0));
    shapes.push(createShape(octahedronGeom, -400, -50, -250, 1.2));
    shapes.push(createShape(dodecahedronGeom, 450, 50, -350, 0.9));
    shapes.push(createShape(tetrahedronGeom, -250, 250, -200, 0.8));
    shapes.push(createShape(torusGeom, -80, -280, -100, 1.3));

    shapes.push(createShape(icosahedronGeom, 500, -200, -400, 0.7));
    shapes.push(createShape(octahedronGeom, -480, 180, -350, 0.6));

    let animationId: number;
    const start = Date.now();

    let mouseX = 0;
    let mouseY = 0;
    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    const onDocumentMouseMove = (event: MouseEvent) => {
      mouseX = event.clientX - windowHalfX;
      mouseY = event.clientY - windowHalfY;

      // Update normalized mouse coordinates for raycasting
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      if (draggedShape) {
        raycaster.setFromCamera(mouse, camera);
        if (raycaster.ray.intersectPlane(plane, intersection)) {
          draggedShape.mesh.position.copy(intersection.sub(offset));
          // Update baseY so it floats around the new position when released
          draggedShape.baseY = draggedShape.mesh.position.y;
        }
      }
    };

    const onDocumentMouseDown = (event: MouseEvent) => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(
        shapes.map((s) => s.mesh),
        false,
      );

      if (intersects.length > 0) {
        const object = intersects[0].object as THREE.Mesh;
        draggedShape = shapes.find((s) => s.mesh === object) || null;

        if (draggedShape) {
          // Set drag plane at the object's current z-depth
          plane.setFromNormalAndCoplanarPoint(planeNormal, object.position);

          if (raycaster.ray.intersectPlane(plane, intersection)) {
            offset.copy(intersection).sub(object.position);
          }

          container.style.cursor = "grabbing";
        }
      }
    };

    const onDocumentMouseUp = () => {
      draggedShape = null;
      container.style.cursor = "auto";
    };

    document.addEventListener("mousemove", onDocumentMouseMove);
    document.addEventListener("mousedown", onDocumentMouseDown);
    document.addEventListener("mouseup", onDocumentMouseUp);

    const animate = () => {
      animationId = requestAnimationFrame(animate);

      mouseLight.position.x += (mouseX - mouseLight.position.x) * 0.1;
      mouseLight.position.y += (-mouseY - mouseLight.position.y) * 0.1;

      const elapsed = Date.now() - start;

      for (const shape of shapes) {
        shape.mesh.rotation.x += shape.rotationSpeed.x;
        shape.mesh.rotation.y += shape.rotationSpeed.y;
        shape.mesh.rotation.z += shape.rotationSpeed.z;

        // Only float if not being dragged
        if (shape !== draggedShape) {
          shape.mesh.position.y =
            shape.baseY +
            Math.sin(elapsed * shape.floatSpeed + shape.phase) *
              shape.floatAmplitude;
        }
      }

      camera.position.x = Math.sin(elapsed * 0.0001) * 30;
      camera.position.y = 50 + Math.cos(elapsed * 0.00015) * 20;
      camera.lookAt(0, 0, 0);

      composer.render();
    };

    animate();

    const handleResize = () => {
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;

      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();

      renderer.setSize(newWidth, newHeight);
      composer.setSize(newWidth, newHeight);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      document.removeEventListener("mousemove", onDocumentMouseMove);
      document.removeEventListener("mousedown", onDocumentMouseDown);
      document.removeEventListener("mouseup", onDocumentMouseUp);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationId);
      container.removeChild(renderer.domElement);
      renderer.dispose();
      composer.dispose();
      for (const g of geometries) g.dispose();
      sharedMaterial.dispose();
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      ref={containerRef}
      className="absolute inset-0 overflow-hidden"
      aria-hidden="true"
    />
  );
}
